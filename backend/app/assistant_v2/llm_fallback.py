import json
import os
import re
import urllib.request
import urllib.error
from backend.app.assistant_v2.schemas import ParsedIntent


ALLOWED_INTENTS = {"show", "list", "update", "delete", "create", "metrics", "help"}
ALLOWED_ENTITIES = {"alert", "incident", "user", "system", "overview"}


class LLMFallbackAdapter:
    """
    Optional free local LLM fallback (Ollama) used ONLY when rule-based parser cannot match.
    Enforces strict structured JSON output schema.
    Can be completely disabled via environment variable ASSISTANT_LLM_ENABLED=false.
    """

    def __init__(self):
        self.enabled = os.getenv("ASSISTANT_LLM_ENABLED", "false").lower() in {"true", "1", "yes"}
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
        self.timeout = float(os.getenv("ASSISTANT_LLM_TIMEOUT", "2.0"))

    def parse(self, text: str) -> ParsedIntent | None:
        if not self.enabled or not text:
            return None

        prompt = (
            "You are an intent parser for a cybersecurity operations center. "
            "Extract the user's intent into STRICT JSON format with no markdown, explanation, or conversational text.\n\n"
            "Allowed intents: show, list, update, delete, create, metrics, help, unknown\n"
            "Allowed entities: alert, incident, user, system, overview\n\n"
            "JSON Format:\n"
            "{\n"
            '  "intent": "show|list|update|delete|create|metrics|help|unknown",\n'
            '  "entity": "alert|incident|user|system|overview|null",\n'
            '  "id": 123 or null,\n'
            '  "params": {}\n'
            "}\n\n"
            f'User command: "{text}"\n'
            "JSON:"
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0,
                "num_predict": 100,
            },
        }

        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_response = data.get("response", "").strip()

                # Clean markdown blocks if present
                clean_json = re.sub(r"^```json\s*|\s*```$", "", raw_response, flags=re.MULTILINE).strip()
                parsed = json.loads(clean_json)

                intent = str(parsed.get("intent", "")).lower()
                entity = parsed.get("entity")
                if entity:
                    entity = str(entity).lower()
                entity_id = parsed.get("id")
                params = parsed.get("params") or {}

                if intent in ALLOWED_INTENTS:
                    if entity and entity not in ALLOWED_ENTITIES:
                        entity = None

                    # Validate ID
                    clean_id = None
                    if entity_id is not None:
                        try:
                            clean_id = int(entity_id)
                        except (ValueError, TypeError):
                            clean_id = str(entity_id)

                    return ParsedIntent(
                        intent=intent,
                        entity=entity,
                        id=clean_id,
                        params=params if isinstance(params, dict) else {},
                        confidence=0.85,
                        source="llm_fallback",
                    )
        except Exception:
            # LLM offline, timed out, or JSON invalid; fail silently to safe fallback
            return None

        return None
