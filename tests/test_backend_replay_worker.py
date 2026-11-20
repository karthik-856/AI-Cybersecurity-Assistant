"""Backend random sampling runs real inference and persists the SOC workflow."""
import csv
import threading
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.database.session import SessionLocal
from backend.app.detection.workload import model_task_lock
from backend.app.models import Alert, NetworkEvent, Incident
from backend.app.replay.replay_worker import DatasetReplayWorker


@pytest.mark.parametrize("label", ["BENIGN", "RECONNAISSANCE"])
def test_random_worker_uses_selected_dataset_and_real_model(initialize_test_database, monkeypatch, label):
    with Path("data/sample_replay.csv").open(encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    index = next(i for i, row in enumerate(rows) if row["zuka_attack_class"] == label)
    worker = DatasetReplayWorker(dataset_path="data/sample_replay.csv")
    monkeypatch.setattr("backend.app.replay.replay_worker.random.randrange", lambda count: index)
    result = worker._process_random_row()
    assert result["row_index"] == index
    assert worker.snapshot()["processed_events"] == 1
    assert worker.snapshot()["last_processed_at"]
    with SessionLocal() as db:
        event = db.get(NetworkEvent, result["network_event_id"])
        assert len(event.extra_metadata["input_features"]) == 14
        if label == "BENIGN":
            assert result["alert_id"] is None
            assert worker.snapshot()["generated_alerts"] == 0
        else:
            alert = db.scalar(select(Alert).where(Alert.alert_id == result["alert_id"]))
            assert len(alert.xai_explanation["top_contributions"]) == 5
            assert db.scalar(select(Incident).where(Incident.alert_id == alert.alert_id))
            assert worker.snapshot()["generated_alerts"] == 1


def test_background_worker_skips_a_busy_model(monkeypatch):
    worker = DatasetReplayWorker(dataset_path="data/sample_replay.csv")
    monkeypatch.setattr("backend.app.replay.replay_worker.SessionLocal", lambda: pytest.fail("Busy worker must not open a DB session"))
    with model_task_lock:
        assert worker._process_random_row() is None
    assert worker.snapshot()["processed_events"] == 0


def test_background_worker_start_stop_and_single_thread(monkeypatch):
    worker = DatasetReplayWorker(interval_seconds=60, dataset_path="data/sample_replay.csv")
    processed = threading.Event()
    monkeypatch.setattr(worker, "_process_random_row", processed.set)
    worker.start()
    try:
        assert processed.wait(2)
        thread = worker._thread
        worker.start()
        assert worker._thread is thread
        assert worker.snapshot()["running"]
    finally:
        worker.stop()
    assert not worker.snapshot()["running"]


def test_worker_status_requires_login_and_exposes_no_model_inputs(client, headers):
    assert client.get("/api/replay/status").status_code == 401
    response = client.get("/api/replay/status", headers=headers["viewer"])
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False and data["running"] is False
    assert data["selection"] == "random"
    assert "input_features" not in data and "dataset_path" not in data
