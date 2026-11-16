from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.alert import Alert
from backend.app.models.incident import Incident
from backend.app.models.network_event import NetworkEvent
from backend.app.models.user import User
from backend.app.security.dependencies import get_current_user

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Returns high-performance, aggregate metrics directly computed across ALL
    records in PostgreSQL for the SOC dashboard KPI cards, network telemetry,
    and attack distributions.
    """

    # 1. ALERTS AGGREGATIONS
    total_alerts = db.scalar(select(func.count(Alert.id))) or 0
    resolved_alerts = (
        db.scalar(
            select(func.count(Alert.id)).where(
                func.upper(Alert.status) == "RESOLVED"
            )
        )
        or 0
    )
    active_alerts = total_alerts - resolved_alerts

    # Active alerts severity breakdown
    critical_active = (
        db.scalar(
            select(func.count(Alert.id)).where(
                func.upper(Alert.status) != "RESOLVED",
                func.upper(Alert.severity) == "CRITICAL",
            )
        )
        or 0
    )
    high_active = (
        db.scalar(
            select(func.count(Alert.id)).where(
                func.upper(Alert.status) != "RESOLVED",
                func.upper(Alert.severity) == "HIGH",
            )
        )
        or 0
    )
    medium_active = (
        db.scalar(
            select(func.count(Alert.id)).where(
                func.upper(Alert.status) != "RESOLVED",
                func.upper(Alert.severity) == "MEDIUM",
            )
        )
        or 0
    )
    low_active = (
        db.scalar(
            select(func.count(Alert.id)).where(
                func.upper(Alert.status) != "RESOLVED",
                func.upper(Alert.severity) == "LOW",
            )
        )
        or 0
    )

    open_alerts = (
        db.scalar(
            select(func.count(Alert.id)).where(
                func.upper(Alert.status) == "OPEN"
            )
        )
        or 0
    )
    acknowledged_alerts = (
        db.scalar(
            select(func.count(Alert.id)).where(
                func.upper(Alert.status) == "ACKNOWLEDGED"
            )
        )
        or 0
    )
    investigating_alerts = (
        db.scalar(
            select(func.count(Alert.id)).where(
                func.upper(Alert.status) == "INVESTIGATING"
            )
        )
        or 0
    )

    # 2. INCIDENTS AGGREGATIONS
    total_incidents = db.scalar(select(func.count(Incident.id))) or 0
    closed_incidents = (
        db.scalar(
            select(func.count(Incident.id)).where(
                func.upper(Incident.status) == "CLOSED"
            )
        )
        or 0
    )
    active_incidents = total_incidents - closed_incidents

    open_incidents = (
        db.scalar(
            select(func.count(Incident.id)).where(
                func.upper(Incident.status) == "OPEN"
            )
        )
        or 0
    )
    acknowledged_incidents = (
        db.scalar(
            select(func.count(Incident.id)).where(
                func.upper(Incident.status) == "ACKNOWLEDGED"
            )
        )
        or 0
    )
    investigating_incidents = (
        db.scalar(
            select(func.count(Incident.id)).where(
                func.upper(Incident.status) == "INVESTIGATING"
            )
        )
        or 0
    )
    resolved_incidents = (
        db.scalar(
            select(func.count(Incident.id)).where(
                func.upper(Incident.status) == "RESOLVED"
            )
        )
        or 0
    )

    # 3. NETWORK TELEMETRY
    total_events = db.scalar(select(func.count(NetworkEvent.id))) or 0
    unique_src_ips = (
        db.scalar(
            select(func.count(func.distinct(NetworkEvent.source_ip)))
        )
        or 0
    )
    unique_dst_ips = (
        db.scalar(
            select(func.count(func.distinct(NetworkEvent.destination_ip)))
        )
        or 0
    )
    tcp_events = (
        db.scalar(
            select(func.count(NetworkEvent.id)).where(
                func.lower(NetworkEvent.protocol) == "tcp"
            )
        )
        or 0
    )
    udp_events = (
        db.scalar(
            select(func.count(NetworkEvent.id)).where(
                func.lower(NetworkEvent.protocol) == "udp"
            )
        )
        or 0
    )
    other_protocol_events = max(0, total_events - tcp_events - udp_events)

    # 4. ATTACK DISTRIBUTION (Aggregated across the ENTIRE database)
    attack_dist_query = text("""
        SELECT predicted_class, COUNT(*) as count
        FROM alerts
        WHERE UPPER(predicted_class) NOT IN ('BENIGN', 'NORMAL', '')
        GROUP BY predicted_class
        ORDER BY count DESC
        LIMIT 8
    """)
    dist_rows = db.execute(attack_dist_query).fetchall()
    attack_distribution = [
        {"name": row[0], "count": int(row[1])}
        for row in dist_rows
    ]

    # 5. RECENT DETECTION RECORDS (Top 6 latest alerts)
    recent_alerts_stmt = (
        select(Alert)
        .order_by(Alert.detected_at.desc())
        .limit(8)
    )
    recent_alerts_records = db.execute(recent_alerts_stmt).scalars().all()
    recent_alerts = [
        {
            "id": a.id,
            "alert_id": a.alert_id,
            "predicted_class": a.predicted_class,
            "confidence": a.confidence,
            "severity": a.severity,
            "status": a.status,
            "source_ip": a.source_ip,
            "destination_ip": a.destination_ip,
            "source_port": a.source_port,
            "destination_port": a.destination_port,
            "dataset_name": a.dataset_name,
            "capture_source": a.capture_source,
            "detected_at": (
                f"{a.detected_at.isoformat()}Z"
                if a.detected_at and not a.detected_at.tzinfo
                else (a.detected_at.isoformat() if a.detected_at else None)
            ),
        }
        for a in recent_alerts_records
    ]

    return {
        "status": "healthy",
        "alerts": {
            "total": total_alerts,
            "active": active_alerts,
            "resolved": resolved_alerts,
            "critical_active": critical_active,
            "high_active": high_active,
            "medium_active": medium_active,
            "low_active": low_active,
            "open": open_alerts,
            "acknowledged": acknowledged_alerts,
            "investigating": investigating_alerts,
        },
        "incidents": {
            "total": total_incidents,
            "active": active_incidents,
            "closed": closed_incidents,
            "open": open_incidents,
            "acknowledged": acknowledged_incidents,
            "investigating": investigating_incidents,
            "resolved": resolved_incidents,
        },
        "network": {
            "total_events": total_events,
            "unique_source_ips": unique_src_ips,
            "unique_destination_ips": unique_dst_ips,
            "tcp_events": tcp_events,
            "udp_events": udp_events,
            "other_protocol_events": other_protocol_events,
        },
        "attack_distribution": attack_distribution,
        "recent_alerts": recent_alerts,
    }
