from __future__ import annotations
from backend.app.core.time import utc_now

from datetime import datetime
from typing import Any
from uuid import uuid4
from sqlalchemy.orm import Session

from backend.app.models import AnalystAction, AuditLog, User


def log_assistant_audit(
    db: Session,
    user: User,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    description: str,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Record an audit trail entry for Zuka Assistant operation."""
    audit_record = AuditLog(
        audit_id=f"AUD-{uuid4().hex[:12].upper()}",
        user_id=user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent or "Zuka-Operations-Assistant",
        metadata_json=metadata or {},
        created_at=utc_now(),
    )
    db.add(audit_record)
    return audit_record


def log_analyst_action_entry(
    db: Session,
    user: User,
    action_type: str,
    description: str,
    incident_id: str | None = None,
    investigation_id: str | None = None,
    result: str | None = None,
) -> AnalystAction:
    """Record an official human-authorized analyst action in the operational action ledger."""
    action_record = AnalystAction(
        action_id=f"ACT-{uuid4().hex[:12].upper()}",
        analyst_id=user.id,
        incident_id=incident_id,
        investigation_id=investigation_id,
        action_type=action_type,
        description=description,
        result=result or "SUCCESS",
        created_at=utc_now(),
    )
    db.add(action_record)
    return action_record
