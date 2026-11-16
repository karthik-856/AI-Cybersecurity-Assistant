from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

from datetime import datetime
from typing import Any
from uuid import uuid4
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.alert import Alert
from backend.app.models.analyst_action import AnalystAction
from backend.app.models.audit_log import AuditLog
from backend.app.models.incident import Incident
from backend.app.models.investigation import Investigation
from backend.app.models.user import User
from backend.app.zuka_assistant.audit import log_analyst_action_entry, log_assistant_audit
from backend.app.zuka_assistant.schemas import AssistantCard


# ============================================================================
# 1. SUMMARIZE INCIDENT (READ TOOL)
# ============================================================================

def tool_summarize_incident(db: Session, incident_id: str, user: User) -> dict[str, Any]:
    """Fetch factual record of incident, linked alert, investigation, and timeline notes."""
    inc = db.scalar(
        select(Incident).where(func.upper(Incident.incident_id) == incident_id.upper())
    )

    if not inc:
        # Check if user passed an alert ID by mistake
        alt = db.scalar(select(Alert).where(func.upper(Alert.alert_id) == incident_id.upper()))
        if alt and alt.incidents:
            inc = alt.incidents[0]
        else:
            return {
                "success": False,
                "reply": f"Incident '{incident_id}' was not found in the database. Please verify the incident ID (e.g. INC-1042 or ZUKA-INC-...).",
                "card": AssistantCard(
                    card_type="error_card",
                    data={"error": f"Incident '{incident_id}' not found."},
                ),
            }

    # Fetch investigation
    inv = inc.investigation
    alert = inc.alert
    owner_name = inc.assigned_to.username if inc.assigned_to else "Unassigned"

    # Fetch recent actions
    actions = db.scalars(
        select(AnalystAction)
        .where(AnalystAction.incident_id == inc.incident_id)
        .order_by(AnalystAction.created_at.desc())
        .limit(5)
    ).all()

    recent_actions_data = [
        {
            "action_id": a.action_id,
            "action_type": a.action_type,
            "description": a.description,
            "result": a.result,
            "timestamp": a.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
        for a in actions
    ]

    card_data = {
        "incident_id": inc.incident_id,
        "title": inc.title,
        "description": inc.description or "No description provided.",
        "status": inc.status,
        "severity": inc.severity,
        "priority": inc.priority,
        "owner": owner_name,
        "escalation_level": inc.escalation_level,
        "created_at": inc.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "resolved_at": inc.resolved_at.strftime("%Y-%m-%d %H:%M:%S UTC") if inc.resolved_at else None,
        "resolution_summary": inc.resolution_summary,
        "linked_alert": {
            "alert_id": alert.alert_id if alert else "None",
            "status": alert.status if alert else "None",
            "predicted_class": alert.predicted_class if alert else "N/A",
            "confidence": f"{alert.confidence:.1%}" if alert else "N/A",
            "source_ip": alert.source_ip if alert else "N/A",
            "destination_ip": alert.destination_ip if alert else "N/A",
            "severity": alert.severity if alert else "N/A",
        } if alert else None,
        "investigation": {
            "investigation_id": inv.investigation_id if inv else "Not created",
            "status": inv.status if inv else "NOT_STARTED",
            "notes": inv.analyst_notes if inv and inv.analyst_notes else "No notes logged yet.",
            "conclusion": inv.conclusion if inv and inv.conclusion else "Pending conclusion.",
            "started_at": inv.started_at.strftime("%Y-%m-%d %H:%M:%S UTC") if (inv and inv.started_at) else None,
        } if inv else None,
        "recent_actions": recent_actions_data,
    }

    # Grounded factual summary string
    reply_lines = [
        f"**Summary for {inc.incident_id}: {inc.title}**",
        f"- **Status**: `{inc.status}` | **Severity**: `{inc.severity}` | **Priority**: `{inc.priority}`",
        f"- **Owner**: `{owner_name}` | **Escalation**: Level {inc.escalation_level}",
    ]

    if alert:
        reply_lines.append(
            f"- **Linked Alert**: `{alert.alert_id}` ({alert.predicted_class}, {alert.confidence:.1%} conf, Status: `{alert.status}`)"
        )
        if alert.source_ip and alert.destination_ip:
            reply_lines.append(f"- **Traffic**: `{alert.source_ip}` → `{alert.destination_ip}`")

    if inv:
        reply_lines.append(f"- **Investigation**: `{inv.status}` (ID: `{inv.investigation_id}`)")
        if inv.conclusion:
            reply_lines.append(f"- **Conclusion**: {inv.conclusion}")
        elif inv.analyst_notes:
            first_note = inv.analyst_notes.splitlines()[-1] if inv.analyst_notes else ""
            reply_lines.append(f"- **Latest Note**: {first_note[:100]}...")
    else:
        reply_lines.append("- **Investigation**: Not started")

    return {
        "success": True,
        "reply": "\n".join(reply_lines),
        "card": AssistantCard(card_type="incident_summary", data=card_data),
        "data": card_data,
    }


# ============================================================================
# 2. SUMMARIZE APP / PLATFORM (READ TOOL)
# ============================================================================

def tool_summarize_app(db: Session, user: User) -> dict[str, Any]:
    """Fetch live counts of alerts, incidents, investigations, and telemetry."""
    alert_status_rows = db.execute(
        select(func.upper(Alert.status), func.count(Alert.id)).group_by(func.upper(Alert.status))
    ).all()
    alert_status_counts = {(status or "UNKNOWN"): count for status, count in alert_status_rows}
    total_alerts = sum(alert_status_counts.values())
    open_alerts = alert_status_counts.get("OPEN", 0)
    acked_alerts = alert_status_counts.get("ACKNOWLEDGED", 0)

    incident_status_rows = db.execute(
        select(func.upper(Incident.status), func.count(Incident.id)).group_by(func.upper(Incident.status))
    ).all()
    incident_status_counts = {(status or "UNKNOWN"): count for status, count in incident_status_rows}
    total_incidents = sum(incident_status_counts.values())
    open_incidents = incident_status_counts.get("OPEN", 0)

    active_investigations = db.scalar(
        select(func.count(Investigation.id)).where(Investigation.status == "IN_PROGRESS")
    ) or 0

    stats = {
        "total_alerts": total_alerts,
        "open_alerts": open_alerts,
        "acknowledged_alerts": acked_alerts,
        "alert_status_counts": alert_status_counts,
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "resolved_incidents": incident_status_counts.get("RESOLVED", 0),
        "closed_incidents": incident_status_counts.get("CLOSED", 0),
        "incident_status_counts": incident_status_counts,
        "active_investigations": active_investigations,
    }

    alert_breakdown = ", ".join(
        f"{alert_status_counts[status]} {status}" for status in sorted(alert_status_counts)
    )
    incident_breakdown = ", ".join(
        f"{incident_status_counts[status]} {status}" for status in sorted(incident_status_counts)
    )

    reply = (
        f"**ZUKA SOC Platform Status**:\n"
        f"- **Alerts**: {total_alerts} total ({alert_breakdown})\n"
        f"- **Incidents**: {total_incidents} total ({incident_breakdown})\n"
        f"- **Active Investigations**: {active_investigations} in progress\n"
        f"- **Data Source**: Current counts are read from the connected database."
    )

    return {
        "success": True,
        "reply": reply,
        "card": AssistantCard(card_type="incident_summary", data={"platform_metrics": stats}),
        "data": stats,
    }


# ============================================================================
# 3. ACKNOWLEDGE ALERT (WRITE TOOL)
# ============================================================================

def tool_acknowledge_alert(
    db: Session,
    alert_id: str | None,
    linked_incident_id: str | None,
    user: User,
) -> dict[str, Any]:
    """Acknowledge an alert directly or by referencing an incident's linked alert."""
    target_alert: Alert | None = None

    if alert_id:
        target_alert = db.scalar(select(Alert).where(func.upper(Alert.alert_id) == alert_id.upper()))
    elif linked_incident_id:
        inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == linked_incident_id.upper()))
        if inc and inc.alert:
            target_alert = inc.alert

    if not target_alert:
        ref = alert_id or f"linked to {linked_incident_id}"
        return {
            "success": False,
            "reply": f"Could not find Alert '{ref}' in the database.",
            "card": AssistantCard(card_type="error_card", data={"error": f"Alert '{ref}' not found."}),
        }

    previous_status = target_alert.status
    if previous_status == "ACKNOWLEDGED":
        return {
            "success": True,
            "reply": f"Alert `{target_alert.alert_id}` is already `ACKNOWLEDGED`. No change needed.",
            "card": AssistantCard(
                card_type="alert_card",
                data={
                    "alert_id": target_alert.alert_id,
                    "status": target_alert.status,
                    "severity": target_alert.severity,
                    "predicted_class": target_alert.predicted_class,
                },
            ),
        }

    # Update database
    target_alert.status = "ACKNOWLEDGED"

    # Also update linked incident if it is OPEN
    linked_inc = target_alert.incidents[0] if target_alert.incidents else None
    if linked_inc and linked_inc.status == "OPEN":
        linked_inc.status = "ACKNOWLEDGED"

    # Audit & Analyst Action Logging
    log_assistant_audit(
        db=db,
        user=user,
        action="ACKNOWLEDGE_ALERT",
        resource_type="Alert",
        resource_id=target_alert.alert_id,
        description=f"User {user.username} acknowledged alert {target_alert.alert_id}",
        metadata={"previous_status": previous_status, "new_status": "ACKNOWLEDGED"},
    )
    action_rec = log_analyst_action_entry(
        db=db,
        user=user,
        action_type="ACKNOWLEDGE_ALERT",
        description=f"Acknowledged alert {target_alert.alert_id}",
        incident_id=linked_inc.incident_id if linked_inc else None,
        result="SUCCESS",
    )

    db.commit()
    db.refresh(target_alert)

    inc_note = f" Linked incident `{linked_inc.incident_id}` is now unlocked for investigation." if linked_inc else ""
    return {
        "success": True,
        "reply": f"Done. `{target_alert.alert_id}` is now `ACKNOWLEDGED`. (Action Ref: `{action_rec.action_id}`).{inc_note}",
        "card": AssistantCard(
            card_type="action_success",
            data={
                "alert_id": target_alert.alert_id,
                "status": "ACKNOWLEDGED",
                "action_id": action_rec.action_id,
                "linked_incident_id": linked_inc.incident_id if linked_inc else None,
            },
        ),
    }


# ============================================================================
# 4. INVESTIGATE INCIDENT (WRITE TOOL)
# ============================================================================

def tool_investigate_incident(db: Session, incident_id: str, user: User) -> dict[str, Any]:
    """Start or open investigation for an incident, enforcing SOC workflow rules."""
    inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == incident_id.upper()))
    if not inc:
        return {
            "success": False,
            "reply": f"Incident '{incident_id}' not found.",
            "card": AssistantCard(card_type="error_card", data={"error": f"Incident '{incident_id}' not found."}),
        }

    # Workflow Check: linked alert must be acknowledged first
    if inc.alert and inc.alert.status != "ACKNOWLEDGED":
        return {
            "success": False,
            "reply": f"⚠️ **Investigation Locked**: Linked alert `{inc.alert_id}` has not been acknowledged yet. In SOC protocol, an alert must be acknowledged before starting investigation. You can type `acknowledge alert {inc.alert_id}` to proceed.",
            "card": AssistantCard(
                card_type="error_card",
                data={
                    "error": "Alert not acknowledged",
                    "incident_id": inc.incident_id,
                    "alert_id": inc.alert_id,
                },
            ),
        }

    # Get or create investigation record
    inv = inc.investigation
    is_new = False
    if not inv:
        inv = Investigation(
            investigation_id=f"INV-{uuid4().hex[:8].upper()}",
            incident_id=inc.incident_id,
            status="IN_PROGRESS",
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(inv)
        db.flush()
        is_new = True
    else:
        if inv.status in ["NOT_STARTED", "PENDING"]:
            inv.status = "IN_PROGRESS"
            inv.started_at = datetime.utcnow()

    # Update incident status to INVESTIGATING if currently OPEN or ACKNOWLEDGED
    if inc.status in ["OPEN", "ACKNOWLEDGED"]:
        inc.status = "INVESTIGATING"

    if not inc.assigned_to_id:
        inc.assigned_to_id = user.id

    action_rec = log_analyst_action_entry(
        db=db,
        user=user,
        action_type="START_INVESTIGATION",
        description=f"Started investigation for incident {inc.incident_id}",
        incident_id=inc.incident_id,
        investigation_id=inv.investigation_id,
        result="SUCCESS",
    )
    log_assistant_audit(
        db=db,
        user=user,
        action="START_INVESTIGATION",
        resource_type="Investigation",
        resource_id=inv.investigation_id,
        description=f"Investigation {inv.investigation_id} opened for {inc.incident_id}",
    )

    db.commit()
    db.refresh(inc)

    card_data = {
        "incident_id": inc.incident_id,
        "investigation_id": inv.investigation_id,
        "status": inv.status,
        "assigned_to": user.username,
        "notes": inv.analyst_notes or "No notes yet.",
        "conclusion": inv.conclusion or "Investigation currently in progress.",
        "findings": {
            "attack_type": inc.alert.predicted_class if inc.alert else "N/A",
            "source_ip": inc.alert.source_ip if inc.alert else "N/A",
            "destination_ip": inc.alert.destination_ip if inc.alert else "N/A",
            "severity": inc.severity,
        },
    }

    reply = (
        f"Investigation **{inv.investigation_id}** is active for incident `{inc.incident_id}`.\n"
        f"- **Assigned Analyst**: `{user.username}`\n"
        f"- **Investigation Status**: `{inv.status}`\n"
        f"- **Threat Type**: `{card_data['findings']['attack_type']}` (`{card_data['findings']['source_ip']}` → `{card_data['findings']['destination_ip']}`)\n"
        f"You can now add analyst notes using: `add analyst note to {inc.incident_id}: <notes>`."
    )

    return {
        "success": True,
        "reply": reply,
        "card": AssistantCard(card_type="investigation_card", data=card_data),
        "data": card_data,
    }


# ============================================================================
# 5. ADD ANALYST NOTE (WRITE TOOL)
# ============================================================================

def tool_add_note(db: Session, incident_id: str, note_text: str, user: User) -> dict[str, Any]:
    """Add timestamped analyst note to the incident's investigation record."""
    if not note_text.strip():
        return {
            "success": False,
            "reply": "Note content cannot be empty. Usage: `add analyst note to INC-1042: <your note here>`",
            "card": AssistantCard(card_type="error_card", data={"error": "Empty note"}),
        }

    inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == incident_id.upper()))
    if not inc:
        return {
            "success": False,
            "reply": f"Incident '{incident_id}' not found.",
            "card": AssistantCard(card_type="error_card", data={"error": f"Incident '{incident_id}' not found."}),
        }

    inv = inc.investigation
    if not inv:
        inv = Investigation(
            investigation_id=f"INV-{uuid4().hex[:8].upper()}",
            incident_id=inc.incident_id,
            status="IN_PROGRESS",
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(inv)
        db.flush()

    timestamp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    formatted_entry = f"[{timestamp_str} | Analyst: {user.username}]\n{note_text.strip()}"

    if inv.analyst_notes:
        inv.analyst_notes = f"{inv.analyst_notes}\n\n{formatted_entry}"
    else:
        inv.analyst_notes = formatted_entry

    action_rec = log_analyst_action_entry(
        db=db,
        user=user,
        action_type="ADD_NOTE",
        description=f"Added analyst note: {note_text[:60]}...",
        incident_id=inc.incident_id,
        investigation_id=inv.investigation_id,
        result="SUCCESS",
    )
    log_assistant_audit(
        db=db,
        user=user,
        action="ADD_ANALYST_NOTE",
        resource_type="Investigation",
        resource_id=inv.investigation_id,
        description=f"Analyst note added to {inc.incident_id}",
    )

    db.commit()

    return {
        "success": True,
        "reply": f"Saved analyst note for incident `{inc.incident_id}`. Action reference: `{action_rec.action_id}`.",
        "card": AssistantCard(
            card_type="action_success",
            data={
                "action_id": action_rec.action_id,
                "incident_id": inc.incident_id,
                "note_preview": note_text[:120],
                "total_notes": inv.analyst_notes,
            },
        ),
    }


# ============================================================================
# 6. ASSIGN INCIDENT (WRITE TOOL)
# ============================================================================

def tool_assign_incident(db: Session, incident_id: str, assignee: str, user: User) -> dict[str, Any]:
    """Assign incident to a specific analyst username."""
    inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == incident_id.upper()))
    if not inc:
        return {
            "success": False,
            "reply": f"Incident '{incident_id}' not found.",
            "card": AssistantCard(card_type="error_card", data={"error": f"Incident '{incident_id}' not found."}),
        }

    target_user = db.scalar(select(User).where(func.upper(User.username) == assignee.upper()))
    if not target_user:
        return {
            "success": False,
            "reply": f"User '{assignee}' was not found in the system.",
            "card": AssistantCard(card_type="error_card", data={"error": f"User '{assignee}' not found."}),
        }

    old_owner = inc.assigned_to.username if inc.assigned_to else "Unassigned"
    inc.assigned_to_id = target_user.id
    if inc.status == "OPEN":
        inc.status = "ASSIGNED"

    action_rec = log_analyst_action_entry(
        db=db,
        user=user,
        action_type="ASSIGN_INCIDENT",
        description=f"Assigned incident {inc.incident_id} to {target_user.username}",
        incident_id=inc.incident_id,
        result="SUCCESS",
    )
    log_assistant_audit(
        db=db,
        user=user,
        action="ASSIGN_INCIDENT",
        resource_type="Incident",
        resource_id=inc.incident_id,
        description=f"Incident {inc.incident_id} reassigned from {old_owner} to {target_user.username}",
    )

    db.commit()

    return {
        "success": True,
        "reply": f"Assigned incident `{inc.incident_id}` to `{target_user.username}` (was `{old_owner}`). Action ID: `{action_rec.action_id}`.",
        "card": AssistantCard(
            card_type="action_success",
            data={
                "action_id": action_rec.action_id,
                "incident_id": inc.incident_id,
                "assigned_to": target_user.username,
                "status": inc.status,
            },
        ),
    }


# ============================================================================
# 7. CHANGE SEVERITY (WRITE TOOL)
# ============================================================================

def tool_change_severity(db: Session, incident_id: str, new_severity: str, user: User) -> dict[str, Any]:
    """Change severity rating of an incident."""
    valid_severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    upper_sev = new_severity.upper() if new_severity else ""
    if upper_sev not in valid_severities:
        return {
            "success": False,
            "reply": f"Invalid severity '{new_severity}'. Allowed values: LOW, MEDIUM, HIGH, CRITICAL.",
            "card": AssistantCard(card_type="error_card", data={"error": "Invalid severity"}),
        }

    inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == incident_id.upper()))
    if not inc:
        return {
            "success": False,
            "reply": f"Incident '{incident_id}' not found.",
            "card": AssistantCard(card_type="error_card", data={"error": f"Incident '{incident_id}' not found."}),
        }

    old_sev = inc.severity
    inc.severity = upper_sev

    action_rec = log_analyst_action_entry(
        db=db,
        user=user,
        action_type="CHANGE_SEVERITY",
        description=f"Changed severity of {inc.incident_id} from {old_sev} to {upper_sev}",
        incident_id=inc.incident_id,
        result="SUCCESS",
    )
    log_assistant_audit(
        db=db,
        user=user,
        action="CHANGE_SEVERITY",
        resource_type="Incident",
        resource_id=inc.incident_id,
        description=f"Changed severity from {old_sev} to {upper_sev}",
    )

    db.commit()

    return {
        "success": True,
        "reply": f"Updated severity of incident `{inc.incident_id}` from `{old_sev}` to `{upper_sev}`. Action ID: `{action_rec.action_id}`.",
        "card": AssistantCard(
            card_type="action_success",
            data={
                "action_id": action_rec.action_id,
                "incident_id": inc.incident_id,
                "previous_severity": old_sev,
                "new_severity": upper_sev,
            },
        ),
    }


# ============================================================================
# 8. RESOLVE INCIDENT (WRITE TOOL)
# ============================================================================

def tool_resolve_incident(db: Session, incident_id: str, summary: str | None, user: User) -> dict[str, Any]:
    """Resolve an incident and record resolution summary."""
    inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == incident_id.upper()))
    if not inc:
        return {
            "success": False,
            "reply": f"Incident '{incident_id}' not found.",
            "card": AssistantCard(card_type="error_card", data={"error": f"Incident '{incident_id}' not found."}),
        }

    # SOC Protocol check: Investigation status
    inv = inc.investigation
    conclusion_text = summary or (inv.conclusion if inv and inv.conclusion else "Resolved by SOC Analyst")

    inc.status = "RESOLVED"
    inc.resolved_at = datetime.utcnow()
    inc.resolution_summary = conclusion_text

    if inv and inv.status != "COMPLETED":
        inv.status = "COMPLETED"
        inv.completed_at = datetime.utcnow()
        if not inv.conclusion:
            inv.conclusion = conclusion_text

    action_rec = log_analyst_action_entry(
        db=db,
        user=user,
        action_type="RESOLVE_INCIDENT",
        description=f"Resolved incident {inc.incident_id}. Summary: {conclusion_text[:60]}",
        incident_id=inc.incident_id,
        result="SUCCESS",
    )
    log_assistant_audit(
        db=db,
        user=user,
        action="RESOLVE_INCIDENT",
        resource_type="Incident",
        resource_id=inc.incident_id,
        description=f"Incident {inc.incident_id} marked as RESOLVED",
    )

    db.commit()

    return {
        "success": True,
        "reply": f"Incident `{inc.incident_id}` has been marked as `RESOLVED`. Summary: \"{conclusion_text}\". Action ID: `{action_rec.action_id}`.",
        "card": AssistantCard(
            card_type="action_success",
            data={
                "action_id": action_rec.action_id,
                "incident_id": inc.incident_id,
                "status": "RESOLVED",
                "resolution_summary": conclusion_text,
            },
        ),
    }


# ============================================================================
# 9. CLOSE INCIDENT (WRITE TOOL)
# ============================================================================

def tool_close_incident(db: Session, incident_id: str, user: User) -> dict[str, Any]:
    """Formally close an incident."""
    inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == incident_id.upper()))
    if not inc:
        return {
            "success": False,
            "reply": f"Incident '{incident_id}' not found.",
            "card": AssistantCard(card_type="error_card", data={"error": f"Incident '{incident_id}' not found."}),
        }

    inc.status = "CLOSED"
    inc.closed_at = datetime.utcnow()

    action_rec = log_analyst_action_entry(
        db=db,
        user=user,
        action_type="CLOSE_INCIDENT",
        description=f"Closed incident {inc.incident_id}",
        incident_id=inc.incident_id,
        result="SUCCESS",
    )
    log_assistant_audit(
        db=db,
        user=user,
        action="CLOSE_INCIDENT",
        resource_type="Incident",
        resource_id=inc.incident_id,
        description=f"Incident {inc.incident_id} closed",
    )

    db.commit()

    return {
        "success": True,
        "reply": f"Incident `{inc.incident_id}` has been officially closed. Action ID: `{action_rec.action_id}`.",
        "card": AssistantCard(
            card_type="action_success",
            data={
                "action_id": action_rec.action_id,
                "incident_id": inc.incident_id,
                "status": "CLOSED",
            },
        ),
    }


# ============================================================================
# 10. ESCALATE INCIDENT (WRITE TOOL)
# ============================================================================

def tool_escalate_incident(db: Session, incident_id: str, user: User) -> dict[str, Any]:
    """Escalate incident level and increase priority."""
    inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == incident_id.upper()))
    if not inc:
        return {
            "success": False,
            "reply": f"Incident '{incident_id}' not found.",
            "card": AssistantCard(card_type="error_card", data={"error": f"Incident '{incident_id}' not found."}),
        }

    inc.escalation_level += 1
    inc.escalation_count += 1
    old_sev = inc.severity
    if inc.severity in ["LOW", "MEDIUM"]:
        inc.severity = "HIGH"
    elif inc.severity == "HIGH":
        inc.severity = "CRITICAL"

    inc.priority = "P1"

    action_rec = log_analyst_action_entry(
        db=db,
        user=user,
        action_type="ESCALATE_INCIDENT",
        description=f"Escalated incident {inc.incident_id} to Level {inc.escalation_level}",
        incident_id=inc.incident_id,
        result="SUCCESS",
    )
    log_assistant_audit(
        db=db,
        user=user,
        action="ESCALATE_INCIDENT",
        resource_type="Incident",
        resource_id=inc.incident_id,
        description=f"Incident escalated to Level {inc.escalation_level}",
    )

    db.commit()

    return {
        "success": True,
        "reply": f"Escalated incident `{inc.incident_id}` to **Level {inc.escalation_level}** (Severity: `{inc.severity}`, Priority: `{inc.priority}`). Action ID: `{action_rec.action_id}`.",
        "card": AssistantCard(
            card_type="action_success",
            data={
                "action_id": action_rec.action_id,
                "incident_id": inc.incident_id,
                "escalation_level": inc.escalation_level,
                "severity": inc.severity,
                "priority": inc.priority,
            },
        ),
    }


# ============================================================================
# 11. LIST ALERTS (READ TOOL)
# ============================================================================

def tool_list_alerts(db: Session, status_filter: str | None = "OPEN", limit: int = 5) -> dict[str, Any]:
    """Fetch active alerts from the database with live threat metadata."""
    query = select(Alert).order_by(Alert.detected_at.desc())
    if status_filter and status_filter.upper() != "ALL":
        query = query.where(func.upper(Alert.status) == status_filter.upper())
    alerts = db.scalars(query.limit(limit)).all()

    if not alerts:
        filter_msg = f"with status '{status_filter}'" if status_filter else ""
        return {
            "success": True,
            "reply": f"No alerts found {filter_msg}. All systems are currently quiet.",
            "card": AssistantCard(card_type="info_card", data={"title": "Alert Center", "message": "No active alerts matching criteria."}),
        }

    items = []
    lines = [f"**Active Alerts ({len(alerts)} shown)**:"]
    for a in alerts:
        lines.append(
            f"- **`{a.alert_id}`** | `{a.predicted_class}` ({a.confidence:.1%}) | Severity: `{a.severity}` | Status: `{a.status}`"
        )
        if a.source_ip and a.destination_ip:
            lines.append(f"  Traffic: `{a.source_ip}` → `{a.destination_ip}` ({a.protocol or 'TCP'})")

        items.append({
            "id": a.alert_id,
            "title": f"{a.predicted_class} ({a.confidence:.1%})",
            "severity": a.severity,
            "status": a.status,
            "meta": f"{a.source_ip or 'N/A'} → {a.destination_ip or 'N/A'}",
            "type": "alert",
        })

    return {
        "success": True,
        "reply": "\n".join(lines),
        "card": AssistantCard(card_type="list_card", data={"title": "Alert Center Detections", "items": items}),
        "data": {"alerts": items},
    }


# ============================================================================
# 12. LIST INCIDENTS (READ TOOL)
# ============================================================================

def tool_list_incidents(db: Session, status_filter: str | None = None, limit: int = 5) -> dict[str, Any]:
    """Fetch recent incidents from the database with live statuses."""
    query = select(Incident).order_by(Incident.created_at.desc())
    if status_filter and status_filter.upper() != "ALL":
        query = query.where(func.upper(Incident.status) == status_filter.upper())
    incidents = db.scalars(query.limit(limit)).all()

    if not incidents:
        return {
            "success": True,
            "reply": "No incidents found in the system.",
            "card": AssistantCard(card_type="info_card", data={"title": "Incident Management", "message": "No incidents found."}),
        }

    items = []
    lines = [f"**Incidents ({len(incidents)} shown)**:"]
    for inc in incidents:
        owner = inc.assigned_to.username if inc.assigned_to else "Unassigned"
        lines.append(
            f"- **`{inc.incident_id}`**: {inc.title}\n"
            f"  Status: `{inc.status}` | Severity: `{inc.severity}` | Owner: `{owner}` | Linked Alert: `{inc.alert_id}`"
        )
        items.append({
            "id": inc.incident_id,
            "title": inc.title,
            "severity": inc.severity,
            "status": inc.status,
            "meta": f"Owner: {owner} | Alert: {inc.alert_id}",
            "type": "incident",
        })

    return {
        "success": True,
        "reply": "\n".join(lines),
        "card": AssistantCard(card_type="list_card", data={"title": "Incident Management Cases", "items": items}),
        "data": {"incidents": items},
    }


# ============================================================================
# 13. LIST INVESTIGATIONS (READ TOOL)
# ============================================================================

def tool_list_investigations(db: Session, limit: int = 5) -> dict[str, Any]:
    """Fetch active investigations and forensic dossiers."""
    invs = db.scalars(select(Investigation).order_by(Investigation.updated_at.desc()).limit(limit)).all()
    if not invs:
        return {
            "success": True,
            "reply": "No active investigations found. To start one, type `investigate incident <ID>`.",
            "card": AssistantCard(card_type="info_card", data={"title": "Investigation Department", "message": "No active investigations."}),
        }

    items = []
    lines = [f"**Investigations ({len(invs)} shown)**:"]
    for inv in invs:
        lines.append(
            f"- **`{inv.investigation_id}`** (Incident: `{inv.incident_id}`)\n"
            f"  Status: `{inv.status}`"
        )
        if inv.conclusion:
            lines.append(f"  Conclusion: {inv.conclusion[:90]}...")
        elif inv.analyst_notes:
            first_note = inv.analyst_notes.splitlines()[-1] if inv.analyst_notes else ""
            lines.append(f"  Latest Note: {first_note[:90]}...")

        items.append({
            "id": inv.investigation_id,
            "title": f"Incident {inv.incident_id}",
            "severity": "MEDIUM",
            "status": inv.status,
            "meta": inv.conclusion or inv.analyst_notes or "In progress",
            "type": "investigation",
        })

    return {
        "success": True,
        "reply": "\n".join(lines),
        "card": AssistantCard(card_type="list_card", data={"title": "Investigation Department Dossiers", "items": items}),
        "data": {"investigations": items},
    }


# ============================================================================
# 14. NETWORK SUMMARY (READ TOOL)
# ============================================================================

def tool_network_summary(db: Session) -> dict[str, Any]:
    """Fetch live traffic statistics and network sensor status."""
    from backend.app.models.network_event import NetworkEvent

    total_events = db.scalar(select(func.count(NetworkEvent.id))) or 0
    recent_events = db.scalars(
        select(NetworkEvent).order_by(NetworkEvent.event_time.desc()).limit(5)
    ).all()

    top_protocols = db.execute(
        select(NetworkEvent.protocol, func.count(NetworkEvent.id).label("cnt"))
        .group_by(NetworkEvent.protocol)
        .order_by(func.count(NetworkEvent.id).desc())
        .limit(3)
    ).all()

    proto_str = ", ".join([f"{p[0] or 'TCP'} ({p[1]})" for p in top_protocols]) if top_protocols else "TCP, UDP, ICMP"

    lines = [
        "**Network Monitor Live Status**:",
        f"- **Total Captured Network Events**: {total_events}",
        f"- **Primary Protocols**: {proto_str}",
        f"- **Sensor Feed**: Packet capture and ML detection pipelines are active.",
    ]

    if recent_events:
        lines.append("\n**Recent Network Flows**:")
        for ev in recent_events[:3]:
            lines.append(f"- `{ev.source_ip}:{ev.source_port}` → `{ev.destination_ip}:{ev.destination_port}` ({ev.protocol or 'TCP'})")

    return {
        "success": True,
        "reply": "\n".join(lines),
        "card": AssistantCard(
            card_type="info_card",
            data={
                "title": "Network Monitor Live Telemetry",
                "total_events": total_events,
                "protocols": proto_str,
            },
        ),
    }


# ============================================================================
# 15. SOC RECOMMENDATIONS & PRIORITIES
# ============================================================================

def tool_soc_recommendation(db: Session, user: User) -> dict[str, Any]:
    """Analyze database state and provide intelligent next actions for the analyst."""
    open_alerts = db.scalars(
        select(Alert).where(Alert.status == "OPEN").order_by(Alert.detected_at.desc()).limit(3)
    ).all()

    investigating_incs = db.scalars(
        select(Incident).where(Incident.status.in_(["INVESTIGATING", "ACKNOWLEDGED"])).limit(3)
    ).all()

    recommendations = []
    if open_alerts:
        first_a = open_alerts[0]
        recommendations.append(
            f"1. **Acknowledge Alert `{first_a.alert_id}`**: High threat `{first_a.predicted_class}` ({first_a.confidence:.1%}) is currently OPEN. Command: `acknowledge alert {first_a.alert_id}`."
        )

    if investigating_incs:
        first_i = investigating_incs[0]
        if first_i.status == "ACKNOWLEDGED":
            recommendations.append(
                f"2. **Start Investigation for `{first_i.incident_id}`**: Incident is acknowledged and ready for forensic analysis. Command: `investigate incident {first_i.incident_id}`."
            )
        else:
            recommendations.append(
                f"2. **Add Notes or Resolve `{first_i.incident_id}`**: Investigation is currently in progress. Command: `add analyst note to {first_i.incident_id}: <notes>`."
            )

    if not recommendations:
        recommendations.append("All current alerts are acknowledged and incident backlogs are clear. You can review the **Network Monitor** or generate an **Executive Report**.")

    reply = "**Recommended Operational Next Steps**:\n" + "\n\n".join(recommendations)
    return {
        "success": True,
        "reply": reply,
        "card": AssistantCard(
            card_type="info_card",
            data={"title": "Operational Recommendations", "recommendations": recommendations},
        ),
    }


# ============================================================================
# 16. EXPLAIN WEBSITE OPERATIONS & SOC WORKFLOWS
# ============================================================================

def tool_explain_workflow(topic: str) -> dict[str, Any]:
    """Provide detailed, professional guidance on all sections of the Zuka SOC platform."""
    lower_topic = topic.lower()

    if "alert" in lower_topic:
        explanation = (
            "🚨 **Alert Center Operations**:\n\n"
            "• **Detection**: Ingests real-time traffic and analyzes packets using trained ML detection models (DoS, PortScan, BruteForce, Infiltration, Botnet, WebAttacks).\n"
            "• **Confidence & XAI**: Every alert displays model confidence (e.g. 98.4%) and Explainable AI feature importances.\n"
            "• **SOC Rule**: New alerts arrive as `OPEN`. Analysts must review the source/destination IPs and click **Acknowledge** (or ask Zuka: `acknowledge alert <ID>`).\n"
            "• **Incident Link**: Acknowledging an alert automatically unlocks the linked incident for investigation."
        )
    elif "investigat" in lower_topic:
        explanation = (
            "🔍 **Investigation Department Operations**:\n\n"
            "• **Prerequisite**: An incident's linked alert must be `ACKNOWLEDGED` before investigation can start.\n"
            "• **Workflow**: Starting an investigation creates a forensic dossier (`INV-...`), starts the analysis timer, and assigns the active analyst.\n"
            "• **Analyst Notes**: Log findings and packet analysis (e.g. `add analyst note to <ID>: Verified brute force payload`). Every note is stamped and logged in the Analyst Action ledger.\n"
            "• **Conclusion**: When done, write an analyst conclusion and mark investigation as `COMPLETED`. This unlocks incident resolution."
        )
    elif "resolve" in lower_topic or "close" in lower_topic:
        explanation = (
            "🛡️ **Incident Resolution & Closure Lifecycle**:\n\n"
            "1. **Investigation Requirement**: According to SOC standards, you cannot resolve an incident until the forensic investigation is completed with analyst conclusion.\n"
            "2. **Resolving Incident**: In Incident Management, click **Resolve** (or ask Zuka: `resolve incident <ID>`). Provide a resolution summary.\n"
            "3. **Closing Incident**: After resolution, review the final post-mortem and click **Close Incident** (or ask Zuka: `close incident <ID>`). The closed timestamp is recorded in the audit trail."
        )
    elif "network" in lower_topic:
        explanation = (
            "🌐 **Network Monitor Operations**:\n\n"
            "• Inspects bidirectional network flows, packet sizes, source/destination ports, and protocols (TCP, UDP, ICMP).\n"
            "• Detects abnormal traffic spikes, port scans, and SYN flood attempts in real-time.\n"
            "• Allows analysts to trace attacker IPs across past sessions."
        )
    elif "database" in lower_topic:
        explanation = (
            "💾 **Database Center Operations**:\n\n"
            "• Displays live database status, table record counts, and schema definitions.\n"
            "• **Analyst Action Ledger**: Stores every human-authorized operational activity with timestamp, analyst ID, and result.\n"
            "• **Audit History**: Permanent audit logs of user logins, role modifications, and system transitions."
        )
    elif "report" in lower_topic:
        explanation = (
            "📄 **Reports & PDF Export Operations**:\n\n"
            "• Generate executive summaries, incident post-mortems, or alert dossiers.\n"
            "• Select specific incident or alert IDs to create targeted, beautifully styled PDF reports for management and compliance.\n"
            "• Multi-page reports include forensic timelines, network charts, and analyst sign-offs."
        )
    elif "user" in lower_topic or "role" in lower_topic:
        explanation = (
            "👥 **User Management Operations**:\n\n"
            "• Supports role-based access control: `ADMIN`, `SOC_ANALYST`, and `VIEWER`.\n"
            "• When a new analyst signs up, admin approval is required before operational privileges are activated.\n"
            "• Password security requires uppercase, numbers, and symbols for robust access governance."
        )
    else:
        explanation = (
            "🛡️ **ZUKA SOC Platform Architecture & Full Lifecycle**:\n\n"
            "1. **Network Monitor** captures packet streams →\n"
            "2. **AI Detection Engine** flags suspicious activity →\n"
            "3. **Alert Center** generates an alert with XAI explanation →\n"
            "4. Analyst **Acknowledges Alert** →\n"
            "5. Incident unlocks for **Investigation** →\n"
            "6. Analyst logs **Forensic Notes & Conclusion** →\n"
            "7. Incident is **Resolved** & **Closed** →\n"
            "8. Formal **Report** is generated for compliance and archive."
        )

    return {
        "success": True,
        "reply": explanation,
        "card": AssistantCard(card_type="info_card", data={"title": "SOC Workflow & Operation Guide", "topic": topic}),
    }


# ============================================================================
# 17. COUNT ENTITIES (REAL DATABASE METRICS)
# ============================================================================

DEFENSE_ACTION_TYPES = (
    "VLAN_QUARANTINE",
    "BLOCK_IP",
    "CREDENTIAL_ROTATION",
    "RATE_LIMIT",
    "FIRMWARE_PATCH",
    "CUSTOM",
)


def tool_count_defense_action_types() -> dict[str, Any]:
    """List documented defense action types without implying they are deployed."""
    labels = {
        "VLAN_QUARANTINE": "VLAN Quarantine",
        "BLOCK_IP": "Block IP",
        "CREDENTIAL_ROTATION": "Credential Rotation",
        "RATE_LIMIT": "Rate Limit",
        "FIRMWARE_PATCH": "Firmware Patch",
        "CUSTOM": "Custom Response",
    }
    names = ", ".join(f"**{labels.get(name, name.replace('_', ' ').title())}**" for name in DEFENSE_ACTION_TYPES)
    count = len(DEFENSE_ACTION_TYPES)
    return {
        "success": True,
        "reply": (
            f"The Defense Department offers **{count} documented response types**: {names}. "
            "These are available response options, not a live count of actions already applied."
        ),
        "card": AssistantCard(
            card_type="info_card",
            data={"count": count, "entity": "defense_action_types", "items": list(DEFENSE_ACTION_TYPES)},
        ),
        "data": {"count": count, "entity": "defense_action_types", "items": list(DEFENSE_ACTION_TYPES)},
    }


def tool_count_entities(
    db: Session,
    entity_type: str,
    severity: str | None = None,
    status: str | None = None,
    timeframe: str | None = None,
) -> dict[str, Any]:
    """Execute real SQL count query for alerts, incidents, or investigations."""
    if entity_type == "alert":
        query = select(func.count(Alert.id))
        filters = []
        if severity:
            query = query.where(func.upper(Alert.severity) == severity.upper())
            filters.append(f"severity: `{severity.upper()}`")
        if status:
            query = query.where(func.upper(Alert.status) == status.upper())
            filters.append(f"status: `{status.upper()}`")
        if timeframe == "today":
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where(Alert.detected_at >= today_start)
            filters.append("detected today")

        count = db.scalar(query) or 0

        # Also get quick breakdown if generic count
        if not severity and not status and not timeframe:
            status_rows = db.execute(
                select(func.upper(Alert.status), func.count(Alert.id)).group_by(func.upper(Alert.status))
            ).all()
            status_counts = {(alert_status or "UNKNOWN"): status_count for alert_status, status_count in status_rows}
            count = sum(status_counts.values())
            breakdown = ", ".join(
                f"{status_counts[alert_status]} {alert_status}"
                for alert_status in sorted(status_counts)
            )
            reply = f"There are **{count}** total alerts in the database ({breakdown})."
        else:
            filter_str = f" ({', '.join(filters)})" if filters else ""
            reply = f"There are **{count}** alerts matching your criteria{filter_str}."

        return {
            "success": True,
            "reply": reply,
            "card": AssistantCard(card_type="info_card", data={"count": count, "entity": "alert", "filters": filters}),
            "data": {"count": count, "entity": "alert"},
        }

    elif entity_type == "incident":
        query = select(func.count(Incident.id))
        filters = []
        if severity:
            query = query.where(func.upper(Incident.severity) == severity.upper())
            filters.append(f"severity: `{severity.upper()}`")
        if status:
            query = query.where(func.upper(Incident.status) == status.upper())
            filters.append(f"status: `{status.upper()}`")
        if timeframe == "today":
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where(Incident.created_at >= today_start)
            filters.append("created today")

        count = db.scalar(query) or 0

        if not severity and not status and not timeframe:
            status_rows = db.execute(
                select(func.upper(Incident.status), func.count(Incident.id)).group_by(func.upper(Incident.status))
            ).all()
            status_counts = {(status or "UNKNOWN"): status_count for status, status_count in status_rows}
            count = sum(status_counts.values())
            breakdown = ", ".join(
                f"{status_counts[incident_status]} {incident_status}"
                for incident_status in sorted(status_counts)
            )
            reply = f"There are **{count}** total incidents ({breakdown})."
        else:
            filter_str = f" ({', '.join(filters)})" if filters else ""
            reply = f"There are **{count}** incidents matching your criteria{filter_str}."

        return {
            "success": True,
            "reply": reply,
            "card": AssistantCard(card_type="info_card", data={"count": count, "entity": "incident", "filters": filters}),
            "data": {"count": count, "entity": "incident"},
        }

    elif entity_type in ["investigation", "investigations"]:
        query = select(func.count(Investigation.id))
        if status:
            query = query.where(func.upper(Investigation.status) == status.upper())
        count = db.scalar(query) or 0
        in_prog = db.scalar(select(func.count(Investigation.id)).where(Investigation.status == "IN_PROGRESS")) or 0
        reply = f"There are **{count}** investigations on record ({in_prog} active IN_PROGRESS)."
        return {
            "success": True,
            "reply": reply,
            "card": AssistantCard(card_type="info_card", data={"count": count, "entity": "investigation"}),
            "data": {"count": count, "entity": "investigation"},
        }

    elif entity_type in ["user", "users"]:
        query = select(func.count(User.id))
        count = db.scalar(query) or 0
        active_count = db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
        reply = f"There are **{count}** users registered in the system ({active_count} active)."
        return {
            "success": True,
            "reply": reply,
            "card": AssistantCard(card_type="info_card", data={"count": count, "entity": "user", "active": active_count}),
            "data": {"count": count, "active": active_count, "entity": "user"},
        }

    elif entity_type in ["report", "reports"]:
        from backend.app.models.report import Report

        count = db.scalar(select(func.count(Report.id))) or 0
        ready_count = db.scalar(
            select(func.count(Report.id)).where(func.upper(Report.status) == "READY")
        ) or 0
        reply = f"There are **{count}** reports in the database ({ready_count} READY)."
        return {
            "success": True,
            "reply": reply,
            "card": AssistantCard(card_type="info_card", data={"count": count, "ready": ready_count, "entity": "reports"}),
            "data": {"count": count, "ready": ready_count, "entity": "reports"},
        }

    elif entity_type in ["network", "networks", "network_event", "network_events"]:
        from backend.app.models.network_event import NetworkEvent
        query = select(func.count(NetworkEvent.id))
        count = db.scalar(query) or 0
        unique_ips = db.scalar(select(func.count(func.distinct(NetworkEvent.source_ip)))) or 0
        reply = f"There are **{count}** network traffic events recorded across **{unique_ips}** distinct source IP addresses."
        return {
            "success": True,
            "reply": reply,
            "card": AssistantCard(card_type="info_card", data={"count": count, "unique_ips": unique_ips, "entity": "network_events"}),
            "data": {"count": count, "unique_ips": unique_ips, "entity": "network_events"},
        }

    return {
        "success": False,
        "reply": f"Unknown entity type '{entity_type}' for count query. Available entities: alerts, incidents, investigations, users, reports, network_events.",
        "card": None,
    }


def tool_count_entity_summary(db: Session, entities: list[str]) -> dict[str, Any]:
    """Count several live SOC record types in one grounded database response."""
    from backend.app.models.report import Report
    from backend.app.models.network_event import NetworkEvent

    entity_models = {
        "alert": (Alert, "Alerts"),
        "incident": (Incident, "Incidents"),
        "investigation": (Investigation, "Investigations"),
        "report": (Report, "Reports"),
        "user": (User, "Users"),
        "network_events": (NetworkEvent, "Network events"),
    }
    counts: dict[str, int] = {}
    labels: list[tuple[str, int]] = []
    for entity in entities:
        entry = entity_models.get(entity)
        if entry is None:
            continue
        model, label = entry
        count = db.scalar(select(func.count(model.id))) or 0
        key = "network_events" if entity == "network_events" else f"{entity}s"
        if entity in {"incident", "user"}:
            key = "incidents" if entity == "incident" else "users"
        if entity == "investigation":
            key = "investigations"
        counts[key] = count
        labels.append((label, count))

    if not labels:
        return {"success": False, "reply": "Tell me which record types you want counted.", "card": None}
    reply = "**Current database counts**\n" + "\n".join(
        f"- **{label}:** {count:,}" for label, count in labels
    )
    return {
        "success": True,
        "reply": reply,
        "card": AssistantCard(card_type="info_card", data={"title": "SOC Record Counts", **counts}),
        "data": counts,
    }


def tool_get_network_event(db: Session, event_id: str) -> dict[str, Any]:
    """Fetch one recorded network flow by its database ID."""
    from backend.app.models.network_event import NetworkEvent

    try:
        numeric_id = int(str(event_id).strip())
        if numeric_id < 1 or numeric_id > 9_223_372_036_854_775_807:
            raise ValueError("Event ID out of 64-bit integer range")
    except (ValueError, TypeError, OverflowError):
        return {
            "success": False,
            "reply": f"Flow event #{event_id} was not found in the network events database.",
            "card": AssistantCard(card_type="error_card", data={"error": "Network event not found", "event_id": str(event_id)}),
        }

    event = db.get(NetworkEvent, numeric_id)
    if not event:
        return {
            "success": False,
            "reply": f"Flow event #{event_id} was not found in the network events database.",
            "card": AssistantCard(card_type="error_card", data={"error": "Network event not found", "event_id": str(event_id)}),
        }

    details = {
        "event_id": event.id,
        "event_time": event.event_time.isoformat() if event.event_time else None,
        "source_ip": event.source_ip,
        "source_port": event.source_port,
        "destination_ip": event.destination_ip,
        "destination_port": event.destination_port,
        "protocol": event.protocol,
        "event_type": event.event_type,
        "packets": event.packets,
        "bytes": event.bytes_count,
        "description": event.description,
        "direction": event.direction,
        "flow_duration_ms": event.flow_duration_ms,
        "interface_name": event.interface_name,
        "capture_source": event.capture_source,
    }
    timestamp = event.event_time.strftime("%Y-%m-%d %H:%M:%S UTC") if event.event_time else "time unavailable"
    observed = []
    if event.source_ip:
        observed.append(f"source {event.source_ip}" + (f":{event.source_port}" if event.source_port else ""))
    if event.destination_ip:
        observed.append(f"destination {event.destination_ip}" + (f":{event.destination_port}" if event.destination_port else ""))
    if event.protocol:
        observed.append(f"protocol {event.protocol}")
    lines = [f"**Flow Event #{event.id}**", f"- **Time:** {timestamp}"]
    lines.append(f"- **Connection:** {'; '.join(observed) if observed else 'endpoint and protocol details are not recorded'}")
    if event.event_type:
        lines.append(f"- **Event type:** {event.event_type}")
    if event.packets is not None:
        lines.append(f"- **Packets:** {event.packets:,}")
    if event.bytes_count is not None:
        lines.append(f"- **Bytes:** {event.bytes_count:,}")
    if event.flow_duration_ms is not None:
        lines.append(f"- **Duration:** {event.flow_duration_ms:,} ms")
    if event.direction:
        lines.append(f"- **Direction:** {event.direction}")
    if event.description:
        lines.append(f"- **Recorded description:** {event.description}")
    reply = "\n".join(lines)
    return {
        "success": True,
        "reply": reply,
        "card": AssistantCard(card_type="info_card", data=details),
        "data": details,
    }


# ============================================================================
# 17B. GET ALERT DETAILS (READ TOOL)
# ============================================================================

def tool_get_alert_details(db: Session, alert_id: str) -> dict[str, Any]:
    """Retrieve full factual details for a specific alert."""
    alt = db.scalar(select(Alert).where(func.upper(Alert.alert_id) == alert_id.upper()))
    if not alt:
        return {
            "success": False,
            "reply": f"Alert '{alert_id}' was not found in the database. Please verify the alert ID.",
            "card": AssistantCard(card_type="error_card", data={"error": f"Alert '{alert_id}' not found."}),
            "data": None,
        }
    linked_inc_id = alt.incidents[0].incident_id if alt.incidents else None
    data = {
        "alert_id": alt.alert_id,
        "predicted_class": alt.predicted_class,
        "confidence": f"{alt.confidence:.1%}",
        "severity": alt.severity,
        "status": alt.status,
        "source_ip": alt.source_ip,
        "source_port": alt.source_port,
        "destination_ip": alt.destination_ip,
        "destination_port": alt.destination_port,
        "protocol": alt.protocol,
        "detected_at": alt.detected_at.strftime("%Y-%m-%d %H:%M:%S UTC") if alt.detected_at else "Unknown",
        "incident_id": linked_inc_id,
    }
    observed = []
    if alt.source_ip:
        observed.append(f"source {alt.source_ip}" + (f":{alt.source_port}" if alt.source_port else ""))
    if alt.destination_ip:
        observed.append(f"destination {alt.destination_ip}" + (f":{alt.destination_port}" if alt.destination_port else ""))
    if alt.protocol:
        observed.append(f"protocol {alt.protocol}")
    network_summary = "; ".join(observed) if observed else "traffic details are not recorded"
    reply = (
        f"**Alert Details for `{alt.alert_id}`**:\n"
        f"- **Threat type:** `{alt.predicted_class}` (confidence **{alt.confidence:.1%}**)\n"
        f"- **Severity:** `{alt.severity}` · **Status:** `{alt.status}`\n"
        f"- **Network:** {network_summary}\n"
        f"- **Correlated incident:** `{linked_inc_id or 'None'}`"
    )
    return {
        "success": True,
        "reply": reply,
        "card": AssistantCard(card_type="alert_card", data=data),
        "data": data,
    }


# ============================================================================
# 18. TOP ATTACKERS & HOSTS WITH MOST ALERTS
# ============================================================================

def tool_top_attackers(db: Session, limit: int = 3) -> dict[str, Any]:
    """Query database for hosts/source IPs generating the highest number of alerts."""
    rows = db.execute(
        select(Alert.source_ip, func.count(Alert.id).label("cnt"))
        .where(Alert.source_ip.isnot(None))
        .group_by(Alert.source_ip)
        .order_by(func.count(Alert.id).desc())
        .limit(limit)
    ).all()

    if not rows:
        return {
            "success": True,
            "reply": "No external IP telemetry found in current alerts.",
            "card": AssistantCard(card_type="info_card", data={"title": "Top Attacking Hosts", "message": "No data."}),
        }

    lines = ["**Hosts / Source IPs with the most alerts**:"]
    items = []
    for rank, (ip, count) in enumerate(rows, start=1):
        # Find top attack class for this IP
        top_cls_row = db.execute(
            select(Alert.predicted_class, func.count(Alert.id))
            .where(Alert.source_ip == ip)
            .group_by(Alert.predicted_class)
            .order_by(func.count(Alert.id).desc())
            .limit(1)
        ).first()
        top_cls = top_cls_row[0] if top_cls_row else "Unknown Threat"

        lines.append(f"{rank}. `{ip}` — **{count} alerts** (Primary threat: `{top_cls}`)")
        items.append({"rank": rank, "ip": ip, "count": count, "class": top_cls})

    return {
        "success": True,
        "reply": "\n".join(lines),
        "card": AssistantCard(card_type="info_card", data={"title": "Top Alert Sources", "hosts": items}),
        "data": {"top_hosts": items},
    }


# ============================================================================
# 19. PROJECT KNOWLEDGE BASE LOOKUP
# ============================================================================

def tool_answer_from_knowledge_base(question: str) -> dict[str, Any]:
    """
    Answer operational, website, and project questions strictly based on the ChromaDB RAG vector store.
    Adheres strictly to the Zero Hallucination policy:
    If the context does not contain the answer, replies exactly:
    "I don't have that information. Please contact <chitlakarthik66@gmail.com>."
    """
    from backend.app.zuka_assistant.rag_engine import query_rag

    try:
        rag_res = query_rag(question)
        answer = rag_res.get("formatted_answer") or rag_res.get("answer") or "I don't have that information. Please contact <chitlakarthik66@gmail.com>."
        sources = rag_res.get("sources", [])
        is_fallback = rag_res.get("is_fallback", False)

        card = None
        if sources and not is_fallback:
            card = AssistantCard(
                card_type="info_card",
                data={
                    "title": "ZUKA Knowledge Base",
                    "sources": sources,
                    "model": "qwen2.5:3b (RAG)",
                }
            )

        return {
            "success": True,
            "reply": answer,
            "sources": sources,
            "is_fallback": is_fallback,
            "card": card,
        }
    except Exception as e:
        logger.error(f"[ZUKA_TOOLS] RAG error: {e}")
        return {
            "success": False,
            "reply": "I don't have that information. Please contact <chitlakarthik66@gmail.com>.",
            "card": None,
        }


# ============================================================================
# 20. REAL SYSTEM TELEMETRY & HEALTH CHECK
# ============================================================================

def tool_verify_system_health(db: Session) -> dict[str, Any]:
    """Perform real database and sensor verification. Never assumes live connection."""
    from backend.app.models.network_event import NetworkEvent

    try:
        alert_cnt = db.scalar(select(func.count(Alert.id))) or 0
        last_net = db.scalar(select(NetworkEvent).order_by(NetworkEvent.event_time.desc()).limit(1))
        last_seen = last_net.event_time.strftime("%Y-%m-%d %H:%M:%S UTC") if last_net else "No recent packets"
        return {
            "healthy": True,
            "status": "connected",
            "message": f"Database verified connected ({alert_cnt} alerts indexed). Latest network sensor activity: {last_seen}.",
        }
    except Exception as e:
        return {
            "healthy": False,
            "status": "data source unavailable",
            "message": "data source unavailable",
            "error": str(e),
        }


def tool_database_status(db: Session) -> dict[str, Any]:
    """Return a compact live database health and record-count overview."""
    from backend.app.models.report import Report
    from backend.app.models.network_event import NetworkEvent

    try:
        counts = {
            "alerts": db.scalar(select(func.count(Alert.id))) or 0,
            "incidents": db.scalar(select(func.count(Incident.id))) or 0,
            "investigations": db.scalar(select(func.count(Investigation.id))) or 0,
            "reports": db.scalar(select(func.count(Report.id))) or 0,
            "users": db.scalar(select(func.count(User.id))) or 0,
            "network_events": db.scalar(select(func.count(NetworkEvent.id))) or 0,
        }
        total = sum(counts.values())
        lines = [
            "**Database Center status: Connected**",
            f"I can read the live SOC database. It contains **{total:,} records** across these areas:",
            "- Alerts: **{alerts:,}**".format(**counts),
            "- Incidents: **{incidents:,}**".format(**counts),
            "- Investigations: **{investigations:,}**".format(**counts),
            "- Reports: **{reports:,}**".format(**counts),
            "- Users: **{users:,}**".format(**counts),
            "- Network events: **{network_events:,}**".format(**counts),
        ]
        return {
            "success": True,
            "reply": "\n".join(lines),
            "card": AssistantCard(card_type="info_card", data={"title": "Database Center", "status": "Connected", **counts}),
            "data": {"status": "connected", **counts},
        }
    except Exception:
        logger.exception("Unable to read Database Center status")
        return {
            "success": False,
            "reply": "**Database Center status: Unavailable**\nI couldn't verify the database connection just now. Please try again shortly.",
            "card": AssistantCard(card_type="error_card", data={"title": "Database Center", "status": "Unavailable"}),
            "data": {"status": "unavailable"},
        }


def tool_list_reports(db: Session, limit: int = 10) -> dict[str, Any]:
    """Show recent reports without exposing server-side file paths."""
    from backend.app.models.report import Report

    rows = db.scalars(select(Report).order_by(Report.created_at.desc()).limit(limit)).all()
    if not rows:
        return {"success": True, "reply": "There are no reports in the database yet.", "card": AssistantCard(card_type="info_card", data={"title": "Reports", "items": []})}
    items = [
        {
            "report_id": row.report_id,
            "title": row.title,
            "type": row.report_type,
            "status": row.status,
            "entity_id": row.entity_id,
            "created_at": row.created_at.strftime("%Y-%m-%d %H:%M UTC") if row.created_at else "Unknown",
        }
        for row in rows
    ]
    lines = ["**Recent reports** (showing up to 10):"]
    lines.extend(
        f"- **{item['title']}** — `{item['report_id']}` · {item['type']} · {item['status']}"
        + (f" · related to `{item['entity_id']}`" if item["entity_id"] else "")
        for item in items
    )
    return {
        "success": True,
        "reply": "\n".join(lines),
        "card": AssistantCard(card_type="list_card", data={"title": "Recent Reports", "items": items}),
        "data": {"items": items, "count": len(items)},
    }


def tool_summarize_report(db: Session, report_id: str) -> dict[str, Any]:
    """Summarize stored report metadata and summary text by report ID."""
    from backend.app.models.report import Report

    report = db.scalar(select(Report).where(func.upper(Report.report_id) == report_id.upper()))
    if report is None:
        return {"success": False, "reply": f"I couldn't find report `{report_id}`. Check the report ID and try again.", "card": AssistantCard(card_type="error_card", data={"error": "Report not found", "report_id": report_id})}
    summary = (report.summary or "This report has no saved summary.").strip()
    reply = (
        f"**{report.title}** (`{report.report_id}`)\n"
        f"- Type: **{report.report_type}** · Status: **{report.status}** · Format: **{report.format}**\n"
        + (f"- Related record: `{report.entity_id}`\n" if report.entity_id else "")
        + f"\n{summary}"
    )
    item = {
        "report_id": report.report_id,
        "title": report.title,
        "type": report.report_type,
        "status": report.status,
        "entity_id": report.entity_id,
        "summary": summary,
        "created_at": report.created_at.strftime("%Y-%m-%d %H:%M UTC") if report.created_at else None,
    }
    return {"success": True, "reply": reply, "card": AssistantCard(card_type="info_card", data={"title": "Report Summary", **item}), "data": item}


def tool_summarize_investigation(db: Session, investigation_id: str) -> dict[str, Any]:
    """Summarize a stored investigation by its public identifier."""
    inv = db.scalar(select(Investigation).where(func.upper(Investigation.investigation_id) == investigation_id.upper()))
    if inv is None:
        return {"success": False, "reply": f"I couldn't find investigation `{investigation_id}`. Check the investigation ID and try again.", "card": AssistantCard(card_type="error_card", data={"error": "Investigation not found", "investigation_id": investigation_id})}
    incident = inv.incident
    sections = [
        f"**Investigation {inv.investigation_id}**",
        f"- Status: **{inv.status}**",
        f"- Related incident: `{inv.incident_id}`" + (f" — {incident.title}" if incident else ""),
    ]
    for label, value in (("Findings", inv.findings), ("Conclusion", inv.conclusion), ("Impact", inv.impact_assessment), ("Remediation", inv.remediation), ("Analyst notes", inv.analyst_notes)):
        if value:
            sections.append(f"- **{label}:** {value.strip()[:700]}")
    item = {
        "investigation_id": inv.investigation_id,
        "incident_id": inv.incident_id,
        "incident_title": incident.title if incident else None,
        "status": inv.status,
        "findings": inv.findings,
        "conclusion": inv.conclusion,
        "impact_assessment": inv.impact_assessment,
        "remediation": inv.remediation,
        "analyst_notes": inv.analyst_notes,
    }
    return {"success": True, "reply": "\n".join(sections), "card": AssistantCard(card_type="info_card", data={"title": "Investigation Summary", **item}), "data": item}


def tool_list_users(db: Session, user: User, limit: int = 10) -> dict[str, Any]:
    """List account names only for administrators; otherwise return safe counts."""
    total = db.scalar(select(func.count(User.id))) or 0
    active = db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    inactive = total - active
    can_view_names = bool(getattr(getattr(user, "role", None), "name", "").lower() in {"admin", "administrator", "soc_admin"})
    if not can_view_names:
        return {
            "success": True,
            "reply": f"There are **{total}** registered users (**{active} active**, **{inactive} inactive**). Individual account details are available to administrators in User Management.",
            "card": AssistantCard(card_type="info_card", data={"title": "User Accounts", "count": total, "active": active, "inactive": inactive}),
            "data": {"count": total, "active": active, "inactive": inactive},
        }
    rows = db.scalars(select(User).order_by(User.id).limit(limit)).all()
    items = [{"user_id": row.id, "username": row.username, "role": row.role.name if row.role else "Unknown", "status": "Active" if row.is_active else "Inactive"} for row in rows]
    lines = [f"**User accounts** (showing {len(items)} of {total}; {active} active, {inactive} inactive):"]
    lines.extend(f"- **{item['username']}** · {item['role']} · {item['status']}" for item in items)
    return {"success": True, "reply": "\n".join(lines), "card": AssistantCard(card_type="list_card", data={"title": "User Accounts", "items": items, "total": total, "active": active, "inactive": inactive}), "data": {"items": items, "count": total, "active": active, "inactive": inactive}}


