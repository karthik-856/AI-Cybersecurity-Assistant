from __future__ import annotations

import csv
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy.orm import Session

from backend.app.database.session import SessionLocal
from backend.app.detection.detection_service import detect_flow
from backend.app.soc.alert_service import create_alert_from_detection
from backend.app.soc.incident_service import create_incident_from_alert
from backend.app.models.network_event import NetworkEvent


FEATURES = [
    "duration_sec",
    "src_packets",
    "dst_packets",
    "src_bytes",
    "dst_bytes",
    "flow_packet_rate",
    "src_packet_rate",
    "dst_packet_rate",
    "src_byte_rate",
    "dst_byte_rate",
    "src_packet_size_mean",
    "dst_packet_size_mean",
    "src_iat_mean_sec",
    "dst_iat_mean_sec",
]

NETWORK_METADATA = [
    "source_ip",
    "destination_ip",
    "source_port",
    "destination_port",
    "protocol",
]

TARGET_COLUMN = "zuka_attack_class"

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_REPLAY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "splits"
    / "test.csv"
)
if not DEFAULT_REPLAY_FILE.exists():
    DEFAULT_REPLAY_FILE = PROJECT_ROOT / "data" / "sample_replay.csv"

DATASET_REPLAY_SOURCE = "Dataset replay"
EVENT_TYPE = "network_flow"


class ReplayValidationError(ValueError):
    """Raised when a replay row cannot be safely processed."""


def _to_float(value: Any, column: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ReplayValidationError(
            f"Invalid numeric value for '{column}': {value!r}"
        ) from exc

    if not math.isfinite(number):
        raise ReplayValidationError(
            f"Non-finite numeric value for '{column}'."
        )

    return number


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text or text.lower() in {"nan", "none", "null"}:
        return None

    return text


def _optional_int(value: Any) -> int | None:
    text = _optional_string(value)

    if text is None:
        return None

    try:
        return int(float(text))
    except ValueError:
        return None


def _iter_csv_rows(
    csv_path: Path,
    start_row: int = 0,
    max_rows: int | None = None,
) -> Iterator[tuple[int, dict[str, str]]]:

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Replay dataset not found: {csv_path}"
        )

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            raise ReplayValidationError(
                f"Replay dataset has no CSV header: {csv_path}"
            )

        missing = [
            column
            for column in FEATURES
            if column not in reader.fieldnames
        ]

        if missing:
            raise ReplayValidationError(
                "Replay dataset is missing required model features: "
                + ", ".join(missing)
            )

        emitted = 0

        for csv_index, row in enumerate(reader):

            if csv_index < start_row:
                continue

            yield csv_index, row

            emitted += 1

            if max_rows is not None and emitted >= max_rows:
                break


def _build_features(row: dict[str, str]) -> dict[str, float]:
    return {
        feature: _to_float(row.get(feature), feature)
        for feature in FEATURES
    }


def _build_network_metadata(
    row: dict[str, str],
) -> dict[str, Any]:

    metadata: dict[str, Any] = {
        "dataset_name": _optional_string(row.get("dataset_name")),
        "capture_source": DATASET_REPLAY_SOURCE,
    }

    source_ip = _optional_string(row.get("source_ip"))
    destination_ip = _optional_string(row.get("destination_ip"))
    protocol = _optional_string(row.get("protocol"))

    if source_ip is not None:
        metadata["source_ip"] = source_ip

    if destination_ip is not None:
        metadata["destination_ip"] = destination_ip

    if protocol is not None:
        metadata["protocol"] = protocol

    source_port = _optional_int(row.get("source_port"))
    destination_port = _optional_int(row.get("destination_port"))

    if source_port is not None:
        metadata["source_port"] = source_port

    if destination_port is not None:
        metadata["destination_port"] = destination_port

    return metadata


def _build_network_event(
    row: dict[str, str],
    network_metadata: dict[str, Any],
) -> NetworkEvent:

    duration_sec = _to_float(
        row.get("duration_sec"),
        "duration_sec",
    )

    src_packets = _to_float(
        row.get("src_packets"),
        "src_packets",
    )

    dst_packets = _to_float(
        row.get("dst_packets"),
        "dst_packets",
    )

    src_bytes = _to_float(
        row.get("src_bytes"),
        "src_bytes",
    )

    dst_bytes = _to_float(
        row.get("dst_bytes"),
        "dst_bytes",
    )

    total_packets = max(
        0,
        int(round(src_packets + dst_packets)),
    )

    total_bytes = max(
        0,
        int(round(src_bytes + dst_bytes)),
    )

    return NetworkEvent(
        event_time=datetime.now(timezone.utc).replace(tzinfo=None),
        source_ip=network_metadata.get("source_ip"),
        destination_ip=network_metadata.get("destination_ip"),
        source_port=network_metadata.get("source_port"),
        destination_port=network_metadata.get("destination_port"),
        protocol=network_metadata.get("protocol"),
        direction=None,
        packets=total_packets,
        bytes_count=total_bytes,
        flow_duration_ms=max(
            0,
            int(round(duration_sec * 1000)),
        ),
        interface_name=None,
        capture_source=DATASET_REPLAY_SOURCE,
        event_type=EVENT_TYPE,
        description=(
            "Dataset-derived network flow replayed through the ZUKA "
            "detection pipeline."
        ),
        extra_metadata={
            "input_features": _build_features(row),
            "replay": True,
            "source_file": row.get("source_file"),
            "dataset_name": row.get("dataset_name"),
            "dataset_split": row.get("dataset_split"),
            "unified_row_id": row.get("unified_row_id"),
            "synthetic": (
                str(row.get("synthetic", "")).strip().lower()
                == "true"
            ),
        },
    )


def replay_row(
    db: Session,
    row: dict[str, str],
    row_index: int,
    include_xai: bool = True,
) -> dict[str, Any]:
    """
    Process one unified-dataset row through the complete
    ZUKA SOC detection pipeline.

    Pipeline:
        Dataset Row
            -> Detection
            -> Network Event
            -> Alert
            -> Incident for attacks
    """

    features = _build_features(row)

    network_metadata = _build_network_metadata(row)

    detection_result = detect_flow(
        features=features,
        network_metadata=network_metadata,
        include_xai=include_xai,
    )

    network_event = _build_network_event(
        row=row,
        network_metadata=network_metadata,
    )

    db.add(network_event)
    db.commit()
    db.refresh(network_event)

    detection_result["network_event_id"] = network_event.id

    alert = create_alert_from_detection(
        db=db,
        detection_result=detection_result,
    )

    incident = None

    # Automatically create an incident for attack alerts.
    if alert is not None:
        incident = create_incident_from_alert(
            db=db,
            alert_id=alert.alert_id,
        )

    prediction = detection_result.get("prediction") or {}

    return {
        "row_index": row_index,
        "unified_row_id": row.get("unified_row_id"),
        "dataset_name": row.get("dataset_name"),
        "predicted_class": prediction.get("predicted_class"),
        "confidence": prediction.get("confidence"),
        "severity": detection_result.get("severity"),
        "is_attack": detection_result.get("is_attack"),
        "network_event_id": network_event.id,
        "alert_id": alert.alert_id if alert else None,
        "incident_id": (
            incident.incident_id
            if incident
            else None
        ),
    }


def replay_dataset(
    csv_path: str | Path = DEFAULT_REPLAY_FILE,
    start_row: int = 0,
    max_rows: int | None = 1,
    include_xai: bool = True,
    db: Session | None = None,
) -> dict[str, Any]:
    """
    Replay dataset rows through ZUKA.

    The default is intentionally one row so a test run cannot
    accidentally process millions of rows.

    Callers must explicitly choose max_rows for larger runs.
    """

    path = Path(csv_path).expanduser().resolve()

    if start_row < 0:
        raise ValueError(
            "start_row must be >= 0."
        )

    if max_rows is not None and max_rows < 1:
        raise ValueError(
            "max_rows must be >= 1 or None."
        )

    owns_session = db is None
    session = db or SessionLocal()

    processed = 0
    attacks = 0
    benign = 0
    alerts_created = 0
    incidents_created = 0
    events_created = 0

    results: list[dict[str, Any]] = []

    try:

        for row_index, row in _iter_csv_rows(
            csv_path=path,
            start_row=start_row,
            max_rows=max_rows,
        ):

            result = replay_row(
                db=session,
                row=row,
                row_index=row_index,
                include_xai=include_xai,
            )

            processed += 1
            events_created += 1

            if result["is_attack"]:
                attacks += 1
            else:
                benign += 1

            if result["alert_id"]:
                alerts_created += 1

            if result["incident_id"]:
                incidents_created += 1

            results.append(result)

        return {
            "status": "completed",
            "dataset_path": str(path),
            "start_row": start_row,
            "requested_rows": max_rows,
            "processed_rows": processed,
            "attack_predictions": attacks,
            "benign_predictions": benign,
            "network_events_created": events_created,
            "alerts_created": alerts_created,
            "incidents_created": incidents_created,
            "results": results,
        }

    except Exception:
        session.rollback()
        raise

    finally:
        if owns_session:
            session.close()
