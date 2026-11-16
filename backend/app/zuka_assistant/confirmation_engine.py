from __future__ import annotations

from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.alert import Alert
from backend.app.models.incident import Incident
from backend.app.models.user import User
from backend.app.zuka_assistant.intent_parser import ParsedIntent
from backend.app.zuka_assistant.schemas import AssistantCard, AssistantResponse, PendingAction
from backend.app.zuka_assistant.tools import (
    tool_acknowledge_alert,
    tool_add_note,
    tool_assign_incident,
    tool_change_severity,
    tool_close_incident,
    tool_escalate_incident,
    tool_investigate_incident,
    tool_resolve_incident,
)


def build_confirmation_card(
    db: Session,
    parsed: ParsedIntent,
    user: User,
) -> tuple[PendingAction | None, AssistantCard | None, str]:
    """
    Generate change preview and safety confirmation for write actions before execution.
    Returns (PendingAction, AssistantCard, confirmation_text).
    """
    action = parsed.intent
    target_id = parsed.entity_id or ""
    params = parsed.params

    if action == "ACKNOWLEDGE_ALERT":
        alert_id = target_id
        linked_inc = params.get("linked_to_incident")
        target_alert: Alert | None = None
        if alert_id:
            target_alert = db.scalar(select(Alert).where(func.upper(Alert.alert_id) == alert_id.upper()))
        elif linked_inc:
            inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == linked_inc.upper()))
            if inc and inc.alert:
                target_alert = inc.alert

        if not target_alert:
            return None, None, f"Alert '{alert_id or linked_inc}' was not found in database."

        preview = {
            "entity": f"Alert {target_alert.alert_id}",
            "current_status": target_alert.status,
            "new_status": "ACKNOWLEDGED",
            "threat_class": target_alert.predicted_class,
        }
        summary = f"Acknowledge alert {target_alert.alert_id} (Change status: {target_alert.status} → ACKNOWLEDGED)"
        pending = PendingAction(
            action=action,
            target_entity="alert",
            target_id=target_alert.alert_id,
            params={"alert_id": target_alert.alert_id},
            preview_changes=preview,
            summary=summary,
        )
        card = AssistantCard(
            card_type="confirmation_prompt",
            data={
                "action": action,
                "title": f"Acknowledge Alert {target_alert.alert_id}",
                "summary": summary,
                "preview": preview,
            },
        )
        return pending, card, f"⚠️ **Confirmation Required**: Would you like to acknowledge alert `{target_alert.alert_id}`?"

    elif action in ["INVESTIGATE_INCIDENT", "START_INVESTIGATION"]:
        inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == target_id.upper()))
        if not inc:
            return None, AssistantCard(card_type="error_card", data={"error": f"Incident '{target_id}' not found."}), f"Incident '{target_id}' was not found in database."

        if inc.alert and inc.alert.status != "ACKNOWLEDGED":
            card = AssistantCard(
                card_type="error_card",
                data={"error": "Alert not acknowledged", "incident_id": inc.incident_id, "alert_id": inc.alert_id},
            )
            return None, card, f"⚠️ **Investigation Locked**: Linked alert `{inc.alert_id}` has not been acknowledged yet. In SOC protocol, an alert must be acknowledged before starting an investigation. Please acknowledge alert `{inc.alert_id}` first."

        preview = {
            "entity": f"Incident {inc.incident_id}",
            "current_status": inc.status,
            "new_status": "INVESTIGATING",
            "assigned_analyst": user.username,
        }
        summary = f"Open investigation for {inc.incident_id} and set assigned analyst to {user.username}"
        pending = PendingAction(
            action=action,
            target_entity="incident",
            target_id=inc.incident_id,
            params={"incident_id": inc.incident_id},
            preview_changes=preview,
            summary=summary,
        )
        card = AssistantCard(
            card_type="confirmation_prompt",
            data={
                "action": action,
                "title": f"Start Investigation for {inc.incident_id}",
                "summary": summary,
                "preview": preview,
            },
        )
        return pending, card, f"⚠️ **Confirmation Required**: Ready to open investigation for incident `{inc.incident_id}`?"

    elif action == "ADD_NOTE":
        note_text = params.get("note_text", "").strip()
        if not note_text:
            return None, None, "Please provide the note text to save. Example: `add analyst note to INC-1042: <text>`."

        inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == target_id.upper()))
        if not inc:
            return None, None, f"Incident '{target_id}' was not found."

        preview = {
            "incident_id": inc.incident_id,
            "analyst": user.username,
            "note_preview": note_text[:120],
        }
        summary = f"Add analyst note to {inc.incident_id}: \"{note_text[:60]}...\""
        pending = PendingAction(
            action=action,
            target_entity="incident",
            target_id=inc.incident_id,
            params={"incident_id": inc.incident_id, "note_text": note_text},
            preview_changes=preview,
            summary=summary,
        )
        card = AssistantCard(
            card_type="confirmation_prompt",
            data={
                "action": action,
                "title": f"Add Note to {inc.incident_id}",
                "summary": summary,
                "preview": preview,
            },
        )
        return pending, card, f"⚠️ **Confirmation Required**: Save the following analyst note to incident `{inc.incident_id}`?\n> \"{note_text}\""

    elif action == "ASSIGN_INCIDENT":
        assignee = params.get("assignee", "").strip()
        if not assignee:
            return None, None, "Please specify an analyst username to assign to. Example: `assign INC-1042 to admin`."

        inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == target_id.upper()))
        if not inc:
            return None, None, f"Incident '{target_id}' was not found."

        target_u = db.scalar(select(User).where(func.upper(User.username) == assignee.upper()))
        if not target_u:
            return None, None, f"User '{assignee}' was not found."

        current_owner = inc.assigned_to.username if inc.assigned_to else "Unassigned"
        preview = {
            "incident_id": inc.incident_id,
            "current_owner": current_owner,
            "new_owner": target_u.username,
        }
        summary = f"Reassign incident {inc.incident_id} from {current_owner} to {target_u.username}"
        pending = PendingAction(
            action=action,
            target_entity="incident",
            target_id=inc.incident_id,
            params={"incident_id": inc.incident_id, "assignee": target_u.username},
            preview_changes=preview,
            summary=summary,
        )
        card = AssistantCard(
            card_type="confirmation_prompt",
            data={
                "action": action,
                "title": f"Assign {inc.incident_id} to {target_u.username}",
                "summary": summary,
                "preview": preview,
            },
        )
        return pending, card, f"⚠️ **Confirmation Required**: Reassign incident `{inc.incident_id}` from `{current_owner}` to `{target_u.username}`?"

    elif action == "CHANGE_SEVERITY":
        new_sev = params.get("severity")
        if not new_sev:
            return None, None, "Please specify the new severity level (LOW, MEDIUM, HIGH, CRITICAL)."

        inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == target_id.upper()))
        if not inc:
            return None, None, f"Incident '{target_id}' was not found."

        preview = {
            "incident_id": inc.incident_id,
            "current_severity": inc.severity,
            "new_severity": new_sev.upper(),
        }
        summary = f"Change severity of {inc.incident_id} from {inc.severity} to {new_sev.upper()}"
        pending = PendingAction(
            action=action,
            target_entity="incident",
            target_id=inc.incident_id,
            params={"incident_id": inc.incident_id, "severity": new_sev.upper()},
            preview_changes=preview,
            summary=summary,
        )
        card = AssistantCard(
            card_type="confirmation_prompt",
            data={
                "action": action,
                "title": f"Change Severity of {inc.incident_id}",
                "summary": summary,
                "preview": preview,
            },
        )
        return pending, card, f"⚠️ **Confirmation Required**: Change severity of `{inc.incident_id}` from `{inc.severity}` to `{new_sev.upper()}`?"

    elif action == "RESOLVE_INCIDENT":
        summary_text = params.get("summary")
        inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == target_id.upper()))
        if not inc:
            return None, None, f"Incident '{target_id}' was not found."

        preview = {
            "incident_id": inc.incident_id,
            "current_status": inc.status,
            "new_status": "RESOLVED",
            "resolution_summary": summary_text or "Resolved by SOC Analyst",
        }
        summary = f"Mark incident {inc.incident_id} as RESOLVED"
        pending = PendingAction(
            action=action,
            target_entity="incident",
            target_id=inc.incident_id,
            params={"incident_id": inc.incident_id, "summary": summary_text},
            preview_changes=preview,
            summary=summary,
        )
        card = AssistantCard(
            card_type="confirmation_prompt",
            data={
                "action": action,
                "title": f"Resolve Incident {inc.incident_id}",
                "summary": summary,
                "preview": preview,
            },
        )
        return pending, card, f"⚠️ **Confirmation Required**: Mark incident `{inc.incident_id}` as RESOLVED?"

    elif action == "CLOSE_INCIDENT":
        inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == target_id.upper()))
        if not inc:
            return None, None, f"Incident '{target_id}' was not found."

        preview = {
            "incident_id": inc.incident_id,
            "current_status": inc.status,
            "new_status": "CLOSED",
        }
        summary = f"Officially CLOSE incident {inc.incident_id}"
        pending = PendingAction(
            action=action,
            target_entity="incident",
            target_id=inc.incident_id,
            params={"incident_id": inc.incident_id},
            preview_changes=preview,
            summary=summary,
        )
        card = AssistantCard(
            card_type="confirmation_prompt",
            data={
                "action": action,
                "title": f"Close Incident {inc.incident_id}",
                "summary": summary,
                "preview": preview,
            },
        )
        return pending, card, f"⚠️ **Confirmation Required**: Officially close incident `{inc.incident_id}`?"

    elif action == "ESCALATE_INCIDENT":
        inc = db.scalar(select(Incident).where(func.upper(Incident.incident_id) == target_id.upper()))
        if not inc:
            return None, None, f"Incident '{target_id}' was not found."

        preview = {
            "incident_id": inc.incident_id,
            "current_level": inc.escalation_level,
            "new_level": inc.escalation_level + 1,
            "current_priority": inc.priority,
            "new_priority": "P1",
        }
        summary = f"Escalate {inc.incident_id} to Level {inc.escalation_level + 1} and Priority P1"
        pending = PendingAction(
            action=action,
            target_entity="incident",
            target_id=inc.incident_id,
            params={"incident_id": inc.incident_id},
            preview_changes=preview,
            summary=summary,
        )
        card = AssistantCard(
            card_type="confirmation_prompt",
            data={
                "action": action,
                "title": f"Escalate Incident {inc.incident_id}",
                "summary": summary,
                "preview": preview,
            },
        )
        return pending, card, f"⚠️ **Confirmation Required**: Escalate incident `{inc.incident_id}` to Level {inc.escalation_level + 1}?"

    return None, None, "Unknown write action."


def execute_confirmed_action(
    db: Session,
    pending: PendingAction,
    user: User,
) -> dict[str, Any]:
    """Execute whitelisted tool with confirmed parameters and verified database commit."""
    action = pending.action
    params = pending.params

    if action == "ACKNOWLEDGE_ALERT":
        return tool_acknowledge_alert(
            db=db,
            alert_id=params.get("alert_id") or pending.target_id,
            linked_incident_id=params.get("linked_to_incident"),
            user=user,
        )

    elif action == "INVESTIGATE_INCIDENT":
        return tool_investigate_incident(
            db=db,
            incident_id=params.get("incident_id") or pending.target_id,
            user=user,
        )

    elif action == "ADD_NOTE":
        return tool_add_note(
            db=db,
            incident_id=params.get("incident_id") or pending.target_id,
            note_text=params.get("note_text", ""),
            user=user,
        )

    elif action == "ASSIGN_INCIDENT":
        return tool_assign_incident(
            db=db,
            incident_id=params.get("incident_id") or pending.target_id,
            assignee=params.get("assignee", ""),
            user=user,
        )

    elif action == "CHANGE_SEVERITY":
        return tool_change_severity(
            db=db,
            incident_id=params.get("incident_id") or pending.target_id,
            new_severity=params.get("severity", ""),
            user=user,
        )

    elif action == "RESOLVE_INCIDENT":
        return tool_resolve_incident(
            db=db,
            incident_id=params.get("incident_id") or pending.target_id,
            summary=params.get("summary"),
            user=user,
        )

    elif action == "CLOSE_INCIDENT":
        return tool_close_incident(
            db=db,
            incident_id=params.get("incident_id") or pending.target_id,
            user=user,
        )

    elif action == "ESCALATE_INCIDENT":
        return tool_escalate_incident(
            db=db,
            incident_id=params.get("incident_id") or pending.target_id,
            user=user,
        )

    return {
        "success": False,
        "reply": f"Action '{action}' is not in the allowed execution whitelist.",
        "card": AssistantCard(card_type="error_card", data={"error": "Action disallowed"}),
    }
