from __future__ import annotations
from backend.app.core.time import utc_now

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Report(Base):
    """
    Persistent report record in PostgreSQL database.
    Stores metadata and references for executive SOC summaries, incident post-mortems,
    investigation dossiers, and detection/XAI evidence documents.
    """
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    report_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    report_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )  # "summary", "incident", "investigation", "alert", "detection-xai"

    entity_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="READY",
        index=True,
    )

    format: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="PDF",
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    file_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    generated_by_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    generated_by_username: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    parameters_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
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
