from datetime import datetime, timedelta, timezone
import secrets

import jwt

from backend.app.core.config import settings


def create_session_id() -> str:
    """Generate a cryptographically secure server-side session identifier."""
    return secrets.token_hex(32)


def create_access_token(
    subject: str,
    role: str,
    session_id: str,
) -> str:
    """Create an access token bound to a server-side authentication session."""

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload = {
        "sub": subject,
        "role": role,
        "sid": session_id,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate an access token."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
