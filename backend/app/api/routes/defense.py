from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.alert import Alert
from backend.app.models.analyst_action import AnalystAction
from backend.app.models.incident import Incident
from backend.app.models.investigation import Investigation
from backend.app.models.user import User
from backend.app.security.dependencies import get_current_user, require_role

router = APIRouter(
    prefix="/api/defense",
    tags=["Defense Department"],
)


class ApplyDefensePayload(BaseModel):
    investigation_id: str
    incident_id: str
    action_type: str = Field(description="e.g. VLAN_QUARANTINE, CREDENTIAL_ROTATION, BLOCK_IP, FIRMWARE_PATCH, RATE_LIMIT, CUSTOM")
    action_label: str
    rationale: str
    defense_note: str


def _diagnose_threat(attack_class: str, src_ip: str, dst_ip: str, src_port: Any, dst_port: Any, has_real_ips: bool = True) -> str:
    cls = (attack_class or "").upper()
    prefix = "" if has_real_ips else "Flow Vector: "
    if "DOS" in cls or "DDOS" in cls:
        if has_real_ips:
            return f"Volumetric packet flood and resource exhaustion attempt targeting endpoint {dst_ip} (Port {dst_port}) from hostile host {src_ip}."
        return f"Volumetric flow exhaustion pattern identified in network telemetry vector targeting {dst_ip}."
    if "PORT_SCAN" in cls or "SCAN" in cls:
        if has_real_ips:
            return f"Systematic TCP/UDP port sweep probing host {dst_ip} for open daemon listeners on port {dst_port} originating from {src_ip}."
        return f"Systematic multi-port discovery sweep identified across local subnet endpoints."
    if "BRUTE_FORCE" in cls:
        if has_real_ips:
            return f"Repetitive dictionary authentication attempts against service on port {dst_port} originating from {src_ip}."
        return f"High-frequency credential brute-force pattern detected in connection telemetry."
    if "BOTNET" in cls:
        if has_real_ips:
            return f"Mirai-style Command & Control (C2) beaconing or automated recruitment traffic between {src_ip} and {dst_ip}."
        return f"Automated botnet C2 beaconing and recruitment synchronization detected in network flow."
    if "BACKDOOR" in cls:
        if has_real_ips:
            return f"Covert reverse listener or unauthorized backdoor connection active between {src_ip} and {dst_ip}."
        return f"Unauthorized persistent reverse shell or backdoor traffic signature observed in flow."
    if "EXPLOIT" in cls or "FUZZING" in cls:
        if has_real_ips:
            return f"High-entropy or vulnerability payload sent to crash embedded network buffers on {dst_ip} from {src_ip}."
        return f"High-entropy malformed packet sequence targeting embedded buffer parsers on {dst_ip}."
    return f"{prefix}Suspicious network anomaly detected for asset {dst_ip} (Class: {attack_class})."


@router.get("/open-investigations")
def get_open_investigations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Returns only open investigations (status != 'COMPLETED') linked with their
    incident and correlated alert network detection details for defense triage.
    """
    investigations = db.scalars(
        select(Investigation)
        .where(Investigation.status.in_(["IN_PROGRESS", "NOT_STARTED", "ON_HOLD", "OPEN"]))
        .order_by(desc(Investigation.id))
    ).all()

    results: list[dict[str, Any]] = []

    for inv in investigations:
        incident = db.scalar(
            select(Incident).where(Incident.incident_id == inv.incident_id)
        )
        if not incident:
            continue

        alert = None
        if incident.alert_id:
            alert = db.scalar(
                select(Alert).where(Alert.alert_id == incident.alert_id)
            )

        has_real_ips = bool(alert and alert.source_ip and alert.destination_ip)
        src_ip = alert.source_ip if (alert and alert.source_ip) else "Flow Telemetry (Subnet Origin)"
        dst_ip = alert.destination_ip if (alert and alert.destination_ip) else "Target IoT Node (Sensor Net)"
        src_port = alert.source_port if (alert and alert.source_port is not None) else "—"
        dst_port = alert.destination_port if (alert and alert.destination_port is not None) else "—"
        attack_class = (alert.predicted_class if alert and alert.predicted_class else None) or (incident.severity or "ANOMALY")
        confidence_pct = int(alert.confidence * 100) if alert and alert.confidence is not None else 85
        severity = (alert.severity if alert and alert.severity else None) or incident.severity or "HIGH"
        protocol = (alert.protocol if alert and alert.protocol else None) or ("TCP" if has_real_ips else "Flow Vector")

        diagnosis = _diagnose_threat(attack_class, src_ip, dst_ip, src_port, dst_port, has_real_ips)

        defense_count = db.scalar(
            select(func.count(AnalystAction.id)).where(
                AnalystAction.incident_id == incident.incident_id,
                AnalystAction.action_type.in_(["DEFEND_INCIDENT", "DEFENSE_ACTION"]),
            )
        ) or 0

        results.append({
            "investigation_id": inv.investigation_id,
            "incident_id": incident.incident_id,
            "incident_title": incident.title,
            "incident_severity": severity,
            "incident_priority": incident.priority,
            "investigation_status": inv.status,
            "started_at": inv.started_at.isoformat() if inv.started_at else None,
            "analyst_notes": inv.analyst_notes or "",
            "conclusion": inv.conclusion or "",
            "alert_id": alert.alert_id if alert else None,
            "predicted_class": attack_class,
            "confidence": confidence_pct,
            "confidence_pct": confidence_pct,
            "source_ip": src_ip,
            "destination_ip": dst_ip,
            "source_port": src_port,
            "destination_port": dst_port,
            "protocol": protocol,
            "diagnosis": diagnosis,
            "threat_diagnosis": diagnosis,
            "defense_actions_count": defense_count,
            "has_real_ips": has_real_ips,
            "telemetry_source": "RAW_PACKET_HEADER" if has_real_ips else "AGGREGATED_FLOW_VECTOR",
        })

    return results


@router.post("/apply-action")
def apply_defense_action(
    payload: ApplyDefensePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "SOC_ANALYST")),
) -> dict[str, Any]:
    """
    Applies defense action to an incident, automatically appends a defense note
    into the linked investigation department dossier, and logs an Analyst Action.
    """
    inv = db.scalar(
        select(Investigation).where(Investigation.investigation_id == payload.investigation_id)
    )
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{payload.investigation_id}' not found.",
        )

    incident = db.scalar(
        select(Incident).where(Incident.incident_id == payload.incident_id)
    )

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if inv.incident_id != incident.incident_id:
        raise HTTPException(status_code=400, detail="Investigation does not belong to this incident.")
    if inv.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Cannot apply defense actions to a completed investigation.")

    now_utc = datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Formulate structured defense note
    defense_header = f"--- [DEFENSE ACTION: {payload.action_label.upper()}] ---"
    defense_body = (
        f"{defense_header}\n"
        f"Timestamp: {timestamp_str}\n"
        f"Operator: {current_user.username}\n"
        f"Rationale: {payload.rationale.strip()}\n"
        f"Details: {payload.defense_note.strip()}\n"
        f"Status: Containment Applied & Synchronized to Investigation Department\n"
    )

    # Append to investigation analyst notes
    existing_notes = (inv.analyst_notes or "").strip()
    if existing_notes:
        inv.analyst_notes = f"{existing_notes}\n\n{defense_body}"
    else:
        inv.analyst_notes = defense_body

    # Log in Analyst Actions ledger
    action = AnalystAction(
        action_id=f"ZUKA-ACT-{secrets.token_hex(4).upper()}",
        incident_id=payload.incident_id,
        investigation_id=payload.investigation_id,
        analyst_id=current_user.id,
        action_type="DEFEND_INCIDENT",
        description=(
            f"Defense action '{payload.action_label}' applied by {current_user.username}. "
            f"Containment note synchronized to Investigation Department."
        ),
    )
    db.add(action)

    db.commit()
    db.refresh(inv)

    return {
        "status": "SUCCESS",
        "success": True,
        "message": f"Defense action '{payload.action_label}' applied successfully. Note synchronized to Investigation Department.",
        "investigation_id": inv.investigation_id,
        "incident_id": payload.incident_id,
        "analyst_action_id": action.id,
        "analyst_notes": inv.analyst_notes,
        "updated_notes": inv.analyst_notes,
    }
