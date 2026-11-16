from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any


def is_llm_enabled() -> bool:
    return os.getenv("ZUKA_LLM_ENABLED", "false").strip().lower() in ("true", "1", "yes")


def get_llm_endpoint() -> str:
    return os.getenv("ZUKA_LLM_URL", "http://localhost:11434/api/generate")


def get_llm_model() -> str:
    return os.getenv("ZUKA_LLM_MODEL", "llama3.2")


def llm_classify_intent(user_text: str, context_info: str = "") -> dict[str, Any] | None:
    """
    Optional free local LLM classifier fallback for fuzzy requests.
    Returns JSON dictionary if successful, or None to fall back to rule-based engine.
    """
    if not is_llm_enabled():
        return None

    prompt = f"""You are the classification component for Zuka Operations Assistant.
Classify the user SOC command into exact JSON with keys:
"intent": one of ["SUMMARIZE_INCIDENT", "SUMMARIZE_APP", "ACKNOWLEDGE_ALERT", "INVESTIGATE_INCIDENT", "ADD_NOTE", "ASSIGN_INCIDENT", "CHANGE_SEVERITY", "RESOLVE_INCIDENT", "CLOSE_INCIDENT", "ESCALATE_INCIDENT", "HELP", "UNKNOWN"],
"entity_type": one of ["incident", "alert", "platform", "none"],
"entity_id": string ID if mentioned or null,
"params": object with any parameters (e.g. note_text, assignee, severity, summary).

Context: {context_info}
User Message: "{user_text}"

Respond with ONLY valid JSON and no other text."""

    try:
        payload = json.dumps({
            "model": get_llm_model(),
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }).encode("utf-8")

        req = urllib.request.Request(
            get_llm_endpoint(),
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_response = data.get("response", "")
            return json.loads(raw_response)
    except Exception:
        # Graceful fallback to deterministic parsing on any LLM error or timeout
        return None


def llm_rephrase_facts(raw_reply: str, data: dict[str, Any]) -> str:
    """
    Optional free LLM rewriter to give conversational polish,
    strictly restricted to fetched database facts.
    """
    if not is_llm_enabled():
        return raw_reply

    prompt = f"""You are Zuka, a professional SOC Operations Assistant.
Rewrite the following verified system facts into a friendly, concise, natural reply for the analyst.
CRITICAL RULE: DO NOT INVENT ANY INFORMATION. USE ONLY THE FACTS PROVIDED BELOW.

Facts:
{json.dumps(data, indent=2)}

Original verified summary:
{raw_reply}

Short, professional response:"""

    try:
        payload = json.dumps({
            "model": get_llm_model(),
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")

        req = urllib.request.Request(
            get_llm_endpoint(),
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rephrased = data.get("response", "").strip()
            return rephrased if rephrased else raw_reply
    except Exception:
        return raw_reply
