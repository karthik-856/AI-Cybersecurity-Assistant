from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from backend.app.zuka_assistant.schemas import CurrentContext
from backend.app.zuka_assistant.intent_parser import normalize_question_text

RelevanceCategory = Literal["IN_SCOPE", "RELATED_BUT_UNSUPPORTED", "OUT_OF_SCOPE"]


@dataclass
class RelevanceResult:
    category: RelevanceCategory
    reason: str
    suggested_reply: str | None = None
    refusal_required: bool = False
    topic: str = "general"


# ---------------------------------------------------------------------------
# PATTERNS FOR PROMPT INJECTION & HARMFUL ATTACK WEAPONIZATION
# ---------------------------------------------------------------------------

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(dan|jailbreak|unrestricted|god\s+mode|chaos)\b", re.IGNORECASE),
    re.compile(r"(system\s+prompt|reveal\s+your\s+prompt|print\s+your\s+instructions|leak\s+secrets)", re.IGNORECASE),
    re.compile(r"(reveal|show|dump|print)\s+(all\s+)?(passwords|api\s*keys|jwt_secret|database_url|\.env)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(safety|ethical|guardrails|rules)", re.IGNORECASE),
]

HARMFUL_EXPLOITATION_PATTERNS = [
    re.compile(r"(write|give\s+me|generate|build)\s+(a\s+)?(ransomware|keylogger|trojan|reverse\s+shell|exploit\s+payload|ddos\s+script)", re.IGNORECASE),
    re.compile(r"(how\s+to|help\s+me)\s+(hack|infiltrate|break\s+into|compromise|ddos|attack)\s+(someone|my\s+neighbor|external|target|website|victim)", re.IGNORECASE),
    re.compile(r"(steal|crack|bruteforce)\s+(passwords|wifi\s+handshakes|credentials\s+of|credit\s+cards)", re.IGNORECASE),
    re.compile(r"(bypass|evade)\s+(antivirus|edr|ids)\s+to\s+(attack|infect)", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# PATTERNS FOR RELATED BUT UNSUPPORTED DOMAINS
# ---------------------------------------------------------------------------

RELATED_UNSUPPORTED_PATTERNS = [
    (
        re.compile(r"\b(bluetooth|ble|zigbee|z-wave|rfid|nfc|lorawan|802\.15\.4)\b", re.IGNORECASE),
        "Non-IP wireless/RF hardware protocol",
        "The current Zuka system analyzes IP network flows (layers 3/4) and does not have physical SDR or RF hardware to inspect raw Bluetooth Low Energy, Zigbee, or Z-Wave radio frequency frames."
    ),
    (
        re.compile(r"\b(modify\s+live\s+firewall|block\s+ip\s+in\s+hardware|iptables\s+-A|cisco\s+asa|palo\s+alto)\b", re.IGNORECASE),
        "Live hardware firewall execution",
        "Automated firewall manipulation on production hardware is intentionally restricted to prevent accidental denial of service."
    ),
    (
        re.compile(r"\b(baseband|cellular|5g\s+core|4g\s+lte|sim\s+cloning)\b", re.IGNORECASE),
        "Cellular baseband radio architecture",
        "Cellular baseband protocols operate on telecommunications hardware layers outside the scope of our smart-device IP packet flow monitor."
    ),
    (
        re.compile(r"\b(scada|plc|modbus|profibus|dnp3|industrial\s+control)\b", re.IGNORECASE),
        "Industrial SCADA/PLC protocol",
        "Industrial SCADA and serial bus protocols (Modbus, Profibus) are not currently included in our smart-device network flow feature extractor."
    ),
    (
        re.compile(r"\b(side-channel|dpa|cpa|power\s+analysis|fault\s+injection|chip\s+glitching)\b", re.IGNORECASE),
        "Physical hardware side-channel analysis",
        "Physical silicon side-channel analysis requires physical lab equipment (oscilloscopes, power probes) and is outside network telemetry detection."
    ),
    (
        re.compile(r"\b(ghidra|ida\s+pro|kernel\s+rootkit\s+disassembly|reverse\s+engineer\s+dll)\b", re.IGNORECASE),
        "Deep binary decompilation/disassembly",
        "Zuka focuses on network traffic flow anomaly detection via XGBoost and TreeSHAP, rather than interactive static binary disassembly."
    ),
    (
        re.compile(r"\b(aws\s+iam|azure\s+ad|gcp\s+service\s+account|cloud\s+privilege\s+escalation)\b", re.IGNORECASE),
        "Cloud enterprise IAM identity auditing",
        "Cloud hyperscaler IAM auditing is outside the scope of this smart device and IoT local network traffic security platform."
    ),
]

# ---------------------------------------------------------------------------
# PATTERNS FOR IN-SCOPE CYBERSECURITY, SMART DEVICES, & SOC OPERATIONS
# ---------------------------------------------------------------------------

IN_SCOPE_KEYWORDS = [
    # Smart device & IoT
    "smart device", "smart home", "iot", "sensor", "camera", "ip camera", "smart meter",
    "gateway", "embedded", "connected device", "smart bulb", "thermostat", "smart lock",
    # Supported attack classes
    "dos", "ddos", "denial of service", "distributed denial", "brute force", "bruteforce",
    "port scan", "port scanning", "scan", "scanning", "reconnaissance", "recon",
    "botnet", "mirai", "backdoor", "infiltration", "exploit", "fuzzing", "malware",
    "web attack", "sql injection", "xss", "benign", "attack", "suspicious", "threat",
    # Network traffic & flow features
    "packet", "packets", "network traffic", "traffic", "telemetry", "flow", "network event",
    "duration", "byte rate", "packet rate", "iat", "inter-arrival", "packet size",
    "ip", "port", "protocol", "tcp", "udp", "icmp", "syn flood", "udp flood", "payload",
    # Detection & Machine Learning
    "detect", "detection", "diagnose", "diagnosis", "predict", "prediction", "xgboost",
    "model", "machine learning", "ml", "accuracy", "f1", "f1-score", "precision",
    "recall", "confusion matrix", "classifier", "confidence", "features", "dataset",
    # Explainable AI
    "xai", "shap", "shapley", "tree explainer", "feature importance", "explainability",
    "why was this flagged", "why is this malicious", "interpretability",
    # SOC Platform Operations & SOPs
    "alert", "alerts", "incident", "incidents", "investigation", "investigations",
    "acknowledge", "investigate", "analyst note", "resolve", "resolution", "close",
    "escalate", "escalation", "severity", "critical", "high", "medium", "low", "p1", "p2",
    "dossier", "report", "reports", "pdf", "dashboard", "network monitor", "database",
    "user", "users", "account", "accounts", "settings", "profile", "session", "password", "email",
    "database center", "database centre", "defense department", "incident management", "alert center",
    # Website, project architecture, access, and documented assistant/SOP questions
    "website", "frontend", "front end", "backend", "back end", "api", "asgi", "server",
    "react", "typescript", "vite", "lucide", "fastapi", "python", "uvicorn", "postgresql",
    "sqlalchemy", "alembic", "ollama", "chromadb", "chroma", "qwen", "regex", "architecture",
    "technology stack", "icon library", "authorization", "administrator", "admin", "role", "roles",
    "viewer", "permission", "permissions", "registration", "registered", "authorize", "sop",
    "workflow", "directive", "guardrail", "assistant", "command", "system status", "conclusion",
    "analyst action ledger", "totp", "two-factor", "microcontroller", "antivirus", "firmware",
    "defensive", "boundary", "policy", "answers", "bytes", "feature", "feature represents",
    "audit", "defense", "mitigate", "remediation", "isolate", "quarantine", "recommendation",
    # Assistant identity & greetings
    "zuka", "who are you", "what can you do", "help", "commands", "hi", "hello", "hey",
    "greetings", "clear", "reset", "capabilities",
]

# ---------------------------------------------------------------------------
# PATTERNS FOR OBVIOUS OUT-OF-SCOPE TOPICS
# ---------------------------------------------------------------------------

OUT_OF_SCOPE_TOPICS = [
    (re.compile(r"\b(recipe|cook|bake|ingredients|dinner|lunch|pasta|pizza|cake|soup|curry)\b", re.IGNORECASE), "cooking & recipes"),
    (re.compile(r"\b(movie|cinema|actor|actress|film|box\s*office|hollywood|netflix|spotify|song|lyrics)\b", re.IGNORECASE), "movies & entertainment"),
    (re.compile(r"\b(football|basketball|cricket|nba|fifa|premier\s*league|tennis|world\s*cup)\b", re.IGNORECASE), "sports"),
    (re.compile(r"\b(poem|love\s*letter|dating|horoscope|zodiac|astrology|tarot)\b", re.IGNORECASE), "creative writing / lifestyle"),
    (re.compile(r"\b(weather\s+today|forecast|rain\s+tomorrow|temperature\s+outside)\b", re.IGNORECASE), "weather forecasts"),
    (re.compile(r"\b(buy\s+shoes|clothing|cheap\s+flights|hotel\s+booking|fashion)\b", re.IGNORECASE), "shopping & travel"),
    (re.compile(r"\b(calculus|integral\s+of|derivative\s+of|quadratic\s+formula|history\s+of\s+rome|french\s+revolution)\b", re.IGNORECASE), "non-security academic homework"),
]


def classify_relevance(text: str, context: CurrentContext | None = None) -> RelevanceResult:
    """
    Classify incoming user message with high precision, zero paid API dependency,
    and strict safety boundaries.

    Categories:
    - IN_SCOPE: smart device security, network traffic, ML detection, diagnosis, XAI, SOC SOPs.
    - RELATED_BUT_UNSUPPORTED: legitimate cybersecurity query beyond current project capabilities.
    - OUT_OF_SCOPE: completely unrelated topics (cooking, entertainment, general homework, etc.).
    """
    clean_text = text.strip()
    lower_text = normalize_question_text(clean_text).lower()

    if not clean_text:
        return RelevanceResult(
            category="IN_SCOPE",
            reason="Empty message",
            suggested_reply="Please ask a question about smart device security, network traffic, or active alerts.",
        )

    # 1. PROMPT INJECTION & GUARDRAIL OVERRIDE ATTEMPTS
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(clean_text):
            return RelevanceResult(
                category="IN_SCOPE",  # Handled safely in-scope by strict refusal
                reason="Prompt injection / rule override attempt",
                refusal_required=True,
                suggested_reply=(
                    "⚠️ **Security Notice**: System instructions, security configurations, and credential stores "
                    "cannot be displayed, bypassed, or modified. I am Zuka, an autonomous SOC assistant dedicated "
                    "to defensive smart device network monitoring and incident investigation."
                ),
            )

    # 2. MALICIOUS OFFENSIVE EXPLOITATION REQUESTS
    for pattern in HARMFUL_EXPLOITATION_PATTERNS:
        if pattern.search(clean_text):
            return RelevanceResult(
                category="IN_SCOPE",  # Handled defensively in-scope by refusal and educational guidance
                reason="Harmful offensive action request",
                refusal_required=True,
                suggested_reply=(
                    "🛡️ **Defensive Policy Restriction**: I cannot generate malicious payloads, attack scripts, "
                    "or assist with unauthorized intrusions against external devices or networks. "
                    "My role is strictly defensive: detecting network attacks, analyzing packet telemetry, "
                    "explaining threat mechanisms, and recommending authorized incident response procedures."
                ),
            )

    # 3. CONVERSATIONAL BASICS (Greetings, Clear, Help, Context Pronouns)
    if lower_text in ["hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon", "good evening", "yo", "sup"]:
        return RelevanceResult(
            category="IN_SCOPE",
            reason="Standard greeting",
            topic="greeting",
        )

    if lower_text.rstrip(" ?!.,").strip() in {"thanks", "thank you", "ok", "okay", "got it", "understood"}:
        return RelevanceResult(
            category="IN_SCOPE", reason="Standard conversational acknowledgment", topic="conversation",
        )

    short_text = re.sub(r"[?!.,]+$", "", lower_text).strip()
    if short_text in [
        "clear", "clear chat", "reset", "help", "commands", "what can you do", "who are you",
        "what operations can you do", "what operations do you support", "what can i do",
        "list your operations", "show your operations",
    ]:
        return RelevanceResult(
            category="IN_SCOPE",
            reason="Assistant capability or conversation management",
            topic="system",
        )

    # If contextual pronouns are used while an alert or incident is focused
    if context and (context.incident_id or context.alert_id):
        if any(p in lower_text for p in ["it", "this", "summarize", "investigate", "acknowledge", "details"]):
            return RelevanceResult(
                category="IN_SCOPE",
                reason="Contextual reference to active SOC entity",
                topic="contextual_followup",
            )

    # 4. RELATED BUT UNSUPPORTED DOMAINS
    for pattern, topic_name, limitation_text in RELATED_UNSUPPORTED_PATTERNS:
        if pattern.search(clean_text):
            return RelevanceResult(
                category="RELATED_BUT_UNSUPPORTED",
                reason=f"Cybersecurity topic outside current system scope: {topic_name}",
                topic=topic_name,
                suggested_reply=(
                    f"ℹ️ **Architectural Scope Boundary**: This question touches on **{topic_name}**, which is beyond the current "
                    f"capabilities of this smart-device cybersecurity prototype.\n\n"
                    f"- **Current System Scope**: Monitored IP network flows (layers 3 and 4), multi-class attack detection (XGBoost 13-class model), "
                    f"and TreeSHAP explainability.\n"
                    f"- **Limitation Note**: {limitation_text}\n\n"
                    f"You can explore our supported capabilities using commands like: `Network monitor`, `Show alerts`, or `how does detection work?`."
                ),
            )

    # 5. OBVIOUS OUT-OF-SCOPE TOPICS (Cooking, Entertainment, Sports, Non-security Homework)
    # Important: Verify that it is NOT a cybersecurity query using security terms
    has_security_term = any(term in lower_text for term in [
        "security", "attack", "malware", "device", "network", "packet", "traffic",
        "ids", "firewall", "vulnerability", "threat", "soc", "incident", "alert", "botnet"
    ])

    if not has_security_term:
        for pattern, topic_name in OUT_OF_SCOPE_TOPICS:
            if pattern.search(clean_text):
                return RelevanceResult(
                    category="OUT_OF_SCOPE",
                    reason=f"Unrelated query topic: {topic_name}",
                    topic=topic_name,
                    suggested_reply="I don't have that information. Please contact <chitlakarthik66@gmail.com>.",
                )

    # 6. IN-SCOPE KEYWORDS & OPERATIONAL ACTIONS CHECK
    for kw in IN_SCOPE_KEYWORDS:
        if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", lower_text):
            return RelevanceResult(
                category="IN_SCOPE",
                reason=f"Matched in-scope keyword/topic: '{kw}'",
                topic=kw,
            )

    # 7. CYBERSECURITY GENERAL SAFETY FALLBACK
    # If the user asks a technical or security-related question with unfamiliar words,
    # NEVER falsely reject it! Default to IN_SCOPE so Qwen or knowledge base can evaluate it.
    if has_security_term or any(w in lower_text for w in ["host", "ip", "port", "flow", "log", "sensor", "hardware", "firmware"]):
        return RelevanceResult(
            category="IN_SCOPE",
            reason="Technical/security terminology present; safely preserved in-scope",
            topic="technical_general",
        )

    # 8. GENERAL FALLTHROUGH: unknown facts use the same contact fallback as
    # long unrelated questions; a short phrase must not bypass the scope policy.
    return RelevanceResult(
        category="OUT_OF_SCOPE",
        reason="General non-cybersecurity query",
        topic="unrelated_general",
        suggested_reply="I don't have that information. Please contact <chitlakarthik66@gmail.com>.",
    )
