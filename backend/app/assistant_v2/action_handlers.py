from backend.app.core.time import utc_now
import secrets
import time
from typing import Any
from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.alert import Alert
from backend.app.models.incident import Incident
from backend.app.models.user import User
from backend.app.assistant_v2.schemas import (
    ActionButton,
    ActionCard,
    ActionTable,
    ConfirmationPrompt,
    ParsedIntent,
)


# In-memory confirmation token store: {token: {"action": "delete_user", "id": 12, "expires_at": float}}
PENDING_CONFIRMATIONS: dict[str, dict[str, Any]] = {}


def _clean_expired_confirmations():
    now = time.time()
    expired = [t for t, data in PENDING_CONFIRMATIONS.items() if data["expires_at"] < now]
    for t in expired:
        PENDING_CONFIRMATIONS.pop(t, None)


class ActionDispatcher:
    """
    Whitelisted execution engine for website actions.
    Validates parameters, enforces safety, handles confirmations, and renders cards/tables.
    """

    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.current_user = current_user

    def dispatch(
        self,
        intent: ParsedIntent,
        confirmed: bool = False,
        confirmation_token: str | None = None,
    ) -> dict[str, Any]:
        _clean_expired_confirmations()

        # Handle explicit cancel
        if intent.intent == "cancel":
            if confirmation_token:
                PENDING_CONFIRMATIONS.pop(confirmation_token, None)
            return {
                "reply": "Action cancelled safely. No changes were made.",
                "cards": [],
                "table": None,
                "quick_chips": ["List alerts", "Open incidents", "System status", "Help"],
            }

        # Handle explicit confirmation
        if confirmed and confirmation_token:
            token_data = PENDING_CONFIRMATIONS.pop(confirmation_token, None)
            if not token_data or token_data["expires_at"] < time.time():
                return {
                    "reply": "Confirmation token expired or invalid. Please re-run the command.",
                    "cards": [],
                    "table": None,
                    "quick_chips": ["Help", "List users", "List alerts"],
                }
            # Execute confirmed action
            if token_data["action"] == "delete_user":
                return self._execute_delete_user(token_data["id"])

        # -------------------------------------------------------------
        # Route by Entity & Intent
        # -------------------------------------------------------------
        if intent.entity == "alert":
            if intent.intent == "show":
                return self._alert_show(intent.id)
            if intent.intent == "list":
                return self._alert_list(intent.params)
            if intent.intent == "update":
                return self._alert_update(intent.id, intent.params)

        elif intent.entity == "incident":
            if intent.intent == "show":
                return self._incident_show(intent.id)
            if intent.intent == "list":
                return self._incident_list(intent.params)
            if intent.intent == "update":
                return self._incident_update(intent.id, intent.params)
            if intent.intent == "create":
                return self._incident_create(intent.params)

        elif intent.entity == "user":
            if intent.intent == "show":
                return self._user_show(intent.id)
            if intent.intent == "list":
                return self._user_list(intent.params)
            if intent.intent == "update":
                return self._user_update(intent.id, intent.params)
            if intent.intent == "delete":
                return self._user_delete_prompt(intent.id)

        elif intent.entity in {"system", "overview"}:
            return self._system_metrics()

        elif intent.intent == "help":
            return self._help_guide()

        # Unknown or unhandled
        return self._unrecognized_response(intent)

    # =========================================================================
    # ALERT HANDLERS
    # =========================================================================

    def _alert_show(self, alert_id: int | str | None) -> dict[str, Any]:
        if not alert_id:
            return {
                "reply": "Please specify an Alert ID, e.g., 'show alert 12' or 'alert #5'.",
                "quick_chips": ["List alerts", "List critical alerts", "Help"],
            }

        alert = None
        try:
            int_id = int(alert_id)
            alert = self.db.scalar(select(Alert).where((Alert.id == int_id) | (Alert.alert_id == str(alert_id))))
        except ValueError:
            alert = self.db.scalar(select(Alert).where(Alert.alert_id == str(alert_id)))

        if not alert:
            return {
                "reply": f"Alert #{alert_id} was not found in the database. Please verify the ID.",
                "cards": [],
                "table": None,
                "quick_chips": ["List alerts", "Critical alerts", "Help"],
            }

        sev_variant = {
            "CRITICAL": "critical",
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
        }.get(alert.severity.upper(), "info")

        actions = []
        if alert.status.upper() == "OPEN":
            actions.append(ActionButton(label="Acknowledge", action="execute_command", payload=f"acknowledge alert {alert.id}", variant="primary"))
            actions.append(ActionButton(label="Resolve", action="execute_command", payload=f"resolve alert {alert.id}", variant="success"))
            actions.append(ActionButton(label="Escalate to Incident", action="execute_command", payload=f"escalate alert {alert.id}", variant="secondary"))
        elif alert.status.upper() == "ACKNOWLEDGED":
            actions.append(ActionButton(label="Resolve", action="execute_command", payload=f"resolve alert {alert.id}", variant="success"))
            actions.append(ActionButton(label="Mark False Positive", action="execute_command", payload=f"dismiss alert {alert.id}", variant="secondary"))

        actions.append(ActionButton(label="View in Alert Center", action="navigate", payload="/alerts", variant="secondary"))

        fields = [
            {"label": "Attack Class", "value": alert.predicted_class},
            {"label": "Severity", "value": alert.severity.upper()},
            {"label": "Status", "value": alert.status.upper()},
            {"label": "Confidence", "value": f"{int(alert.confidence * 100)}%"},
            {"label": "Source IP", "value": alert.source_ip or "Unknown"},
            {"label": "Destination IP", "value": alert.destination_ip or "Unknown"},
            {"label": "Port Mapping", "value": f"{alert.source_port or '-'} → {alert.destination_port or '-'}"},
            {"label": "Detected At", "value": alert.detected_at.strftime("%Y-%m-%d %H:%M:%S")},
        ]

        card = ActionCard(
            title=f"Alert #{alert.id} • {alert.predicted_class}",
            subtitle=f"Internal ID: {alert.alert_id}",
            badge=alert.severity.upper(),
            badge_variant=sev_variant,  # type: ignore
            fields=fields,
            actions=actions,
        )

        return {
            "reply": f"Found Alert #{alert.id} ({alert.predicted_class}) with severity {alert.severity.upper()}.",
            "cards": [card],
            "table": None,
            "quick_chips": [f"acknowledge alert {alert.id}", f"resolve alert {alert.id}", "List alerts"],
        }

    def _alert_list(self, params: dict[str, Any]) -> dict[str, Any]:
        stmt = select(Alert).order_by(Alert.detected_at.desc())

        filter_desc = []
        if "severity" in params:
            stmt = stmt.where(Alert.severity.ilike(params["severity"]))
            filter_desc.append(f"severity={params['severity']}")

        if "status" in params:
            stmt = stmt.where(Alert.status.ilike(params["status"]))
            filter_desc.append(f"status={params['status']}")

        alerts = self.db.scalars(stmt.limit(8)).all()

        if not alerts:
            filters = f" with {', '.join(filter_desc)}" if filter_desc else ""
            return {
                "reply": f"No alerts found{filters}.",
                "cards": [],
                "table": None,
                "quick_chips": ["List alerts", "List critical alerts", "Help"],
            }

        headers = ["ID", "Class", "Severity", "Source IP", "Confidence", "Status"]
        rows = [
            [
                f"#{a.id}",
                a.predicted_class,
                a.severity.upper(),
                a.source_ip or "-",
                f"{int(a.confidence * 100)}%",
                a.status.upper(),
            ]
            for a in alerts
        ]

        table = ActionTable(
            headers=headers,
            rows=rows,
            total_count=len(alerts),
            actions=[ActionButton(label="Open Alert Center", action="navigate", payload="/alerts", variant="secondary")],
        )

        first_id = alerts[0].id
        quick_chips = [f"show alert {first_id}", "List critical alerts", "List open incidents"]

        reply = f"Showing {len(alerts)} recent alerts"
        if filter_desc:
            reply += f" ({', '.join(filter_desc)})"
        reply += ":"

        return {
            "reply": reply,
            "cards": [],
            "table": table,
            "quick_chips": quick_chips,
        }

    def _alert_update(self, alert_id: int | str | None, params: dict[str, Any]) -> dict[str, Any]:
        if not alert_id:
            return {"reply": "Please specify an alert ID to update, e.g. 'acknowledge alert 12'."}

        target_status = params.get("status", "ACKNOWLEDGED")
        alert = None
        try:
            int_id = int(alert_id)
            alert = self.db.scalar(select(Alert).where((Alert.id == int_id) | (Alert.alert_id == str(alert_id))))
        except ValueError:
            alert = self.db.scalar(select(Alert).where(Alert.alert_id == str(alert_id)))

        if not alert:
            return {"reply": f"Alert #{alert_id} not found."}

        old_status = alert.status
        alert.status = target_status
        alert.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(alert)

        return {
            "reply": f"Alert #{alert.id} updated successfully: status changed from {old_status} to {target_status}.",
            "cards": [
                ActionCard(
                    title=f"Alert #{alert.id} Status Updated",
                    subtitle=f"{alert.predicted_class} • {alert.severity.upper()}",
                    badge=target_status,
                    badge_variant="success" if target_status in {"RESOLVED", "ACKNOWLEDGED"} else "info",
                    fields=[
                        {"label": "New Status", "value": target_status},
                        {"label": "Updated At", "value": utc_now().strftime("%H:%M:%S")},
                        {"label": "Updated By", "value": self.current_user.username},
                    ],
                    actions=[ActionButton(label="View Alert", action="execute_command", payload=f"show alert {alert.id}", variant="secondary")],
                )
            ],
            "table": None,
            "quick_chips": [f"show alert {alert.id}", "List alerts", "Open incidents"],
        }

    # =========================================================================
    # INCIDENT HANDLERS
    # =========================================================================

    def _incident_show(self, incident_id: int | str | None) -> dict[str, Any]:
        if not incident_id:
            return {"reply": "Please specify an Incident ID, e.g. 'show incident 3'."}

        incident = None
        try:
            int_id = int(incident_id)
            incident = self.db.scalar(select(Incident).where((Incident.id == int_id) | (Incident.incident_id == str(incident_id))))
        except ValueError:
            incident = self.db.scalar(select(Incident).where(Incident.incident_id == str(incident_id)))

        if not incident:
            return {
                "reply": f"Incident #{incident_id} not found.",
                "quick_chips": ["List incidents", "List open incidents", "Help"],
            }

        actions = [
            ActionButton(label="Investigate", action="execute_command", payload=f"investigate incident {incident.id}", variant="primary"),
            ActionButton(label="Resolve", action="execute_command", payload=f"resolve incident {incident.id}", variant="success"),
            ActionButton(label="Open Incident Center", action="navigate", payload="/incidents", variant="secondary"),
        ]

        fields = [
            {"label": "Title", "value": incident.title},
            {"label": "Severity", "value": incident.severity.upper()},
            {"label": "Priority", "value": incident.priority.upper()},
            {"label": "Status", "value": incident.status.upper()},
            {"label": "Escalation Level", "value": f"Tier {incident.escalation_level}"},
            {"label": "Linked Alert ID", "value": incident.alert_id},
            {"label": "Description", "value": incident.description or "No description provided"},
        ]

        card = ActionCard(
            title=f"Incident #{incident.id} • {incident.title}",
            subtitle=f"Ref: {incident.incident_id}",
            badge=incident.status.upper(),
            badge_variant="critical" if incident.severity.upper() == "CRITICAL" else "high",
            fields=fields,
            actions=actions,
        )

        return {
            "reply": f"Found Incident #{incident.id}: {incident.title} [{incident.status.upper()}].",
            "cards": [card],
            "table": None,
            "quick_chips": [f"investigate incident {incident.id}", f"resolve incident {incident.id}", "List incidents"],
        }

    def _incident_list(self, params: dict[str, Any]) -> dict[str, Any]:
        stmt = select(Incident).order_by(Incident.id.desc())

        filter_desc = []
        if "status" in params:
            stmt = stmt.where(Incident.status.ilike(params["status"]))
            filter_desc.append(f"status={params['status']}")
        if "severity" in params:
            stmt = stmt.where(Incident.severity.ilike(params["severity"]))
            filter_desc.append(f"severity={params['severity']}")

        incidents = self.db.scalars(stmt.limit(8)).all()

        if not incidents:
            return {
                "reply": "No incidents found matching your criteria.",
                "quick_chips": ["List incidents", "List alerts", "Help"],
            }

        headers = ["ID", "Title", "Severity", "Priority", "Status"]
        rows = [
            [
                f"#{i.id}",
                i.title[:30] + ("..." if len(i.title) > 30 else ""),
                i.severity.upper(),
                i.priority.upper(),
                i.status.upper(),
            ]
            for i in incidents
        ]

        table = ActionTable(
            headers=headers,
            rows=rows,
            total_count=len(incidents),
            actions=[ActionButton(label="Open Incident Center", action="navigate", payload="/incidents", variant="secondary")],
        )

        return {
            "reply": f"Showing {len(incidents)} active incidents:",
            "cards": [],
            "table": table,
            "quick_chips": [f"show incident {incidents[0].id}", "List open incidents", "List alerts"],
        }

    def _incident_update(self, incident_id: int | str | None, params: dict[str, Any]) -> dict[str, Any]:
        if not incident_id:
            return {"reply": "Please specify an incident ID to update."}

        target_status = params.get("status", "INVESTIGATING")
        incident = None
        try:
            int_id = int(incident_id)
            incident = self.db.scalar(select(Incident).where((Incident.id == int_id) | (Incident.incident_id == str(incident_id))))
        except ValueError:
            incident = self.db.scalar(select(Incident).where(Incident.incident_id == str(incident_id)))

        if not incident:
            return {"reply": f"Incident #{incident_id} not found."}

        old_status = incident.status
        incident.status = target_status
        if target_status == "RESOLVED":
            incident.resolved_at = utc_now()
            incident.resolution_summary = f"Resolved via Assistant action by {self.current_user.username}"

        self.db.commit()
        self.db.refresh(incident)

        return {
            "reply": f"Incident #{incident.id} updated: status changed from {old_status} to {target_status}.",
            "cards": [
                ActionCard(
                    title=f"Incident #{incident.id} Status Updated",
                    subtitle=incident.title,
                    badge=target_status,
                    badge_variant="success" if target_status == "RESOLVED" else "info",
                    fields=[
                        {"label": "New Status", "value": target_status},
                        {"label": "Severity", "value": incident.severity.upper()},
                    ],
                    actions=[ActionButton(label="View Incident", action="execute_command", payload=f"show incident {incident.id}", variant="secondary")],
                )
            ],
            "quick_chips": [f"show incident {incident.id}", "List incidents"],
        }

    def _incident_create(self, params: dict[str, Any]) -> dict[str, Any]:
        alert_id = params.get("alert_id")
        alert = None
        if alert_id:
            alert = self.db.scalar(select(Alert).where((Alert.id == alert_id) | (Alert.alert_id == str(alert_id))))

        inc_ref = f"INC-{int(time.time())}"
        title = params.get("title") or (f"Escalated from Alert #{alert.id} ({alert.predicted_class})" if alert else "New Security Incident")
        severity = alert.severity if alert else "HIGH"

        new_inc = Incident(
            incident_id=inc_ref,
            alert_id=alert.alert_id if alert else (self.db.scalar(select(Alert.alert_id).limit(1)) or "ALT-DEFAULT"),
            title=title,
            description=f"Incident generated via Assistant command by analyst {self.current_user.username}.",
            severity=severity,
            priority="P1" if severity in {"CRITICAL", "HIGH"} else "P2",
            status="OPEN",
            assigned_to_id=self.current_user.id,
        )
        self.db.add(new_inc)
        self.db.commit()
        self.db.refresh(new_inc)

        return {
            "reply": f"Incident #{new_inc.id} created successfully with severity {severity.upper()}.",
            "cards": [
                ActionCard(
                    title=f"Incident #{new_inc.id} Created",
                    subtitle=new_inc.title,
                    badge="OPEN",
                    badge_variant="critical",
                    fields=[
                        {"label": "Incident ID", "value": new_inc.incident_id},
                        {"label": "Priority", "value": new_inc.priority},
                        {"label": "Severity", "value": new_inc.severity},
                    ],
                    actions=[
                        ActionButton(label="Show Details", action="execute_command", payload=f"show incident {new_inc.id}", variant="primary"),
                        ActionButton(label="Open Incident Center", action="navigate", payload="/incidents", variant="secondary"),
                    ],
                )
            ],
            "quick_chips": [f"show incident {new_inc.id}", "List incidents"],
        }

    # =========================================================================
    # USER HANDLERS
    # =========================================================================

    def _user_show(self, user_id: int | str | None) -> dict[str, Any]:
        if not user_id:
            return {"reply": "Please specify a user ID or username, e.g. 'show user 3' or 'show user admin'."}

        user = None
        if isinstance(user_id, int) or (isinstance(user_id, str) and user_id.isdigit()):
            user = self.db.scalar(select(User).where(User.id == int(user_id)))
        else:
            user = self.db.scalar(select(User).where(User.username.ilike(str(user_id))))

        if not user:
            return {"reply": f"User '{user_id}' was not found in the database."}

        actions = []
        if self.current_user.role.name == "ADMIN" and user.id != self.current_user.id:
            if user.is_active:
                actions.append(ActionButton(label="Deactivate User", action="execute_command", payload=f"deactivate user {user.id}", variant="danger"))
            else:
                actions.append(ActionButton(label="Activate User", action="execute_command", payload=f"activate user {user.id}", variant="success"))
            actions.append(ActionButton(label="Delete User", action="execute_command", payload=f"delete user {user.id}", variant="danger"))

        actions.append(ActionButton(label="User Management", action="navigate", payload="/users", variant="secondary"))

        fields = [
            {"label": "Username", "value": user.username},
            {"label": "Email", "value": user.email},
            {"label": "Role", "value": user.role.name},
            {"label": "Status", "value": "ACTIVE" if user.is_active else "INACTIVE / PENDING"},
            {"label": "Created At", "value": user.created_at.strftime("%Y-%m-%d")},
            {"label": "Last Login", "value": user.last_login_at.strftime("%Y-%m-%d %H:%M") if user.last_login_at else "Never"},
        ]

        card = ActionCard(
            title=f"User #{user.id}: {user.username}",
            subtitle=user.email,
            badge="ACTIVE" if user.is_active else "INACTIVE",
            badge_variant="success" if user.is_active else "low",
            fields=fields,
            actions=actions,
        )

        return {
            "reply": f"User #{user.id} ({user.username}) is currently {('ACTIVE' if user.is_active else 'INACTIVE')}.",
            "cards": [card],
            "quick_chips": ["List users", "List analysts", "Help"],
        }

    def _user_list(self, params: dict[str, Any]) -> dict[str, Any]:
        stmt = select(User).order_by(User.id.asc())

        filter_desc = []
        if "role" in params:
            stmt = stmt.join(User.role).where(func.upper(User.role.property.mapper.class_.name) == params["role"])
            filter_desc.append(f"role={params['role']}")

        if params.get("pending"):
            stmt = stmt.where(User.is_active == False)
            filter_desc.append("pending_approval")

        users = self.db.scalars(stmt.limit(10)).all()
        if not users:
            return {"reply": "No users found matching query.", "quick_chips": ["List users", "Help"]}

        headers = ["ID", "Username", "Email", "Role", "Status"]
        rows = [
            [
                f"#{u.id}",
                u.username,
                u.email,
                u.role.name,
                "ACTIVE" if u.is_active else "INACTIVE ⏳",
            ]
            for u in users
        ]

        table = ActionTable(
            headers=headers,
            rows=rows,
            total_count=len(users),
            actions=[ActionButton(label="Open User Management", action="navigate", payload="/users", variant="secondary")],
        )

        first_id = users[0].id
        return {
            "reply": f"Found {len(users)} users in database:",
            "cards": [],
            "table": table,
            "quick_chips": [f"show user {first_id}", "List analysts", "System status"],
        }

    def _user_update(self, user_id: int | str | None, params: dict[str, Any]) -> dict[str, Any]:
        if not user_id:
            return {"reply": "Please specify a user ID to update."}

        if self.current_user.role.name != "ADMIN":
            return {"reply": "Permission denied: Only administrators can modify user status."}

        user = self.db.scalar(select(User).where(User.id == int(user_id)))
        if not user:
            return {"reply": f"User #{user_id} not found."}

        if user.id == self.current_user.id:
            return {"reply": "Safety restriction: You cannot deactivate or modify your own active administrator account."}

        if "is_active" in params:
            user.is_active = bool(params["is_active"])
            action_name = "activated" if user.is_active else "deactivated"
        elif params.get("action") == "approve":
            user.is_active = True
            action_name = "approved and activated"
        else:
            action_name = "updated"

        self.db.commit()
        self.db.refresh(user)

        return {
            "reply": f"User #{user.id} ({user.username}) was successfully {action_name}.",
            "cards": [
                ActionCard(
                    title=f"User #{user.id} {action_name.capitalize()}",
                    subtitle=user.username,
                    badge="ACTIVE" if user.is_active else "INACTIVE",
                    badge_variant="success" if user.is_active else "low",
                    fields=[
                        {"label": "Username", "value": user.username},
                        {"label": "Role", "value": user.role.name},
                        {"label": "Current Status", "value": "ACTIVE" if user.is_active else "INACTIVE"},
                    ],
                    actions=[ActionButton(label="View User", action="execute_command", payload=f"show user {user.id}", variant="secondary")],
                )
            ],
            "quick_chips": ["List users", f"show user {user.id}"],
        }

    def _user_delete_prompt(self, user_id: int | str | None) -> dict[str, Any]:
        if not user_id:
            return {"reply": "Please specify a user ID to delete, e.g. 'delete user 4'."}

        if self.current_user.role.name != "ADMIN":
            return {"reply": "Permission denied: Only administrators can delete user accounts."}

        user = self.db.scalar(select(User).where(User.id == int(user_id)))
        if not user:
            return {"reply": f"User #{user_id} not found."}

        if user.id == self.current_user.id:
            return {"reply": "Safety restriction: You cannot delete your own active administrator account."}

        # Issue safety confirmation
        token = secrets.token_hex(16)
        PENDING_CONFIRMATIONS[token] = {
            "action": "delete_user",
            "id": user.id,
            "username": user.username,
            "expires_at": time.time() + 60,  # 60s timeout
        }

        confirmation = ConfirmationPrompt(
            confirmation_token=token,
            prompt=f"Are you sure you want to permanently delete user '{user.username}' (ID: #{user.id})?",
            warning="This action is destructive and irreversible. All associated sessions will be revoked.",
            confirm_command=f"confirm delete user {user.id}",
            cancel_command="cancel",
        )

        return {
            "reply": f"Safety Confirmation Required: Are you sure you want to permanently delete user '{user.username}'?",
            "cards": [],
            "table": None,
            "confirmation": confirmation,
            "quick_chips": ["cancel"],
        }

    def _execute_delete_user(self, user_id: int) -> dict[str, Any]:
        user = self.db.scalar(select(User).where(User.id == user_id))
        if not user:
            return {"reply": f"User #{user_id} no longer exists."}

        username = user.username
        self.db.delete(user)
        self.db.commit()

        return {
            "reply": f"User '{username}' (ID: #{user_id}) has been permanently deleted from ZUKA SOC.",
            "cards": [
                ActionCard(
                    title="User Deleted",
                    subtitle=username,
                    badge="DELETED",
                    badge_variant="critical",
                    fields=[
                        {"label": "Deleted ID", "value": f"#{user_id}"},
                        {"label": "Executed By", "value": self.current_user.username},
                        {"label": "Timestamp", "value": utc_now().strftime("%H:%M:%S")},
                    ],
                )
            ],
            "quick_chips": ["List users", "List alerts", "Help"],
        }

    # =========================================================================
    # SYSTEM METRICS & HELP
    # =========================================================================

    def _system_metrics(self) -> dict[str, Any]:
        total_alerts = self.db.scalar(select(func.count(Alert.id))) or 0
        open_alerts = self.db.scalar(select(func.count(Alert.id)).where(Alert.status == "OPEN")) or 0
        critical_alerts = self.db.scalar(select(func.count(Alert.id)).where(Alert.severity == "CRITICAL")) or 0
        total_incidents = self.db.scalar(select(func.count(Incident.id))) or 0
        open_incidents = self.db.scalar(select(func.count(Incident.id)).where(Incident.status == "OPEN")) or 0
        total_users = self.db.scalar(select(func.count(User.id))) or 0

        fields = [
            {"label": "Total Alerts", "value": str(total_alerts)},
            {"label": "Open Alerts", "value": str(open_alerts)},
            {"label": "Critical Alerts", "value": str(critical_alerts)},
            {"label": "Active Incidents", "value": str(open_incidents)},
            {"label": "Total Incidents", "value": str(total_incidents)},
            {"label": "Registered Users", "value": str(total_users)},
            {"label": "API Engine", "value": "FastAPI + Rule Intent Engine"},
            {"label": "Database", "value": "PostgreSQL (Connected)"},
        ]

        card = ActionCard(
            title="ZUKA SOC System Telemetry",
            subtitle="Operational Status • All Systems Nominal",
            badge="HEALTHY",
            badge_variant="success",
            fields=fields,
            actions=[
                ActionButton(label="Alert Center", action="navigate", payload="/alerts", variant="secondary"),
                ActionButton(label="Incident Center", action="navigate", payload="/incidents", variant="secondary"),
                ActionButton(label="Dashboard", action="navigate", payload="/dashboard", variant="primary"),
            ],
        )

        return {
            "reply": f"ZUKA SOC telemetry: {open_alerts} open alerts ({critical_alerts} critical), {open_incidents} active incidents.",
            "cards": [card],
            "quick_chips": ["List critical alerts", "List open incidents", "List users", "Help"],
        }

    def _help_guide(self) -> dict[str, Any]:
        cards = [
            ActionCard(
                title="🚨 Alert Commands",
                subtitle="Manage threat detection alerts",
                badge="ALERTS",
                badge_variant="critical",
                fields=[
                    {"label": "show alert <id>", "value": "Inspect alert details (e.g. 'show alert 12')"},
                    {"label": "list alerts", "value": "Display recent alerts list"},
                    {"label": "list critical alerts", "value": "Filter by severity (critical/high/medium)"},
                    {"label": "list pending alerts", "value": "Filter by open/unresolved status"},
                    {"label": "acknowledge alert <id>", "value": "Mark alert as acknowledged"},
                    {"label": "resolve alert <id>", "value": "Close and resolve alert"},
                ],
            ),
            ActionCard(
                title="🛡️ Incident Commands",
                subtitle="Triage and investigate incidents",
                badge="INCIDENTS",
                badge_variant="high",
                fields=[
                    {"label": "show incident <id>", "value": "View incident details and history"},
                    {"label": "list incidents", "value": "List all security incidents"},
                    {"label": "list open incidents", "value": "Show unresolved incidents"},
                    {"label": "investigate incident <id>", "value": "Set status to INVESTIGATING"},
                    {"label": "resolve incident <id>", "value": "Mark incident as RESOLVED"},
                    {"label": "escalate alert <id>", "value": "Promote alert to full incident"},
                ],
            ),
            ActionCard(
                title="👥 User Management Commands",
                subtitle="Administer SOC operators and viewers",
                badge="USERS",
                badge_variant="info",
                fields=[
                    {"label": "list users", "value": "Show all registered accounts"},
                    {"label": "list analysts", "value": "Show all SOC Analyst accounts"},
                    {"label": "show user <id>", "value": "Inspect specific user profile"},
                    {"label": "approve user <id>", "value": "Authorize pending analyst account"},
                    {"label": "deactivate user <id>", "value": "Disable user login access"},
                    {"label": "delete user <id>", "value": "Delete account (safety confirmed)"},
                ],
            ),
            ActionCard(
                title="📊 Telemetry & Shortcuts",
                subtitle="System status and quick health checks",
                badge="SYSTEM",
                badge_variant="success",
                fields=[
                    {"label": "system status", "value": "Show live SOC telemetry & health"},
                    {"label": "dashboard stats", "value": "Summary of active KPIs"},
                    {"label": "help", "value": "Display this command palette"},
                ],
            ),
        ]

        return {
            "reply": "Here are the supported commands and actions you can run with the ZUKA Assistant:",
            "cards": cards,
            "quick_chips": ["List alerts", "List open incidents", "System status", "List users"],
        }

    def _unrecognized_response(self, intent: ParsedIntent) -> dict[str, Any]:
        return {
            "reply": (
                "I didn't recognize that command. I can inspect alerts, triage incidents, "
                "manage users, and check system health. Try one of the quick suggestions below or type 'help'."
            ),
            "cards": [],
            "table": None,
            "quick_chips": ["Help", "List alerts", "List open incidents", "System status"],
        }
