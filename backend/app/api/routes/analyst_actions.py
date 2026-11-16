from __future__ import annotations
from backend.app.core.time import utc_now

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.alert import Alert
from backend.app.models.analyst_action import AnalystAction
from backend.app.models.incident import Incident
from backend.app.models.investigation import Investigation
from backend.app.models.user import User
from backend.app.schemas.analyst_action import (
    AnalystActionCreate,
    AnalystActionListResponse,
    AnalystActionResponse,
)
from backend.app.security.dependencies import (
    get_current_user,
    require_role,
)
from backend.app.audit.audit_service import record_audit_event

router = APIRouter(
    prefix="/api/analyst-actions",
    tags=["Analyst Actions"],
)


VALID_ACTION_TYPES = {
    "ACKNOWLEDGE_ALERT",
    "ACKNOWLEDGE_INCIDENT",
    "START_INVESTIGATION",
    "COMPLETE_INVESTIGATION",
    "ADD_NOTE",
    "UPDATE_STATUS",
    "ASSIGN_INCIDENT",
    "ESCALATE_INCIDENT",
    "RECOMMEND_ACTION",
    "DEFEND_INCIDENT",
    "DEFENSE_ACTION",
    "RESOLVE_INCIDENT",
    "CLOSE_INCIDENT",
    "OTHER",
}


def generate_action_id() -> str:
    return f"ZUKA-ACT-{uuid4().hex[:12].upper()}"


def validate_incident(
    db: Session,
    incident_id: str | None,
) -> None:
    if not incident_id or not incident_id.strip():
        return

    incident = db.scalar(
        select(Incident).where(
            Incident.incident_id == incident_id.strip()
        )
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id.strip()}' not found in database.",
        )


def validate_investigation(
    db: Session,
    investigation_id: str | None,
) -> None:
    if not investigation_id or not investigation_id.strip():
        return

    investigation = db.scalar(
        select(Investigation).where(
            Investigation.investigation_id
            == investigation_id.strip()
        )
    )

    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id.strip()}' not found in database.",
        )


@router.get(
    "",
    response_model=AnalystActionListResponse,
)
def get_analyst_actions(
    incident_id: str | None = None,
    investigation_id: str | None = None,
    action_type: str | None = None,
    analyst_id: int | None = None,
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
    statement = select(AnalystAction)

    if incident_id:
        statement = statement.where(
            AnalystAction.incident_id
            == incident_id.strip()
        )

    if investigation_id:
        statement = statement.where(
            AnalystAction.investigation_id
            == investigation_id.strip()
        )

    if action_type:
        statement = statement.where(
            func.upper(AnalystAction.action_type)
            == action_type.strip().upper()
        )

    if analyst_id is not None:
        statement = statement.where(
            AnalystAction.analyst_id == analyst_id
        )

    if search:
        value = f"%{search.strip()}%"
        statement = statement.where(
            AnalystAction.action_id.ilike(value)
            | AnalystAction.action_type.ilike(value)
            | AnalystAction.description.ilike(value)
            | AnalystAction.result.ilike(value)
            | AnalystAction.incident_id.ilike(value)
            | AnalystAction.investigation_id.ilike(value)
        )

    count_statement = statement.with_only_columns(
        func.count(AnalystAction.id)
    )

    total = db.scalar(count_statement) or 0

    statement = (
        statement
        .order_by(AnalystAction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    items = db.execute(statement).scalars().all()

    return AnalystActionListResponse(
        items=items,
        total=total,
    )


@router.get(
    "/{action_id}",
    response_model=AnalystActionResponse,
)
def get_analyst_action(
    action_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    action = db.scalar(
        select(AnalystAction).where(
            AnalystAction.action_id == action_id
        )
    )

    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyst action not found.",
        )

    return action


@router.post(
    "",
    response_model=AnalystActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analyst_action(
    payload: AnalystActionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    incident_id = (
        payload.incident_id.strip()
        if payload.incident_id
        else None
    )

    investigation_id = (
        payload.investigation_id.strip()
        if payload.investigation_id
        else None
    )

    action_type = payload.action_type.strip().upper()

    if action_type not in VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid action_type. Allowed values: "
                + ", ".join(sorted(VALID_ACTION_TYPES))
            ),
        )

    if not payload.description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action description cannot be empty.",
        )

    # Auto-correlate IDs if one was omitted
    if incident_id and not investigation_id:
        linked_inv = db.scalar(select(Investigation).where(Investigation.incident_id == incident_id))
        if linked_inv:
            investigation_id = linked_inv.investigation_id
    elif investigation_id and not incident_id:
        linked_inv = db.scalar(select(Investigation).where(Investigation.investigation_id == investigation_id))
        if linked_inv and linked_inv.incident_id:
            incident_id = linked_inv.incident_id

    validate_incident(db, incident_id)
    validate_investigation(db, investigation_id)

    action = AnalystAction(
        action_id=generate_action_id(),
        analyst_id=current_user.id,
        incident_id=incident_id,
        investigation_id=investigation_id,
        action_type=action_type,
        description=payload.description.strip(),
        result=(
            payload.result.strip()
            if payload.result
            else None
        ),
        created_at=utc_now(),
    )

    db.add(action)

    now = utc_now()

    # Link action to real Incident lifecycle
    if incident_id:
        incident = db.scalar(select(Incident).where(Incident.incident_id == incident_id))
        if incident:
            if action_type == "RESOLVE_INCIDENT":
                incident.status = "RESOLVED"
                incident.resolved_at = now
                if not incident.resolution_summary:
                    incident.resolution_summary = payload.description.strip()
                if incident.assigned_to_id is None:
                    incident.assigned_to_id = current_user.id
                # Also resolve any linked alert
                if incident.alert_id:
                    alt = db.scalar(select(Alert).where(Alert.alert_id == incident.alert_id))
                    if alt:
                        alt.status = "RESOLVED"
                        alt.updated_at = now
                # Also resolve any linked investigation
                linked_inv = db.scalar(select(Investigation).where(Investigation.incident_id == incident_id))
                if linked_inv and linked_inv.status != "COMPLETED":
                    linked_inv.status = "COMPLETED"
                    linked_inv.completed_at = now
                    if not linked_inv.conclusion:
                        linked_inv.conclusion = payload.description.strip()
            elif action_type == "CLOSE_INCIDENT":
                incident.status = "CLOSED"
                incident.closed_at = now
                if not incident.resolution_summary:
                    incident.resolution_summary = payload.description.strip()
            elif action_type == "ASSIGN_INCIDENT":
                incident.assigned_to_id = current_user.id
            elif action_type == "ESCALATE_INCIDENT":
                incident.priority = "CRITICAL"
                incident.escalation_level = (incident.escalation_level or 0) + 1
                incident.escalation_count = (incident.escalation_count or 0) + 1
            elif action_type == "START_INVESTIGATION":
                incident.status = "INVESTIGATING"
                if incident.assigned_to_id is None:
                    incident.assigned_to_id = current_user.id
                if incident.alert_id:
                    alt = db.scalar(select(Alert).where(Alert.alert_id == incident.alert_id))
                    if alt and alt.status.upper() != "RESOLVED":
                        alt.status = "INVESTIGATING"
                        alt.updated_at = now
            elif action_type == "ACKNOWLEDGE_ALERT":
                incident.status = "ACKNOWLEDGED"
                if incident.alert_id:
                    alt = db.scalar(select(Alert).where(Alert.alert_id == incident.alert_id))
                    if alt:
                        alt.status = "ACKNOWLEDGED"
                        alt.updated_at = now

    # Link action to real Investigation lifecycle
    if investigation_id:
        investigation = db.scalar(select(Investigation).where(Investigation.investigation_id == investigation_id))
        if investigation:
            if action_type == "START_INVESTIGATION":
                investigation.status = "IN_PROGRESS"
                if not investigation.started_at:
                    investigation.started_at = now
            elif action_type in ("DEFEND_INCIDENT",
    "DEFENSE_ACTION",
    "RESOLVE_INCIDENT", "CLOSE_INCIDENT"):
                investigation.status = "COMPLETED"
                if not investigation.completed_at:
                    investigation.completed_at = now
                if not investigation.conclusion:
                    investigation.conclusion = payload.description.strip()
            elif action_type in ("ADD_NOTE", "UPDATE_STATUS"):
                prev_notes = investigation.analyst_notes or ""
                investigation.analyst_notes = (
                    f"{prev_notes}\n[{current_user.username}]: {payload.description.strip()}"
                    if prev_notes
                    else f"[{current_user.username}]: {payload.description.strip()}"
                )

    record_audit_event(
        db,
        user_id=current_user.id,
        action="ANALYST_ACTION_CREATED",
        resource_type="ANALYST_ACTION",
        resource_id=action.action_id,
        description=(
            f"Analyst action {action.action_type} "
            f"was recorded for incident "
            f"{action.incident_id or 'N/A'}."
        ),
        metadata={
            "investigation_id": action.investigation_id,
            "action_type": action.action_type,
        },
        commit=False,
    )

    db.commit()
    db.refresh(action)

    return action
