from __future__ import annotations
from backend.app.core.time import utc_now

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.alert import Alert
from backend.app.models.incident import Incident


VALID_PRIORITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


FEATURE_LABELS = {
    "duration_sec": "Flow duration",
    "src_packets": "Source packet count",
    "dst_packets": "Destination packet count",
    "src_bytes": "Source byte volume",
    "dst_bytes": "Destination byte volume",
    "flow_packet_rate": "Overall packet rate",
    "src_packet_rate": "Source packet rate",
    "dst_packet_rate": "Destination packet rate",
    "src_byte_rate": "Source byte rate",
    "dst_byte_rate": "Destination byte rate",
    "src_packet_size_mean": "Mean source packet size",
    "dst_packet_size_mean": "Mean destination packet size",
    "src_iat_mean_sec": "Mean source inter-arrival time",
    "dst_iat_mean_sec": "Mean destination inter-arrival time",
}


ATTACK_CONTEXT = {
    "PORT_SCAN": (
        "The model classified this traffic as port scanning activity. "
        "This class represents traffic patterns associated with probing "
        "multiple service ports or destinations to discover reachable services."
    ),
    "DOS": (
        "The model classified this traffic as denial-of-service activity. "
        "This class represents traffic patterns associated with unusually "
        "aggressive or resource-exhausting network activity."
    ),
    "DDOS": (
        "The model classified this traffic as distributed denial-of-service "
        "activity. The classification represents a high-volume or distributed "
        "traffic pattern associated with service disruption."
    ),
    "BRUTE_FORCE": (
        "The model classified this traffic as brute-force activity. "
        "The class represents repeated service-access attempts or traffic "
        "patterns associated with credential or authentication attacks."
    ),
    "RECONNAISSANCE": (
        "The model classified this traffic as reconnaissance activity. "
        "This represents probing or information-gathering traffic that may "
        "precede a more direct attack."
    ),
    "EXPLOIT": (
        "The model classified this traffic as exploit activity. "
        "The observed flow characteristics match patterns the trained model "
        "associated with exploitation attempts."
    ),
    "FUZZING": (
        "The model classified this traffic as fuzzing activity. "
        "This represents traffic patterns associated with abnormal or varied "
        "inputs intended to expose weaknesses in a service or protocol."
    ),
    "WEB_ATTACK": (
        "The model classified this traffic as web-attack activity. "
        "The flow characteristics match patterns learned from web-service "
        "attack traffic."
    ),
    "INFILTRATION": (
        "The model classified this traffic as infiltration activity. "
        "The traffic pattern is associated with unauthorized access or "
        "post-compromise activity represented in the training data."
    ),
    "MALWARE": (
        "The model classified this traffic as malware-related activity. "
        "The flow characteristics match malicious communication patterns "
        "represented in the training data."
    ),
    "BACKDOOR": (
        "The model classified this traffic as backdoor activity. "
        "The classification represents suspicious communication patterns "
        "associated with unauthorized persistent access."
    ),
    "OTHER_ATTACK": (
        "The model classified this traffic as another attack category that "
        "does not map to one of the more specific ZUKA attack classes."
    ),
}


def generate_incident_id() -> str:
    """Generate a unique human-readable ZUKA incident identifier."""
    timestamp = utc_now().strftime("%Y%m%d%H%M%S%f")
    return f"ZUKA-INC-{timestamp}"


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "not available"

    if number == 0:
        return "0"
    if abs(number) >= 100000:
        return f"{number:.3e}"
    if abs(number) >= 10:
        return f"{number:.2f}"
    return f"{number:.4f}".rstrip("0").rstrip(".")


def _format_confidence(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "not available"


def _feature_name(feature: Any) -> str:
    text = str(feature or "unknown_feature")
    return FEATURE_LABELS.get(text, text.replace("_", " ").title())


def _contribution_text(item: dict[str, Any]) -> str:
    feature = _feature_name(item.get("feature"))
    value = _format_number(item.get("feature_value"))
    shap_value = _format_number(item.get("shap_value"))
    direction = str(item.get("direction") or "").lower()

    if direction == "supports_prediction":
        effect = "supports the predicted class"
    elif direction == "opposes_prediction":
        effect = "opposes the predicted class"
    else:
        effect = "contributes to the model decision"

    return (
        f"{feature} = {value}; SHAP contribution = {shap_value} "
        f"({effect})"
    )


def build_detailed_incident_description(alert: Alert) -> str:
    """
    Build an analyst-friendly incident narrative directly from the alert's
    stored model prediction, network metadata and TreeSHAP explanation.

    The wording deliberately distinguishes model evidence from confirmed
    security facts. SHAP contributions explain why the model made its
    classification; they do not by themselves prove malicious intent.
    """
    predicted_class = str(alert.predicted_class or "NETWORK ATTACK").upper()
    severity = str(alert.severity or "MEDIUM").upper()
    confidence = _format_confidence(alert.confidence)

    lines: list[str] = [
        f"ZUKA detected a network security event classified as {predicted_class}.",
        "",
        "DETECTION ASSESSMENT",
        f"• Predicted attack class: {predicted_class}",
        f"• Model confidence: {confidence}",
        f"• Severity assigned by ZUKA: {severity}",
        f"• Alert identifier: {alert.alert_id}",
    ]

    lines.append("• Dataset/source: Unknown")

    lines.extend(
        [
            "",
            "WHAT THIS CLASSIFICATION MEANS",
            "• " + ATTACK_CONTEXT.get(
                predicted_class,
                "The model classified the traffic as an attack pattern represented in the ZUKA training classes.",
            ),
            "",
            "NETWORK CONTEXT",
        ]
    )

    network_values = [
        ("Source IP", alert.source_ip),
        ("Destination IP", alert.destination_ip),
        ("Source port", alert.source_port),
        ("Destination port", alert.destination_port),
        ("Protocol", alert.protocol),
    ]

    available_network = False
    for label, value in network_values:
        if value is not None and str(value).strip() != "":
            lines.append(f"• {label}: {value}")
            available_network = True

    if not available_network:
        lines.append(
            "• Network identifiers are not available in the source record for this event."
        )

    explanation = alert.xai_explanation or {}
    method = explanation.get("method") or "TreeSHAP"
    top = explanation.get("top_contributions") or []
    supporting = explanation.get("supporting_features") or []
    opposing = explanation.get("opposing_features") or []

    lines.extend(
        [
            "",
            "EXPLAINABLE AI EVIDENCE",
            f"• Explanation method: {method}",
        ]
    )

    if top:
        lines.append("• Strongest model-driving features:")
        for index, item in enumerate(top[:8], start=1):
            if isinstance(item, dict):
                lines.append(f"  {index}. {_contribution_text(item)}")
    else:
        lines.append(
            "• No per-event SHAP feature contributions were stored for this alert."
        )

    if supporting:
        lines.append(
            "• Supporting evidence: "
            + "; ".join(
                _feature_name(item.get("feature"))
                for item in supporting[:5]
                if isinstance(item, dict)
            )
            + "."
        )

    if opposing:
        lines.append(
            "• Counter-evidence: "
            + "; ".join(
                _feature_name(item.get("feature"))
                for item in opposing[:5]
                if isinstance(item, dict)
            )
            + "."
        )

    lines.extend(
        [
            "",
            "ANALYST INTERPRETATION",
            "• The model's classification is based on learned patterns in the training data. "
            "It does not by itself prove malicious intent or confirm a security incident.",
            "RECOMMENDED INVESTIGATION",
            "• Review the source and destination context when network identifiers are available.",
            "• Validate the highest-impact SHAP features against surrounding network events and related alerts.",
            "• Check whether similar traffic appears repeatedly or across multiple hosts, ports, or time windows.",
            "• Correlate the event with available security telemetry before concluding that the activity is malicious.",
            "• Record the evidence reviewed, analyst observations, and final conclusion in the Investigation Center.",
            "",
            "DISCLAIMER",
            "This incident description is automatically generated by ZUKA's AI model. It is intended to assist analysts in understanding the model's prediction and should not be considered definitive proof of malicious activity. Analysts should conduct further investigation and validation before taking any action.",
        ]
    )

    return "\n".join(lines)


def is_legacy_incident_description(description: str | None) -> bool:
    """Identify the older short incident narrative so it can be upgraded."""
    if not description:
        return True
    normalized = description.strip().lower()
    return (
        normalized.startswith("zuka automatically created this incident from alert")
        or "detection assessment" not in normalized
    ) and len(description) < 500


def enrich_incident_description(
    db: Session,
    incident: Incident,
    *,
    persist: bool = True,
) -> Incident:
    """
    Upgrade an older short incident description using its linked Alert.

    Existing manually written long descriptions are preserved.
    """
    if not is_legacy_incident_description(incident.description):
        return incident

    alert = db.scalar(
        select(Alert).where(Alert.alert_id == incident.alert_id)
    )
    if alert is None:
        return incident

    detailed = build_detailed_incident_description(alert)
    if incident.description != detailed:
        incident.description = detailed
        if persist:
            db.commit()
            db.refresh(incident)

    return incident


def create_incident_from_alert(
    db: Session,
    alert_id: str,
) -> Incident | None:
    """
    Create an OPEN incident automatically from an existing alert.

    Returns the existing incident when the alert has already been
    converted into an incident. Returns None only when the alert
    does not exist or is not an attack alert.
    """
    alert = db.scalar(
        select(Alert).where(Alert.alert_id == alert_id)
    )

    if alert is None:
        return None

    # Only attack alerts should become incidents.
    if not getattr(alert, "is_attack", True):
        return None

    # One incident per alert.
    existing_incident = db.scalar(
        select(Incident).where(
            Incident.alert_id == alert.alert_id
        )
    )

    if existing_incident is not None:
        return enrich_incident_description(db, existing_incident)

    severity = str(alert.severity or "MEDIUM").strip().upper()
    priority = severity if severity in VALID_PRIORITIES else "MEDIUM"

    predicted_class = getattr(alert, "predicted_class", None) or "NETWORK ATTACK"

    title = f"ZUKA detected {str(predicted_class).upper()} activity"
    description = build_detailed_incident_description(alert)

    incident = Incident(
        incident_id=generate_incident_id(),
        alert_id=alert.alert_id,
        title=title[:200],
        description=description,
        severity=severity,
        priority=priority,
        status="OPEN",
        assigned_to_id=None,
        escalation_level=0,
        escalation_count=0,
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident
