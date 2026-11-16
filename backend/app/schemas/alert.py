from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    id: int
    alert_id: str
    detected_at: datetime

    predicted_class: str
    confidence: float
    severity: str
    status: str

    source_ip: str | None = None
    destination_ip: str | None = None
    source_port: int | None = None
    destination_port: int | None = None
    protocol: str | None = None

    dataset_name: str | None = None
    capture_source: str | None = None

    description: str | None = None

    detection_result: dict | None = None
    xai_explanation: dict | None = None

    incident_id: str | None = None
    investigation_id: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]
    total: int


class AlertStatsResponse(BaseModel):
    total: int
    open: int
    acknowledged: int
    investigating: int
    resolved: int
    critical: int
    high: int
    medium: int
    low: int
    info: int
    active_critical: int = 0
    active_high: int = 0

class AlertStatusUpdate(BaseModel):
    status: str