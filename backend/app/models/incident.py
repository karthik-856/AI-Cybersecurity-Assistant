from __future__ import annotations
from backend.app.core.time import utc_now

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (UniqueConstraint("incident_id", name="incidents_incident_id_key"),)

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    incident_id: Mapped[str] = mapped_column(
    String(50),
    unique=True,
    nullable=False,
    index=True,
    )


    alert_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey(
            "alerts.alert_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="OPEN",
        index=True,
    )

    assigned_to_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    escalation_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    escalation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    resolution_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    alert = relationship(
        "Alert",
        back_populates="incidents",
    )

    assigned_to = relationship(
        "User",
        foreign_keys=[assigned_to_id],
    )
    investigation = relationship(
    "Investigation",
    back_populates="incident",
    uselist=False,
    cascade="all, delete-orphan",
)
