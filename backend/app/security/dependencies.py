from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models import AuthSession, User
from backend.app.security.jwt import decode_access_token


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated user after validating the JWT and server session."""

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    session_id = payload.get("sid")

    if not user_id or not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication session.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_session = db.scalar(
        select(AuthSession).where(
            AuthSession.session_id == session_id,
            AuthSession.user_id == user_id,
        )
    )

    if auth_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication session is invalid or has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if auth_session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This session has been signed out.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if auth_session.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication session has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Avoid writing to PostgreSQL on every authenticated request.
    # Refresh the activity timestamp at most once every five minutes.
    if (
        auth_session.last_seen_at is None
        or now - auth_session.last_seen_at >= timedelta(minutes=5)
    ):
        auth_session.last_seen_at = now
        db.commit()

    return user


def require_role(*allowed_roles: str):
    """Require the authenticated user to have one of the allowed roles."""

    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        role_name = current_user.role.name

        if role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return role_checker
