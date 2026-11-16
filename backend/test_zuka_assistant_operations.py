import pytest
from backend.app.zuka_assistant.intent_parser import parse_intent
from backend.app.zuka_assistant.schemas import CurrentContext


def test_greeting_intent():
    parsed = parse_intent("hi")
    assert parsed.intent == "GREETING"
    parsed_hello = parse_intent("Hello Zuka, how are you?")
    assert parsed_hello.intent == "GREETING"


def test_clear_chat_intent():
    parsed = parse_intent("clear chat")
    assert parsed.intent == "CLEAR_CHAT"


def test_list_alerts_intent():
    parsed = parse_intent("show open alerts")
    assert parsed.intent == "LIST_ALERTS"


def test_list_incidents_intent():
    parsed = parse_intent("show incidents")
    assert parsed.intent == "LIST_INCIDENTS"


def test_network_summary_intent():
    parsed = parse_intent("network monitor")
    assert parsed.intent == "NETWORK_SUMMARY"


def test_recommend_actions_intent():
    parsed = parse_intent("what should I do next?")
    assert parsed.intent == "RECOMMEND_ACTIONS"


def test_explain_operation_intent():
    parsed = parse_intent("how do investigations work?")
    assert parsed.intent == "EXPLAIN_OPERATION"


def test_cyber_question_intent():
    parsed = parse_intent("what is a ddos attack?")
    assert parsed.intent in ["CYBER_QUESTION", "EXPLAIN_OPERATION"]


def test_summarize_incident_explicit():
    parsed = parse_intent("summarize incident INC-1042")
    assert parsed.intent == "SUMMARIZE_INCIDENT"
    assert parsed.entity_id == "INC-1042"


def test_summarize_incident_zuka_prefix():
    parsed = parse_intent("summarize incident ZUKA-INC-20261016-001")
    assert parsed.intent == "SUMMARIZE_INCIDENT"
    assert parsed.entity_id == "ZUKA-INC-20261016-001"


def test_summarize_incident_pronoun_context():
    ctx = CurrentContext(incident_id="INC-1042")
    parsed = parse_intent("summarize it", context=ctx)
    assert parsed.intent == "SUMMARIZE_INCIDENT"
    assert parsed.entity_id == "INC-1042"


def test_summarize_app():
    parsed = parse_intent("summarize this app")
    assert parsed.intent == "SUMMARIZE_APP"
    assert parsed.entity_type == "platform"


def test_acknowledge_alert_explicit():
    parsed = parse_intent("acknowledge alert ALT-77")
    assert parsed.intent == "ACKNOWLEDGE_ALERT"
    assert parsed.entity_id == "ALT-77"


def test_acknowledge_alert_pronoun_context():
    ctx = CurrentContext(alert_id="ALT-77")
    parsed = parse_intent("acknowledge it", context=ctx)
    assert parsed.intent == "ACKNOWLEDGE_ALERT"
    assert parsed.entity_id == "ALT-77"


def test_acknowledge_alert_from_incident_context():
    ctx = CurrentContext(incident_id="INC-1042")
    parsed = parse_intent("acknowledge linked alert", context=ctx)
    assert parsed.intent == "ACKNOWLEDGE_ALERT"
    assert parsed.params.get("linked_to_incident") == "INC-1042"


def test_investigate_incident_explicit():
    parsed = parse_intent("investigate incident INC-1042")
    assert parsed.intent == "INVESTIGATE_INCIDENT"
    assert parsed.entity_id == "INC-1042"


def test_investigate_incident_context():
    ctx = CurrentContext(incident_id="INC-1042")
    parsed = parse_intent("start investigation", context=ctx)
    assert parsed.intent == "INVESTIGATE_INCIDENT"
    assert parsed.entity_id == "INC-1042"


def test_add_analyst_note():
    parsed = parse_intent("add analyst note to INC-1042: Inbound port scan verified from external IP")
    assert parsed.intent == "ADD_NOTE"
    assert parsed.entity_id == "INC-1042"
    assert "Inbound port scan" in parsed.params.get("note_text", "")


def test_assign_incident():
    parsed = parse_intent("assign incident INC-1042 to admin")
    assert parsed.intent == "ASSIGN_INCIDENT"
    assert parsed.entity_id == "INC-1042"
    assert parsed.params.get("assignee") == "admin"


def test_change_severity():
    parsed = parse_intent("change severity of INC-1042 to CRITICAL")
    assert parsed.intent == "CHANGE_SEVERITY"
    assert parsed.entity_id == "INC-1042"
    assert parsed.params.get("severity") == "CRITICAL"


def test_resolve_incident():
    parsed = parse_intent("resolve incident INC-1042 with summary: Confirmed blocked IP at boundary firewall")
    assert parsed.intent == "RESOLVE_INCIDENT"
    assert parsed.entity_id == "INC-1042"
    assert "Confirmed blocked IP" in parsed.params.get("summary", "")


def test_close_incident():
    parsed = parse_intent("close incident INC-1042")
    assert parsed.intent == "CLOSE_INCIDENT"
    assert parsed.entity_id == "INC-1042"


def test_escalate_incident():
    parsed = parse_intent("escalate incident INC-1042")
    assert parsed.intent == "ESCALATE_INCIDENT"
    assert parsed.entity_id == "INC-1042"


def test_help_intent():
    parsed = parse_intent("what can you do")
    assert parsed.intent == "HELP"


def test_unknown_intent():
    parsed = parse_intent("pizza delivery order 4567")
    assert parsed.intent == "UNKNOWN"


def test_count_alerts_intent():
    parsed = parse_intent("how many alerts are there")
    assert parsed.intent == "COUNT_ENTITIES"
    assert parsed.entity_type == "alert"


def test_count_critical_alerts_intent():
    parsed = parse_intent("how many critical alerts")
    assert parsed.intent == "COUNT_ENTITIES"
    assert parsed.entity_type == "alert"
    assert parsed.params.get("severity") == "CRITICAL"


def test_count_alerts_today_intent():
    parsed = parse_intent("alerts today")
    assert parsed.intent == "COUNT_ENTITIES"
    assert parsed.entity_type == "alert"
    assert parsed.params.get("timeframe") == "today"


def test_count_open_incidents_intent():
    parsed = parse_intent("how many open incidents")
    assert parsed.intent == "COUNT_ENTITIES"
    assert parsed.entity_type == "incident"
    assert parsed.params.get("status") == "OPEN"


def test_count_investigations_intent():
    parsed = parse_intent("how many investigations")
    assert parsed.intent == "COUNT_ENTITIES"
    assert parsed.entity_type == "investigation"


def test_top_attackers_intent():
    parsed = parse_intent("which host has most alerts")
    assert parsed.intent == "TOP_ATTACKERS"
    assert parsed.entity_type == "network"


def test_who_attacked_the_most_intent():
    parsed = parse_intent("who attacked the most")
    assert parsed.intent == "TOP_ATTACKERS"


def test_show_incident_by_id():
    parsed = parse_intent("show incident INC-12")
    assert parsed.intent == "SUMMARIZE_INCIDENT"
    assert parsed.entity_id == "INC-12"


def test_show_alert_by_id():
    parsed = parse_intent("show alert ALT-77")
    assert parsed.intent == "SUMMARIZE_ALERT"
    assert parsed.entity_id == "ALT-77"


def test_knowledge_base_lookup(monkeypatch):
    # Exercise the adapter contract deterministically; a live LLM is a
    # separately configured integration, not a unit-test dependency.
    from backend.app.zuka_assistant import rag_engine
    monkeypatch.setattr(rag_engine, "query_rag", lambda question: {
        "formatted_answer": "To resolve an incident the linked investigation must be COMPLETED.",
        "sources": ["Incident workflow"], "is_fallback": False,
    })
    from backend.app.zuka_assistant.tools import tool_answer_from_knowledge_base
    ans = tool_answer_from_knowledge_base("how do I resolve an incident")
    assert "resolve" in ans["reply"].lower()
    assert "COMPLETED" in ans["reply"]


def test_knowledge_base_not_found(monkeypatch):
    from backend.app.zuka_assistant import rag_engine
    from rag_assistant.config import FALLBACK_RESPONSE
    monkeypatch.setattr(rag_engine, "query_rag", lambda question: {
        "answer": FALLBACK_RESPONSE, "sources": [], "is_fallback": True,
    })
    from backend.app.zuka_assistant.tools import tool_answer_from_knowledge_base
    ans = tool_answer_from_knowledge_base("how do I bake a cake?")
    assert "I don't have that information" in ans["reply"]


def test_ollama_agent_greeting():
    from backend.app.zuka_assistant.ollama_adapter import run_ollama_agent
    from backend.app.models.user import User

    fake_user = User(username="karthik", email="karthik@test.com")
    resp = run_ollama_agent(message="hi", db=None, user=fake_user)
    assert resp.intent == "GREETING"
    assert "Hi karthik, I'm Zuka. What do you need?" in resp.reply
    assert "Ollama" in resp.engine
    assert resp.suggested_prompts == ["Show alerts", "Show incidents", "Network monitor"]


def test_ollama_tools_schema_definition():
    from backend.app.zuka_assistant.ollama_adapter import OLLAMA_TOOLS
    tool_names = [t["function"]["name"] for t in OLLAMA_TOOLS]
    assert "count_entities" in tool_names
    assert "get_dashboard_summary" in tool_names
    assert "get_top_attackers" in tool_names
    assert "get_incident_details" in tool_names
    assert "get_alert_details" in tool_names
    assert "search_knowledge_base" in tool_names
    assert "propose_action" in tool_names
