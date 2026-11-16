from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ReportBase(BaseModel):
    title: str = Field(..., max_length=255)
    report_type: str = Field(..., max_length=64)  # "summary", "incident", "investigation", "alert", "detection-xai"
    entity_id: str | None = Field(default=None, max_length=100)
    summary: str | None = None
    format: str = Field(default="PDF", max_length=16)


class ReportCreate(ReportBase):
    parameters_json: dict[str, Any] | None = None


class ReportResponse(ReportBase):
    id: int
    report_id: str
    status: str = "READY"
    file_path: str | None = None
    file_size_bytes: int | None = None
    generated_by_id: int | None = None
    generated_by_username: str | None = None
    parameters_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    page: int = 1
    page_size: int = 10
