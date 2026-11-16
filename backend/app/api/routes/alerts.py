from datetime import datetime, timezone
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.alert import Alert
from backend.app.models.incident import Incident
from backend.app.models.investigation import Investigation
from backend.app.models.analyst_action import AnalystAction
from backend.app.models.user import User
from backend.app.schemas.alert import (
    AlertListResponse,
    AlertResponse,
    AlertStatsResponse,
    AlertStatusUpdate,
)
from backend.app.security.dependencies import (
    get_current_user,
    require_role,
)

router = APIRouter(
    prefix="/api/alerts",
    tags=["Alert Center"],
)

from backend.app.soc.telemetry_resolver import resolve_network_telemetry

def _enrich_alert_with_correlations(alert: Alert, db: Session) -> AlertResponse:
    alert_resp = AlertResponse.model_validate(alert)

    # Ensure complete, professional network detection telemetry
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
    alert_resp.source_ip = telemetry["source_ip"]
    alert_resp.destination_ip = telemetry["destination_ip"]
    alert_resp.source_port = telemetry["source_port"]
    alert_resp.destination_port = telemetry["destination_port"]
    alert_resp.protocol = telemetry["protocol"]
    alert_resp.dataset_name = telemetry["dataset_name"]
    alert_resp.capture_source = telemetry["capture_source"]

    inc = db.execute(
        select(Incident).where(Incident.alert_id == alert.alert_id)
    ).scalars().first()
    if inc:
        alert_resp.incident_id = inc.incident_id
        inv = db.execute(
            select(Investigation).where(Investigation.incident_id == inc.incident_id)
        ).scalars().first()
        if inv:
            alert_resp.investigation_id = inv.investigation_id
    return alert_resp

ALLOWED_STATUS_TRANSITIONS = {
    "OPEN": {"ACKNOWLEDGED", "INVESTIGATING", "RESOLVED"},
    "ACKNOWLEDGED": {"INVESTIGATING", "RESOLVED"},
    "INVESTIGATING": {"RESOLVED"},
    "RESOLVED": set(),
}


@router.get(
    "",
    response_model=AlertListResponse,
)
def get_alerts(
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    severity: str | None = None,
    predicted_class: str | None = None,
    search: str | None = None,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Alert)

    if status_filter is None:
        statement = statement.where(
        func.upper(Alert.status) != "RESOLVED"
    )

    if status_filter:
        statement = statement.where(
            func.upper(Alert.status) == status_filter.upper()
        )

    if severity:
        statement = statement.where(
            func.upper(Alert.severity) == severity.upper()
        )

    if predicted_class:
        statement = statement.where(
            func.upper(Alert.predicted_class)
            == predicted_class.upper()
        )

    if search and search.strip():
        search_value = f"%{search.strip()}%"
        incident_subquery = select(Incident.alert_id).where(
            Incident.incident_id.ilike(search_value)
        )
        inv_subquery = select(Incident.alert_id).join(
            Investigation, Investigation.incident_id == Incident.incident_id
        ).where(Investigation.investigation_id.ilike(search_value))

        statement = statement.where(
            Alert.alert_id.ilike(search_value)
            | Alert.predicted_class.ilike(search_value)
            | Alert.description.ilike(search_value)
            | Alert.source_ip.ilike(search_value)
            | Alert.destination_ip.ilike(search_value)
            | Alert.dataset_name.ilike(search_value)
            | Alert.alert_id.in_(incident_subquery)
            | Alert.alert_id.in_(inv_subquery)
        )

    total_statement = statement.with_only_columns(
        func.count(Alert.id)
    )
    total = db.scalar(total_statement) or 0

    statement = (
        statement
        .order_by(Alert.detected_at.desc())
        .limit(limit)
        .offset(offset)
    )

    alerts = db.execute(statement).scalars().all()
    enriched = [_enrich_alert_with_correlations(a, db) for a in alerts]

    return AlertListResponse(
        alerts=enriched,
        total=total,
    )


@router.get(
    "/stats",
    response_model=AlertStatsResponse,
)
def get_alert_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    def count_where(column, value):
        return (
            db.scalar(
                select(func.count(Alert.id)).where(
                    func.upper(column) == value
                )
            )
            or 0
        )

    active_critical = db.scalar(
        select(func.count(Alert.id)).where(
            func.upper(Alert.severity) == "CRITICAL",
            func.upper(Alert.status) != "RESOLVED",
        )
    ) or 0

    active_high = db.scalar(
        select(func.count(Alert.id)).where(
            func.upper(Alert.severity) == "HIGH",
            func.upper(Alert.status) != "RESOLVED",
        )
    ) or 0

    return AlertStatsResponse(
        total=db.scalar(select(func.count(Alert.id))) or 0,
        open=count_where(Alert.status, "OPEN"),
        acknowledged=count_where(Alert.status, "ACKNOWLEDGED"),
        investigating=count_where(Alert.status, "INVESTIGATING"),
        resolved=count_where(Alert.status, "RESOLVED"),
        critical=count_where(Alert.severity, "CRITICAL"),
        high=count_where(Alert.severity, "HIGH"),
        medium=count_where(Alert.severity, "MEDIUM"),
        low=count_where(Alert.severity, "LOW"),
        info=count_where(Alert.severity, "INFO"),
        active_critical=active_critical,
        active_high=active_high,
    )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.scalar(
        select(Alert).where(
            Alert.alert_id == alert_id
        )
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    return _enrich_alert_with_correlations(alert, db)


@router.patch("/{alert_id}/status", response_model=AlertResponse)
def update_alert_status(
    alert_id: str,
    payload: AlertStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    alert = db.scalar(
        select(Alert).where(Alert.alert_id == alert_id)
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    new_status = payload.status.strip().upper()
    current_status = alert.status.upper()

    valid_statuses = {
        "OPEN",
        "ACKNOWLEDGED",
        "INVESTIGATING",
        "RESOLVED",
    }

    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid alert status. "
                "Allowed statuses: OPEN, ACKNOWLEDGED, "
                "INVESTIGATING, RESOLVED."
            ),
        )

    if new_status == current_status:
        return _enrich_alert_with_correlations(alert, db)

    allowed_next = ALLOWED_STATUS_TRANSITIONS.get(
        current_status,
        set(),
    )

    if new_status not in allowed_next:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Invalid status transition: "
                f"{current_status} -> {new_status}."
            ),
        )

    alert.status = new_status
    alert.updated_at = datetime.now(timezone.utc)

    # When transitioning to ACKNOWLEDGED: ensure incident exists and is marked ACKNOWLEDGED
    if new_status == "ACKNOWLEDGED":
        incident = db.execute(
            select(Incident).where(Incident.alert_id == alert.alert_id)
        ).scalars().first()
        if not incident:
            incident = Incident(
                incident_id=f"ZUKA-INC-{secrets.token_hex(4).upper()}",
                alert_id=alert.alert_id,
                title=f"Incident for {alert.alert_id} - {alert.predicted_class}",
                description=f"Correlated from Alert {alert.alert_id}. Attack: {alert.predicted_class}, Severity: {alert.severity}.",
                severity=alert.severity,
                priority="P1" if alert.severity.upper() == "CRITICAL" else ("P2" if alert.severity.upper() == "HIGH" else "P3"),
                status="ACKNOWLEDGED",
                assigned_to_id=current_user.id,
            )
            db.add(incident)
            db.flush()
        else:
            incident.status = "ACKNOWLEDGED"
            if not incident.assigned_to_id:
                incident.assigned_to_id = current_user.id

        action = AnalystAction(
            action_id=f"ACT-{secrets.token_hex(4).upper()}",
            incident_id=incident.incident_id,
            analyst_id=current_user.id,
            action_type="ACKNOWLEDGE_ALERT",
            description=f"Alert {alert.alert_id} acknowledged by {current_user.username}. Correlated Incident {incident.incident_id} marked ACKNOWLEDGED.",
        )
        db.add(action)

    # When transitioning to INVESTIGATING: auto-escalate/link incident and investigation
    elif new_status == "INVESTIGATING":
        incident = db.execute(
            select(Incident).where(Incident.alert_id == alert.alert_id)
        ).scalars().first()
        if not incident:
            incident = Incident(
                incident_id=f"ZUKA-INC-{secrets.token_hex(4).upper()}",
                alert_id=alert.alert_id,
                title=f"Incident for {alert.alert_id} - {alert.predicted_class}",
                description=f"Auto-escalated from Alert {alert.alert_id}. Attack: {alert.predicted_class}, Severity: {alert.severity}.",
                severity=alert.severity,
                priority="P1" if alert.severity.upper() == "CRITICAL" else ("P2" if alert.severity.upper() == "HIGH" else "P3"),
                status="INVESTIGATING",
                assigned_to_id=current_user.id,
            )
            db.add(incident)
            db.flush()
        else:
            incident.status = "INVESTIGATING"

        investigation = db.execute(
            select(Investigation).where(Investigation.incident_id == incident.incident_id)
        ).scalars().first()
        if not investigation:
            investigation = Investigation(
                investigation_id=f"ZUKA-INV-{secrets.token_hex(4).upper()}",
                incident_id=incident.incident_id,
                status="IN_PROGRESS",
                analyst_notes=f"Alert {alert.alert_id} escalated to Investigation Department by {current_user.username}.",
                started_at=datetime.now(timezone.utc),
            )
            db.add(investigation)
            db.flush()
        else:
            investigation.status = "IN_PROGRESS"

        action = AnalystAction(
            action_id=f"ACT-{secrets.token_hex(4).upper()}",
            incident_id=incident.incident_id,
            investigation_id=investigation.investigation_id,
            analyst_id=current_user.id,
            action_type="ALERT_ESCALATED_INVESTIGATION",
            description=f"Alert {alert.alert_id} status moved to INVESTIGATING.",
        )
        db.add(action)

    # When transitioning to RESOLVED: synchronize incident and investigation
    elif new_status == "RESOLVED":
        incident = db.execute(
            select(Incident).where(Incident.alert_id == alert.alert_id)
        ).scalars().first()
        if incident:
            incident.status = "RESOLVED"
            incident.resolved_at = datetime.now(timezone.utc)
            if not incident.resolution_summary:
                incident.resolution_summary = f"Alert {alert.alert_id} resolved by {current_user.username}."
            inv = db.execute(
                select(Investigation).where(Investigation.incident_id == incident.incident_id)
            ).scalars().first()
            if inv:
                inv.status = "COMPLETED"
                inv.completed_at = datetime.now(timezone.utc)
                if not inv.conclusion:
                    inv.conclusion = f"Resolved alongside Alert {alert.alert_id}."
            action = AnalystAction(
                action_id=f"ACT-{secrets.token_hex(4).upper()}",
                incident_id=incident.incident_id,
                analyst_id=current_user.id,
                action_type="RESOLVE_INCIDENT",
                description=f"Alert {alert.alert_id} resolved by {current_user.username}.",
            )
            db.add(action)

    db.commit()
    db.refresh(alert)

    return _enrich_alert_with_correlations(alert, db)