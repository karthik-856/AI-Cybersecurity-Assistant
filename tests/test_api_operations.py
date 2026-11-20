"""Regression coverage for application operations and publication fixes."""
from backend.app.core.time import utc_now
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.database.session import SessionLocal
from backend.app.models import Alert, Incident, Investigation, User
from backend.app.security.password import hash_password, pwd_context, verify_password


@pytest.mark.parametrize("password", ["Test-Password1!", "A" + "b" * 110 + "1!"])
def test_password_hash_round_trip(password):
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password(password + "wrong", hashed)


def test_plaintext_passwords_are_rejected():
    assert not verify_password("Test-Password1!", "Test-Password1!")
    assert not verify_password("x", "broken-hash")


def test_existing_bcrypt_hashes_remain_supported():
    from passlib.hash import bcrypt
    hashed = bcrypt.hash("Test-Password1!")
    assert verify_password("Test-Password1!", hashed)


@pytest.mark.parametrize("path", [
    "/api/auth/me", "/api/dashboard/summary", "/api/network/stats", "/api/alerts",
    "/api/incidents", "/api/investigations", "/api/reports", "/api/defense/open-investigations",
    "/api/database/overview", "/api/admin/users", "/api/auth/sessions",
])
def test_anonymous_access_denied(client, path):
    assert client.get(path).status_code in (401, 403)


@pytest.mark.parametrize("path", [
    "/api/auth/me", "/api/dashboard/summary", "/api/network/stats", "/api/alerts",
    "/api/incidents", "/api/investigations", "/api/reports", "/api/defense/open-investigations",
    "/api/admin/users", "/api/auth/sessions", "/api/auth/login-activity", "/api/auth/2fa/status",
    "/api/zuka-assistant/suggestions", "/api/database/overview", "/api/database/tables",
])
def test_authenticated_reads(client, headers, path):
    response = client.get(path, headers=headers["admin"])
    assert response.status_code == 200, response.text


def test_health_and_security_headers(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_unconfigured_push_is_reported(client):
    response = client.get("/api/push/public-key")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_login_and_invalid_password(client):
    good = client.post("/api/auth/login", json={"username_or_email": "admin", "password": "Test-Password1!"})
    assert good.status_code == 200, good.text
    assert good.json()["access_token"]
    bad = client.post("/api/auth/login", json={"username_or_email": "admin", "password": "Wrong-Password1!"})
    assert bad.status_code == 401


def test_registration_cannot_grant_analyst_privileges(client, monkeypatch):
    from backend.app.api.routes import auth
    monkeypatch.setattr(auth, "send_email_verification_otp", lambda **kwargs: None)
    name = "signup_" + uuid4().hex[:8]
    response = client.post("/api/auth/register", json={
        "username": name, "email": f"{name}@example.com", "password": "Test-Password1!", "role": "SOC_ANALYST"})
    assert response.status_code == 201, response.text
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == name))
        assert user.role.name == "SOC_ANALYST"
        assert user.approval_pending and not user.email_verified
        assert not user.is_active


@pytest.fixture
def investigation_ids():
    suffix = uuid4().hex[:12]
    with SessionLocal() as db:
        alert = Alert(alert_id=f"TEST-ALT-{suffix}", detected_at=utc_now(),
                      predicted_class="DOS", confidence=0.99, severity="HIGH", status="OPEN")
        db.add(alert)
        db.flush()
        incident = Incident(incident_id=f"TEST-INC-{suffix}", alert_id=alert.alert_id,
                            title="Isolated operation test", status="INVESTIGATING", severity="HIGH", priority="HIGH")
        db.add(incident)
        db.flush()
        inv = Investigation(investigation_id=f"TEST-INV-{suffix}", incident_id=incident.incident_id, status="IN_PROGRESS")
        db.add(inv)
        db.commit()
        return {"incident_id": incident.incident_id, "investigation_id": inv.investigation_id,
                "action_type": "BLOCK_IP", "action_label": "Simulated IP block",
                "rationale": "Regression test", "defense_note": "Simulated containment only."}


def test_viewer_cannot_apply_defense(client, headers, investigation_ids):
    response = client.post("/api/defense/apply-action", headers=headers["viewer"], json=investigation_ids)
    assert response.status_code == 403


def test_defense_action_updates_investigation(client, headers, investigation_ids):
    response = client.post("/api/defense/apply-action", headers=headers["arif"], json=investigation_ids)
    assert response.status_code == 200, response.text
    assert "Simulated containment only." in response.json()["updated_notes"]


def test_defense_rejects_missing_incident(client, headers, investigation_ids):
    investigation_ids["incident_id"] = "MISSING-INCIDENT"
    response = client.post("/api/defense/apply-action", headers=headers["arif"], json=investigation_ids)
    assert response.status_code == 404


def test_viewer_cannot_manage_users(client, headers):
    assert client.get("/api/admin/users", headers=headers["viewer"]).status_code == 403


def test_summary_pdf(client, headers):
    response = client.get("/api/reports/summary/pdf", headers=headers["admin"])
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF-")


@pytest.mark.parametrize("message", ["hi", "show alerts", "show incidents", "how many reports are in the database?"])
def test_assistant_database_operations(client, headers, message):
    response = client.post("/api/zuka-assistant/chat", headers=headers["admin"], json={"message": message})
    assert response.status_code == 200, response.text
    assert response.json()["reply"]
