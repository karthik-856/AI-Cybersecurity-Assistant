"""UTC timestamps for the existing timezone-naive PostgreSQL columns."""
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
