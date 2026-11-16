from backend.app.core.time import utc_now
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class NetworkEvent(Base):
    __tablename__ = "network_events"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    event_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    source_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        index=True,
    )

    destination_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        index=True,
    )

    source_port: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    destination_port: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    protocol: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )

    direction: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    packets: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    bytes_count: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    flow_duration_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    interface_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    capture_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="network_flow",
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    extra_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
        index=True,
    )