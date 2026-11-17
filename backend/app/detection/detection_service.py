from __future__ import annotations

from datetime import datetime, timezone

from backend.app.detection.model_service import (
    zuka_model_service,
)

from backend.app.detection.xai_service import (
    zuka_xai_service,
)


ATTACK_CLASSES = {
    "BRUTE_FORCE",
    "DDOS",
    "DOS",
    "EXPLOIT",
    "INFILTRATION",
    "MALWARE",
    "PORT_SCAN",
    "WEB_ATTACK",
    "BACKDOOR",
    "FUZZING",
    "RECONNAISSANCE",
    "OTHER_ATTACK",
}


def calculate_severity(
    predicted_class: str,
    confidence: float,
) -> str:

    if predicted_class == "BENIGN":
        return "INFO"

    if confidence >= 0.90:
        return "CRITICAL"

    if confidence >= 0.75:
        return "HIGH"

    if confidence >= 0.55:
        return "MEDIUM"

    return "LOW"


def detect_flow(
    features: dict,
    network_metadata: dict | None = None,
    include_xai: bool = True,
) -> dict:

    prediction = zuka_model_service.predict(
        features
    )

    explanation = None

    if include_xai:

        explanation = zuka_xai_service.explain(
            features,
            prediction,
        )

    predicted_class = prediction[
        "predicted_class"
    ]

    confidence = prediction[
        "confidence"
    ]

    is_attack = (
        predicted_class in ATTACK_CLASSES
    )

    severity = calculate_severity(
        predicted_class,
        confidence,
    )

    return {
        "detected_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "is_attack": is_attack,

        "prediction": prediction,
        "input_features": {name: float(features[name]) for name in zuka_model_service.features},

        "severity": severity,

        "explanation": explanation,

        "network_metadata": (
            network_metadata or {}
        ),
    }
