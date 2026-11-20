"""Mail diagnostics disclose names only and require administrator access."""
import pytest


@pytest.mark.parametrize("configured", [False, True])
def test_mail_diagnostics_only_return_missing_names(client, headers, monkeypatch, configured):
    from backend.app.core.config import settings
    values = dict(smtp_host="smtp.example.com", smtp_username="test-private-login", smtp_password="test-private-key", smtp_from_email="sender@example.com")
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)
    if not configured:
        monkeypatch.setattr(settings, "smtp_password", "   ")
    response = client.get("/api/auth/email-status", headers=headers["admin"])
    assert response.status_code == 200
    assert response.json() == {"configured": configured, "missing_fields": [] if configured else ["SMTP_PASSWORD"]}
    assert all(value not in response.text for value in values.values())
    assert client.get("/api/auth/features").json()["two_factor"] is configured


def test_mail_diagnostics_require_admin(client, headers):
    assert client.get("/api/auth/email-status").status_code == 401
    assert client.get("/api/auth/email-status", headers=headers["viewer"]).status_code == 403
    assert client.get("/api/auth/email-status", headers=headers["arif"]).status_code == 403


@pytest.mark.parametrize("kind,expected", [("timeout", "connection_timeout"), ("authentication", "authentication_failed"), ("tls", "tls_failed")])
def test_mail_connection_diagnostic_hides_upstream_secrets(client, headers, monkeypatch, kind, expected):
    import smtplib
    import ssl
    from unittest.mock import MagicMock
    from backend.app.core.config import settings
    from backend.app.services import email_service
    for name, value in dict(smtp_host="smtp.example.com", smtp_username="test-login", smtp_password="test-key", smtp_from_email="sender@example.com", smtp_use_tls=True, smtp_use_ssl=False).items():
        monkeypatch.setattr(settings, name, value)
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    if kind == "timeout":
        factory = MagicMock(side_effect=TimeoutError("private-upstream-secret"))
    else:
        factory = MagicMock(return_value=smtp)
        if kind == "authentication":
            smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"private-upstream-secret")
        else:
            smtp.starttls.side_effect = ssl.SSLError("private-upstream-secret")
    monkeypatch.setattr(email_service.smtplib, "SMTP", factory)
    response = client.post("/api/auth/email-status/check", headers=headers["admin"])
    assert response.status_code == 200
    assert response.json()["error_code"] == expected
    assert response.json()["connected"] is False
    assert "private-upstream-secret" not in response.text and "test-key" not in response.text
    assert client.post("/api/auth/email-status/check", headers=headers["viewer"]).status_code == 403
