from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.audit.audit_service import record_audit_event
from backend.app.database.session import get_db
from backend.app.models.audit_log import AuditLog
from backend.app.models import User
from backend.app.security.dependencies import get_current_user


router = APIRouter(
    prefix="/api/database",
    tags=["Audit History"],
)


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role.name != "ADMIN":
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit History is available only to administrators.",
        )
    return current_user


def serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def serialize_audit(event: AuditLog) -> dict[str, Any]:
    return {
        "id": event.id,
        "audit_id": event.audit_id,
        "user_id": event.user_id,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "description": event.description,
        "ip_address": event.ip_address,
        "user_agent": event.user_agent,
        "metadata_json": event.metadata_json,
        "created_at": serialize(event.created_at),
    }


@router.get("/audit")
def get_audit_history(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, Any]:
    """Return persisted ZUKA audit history for Database Center."""

    conditions = []

    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            or_(
                AuditLog.audit_id.ilike(term),
                AuditLog.action.ilike(term),
                AuditLog.resource_type.ilike(term),
                AuditLog.resource_id.ilike(term),
                AuditLog.description.ilike(term),
                AuditLog.ip_address.ilike(term),
            )
        )

    if action and action.strip():
        conditions.append(
            AuditLog.action == action.strip().upper()
        )

    if resource_type and resource_type.strip():
        conditions.append(
            AuditLog.resource_type == resource_type.strip().upper()
        )

    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)

    total_stmt = select(func.count()).select_from(AuditLog)
    rows_stmt = (
        select(AuditLog)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
    )

    if conditions:
        total_stmt = total_stmt.where(*conditions)
        rows_stmt = rows_stmt.where(*conditions)

    total = int(db.scalar(total_stmt) or 0)
    events = list(db.scalars(rows_stmt).all())
    records = [serialize_audit(event) for event in events]

    return {
        "section": "audit",
        "table": "audit_logs",
        "available": True,
        "columns": [
            "id",
            "audit_id",
            "user_id",
            "action",
            "resource_type",
            "resource_id",
            "description",
            "ip_address",
            "user_agent",
            "metadata_json",
            "created_at",
        ],
        "records": records,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/audit/{audit_id}")
def get_audit_event(
    audit_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, Any]:
    event = db.scalar(
        select(AuditLog).where(AuditLog.audit_id == audit_id)
    )

    if event is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit event not found.",
        )

    return serialize_audit(event)
