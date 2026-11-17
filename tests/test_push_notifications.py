import base64
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import SecretStr
from requests import Response
from sqlalchemy import select
from pywebpush import WebPushException

from backend.app.core.config import settings
from backend.app.database.session import SessionLocal
from backend.app.models import PushSubscription, Role, User
from backend.app.push import push_service


@pytest.fixture
def configured_push(monkeypatch, tmp_path):
    key = ec.generate_private_key(ec.SECP256R1())
    encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
    public = encode(key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))
    monkeypatch.setattr(settings, "vapid_public_key", public)
    monkeypatch.setattr(settings, "vapid_private_key", SecretStr(encode(key.private_numbers().private_value.to_bytes(32, "big"))))
    monkeypatch.setattr(settings, "vapid_private_key_path", str(tmp_path / "missing.pem"))
    monkeypatch.setattr(settings, "vapid_subject", "https://zuka-soc.onrender.com")
    return public


def subscription_payload():
    return {"endpoint": f"https://fcm.googleapis.com/test-{uuid4().hex}", "keys": {"auth": "test", "p256dh": "test"}}


def test_environment_key_pair_is_validated_without_a_key_file(client, configured_push, monkeypatch):
    assert push_service.push_is_configured()
    assert client.get("/api/push/status").json() == {"configured": True}
    assert client.get("/api/push/public-key").json() == {"public_key": configured_push}
    monkeypatch.setattr(settings, "vapid_public_key", "different-public-key")
    assert not push_service.push_is_configured()
    assert client.get("/api/push/public-key").status_code == 503


def test_missing_push_configuration_has_an_explicit_status(client, headers, monkeypatch):
    monkeypatch.setattr(settings, "vapid_public_key", None)
    assert client.get("/api/push/status").json() == {"configured": False}
    assert client.post("/api/push/test", headers=headers["admin"], json={"endpoint": subscription_payload()["endpoint"]}).status_code == 503


def test_viewers_cannot_register_for_security_alerts_or_send_push_tests(client, headers):
    payload = subscription_payload()
    assert client.post("/api/push/subscribe", headers=headers["viewer"], json=payload).status_code == 403
    assert client.post("/api/push/test", headers=headers["viewer"], json={"endpoint": payload["endpoint"]}).status_code == 403


def test_device_preferences_are_saved_and_updated(client, headers):
    payload = {**subscription_payload(), "critical_alerts": False, "high_alerts": False, "notification_preview": False}
    assert client.post("/api/push/subscribe", headers=headers["admin"], json=payload).status_code == 200
    payload["critical_alerts"] = True
    assert client.post("/api/push/subscribe", headers=headers["admin"], json=payload).status_code == 200
    with SessionLocal() as db:
        stored = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == payload["endpoint"]))
        assert stored.critical_alerts and not stored.high_alerts and not stored.notification_preview
    assert client.request("DELETE", "/api/push/subscribe", headers=headers["admin"], json=payload).status_code == 200


def test_push_test_is_limited_to_the_requesting_account(client, headers, configured_push, monkeypatch):
    payload = subscription_payload()
    assert client.post("/api/push/subscribe", headers=headers["arif"], json=payload).status_code == 200
    delivered = []
    monkeypatch.setattr("backend.app.api.routes.push.send_push_to_subscription", lambda sub, body: delivered.append((sub.endpoint, body)) or True)
    body = {"endpoint": payload["endpoint"]}
    assert client.post("/api/push/test", headers=headers["admin"], json=body).status_code == 404
    assert client.post("/api/push/test", headers=headers["arif"], json=body).status_code == 200
    assert len(delivered) == 1 and delivered[0][0] == payload["endpoint"] and delivered[0][1]["type"] == "test"
    assert client.request("DELETE", "/api/push/subscribe", headers=headers["arif"], json=payload).status_code == 200


def test_delivery_has_timeout_and_offline_queue_ttl(configured_push, monkeypatch):
    calls = []
    monkeypatch.setattr(push_service, "webpush", lambda **kwargs: calls.append(kwargs))
    subscription = SimpleNamespace(id=1, endpoint="https://fcm.googleapis.com/test", auth="test", p256dh="test")
    assert push_service.send_push_to_subscription(subscription, {"type": "test"})
    assert calls[0]["timeout"] == 10 and calls[0]["ttl"] == 86400
    assert calls[0]["vapid_private_key"].private_key is not None


def test_alert_dispatch_obeys_active_roles_severity_and_preview(configured_push, monkeypatch):
    ids = {}
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == "admin"))
        analyst = db.scalar(select(User).where(User.username == "arif"))
        viewer = db.scalar(select(User).where(User.username == "viewer"))
        inactive = User(username="inactive-" + uuid4().hex[:12], email=uuid4().hex + "@example.com", hashed_password="unused-test-account", role_id=admin.role_id, is_active=False)
        db.add(inactive)
        db.flush()
        for name, user in (("admin", admin), ("analyst", analyst), ("viewer", viewer), ("inactive", inactive)):
            sub = PushSubscription(user_id=user.id, endpoint=subscription_payload()["endpoint"], p256dh="test", auth="test", high_alerts=name != "analyst", notification_preview=False)
            db.add(sub)
            db.flush()
            ids[name] = sub.id
        db.commit()
    delivered = []
    monkeypatch.setattr(push_service, "send_push_to_subscription", lambda sub, body: delivered.append((sub.id, body)) or True)
    push_service.send_security_alert_push(SimpleNamespace(severity="HIGH", alert_id="test-event", predicted_class="TEST_CLASS", confidence=.99))
    assert ids["admin"] in [item[0] for item in delivered]
    assert not {ids["analyst"], ids["viewer"], ids["inactive"]}.intersection(item[0] for item in delivered)
    message = next(item[1] for item in delivered if item[0] == ids["admin"])
    assert "TEST_CLASS" not in json.dumps(message) and "confidence" not in message
    assert message["url"] == "/alerts?search=test-event"
    with SessionLocal() as db:
        for sub_id in ids.values():
            db.delete(db.get(PushSubscription, sub_id))
        db.commit()


def test_expired_browser_subscription_is_removed(configured_push, monkeypatch):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "admin"))
        sub = PushSubscription(user_id=user.id, endpoint=subscription_payload()["endpoint"], p256dh="test", auth="test")
        db.add(sub)
        db.commit()
        db.refresh(sub)
        sub_id = sub.id
        response = Response()
        response.status_code = 410
        def expired(**kwargs):
            raise WebPushException("Gone", response=response)
        monkeypatch.setattr(push_service, "webpush", expired)
        assert not push_service.send_push_to_subscription(sub, {"type": "test"})
    with SessionLocal() as db:
        assert db.get(PushSubscription, sub_id) is None
