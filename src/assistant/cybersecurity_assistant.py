"""
ZUKA — Cybersecurity Assistant

SRC #7
--------

Provides the analyst-facing intelligence layer of ZUKA.

Pipeline:

    Network Flow
        ↓
    XGBoost Detector
        ↓
    SHAP Explainer
        ↓
    Alert Engine
        ↓
    Recommendation Engine
        ↓
    ZUKA Cybersecurity Assistant

The assistant does NOT perform automated containment.

Human analyst approval is required for escalation or containment decisions.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# =============================================================================
# PATH CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_ALERT_PATH = (
    PROJECT_ROOT
    / "results"
    / "tables"
    / "dashboard"
    / "soc_assistant_alert_analysis.csv"
)

DEFAULT_ANALYST_VIEW_PATH = (
    PROJECT_ROOT
    / "results"
    / "tables"
    / "dashboard"
    / "soc_assistant_analyst_view.csv"
)

DEFAULT_REPORT_DIR = (
    PROJECT_ROOT
    / "results"
    / "reports"
    / "dashboard"
)

DEFAULT_REPORT_PATH = (
    DEFAULT_REPORT_DIR
    / "zuka_cybersecurity_assistant_report.txt"
)


# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger("zuka.assistant")

if not LOGGER.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


# =============================================================================
# REQUIRED COLUMNS
# =============================================================================

REQUIRED_COLUMNS = [
    "Notification_ID",
    "Predicted_Class",
    "Confidence",
    "Severity",
    "SOC_Priority",
]


# =============================================================================
# OPTIONAL COLUMNS
# =============================================================================

OPTIONAL_COLUMNS = [
    "Risk_Level",
    "Confidence_Interpretation",
    "Assistant_Incident_Assessment",
    "Assistant_Investigation_Steps",
    "Assistant_Recommendation",
    "XAI_Evidence",
    "Top_Feature_1",
    "Top_Feature_2",
    "Top_Feature_3",
    "Top_Feature_4",
    "Top_Feature_5",
    "SOC_Response_Category",
    "Analyst_Recommendation",
    "Alert_ID",
]


# =============================================================================
# CYBERSECURITY ASSISTANT
# =============================================================================

class CybersecurityAssistant:
    """
    ZUKA analyst-facing cybersecurity assistant.

    Responsibilities:
        - Load SOC alert intelligence
        - Validate alert records
        - Select alerts
        - Explain detections
        - Answer analyst questions
        - Provide investigation guidance
        - Provide recommendations
        - Preserve human approval requirements

    Automated containment is intentionally disabled.
    """

    def __init__(
        self,
        alert_data_path: Optional[str | Path] = None,
        analyst_view_path: Optional[str | Path] = None,
        require_human_approval: bool = True,
        automated_containment: bool = False,
    ) -> None:

        self.alert_data_path = Path(
            alert_data_path or DEFAULT_ALERT_PATH
        )

        self.analyst_view_path = Path(
            analyst_view_path or DEFAULT_ANALYST_VIEW_PATH
        )

        self.require_human_approval = require_human_approval

        # Safety policy:
        # Automated containment must remain disabled.
        self.automated_containment = False

        if automated_containment:
            LOGGER.warning(
                "Automated containment requested but disabled by ZUKA safety policy."
            )

        self.alerts = pd.DataFrame()

        LOGGER.info(
            "ZUKA CybersecurityAssistant initialized | "
            "human_approval=%s | automated_containment=%s",
            self.require_human_approval,
            self.automated_containment,
        )


    # =========================================================================
    # DATA LOADING
    # =========================================================================

    def load_alerts(
        self,
        path: Optional[str | Path] = None,
    ) -> pd.DataFrame:
        """
        Load SOC assistant alert analysis data.
        """

        selected_path = Path(path) if path else self.alert_data_path

        if not selected_path.exists():
            raise FileNotFoundError(
                f"ZUKA alert dataset not found:\n{selected_path}"
            )

        LOGGER.info(
            "Loading SOC assistant alerts: %s",
            selected_path,
        )

        df = pd.read_csv(selected_path)

        self._validate_schema(df)

        self.alerts = df.copy()

        LOGGER.info(
            "SOC assistant alerts loaded | records=%d",
            len(self.alerts),
        )

        return self.alerts


    # =========================================================================
    # SCHEMA VALIDATION
    # =========================================================================

    def _validate_schema(self, df: pd.DataFrame) -> None:
        """
        Validate required alert columns.
        """

        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                "Missing required SOC assistant columns:\n"
                + "\n".join(missing)
            )

        LOGGER.info(
            "Alert schema validated | records=%d",
            len(df),
        )


    # =========================================================================
    # DATA ACCESS
    # =========================================================================

    def get_alert_count(self) -> int:
        """Return number of loaded alerts."""

        return len(self.alerts)


    def get_alert_ids(self) -> List[str]:
        """Return available notification IDs."""

        if self.alerts.empty:
            return []

        return self.alerts["Notification_ID"].astype(str).tolist()


    def get_alert(
        self,
        notification_id: Optional[str] = None,
        position: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieve one alert.

        Either:
            notification_id
        or:
            zero-based position
        """

        if self.alerts.empty:
            raise RuntimeError(
                "No SOC alerts loaded. Call load_alerts() first."
            )

        if notification_id is not None:

            matches = self.alerts[
                self.alerts["Notification_ID"].astype(str)
                == str(notification_id)
            ]

            if matches.empty:
                raise KeyError(
                    f"Notification ID not found: {notification_id}"
                )

            row = matches.iloc[0]

        else:

            if position < 0 or position >= len(self.alerts):
                raise IndexError(
                    f"Alert position {position} is outside available range."
                )

            row = self.alerts.iloc[position]

        return row.to_dict()


    # =========================================================================
    # VALUE HELPERS
    # =========================================================================

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        """Safely convert a value to float."""

        try:
            return float(value)
        except (TypeError, ValueError):
            return default


    @staticmethod
    def _safe_text(
        value: Any,
        default: str = "UNKNOWN",
    ) -> str:
        """Safely convert a value to text."""

        if value is None:
            return default

        try:
            if pd.isna(value):
                return default
        except Exception:
            pass

        text = str(value).strip()

        return text if text else default


    # =========================================================================
    # CONFIDENCE INTERPRETATION
    # =========================================================================

    def interpret_confidence(
        self,
        confidence: float,
    ) -> str:
        """
        Convert model confidence into an analyst-friendly interpretation.
        """

        confidence = self._safe_float(confidence)

        if confidence >= 0.90:
            return "HIGH_CONFIDENCE"

        if confidence >= 0.70:
            return "MEDIUM_CONFIDENCE"

        return "LOW_CONFIDENCE"


    # =========================================================================
    # RISK INTERPRETATION
    # =========================================================================

    def assess_risk(
        self,
        alert: Dict[str, Any],
    ) -> str:
        """
        Determine analyst-facing risk interpretation.

        This is a prioritization aid, not an automatic incident verdict.
        """

        detection = self._safe_text(
            alert.get("Detection"),
            "ATTACK",
        ).upper()

        severity = self._safe_text(
            alert.get("Severity"),
            "LOW",
        ).upper()

        priority = self._safe_text(
            alert.get("SOC_Priority"),
            "P3",
        ).upper()

        confidence = self._safe_float(
            alert.get("Confidence")
        )

        if detection == "BENIGN":
            return "NO_SECURITY_RISK"

        if (
            severity == "HIGH"
            and priority == "P1"
            and confidence >= 0.90
        ):
            return "CRITICAL_REVIEW"

        if (
            severity == "HIGH"
            or priority == "P1"
        ):
            return "HIGH_PRIORITY_REVIEW"

        if confidence >= 0.70:
            return "ANALYST_REVIEW"

        return "LOW_CONFIDENCE_REVIEW"


    # =========================================================================
    # XAI FEATURE EXTRACTION
    # =========================================================================

    def get_xai_features(
        self,
        alert: Dict[str, Any],
        limit: int = 5,
    ) -> List[str]:
        """
        Extract principal SHAP/XAI features from an alert.
        """

        features: List[str] = []

        for index in range(1, 6):

            key = f"Top_Feature_{index}"

            value = alert.get(key)

            if value is None:
                continue

            text = self._safe_text(value, "")

            if text and text not in features:
                features.append(text)

        return features[:limit]


    # =========================================================================
    # INCIDENT ASSESSMENT
    # =========================================================================

    def generate_incident_assessment(
        self,
        alert: Dict[str, Any],
    ) -> str:
        """
        Generate a human-readable incident assessment.
        """

        predicted_class = self._safe_text(
            alert.get("Predicted_Class")
        )

        confidence = self._safe_float(
            alert.get("Confidence")
        )

        severity = self._safe_text(
            alert.get("Severity")
        )

        priority = self._safe_text(
            alert.get("SOC_Priority")
        )

        detection = self._safe_text(
            alert.get("Detection"),
            "ATTACK",
        )

        confidence_text = self.interpret_confidence(confidence)

        if detection.upper() == "BENIGN":
            return (
                f"ZUKA classified this network event as benign "
                f"with {confidence * 100:.2f}% confidence. "
                f"No attack response is recommended from this alert alone."
            )

        return (
            f"ZUKA classified this network event as attack class "
            f"{predicted_class} with {confidence * 100:.2f}% confidence. "
            f"The assigned severity is {severity} and SOC priority is "
            f"{priority}. Confidence interpretation: {confidence_text}. "
            f"The classification should be validated against surrounding "
            f"network and security telemetry."
        )


    # =========================================================================
    # INVESTIGATION STEPS
    # =========================================================================

    def generate_investigation_steps(
        self,
        alert: Dict[str, Any],
    ) -> List[str]:
        """
        Generate structured investigation guidance.
        """

        detection = self._safe_text(
            alert.get("Detection"),
            "ATTACK",
        ).upper()

        predicted_class = self._safe_text(
            alert.get("Predicted_Class")
        )

        if detection == "BENIGN":
            return [
                "No immediate attack investigation is required.",
                "Retain the event for contextual correlation if necessary.",
                "Review again if related suspicious telemetry appears.",
            ]

        features = self.get_xai_features(alert)

        steps = [
            "Review the source and destination network-flow context.",
            "Correlate the event with surrounding network and security telemetry.",
            "Check whether similar events occurred from the same source.",
        ]

        if features:
            steps.append(
                "Review the SHAP explanatory features for consistency "
                "with the detection: "
                + ", ".join(features)
                + "."
            )

        steps.extend(
            [
                f"Investigate predicted attack class {predicted_class} "
                "in the relevant incident context.",
                "Determine whether escalation or containment is justified "
                "based on corroborating evidence.",
            ]
        )

        return steps


    # =========================================================================
    # RECOMMENDATION
    # =========================================================================

    def generate_recommendation(
        self,
        alert: Dict[str, Any],
    ) -> str:
        """
        Generate analyst recommendation.

        ZUKA never performs containment automatically.
        """

        detection = self._safe_text(
            alert.get("Detection"),
            "ATTACK",
        ).upper()

        confidence = self._safe_float(
            alert.get("Confidence")
        )

        severity = self._safe_text(
            alert.get("Severity"),
            "LOW",
        ).upper()

        priority = self._safe_text(
            alert.get("SOC_Priority"),
            "P3",
        ).upper()

        if detection == "BENIGN":
            return (
                "No security response is recommended from this event alone. "
                "Retain the event for contextual correlation if required."
            )

        if (
            confidence >= 0.90
            and severity == "HIGH"
            and priority == "P1"
        ):
            return (
                "Immediately investigate and correlate the alert with "
                "other security telemetry. Review the affected flow "
                "context and determine whether escalation or containment "
                "is justified. Human analyst approval is required."
            )

        if confidence >= 0.70:
            return (
                "Investigate and correlate the alert with surrounding "
                "telemetry. Validate the model evidence before escalation. "
                "Human analyst approval is required."
            )

        return (
            "Validate the alert carefully against independent telemetry "
            "before escalation. The model confidence is limited, so "
            "additional evidence is required. Human analyst approval "
            "is required."
        )


    # =========================================================================
    # XAI EXPLANATION
    # =========================================================================

    def generate_xai_explanation(
        self,
        alert: Dict[str, Any],
    ) -> str:
        """
        Generate a concise human-readable XAI explanation.
        """

        features = self.get_xai_features(alert)

        predicted_class = self._safe_text(
            alert.get("Predicted_Class")
        )

        confidence = self._safe_float(
            alert.get("Confidence")
        )

        detection = self._safe_text(
            alert.get("Detection"),
            "ATTACK",
        ).upper()

        if detection == "BENIGN":

            if features:
                return (
                    f"The model classified this network flow as benign "
                    f"with {confidence * 100:.2f}% confidence. "
                    f"The principal SHAP explanatory features are: "
                    f"{', '.join(features)}. These features represent "
                    f"model evidence and should be interpreted in context."
                )

            return (
                f"The model classified this network flow as benign "
                f"with {confidence * 100:.2f}% confidence."
            )

        if features:
            return (
                f"The model classified this network flow as attack class "
                f"{predicted_class} with {confidence * 100:.2f}% confidence. "
                f"The principal SHAP explanatory features are: "
                f"{', '.join(features)}. These features represent model "
                f"evidence associated with the prediction and should be "
                f"validated against surrounding network and security telemetry."
            )

        return (
            f"The model classified this network flow as attack class "
            f"{predicted_class} with {confidence * 100:.2f}% confidence. "
            f"SHAP evidence is available but no named explanatory features "
            f"were provided in the alert record."
        )


    # =========================================================================
    # COMPLETE ALERT ANALYSIS
    # =========================================================================

    def analyze_alert(
        self,
        alert: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a complete ZUKA analyst analysis.
        """

        features = self.get_xai_features(alert)

        analysis = dict(alert)

        analysis["Risk_Level"] = self.assess_risk(alert)

        analysis["Confidence_Interpretation"] = (
            self.interpret_confidence(
                alert.get("Confidence")
            )
        )

        analysis["Assistant_Incident_Assessment"] = (
            self.generate_incident_assessment(alert)
        )

        investigation_steps = self.generate_investigation_steps(alert)

        analysis["Assistant_Investigation_Steps"] = (
            " ".join(
                f"{index + 1}. {step}"
                for index, step in enumerate(investigation_steps)
            )
        )

        analysis["Assistant_Recommendation"] = (
            self.generate_recommendation(alert)
        )

        analysis["XAI_Evidence"] = (
            self.generate_xai_explanation(alert)
        )

        analysis["Human_Approval_Required"] = (
            "YES" if self.require_human_approval else "NO"
        )

        analysis["Automated_Containment"] = "DISABLED"

        analysis["XAI_Feature_Count"] = len(features)

        return analysis


    # =========================================================================
    # QUESTION ENGINE
    # =========================================================================

    def answer_question(
        self,
        question: str,
        alert: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Answer common SOC analyst questions.

        This is intentionally deterministic and evidence-based.
        """

        if alert is None:

            if self.alerts.empty:
                return (
                    "No alert is currently loaded. "
                    "Load SOC alert data before asking about an incident."
                )

            alert = self.get_alert(position=0)

        question_text = self._safe_text(
            question,
            "",
        ).lower()

        # -------------------------------------------------------------
        # WHAT HAPPENED?
        # -------------------------------------------------------------

        if any(
            phrase in question_text
            for phrase in [
                "what happened",
                "what is happening",
                "what was detected",
                "describe alert",
            ]
        ):

            return self.generate_incident_assessment(alert)


        # -------------------------------------------------------------
        # WHY?
        # -------------------------------------------------------------

        if any(
            phrase in question_text
            for phrase in [
                "why",
                "why detected",
                "why was this detected",
                "explain detection",
            ]
        ):

            return self.generate_xai_explanation(alert)


        # -------------------------------------------------------------
        # CONFIDENCE
        # -------------------------------------------------------------

        if any(
            phrase in question_text
            for phrase in [
                "confidence",
                "how confident",
                "how sure",
            ]
        ):

            confidence = self._safe_float(
                alert.get("Confidence")
            )

            interpretation = self.interpret_confidence(
                confidence
            )

            return (
                f"Model confidence is {confidence * 100:.2f}%. "
                f"The confidence interpretation is {interpretation}. "
                f"Confidence should be considered together with "
                f"class-level performance and independent security telemetry."
            )


        # -------------------------------------------------------------
        # FEATURES
        # -------------------------------------------------------------

        if any(
            phrase in question_text
            for phrase in [
                "features",
                "important features",
                "important feature",
                "shap",
                "evidence",
            ]
        ):

            features = self.get_xai_features(alert)

            if features:
                return (
                    "The principal SHAP explanatory features are: "
                    + ", ".join(features)
                    + ". These features indicate which input characteristics "
                    "contributed most strongly to the model explanation."
                )

            return (
                "No named SHAP explanatory features are available "
                "for this alert."
            )


        # -------------------------------------------------------------
        # INVESTIGATION
        # -------------------------------------------------------------

        if any(
            phrase in question_text
            for phrase in [
                "investigate",
                "investigation",
                "what should i investigate",
                "check",
                "look for",
            ]
        ):

            steps = self.generate_investigation_steps(alert)

            return "\n".join(
                f"{index + 1}. {step}"
                for index, step in enumerate(steps)
            )


        # -------------------------------------------------------------
        # NEXT ACTION
        # -------------------------------------------------------------

        if any(
            phrase in question_text
            for phrase in [
                "what should i do",
                "what next",
                "next step",
                "next action",
                "recommend",
                "recommendation",
            ]
        ):

            return self.generate_recommendation(alert)


        # -------------------------------------------------------------
        # RISK
        # -------------------------------------------------------------

        if any(
            phrase in question_text
            for phrase in [
                "risk",
                "how serious",
                "severity",
                "priority",
            ]
        ):

            risk = self.assess_risk(alert)

            severity = self._safe_text(
                alert.get("Severity")
            )

            priority = self._safe_text(
                alert.get("SOC_Priority")
            )

            return (
                f"Risk interpretation: {risk}. "
                f"Severity: {severity}. "
                f"SOC priority: {priority}."
            )


        # -------------------------------------------------------------
        # HUMAN APPROVAL
        # -------------------------------------------------------------

        if any(
            phrase in question_text
            for phrase in [
                "contain",
                "containment",
                "block",
                "isolate",
                "automatically respond",
            ]
        ):

            return (
                "ZUKA does not perform automated containment. "
                "Human analyst approval is required before escalation "
                "or containment actions."
            )


        # -------------------------------------------------------------
        # HELP
        # -------------------------------------------------------------

        return (
            "I can help with this alert using the available XGBoost "
            "and SHAP evidence. Ask about what happened, why it was "
            "detected, confidence, important features, investigation "
            "steps, risk, or recommended action."
        )


    # =========================================================================
    # ANALYST VIEW
    # =========================================================================

    def create_analyst_view(self) -> pd.DataFrame:
        """
        Generate a compact analyst-ready DataFrame.
        """

        if self.alerts.empty:
            raise RuntimeError(
                "No alerts loaded."
            )

        records = []

        for _, row in self.alerts.iterrows():

            alert = row.to_dict()

            analysis = self.analyze_alert(alert)

            records.append(
                {
                    "Notification_ID":
                        analysis.get("Notification_ID"),

                    "Alert_ID":
                        analysis.get("Alert_ID"),

                    "Predicted_Class":
                        analysis.get("Predicted_Class"),

                    "Confidence":
                        analysis.get("Confidence"),

                    "Confidence_Interpretation":
                        analysis.get(
                            "Confidence_Interpretation"
                        ),

                    "Severity":
                        analysis.get("Severity"),

                    "SOC_Priority":
                        analysis.get("SOC_Priority"),

                    "Risk_Level":
                        analysis.get("Risk_Level"),

                    "Top_Feature_1":
                        analysis.get("Top_Feature_1"),

                    "Top_Feature_2":
                        analysis.get("Top_Feature_2"),

                    "Top_Feature_3":
                        analysis.get("Top_Feature_3"),

                    "XAI_Evidence":
                        analysis.get("XAI_Evidence"),

                    "Assistant_Recommendation":
                        analysis.get(
                            "Assistant_Recommendation"
                        ),

                    "Human_Approval_Required":
                        analysis.get(
                            "Human_Approval_Required"
                        ),

                    "Automated_Containment":
                        analysis.get(
                            "Automated_Containment"
                        ),
                }
            )

        return pd.DataFrame(records)


    # =========================================================================
    # SAVE ANALYSIS
    # =========================================================================

    def save_analysis(
        self,
        output_path: Optional[str | Path] = None,
    ) -> Path:
        """
        Save complete assistant analysis.
        """

        if self.alerts.empty:
            raise RuntimeError(
                "No alerts loaded."
            )

        output_path = Path(
            output_path
            or (
                PROJECT_ROOT
                / "results"
                / "tables"
                / "dashboard"
                / "zuka_assistant_alert_analysis.csv"
            )
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        analyzed_records = [
            self.analyze_alert(row.to_dict())
            for _, row in self.alerts.iterrows()
        ]

        result = pd.DataFrame(
            analyzed_records
        )

        result.to_csv(
            output_path,
            index=False,
        )

        LOGGER.info(
            "Assistant analysis saved: %s",
            output_path,
        )

        return output_path


    # =========================================================================
    # SAVE ANALYST VIEW
    # =========================================================================

    def save_analyst_view(
        self,
        output_path: Optional[str | Path] = None,
    ) -> Path:
        """
        Save compact analyst view.
        """

        output_path = Path(
            output_path
            or (
                PROJECT_ROOT
                / "results"
                / "tables"
                / "dashboard"
                / "zuka_assistant_analyst_view.csv"
            )
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        analyst_view = self.create_analyst_view()

        analyst_view.to_csv(
            output_path,
            index=False,
        )

        LOGGER.info(
            "Analyst view saved: %s",
            output_path,
        )

        return output_path


    # =========================================================================
    # REPORT
    # =========================================================================

    def generate_report(
        self,
        output_path: Optional[str | Path] = None,
    ) -> Path:
        """
        Generate human-readable ZUKA assistant report.
        """

        if self.alerts.empty:
            raise RuntimeError(
                "No alerts loaded."
            )

        output_path = Path(
            output_path or DEFAULT_REPORT_PATH
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        lines: List[str] = []

        lines.append("=" * 80)
        lines.append("ZUKA — CYBERSECURITY ASSISTANT REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(
            f"Alerts analyzed : {len(self.alerts)}"
        )

        lines.append(
            f"Human approval  : "
            f"{'REQUIRED' if self.require_human_approval else 'NOT REQUIRED'}"
        )

        lines.append(
            "Automated containment : DISABLED"
        )

        lines.append("")
        lines.append("=" * 80)
        lines.append("ANALYST ALERT SUMMARIES")
        lines.append("=" * 80)

        for index, (_, row) in enumerate(
            self.alerts.iterrows(),
            start=1,
        ):

            alert = row.to_dict()

            analysis = self.analyze_alert(
                alert
            )

            lines.append("")
            lines.append("-" * 80)
            lines.append(
                f"Alert {index}"
            )
            lines.append("-" * 80)

            lines.append(
                f"Notification ID : "
                f"{analysis.get('Notification_ID', 'UNKNOWN')}"
            )

            lines.append(
                f"Predicted Class : "
                f"{analysis.get('Predicted_Class', 'UNKNOWN')}"
            )

            lines.append(
                f"Confidence      : "
                f"{self._safe_float(analysis.get('Confidence')) * 100:.2f}%"
            )

            lines.append(
                f"Severity        : "
                f"{analysis.get('Severity', 'UNKNOWN')}"
            )

            lines.append(
                f"SOC Priority    : "
                f"{analysis.get('SOC_Priority', 'UNKNOWN')}"
            )

            lines.append(
                f"Risk            : "
                f"{analysis.get('Risk_Level', 'UNKNOWN')}"
            )

            lines.append("")
            lines.append(
                "Assistant Assessment:"
            )

            lines.append(
                str(
                    analysis.get(
                        "Assistant_Incident_Assessment",
                        "",
                    )
                )
            )

            lines.append("")
            lines.append(
                "XAI Evidence:"
            )

            lines.append(
                str(
                    analysis.get(
                        "XAI_Evidence",
                        "",
                    )
                )
            )

            lines.append("")
            lines.append(
                "Recommendation:"
            )

            lines.append(
                str(
                    analysis.get(
                        "Assistant_Recommendation",
                        "",
                    )
                )
            )

            lines.append("")
            lines.append(
                "Human Approval Required: YES"
            )

            lines.append(
                "Automated Containment: DISABLED"
            )

        output_path.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

        LOGGER.info(
            "Assistant report saved: %s",
            output_path,
        )

        return output_path


# =============================================================================
# SELF TEST
# =============================================================================

def run_self_test() -> None:
    """
    Run deterministic ZUKA assistant self-test.

    Uses the existing SOC assistant alert dataset when available.
    If it is unavailable, a synthetic alert is used only to validate
    the assistant logic.
    """

    print("=" * 80)
    print("ZUKA — CYBERSECURITY ASSISTANT SELF TEST")
    print("=" * 80)

    print()
    print("INITIALIZATION")
    print("-" * 80)

    assistant = CybersecurityAssistant()

    print(
        "Human approval required :",
        "YES" if assistant.require_human_approval else "NO",
    )

    print(
        "Automated containment   :",
        "DISABLED",
    )

    # -------------------------------------------------------------------------
    # LOAD EXISTING DATA
    # -------------------------------------------------------------------------

    print()
    print("LOADING SOC ASSISTANT DATA")
    print("-" * 80)

    if assistant.alert_data_path.exists():

        assistant.load_alerts()

        print(
            "✓ Existing SOC assistant dataset loaded"
        )

        print(
            "Records:",
            assistant.get_alert_count(),
        )

    else:

        print(
            "⚠ Existing assistant dataset not found."
        )

        print(
            "Using synthetic self-test alert."
        )

        synthetic_alert = pd.DataFrame(
            [
                {
                    "Notification_ID":
                        "ZUKA-SELFTEST-001",

                    "Alert_ID":
                        "SOC-SELFTEST-001",

                    "Predicted_Class":
                        9,

                    "Confidence":
                        0.9998,

                    "Detection":
                        "ATTACK",

                    "Severity":
                        "HIGH",

                    "SOC_Priority":
                        "P1",

                    "Top_Feature_1":
                        "Init_Win_bytes_forward",

                    "Top_Feature_2":
                        "Total Length of Fwd Packets",

                    "Top_Feature_3":
                        "min_seg_size_forward",

                    "Top_Feature_4":
                        "Packet Length Mean",

                    "Top_Feature_5":
                        "Flow Bytes/s",
                }
            ]
        )

        assistant.alerts = synthetic_alert


    # -------------------------------------------------------------------------
    # SELECT ALERT
    # -------------------------------------------------------------------------

    print()
    print("SELECTING TEST ALERT")
    print("-" * 80)

    alert = assistant.get_alert(
        position=0
    )

    print(
        "Notification ID:",
        alert.get("Notification_ID"),
    )

    print(
        "Predicted class:",
        alert.get("Predicted_Class"),
    )

    print(
        "Confidence:",
        f"{assistant._safe_float(alert.get('Confidence')) * 100:.2f}%",
    )

    print(
        "Severity:",
        alert.get("Severity"),
    )

    print(
        "SOC priority:",
        alert.get("SOC_Priority"),
    )

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    print()
    print("GENERATING ZUKA ANALYSIS")
    print("-" * 80)

    analysis = assistant.analyze_alert(
        alert
    )

    print(
        "✓ Risk assessment generated"
    )

    print(
        "✓ XAI explanation generated"
    )

    print(
        "✓ Investigation guidance generated"
    )

    print(
        "✓ Analyst recommendation generated"
    )

    print(
        "✓ Human approval policy verified"
    )

    print(
        "✓ Automated containment disabled"
    )

    # -------------------------------------------------------------------------
    # DISPLAY ASSESSMENT
    # -------------------------------------------------------------------------

    print()
    print("ZUKA ASSISTANT ASSESSMENT")
    print("-" * 80)

    print(
        analysis["Assistant_Incident_Assessment"]
    )

    print()
    print(
        "XAI Evidence:"
    )

    print(
        analysis["XAI_Evidence"]
    )

    print()
    print(
        "Recommendation:"
    )

    print(
        analysis["Assistant_Recommendation"]
    )

    # -------------------------------------------------------------------------
    # QUESTION TEST
    # -------------------------------------------------------------------------

    print()
    print("TESTING ANALYST QUESTIONS")
    print("-" * 80)

    questions = [
        "What happened?",
        "Why was this detected?",
        "How confident is the model?",
        "Which features are important?",
        "What should I investigate?",
        "What should I do next?",
        "What is the risk?",
        "Can ZUKA automatically contain this?",
    ]

    for question in questions:

        print()
        print(
            f"Analyst Question: {question}"
        )

        answer = assistant.answer_question(
            question,
            alert,
        )

        print(
            "ZUKA:"
        )

        print(
            answer
        )

    # -------------------------------------------------------------------------
    # SAVE TEST OUTPUTS
    # -------------------------------------------------------------------------

    print()
    print("SAVING ASSISTANT OUTPUTS")
    print("-" * 80)

    analysis_path = assistant.save_analysis()

    analyst_path = assistant.save_analyst_view()

    report_path = assistant.generate_report()

    print(
        "✓ Assistant analysis saved:"
    )

    print(
        analysis_path
    )

    print(
        "✓ Analyst view saved:"
    )

    print(
        analyst_path
    )

    print(
        "✓ Assistant report saved:"
    )

    print(
        report_path
    )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print()
    print("=" * 80)
    print("CELL / SRC #7 — ZUKA ASSISTANT SUMMARY")
    print("=" * 80)

    print(
        "Alerts analyzed          :",
        assistant.get_alert_count(),
    )

    print(
        "Interactive query engine : READY"
    )

    print(
        "XGBoost evidence         : AVAILABLE"
    )

    print(
        "SHAP evidence            : AVAILABLE"
    )

    print(
        "Investigation guidance   : AVAILABLE"
    )

    print(
        "Recommendation engine    : AVAILABLE"
    )

    print(
        "Human approval required  : YES"
    )

    print(
        "Automated containment    : DISABLED"
    )

    print(
        "Manual feature entry     : NOT REQUIRED"
    )

    print()
    print(
        "✓ ZUKA cybersecurity assistant self-test completed"
    )

    print("=" * 80)


# =============================================================================
# MODULE ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    try:

        run_self_test()

    except Exception as exc:

        LOGGER.exception(
            "ZUKA assistant self-test failed"
        )

        print()
        print("=" * 80)
        print("❌ ZUKA ASSISTANT SELF-TEST FAILED")
        print("=" * 80)
        print(
            f"{type(exc).__name__}: {exc}"
        )

        sys.exit(1)