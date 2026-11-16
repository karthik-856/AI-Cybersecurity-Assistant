"""Production regressions: permissions, request budgets, real explanations, and offline knowledge."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
import csv

import numpy as np
import pytest
from pydantic import ValidationError
from sqlalchemy import select, func


def test_logout_revokes_the_server_session(client, headers):
    assert client.post("/api/auth/logout", headers=headers["viewer"]).status_code == 200
    assert client.get("/api/auth/me", headers=headers["viewer"]).status_code == 401


def test_concurrent_authentication_budget_is_shared():
    from backend.app.security.auth_rate_limit import allow_auth_request
    identity = "isolated-budget-" + uuid4().hex
    with ThreadPoolExecutor(max_workers=4) as pool:
        allowed = list(pool.map(lambda _: allow_auth_request(identity, "/api/auth/login")[0], range(25)))
    assert sum(allowed) == 20
    assert allow_auth_request(identity, "/api/auth/login") == (False, 300)


def test_authentication_throttle_returns_retry_header(client, monkeypatch):
    from backend.app.core.config import settings
    import backend.app.main as main
    monkeypatch.setattr(settings, "auth_rate_limit_enabled", True)
    monkeypatch.setattr(main, "allow_auth_request", lambda address, path: (False, 300))
    response = client.post("/api/auth/login", json={"username_or_email": "admin", "password": "Test-Password1!"})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "300"


@pytest.mark.parametrize("url", ["http://127.0.0.1/push", "https://169.254.169.254/push", "https://fcm.googleapis.com.attacker.invalid/push", "https://attacker.invalid@fcm.googleapis.com/push"])
def test_push_cannot_reach_arbitrary_services(url):
    from backend.app.api.routes.push import PushSubscriptionRequest
    with pytest.raises(ValidationError):
        PushSubscriptionRequest(endpoint=url, keys={"auth": "test", "p256dh": "test"})


def test_push_subscriptions_cannot_be_taken_over(client, headers):
    payload = {"endpoint": f"https://fcm.googleapis.com/test-{uuid4().hex}", "keys": {"auth": "test", "p256dh": "test"}}
    assert client.post("/api/push/subscribe", headers=headers["admin"], json=payload).status_code == 200
    assert client.post("/api/push/subscribe", headers=headers["viewer"], json=payload).status_code == 409
    assert client.request("DELETE", "/api/push/subscribe", headers=headers["admin"], json=payload).status_code == 200


def test_listing_reports_does_not_fabricate_records(client, headers):
    from backend.app.database.session import SessionLocal
    from backend.app.models import Report
    with SessionLocal() as db:
        before = db.scalar(select(func.count(Report.id)))
    assert client.get("/api/reports", headers=headers["admin"]).status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Report.id))) == before


def test_sqlite_index_is_atomic_and_ranks_by_similarity(tmp_path):
    from rag_assistant.vector_index import VectorIndex
    index = VectorIndex(str(tmp_path), "test")
    index.replace(["a", "b"], ["alpha", "beta"], [{"section": "Alpha"}, {"section": "Beta"}], [[1, 0], [0, 1]], {"version": 1})
    assert index.query([[0, 1]], n_results=1)["documents"] == [["beta"]]
    with pytest.raises(ValueError):
        index.replace(["bad"], ["bad"], [{}], [[float("nan")]], {"version": 2})
    assert index.count() == 2 and index.metadata["version"] == 1


def test_knowledge_operations_work_without_an_external_model(tmp_path, monkeypatch):
    from rag_assistant.ingest import ingest_documents
    from rag_assistant.rag import RAGPipeline
    import rag_assistant.rag as rag
    monkeypatch.setenv("RAG_GENERATION_ENABLED", "false")
    def unexpected_request(*args, **kwargs):
        raise AssertionError("Offline knowledge must not contact an external service")
    monkeypatch.setattr(rag.requests, "post", unexpected_request)
    result = ingest_documents(persist_dir=str(tmp_path))
    assert result["chunks_indexed"] > 0
    pipeline = RAGPipeline(persist_dir=str(tmp_path))
    answer = pipeline.query("How do I resolve an incident?")
    assert not answer["is_fallback"] and "COMPLETED" in answer["answer"] and answer["sources"]
    assert pipeline.query("How do I bake a cake?")["is_fallback"]


def test_native_shap_contributions_sum_to_the_model_margin():
    import xgboost as xgb
    from backend.app.detection.model_service import zuka_model_service as service
    service.load()
    with Path("data/sample_replay.csv").open(encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    matrix = xgb.DMatrix(np.asarray([[float(row[name]) for name in service.features]]), feature_names=service.features)
    booster = service._model
    contributions = booster.predict(matrix, pred_contribs=True, strict_shape=True, iteration_range=service.iteration_range)
    margin = booster.predict(matrix, output_margin=True, strict_shape=True, iteration_range=service.iteration_range)
    np.testing.assert_allclose(contributions.sum(axis=2), margin, rtol=1e-4, atol=1e-4)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 1e308])
def test_nonfinite_model_inputs_are_rejected(value):
    from backend.app.detection.model_service import zuka_model_service as service
    features = {name: 0 for name in service.features}
    features[service.features[0]] = value
    with pytest.raises(ValueError):
        service.predict(features)


def test_spa_deep_links_and_unknown_api_routes(client, tmp_path, monkeypatch):
    import backend.app.main as main
    (tmp_path / "index.html").write_text("<!doctype html><title>ZUKA test</title>", encoding="utf-8")
    monkeypatch.setattr(main, "frontend_root", tmp_path)
    page = client.get("/incidents")
    assert "ZUKA test" in page.text
    assert page.headers["cache-control"] == "no-store"
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404 and "application/json" in response.headers["content-type"]


def test_production_headers_and_secret_validation(client, monkeypatch):
    from backend.app.core.config import settings, Settings
    monkeypatch.setattr(settings, "app_env", "production")
    response = client.get("/api/health")
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "max-age=" in response.headers["strict-transport-security"]
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", database_url="postgresql://localhost/test", jwt_secret_key="short", otp_secret="short")
