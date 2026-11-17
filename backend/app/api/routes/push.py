from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models import User
from backend.app.models.push_subscription import PushSubscription
from backend.app.security.dependencies import get_current_user, require_role
from backend.app.push.push_service import push_is_configured, send_push_to_subscription
from backend.app.security.auth_rate_limit import allow_auth_request

router = APIRouter(prefix="/api/push", tags=["Web Push"])


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscriptionRequest(BaseModel):
    endpoint: HttpUrl
    keys: PushKeys
    critical_alerts: bool = True
    high_alerts: bool = True
    notification_preview: bool = True

    @field_validator("endpoint")
    @classmethod
    def validate_push_provider(cls, value):
        host = (value.host or "").lower()
        providers = ("fcm.googleapis.com", "push.services.mozilla.com", "notify.windows.com", "push.apple.com")
        if value.scheme != "https" or value.username or value.password or value.port not in (None, 443) or not any(host == domain or host.endswith("." + domain) for domain in providers):
            raise ValueError("Use a supported browser push provider with HTTPS.")
        return value


@router.get("/public-key")
def get_public_key():
    if not push_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistent Web Push is not configured on this server.",
        )

    return {
        "public_key": settings.vapid_public_key,
    }


@router.get("/status")
def get_push_status():
    return {"configured": push_is_configured()}


@router.post("/subscribe")
def subscribe(
    payload: PushSubscriptionRequest,
    current_user: User = Depends(require_role("ADMIN", "SOC_ANALYST")),
    db: Session = Depends(get_db),
):
    endpoint = str(payload.endpoint)

    subscription = db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint
        )
    )

    if subscription is None:
        subscription = PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
        )
        db.add(subscription)
    else:
        if subscription.user_id != current_user.id:
            raise HTTPException(status_code=409, detail="This push subscription belongs to another account.")
        subscription.user_id = current_user.id
        subscription.p256dh = payload.keys.p256dh
        subscription.auth = payload.keys.auth

    subscription.critical_alerts = payload.critical_alerts
    subscription.high_alerts = payload.high_alerts
    subscription.notification_preview = payload.notification_preview
    db.commit()
    db.refresh(subscription)

    return {
        "status": "subscribed",
        "subscription_id": subscription.id,
    }


@router.delete("/subscribe")
def unsubscribe(
    payload: PushSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    endpoint = str(payload.endpoint)

    subscription = db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.user_id == current_user.id,
        )
    )

    if subscription is not None:
        db.delete(subscription)
        db.commit()

    return {"status": "unsubscribed"}


class PushTestRequest(BaseModel):
    endpoint: HttpUrl


@router.post("/test")
def test_own_push(
    payload: PushTestRequest,
    current_user: User = Depends(require_role("ADMIN", "SOC_ANALYST")),
    db: Session = Depends(get_db),
):
    if not push_is_configured():
        raise HTTPException(status_code=503, detail="Background push is not configured on this server.")
    if settings.auth_rate_limit_enabled:
        allowed, retry = allow_auth_request(f"user:{current_user.id}", "/api/push/test")
        if not allowed:
            raise HTTPException(status_code=429, detail="Wait before sending another test.", headers={"Retry-After": str(retry)})
    subscription = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == str(payload.endpoint), PushSubscription.user_id == current_user.id))
    if subscription is None:
        raise HTTPException(status_code=404, detail="No subscription for this device and account.")
    sent = send_push_to_subscription(subscription, {"type": "test", "title": "ZUKA test notification", "body": "Background notification delivery is working for this device.", "url": "/settings"})
    if not sent:
        raise HTTPException(status_code=502, detail="The browser push service could not accept the notification. Try enabling notifications again.")
    return {"status": "sent"}
