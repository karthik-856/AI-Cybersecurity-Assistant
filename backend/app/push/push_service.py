from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pywebpush import WebPushException, webpush
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.database.session import SessionLocal
from backend.app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


def push_is_configured() -> bool:
    return bool(
        settings.vapid_public_key
        and settings.vapid_subject
        and Path(settings.vapid_private_key_path).exists()
    )


def send_push_to_subscription(
    subscription: PushSubscription,
    payload: dict[str, Any],
) -> bool:
    if not push_is_configured():
        return False

    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }

    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key_path,
            vapid_claims={"sub": settings.vapid_subject},
        )
        return True
    except WebPushException as exc:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)

        # 404/410 means the browser subscription is no longer valid.
        if status_code in {404, 410}:
            logger.info(
                "Removing expired Web Push subscription id=%s.",
                subscription.id,
            )
            try:
                with SessionLocal() as cleanup_db:
                    stale = cleanup_db.get(PushSubscription, subscription.id)
                    if stale is not None:
                        cleanup_db.delete(stale)
                        cleanup_db.commit()
            except Exception:
                logger.exception("Unable to remove stale push subscription.")
        else:
            logger.warning(
                "Web Push delivery failed for subscription id=%s: %s",
                subscription.id,
                exc,
            )
        return False
    except Exception:
        logger.exception(
            "Unexpected Web Push delivery error for subscription id=%s.",
            subscription.id,
        )
        return False


def send_security_alert_push(alert: Any) -> None:
    """Send a persistent OS/browser push for a CRITICAL/HIGH alert."""
    severity = str(getattr(alert, "severity", "")).upper()

    if severity not in {"CRITICAL", "HIGH"}:
        return

    if not push_is_configured():
        return

    payload = {
        "type": "security_alert",
        "title": f"{severity} SECURITY ALERT",
        "body": (
            f"{getattr(alert, 'predicted_class', 'Security threat')} detected "
            f"• {float(getattr(alert, 'confidence', 0.0)) * 100:.2f}% confidence"
        ),
        "alert_id": getattr(alert, "alert_id", None),
        "severity": severity,
        "predicted_class": getattr(alert, "predicted_class", None),
        "confidence": float(getattr(alert, "confidence", 0.0)),
        "url": (
            "/alerts?alert="
            f"{getattr(alert, 'alert_id', '')}"
        ),
    }

    with SessionLocal() as db:
        subscriptions = db.scalars(
            select(PushSubscription)
        ).all()

    for subscription in subscriptions:
        send_push_to_subscription(subscription, payload)
