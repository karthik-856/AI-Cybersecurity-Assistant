from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.models.alert import Alert


def _send_persistent_push(alert: Alert) -> None:
    try:
        from backend.app.push.push_service import send_security_alert_push

        send_security_alert_push(alert)
    except Exception:
        # Push delivery must never break the detection/alert pipeline.
        import logging

        logging.getLogger(__name__).exception(
            "Persistent Web Push delivery failed for alert %s.",
            getattr(alert, "alert_id", "unknown"),
        )


def create_alert_from_detection(
    db: Session,
    detection_result: dict,
) -> Alert | None:
    """
    Persist an attack detection as a SOC alert.

    BENIGN detections are intentionally not persisted as alerts.
    """

    if not detection_result.get("is_attack"):
        return None

    prediction = detection_result.get("prediction", {})
    metadata = detection_result.get("network_metadata") or {}
    explanation = detection_result.get("explanation")

    predicted_class = prediction.get("predicted_class")
    confidence = prediction.get("confidence")
    severity = detection_result.get("severity")

    if not predicted_class or confidence is None or not severity:
        raise ValueError("Detection result is missing required alert fields.")

    alert = Alert(
        alert_id=f"ZUKA-{uuid4().hex[:12].upper()}",
        detected_at=datetime.now(timezone.utc).replace(tzinfo=None),
        predicted_class=predicted_class,
        confidence=float(confidence),
        severity=severity,
        status="OPEN",
        source_ip=metadata.get("source_ip"),
        destination_ip=metadata.get("destination_ip"),
        source_port=metadata.get("source_port"),
        destination_port=metadata.get("destination_port"),
        protocol=metadata.get("protocol"),
        dataset_name=metadata.get("dataset_name"),
        capture_source=metadata.get("capture_source"),
        description=(
            f"ZUKA detected {predicted_class} activity "
            f"with {float(confidence) * 100:.2f}% confidence."
        ),
        detection_result=detection_result,
        xai_explanation=explanation,
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Push delivery is deliberately asynchronous so it never blocks
    # or breaks the detection/alert pipeline.
    import threading

    threading.Thread(
        target=_send_persistent_push,
        args=(alert,),
        daemon=True,
        name="zuka-alert-push",
    ).start()

    return alert