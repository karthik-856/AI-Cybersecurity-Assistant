"""Generate explanations from retained inputs or unambiguous demo evidence."""
import csv
import math
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select

from backend.app.models import NetworkEvent
from backend.app.detection.model_service import zuka_model_service
from backend.app.detection.xai_service import zuka_xai_service
from backend.app.replay.replay_service import (
    _build_features,
    _build_network_metadata,
    DATASET_REPLAY_SOURCE,
)

DEMO_FILE = Path(__file__).resolve().parents[3] / "data" / "sample_replay.csv"
NETWORK_FIELDS = ("source_ip", "destination_ip", "source_port", "destination_port", "protocol")


def same_prediction(saved, current):
    try:
        if (
            saved["predicted_class_id"] != current["predicted_class_id"]
            or saved["predicted_class"] != current["predicted_class"]
        ):
            return False
        if not math.isclose(
            float(saved["confidence"]), float(current["confidence"]),
            rel_tol=0, abs_tol=1e-7,
        ):
            return False
        old, new = saved["top_predictions"], current["top_predictions"]
        return len(old) == len(new) == 3 and all(
            a["class_id"] == b["class_id"] and a["class"] == b["class"]
            and math.isclose(
                float(a["confidence"]), float(b["confidence"]),
                rel_tol=0, abs_tol=1e-7,
            )
            for a, b in zip(old, new)
        )
    except (KeyError, TypeError, ValueError):
        return False


@lru_cache(maxsize=1)
def demo_catalog():
    with DEMO_FILE.open(encoding="utf-8") as source:
        return [
            (row, _build_features(row), _build_network_metadata(row))
            for row in csv.DictReader(source)
        ]


def restore_demo_inputs(alert, db):
    """Do not guess inputs for an unknown source or ambiguous feature vector."""
    if alert.capture_source not in (None, "", DATASET_REPLAY_SOURCE):
        return None
    events = db.scalars(
        select(NetworkEvent).where(
            NetworkEvent.capture_source == DATASET_REPLAY_SOURCE,
            NetworkEvent.event_time >= alert.detected_at - timedelta(seconds=5),
            NetworkEvent.event_time <= alert.detected_at + timedelta(seconds=1),
        )
    ).all()
    evidence = [
        event for event in events
        if (event.extra_metadata or {}).get("replay") is True
        and all(getattr(event, name) == getattr(alert, name) for name in NETWORK_FIELDS)
    ]
    candidates = {}
    saved = (alert.detection_result or {}).get("prediction", {})
    if not evidence:
        return None
    try:
        catalog = demo_catalog()
    except OSError:
        return None
    for row, features, metadata in catalog:
        if not all(metadata.get(name) == getattr(alert, name) for name in NETWORK_FIELDS):
            continue
        if not any(
            str((event.extra_metadata or {}).get("unified_row_id")) == row["unified_row_id"]
            and (event.extra_metadata or {}).get("dataset_name") == row["dataset_name"]
            and (event.extra_metadata or {}).get("source_file") == row["source_file"]
            for event in evidence
        ):
            continue
        if same_prediction(saved, zuka_model_service.predict(features)):
            signature = tuple(features[name] for name in zuka_model_service.features)
            candidates[signature] = (features, metadata)
    return next(iter(candidates.values())) if len(candidates) == 1 else None


def generate_alert_explanation(alert, db):
    detection = dict(alert.detection_result or {})
    features = detection.get("input_features")
    source = "reconstructed_demo_sample" if detection.get("input_reconstruction") else "stored_model_inputs"
    if not isinstance(features, dict):
        restored = restore_demo_inputs(alert, db)
        if restored is None:
            raise ValueError(
                "This older alert has no retained model inputs and cannot be matched "
                "unambiguously to a replay sample. Process a new demo event in "
                "Network Monitor to create an explained detection."
            )
        features, metadata = restored
        detection["input_features"] = features
        detection["input_reconstruction"] = "Matched bundled sample, network metadata, replay event provenance, and saved model probabilities."
        source = "reconstructed_demo_sample"
        if not alert.dataset_name:
            alert.dataset_name = metadata.get("dataset_name")
        if not alert.capture_source:
            alert.capture_source = DATASET_REPLAY_SOURCE
    prediction = zuka_model_service.predict(features)
    if not same_prediction(detection.get("prediction", {}), prediction):
        raise ValueError("The current model does not reproduce this saved detection. An explanation was not generated.")
    explanation = zuka_xai_service.explain(features, prediction)
    explanation["input_source"] = source
    alert.detection_result = detection
    alert.xai_explanation = explanation
    db.commit()
    db.refresh(alert)
    return alert
