from typing import Any, Literal
from pydantic import BaseModel, Field


class ParsedIntent(BaseModel):
    intent: str = Field(description="Action intent, e.g. show, list, update, delete, help, metrics")
    entity: str | None = Field(default=None, description="Target entity: alert, incident, user, system")
    id: int | str | None = Field(default=None, description="Extracted entity identifier")
    params: dict[str, Any] = Field(default_factory=dict, description="Additional extracted filters/parameters")
    confidence: float = Field(default=1.0, description="Match confidence")
    source: Literal["rule", "llm_fallback", "unknown"] = "rule"


class ActionButton(BaseModel):
    label: str
    action: str = Field(description="Type: execute_command | navigate | prompt")
    payload: str = Field(description="Command string to run or URL path")
    variant: Literal["primary", "secondary", "danger", "success"] = "secondary"


class ActionCard(BaseModel):
    title: str
    subtitle: str | None = None
    badge: str | None = None
    badge_variant: Literal["critical", "high", "medium", "low", "success", "info"] | None = None
    fields: list[dict[str, str]] = Field(default_factory=list)
    actions: list[ActionButton] = Field(default_factory=list)


class ActionTable(BaseModel):
    headers: list[str]
    rows: list[list[str]]
    total_count: int
    actions: list[ActionButton] = Field(default_factory=list)


class ConfirmationPrompt(BaseModel):
    confirmation_token: str
    prompt: str
    warning: str
    confirm_command: str
    cancel_command: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    confirmed: bool = False
    confirmation_token: str | None = None


class ChatResponse(BaseModel):
    reply: str
    intent: ParsedIntent | None = None
    cards: list[ActionCard] = Field(default_factory=list)
    table: ActionTable | None = None
    quick_chips: list[str] = Field(default_factory=list)
    confirmation: ConfirmationPrompt | None = None
    execution_time_ms: float = 0.0
