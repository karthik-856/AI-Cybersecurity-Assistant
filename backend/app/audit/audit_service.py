from __future__ import annotations

from uuid import uuid4
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog


def record_audit_event(
    db: Session,
    *,
    action: str,
    description: str,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = False,
) -> AuditLog:
    """Create a durable ZUKA audit event."""

    event = AuditLog(
        audit_id=f"ZUKA-AUD-{uuid4().hex[:12].upper()}",
        user_id=user_id,
        action=action.strip().upper(),
        resource_type=resource_type.strip().upper() if resource_type else None,
        resource_id=resource_id,
        description=description.strip(),
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata,
    )

    db.add(event)

    if commit:
        db.commit()
        db.refresh(event)

    return event
