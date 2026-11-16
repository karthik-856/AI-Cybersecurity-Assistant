from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models import User
from backend.app.models.push_subscription import PushSubscription
from backend.app.security.dependencies import get_current_user
from backend.app.push.push_service import push_is_configured

router = APIRouter(prefix="/api/push", tags=["Web Push"])


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscriptionRequest(BaseModel):
    endpoint: HttpUrl
    keys: PushKeys


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


@router.post("/subscribe")
def subscribe(
    payload: PushSubscriptionRequest,
    current_user: User = Depends(get_current_user),
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
        subscription.user_id = current_user.id
        subscription.p256dh = payload.keys.p256dh
        subscription.auth = payload.keys.auth

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
