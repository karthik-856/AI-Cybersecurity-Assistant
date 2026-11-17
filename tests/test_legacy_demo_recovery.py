"""Isolated compatibility check for the original sample without saved inputs."""
import csv
from sqlalchemy import select
from backend.app.database.session import SessionLocal
from backend.app.models import Alert, NetworkEvent
from backend.app.replay.replay_service import replay_row
from backend.app.detection.explanation_service import restore_demo_inputs


def test_original_demo_recovery_rejects_ambiguous_inputs():
    with open("data/sample_replay.csv", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    recovered = 0
    unmatched = []
    with SessionLocal() as db:
        for index, row in enumerate(rows):
            result = replay_row(db, row, index, include_xai=False)
            if not result["alert_id"]:
                continue
            alert = db.scalar(select(Alert).where(Alert.alert_id == result["alert_id"]))
            original = alert.detection_result["input_features"]
            alert.detection_result = {k: v for k, v in alert.detection_result.items() if k not in ("input_features", "network_event_id")}
            alert.dataset_name = alert.capture_source = None
            event = db.get(NetworkEvent, result["network_event_id"])
            event.extra_metadata = {k: v for k, v in event.extra_metadata.items() if k != "input_features"}
            db.commit()
            restored = restore_demo_inputs(alert, db)
            if restored is None:
                unmatched.append(index)
                continue
            assert restored[0] == original
            assert alert.xai_explanation is None
            recovered += 1
    assert recovered + len(unmatched) == 53
    assert recovered == 50
    assert unmatched == [32, 33, 38]
