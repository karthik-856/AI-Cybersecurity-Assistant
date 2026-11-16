from __future__ import annotations
from backend.app.core.time import utc_now

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    investigation_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    incident_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("incidents.incident_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="NOT_STARTED",
        index=True,
    )

    conclusion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    analyst_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    findings: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_reviewed: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    investigation_steps: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    impact_assessment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    remediation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
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

    incident = relationship(
        "Incident",
        back_populates="investigation",
    )