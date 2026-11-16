import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.security.dependencies import get_current_user
from backend.app.assistant_v2.schemas import ChatRequest, ChatResponse, ParsedIntent
from backend.app.assistant_v2.intent_parser import IntentParser
from backend.app.assistant_v2.llm_fallback import LLMFallbackAdapter
from backend.app.assistant_v2.action_handlers import ActionDispatcher
from backend.app.zuka_assistant.rate_limit import enforce_assistant_rate_limit
from backend.app.zuka_assistant.intent_parser import is_knowledge_question


router = APIRouter(
    prefix="/api/assistant-v2",
    tags=["Assistant v2"],
)

intent_parser = IntentParser()
llm_fallback = LLMFallbackAdapter()


COMMAND_AUTOCOMPLETE_SUGGESTIONS = [
    {"label": "show alert <id>", "description": "Inspect detailed alert flow & predictions", "category": "Alerts"},
    {"label": "list alerts", "description": "Display 8 most recent threat detections", "category": "Alerts"},
    {"label": "list critical alerts", "description": "Filter alerts by CRITICAL severity", "category": "Alerts"},
    {"label": "list pending alerts", "description": "Filter alerts with OPEN status", "category": "Alerts"},
    {"label": "acknowledge alert <id>", "description": "Set alert status to ACKNOWLEDGED", "category": "Alerts"},
    {"label": "resolve alert <id>", "description": "Mark alert as RESOLVED", "category": "Alerts"},
    {"label": "dismiss alert <id>", "description": "Flag alert as FALSE POSITIVE", "category": "Alerts"},
    {"label": "escalate alert <id>", "description": "Create an incident from an existing alert", "category": "Alerts"},
    {"label": "show incident <id>", "description": "View incident investigation record", "category": "Incidents"},
    {"label": "list incidents", "description": "List all active security incidents", "category": "Incidents"},
    {"label": "list open incidents", "description": "Filter incidents awaiting resolution", "category": "Incidents"},
    {"label": "investigate incident <id>", "description": "Move incident to INVESTIGATING status", "category": "Incidents"},
    {"label": "resolve incident <id>", "description": "Close and resolve an incident", "category": "Incidents"},
    {"label": "create incident", "description": "Open a new security incident case", "category": "Incidents"},
    {"label": "list users", "description": "Show all registered user accounts", "category": "Users"},
    {"label": "list analysts", "description": "Filter SOC Analyst accounts", "category": "Users"},
    {"label": "list pending users", "description": "Show analyst accounts pending authorization", "category": "Users"},
    {"label": "show user <id>", "description": "Display user profile and login history", "category": "Users"},
    {"label": "approve user <id>", "description": "Authorize pending analyst account", "category": "Users"},
    {"label": "deactivate user <id>", "description": "Revoke login access for user", "category": "Users"},
    {"label": "delete user <id>", "description": "Permanently delete user (with confirmation)", "category": "Users"},
    {"label": "system status", "description": "Check SOC telemetry and component health", "category": "System"},
    {"label": "dashboard stats", "description": "View live SOC KPI metrics overview", "category": "System"},
    {"label": "help", "description": "Show complete command palette and examples", "category": "General"},
]


@router.post("/chat", response_model=ChatResponse)
def handle_assistant_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_assistant_rate_limit),
):
    start_time = time.perf_counter()

    # 1. Primary Engine: Rule-Based Intent Parser (sub-5ms)
    parsed_intent = intent_parser.parse(request.message)

    # 2. Route ordinary questions directly through the shared RAG knowledge
    # engine before any optional LLM intent fallback can time out or guess.
    if (parsed_intent is None or parsed_intent.intent == "unknown") and is_knowledge_question(request.message):
        from backend.app.zuka_assistant.tools import tool_answer_from_knowledge_base
        kb_res = tool_answer_from_knowledge_base(request.message)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return ChatResponse(
            reply=kb_res.get("reply", "I don't have that information. Please contact <chitlakarthik66@gmail.com>."),
            intent=ParsedIntent(intent="KNOWLEDGE_BASE_RAG", entity="knowledge", source="rag", confidence=1.0),
            cards=[],
            table=None,
            quick_chips=["Show alerts", "Show incidents", "Network monitor"],
            confirmation=None,
            execution_time_ms=round(elapsed_ms, 2),
        )

    # 3. Secondary Engine: Optional Free LLM Fallback (only if rule didn't match and enabled)
    if parsed_intent is None and llm_fallback.enabled:
        parsed_intent = llm_fallback.parse(request.message)

    # 3. If still unmatched, query the unified Knowledge Base RAG Engine
    if parsed_intent is None or parsed_intent.intent == "unknown":
        from backend.app.zuka_assistant.tools import tool_answer_from_knowledge_base
        kb_res = tool_answer_from_knowledge_base(request.message)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return ChatResponse(
            reply=kb_res.get("reply", "I don't have that information. Please contact <chitlakarthik66@gmail.com>."),
            intent=ParsedIntent(intent="KNOWLEDGE_BASE_RAG", entity="knowledge", source="rag", confidence=1.0),
            cards=[],
            table=None,
            quick_chips=["Show alerts", "Show incidents", "Network monitor"],
            confirmation=None,
            execution_time_ms=round(elapsed_ms, 2),
        )

    # 4. Action Dispatcher (execute action, check permissions, handle confirmation)
    dispatcher = ActionDispatcher(db=db, current_user=current_user)
    result = dispatcher.dispatch(
        intent=parsed_intent,
        confirmed=request.confirmed,
        confirmation_token=request.confirmation_token,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return ChatResponse(
        reply=result.get("reply", ""),
        intent=parsed_intent,
        cards=result.get("cards", []),
        table=result.get("table"),
        quick_chips=result.get("quick_chips", []),
        confirmation=result.get("confirmation"),
        execution_time_ms=round(elapsed_ms, 2),
    )


@router.get("/suggestions")
def get_command_suggestions():
    """Returns command autocomplete suggestions for the UI."""
    return {"suggestions": COMMAND_AUTOCOMPLETE_SUGGESTIONS}
