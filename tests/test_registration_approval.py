"""Viewer verification and administrator-gated analyst registration."""
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.database.session import SessionLocal
from backend.app.models import User


def signup(client, monkeypatch, role="SOC_ANALYST"):
    from backend.app.api.routes import auth, admin
    captured = {}
    notices = []
    monkeypatch.setattr(auth, "send_email_verification_otp", lambda **kw: captured.update(kw))
    monkeypatch.setattr(auth, "send_analyst_approval_email", lambda **kw: notices.append(kw))
    monkeypatch.setattr(admin, "send_analyst_approved_notice", lambda *args: None)
    name = "approval_" + uuid4().hex[:9]
    email = name + "@example.com"
    response = client.post("/api/auth/register", json={"username": name, "email": email,
        "password": "Test-Password1!", "role": role})
    assert response.status_code == 201, response.text
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.username == name))
    return name, email, user_id, captured, notices


def login(client, name):
    return client.post("/api/auth/login", json={"username_or_email": name, "password": "Test-Password1!"})


def test_analyst_needs_email_then_administrator_approval(client, headers, monkeypatch):
    name, email, user_id, captured, notices = signup(client, monkeypatch)
    assert login(client, name).status_code == 403
    assert client.post(f"/api/admin/users/{user_id}/approve", headers=headers["admin"]).status_code == 409
    assert client.post("/api/auth/verify-email", json={"email": email, "otp": captured["otp"]}).status_code == 200
    pending = login(client, name)
    assert pending.status_code == 403 and "approval" in pending.json()["detail"]
    assert notices and all("/users" in item["approval_url"] for item in notices)
    assert client.post(f"/api/admin/users/{user_id}/approve", headers=headers["viewer"]).status_code == 403
    response = client.post(f"/api/admin/users/{user_id}/approve", headers=headers["admin"])
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] and not response.json()["approval_pending"]
    assert login(client, name).json()["user"]["role"] == "SOC_ANALYST"


def test_viewer_signs_in_after_email_verification(client, monkeypatch):
    name, email, user_id, captured, notices = signup(client, monkeypatch, "VIEWER")
    assert login(client, name).status_code == 403
    assert client.post("/api/auth/verify-email", json={"email": email, "otp": captured["otp"]}).status_code == 200
    assert login(client, name).json()["user"]["role"] == "VIEWER"
    assert not notices


def test_status_and_role_changes_cannot_bypass_pending_approval(client, headers, monkeypatch):
    name, email, user_id, captured, notices = signup(client, monkeypatch)
    assert client.patch(f"/api/admin/users/{user_id}/status", headers=headers["admin"], json={"is_active": True}).status_code == 409
    assert client.patch(f"/api/admin/users/{user_id}/role", headers=headers["admin"], json={"role": "ADMIN"}).status_code == 409
    client.post("/api/auth/verify-email", json={"email": email, "otp": captured["otp"]})
    assert client.patch(f"/api/admin/users/{user_id}/status", headers=headers["admin"], json={"is_active": True}).status_code == 409
    assert client.patch(f"/api/admin/users/{user_id}/role", headers=headers["admin"], json={"role": "ADMIN"}).status_code == 409
    assert login(client, name).status_code == 403


def test_email_link_is_read_only_and_does_not_approve(client, monkeypatch):
    name, email, user_id, captured, notices = signup(client, monkeypatch)
    response = client.get(f"/api/admin/users/{user_id}/approve-via-mail?token=example", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"].endswith("/users")
    assert response.headers["referrer-policy"] == "no-referrer"
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert not user.is_active and user.approval_pending and not user.email_verified


def test_resend_uses_current_email_service_signature(client, monkeypatch):
    from datetime import timedelta
    from backend.app.models.auth_otp import AuthOtp
    name, email, user_id, captured, notices = signup(client, monkeypatch, "VIEWER")
    with SessionLocal() as db:
        otp = db.scalar(select(AuthOtp).where(AuthOtp.user_id == user_id))
        otp.created_at -= timedelta(minutes=2)
        db.commit()
    captured.clear()
    response = client.post("/api/auth/resend-verification", json={"email": email})
    assert response.status_code == 200, response.text
    assert captured["recipient"] == email and captured["username"] == name
    assert len(captured["otp"]) == 6


def test_public_signup_cannot_request_administrator(client):
    response = client.post("/api/auth/register", json={"username": "untrusted_admin", "email": "request@example.com",
        "password": "Test-Password1!", "role": "ADMIN"})
    assert response.status_code == 422
