from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnalystActionCreate(BaseModel):
    incident_id: str | None = Field(
        default=None,
        max_length=50,
    )
    investigation_id: str | None = Field(
        default=None,
        max_length=50,
    )
    action_type: str = Field(
        min_length=1,
        max_length=50,
    )
    description: str = Field(
        min_length=1,
    )
    result: str | None = None


class AnalystActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_id: str
    analyst_id: int | None
    incident_id: str | None
    investigation_id: str | None
    action_type: str
    description: str
    result: str | None
    created_at: datetime


class AnalystActionListResponse(BaseModel):
    items: list[AnalystActionResponse]
    total: int
