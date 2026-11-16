from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    alert_id: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: str = Field(default="MEDIUM", max_length=10)
    assigned_to_id: int | None = None


class IncidentStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    resolution_summary: str | None = None
    summary: str | None = None

    def get_summary(self) -> str | None:
        return self.resolution_summary if self.resolution_summary is not None else self.summary


class IncidentAssignmentUpdate(BaseModel):
    assigned_to_id: int | None = None


class IncidentEscalationUpdate(BaseModel):
    reason: str | None = None


class IncidentNoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: str
    alert_id: str
    title: str
    description: str | None
    severity: str
    priority: str
    status: str
    assigned_to_id: int | None
    assigned_to_username: str | None = None
    assigned_analyst: str | None = None
    escalation_level: int
    escalation_count: int
    resolution_summary: str | None
    resolved_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    source_ip: str | None = None
    destination_ip: str | None = None
    source_port: int | None = None
    destination_port: int | None = None
    protocol: str | None = None
    dataset_name: str | None = None
    attack_class: str | None = None
    confidence: float | None = None
    investigation_id: str | None = None
    investigation_status: str | None = None
    investigation_conclusion: str | None = None
    affected_asset: str | None = None
    detection_result: dict | None = None
    xai_explanation: dict | None = None


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int


class IncidentStatsResponse(BaseModel):
    total: int
    active: int
    closed: int
    open: int
    acknowledged: int
    investigating: int
    resolved: int
    critical: int
    high: int
    medium: int
    low: int