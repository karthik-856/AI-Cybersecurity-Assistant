from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import Depends, HTTPException, status

from backend.app.models.user import User
from backend.app.security.dependencies import get_current_user

_WINDOW_SECONDS = 60
_MAX_REQUESTS = 30
_requests_by_user: dict[int, deque[float]] = defaultdict(deque)
_lock = Lock()


def enforce_assistant_rate_limit(
    user: User = Depends(get_current_user),
) -> None:
    """Limit authenticated assistant requests to 30 per user per minute."""
    now = monotonic()
    cutoff = now - _WINDOW_SECONDS

    with _lock:
        timestamps = _requests_by_user[user.id]
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        if len(timestamps) >= _MAX_REQUESTS:
            retry_after = max(1, int(_WINDOW_SECONDS - (now - timestamps[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Assistant request limit reached. Please try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)

        if len(_requests_by_user) > 10_000:
            stale_users = [
                user_id
                for user_id, user_requests in _requests_by_user.items()
                if not user_requests or user_requests[-1] <= cutoff
            ]
            for user_id in stale_users:
                _requests_by_user.pop(user_id, None)
