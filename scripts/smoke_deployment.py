"""Verify the production image against an explicitly disposable CI database."""
import csv
import os
import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url

from backend.app.core.config import settings
from backend.app.database.session import SessionLocal
from backend.app.models import Role, User
from backend.app.security.password import hash_password
from scripts.start_server import initialize_database


def main():
    if os.environ.get("SMOKE_TEST_ONLY") != "true" or not (make_url(settings.database_url).database or "").startswith("zuka_test_"):
        raise RuntimeError("Smoke tests require SMOKE_TEST_ONLY=true and a disposable zuka_test_* database.")
    initialize_database()
    with SessionLocal() as db:
        for username, role_name in (("admin", "ADMIN"), ("viewer", "VIEWER")):
            if db.scalar(select(User).where(User.username == username)) is None:
                role = db.scalar(select(Role).where(Role.name == role_name))
                db.add(User(username=username, email=f"{username}@example.com", hashed_password=hash_password("Test-Password1!"), role_id=role.id, is_active=True))
        db.commit()
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.detection.model_service import zuka_model_service
    with TestClient(app) as client:
        assert client.get("/api/ready").status_code == 200
        assert "ZUKA SOC" in client.get("/dashboard").text
        assert client.get("/api/not-real").status_code == 404
        response = client.post("/api/auth/login", json={"username_or_email": "admin", "password": "Test-Password1!"})
        assert response.status_code == 200, response.text
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        assert client.get("/api/detection/health", headers=headers).status_code == 200
        if settings.enable_in_process_replay:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                replay = client.get("/api/replay/status", headers=headers).json()
                if replay["processed_events"] > 0:
                    assert replay["running"] and replay["dataset_rows"] == 65
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("The production background worker did not process a dataset sample.")
        with Path("data/sample_replay.csv").open(encoding="utf-8") as source:
            row = next(csv.DictReader(source))
        response = client.post("/api/detection/predict", headers=headers, json={"features": {name: float(row[name]) for name in zuka_model_service.features}, "include_xai": True})
        assert response.status_code == 200, response.text
        assert response.json()["explanation"]["method"] == "TreeSHAP"
        assert client.get("/api/reports/summary/pdf", headers=headers).content.startswith(b"%PDF-")
        response = client.post("/api/zuka-assistant/chat", headers=headers, json={"message": "How do I resolve an incident?"})
        assert response.status_code == 200 and "COMPLETED" in response.json()["reply"]
    print("Production image smoke checks passed: UI, database, authentication, model, TreeSHAP, PDF, and offline assistant.")


if __name__ == "__main__":
    main()
