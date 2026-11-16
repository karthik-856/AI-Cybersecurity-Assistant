from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InvestigationCreate(BaseModel):
    incident_id: str = Field(
        min_length=1,
        max_length=50,
    )


class InvestigationStatusUpdate(BaseModel):
    status: str = Field(
        min_length=1,
        max_length=30,
    )


class InvestigationNotesUpdate(BaseModel):
    analyst_notes: str | None = None
    notes: str | None = None

    def get_notes(self) -> str | None:
        return self.analyst_notes if self.analyst_notes is not None else self.notes


class InvestigationConclusionUpdate(BaseModel):
    conclusion: str | None = None
    analyst_conclusion: str | None = None

    def get_conclusion(self) -> str | None:
        return self.conclusion if self.conclusion is not None else self.analyst_conclusion


class InvestigationFindingsUpdate(BaseModel):
    findings: str | None = None


class InvestigationWorkspaceUpdate(BaseModel):
    analyst_notes: str | None = None
    findings: str | None = None
    conclusion: str | None = None
    evidence_reviewed: str | None = None
    investigation_steps: str | None = None
    impact_assessment: str | None = None
    remediation: str | None = None


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    investigation_id: str
    incident_id: str
    status: str
    conclusion: str | None = None
    analyst_notes: str | None = None
    findings: str | None = None
    evidence_reviewed: str | None = None
    investigation_steps: str | None = None
    impact_assessment: str | None = None
    remediation: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    alert_id: str | None = None
    source_ip: str | None = None
    destination_ip: str | None = None


class InvestigationListResponse(BaseModel):
    items: list[InvestigationResponse]
    total: int