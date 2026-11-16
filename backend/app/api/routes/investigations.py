from __future__ import annotations
from backend.app.core.time import utc_now

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.alert import Alert
from backend.app.models.incident import Incident
from backend.app.models.investigation import Investigation
from backend.app.models.analyst_action import AnalystAction
from backend.app.models.user import User
from backend.app.schemas.investigation import (
    InvestigationConclusionUpdate,
    InvestigationCreate,
    InvestigationFindingsUpdate,
    InvestigationListResponse,
    InvestigationNotesUpdate,
    InvestigationResponse,
    InvestigationStatusUpdate,
    InvestigationWorkspaceUpdate,
)
from backend.app.security.dependencies import (
    get_current_user,
    require_role,
)


router = APIRouter(
    prefix="/api/investigations",
    tags=["Investigation"],
)


# ---------------------------------------------------------------------------
# Investigation status workflow
# ---------------------------------------------------------------------------

VALID_STATUSES = {
    "NOT_STARTED",
    "IN_PROGRESS",
    "ON_HOLD",
    "COMPLETED",
}


ALLOWED_STATUS_TRANSITIONS = {
    "NOT_STARTED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"ON_HOLD", "COMPLETED"},
    "ON_HOLD": {"IN_PROGRESS", "COMPLETED"},
    "COMPLETED": set(),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def generate_investigation_id() -> str:
    """
    Generate a unique human-readable ZUKA investigation identifier.
    """
    return f"ZUKA-INV-{uuid4().hex[:12].upper()}"


def _enrich_investigation(inv: Investigation, db: Session) -> InvestigationResponse:
    alert_id = None
    source_ip = None
    destination_ip = None

    inc = inv.incident if hasattr(inv, "incident") and inv.incident else db.scalar(
        select(Incident).where(Incident.incident_id == inv.incident_id)
    )
    if inc:
        alert_id = inc.alert_id
        alt = inc.alert if hasattr(inc, "alert") and inc.alert else (
            db.scalar(select(Alert).where(Alert.alert_id == inc.alert_id)) if inc.alert_id else None
        )
        if alt:
            source_ip = alt.source_ip
            destination_ip = alt.destination_ip

    return InvestigationResponse(
        id=inv.id,
        investigation_id=inv.investigation_id,
        incident_id=inv.incident_id,
        status=inv.status,
        conclusion=inv.conclusion,
        analyst_notes=inv.analyst_notes,
        findings=getattr(inv, "findings", None),
        evidence_reviewed=getattr(inv, "evidence_reviewed", None),
        investigation_steps=getattr(inv, "investigation_steps", None),
        impact_assessment=getattr(inv, "impact_assessment", None),
        remediation=getattr(inv, "remediation", None),
        started_at=inv.started_at,
        completed_at=inv.completed_at,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        alert_id=alert_id,
        source_ip=source_ip,
        destination_ip=destination_ip,
    )


def get_investigation_or_404(
    db: Session,
    investigation_id: str,
) -> Investigation:
    investigation = db.scalar(
        select(Investigation).where(
            Investigation.investigation_id == investigation_id
        )
    )

    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found.",
        )

    return investigation


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


# ---------------------------------------------------------------------------
# GET /api/investigations
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=InvestigationListResponse,
)
def get_investigations(
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    incident_id: str | None = None,
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
    statement = select(Investigation)

    # Status filter
    if status_filter:
        statement = statement.where(
            func.upper(Investigation.status)
            == status_filter.strip().upper()
        )

    # Incident filter
    if incident_id:
        statement = statement.where(
            Investigation.incident_id == incident_id.strip()
        )

    # Search
    if search:
        search_value = f"%{search.strip()}%"

        statement = statement.where(
            Investigation.investigation_id.ilike(search_value)
            | Investigation.incident_id.ilike(search_value)
            | Investigation.analyst_notes.ilike(search_value)
            | Investigation.conclusion.ilike(search_value)
        )

    # Total count before pagination
    count_statement = statement.with_only_columns(
        func.count(Investigation.id)
    )

    total = db.scalar(count_statement) or 0

    # Pagination
    statement = (
        statement
        .order_by(Investigation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    investigations = db.execute(
        statement
    ).scalars().all()

    return InvestigationListResponse(
        items=[_enrich_investigation(inv, db) for inv in investigations],
        total=total,
    )


# ---------------------------------------------------------------------------
# GET /api/investigations/{investigation_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{investigation_id}",
    response_model=InvestigationResponse,
)
def get_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _enrich_investigation(
        get_investigation_or_404(
            db,
            investigation_id,
        ),
        db,
    )


# ---------------------------------------------------------------------------
# POST /api/investigations
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_investigation(
    payload: InvestigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    # ---------------------------------------------------------
    # Verify the incident exists
    # ---------------------------------------------------------

    incident = get_incident_or_404(
        db,
        payload.incident_id.strip(),
    )

    # ---------------------------------------------------------
    # Prevent duplicate investigation
    # ---------------------------------------------------------

    existing_investigation = db.scalar(
        select(Investigation).where(
            Investigation.incident_id
            == incident.incident_id
        )
    )

    if existing_investigation is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An investigation already exists for this incident: "
                f"{existing_investigation.investigation_id}"
            ),
        )

    # ---------------------------------------------------------
    # Create investigation
    # ---------------------------------------------------------

    investigation = Investigation(
        investigation_id=generate_investigation_id(),
        incident_id=incident.incident_id,
        status="NOT_STARTED",
        conclusion=None,
        analyst_notes=None,
        started_at=None,
        completed_at=None,
    )

    db.add(investigation)
    db.commit()
    db.refresh(investigation)

    return _enrich_investigation(investigation, db)


# ---------------------------------------------------------------------------
# PATCH /api/investigations/{investigation_id}/status
# ---------------------------------------------------------------------------

@router.patch(
    "/{investigation_id}/status",
    response_model=InvestigationResponse,
)
def update_investigation_status(
    investigation_id: str,
    payload: InvestigationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    investigation = get_investigation_or_404(
        db,
        investigation_id,
    )

    new_status = payload.status.strip().upper()
    current_status = investigation.status.upper()

    # ---------------------------------------------------------
    # Validate status
    # ---------------------------------------------------------

    if new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid investigation status. Allowed statuses: "
                "NOT_STARTED, IN_PROGRESS, ON_HOLD, COMPLETED."
            ),
        )

    # Same status = no change
    if new_status == current_status:
        return _enrich_investigation(investigation, db)

    # ---------------------------------------------------------
    # Validate transition
    # ---------------------------------------------------------

    allowed_next = ALLOWED_STATUS_TRANSITIONS.get(
        current_status,
        set(),
    )

    if new_status not in allowed_next:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invalid investigation status transition: "
                f"{current_status} -> {new_status}."
            ),
        )

    # ---------------------------------------------------------
    # Investigation start
    # ---------------------------------------------------------

    if new_status == "IN_PROGRESS":
        if investigation.started_at is None:
            investigation.started_at = utc_now()

    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # Investigation completion
    # ---------------------------------------------------------

    if new_status == "COMPLETED":
        # Required: Analyst must provide a conclusion
        if not investigation.conclusion or not investigation.conclusion.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot complete investigation: An analyst conclusion must be documented before completing.",
            )

        # Auto-populate findings and analyst notes if empty so legacy required fields do not block completion
        if not getattr(investigation, "findings", None) or not investigation.findings.strip():
            investigation.findings = investigation.conclusion.strip()
        if not investigation.analyst_notes or not investigation.analyst_notes.strip():
            investigation.analyst_notes = f"Investigation concluded by {current_user.username}: {investigation.conclusion.strip()}"

        if investigation.started_at is None:
            investigation.started_at = utc_now()

        investigation.completed_at = utc_now()

        action = AnalystAction(
            action_id=f"ZUKA-ACT-{utc_now().strftime('%Y%m%d%H%M%S%f')}",
            incident_id=investigation.incident_id,
            investigation_id=investigation.investigation_id,
            analyst_id=current_user.id,
            action_type="COMPLETE_INVESTIGATION",
            description=f"Investigation {investigation.investigation_id} marked COMPLETED by {current_user.username}.",
        )
        db.add(action)

    investigation.status = new_status

    db.commit()
    db.refresh(investigation)

    return _enrich_investigation(investigation, db)


# ---------------------------------------------------------------------------
# PATCH /api/investigations/{investigation_id}/notes
# ---------------------------------------------------------------------------

@router.patch(
    "/{investigation_id}/notes",
    response_model=InvestigationResponse,
)
def update_investigation_notes(
    investigation_id: str,
    payload: InvestigationNotesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    investigation = get_investigation_or_404(
        db,
        investigation_id,
    )

    notes_val = payload.get_notes()
    if notes_val is not None:
        investigation.analyst_notes = notes_val.strip()

    action = AnalystAction(
        action_id=f"ZUKA-ACT-{utc_now().strftime('%Y%m%d%H%M%S%f')}",
        incident_id=investigation.incident_id,
        investigation_id=investigation.investigation_id,
        analyst_id=current_user.id,
        action_type="ADD_NOTE",
        description=f"Analyst notes updated by {current_user.username}.",
    )
    db.add(action)

    db.commit()
    db.refresh(investigation)

    return _enrich_investigation(investigation, db)


# ---------------------------------------------------------------------------
# PATCH /api/investigations/{investigation_id}/findings
# ---------------------------------------------------------------------------

@router.patch(
    "/{investigation_id}/findings",
    response_model=InvestigationResponse,
)
def update_investigation_findings(
    investigation_id: str,
    payload: InvestigationFindingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    investigation = get_investigation_or_404(
        db,
        investigation_id,
    )

    if payload.findings is not None:
        investigation.findings = payload.findings.strip()

    action = AnalystAction(
        action_id=f"ZUKA-ACT-{utc_now().strftime('%Y%m%d%H%M%S%f')}",
        incident_id=investigation.incident_id,
        investigation_id=investigation.investigation_id,
        analyst_id=current_user.id,
        action_type="ADD_NOTE",
        description=f"Investigation findings saved by {current_user.username}.",
    )
    db.add(action)

    db.commit()
    db.refresh(investigation)

    return _enrich_investigation(investigation, db)


# ---------------------------------------------------------------------------
# PATCH /api/investigations/{investigation_id}/conclusion
# ---------------------------------------------------------------------------

@router.patch(
    "/{investigation_id}/conclusion",
    response_model=InvestigationResponse,
)
def update_investigation_conclusion(
    investigation_id: str,
    payload: InvestigationConclusionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    investigation = get_investigation_or_404(
        db,
        investigation_id,
    )

    conclusion_val = payload.get_conclusion()
    if conclusion_val is None or not conclusion_val.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conclusion cannot be empty.",
        )

    investigation.conclusion = conclusion_val.strip()

    # Also synchronize the conclusion to the linked incident resolution summary if present
    incident = db.scalar(
        select(Incident).where(Incident.incident_id == investigation.incident_id)
    )
    if incident is not None:
        incident.resolution_summary = investigation.conclusion

    action = AnalystAction(
        action_id=f"ZUKA-ACT-{utc_now().strftime('%Y%m%d%H%M%S%f')}",
        incident_id=investigation.incident_id,
        investigation_id=investigation.investigation_id,
        analyst_id=current_user.id,
        action_type="ADD_NOTE",
        description=f"Investigation conclusion saved by {current_user.username}.",
    )
    db.add(action)

    db.commit()
    db.refresh(investigation)

    return _enrich_investigation(investigation, db)


# ---------------------------------------------------------------------------
# PATCH /api/investigations/{investigation_id}/workspace
# ---------------------------------------------------------------------------

@router.patch(
    "/{investigation_id}/workspace",
    response_model=InvestigationResponse,
)
def update_investigation_workspace(
    investigation_id: str,
    payload: InvestigationWorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    investigation = get_investigation_or_404(
        db,
        investigation_id,
    )

    if payload.analyst_notes is not None:
        investigation.analyst_notes = payload.analyst_notes.strip()
    if payload.findings is not None:
        investigation.findings = payload.findings.strip()
    if payload.evidence_reviewed is not None:
        investigation.evidence_reviewed = payload.evidence_reviewed.strip()
    if payload.investigation_steps is not None:
        investigation.investigation_steps = payload.investigation_steps.strip()
    if payload.impact_assessment is not None:
        investigation.impact_assessment = payload.impact_assessment.strip()
    if payload.remediation is not None:
        investigation.remediation = payload.remediation.strip()
    if payload.conclusion is not None:
        investigation.conclusion = payload.conclusion.strip()
        incident = db.scalar(
            select(Incident).where(Incident.incident_id == investigation.incident_id)
        )
        if incident is not None:
            incident.resolution_summary = investigation.conclusion

    action = AnalystAction(
        action_id=f"ZUKA-ACT-{utc_now().strftime('%Y%m%d%H%M%S%f')}",
        incident_id=investigation.incident_id,
        investigation_id=investigation.investigation_id,
        analyst_id=current_user.id,
        action_type="ADD_NOTE",
        description=f"Investigation workspace saved by {current_user.username}.",
    )
    db.add(action)

    db.commit()
    db.refresh(investigation)

    return _enrich_investigation(investigation, db)