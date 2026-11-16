from __future__ import annotations

import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


def _friendly_module_names(text: str) -> str:
    """Render internal route fragments as website labels in assistant replies."""
    labels = {
        "alerts": "Alert Center",
        "alert": "Alert Center",
        "incidents": "Incident Management",
        "incident": "Incident Management",
        "reports": "Reports",
        "report": "Reports",
        "settings": "Settings",
        "databases": "Database Center",
        "database-center": "Database Center",
        "database-centre": "Database Center",
        "database_center": "Database Center",
        "database_centre": "Database Center",
        "users": "User Management",
        "user": "User Management",
        "investigations": "Investigation",
        "investigation": "Investigation",
        "defense": "Defense Department",
        "defense-department": "Defense Department",
        "alert-center": "Alert Center",
        "incident-management": "Incident Management",
        "user-management": "User Management",
        "dashboard": "Dashboard",
        "network-monitor": "Network Monitor",
        "network_monitor": "Network Monitor",
    }
    pattern = re.compile(
        r"(?<![\w.:/\\#?&=])[/\\]+(" + "|".join(sorted(map(re.escape, labels), key=len, reverse=True)) + r")(?![\w-])",
        re.IGNORECASE,
    )
    route = r"(?<![\w.:/\\#?&=])[/\\]+(?:" + "|".join(sorted(map(re.escape, labels), key=len, reverse=True)) + r")(?![\w-])"
    text = re.sub(r"(?i)\b(Database Center)\s+is\s+at\s+`?" + route + r"`?\s+and\s+is\s+available", r"\1 is available", text)
    text = re.sub(r"(?i)\b(Database Center|Settings|Alert Center|Incident Management|Reports|User Management|Investigation|Dashboard|Network Monitor)\s+(?:is\s+)?at\s+`?" + route + r"`?", r"\1", text)
    text = re.sub(r"\(\s*`?" + route + r"`?\s*\)", "", text)
    return pattern.sub(lambda match: labels[match.group(1).lower()], text)


class CurrentContext(BaseModel):
    incident_id: str | None = None
    alert_id: str | None = None
    page_route: str | None = None


class PendingAction(BaseModel):
    action: str = Field(description="Whitelisted action name to execute")
    target_entity: str = Field(description="Target entity type: incident, alert, or investigation")
    target_id: str = Field(description="Target identifier, e.g. INC-1042 or ALT-77")
    params: dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    preview_changes: dict[str, Any] = Field(default_factory=dict, description="Preview of field modifications")
    summary: str = Field(default="", description="Human-readable summary of what will change")


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, description="User question or operational command")
    conversation_id: str | None = None
    current_context: CurrentContext | None = None
    confirmed_action: PendingAction | None = None


class ActionConfirmationRequest(BaseModel):
    action: str
    target_entity: str
    target_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None


class AssistantCard(BaseModel):
    card_type: Literal[
        "incident_summary",
        "alert_card",
        "investigation_card",
        "confirmation_prompt",
        "action_success",
        "error_card",
        "help_card",
        "list_card",
        "info_card",
        "none",
    ] = "none"
    data: dict[str, Any] = Field(default_factory=dict)


class AssistantResponse(BaseModel):
    reply: str
    intent: str
    entity_type: str
    entity_id: str | None = None
    page_route: str | None = None
    card: AssistantCard | None = None
    confirmation_required: bool = False
    pending_action: PendingAction | None = None
    suggested_prompts: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    engine: str = "rule-based"
    relevance: Literal["IN_SCOPE", "RELATED_BUT_UNSUPPORTED", "OUT_OF_SCOPE"] = "IN_SCOPE"
    timestamp: str

    @field_validator("reply", mode="before")
    @classmethod
    def use_friendly_module_names(cls, value: Any) -> Any:
        return _friendly_module_names(value) if isinstance(value, str) else value
