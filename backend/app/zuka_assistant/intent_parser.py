from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Any
from backend.app.zuka_assistant.schemas import CurrentContext


# Regex patterns for SOC identifiers
# Incident ID examples: INC-1042, ZUKA-INC-20261016-001, INC1042, INC-1234
INCIDENT_PATTERN = re.compile(
    r"\b(ZUKA-INC-[A-Za-z0-9_-]+|INC-[A-Za-z0-9_-]+|INC\d+)\b",
    re.IGNORECASE,
)

# Alert ID examples: ALT-77, ZUKA-ALT-20261016-001, ZUKA-20261016-001, ALT77
ALERT_PATTERN = re.compile(
    r"\b(ZUKA-ALT-[A-Za-z0-9_-]+|ALT-[A-Za-z0-9_-]+|ALT\d+|ZUKA-(?!INC-|INV-)[A-Za-z0-9_-]+)\b",
    re.IGNORECASE,
)

REPORT_PATTERN = re.compile(r"\b(?:REP|RPT|REPORT)[-_][A-Za-z0-9_-]+\b", re.IGNORECASE)
INVESTIGATION_PATTERN = re.compile(r"\b(?:ZUKA-INV|INV|INVESTIGATION)[-_][A-Za-z0-9_-]+\b", re.IGNORECASE)

PRONOUN_INCIDENT_PATTERN = re.compile(
    r"\b(it|this|this incident|the incident|current incident|here)\b",
    re.IGNORECASE,
)

PRONOUN_ALERT_PATTERN = re.compile(
    r"\b(it|this|this alert|the alert|current alert|linked alert|here)\b",
    re.IGNORECASE,
)

SEVERITY_PATTERN = re.compile(
    r"\b(CRITICAL|HIGH|MEDIUM|LOW)\b",
    re.IGNORECASE,
)

KNOWLEDGE_QUESTION_START = re.compile(
    r"^(?:what|how|why|which|where|who|when|can|could|would|should|is|are|do|does|will)\b",
    re.IGNORECASE,
)

# Normalize common typos and spoken variants before intent parsing. Keep this
# list deliberately small and domain focused so record IDs and user data stay
# untouched.
QUESTION_WORD_CORRECTIONS = {
    "alrt": "alert", "alrets": "alerts", "aler": "alert", "alrets": "alerts",
    "incidnet": "incident", "incidnets": "incidents",
    "investgation": "investigation", "investgations": "investigations",
    "reprots": "reports", "reprot": "report", "usres": "users", "usr": "user",
    "dashbord": "dashboard", "dashbaord": "dashboard",
    "seting": "setting", "setings": "settings", "seetings": "settings",
    "databse": "database", "centre": "center", "cnter": "center",
    "defence": "defense", "departement": "department", "modul": "module",
}
DOMAIN_TERMS = {
    "alert", "alerts", "incident", "incidents", "investigation", "investigations",
    "report", "reports", "user", "users", "dashboard", "settings", "setting",
    "database", "databases", "defense", "department", "module", "network", "investigate",
    "monitor", "severity", "acknowledge", "port", "ports", "scan", "host", "packet",
}
STATUS_TERMS = {
    "open", "acknowledged", "resolved", "closed", "investigating",
    "in_progress", "assigned", "active", "pending", "escalated",
}


def normalize_question_text(text: str) -> str:
    """Correct common website/SOC typos without rewriting identifiers."""
    def correct(match: re.Match[str]) -> str:
        token = match.group(0)
        lowered = token.casefold()
        if lowered in STATUS_TERMS:
            return token
        replacement = QUESTION_WORD_CORRECTIONS.get(lowered)
        if not replacement and token.isalpha() and len(token) >= 4:
            close = get_close_matches(lowered, DOMAIN_TERMS, n=1, cutoff=0.78)
            if close and close[0] != lowered:
                replacement = close[0]
        if not replacement:
            return token
        return replacement.capitalize() if token[:1].isupper() else replacement

    return re.sub(r"\b[\w-]+\b", correct, text.strip())


def is_knowledge_question(text: str) -> bool:
    """Identify ordinary questions that should be answered from RAG, not guessed by the LLM."""
    clean_text = text.strip()
    return bool(clean_text and (KNOWLEDGE_QUESTION_START.search(clean_text) or "?" in clean_text))


class ParsedIntent:
    def __init__(
        self,
        intent: str,
        entity_type: str = "none",
        entity_id: str | None = None,
        params: dict[str, Any] | None = None,
        confidence: float = 1.0,
        raw_text: str = "",
    ):
        self.intent = intent
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.params = params or {}
        self.confidence = confidence
        self.raw_text = raw_text

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "params": self.params,
            "confidence": self.confidence,
        }


def parse_intent(text: str, context: CurrentContext | None = None) -> ParsedIntent:
    """
    Deterministically parse SOC operational user message into structured intent and entities.
    Zero hallucination rule: matches strictly against whitelist of tools and formats.
    """
    raw_input = text.strip()
    clean_text = normalize_question_text(text)
    lower_text = clean_text.lower()

    # Extract potential IDs once and reuse throughout
    inc_match = INCIDENT_PATTERN.search(clean_text)
    alt_match = ALERT_PATTERN.search(clean_text)
    report_match = REPORT_PATTERN.search(clean_text)
    investigation_match = INVESTIGATION_PATTERN.search(clean_text)
    has_record_id = bool(inc_match or alt_match or report_match or investigation_match)

    asks_for_live_or_business_detail = bool(re.search(
        r"\b(price|pricing|cost|subscription|hours|response time|contact|email|count|how many|number of|total|status|latest|current)\b",
        lower_text,
    ))
    asks_about_zuka_soc = bool(
        not asks_for_live_or_business_detail
        and re.search(r"\b(?:what|who)\s+(?:is|are)\s+(?:the\s+)?zuka\s+(?:soc|platform|website)\b", lower_text)
    )
    if asks_about_zuka_soc:
        return ParsedIntent(intent="ABOUT_PLATFORM", entity_type="platform", raw_text=clean_text)

    asks_about_zuka = bool(
        not asks_for_live_or_business_detail
        and (
            re.search(r"\b(?:what|who)\s+(?:is|are)\s+(?:the\s+)?zuka\b", lower_text)
            or re.search(r"\bwhat\s+(?:can|does|will)\s+zuka\s+(?:do|help|handle)\b", lower_text)
            or re.search(r"\bhow\s+does\s+zuka\s+help\b", lower_text)
        )
    )
    if asks_about_zuka:
        return ParsedIntent(intent="ABOUT_ASSISTANT", entity_type="assistant", raw_text=clean_text)

    if lower_text.rstrip(" ?!.") in {"who are you", "what are you"}:
        return ParsedIntent(intent="ABOUT_ASSISTANT", entity_type="assistant", raw_text=clean_text)

    # Explicit requests to open a website module should navigate, not retrieve
    # an explanatory paragraph about that module from RAG.
    module_routes = [
        ("database", "/databases", "Database Center", ("database center", "database centre", "databases")),
        ("settings", "/settings", "Settings", ("settings", "settings page", "settings module")),
        ("users", "/users", "User Management", ("user management", "users", "users page", "users module")),
        ("reports", "/reports", "Reports", ("reports", "reports page", "reports module")),
        ("investigation", "/investigation", "Investigation", ("investigation", "investigations", "investigation page", "investigations page", "investigation module", "investigations module")),
        ("defense", "/defense", "Defense Department", ("defense", "defense department", "defense department page", "defense page", "defense module")),
        ("incidents", "/incidents", "Incident Management", ("incident management", "incident management page", "incidents page", "incidents module")),
        ("alerts", "/alerts", "Alert Center", ("alert center", "alerts page", "alert page", "alerts module")),
        ("dashboard", "/dashboard", "Dashboard", ("dashboard", "dashboard page")),
        ("network monitor", "/network-monitor", "Network Monitor", ("network monitor", "network monitor page")),
    ]
    asks_to_open = bool(re.match(
        r"^(?:(?:please|can|could|would|will)\s+(?:you\s+)?(?:please\s+)?)?"
        r"(?:open|go\s+to|take\s+me\s+to|navigate\s+to)\b",
        lower_text,
    ))
    if asks_to_open:
        for module, route, label, aliases in module_routes:
            if module == "investigation" and has_record_id:
                # "Open/start an investigation for INC-..." or targeting any specific record ID
                # is an operation, while "Open Investigation" without a case ID is navigation.
                continue
            if any(re.search(rf"\b{re.escape(alias)}\b", lower_text) for alias in aliases):
                return ParsedIntent(
                    intent="OPEN_MODULE",
                    entity_type="page",
                    params={"page_route": route, "page_name": label, "module": module},
                    raw_text=clean_text,
                )

    # Database Center status is a live read from the configured database.
    if any(phrase in lower_text for phrase in [
        "database status", "database center status", "database centre status",
        "status of database", "status of the database", "connect to database center",
        "connect to database centre", "connect to the database center", "connect to the database centre",
        "show the database center", "show me the database center", "show database center",
        "show the database centre", "show me the database centre", "show database centre",
        "database center overview", "database centre overview",
    ]):
        return ParsedIntent(intent="DATABASE_STATUS", entity_type="database", raw_text=clean_text)

    # 1. GREETINGS & CONVERSATIONAL INTROS (like ChatGPT & Gemini)
    if (
        re.match(r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening)|yo|sup)\b", lower_text)
        or lower_text in ["hi", "hello", "hey", "hola", "how are you", "how are you?"]
        or lower_text.rstrip(" ?!.,") in ["thanks", "thank you", "ok", "okay", "got it", "understood"]
    ):
        return ParsedIntent(
            intent="GREETING",
            entity_type="system",
            raw_text=clean_text,
        )

    # 2. CLEAR / DELETE CONVERSATION
    if lower_text in ["clear", "clear chat", "delete conversation", "clear conversation", "reset", "reset chat", "new chat", "start over"]:
        return ParsedIntent(
            intent="CLEAR_CHAT",
            entity_type="system",
            raw_text=clean_text,
        )

    # 3. HELP / CAPABILITIES
    if lower_text in ["help", "commands", "what can you do", "what can you do?", "?"] or any(phrase in lower_text for phrase in [
        "what can you do", "what operations can you do", "what operations do you support",
        "what can i do", "list your operations", "show your operations",
    ]):
        return ParsedIntent(
            intent="HELP",
            entity_type="system",
            raw_text=clean_text,
        )

    # 4. TOP ATTACKERS & HOSTS WITH MOST ALERTS
    if any(kw in lower_text for kw in [
        "which host has most alerts",
        "which host has the most alerts",
        "hosts with most alerts",
        "host with most alerts",
        "top attackers",
        "top attacking hosts",
        "top source ips",
        "top source ip",
        "top attacker",
        "who attacked the most",
        "which ip has most alerts",
        "which host has most",
    ]):
        return ParsedIntent(
            intent="TOP_ATTACKERS",
            entity_type="network",
            raw_text=clean_text,
        )

    # 5. COUNT ENTITIES & FILTERED METRICS
    # Examples: "how many alerts are there", "count alerts", "how many critical alerts", "alerts today", "count incidents", "how many open incidents", "how many investigations", "number of alerts", "total alerts"
    is_count_query = (
        lower_text.startswith("count")
        or "how many" in lower_text
        or "number of" in lower_text
        or "total of" in lower_text
        or lower_text in ["alerts count", "incidents count", "total alerts", "total incidents", "alerts today", "incidents today"]
        or (re.search(r"\b(alerts|incidents)\s+(today|this week|24h)\b", lower_text) is not None and not any(kw in lower_text for kw in ["show", "list", "view"]))
    )
    if is_count_query:
        count_entities = []
        for entity_name, pattern in [
            ("alert", r"\balerts?\b"),
            ("incident", r"\bincidents?\b"),
            ("investigation", r"\binvestigations?\b"),
            ("report", r"\breports?\b"),
            ("user", r"\busers?\b"),
            ("network_events", r"\b(?:network\s+)?events?\b|\bflows?\b"),
        ]:
            if re.search(pattern, lower_text):
                count_entities.append(entity_name)
        if len(count_entities) > 1:
            return ParsedIntent(
                intent="COUNT_ENTITY_SUMMARY",
                entity_type="multiple",
                params={"entities": count_entities},
                raw_text=clean_text,
            )

        # Counts about training data are static project facts, not current
        # network-event totals from the operational database.
        if any(term in lower_text for term in ["train", "training", "dataset", "corpus"]):
            return ParsedIntent(
                intent="EXPLAIN_OPERATION",
                entity_type="system",
                params={"question": clean_text, "topic": clean_text},
                raw_text=clean_text,
            )

        if any(word in lower_text for word in ["defense", "defence", "countermeasure"]):
            return ParsedIntent(
                intent="COUNT_DEFENSE_ACTION_TYPES",
                entity_type="defense_action_type",
                raw_text=clean_text,
            )

        if len(count_entities) == 1:
            cnt_entity = count_entities[0]
        elif "network" in lower_text:
            cnt_entity = "network_events"
        else:
            return ParsedIntent(
                intent="EXPLAIN_OPERATION",
                entity_type="system",
                params={"question": clean_text, "topic": clean_text},
                raw_text=clean_text,
            )

        sev_match = SEVERITY_PATTERN.search(clean_text)
        cnt_sev = sev_match.group(1).upper() if sev_match else None

        cnt_status = None
        for st in ["OPEN", "ACKNOWLEDGED", "RESOLVED", "CLOSED", "INVESTIGATING", "IN_PROGRESS", "ASSIGNED"]:
            if re.search(r"\b" + re.escape(st) + r"\b", clean_text, re.IGNORECASE):
                cnt_status = st
                break

        cnt_tf = None
        if "today" in lower_text:
            cnt_tf = "today"
        elif "24h" in lower_text or "24 hours" in lower_text:
            cnt_tf = "24h"
        elif "week" in lower_text:
            cnt_tf = "week"

        return ParsedIntent(
            intent="COUNT_ENTITIES",
            entity_type=cnt_entity,
            params={
                "severity": cnt_sev,
                "status": cnt_status,
                "timeframe": cnt_tf,
            },
            raw_text=clean_text,
        )

    if any(phrase in lower_text for phrase in [
        "defense actions", "defence actions", "available defenses", "available defences",
        "defense department capabilities", "defence department capabilities",
    ]):
        return ParsedIntent(
            intent="COUNT_DEFENSE_ACTION_TYPES",
            entity_type="defense_action_type",
            raw_text=clean_text,
        )

    # 6. RECOMMEND NEXT ACTIONS & PENDING TASKS
    if any(kw in lower_text for kw in ["what should i do", "what are my tasks", "pending tasks", "next steps", "priority tasks", "what to do next", "recommendations", "pending actions"]):
        return ParsedIntent(
            intent="RECOMMEND_ACTIONS",
            entity_type="platform",
            raw_text=clean_text,
        )

    # 7. LIST ACTIVE ALERTS (when no specific alert ID is given)
    if any(kw in lower_text for kw in ["show alerts", "show me alerts", "show me the alerts", "show me all alerts", "list alerts", "list all alerts", "view all alerts", "open alerts", "view alerts", "active alerts", "show open alerts", "get alerts", "what alerts do we have", "what alerts are there"]):
        return ParsedIntent(
            intent="LIST_ALERTS",
            entity_type="alert",
            raw_text=clean_text,
        )

    # 8. LIST ACTIVE INCIDENTS (when no specific incident ID is given)
    if any(kw in lower_text for kw in ["show incidents", "show me incidents", "show me the incidents", "show me all incidents", "list incidents", "list all incidents", "view all incidents", "open incidents", "view incidents", "active incidents", "show open incidents", "get incidents", "what incidents do we have"]):
        return ParsedIntent(
            intent="LIST_INCIDENTS",
            entity_type="incident",
            raw_text=clean_text,
        )

    # 9. LIST INVESTIGATIONS
    if any(kw in lower_text for kw in ["show investigations", "list investigations", "list all investigations", "show all investigations", "view all investigations", "active investigations", "dossiers", "investigation list", "what investigations"]):
        return ParsedIntent(
            intent="LIST_INVESTIGATIONS",
            entity_type="investigation",
            raw_text=clean_text,
        )

    if any(kw in lower_text for kw in ["show reports", "show me reports", "show me the reports", "list reports", "list all reports", "view reports", "recent reports", "what reports are there"]):
        return ParsedIntent(intent="LIST_REPORTS", entity_type="report", raw_text=clean_text)

    if any(kw in lower_text for kw in ["show users", "show me users", "show me the users", "list users", "list all users", "view users", "user list"]):
        return ParsedIntent(intent="LIST_USERS", entity_type="user", raw_text=clean_text)

    # 10. NETWORK MONITOR SUMMARY
    if any(kw in lower_text for kw in ["network monitor", "show network", "network traffic", "traffic status", "network events", "packet traffic"]):
        return ParsedIntent(
            intent="NETWORK_SUMMARY",
            entity_type="network",
            raw_text=clean_text,
        )

    # Extract potential IDs once and reuse throughout
    inc_match = INCIDENT_PATTERN.search(clean_text)
    alt_match = ALERT_PATTERN.search(clean_text)
    report_match = REPORT_PATTERN.search(clean_text)
    investigation_match = INVESTIGATION_PATTERN.search(clean_text)

    # Recognize supported live entity names in the SOC system
    has_live_entity = bool(
        re.search(r"\b(alerts?|incidents?|investigations?|network|events?|flows?|users?|reports?)\b", lower_text)
    )
    has_record_id = bool(inc_match or alt_match or report_match or investigation_match)

    # General reference questions are often phrased as requests to list facts.
    # Specific live alert, incident, and investigation lists were handled above;
    # run this catch-all only when the request contains neither a record ID nor a live entity type.
    if lower_text.startswith("list ") and not has_record_id and not has_live_entity:
        return ParsedIntent(
            intent="EXPLAIN_OPERATION",
            entity_type="system",
            params={"question": clean_text, "topic": clean_text},
            raw_text=clean_text,
        )

    # Check if the message starts with an action verb (write command) or targets a specific record ID
    starts_with_action_verb = bool(
        re.match(
            r"^(?:(?:please|can\s+you(?:\s+please)?|could\s+you(?:\s+please)?|would\s+you(?:\s+please)?)\s+)?"
            r"(?:acknowledge|ack|resolve|close|escalate|assign|reassign|investigate|start\s+investigation|open\s+investigation|add|note|analyst\s+note|set|change|mark)\b",
            lower_text,
        )
    )
    skip_flow_and_nav = bool(starts_with_action_verb or has_record_id)

    if not skip_flow_and_nav:
        # A flow ID is a live operational record, so resolve it before general KB questions.
        flow_match = re.search(r"\b(?:flow|network)\s+event\s*#?\s*(\d+)\b", clean_text, re.IGNORECASE)
        if flow_match:
            return ParsedIntent(
                intent="GET_NETWORK_EVENT",
                entity_type="network_event",
                entity_id=flow_match.group(1),
                raw_text=clean_text,
            )

    if not skip_flow_and_nav:
        # SUMMARIZE APP / PLATFORM / DASHBOARD STATUS
        if any(phrase in lower_text for phrase in [
            "dashboard status", "dashboard health", "status of the dashboard", "dashboard overview",
            "platform status", "platform health", "platform summary", "platform overview", "status of the platform",
            "summarize platform", "summarize the platform", "summarize this platform",
            "system status", "system health", "system summary", "system overview", "status of the system",
            "summarize system", "summarize the system", "summarize this system",
            "app status", "app health", "app summary", "app overview", "status of the app",
            "summarize app", "summarize the app", "summarize this app",
            "soc overview", "soc status", "soc health",
        ]):
            return ParsedIntent(intent="SUMMARIZE_APP", entity_type="platform", raw_text=clean_text)

    if not skip_flow_and_nav:
        # Navigation questions about site modules belong to the website KB (bare 'settings' removed).
        if any(phrase in lower_text for phrase in [
            "database centre", "database center", "settings module", "settings page",
            "user management", "reports module", "reports page", "defense department",
            "investigation department", "incident management", "alert center",
            "open database", "go to database",
        ]):
            return ParsedIntent(
                intent="EXPLAIN_OPERATION",
                entity_type="system",
                params={"question": clean_text, "topic": clean_text},
                raw_text=clean_text,
            )

    cmd_match = re.match(
        r"^(?:(?:please|can\s+you(?:\s+please)?|could\s+you(?:\s+please)?|would\s+you(?:\s+please)?)\s+)?"
        r"(acknowledge|ack|resolve|close|escalate|assign|reassign|investigate|start\s+investigation|open\s+investigation|add\s+(?:a\s+|an\s+)?(?:analyst\s+)?note|note\s+(?:to|on)|analyst\s+note|change\s+severity|set\s+severity|mark)\b",
        lower_text,
    )
    has_matching_target = False
    if cmd_match:
        if alt_match is not None or inc_match is not None:
            has_matching_target = True
        elif cmd_match.group(1) in ["acknowledge", "ack"]:
            has_matching_target = bool(context and (context.alert_id or context.incident_id))
        else:
            has_matching_target = bool(context and context.incident_id)

    is_explicit_command = bool(cmd_match and has_matching_target)

    # Recognize focused records in question matching only through noun-qualified references
    refers_to_focused = bool(
        context and (
            (context.incident_id and re.search(r"\b(?:this|the|current)\s+incident\b", lower_text) is not None)
            or (context.alert_id and re.search(r"\b(?:this|the|current)\s+alert\b", lower_text) is not None)
        )
    )

    # Route general questions without a live record identifier straight to RAG.
    # Operational list/count commands have already been recognized above; keeping
    # this before mutation parsers prevents questions such as "What severity
    # levels exist?" from being mistaken for a request to change severity.
    # Context-targeted commands containing question marks and questions referring
    # to the focused record bypass this check.
    if not is_explicit_command and not has_record_id and not refers_to_focused and is_knowledge_question(clean_text):
        return ParsedIntent(
            intent="EXPLAIN_OPERATION",
            entity_type="system",
            params={"question": clean_text, "topic": clean_text},
            raw_text=clean_text,
        )

    # 11. EXPLAIN WEBSITE OPERATION / WORKFLOW / CYBERSECURITY TECHNICAL TOPICS (SOP Knowledge Base)
    if not is_explicit_command and not has_record_id and not refers_to_focused and (
        lower_text.startswith("how do i")
        or lower_text.startswith("how can i")
        or lower_text.startswith("how to")
        or lower_text.startswith("how does")
        or lower_text.startswith("how is")
        or lower_text.startswith("how should")
        or lower_text.startswith("how are")
        or lower_text.startswith("why are")
        or lower_text.startswith("why do")
        or lower_text.startswith("why would")
        or lower_text.startswith("why is")
        or lower_text.startswith("what does")
        or lower_text.startswith("what is")
        or lower_text.startswith("what are")
        or lower_text.startswith("what characterizes")
        or lower_text.startswith("what information")
        or lower_text.startswith("what happens")
        or lower_text.startswith("what should")
        or lower_text.startswith("what format")
        or lower_text.startswith("which local")
        or lower_text.startswith("which machine")
        or lower_text.startswith("explain")
        or lower_text.startswith("does zuka")
        or lower_text.startswith("are raw")
        or lower_text.startswith("are you")
        or lower_text.startswith("who are you")
        or lower_text.startswith("what can you do")
        or lower_text.startswith("can i upload")
        or lower_text.startswith("can high")
        or lower_text.startswith("can a smart")
        or lower_text.startswith("can automated")
        or lower_text.startswith("can unauthorized")
        or lower_text.startswith("is an ntp")
        or lower_text.startswith("should an analyst")
        or lower_text.startswith("where can i view")
        or lower_text.startswith("where can analysts")
        or "workflow" in lower_text
        or "lifecycle" in lower_text
        or "how does the website" in lower_text
        or "how does the app" in lower_text
        or "how do investigations" in lower_text
        or "tree shap" in lower_text or "treeshap" in lower_text
        or "it looks slow" in lower_text
        or "is it dangerous" in lower_text
        or lower_text in ["fix it", "check device", "what happened?"]
    ):
        return ParsedIntent(
            intent="EXPLAIN_OPERATION",
            entity_type="system",
            params={"question": clean_text, "topic": clean_text},
            raw_text=clean_text,
        )

    # 13. SHOW / SUMMARIZE INCIDENT OR ALERT BY ID (e.g. "show incident INC-12", "summarize incident INC-1042")
    is_summary_command = (
        any(kw in lower_text for kw in ["summarize", "overview", "summary", "show", "view", "details of", "status of", "get"])
        and not any(action_kw in lower_text for action_kw in ["resolve", "close", "escalate", "assign", "change severity", "add note", "add analyst note", "acknowledge"])
    )

    if is_summary_command:
        # Check incident ID
        if inc_match:
            return ParsedIntent(
                intent="SUMMARIZE_INCIDENT",
                entity_type="incident",
                entity_id=inc_match.group(1).upper(),
                raw_text=clean_text,
            )
        # Check alert ID
        if alt_match:
            return ParsedIntent(
                intent="SUMMARIZE_ALERT",
                entity_type="alert",
                entity_id=alt_match.group(1).upper(),
                raw_text=clean_text,
            )
        if report_match:
            return ParsedIntent(
                intent="SUMMARIZE_REPORT",
                entity_type="report",
                entity_id=report_match.group(0).upper(),
                raw_text=clean_text,
            )
        if investigation_match:
            return ParsedIntent(
                intent="SUMMARIZE_INVESTIGATION",
                entity_type="investigation",
                entity_id=investigation_match.group(0).upper(),
                raw_text=clean_text,
            )
        if "investigation" in lower_text:
            return ParsedIntent(intent="SUMMARIZE_INVESTIGATION", entity_type="investigation", raw_text=clean_text)
        if "report" in lower_text:
            return ParsedIntent(intent="SUMMARIZE_REPORT", entity_type="report", raw_text=clean_text)
        # Check pronoun resolution with explicit reference
        if context and context.incident_id and re.search(r"\b(this\s+incident|the\s+incident|current\s+incident|this|it|here)\b", lower_text):
            return ParsedIntent(
                intent="SUMMARIZE_INCIDENT",
                entity_type="incident",
                entity_id=context.incident_id.upper(),
                raw_text=clean_text,
            )
        if context and context.alert_id and re.search(r"\b(this\s+alert|the\s+alert|current\s+alert|this|it|here)\b", lower_text):
            return ParsedIntent(
                intent="SUMMARIZE_ALERT",
                entity_type="alert",
                entity_id=context.alert_id.upper(),
                raw_text=clean_text,
            )
        if "alert" in lower_text:
            return ParsedIntent(intent="SUMMARIZE_ALERT", entity_type="alert", raw_text=clean_text)
        # If user typed "summarize incident" without ID
        if "incident" in lower_text:
            return ParsedIntent(
                intent="SUMMARIZE_INCIDENT",
                entity_type="incident",
                entity_id=None,
                raw_text=clean_text,
            )

    # Guard: Informational or procedural questions should be answered via RAG, not action mutations
    is_question = (
        bool(re.match(r"^(?:what|how|why|which|where|who|when|explain|describe|can|is|does|are|should|do)\b", lower_text))
        or "?" in clean_text
    )

    if is_question and not is_explicit_command:
        # Record-specific questions return summary intent using the matched entity ID
        if inc_match:
            return ParsedIntent(
                intent="SUMMARIZE_INCIDENT",
                entity_type="incident",
                entity_id=inc_match.group(1).upper(),
                raw_text=clean_text,
            )
        if alt_match:
            return ParsedIntent(
                intent="SUMMARIZE_ALERT",
                entity_type="alert",
                entity_id=alt_match.group(1).upper(),
                raw_text=clean_text,
            )
        if report_match:
            return ParsedIntent(
                intent="SUMMARIZE_REPORT",
                entity_type="report",
                entity_id=report_match.group(0).upper(),
                raw_text=clean_text,
            )
        if investigation_match:
            return ParsedIntent(
                intent="SUMMARIZE_INVESTIGATION",
                entity_type="investigation",
                entity_id=investigation_match.group(0).upper(),
                raw_text=clean_text,
            )
        if context and context.incident_id and re.search(r"\b(?:this|the|current)\s+incident\b", lower_text) is not None:
            return ParsedIntent(
                intent="SUMMARIZE_INCIDENT",
                entity_type="incident",
                entity_id=context.incident_id.upper(),
                raw_text=clean_text,
            )
        if context and context.alert_id and re.search(r"\b(?:this|the|current)\s+alert\b", lower_text) is not None:
            return ParsedIntent(
                intent="SUMMARIZE_ALERT",
                entity_type="alert",
                entity_id=context.alert_id.upper(),
                raw_text=clean_text,
            )
        return ParsedIntent(
            intent="EXPLAIN_OPERATION",
            entity_type="system",
            params={"question": clean_text, "topic": clean_text},
            raw_text=clean_text,
        )

    # 4. ACKNOWLEDGE ALERT
    is_ack_command = bool(
        (re.search(r"\backnowledge\b", lower_text)
         or re.search(r"^(?:(?:please|can\s+you(?:\s+please)?|could\s+you(?:\s+please)?|would\s+you(?:\s+please)?)\s+)?ack\b", lower_text)
         or re.search(r"\back\s+(?:alert|alt|this|it|incident|inc)\b", lower_text))
        and not re.match(r"^(?:(?:please|can\s+you(?:\s+please)?|could\s+you(?:\s+please)?|would\s+you(?:\s+please)?)\s+)?(?:add\s+(?:analyst\s+)?note|note\s+(?:to|on)|analyst\s+note)\b", lower_text)
    )
    if is_ack_command:
        target_alert_id = None
        if alt_match:
            target_alert_id = alt_match.group(1).upper()
        elif context and context.alert_id:
            target_alert_id = context.alert_id.upper()
        elif context and context.incident_id:
            # User wants to acknowledge the alert linked to the current incident
            return ParsedIntent(
                intent="ACKNOWLEDGE_ALERT",
                entity_type="alert",
                entity_id=None,
                params={"linked_to_incident": context.incident_id.upper()},
                raw_text=clean_text,
            )
        elif inc_match:
            # User said "acknowledge alert for INC-1042"
            return ParsedIntent(
                intent="ACKNOWLEDGE_ALERT",
                entity_type="alert",
                entity_id=None,
                params={"linked_to_incident": inc_match.group(1).upper()},
                raw_text=clean_text,
            )

        return ParsedIntent(
            intent="ACKNOWLEDGE_ALERT",
            entity_type="alert",
            entity_id=target_alert_id,
            raw_text=clean_text,
        )

    # 5. INVESTIGATE INCIDENT
    if "investigate" in lower_text or "start investigation" in lower_text or "open investigation" in lower_text:
        target_inc_id = None
        if inc_match:
            target_inc_id = inc_match.group(1).upper()
        elif context and context.incident_id:
            target_inc_id = context.incident_id.upper()

        return ParsedIntent(
            intent="INVESTIGATE_INCIDENT",
            entity_type="incident",
            entity_id=target_inc_id,
            raw_text=clean_text,
        )

    # 6. ADD ANALYST NOTE
    # Pattern: add analyst note to INC-1042: note text OR note: text OR note on INC-1042: text
    if "add note" in lower_text or "add a note" in lower_text or "add analyst note" in lower_text or "note to" in lower_text or "note on" in lower_text or "analyst note" in lower_text:
        target_inc_id = None
        if inc_match:
            target_inc_id = inc_match.group(1).upper()
        elif context and context.incident_id:
            target_inc_id = context.incident_id.upper()

        # Extract note text
        note_text = ""
        if ":" in raw_input:
            parts = raw_input.split(":", 1)
            note_text = parts[1].strip()
        else:
            # Try to grab text after keywords
            note_match = re.search(
                r"(?:add\s+(?:a\s+|an\s+)?(?:analyst\s+)?note(?:\s+to|\s+on|\s+here)?(?:\s+[\w-]+)?\s+)(.+)$",
                raw_input,
                re.IGNORECASE,
            )
            if note_match:
                note_text = note_match.group(1).strip()

        return ParsedIntent(
            intent="ADD_NOTE",
            entity_type="incident",
            entity_id=target_inc_id,
            params={"note_text": note_text},
            raw_text=raw_input,
        )

    # 7. ASSIGN INCIDENT
    if "assign" in lower_text or "reassign" in lower_text:
        target_inc_id = None
        if inc_match:
            target_inc_id = inc_match.group(1).upper()
        elif context and context.incident_id:
            target_inc_id = context.incident_id.upper()

        # Extract assigned username or ID
        assignee = None
        assign_match = re.search(r"\b(?:to\s+(?:user\s+)?|user\s+)([A-Za-z0-9_.-]+)", raw_input, re.IGNORECASE)
        if assign_match:
            assignee = assign_match.group(1).strip()

        return ParsedIntent(
            intent="ASSIGN_INCIDENT",
            entity_type="incident",
            entity_id=target_inc_id,
            params={"assignee": assignee},
            raw_text=raw_input,
        )

    # 8. CHANGE SEVERITY
    if "severity" in lower_text or "set severity" in lower_text or "change severity" in lower_text:
        target_inc_id = None
        if inc_match:
            target_inc_id = inc_match.group(1).upper()
        elif context and context.incident_id:
            target_inc_id = context.incident_id.upper()

        sev_match = SEVERITY_PATTERN.search(clean_text)
        new_sev = sev_match.group(1).upper() if sev_match else None

        return ParsedIntent(
            intent="CHANGE_SEVERITY",
            entity_type="incident",
            entity_id=target_inc_id,
            params={"severity": new_sev},
            raw_text=raw_input,
        )

    # 9. RESOLVE INCIDENT
    if "resolve" in lower_text or "mark as resolved" in lower_text:
        target_inc_id = None
        if inc_match:
            target_inc_id = inc_match.group(1).upper()
        elif context and context.incident_id:
            target_inc_id = context.incident_id.upper()

        # Check for summary
        summary = ""
        raw_lower = raw_input.lower()
        if ":" in raw_input:
            summary = raw_input.split(":", 1)[1].strip()
        elif "with summary" in raw_lower:
            idx = raw_lower.find("with summary")
            summary = raw_input[idx + len("with summary"):].strip()

        return ParsedIntent(
            intent="RESOLVE_INCIDENT",
            entity_type="incident",
            entity_id=target_inc_id,
            params={"summary": summary},
            raw_text=raw_input,
        )

    # 10. CLOSE INCIDENT
    if "close" in lower_text or "mark as closed" in lower_text:
        target_inc_id = None
        if inc_match:
            target_inc_id = inc_match.group(1).upper()
        elif context and context.incident_id:
            target_inc_id = context.incident_id.upper()

        return ParsedIntent(
            intent="CLOSE_INCIDENT",
            entity_type="incident",
            entity_id=target_inc_id,
            raw_text=clean_text,
        )

    # 11. ESCALATE INCIDENT
    if "escalate" in lower_text:
        target_inc_id = None
        if inc_match:
            target_inc_id = inc_match.group(1).upper()
        elif context and context.incident_id:
            target_inc_id = context.incident_id.upper()

        return ParsedIntent(
            intent="ESCALATE_INCIDENT",
            entity_type="incident",
            entity_id=target_inc_id,
            raw_text=clean_text,
        )

    # 14. GENERAL CYBERSECURITY INQUIRY
    if any(kw in lower_text for kw in [
        "ddos", "dos attack", "denial of service", "port scan", "reconnaissance",
        "brute force", "credential stuffing", "xai", "explainable ai",
        "confidence score", "who are you", "what are you"
    ]):
        return ParsedIntent(
            intent="CYBER_QUESTION",
            entity_type="system",
            params={"question": clean_text},
            raw_text=clean_text,
        )

    # 13. UNKNOWN INTENT (Zero Hallucination - Never guess)
    return ParsedIntent(
        intent="UNKNOWN",
        entity_type="none",
        entity_id=inc_match.group(1).upper() if inc_match else (alt_match.group(1).upper() if alt_match else None),
        raw_text=clean_text,
    )
