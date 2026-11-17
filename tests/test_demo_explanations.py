"""Real model, persisted replay evidence, and email transport regressions."""
import csv
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from backend.app.database.session import SessionLocal
from backend.app.models import Alert, NetworkEvent
from backend.app.replay.replay_service import replay_row


@pytest.fixture
def unexplained_alert():
    with open("data/sample_replay.csv", encoding="utf-8") as source:
        row = next(row for row in csv.DictReader(source) if row["zuka_attack_class"] == "RECONNAISSANCE")
    with SessionLocal() as db:
        result = replay_row(db, row, row_index=0, include_xai=False)
    assert result["alert_id"]
    return result


def test_demo_event_records_flow_detection_explanation_and_incident(client, headers):
    with open("data/sample_replay.csv", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    index = next(i for i, row in enumerate(rows) if row["zuka_attack_class"] == "RECONNAISSANCE")
    response = client.post("/api/replay/demo", headers=headers["arif"], json={"row_index": index + len(rows)})
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert response.json()["next_row_index"] == (index + 1) % len(rows)
    assert result["alert_id"] and result["incident_id"]
    assert response.json()["incident"]["incident_id"] == result["incident_id"]
    with SessionLocal() as db:
        alert = db.scalar(select(Alert).where(Alert.alert_id == result["alert_id"]))
        event = db.get(NetworkEvent, result["network_event_id"])
        assert len(alert.detection_result["input_features"]) == 14
        assert alert.detection_result["network_event_id"] == event.id
        assert event.extra_metadata["input_features"] == alert.detection_result["input_features"]
        assert len(alert.xai_explanation["top_contributions"]) == 5


def test_explanation_from_retained_inputs_is_persisted_and_cached(client, headers, unexplained_alert, monkeypatch):
    path = f'/api/alerts/{unexplained_alert["alert_id"]}/explanation'
    response = client.post(path, headers=headers["arif"])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "OPEN"
    assert data["capture_source"] == "Dataset replay"
    assert data["dataset_name"] not in ("Unknown", "Not provided")
    assert data["xai_explanation"]["input_source"] == "stored_model_inputs"
    assert len(data["xai_explanation"]["top_contributions"]) == 5
    from backend.app.api.routes import alerts
    monkeypatch.setattr(alerts, "generate_alert_explanation", lambda *_: pytest.fail("Cached explanation must be reused"))
    assert client.post(path, headers=headers["arif"]).json()["xai_explanation"] == data["xai_explanation"]
    assert client.get(path.removesuffix("/explanation"), headers=headers["viewer"]).json()["xai_explanation"] == data["xai_explanation"]


def test_legacy_demo_explanation_requires_matching_retained_event(client, headers, unexplained_alert):
    with SessionLocal() as db:
        alert = db.scalar(select(Alert).where(Alert.alert_id == unexplained_alert["alert_id"]))
        detection = dict(alert.detection_result)
        detection.pop("input_features")
        detection.pop("network_event_id")
        alert.detection_result = detection
        alert.dataset_name = alert.capture_source = None
        event = db.get(NetworkEvent, unexplained_alert["network_event_id"])
        event.event_time = alert.detected_at - timedelta(seconds=1)
        event.extra_metadata = {k: v for k, v in event.extra_metadata.items() if k != "input_features"}
        db.commit()
    response = client.post(f'/api/alerts/{unexplained_alert["alert_id"]}/explanation', headers=headers["admin"])
    assert response.status_code == 200, response.text
    assert response.json()["xai_explanation"]["input_source"] == "reconstructed_demo_sample"


@pytest.mark.parametrize("failure", ["unknown_source", "mismatched_prediction", "missing_evidence"])
def test_explanation_does_not_invent_evidence(client, headers, unexplained_alert, failure):
    with SessionLocal() as db:
        alert = db.scalar(select(Alert).where(Alert.alert_id == unexplained_alert["alert_id"]))
        detection = dict(alert.detection_result)
        if failure == "mismatched_prediction":
            detection["prediction"] = {**detection["prediction"], "confidence": 0.123456}
        else:
            detection.pop("input_features")
            alert.capture_source = "External collector" if failure == "unknown_source" else "Dataset replay"
            if failure == "missing_evidence":
                alert.source_ip = "203.0.113.250"
        alert.detection_result = detection
        db.commit()
    response = client.post(f'/api/alerts/{unexplained_alert["alert_id"]}/explanation', headers=headers["admin"])
    assert response.status_code == 409, response.text
    with SessionLocal() as db:
        alert = db.scalar(select(Alert).where(Alert.alert_id == unexplained_alert["alert_id"]))
        assert alert.xai_explanation is None
        assert alert.status == "OPEN"


def test_demo_and_explanation_permissions_and_busy_model(client, headers, unexplained_alert):
    from backend.app.detection.workload import model_task_lock
    path = f'/api/alerts/{unexplained_alert["alert_id"]}/explanation'
    assert client.post(path, headers=headers["viewer"]).status_code == 403
    assert client.post("/api/replay/demo", headers=headers["viewer"], json={}).status_code == 403
    assert client.post("/api/alerts/does-not-exist/explanation", headers=headers["admin"]).status_code == 404
    with model_task_lock:
        for endpoint, payload in ((path, None), ("/api/replay/demo", {}), ("/api/replay/next", {}), ("/api/detection/predict", {"features": {}})):
            response = client.post(endpoint, headers=headers["admin"], json=payload)
            assert response.status_code == 429
            assert response.headers["retry-after"] == "2"


def test_email_codes_support_starttls_on_free_host_compatible_port(monkeypatch):
    from backend.app.services import email_service
    for name, value in dict(smtp_host="smtp.example.com", smtp_port=2525, smtp_username="isolated-test-login", smtp_password="isolated-test-smtp-key", smtp_from_email="verified@example.com", smtp_use_tls=True, smtp_use_ssl=False).items():
        monkeypatch.setattr(email_service.settings, name, value)
    smtp = MagicMock()
    monkeypatch.setattr(email_service.smtplib, "SMTP", smtp)
    email_service.send_two_factor_otp(recipient="recipient@example.com", username="test", otp="123456", purpose="2FA")
    smtp.assert_called_once_with("smtp.example.com", 2525, timeout=20)
    server = smtp.return_value.__enter__.return_value
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("isolated-test-login", "isolated-test-smtp-key")
    message = server.send_message.call_args.args[0]
    assert message["To"] == "recipient@example.com"
    assert "123456" in message.get_body(preferencelist=("plain",)).get_content()
