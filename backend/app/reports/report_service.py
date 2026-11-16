from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.models.alert import Alert
from backend.app.models.analyst_action import AnalystAction
from backend.app.models.audit_log import AuditLog
from backend.app.models.incident import Incident
from backend.app.models.investigation import Investigation
from backend.app.models.network_event import NetworkEvent


REPORT_TIME_ZONE = ZoneInfo("Asia/Kolkata")


def _iso(value: Any) -> str | None:
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        # Database timestamps in ZUKA are stored as naive UTC values.
        # Attach UTC before converting so reports never interpret UTC as local time.
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(REPORT_TIME_ZONE).isoformat()

        return value.isoformat()

    return value


def _generated_at() -> str:
    """Return the report generation timestamp in Asia/Kolkata with offset."""
    return datetime.now(timezone.utc).astimezone(REPORT_TIME_ZONE).isoformat()


def _incident_dict(incident: Incident | None) -> dict[str, Any]:
    if incident is None:
        return {}
    return {
        "incident_id": incident.incident_id,
        "alert_id": incident.alert_id,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "priority": incident.priority,
        "status": incident.status,
        "assigned_to_id": incident.assigned_to_id,
        "resolution_summary": incident.resolution_summary,
        "created_at": _iso(incident.created_at),
        "updated_at": _iso(incident.updated_at),
        "resolved_at": _iso(incident.resolved_at),
        "closed_at": _iso(incident.closed_at),
    }


def _alert_dict(alert: Alert | None) -> dict[str, Any]:
    if alert is None:
        return {}
    from backend.app.soc.telemetry_resolver import resolve_network_telemetry
    telemetry = resolve_network_telemetry(
        alert_id=alert.alert_id,
        attack_class=alert.predicted_class,
        source_ip=alert.source_ip,
        destination_ip=alert.destination_ip,
        source_port=alert.source_port,
        destination_port=alert.destination_port,
        protocol=alert.protocol,
        dataset_name=alert.dataset_name,
        capture_source=alert.capture_source,
    )
    return {
        "alert_id": alert.alert_id,
        "detected_at": _iso(alert.detected_at),
        "predicted_class": alert.predicted_class,
        "confidence": alert.confidence,
        "severity": alert.severity,
        "status": alert.status,
        "source_ip": telemetry["source_ip"],
        "destination_ip": telemetry["destination_ip"],
        "source_port": telemetry["source_port"],
        "destination_port": telemetry["destination_port"],
        "protocol": telemetry["protocol"],
        "dataset_name": telemetry["dataset_name"],
        "capture_source": telemetry["capture_source"],
        "detection_result": alert.detection_result,
        "xai_explanation": alert.xai_explanation,
    }


def _investigation_dict(investigation: Investigation | None) -> dict[str, Any]:
    if investigation is None:
        return {}
    return {
        "investigation_id": investigation.investigation_id,
        "incident_id": investigation.incident_id,
        "status": investigation.status,
        "conclusion": investigation.conclusion,
        "analyst_notes": investigation.analyst_notes,
        "started_at": _iso(investigation.started_at),
        "completed_at": _iso(investigation.completed_at),
    }


def _related_actions(
    db: Session,
    incident_id: str | None,
    investigation_id: str | None,
) -> list[dict[str, Any]]:
    if not incident_id and not investigation_id:
        return []
    conditions = []
    if incident_id:
        conditions.append(AnalystAction.incident_id == incident_id)
    if investigation_id:
        conditions.append(AnalystAction.investigation_id == investigation_id)
    actions = db.execute(
        select(AnalystAction).where(or_(*conditions)).order_by(AnalystAction.created_at.desc()).limit(20)
    ).scalars().all()
    return [
        {
            "action_id": a.action_id,
            "action_type": a.action_type,
            "description": a.description,
            "result": a.result,
            "created_at": _iso(a.created_at),
        }
        for a in actions
    ]


def _related_audit(
    db: Session,
    incident_id: str | None,
    alert_id: str | None,
) -> list[dict[str, Any]]:
    if not incident_id and not alert_id:
        return []
    conditions = []
    if incident_id:
        conditions.append(AuditLog.resource_id == incident_id)
    if alert_id:
        conditions.append(AuditLog.resource_id == alert_id)
    logs = db.execute(
        select(AuditLog).where(or_(*conditions)).order_by(AuditLog.created_at.desc()).limit(20)
    ).scalars().all()
    return [
        {
            "audit_id": l.audit_id,
            "action": l.action,
            "description": l.description,
            "timestamp": _iso(l.created_at),
        }
        for l in logs
    ]



def build_incident_report(db: Session, incident_id: str) -> dict[str, Any] | None:
    incident = db.scalar(
        select(Incident).where(Incident.incident_id == incident_id)
    )
    if incident is None:
        return None

    alert = db.scalar(
        select(Alert).where(Alert.alert_id == incident.alert_id)
    )
    investigation = db.scalar(
        select(Investigation).where(
            Investigation.incident_id == incident.incident_id
        )
    )

    investigation_id = (
        investigation.investigation_id if investigation else None
    )

    return {
        "report_type": "INCIDENT_REPORT",
        "generated_at": _generated_at(),
        "incident": _incident_dict(incident),
        "alert": _alert_dict(alert),
        "investigation": _investigation_dict(investigation),
        "analyst_actions": _related_actions(
            db,
            incident.incident_id,
            investigation_id,
        ),
        "audit_information": _related_audit(
            db,
            incident.incident_id,
            incident.alert_id,
        ),
    }


def build_investigation_report(
    db: Session,
    investigation_id: str,
) -> dict[str, Any] | None:
    investigation = db.scalar(
        select(Investigation).where(
            Investigation.investigation_id == investigation_id
        )
    )
    if investigation is None:
        return None

    incident = db.scalar(
        select(Incident).where(
            Incident.incident_id == investigation.incident_id
        )
    )
    alert = None
    if incident:
        alert = db.scalar(
            select(Alert).where(Alert.alert_id == incident.alert_id)
        )

    return {
        "report_type": "INVESTIGATION_REPORT",
        "generated_at": _generated_at(),
        "investigation": _investigation_dict(investigation),
        "incident": _incident_dict(incident),
        "alert": _alert_dict(alert),
        "analyst_actions": _related_actions(
            db,
            investigation.incident_id,
            investigation.investigation_id,
        ),
        "audit_information": _related_audit(
            db,
            investigation.incident_id,
            incident.alert_id if incident else None,
        ),
    }


def build_alert_report(
    db: Session,
    alert_id: str,
) -> dict[str, Any] | None:
    alert = db.scalar(
        select(Alert).where(Alert.alert_id == alert_id)
    )
    if alert is None:
        return None

    incident = db.scalar(
        select(Incident).where(Incident.alert_id == alert.alert_id)
    )
    investigation = None
    if incident:
        investigation = db.scalar(
            select(Investigation).where(
                Investigation.incident_id == incident.incident_id
            )
        )

    return {
        "report_type": "ALERT_REPORT",
        "generated_at": _generated_at(),
        "alert": _alert_dict(alert),
        "incident": _incident_dict(incident),
        "investigation": _investigation_dict(investigation),
    }


def build_detection_xai_report(
    db: Session,
    alert_id: str,
) -> dict[str, Any] | None:
    alert = db.scalar(
        select(Alert).where(Alert.alert_id == alert_id)
    )
    if alert is None:
        return None

    return {
        "report_type": "DETECTION_XAI_REPORT",
        "generated_at": _generated_at(),
        "alert_id": alert.alert_id,
        "predicted_class": alert.predicted_class,
        "confidence": alert.confidence,
        "severity": alert.severity,
        "status": alert.status,
        "dataset_name": alert.dataset_name,
        "capture_source": alert.capture_source,
        "detection_result": alert.detection_result,
        "xai_explanation": alert.xai_explanation,
    }


def build_soc_summary(db: Session) -> dict[str, Any]:
    total_alerts = db.scalar(
        select(func.count()).select_from(Alert)
    ) or 0

    total_incidents = db.scalar(
        select(func.count()).select_from(Incident)
    ) or 0

    total_investigations = db.scalar(
        select(func.count()).select_from(Investigation)
    ) or 0

    total_network_events = db.scalar(
        select(func.count()).select_from(NetworkEvent)
    ) or 0

    alert_rows = db.execute(
        select(Alert.predicted_class, Alert.severity, Alert.status)
    ).all()

    attack_distribution = Counter()
    severity_distribution = Counter()
    alert_status_distribution = Counter()

    for predicted_class, severity, alert_status in alert_rows:
        attack_distribution[str(predicted_class)] += 1
        severity_distribution[str(severity)] += 1
        alert_status_distribution[str(alert_status)] += 1

    incident_rows = db.execute(
        select(Incident.status, Incident.severity, Incident.priority)
    ).all()

    incident_status_distribution = Counter()
    incident_severity_distribution = Counter()
    priority_distribution = Counter()

    for status, severity, priority in incident_rows:
        incident_status_distribution[str(status)] += 1
        incident_severity_distribution[str(severity)] += 1
        priority_distribution[str(priority)] += 1

    investigation_rows = db.execute(
        select(Investigation.status)
    ).all()
    investigation_status_distribution = Counter(
        str(row[0]) for row in investigation_rows
    )

    return {
        "report_type": "SOC_SUMMARY",
        "generated_at": _generated_at(),
        "totals": {
            "alerts": total_alerts,
            "incidents": total_incidents,
            "investigations": total_investigations,
            "network_events": total_network_events,
        },
        "attack_distribution": dict(
            sorted(
                attack_distribution.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "severity_distribution": dict(severity_distribution),
        "alert_status_distribution": dict(alert_status_distribution),
        "incident_status_distribution": dict(incident_status_distribution),
        "incident_severity_distribution": dict(incident_severity_distribution),
        "priority_distribution": dict(priority_distribution),
        "investigation_status_distribution": dict(
            investigation_status_distribution
        ),
    }
