from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NetworkEventCreate(BaseModel):
    event_time: datetime

    source_ip: str | None = None
    destination_ip: str | None = None

    source_port: int | None = Field(
        default=None,
        ge=0,
        le=65535,
    )

    destination_port: int | None = Field(
        default=None,
        ge=0,
        le=65535,
    )

    protocol: str | None = None
    direction: str | None = None

    packets: int | None = Field(
        default=None,
        ge=0,
    )

    bytes_count: int | None = Field(
        default=None,
        ge=0,
    )

    flow_duration_ms: int | None = Field(
        default=None,
        ge=0,
    )

    interface_name: str | None = None

    capture_source: str = "unknown"

    event_type: str = "network_flow"

    description: str | None = None

    extra_metadata: dict | None = None


class NetworkEventResponse(NetworkEventCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class NetworkEventStats(BaseModel):
    total_events: int
    unique_source_ips: int
    unique_destination_ips: int
    tcp_events: int
    udp_events: int
    other_protocol_events: int

class CaptureStatusResponse(BaseModel):
    running: bool
    interface: str
    packet_count: int
    flow_count: int
    active_flows: int
    started_at: datetime | None = None
    last_error: str | None = None