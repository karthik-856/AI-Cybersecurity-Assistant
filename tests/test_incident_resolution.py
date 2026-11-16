from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.database.session import SessionLocal
from backend.app.main import app
from backend.app.models import Alert, AuthSession, Incident, Investigation, User


client = TestClient(app)


def get_analyst_token() -> str:
    db = SessionLocal()
    user = db.scalar(select(User).where(User.username == "arif"))
    if not user:
        user = db.scalar(select(User).order_by(User.id.asc()).limit(1))
    if not user:
        db.close()
        raise ValueError("No user found")

    user_id = user.id
    role_name = getattr(user.role, "name", str(user.role))
    session_id = f"test-sess-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    now = datetime.utcnow()
    auth_session = AuthSession(
        session_id=session_id,
        user_id=user_id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(minutes=settings.access_token_expire_minutes),
        ip_address="127.0.0.1",
        user_agent="Pytest",
    )
    db.add(auth_session)
    db.commit()
    db.close()

    from backend.app.security.jwt import create_access_token
    return create_access_token(
        subject=str(user_id),
        role=role_name,
        session_id=session_id,
    )


def create_test_incident(status: str = "INVESTIGATING") -> str:
    db = SessionLocal()
    now = datetime.utcnow()
    ts = now.strftime("%Y%m%d%H%M%S%f")
    alert_id = f"ZUKA-TEST-ALERT-{ts}"
    alert = Alert(
        alert_id=alert_id,
        detected_at=now,
        predicted_class="DOS",
        confidence=0.95,
        severity="HIGH",
        status="INVESTIGATING",
    )
    db.add(alert)
    db.flush()

    incident_id = f"ZUKA-TEST-INC-{ts}"
    incident = Incident(
        incident_id=incident_id,
        alert_id=alert_id,
        title=f"Test Incident {ts}",
        description="Test incident for resolution flow verification",
        severity="HIGH",
        priority="HIGH",
        status=status,
    )
    db.add(incident)
    db.commit()
    db.close()
    return incident_id


def test_resolution_without_investigation_is_rejected():
    """Reject resolution if no investigation exists for the incident."""
    token = get_analyst_token()
    headers = {"Authorization": f"Bearer {token}"}
    incident_id = create_test_incident(status="INVESTIGATING")

    resp = client.patch(
        f"/api/incidents/{incident_id}/status",
        json={"status": "RESOLVED", "resolution_summary": "Attempting resolve without investigation."},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "The linked investigation must be completed with an analyst conclusion" in resp.json()["detail"]


def test_resolution_with_in_progress_investigation_is_rejected():
    """Reject resolution if the investigation is IN_PROGRESS (not COMPLETED)."""
    token = get_analyst_token()
    headers = {"Authorization": f"Bearer {token}"}
    incident_id = create_test_incident(status="INVESTIGATING")

    # Investigation exists and has conclusion, but status is IN_PROGRESS
    db = SessionLocal()
    now = datetime.utcnow()
    inv = Investigation(
        investigation_id=f"ZUKA-INV-TEST-{now.strftime('%Y%m%d%H%M%S%f')}",
        incident_id=incident_id,
        status="IN_PROGRESS",
        conclusion="Preliminary conclusion documented.",
        started_at=now,
    )
    db.add(inv)
    db.commit()
    db.close()

    resp = client.patch(
        f"/api/incidents/{incident_id}/status",
        json={"status": "RESOLVED"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "The linked investigation must be completed with an analyst conclusion" in resp.json()["detail"]


def test_resolution_with_blank_conclusion_is_rejected():
    """Reject resolution if the investigation is COMPLETED but has an empty conclusion."""
    token = get_analyst_token()
    headers = {"Authorization": f"Bearer {token}"}
    incident_id = create_test_incident(status="INVESTIGATING")

    db = SessionLocal()
    now = datetime.utcnow()
    inv = Investigation(
        investigation_id=f"ZUKA-INV-TEST-{now.strftime('%Y%m%d%H%M%S%f')}",
        incident_id=incident_id,
        status="COMPLETED",
        conclusion="   ",
        started_at=now,
        completed_at=now,
    )
    db.add(inv)
    db.commit()
    db.close()

    resp = client.patch(
        f"/api/incidents/{incident_id}/status",
        json={"status": "RESOLVED"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "The linked investigation must be completed with an analyst conclusion" in resp.json()["detail"]


def test_resolution_with_completed_investigation_prefills_conclusion():
    """Completed investigation conclusion pre-fills resolution summary when no override is provided."""
    token = get_analyst_token()
    headers = {"Authorization": f"Bearer {token}"}
    incident_id = create_test_incident(status="INVESTIGATING")

    investigation_conclusion = "Threat actor contained, malicious IPs blocklisted, network restored."
    db = SessionLocal()
    now = datetime.utcnow()
    inv = Investigation(
        investigation_id=f"ZUKA-INV-TEST-{now.strftime('%Y%m%d%H%M%S%f')}",
        incident_id=incident_id,
        status="COMPLETED",
        analyst_notes="Forensic triage completed.",
        findings="SYN flood attack from rogue botnet.",
        conclusion=investigation_conclusion,
        started_at=now,
        completed_at=now,
    )
    db.add(inv)
    db.commit()
    db.close()

    resp = client.patch(
        f"/api/incidents/{incident_id}/status",
        json={"status": "RESOLVED"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "RESOLVED"
    assert data["resolution_summary"] == investigation_conclusion


def test_resolution_with_completed_investigation_analyst_override():
    """Analyst can edit/override the pre-filled summary upon resolving."""
    token = get_analyst_token()
    headers = {"Authorization": f"Bearer {token}"}
    incident_id = create_test_incident(status="INVESTIGATING")

    investigation_conclusion = "Original investigation conclusion."
    override_summary = "Custom analyst override: Verified zero customer impact."

    db = SessionLocal()
    now = datetime.utcnow()
    inv = Investigation(
        investigation_id=f"ZUKA-INV-TEST-{now.strftime('%Y%m%d%H%M%S%f')}",
        incident_id=incident_id,
        status="COMPLETED",
        analyst_notes="Forensic triage completed.",
        findings="SYN flood attack from rogue botnet.",
        conclusion=investigation_conclusion,
        started_at=now,
        completed_at=now,
    )
    db.add(inv)
    db.commit()
    db.close()

    resp = client.patch(
        f"/api/incidents/{incident_id}/status",
        json={"status": "RESOLVED", "resolution_summary": override_summary},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "RESOLVED"
    assert data["resolution_summary"] == override_summary
