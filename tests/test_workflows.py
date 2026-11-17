"""Workflow tests against the disposable database; mail delivery is captured locally."""
import csv
import re
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.main import app


def _protected_operations():
    operations = []
    for path, methods in app.openapi()["paths"].items():
        for method, operation in methods.items():
            if isinstance(operation, dict) and operation.get("security"):
                resolved = re.sub(r"\{[^}]+\}", "1", path)
                operations.append((method, resolved))
    return operations


@pytest.mark.parametrize("method,path", _protected_operations())
def test_every_protected_operation_requires_authentication(client, method, path):
    response = client.request(method, path, json={} if method in ("post", "put", "patch") else None)
    assert response.status_code in (401, 403), f"{method} {path}: {response.status_code}"


def _verified_account(client, monkeypatch):
    from backend.app.api.routes import auth
    captured = {}
    monkeypatch.setattr(auth, "send_email_verification_otp", lambda **kw: captured.update(kw))
    name = "workflow_" + uuid4().hex[:10]
    email = f"{name}@example.com"
    password = "Test-Password1!"
    response = client.post("/api/auth/register", json={"username": name, "email": email, "password": password})
    assert response.status_code == 201, response.text
    blocked = client.post("/api/auth/login", json={"username_or_email": name, "password": password})
    assert blocked.status_code == 403
    verified = client.post("/api/auth/verify-email", json={"email": email, "otp": captured["otp"]})
    assert verified.status_code == 200, verified.text
    response = client.post("/api/auth/login", json={"username_or_email": name, "password": password})
    assert response.status_code == 200, response.text
    return name, email, {"Authorization": "Bearer " + response.json()["access_token"]}


def test_verification_reset_and_revocation(client, monkeypatch):
    from backend.app.api.routes import auth
    name, email, old_headers = _verified_account(client, monkeypatch)
    captured = {}
    monkeypatch.setattr(auth, "send_password_reset_otp", lambda **kw: captured.update(kw))
    response = client.post("/api/auth/forgot-password", json={"email": email})
    assert response.status_code == 200, response.text
    verified = client.post("/api/auth/verify-reset-otp", json={"email": email, "otp": captured["otp"]})
    assert verified.status_code == 200, verified.text
    response = client.post("/api/auth/reset-password", json={
        "email": email, "otp": captured["otp"], "new_password": "Reset-Password2!"})
    assert response.status_code == 200, response.text
    assert client.get("/api/auth/me", headers=old_headers).status_code == 401
    assert client.post("/api/auth/login", json={"username_or_email": name, "password": "Test-Password1!"}).status_code == 401
    response = client.post("/api/auth/login", json={"username_or_email": name, "password": "Reset-Password2!"})
    assert response.status_code == 200, response.text
    reused = client.post("/api/auth/reset-password", json={
        "email": email, "otp": captured["otp"], "new_password": "Reuse-Password3!"})
    assert reused.status_code == 400


def test_two_factor_setup_and_login(client, monkeypatch):
    from backend.app.api.routes import auth
    name, email, account_headers = _verified_account(client, monkeypatch)
    captured = {}
    monkeypatch.setattr(auth, "send_two_factor_otp", lambda **kw: captured.update(kw))
    response = client.post("/api/auth/2fa/request", headers=account_headers, json={"action": "enable"})
    assert response.status_code == 200, response.text
    response = client.post("/api/auth/2fa/verify", headers=account_headers,
                           json={"action": "enable", "otp": captured["otp"]})
    assert response.status_code == 200, response.text
    response = client.post("/api/auth/login", json={"username_or_email": name, "password": "Test-Password1!"})
    assert response.status_code == 200, response.text
    assert response.json()["requires_two_factor"] is True
    assert not response.json()["access_token"]
    challenge = response.json()["challenge_token"]
    response = client.post("/api/auth/2fa/login", json={"challenge_token": challenge, "otp": captured["otp"]})
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_reports_crud_and_viewer_denial(client, headers):
    payload = {"title": "Isolated review report", "report_type": "summary"}
    assert client.post("/api/reports", headers=headers["viewer"], json=payload).status_code == 403
    response = client.post("/api/reports", headers=headers["arif"], json=payload)
    assert response.status_code == 201, response.text
    report_id = response.json()["report_id"]
    assert client.get(f"/api/reports/{report_id}", headers=headers["viewer"]).status_code == 200
    assert client.delete(f"/api/reports/{report_id}", headers=headers["viewer"]).status_code == 403
    assert client.delete(f"/api/reports/{report_id}", headers=headers["admin"]).status_code == 200
    assert client.get(f"/api/reports/{report_id}", headers=headers["admin"]).status_code == 404


def test_signup_without_email_configuration_does_not_persist_account(client):
    from sqlalchemy import select
    from backend.app.database.session import SessionLocal
    from backend.app.models import User
    name = "unconfigured_" + uuid4().hex[:10]
    response = client.post("/api/auth/register", json={
        "username": name, "email": f"{name}@example.com", "password": "Test-Password1!"})
    assert response.status_code == 503, response.text
    assert "temporarily unavailable" in response.json()["detail"]
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.username == name)) is None


def test_database_restricts_and_redacts_security_records(client, headers):
    assert client.get("/api/database/overview", headers=headers["viewer"]).status_code == 403
    for table, forbidden in (("users", "hashed_password"), ("auth_otps", "otp_hash"), ("auth_sessions", "session_id")):
        response = client.get(f"/api/database/table/{table}", headers=headers["admin"])
        assert response.status_code == 200, response.text
        data = response.json()
        for row in data["records"]:
            assert row.get(forbidden) in (None, "[REDACTED - HASHED]")


@pytest.mark.model
def test_packaged_compressed_model_predicts_all_sample_classes(tmp_path):
    import os
    from shutil import copyfile
    from backend.app.detection.model_service import ZukaModelService
    root = Path(__file__).resolve().parents[1]
    destination = tmp_path / "models" / "zuka_unified_xgboost"
    destination.mkdir(parents=True)
    source = root / "models" / "zuka_unified_xgboost"
    for name in ("label_encoder.json", "feature_schema.json"):
        copyfile(source / name, destination / name)
    os.link(source / "model.json.gz", destination / "model.json.gz")
    service = ZukaModelService(tmp_path)
    seen = set()
    with (root / "data" / "sample_replay.csv").open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["zuka_attack_class"] in seen:
                continue
            seen.add(row["zuka_attack_class"])
            response = service.predict({name: float(row[name]) for name in service.features})
            assert response["predicted_class"] in service.labels.values()
            assert 0 <= response["confidence"] <= 1
    assert len(seen) == 13


@pytest.mark.model
def test_detection_xai_and_replay(client, headers):
    from backend.app.detection.model_service import zuka_model_service
    from backend.app.replay.replay_service import replay_dataset
    sample_path = Path(__file__).resolve().parents[1] / "data" / "sample_replay.csv"
    with sample_path.open(encoding="utf-8") as stream:
        row = next(csv.DictReader(stream))
    payload = {"features": {name: float(row[name]) for name in zuka_model_service.features}, "include_xai": True}
    assert client.get("/api/detection/health", headers=headers["admin"]).status_code == 200
    response = client.post("/api/detection/predict", headers=headers["arif"], json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["explanation"]
    assert client.post("/api/detection/predict", headers=headers["viewer"], json=payload).status_code == 403
    assert client.post("/api/replay/next", headers=headers["viewer"], json={}).status_code == 403
    result = replay_dataset(csv_path=sample_path, max_rows=2, include_xai=False)
    assert result["processed_rows"] == 2


def test_unavailable_knowledge_engine_fails_gracefully(monkeypatch):
    from backend.app.zuka_assistant import rag_engine
    from backend.app.zuka_assistant.tools import tool_answer_from_knowledge_base
    def unavailable(question):
        raise ImportError("Optional knowledge dependencies unavailable")
    monkeypatch.setattr(rag_engine, "query_rag", unavailable)
    result = tool_answer_from_knowledge_base("What is Zuka?")
    assert result["success"] is False
    assert "I don't have that information" in result["reply"]


def test_replay_preserves_dataset_provenance():
    from sqlalchemy import select
    from backend.app.database.session import SessionLocal
    from backend.app.models import Alert
    from backend.app.replay.replay_service import replay_row
    with Path("data/sample_replay.csv").open(encoding="utf-8") as source:
        row = next(row for row in csv.DictReader(source) if row["zuka_attack_class"] == "RECONNAISSANCE")
    with SessionLocal() as db:
        result = replay_row(db, row, row_index=0, include_xai=False)
        alert = db.scalar(select(Alert).where(Alert.alert_id == result["alert_id"]))
        assert alert is not None
        assert alert.dataset_name == row["dataset_name"]
        assert alert.capture_source == "Dataset replay"

