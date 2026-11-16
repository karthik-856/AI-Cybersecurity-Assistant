"""Start the single-origin deployment after applying safe database initialization."""
from pathlib import Path
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import select, func
import uvicorn

from backend.app.database.session import SessionLocal
from backend.app.models import Role, User, NetworkEvent
from backend.app.security.password import hash_password, validate_password_complexity


def initialize_database():
    command.upgrade(Config("alembic.ini"), "head")
    with SessionLocal() as db:
        for name in ("ADMIN", "SOC_ANALYST", "VIEWER"):
            if db.scalar(select(Role).where(Role.name == name)) is None:
                db.add(Role(name=name))
        db.flush()
        email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL")
        password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
        username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "admin")
        if bool(email) != bool(password):
            raise RuntimeError("Set both bootstrap administrator secrets, or neither.")
        if email and password:
            existing = db.scalar(select(User).where(User.email == email))
            if not existing:
                valid, error = validate_password_complexity(password)
                if not valid:
                    raise RuntimeError(error)
                role = db.scalar(select(Role).where(Role.name == "ADMIN"))
                db.add(User(username=username, email=email, hashed_password=hash_password(password), role_id=role.id, is_active=True))
        db.commit()
        empty = not db.scalar(select(func.count(NetworkEvent.id)))
    if empty and os.environ.get("SEED_DEMO_DATA", "false").lower() == "true":
        from backend.app.replay.replay_service import replay_dataset
        replay_dataset(csv_path=Path("data/sample_replay.csv"), max_rows=65, include_xai=False)


def main():
    initialize_database()
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), workers=1,
                proxy_headers=True, forwarded_allow_ips=os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1"))


if __name__ == "__main__":
    main()
