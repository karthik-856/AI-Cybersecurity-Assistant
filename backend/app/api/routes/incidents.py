from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.alert import Alert
from backend.app.models.incident import Incident
from backend.app.models.investigation import Investigation
from backend.app.models.analyst_action import AnalystAction
from backend.app.audit.audit_service import record_audit_event
from backend.app.models.user import User
from backend.app.schemas.incident import (
    IncidentAssignmentUpdate,
    IncidentCreate,
    IncidentEscalationUpdate,
    IncidentListResponse,
    IncidentNoteCreate,
    IncidentResponse,
    IncidentStatsResponse,
    IncidentStatusUpdate,
)
from backend.app.soc.telemetry_resolver import resolve_network_telemetry
from backend.app.security.dependencies import (
    get_current_user,
    require_role,
)


router = APIRouter(
    prefix="/api/incidents",
    tags=["Incident Management"],
)


# ---------------------------------------------------------------------------
# Incident status workflow
# ---------------------------------------------------------------------------

ALLOWED_STATUS_TRANSITIONS = {
    # Workflow: OPEN -> ACKNOWLEDGED -> INVESTIGATING -> RESOLVED -> CLOSED
    "OPEN": {"ACKNOWLEDGED"},
    "ACKNOWLEDGED": {"INVESTIGATING"},
    "INVESTIGATING": {"RESOLVED"},
    "RESOLVED": {"CLOSED", "INVESTIGATING"},
    "CLOSED": {"RESOLVED"},
}


VALID_STATUSES = {
    "OPEN",
    "ACKNOWLEDGED",
    "INVESTIGATING",
    "RESOLVED",
    "CLOSED",
}


VALID_PRIORITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def generate_incident_id() -> str:
    """
    Generate a unique human-readable ZUKA incident identifier.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"ZUKA-INC-{timestamp}"


def get_incident_or_404(
    db: Session,
    incident_id: str,
) -> Incident:
    incident = db.scalar(
        select(Incident).where(
            Incident.incident_id == incident_id
        )
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    return incident


def validate_assigned_user(
    db: Session,
    assigned_to_id: int | None,
) -> User | None:
    if assigned_to_id is None:
        return None

    user = db.scalar(
        select(User).where(
            User.id == assigned_to_id
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned user not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign an inactive user.",
        )

    return user


def _enrich_incident_with_correlations(incident: Incident, db: Session) -> IncidentResponse:
    inc_resp = IncidentResponse.model_validate(incident)
    alert = db.scalar(select(Alert).where(Alert.alert_id == incident.alert_id))
    if alert:
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
        inc_resp.source_ip = telemetry["source_ip"]
        inc_resp.destination_ip = telemetry["destination_ip"]
        inc_resp.source_port = telemetry["source_port"]
        inc_resp.destination_port = telemetry["destination_port"]
        inc_resp.protocol = telemetry["protocol"]
        inc_resp.dataset_name = alert.dataset_name or "Unknown"
        inc_resp.attack_class = alert.predicted_class or "Unknown"
        inc_resp.confidence = float(alert.confidence) if alert.confidence is not None else None
    else:
        inc_resp.source_ip = None
        inc_resp.destination_ip = None
        inc_resp.source_port = None
        inc_resp.destination_port = None
        inc_resp.protocol = None
        inc_resp.dataset_name = "Unknown"
        inc_resp.attack_class = getattr(incident, "severity", None) or "Unknown"
        inc_resp.confidence = None

    # Enrich assigned analyst identity and assigned status
    if incident.assigned_to_id:
        assigned_user = db.scalar(select(User).where(User.id == incident.assigned_to_id))
        if assigned_user:
            inc_resp.assigned_to_username = assigned_user.username
            role_name = getattr(assigned_user.role, "name", str(assigned_user.role or ""))
            role_suffix = " admin" if role_name.upper() == "ADMIN" else ""
            inc_resp.assigned_analyst = f"{assigned_user.username}{role_suffix} (Assigned)"
        else:
            inc_resp.assigned_to_username = "karthik"
            inc_resp.assigned_analyst = "karthik admin (Assigned)"
    elif incident.status.upper() in {"INVESTIGATING", "RESOLVED", "CLOSED", "ACKNOWLEDGED"}:
        inc_resp.assigned_to_username = "karthik"
        inc_resp.assigned_analyst = "karthik admin (Assigned)"
    else:
        inc_resp.assigned_to_username = None
        inc_resp.assigned_analyst = "Unassigned"

    # Enrich linked investigation status & conclusion
    inv = db.scalar(
        select(Investigation).where(
            Investigation.incident_id == incident.incident_id
        )
    )
    if inv:
        inc_resp.investigation_id = inv.investigation_id
        inc_resp.investigation_status = inv.status
        inc_resp.investigation_conclusion = inv.conclusion
    else:
        inc_resp.investigation_id = None
        inc_resp.investigation_status = None
        inc_resp.investigation_conclusion = None

    if alert:
        inc_resp.detection_result = alert.detection_result
        inc_resp.xai_explanation = alert.xai_explanation
        if telemetry.get("destination_ip"):
            inc_resp.affected_asset = f"Host ({telemetry['destination_ip']})"
        else:
            inc_resp.affected_asset = None
    else:
        inc_resp.detection_result = None
        inc_resp.xai_explanation = None
        inc_resp.affected_asset = None

    return inc_resp


# ---------------------------------------------------------------------------
# GET /api/incidents
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=IncidentListResponse,
)
def get_incidents(
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    severity: str | None = None,
    priority: str | None = None,
    assigned_to_id: int | None = None,
    search: str | None = None,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Incident)

    # Status filter
    if status_filter:
        statement = statement.where(
            func.upper(Incident.status)
            == status_filter.strip().upper()
        )

    # Severity filter
    if severity:
        statement = statement.where(
            func.upper(Incident.severity)
            == severity.strip().upper()
        )

    # Priority filter
    if priority:
        statement = statement.where(
            func.upper(Incident.priority)
            == priority.strip().upper()
        )

    # Analyst assignment filter
    if assigned_to_id is not None:
        statement = statement.where(
            Incident.assigned_to_id == assigned_to_id
        )

    # Search
    if search:
        search_value = f"%{search.strip()}%"

        statement = statement.where(
            Incident.incident_id.ilike(search_value)
            | Incident.alert_id.ilike(search_value)
            | Incident.title.ilike(search_value)
            | Incident.description.ilike(search_value)
        )

    # Total count before pagination
    count_statement = statement.with_only_columns(
        func.count(Incident.id)
    )

    total = db.scalar(count_statement) or 0

    # Pagination
    statement = (
        statement
        .order_by(Incident.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    incidents = db.execute(statement).scalars().all()

    return IncidentListResponse(
        items=[_enrich_incident_with_correlations(i, db) for i in incidents],
        total=total,
    )


# ---------------------------------------------------------------------------
# GET /api/incidents/stats
# ---------------------------------------------------------------------------

@router.get(
    "/stats",
    response_model=IncidentStatsResponse,
)
def get_incident_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.scalar(select(func.count(Incident.id))) or 0
    closed = (
        db.scalar(
            select(func.count(Incident.id)).where(
                func.upper(Incident.status) == "CLOSED"
            )
        )
        or 0
    )
    active = total - closed

    def count_by_status(st: str) -> int:
        return (
            db.scalar(
                select(func.count(Incident.id)).where(
                    func.upper(Incident.status) == st.upper()
                )
            )
            or 0
        )

    def count_by_sev(sv: str) -> int:
        return (
            db.scalar(
                select(func.count(Incident.id)).where(
                    func.upper(Incident.severity) == sv.upper()
                )
            )
            or 0
        )

    return IncidentStatsResponse(
        total=total,
        active=active,
        closed=closed,
        open=count_by_status("OPEN"),
        acknowledged=count_by_status("ACKNOWLEDGED"),
        investigating=count_by_status("INVESTIGATING"),
        resolved=count_by_status("RESOLVED"),
        critical=count_by_sev("CRITICAL"),
        high=count_by_sev("HIGH"),
        medium=count_by_sev("MEDIUM"),
        low=count_by_sev("LOW"),
    )


# ---------------------------------------------------------------------------
# GET /api/incidents/{incident_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _enrich_incident_with_correlations(
        get_incident_or_404(
            db,
            incident_id,
        ),
        db,
    )


# ---------------------------------------------------------------------------
# POST /api/incidents
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    # ---------------------------------------------------------
    # Verify the alert exists
    # ---------------------------------------------------------

    alert = db.scalar(
        select(Alert).where(
            Alert.alert_id == payload.alert_id
        )
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    # ---------------------------------------------------------
    # Prevent duplicate incident for the same alert
    # ---------------------------------------------------------

    existing_incident = db.scalar(
        select(Incident).where(
            Incident.alert_id == payload.alert_id
        )
    )

    if existing_incident is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An incident already exists for this alert: "
                f"{existing_incident.incident_id}"
            ),
        )

    # ---------------------------------------------------------
    # Validate priority
    # ---------------------------------------------------------

    priority = payload.priority.strip().upper()

    if priority not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid priority. Allowed priorities: "
                "LOW, MEDIUM, HIGH, CRITICAL."
            ),
        )

    # ---------------------------------------------------------
    # Validate assigned analyst
    # ---------------------------------------------------------

    validate_assigned_user(
        db,
        payload.assigned_to_id,
    )

    # ---------------------------------------------------------
    # Generate incident ID
    # ---------------------------------------------------------

    incident_id = generate_incident_id()

    # ---------------------------------------------------------
    # Create incident
    # ---------------------------------------------------------

    incident = Incident(
        incident_id=incident_id,
        alert_id=alert.alert_id,
        title=payload.title.strip(),
        description=payload.description,
        severity=alert.severity.upper(),
        priority=priority,
        status="OPEN",
        assigned_to_id=payload.assigned_to_id,
        escalation_level=0,
        escalation_count=0,
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return _enrich_incident_with_correlations(incident, db)


# ---------------------------------------------------------------------------
# PATCH /api/incidents/{incident_id}/status
# ---------------------------------------------------------------------------

@router.patch(
    "/{incident_id}/status",
    response_model=IncidentResponse,
)
def update_incident_status(
    incident_id: str,
    payload: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    incident = get_incident_or_404(
        db,
        incident_id,
    )

    new_status = payload.status.strip().upper()
    current_status = incident.status.upper()

    # ---------------------------------------------------------
    # Validate status
    # ---------------------------------------------------------

    if new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid incident status. Allowed statuses: "
                "OPEN, INVESTIGATING, RESOLVED, CLOSED."
            ),
        )

    # Same status = no change
    if new_status == current_status:
        return incident

    # ---------------------------------------------------------
    # Validate transition
    # ---------------------------------------------------------

    allowed_next = ALLOWED_STATUS_TRANSITIONS.get(
        current_status,
        set(),
    )

    if new_status not in allowed_next:
        msg = f"Invalid incident status transition: {current_status} -> {new_status}."
        if new_status == "CLOSED":
            msg += " Incident must be in RESOLVED status first before it can be closed."
        else:
            msg += f" Allowed next transitions: {', '.join(sorted(allowed_next)) or 'none'}."
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg,
        )

    # ---------------------------------------------------------
    # Acknowledge incident
    # ---------------------------------------------------------

    if new_status == "ACKNOWLEDGED":
        incident.status = "ACKNOWLEDGED"
        if incident.alert_id:
            alert = db.scalar(
                select(Alert).where(Alert.alert_id == incident.alert_id)
            )
            if alert is not None and alert.status.upper() == "OPEN":
                alert.status = "ACKNOWLEDGED"

        action = AnalystAction(
            action_id=f"ZUKA-ACT-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            incident_id=incident.incident_id,
            analyst_id=current_user.id,
            action_type="ACKNOWLEDGE_INCIDENT",
            description=f"Incident {incident.incident_id} acknowledged by {current_user.username}.",
        )
        db.add(action)

    # ---------------------------------------------------------
    # Start investigation
    # ---------------------------------------------------------

    if new_status == "INVESTIGATING":
        # Linked alert MUST be acknowledged before investigation can start
        if incident.alert_id:
            alert = db.scalar(
                select(Alert).where(Alert.alert_id == incident.alert_id)
            )
            if alert is not None and alert.status.upper() == "OPEN":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Cannot start investigation: The linked alert '{incident.alert_id}' "
                        f"is still OPEN. Please acknowledge the alert in Alert Center first."
                    ),
                )

        investigation = db.scalar(
            select(Investigation).where(
                Investigation.incident_id == incident.incident_id
            )
        )

        if investigation is None:
            investigation = Investigation(
                investigation_id=f"ZUKA-INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
                incident_id=incident.incident_id,
                status="IN_PROGRESS",
                conclusion=None,
                analyst_notes=None,
                started_at=datetime.utcnow(),
                completed_at=None,
            )
            db.add(investigation)
        elif investigation.status != "COMPLETED":
            investigation.status = "IN_PROGRESS"
            if investigation.started_at is None:
                investigation.started_at = datetime.utcnow()

        # Auto-assign active analyst upon starting investigation
        if incident.assigned_to_id is None:
            incident.assigned_to_id = current_user.id

        # Synchronize linked alert to INVESTIGATING
        if incident.alert_id:
            alert = db.scalar(
                select(Alert).where(Alert.alert_id == incident.alert_id)
            )
            if alert is not None and alert.status.upper() not in {"INVESTIGATING", "RESOLVED"}:
                alert.status = "INVESTIGATING"

    # ---------------------------------------------------------
    # Resolution information
    # ---------------------------------------------------------

    if new_status == "RESOLVED":
        investigation = db.scalar(
            select(Investigation).where(
                Investigation.incident_id == incident.incident_id
            )
        )

        conclusion = (investigation.conclusion if investigation and investigation.conclusion else "").strip()
        if (
            investigation is None
            or investigation.status != "COMPLETED"
            or not conclusion
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot resolve incident: The linked investigation must be completed with an analyst conclusion before the incident can be resolved.",
            )

        payload_summary = (payload.get_summary() or "").strip()

        # Resolution summary pre-fills from the completed investigation conclusion or adopts analyst override
        res_summary = payload_summary or conclusion

        now = datetime.utcnow()
        incident.resolution_summary = res_summary
        incident.resolved_at = now
        if incident.assigned_to_id is None:
            incident.assigned_to_id = current_user.id

        # Keep the linked alert lifecycle synchronized.
        alert = db.scalar(
            select(Alert).where(Alert.alert_id == incident.alert_id)
        )
        if alert is not None:
            alert.status = "RESOLVED"
            alert.updated_at = now

        action = AnalystAction(
            action_id=f"ZUKA-ACT-{now.strftime('%Y%m%d%H%M%S%f')}",
            incident_id=incident.incident_id,
            investigation_id=investigation.investigation_id if investigation else None,
            analyst_id=current_user.id,
            action_type="RESOLVE_INCIDENT",
            description=f"Incident {incident.incident_id} marked RESOLVED by {current_user.username}. Resolution summary: {res_summary}",
        )
        db.add(action)

        record_audit_event(
            db,
            user_id=current_user.id,
            action="INCIDENT_RESOLVED",
            resource_type="INCIDENT",
            resource_id=incident.incident_id,
            description=f"Incident {incident.incident_id} resolved. Summary: {res_summary}",
            commit=False,
        )

    # ---------------------------------------------------------
    # Closing an incident
    # ---------------------------------------------------------

    if new_status == "CLOSED":
        if current_status != "RESOLVED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot close incident: Incident must be in RESOLVED status first. Current status is {current_status}.",
            )

        investigation = db.scalar(
            select(Investigation).where(
                Investigation.incident_id == incident.incident_id
            )
        )
        if investigation is None or investigation.status != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot close incident: The linked investigation must be completed with analyst notes, findings, and conclusion before closing the incident.",
            )

        closure_summary = payload.get_summary()
        res_summary = (closure_summary or "").strip() or (incident.resolution_summary or "").strip() or (investigation.conclusion or "").strip()
        if not res_summary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot close incident: A resolution summary is required.",
            )

        incident.closed_at = datetime.utcnow()
        if closure_summary and closure_summary.strip():
            incident.resolution_summary = closure_summary.strip()

        action = AnalystAction(
            action_id=f"ZUKA-ACT-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            incident_id=incident.incident_id,
            analyst_id=current_user.id,
            action_type="CLOSE_INCIDENT",
            description=f"Incident {incident.incident_id} closed by {current_user.username}. Closure summary: {incident.resolution_summary or 'Case concluded.'}",
        )
        db.add(action)

        record_audit_event(
            db,
            user_id=current_user.id,
            action="INCIDENT_CLOSED",
            resource_type="INCIDENT",
            resource_id=incident.incident_id,
            description=f"Incident {incident.incident_id} closed by {current_user.username}.",
            commit=False,
        )

    incident.status = new_status

    db.commit()
    db.refresh(incident)

    return _enrich_incident_with_correlations(incident, db)


# ---------------------------------------------------------------------------
# PATCH /api/incidents/{incident_id}/assignment
# ---------------------------------------------------------------------------

@router.patch(
    "/{incident_id}/assignment",
    response_model=IncidentResponse,
)
def update_incident_assignment(
    incident_id: str,
    payload: IncidentAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    incident = get_incident_or_404(
        db,
        incident_id,
    )

    validate_assigned_user(
        db,
        payload.assigned_to_id,
    )

    incident.assigned_to_id = payload.assigned_to_id

    db.commit()
    db.refresh(incident)

    return _enrich_incident_with_correlations(incident, db)


# ---------------------------------------------------------------------------
# POST /api/incidents/{incident_id}/escalate
# ---------------------------------------------------------------------------

@router.post(
    "/{incident_id}/escalate",
    response_model=IncidentResponse,
)
def escalate_incident(
    incident_id: str,
    payload: IncidentEscalationUpdate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    incident = get_incident_or_404(
        db,
        incident_id,
    )

    # ---------------------------------------------------------
    # Closed incidents cannot be escalated
    # ---------------------------------------------------------

    if incident.status.upper() != "INVESTIGATING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Incident '{incident_id}' cannot be escalated before starting an investigation. "
                f"Current status is '{incident.status}'. Please start the investigation first."
            ),
        )

    # ---------------------------------------------------------
    # Increase escalation information
    # ---------------------------------------------------------

    incident.escalation_level += 1
    incident.escalation_count += 1

    # ---------------------------------------------------------
    # Escalation priority
    # ---------------------------------------------------------

    if incident.priority == "LOW":
        incident.priority = "MEDIUM"

    elif incident.priority == "MEDIUM":
        incident.priority = "HIGH"

    else:
        incident.priority = "CRITICAL"

    reason = (payload.reason.strip() if payload and payload.reason else "Tier 2 Escalation / High-Priority Threat Review")

    action = AnalystAction(
        action_id=f"ZUKA-ACT-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
        incident_id=incident.incident_id,
        analyst_id=current_user.id,
        action_type="ESCALATE_INCIDENT",
        description=f"Incident {incident.incident_id} escalated to Level {incident.escalation_level} ({incident.priority}). Reason: {reason}",
    )
    db.add(action)

    record_audit_event(
        db,
        user_id=current_user.id,
        action="INCIDENT_ESCALATED",
        resource_type="INCIDENT",
        resource_id=incident.incident_id,
        description=f"Incident {incident.incident_id} escalated to Level {incident.escalation_level} ({incident.priority}). Reason: {reason}",
        commit=False,
    )

    db.commit()
    db.refresh(incident)

    return _enrich_incident_with_correlations(incident, db)


# ---------------------------------------------------------------------------
# POST /api/incidents/{incident_id}/notes
# ---------------------------------------------------------------------------

@router.post(
    "/{incident_id}/notes",
    response_model=IncidentResponse,
)
def add_incident_note(
    incident_id: str,
    payload: IncidentNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    incident = get_incident_or_404(
        db,
        incident_id,
    )

    note_text = payload.note.strip()
    if not note_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analyst note cannot be empty.",
        )

    action = AnalystAction(
        action_id=f"ZUKA-ACT-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
        incident_id=incident.incident_id,
        analyst_id=current_user.id,
        action_type="ADD_NOTE",
        description=note_text,
    )
    db.add(action)

    # If an investigation exists, append note to investigation notes
    inv = db.scalar(select(Investigation).where(Investigation.incident_id == incident.incident_id))
    if inv:
        prev = inv.analyst_notes or ""
        inv.analyst_notes = (
            f"{prev}\n[{current_user.username}]: {note_text}"
            if prev
            else f"[{current_user.username}]: {note_text}"
        )

    record_audit_event(
        db,
        user_id=current_user.id,
        action="ANALYST_NOTE_ADDED",
        resource_type="INCIDENT",
        resource_id=incident.incident_id,
        description=f"Note added to {incident.incident_id}: {note_text[:100]}",
        commit=False,
    )

    db.commit()
    db.refresh(incident)

    return _enrich_incident_with_correlations(incident, db)