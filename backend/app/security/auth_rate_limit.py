"""Atomic PostgreSQL request budgets for public authentication endpoints."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac

from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert

from backend.app.core.config import settings
from backend.app.database.session import SessionLocal
from backend.app.models.auth_rate_limit import AuthRateLimit

PUBLIC_AUTH_LIMITS = {
    "/api/auth/login": (20, 300),
    "/api/auth/register": (10, 3600),
    "/api/auth/forgot-password": (5, 900),
    "/api/auth/resend-verification": (5, 900),
    "/api/auth/verify-email": (20, 300),
    "/api/auth/verify-reset-otp": (20, 300),
    "/api/auth/reset-password": (10, 300),
    "/api/auth/2fa/login": (20, 300),
}


def allow_auth_request(address: str, path: str) -> tuple[bool, int]:
    limit, seconds = PUBLIC_AUTH_LIMITS[path]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(seconds=seconds)
    scope = hmac.new(settings.jwt_secret_key.encode(), f"{path}:{address}".encode(), hashlib.sha256).hexdigest()
    statement = insert(AuthRateLimit).values(scope=scope, window_started_at=now, attempts=1)
    expired = AuthRateLimit.window_started_at <= cutoff
    statement = statement.on_conflict_do_update(index_elements=[AuthRateLimit.scope], set_={
        "window_started_at": case((expired, now), else_=AuthRateLimit.window_started_at),
        "attempts": case((expired, 1), else_=AuthRateLimit.attempts + 1),
    }).returning(AuthRateLimit.attempts)
    with SessionLocal() as db:
        attempts = db.scalar(statement)
        db.execute(delete(AuthRateLimit).where(AuthRateLimit.window_started_at < now - timedelta(days=1)))
        db.commit()
    return attempts <= limit, seconds
