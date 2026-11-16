from __future__ import annotations
from backend.app.core.time import utc_now

import logging
import json
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.security.dependencies import get_current_user
from backend.app.zuka_assistant.confirmation_engine import execute_confirmed_action
from rag_assistant.config import FALLBACK_RESPONSE
from backend.app.zuka_assistant.ollama_adapter import run_ollama_agent
from backend.app.zuka_assistant.relevance import classify_relevance
from backend.app.zuka_assistant.rate_limit import enforce_assistant_rate_limit
from backend.app.zuka_assistant.schemas import (
    ActionConfirmationRequest,
    AssistantCard,
    AssistantResponse,
    ChatMessageRequest,
    PendingAction,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/zuka-assistant",
    tags=["Zuka Operations Assistant"],
)


def _generate_suggestions(incident_id: str | None, alert_id: str | None) -> list[str]:
    suggestions: list[str] = []
    if incident_id:
        suggestions.append(f"summarize incident {incident_id}")
        suggestions.append(f"investigate incident {incident_id}")
        suggestions.append(f"add analyst note to {incident_id}: Verified telemetry")
        suggestions.append(f"escalate incident {incident_id}")
    elif alert_id:
        suggestions.append(f"acknowledge alert {alert_id}")
        suggestions.append(f"summarize alert {alert_id}")
    else:
        suggestions.append("Show alerts")
        suggestions.append("Show incidents")
        suggestions.append("Network monitor")
    return suggestions


@router.post("/chat", response_model=AssistantResponse)
def handle_chat_message(
    req: ChatMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_assistant_rate_limit),
) -> AssistantResponse:
    now_iso = utc_now().isoformat()
    active_inc = req.current_context.incident_id if req.current_context else None
    active_alt = req.current_context.alert_id if req.current_context else None

    # CASE 1: Pre-confirmed Action Payload from Analyst
    if req.confirmed_action:
        result = execute_confirmed_action(db=db, pending=req.confirmed_action, user=user)
        tgt_inc = req.confirmed_action.target_id if req.confirmed_action.target_entity == "incident" else active_inc
        tgt_alt = req.confirmed_action.target_id if req.confirmed_action.target_entity == "alert" else active_alt

        return AssistantResponse(
            reply=result.get("reply", "Action executed."),
            intent=req.confirmed_action.action,
            entity_type=req.confirmed_action.target_entity,
            entity_id=req.confirmed_action.target_id,
            card=result.get("card"),
            confirmation_required=False,
            pending_action=None,
            suggested_prompts=_generate_suggestions(tgt_inc, tgt_alt),
            context={"incident_id": tgt_inc, "alert_id": tgt_alt},
            timestamp=now_iso,
            engine="Ollama (Local LLM)",
        )

    # CASE 2: Ollama Local LLM Agent Execution Loop
    logger.info(f"[ZUKA_ROUTER] Dispatching user prompt to Ollama Agent: '{req.message}'")
    return run_ollama_agent(
        message=req.message,
        db=db,
        user=user,
        current_context=req.current_context,
    )


@router.post("/chat/stream")
def handle_chat_message_stream(
    req: ChatMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_assistant_rate_limit),
):
    """Return grounded website operations and stable unsupported-question fallbacks."""
    relevance = classify_relevance(req.message, req.current_context)

    def events():
        if relevance.category == "OUT_OF_SCOPE" and not relevance.refusal_required and not req.confirmed_action:
            full_reply = relevance.suggested_reply or FALLBACK_RESPONSE
            yield f"data: {json.dumps({'type': 'token', 'text': full_reply}, ensure_ascii=False)}\n\n"
            response = AssistantResponse(
                reply=full_reply,
                intent="UNKNOWN",
                entity_type="system",
                suggested_prompts=["What is Zuka?", "What operations can you do?", "Show alerts"],
                context={
                    "incident_id": req.current_context.incident_id if req.current_context else None,
                    "alert_id": req.current_context.alert_id if req.current_context else None,
                },
                timestamp=utc_now().isoformat(),
                engine="Zuka Knowledge Boundary",
                relevance="OUT_OF_SCOPE",
            )
            yield f"data: {json.dumps({'type': 'done', 'response': response.model_dump()}, ensure_ascii=False)}\n\n"
            return

        # Deterministic website operations and high-confidence FAQ answers have
        # short responses; preserve their structured cards and return them at once.
        response = handle_chat_message(req, user, db, None)
        yield f"data: {json.dumps({'type': 'done', 'response': response.model_dump()}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/confirm", response_model=AssistantResponse)
def confirm_action_direct(
    req: ActionConfirmationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_assistant_rate_limit),
) -> AssistantResponse:
    now_iso = utc_now().isoformat()
    pending = PendingAction(
        action=req.action,
        target_entity=req.target_entity,
        target_id=req.target_id,
        params=req.params,
    )
    result = execute_confirmed_action(db=db, pending=pending, user=user)

    tgt_inc = req.target_id if req.target_entity == "incident" else None
    tgt_alt = req.target_id if req.target_entity == "alert" else None

    return AssistantResponse(
        reply=result.get("reply", "Action executed."),
        intent=req.action,
        entity_type=req.target_entity,
        entity_id=req.target_id,
        card=result.get("card"),
        confirmation_required=False,
        pending_action=None,
        suggested_prompts=_generate_suggestions(tgt_inc, tgt_alt),
        context={"incident_id": tgt_inc, "alert_id": tgt_alt},
        timestamp=now_iso,
        engine="Ollama (Local LLM)",
    )


@router.get("/suggestions")
def get_assistant_suggestions(
    incident_id: str | None = Query(None),
    alert_id: str | None = Query(None),
) -> list[str]:
    return _generate_suggestions(incident_id, alert_id)
