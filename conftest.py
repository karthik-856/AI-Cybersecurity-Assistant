"""Run tests only against an explicitly selected, disposable PostgreSQL database."""
import os

import pytest
from sqlalchemy.engine import make_url

test_url = os.environ.get("TEST_DATABASE_URL")
if not test_url or not (make_url(test_url).database or "").startswith("zuka_test_"):
    raise pytest.UsageError(
        "Set TEST_DATABASE_URL to a disposable PostgreSQL database named zuka_test_*. "
        "Tests refuse to use the application database."
    )

os.environ.update(
    DATABASE_URL=test_url,
    JWT_SECRET_KEY="isolated-test-signing-key-not-for-deployment",
    OTP_SECRET="isolated-test-otp-key-not-for-deployment",
    ENABLE_IN_PROCESS_REPLAY="false",
    SMTP_HOST="",
    SMTP_USERNAME="",
    SMTP_PASSWORD="",
    VAPID_PUBLIC_KEY="",
    ZUKA_LLM_PROVIDER="disabled",
)


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import select
    from backend.app.database.session import SessionLocal
    from backend.app.models import Role, User
    from backend.app.security.password import hash_password

    command.upgrade(Config("alembic.ini"), "head")
    with SessionLocal() as db:
        for role_name in ("ADMIN", "SOC_ANALYST", "VIEWER"):
            if db.scalar(select(Role).where(Role.name == role_name)) is None:
                db.add(Role(name=role_name))
        db.flush()
        for username, role_name in (("admin", "ADMIN"), ("arif", "SOC_ANALYST"), ("viewer", "VIEWER")):
            if db.scalar(select(User).where(User.username == username)) is None:
                role = db.scalar(select(Role).where(Role.name == role_name))
                db.add(User(username=username, email=f"{username}@example.com", role_id=role.id,
                            hashed_password=hash_password("Test-Password1!"), is_active=True))
        db.commit()


@pytest.fixture
def client(initialize_test_database):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def headers():
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from backend.app.database.session import SessionLocal
    from backend.app.models import AuthSession, User
    from backend.app.security.jwt import create_access_token, create_session_id
    result = {}
    with SessionLocal() as db:
        for username in ("admin", "arif", "viewer"):
            user = db.scalar(select(User).where(User.username == username))
            sid = create_session_id()
            now = datetime.utcnow()
            db.add(AuthSession(session_id=sid, user_id=user.id, created_at=now,
                               last_seen_at=now, expires_at=now + timedelta(hours=1)))
            result[username] = {"Authorization": "Bearer " + create_access_token(
                str(user.id), user.role.name, sid)}
        db.commit()
    return result
