from __future__ import annotations

import json
import logging
import base64
import hmac
from pathlib import Path
from typing import Any

from pywebpush import WebPushException, webpush
from py_vapid import Vapid
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.database.session import SessionLocal
from backend.app.models.push_subscription import PushSubscription
from backend.app.models import User, Role

logger = logging.getLogger(__name__)


def get_vapid_signer():
    """Load stable hosting secrets and reject mismatched key pairs."""
    if not settings.vapid_public_key or not settings.vapid_subject.startswith(("mailto:", "https://")):
        return None
    try:
        if settings.vapid_private_key:
            signer = Vapid.from_string(settings.vapid_private_key.get_secret_value())
        elif Path(settings.vapid_private_key_path).is_file():
            signer = Vapid.from_pem(Path(settings.vapid_private_key_path).read_bytes())
        else:
            return None
        encoded = base64.urlsafe_b64encode(signer.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)).decode().rstrip("=")
        return signer if hmac.compare_digest(encoded, settings.vapid_public_key.rstrip("=")) else None
    except Exception:
        logger.warning("Web Push signing configuration is invalid.")
        return None


def push_is_configured() -> bool:
    return get_vapid_signer() is not None


def send_push_to_subscription(
    subscription: PushSubscription,
    payload: dict[str, Any],
) -> bool:
    signer = get_vapid_signer()
    if signer is None:
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
            vapid_private_key=signer,
            vapid_claims={"sub": settings.vapid_subject},
            timeout=10,
            ttl=86400,
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
                "Web Push delivery failed for subscription id=%s, status=%s",
                subscription.id,
                status_code,
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
            "/alerts?search="
            f"{getattr(alert, 'alert_id', '')}"
        ),
    }

    with SessionLocal() as db:
        subscriptions = db.scalars(
            select(PushSubscription).join(User, User.id == PushSubscription.user_id).join(Role, Role.id == User.role_id).where(User.is_active.is_(True), Role.name.in_(("ADMIN", "SOC_ANALYST")))
        ).all()

    for subscription in subscriptions:
        if (severity == "CRITICAL" and not subscription.critical_alerts) or (severity == "HIGH" and not subscription.high_alerts):
            continue
        message = dict(payload)
        if not subscription.notification_preview:
            message["body"] = "A new security alert requires your attention."
            message.pop("predicted_class", None)
            message.pop("confidence", None)
        send_push_to_subscription(subscription, message)
