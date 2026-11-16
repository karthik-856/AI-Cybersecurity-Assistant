import re
from typing import Any
from backend.app.assistant_v2.schemas import ParsedIntent


class IntentParser:
    """
    High-performance rule-based intent parser.
    Uses precompiled regex and entity extractors to deterministically map
    natural language text -> {intent, entity, id, params} in sub-5ms with zero cost.
    """

    def __init__(self):
        # Normalization map for status keywords
        self.status_aliases = {
            "open": "OPEN",
            "pending": "OPEN",
            "unresolved": "OPEN",
            "ack": "ACKNOWLEDGED",
            "acknowledged": "ACKNOWLEDGED",
            "resolved": "RESOLVED",
            "closed": "RESOLVED",
            "false positive": "FALSE_POSITIVE",
            "fp": "FALSE_POSITIVE",
            "dismissed": "FALSE_POSITIVE",
            "investigating": "INVESTIGATING",
            "in progress": "INVESTIGATING",
        }

        self.severity_aliases = {
            "critical": "CRITICAL",
            "high": "HIGH",
            "medium": "MEDIUM",
            "low": "LOW",
            "informational": "LOW",
            "info": "LOW",
        }

    def parse(self, text: str) -> ParsedIntent | None:
        if not text:
            return None

        cleaned = text.strip()
        lower = cleaned.lower()

        # ---------------------------------------------------------
        # 1. HELP & OVERVIEW COMMANDS
        # ---------------------------------------------------------
        if re.search(r"^(help|\?|commands|what can you do|usage|how to use|menu)$", lower):
            return ParsedIntent(intent="help", entity="system", source="rule")

        if re.search(r"^(system status|health|server status|status|ping|soc health)$", lower):
            return ParsedIntent(intent="metrics", entity="system", source="rule")

        if re.search(r"^(dashboard stats|overview|summary|soc summary|metrics|stats|kpi)$", lower):
            return ParsedIntent(intent="metrics", entity="overview", source="rule")

        # ---------------------------------------------------------
        # 2. DESTRUCTIVE ACTIONS (Delete / Deactivate)
        # ---------------------------------------------------------
        # Delete user <id>
        m = re.search(r"^(?:delete|remove|drop)\s+user\s+#?(\d+)", lower)
        if m:
            return ParsedIntent(
                intent="delete",
                entity="user",
                id=int(m.group(1)),
                source="rule"
            )

        # Deactivate / Disable user <id>
        m = re.search(r"^(?:deactivate|disable|suspend|block)\s+user\s+#?(\d+)", lower)
        if m:
            return ParsedIntent(
                intent="update",
                entity="user",
                id=int(m.group(1)),
                params={"is_active": False},
                source="rule"
            )

        # Activate / Enable user <id>
        m = re.search(r"^(?:activate|enable|unblock)\s+user\s+#?(\d+)", lower)
        if m:
            return ParsedIntent(
                intent="update",
                entity="user",
                id=int(m.group(1)),
                params={"is_active": True},
                source="rule"
            )

        # Approve user / analyst <id>
        m = re.search(r"^(?:approve|authorize)\s+(?:user|analyst|soc analyst)?\s*#?(\d+)", lower)
        if m:
            return ParsedIntent(
                intent="update",
                entity="user",
                id=int(m.group(1)),
                params={"action": "approve"},
                source="rule"
            )

        # ---------------------------------------------------------
        # 3. UPDATE / ACTION COMMANDS
        # ---------------------------------------------------------
        # Acknowledge alert <id>
        m = re.search(r"^(?:ack|acknowledge)\s+alert\s+#?(\d+)", lower)
        if m:
            return ParsedIntent(
                intent="update",
                entity="alert",
                id=int(m.group(1)),
                params={"status": "ACKNOWLEDGED"},
                source="rule"
            )

        # Resolve / Close alert <id>
        m = re.search(r"^(?:resolve|close|fix)\s+alert\s+#?(\d+)", lower)
        if m:
            return ParsedIntent(
                intent="update",
                entity="alert",
                id=int(m.group(1)),
                params={"status": "RESOLVED"},
                source="rule"
            )

        # Dismiss / False positive alert <id>
        m = re.search(r"^(?:dismiss|mark false positive|fp)\s+alert\s+#?(\d+)", lower)
        if m:
            return ParsedIntent(
                intent="update",
                entity="alert",
                id=int(m.group(1)),
                params={"status": "FALSE_POSITIVE"},
                source="rule"
            )

        # Generic: update alert <id> status to <status>
        m = re.search(r"^(?:update|change|set)\s+alert\s+#?(\d+)\s+(?:status\s+)?(?:to\s+)?([a-z_ ]+)", lower)
        if m:
            alert_id = int(m.group(1))
            status_text = m.group(2).strip()
            target_status = self.status_aliases.get(status_text, status_text.upper())
            return ParsedIntent(
                intent="update",
                entity="alert",
                id=alert_id,
                params={"status": target_status},
                source="rule"
            )

        # Escalate alert <id> to incident
        m = re.search(r"^(?:escalate|promote|convert)\s+alert\s+#?(\d+)(?:\s+to\s+incident)?", lower)
        if m:
            return ParsedIntent(
                intent="create",
                entity="incident",
                params={"alert_id": int(m.group(1))},
                source="rule"
            )

        # Investigate / Update incident <id>
        m = re.search(r"^(?:investigate|start investigation on)\s+incident\s+#?(\d+)", lower)
        if m:
            return ParsedIntent(
                intent="update",
                entity="incident",
                id=int(m.group(1)),
                params={"status": "INVESTIGATING"},
                source="rule"
            )

        # Resolve incident <id>
        m = re.search(r"^(?:resolve|close)\s+incident\s+#?(\d+)", lower)
        if m:
            return ParsedIntent(
                intent="update",
                entity="incident",
                id=int(m.group(1)),
                params={"status": "RESOLVED"},
                source="rule"
            )

        # Generic: update incident <id> status to <status>
        m = re.search(r"^(?:update|change|set)\s+incident\s+#?(\d+)\s+(?:status\s+)?(?:to\s+)?([a-z_ ]+)", lower)
        if m:
            inc_id = int(m.group(1))
            status_text = m.group(2).strip()
            target_status = self.status_aliases.get(status_text, status_text.upper())
            return ParsedIntent(
                intent="update",
                entity="incident",
                id=inc_id,
                params={"status": target_status},
                source="rule"
            )

        # ---------------------------------------------------------
        # 4. SINGLE ENTITY DISPLAY (Show / Get / View)
        # ---------------------------------------------------------
        # Alert: "show alert 12", "alert 12", "get alert #12", "view alert 12", "alert #12"
        m = re.search(r"^(?:show|get|view|inspect|display|fetch)?\s*alert\s+#?(\d+)$", lower)
        if m:
            return ParsedIntent(
                intent="show",
                entity="alert",
                id=int(m.group(1)),
                source="rule"
            )

        # Incident: "show incident 5", "incident 5", "view incident #5"
        m = re.search(r"^(?:show|get|view|inspect|display|fetch)?\s*incident\s+#?(\d+)$", lower)
        if m:
            return ParsedIntent(
                intent="show",
                entity="incident",
                id=int(m.group(1)),
                source="rule"
            )

        # User: "show user 3", "user 3", "view user admin"
        m = re.search(r"^(?:show|get|view|inspect|display|fetch)?\s*user\s+#?(\d+)$", lower)
        if m:
            return ParsedIntent(
                intent="show",
                entity="user",
                id=int(m.group(1)),
                source="rule"
            )

        m = re.search(r"^(?:show|get|view|inspect)\s+user\s+([a-zA-Z0-9_\-\.@]+)$", lower)
        if m and m.group(1) not in {"all", "list", "analysts", "viewers"}:
            return ParsedIntent(
                intent="show",
                entity="user",
                id=m.group(1),
                source="rule"
            )

        # ---------------------------------------------------------
        # 5. LIST & FILTER COMMANDS
        # ---------------------------------------------------------
        # Alerts listing: "list alerts", "show all alerts", "critical alerts", "list pending alerts", "list open alerts"
        if "alert" in lower and not m:
            params: dict[str, Any] = {}
            for sev_key, sev_val in self.severity_aliases.items():
                if sev_key in lower:
                    params["severity"] = sev_val
                    break
            for stat_key, stat_val in self.status_aliases.items():
                if stat_key in lower:
                    params["status"] = stat_val
                    break
            if re.search(r"(?:list|show|get|all|display|view|fetch)\s+.*alerts?", lower) or lower in {"alerts", "recent alerts"}:
                return ParsedIntent(intent="list", entity="alert", params=params, source="rule")

        # Specific severity/status alerts
        for sev_key, sev_val in self.severity_aliases.items():
            if re.search(rf"\b{sev_key}\b.*alerts?", lower):
                return ParsedIntent(intent="list", entity="alert", params={"severity": sev_val}, source="rule")

        for stat_key, stat_val in self.status_aliases.items():
            if re.search(rf"\b{stat_key}\b.*alerts?", lower):
                return ParsedIntent(intent="list", entity="alert", params={"status": stat_val}, source="rule")

        # Incidents listing: "list incidents", "open incidents", "list open incidents", "all incidents"
        if "incident" in lower:
            params = {}
            for sev_key, sev_val in self.severity_aliases.items():
                if sev_key in lower:
                    params["severity"] = sev_val
                    break
            for stat_key, stat_val in self.status_aliases.items():
                if stat_key in lower:
                    params["status"] = stat_val
                    break
            if re.search(r"(?:list|show|get|all|display|view|fetch)\s+.*incidents?", lower) or lower in {"incidents", "active incidents"}:
                return ParsedIntent(intent="list", entity="incident", params=params, source="rule")

        for sev_key, sev_val in self.severity_aliases.items():
            if re.search(rf"\b{sev_key}\b.*incidents?", lower):
                return ParsedIntent(intent="list", entity="incident", params={"severity": sev_val}, source="rule")

        for stat_key, stat_val in self.status_aliases.items():
            if re.search(rf"\b{stat_key}\b.*incidents?", lower):
                return ParsedIntent(intent="list", entity="incident", params={"status": stat_val}, source="rule")

        # Users listing: "list users", "show users", "all users", "list analysts", "pending analysts"
        if re.search(r"(?:list|show|get|all|display)\s*(?:all\s*)?users", lower) or lower in {"users", "accounts"}:
            params = {}
            if "analyst" in lower:
                params["role"] = "SOC_ANALYST"
            elif "viewer" in lower:
                params["role"] = "VIEWER"
            elif "admin" in lower:
                params["role"] = "ADMIN"
            if "pending" in lower:
                params["pending"] = True
            return ParsedIntent(intent="list", entity="user", params=params, source="rule")

        if re.search(r"(?:list|show)\s+(?:soc\s+)?analysts", lower):
            return ParsedIntent(intent="list", entity="user", params={"role": "SOC_ANALYST"}, source="rule")

        if re.search(r"(?:list|show)\s+pending\s+(?:users|analysts|approvals)", lower):
            return ParsedIntent(intent="list", entity="user", params={"pending": True}, source="rule")

        # ---------------------------------------------------------
        # 6. CREATION SHORTCUTS
        # ---------------------------------------------------------
        if re.search(r"^(?:create|new|open)\s+incident", lower):
            # Check for title
            title_match = re.search(r"(?:titled|with title|name)\s+[\"']?([^\"']+)[\"']?", text)
            title = title_match.group(1) if title_match else "Incident Created via Assistant"
            return ParsedIntent(intent="create", entity="incident", params={"title": title}, source="rule")

        # If no rule matched, return None so it can either use optional free LLM fallback or suggest commands
        return None
