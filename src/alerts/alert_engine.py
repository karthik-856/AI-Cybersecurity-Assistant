"""
ZUKA — SOC Alert Engine

Converts XGBoost predictions and SHAP explanations into
structured SOC alerts.

The engine does NOT automatically contain or block traffic.
It produces analyst-facing alerts requiring human review.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


LOGGER = logging.getLogger("zuka.alerts")


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "results" / "tables" / "alerts"
)

DEFAULT_REPORT_DIR = (
    PROJECT_ROOT / "results" / "reports" / "alerts"
)


# =============================================================================
# ALERT ENGINE
# =============================================================================

class AlertEngine:
    """
    ZUKA SOC alert generation engine.

    Alert policy
    ------------
    Class 0:
        BENIGN

    Confidence >= 0.90:
        HIGH confidence

    Confidence >= 0.70:
        MEDIUM confidence

    Confidence < 0.70:
        LOW confidence

    Attack severity:
        HIGH confidence attack -> HIGH severity / P1

        MEDIUM confidence attack -> MEDIUM severity / P2

        LOW confidence attack -> LOW severity / P3
    """

    BENIGN_CLASS = 0

    HIGH_CONFIDENCE = 0.90
    MEDIUM_CONFIDENCE = 0.70

    def __init__(
        self,
        output_dir: str | Path = DEFAULT_OUTPUT_DIR,
        report_dir: str | Path = DEFAULT_REPORT_DIR,
    ) -> None:

        self.output_dir = Path(output_dir)
        self.report_dir = Path(report_dir)

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.report_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        LOGGER.info(
            "ZUKA AlertEngine initialized"
        )

    # =========================================================================
    # CONFIDENCE
    # =========================================================================

    def confidence_level(
        self,
        confidence: float,
    ) -> str:

        if confidence >= self.HIGH_CONFIDENCE:
            return "HIGH_CONFIDENCE"

        if confidence >= self.MEDIUM_CONFIDENCE:
            return "MEDIUM_CONFIDENCE"

        return "LOW_CONFIDENCE"

    # =========================================================================
    # SEVERITY
    # =========================================================================

    def severity(
        self,
        predicted_class: int,
        confidence: float,
    ) -> str:

        if predicted_class == self.BENIGN_CLASS:
            return "NONE"

        if confidence >= self.HIGH_CONFIDENCE:
            return "HIGH"

        if confidence >= self.MEDIUM_CONFIDENCE:
            return "MEDIUM"

        return "LOW"

    # =========================================================================
    # SOC PRIORITY
    # =========================================================================

    def priority(
        self,
        predicted_class: int,
        confidence: float,
    ) -> str:

        if predicted_class == self.BENIGN_CLASS:
            return "NONE"

        if confidence >= self.HIGH_CONFIDENCE:
            return "P1"

        if confidence >= self.MEDIUM_CONFIDENCE:
            return "P2"

        return "P3"

    # =========================================================================
    # RESPONSE CATEGORY
    # =========================================================================

    def response_category(
        self,
        predicted_class: int,
        confidence: float,
    ) -> str:

        if predicted_class == self.BENIGN_CLASS:
            return "NO_ACTION"

        if confidence >= self.HIGH_CONFIDENCE:
            return "INVESTIGATE_AND_CORRELATE"

        if confidence >= self.MEDIUM_CONFIDENCE:
            return "ANALYST_REVIEW"

        return "VALIDATE_BEFORE_ESCALATION"

    # =========================================================================
    # RECOMMENDATION
    # =========================================================================

    def recommendation(
        self,
        predicted_class: int,
        confidence: float,
        severity: str,
    ) -> str:

        if predicted_class == self.BENIGN_CLASS:

            return (
                "No security response is required. "
                "Retain the event for monitoring and audit purposes."
            )

        if severity == "HIGH":

            return (
                "Immediately investigate and correlate the alert "
                "with surrounding network and security telemetry. "
                "Review the affected flow context and determine "
                "whether escalation or containment is justified."
            )

        if severity == "MEDIUM":

            return (
                "Review the alert and correlate it with surrounding "
                "network and security telemetry before escalation."
            )

        return (
            "Validate the detection against additional telemetry "
            "before escalating or taking containment action."
        )

    # =========================================================================
    # XAI EXPLANATION
    # =========================================================================

    def build_xai_explanation(
        self,
        predicted_class: int,
        confidence: float,
        top_features: list[dict[str, Any]],
    ) -> str:

        if predicted_class == self.BENIGN_CLASS:

            prefix = (
                "ZUKA classified this network event as "
                f"benign class {predicted_class} "
                f"with {confidence * 100:.2f}% confidence."
            )

        else:

            prefix = (
                "ZUKA classified this network event as "
                f"attack class {predicted_class} "
                f"with {confidence * 100:.2f}% confidence."
            )

        if not top_features:

            return (
                prefix
                + " No SHAP explanatory features were available."
            )

        feature_names = [
            item["Feature"]
            for item in top_features
        ]

        feature_text = ", ".join(feature_names)

        return (
            prefix
            + " The principal SHAP explanatory features are: "
            + feature_text
            + ". These represent model evidence associated "
              "with the prediction and should be validated "
              "against surrounding network telemetry."
        )

    # =========================================================================
    # ALERT ID
    # =========================================================================

    @staticmethod
    def generate_alert_id(
        sequence: int,
    ) -> str:

        timestamp = datetime.now(
            timezone.utc
        ).strftime("%Y%m%d%H%M%S")

        return (
            f"SOC-{timestamp}-"
            f"{sequence:04d}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

    # =========================================================================
    # SINGLE ALERT
    # =========================================================================

    def create_alert(
        self,
        predicted_class: int,
        confidence: float,
        top_features: list[dict[str, Any]] | None = None,
        source: str = "automatic_detection",
        event_id: int | str | None = None,
        sequence: int = 1,
    ) -> dict[str, Any]:

        predicted_class = int(predicted_class)
        confidence = float(confidence)

        top_features = top_features or []

        severity = self.severity(
            predicted_class,
            confidence,
        )

        priority = self.priority(
            predicted_class,
            confidence,
        )

        response_category = self.response_category(
            predicted_class,
            confidence,
        )

        confidence_interpretation = (
            self.confidence_level(confidence)
        )

        recommendation = self.recommendation(
            predicted_class,
            confidence,
            severity,
        )

        explanation = self.build_xai_explanation(
            predicted_class,
            confidence,
            top_features,
        )

        alert = {
            "Alert_ID": self.generate_alert_id(sequence),
            "Event_ID": event_id,
            "Timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "Source": source,

            "Predicted_Class": predicted_class,
            "Confidence": confidence,

            "Detection": (
                "BENIGN"
                if predicted_class == self.BENIGN_CLASS
                else "ATTACK"
            ),

            "Confidence_Level": confidence_interpretation,
            "Severity": severity,
            "SOC_Priority": priority,
            "SOC_Response_Category": response_category,

            "Top_Feature_1": None,
            "Top_Feature_1_Value": None,
            "Top_Feature_1_SHAP": None,

            "Top_Feature_2": None,
            "Top_Feature_2_Value": None,
            "Top_Feature_2_SHAP": None,

            "Top_Feature_3": None,
            "Top_Feature_3_Value": None,
            "Top_Feature_3_SHAP": None,

            "XAI_Explanation": explanation,
            "Analyst_Recommendation": recommendation,
        }

        # ---------------------------------------------------------------------
        # Insert top three SHAP features
        # ---------------------------------------------------------------------

        for rank, feature in enumerate(
            top_features[:3],
            start=1,
        ):

            alert[f"Top_Feature_{rank}"] = (
                feature.get("Feature")
            )

            alert[f"Top_Feature_{rank}_Value"] = (
                feature.get("Feature_Value")
            )

            alert[f"Top_Feature_{rank}_SHAP"] = (
                feature.get("SHAP_Value")
            )

        return alert

    # =========================================================================
    # BATCH ALERTS
    # =========================================================================

    def create_alerts(
        self,
        predictions: np.ndarray | list[int],
        probabilities: np.ndarray,
        top_features: list[list[dict[str, Any]]],
        source: str = "automatic_detection",
    ) -> pd.DataFrame:
        """
        Create SOC alerts for a batch of predictions.
        """

        predictions = np.asarray(
            predictions
        )

        probabilities = np.asarray(
            probabilities
        )

        if len(predictions) != len(probabilities):

            raise ValueError(
                "Prediction/probability record count mismatch."
            )

        if len(predictions) != len(top_features):

            raise ValueError(
                "Prediction/SHAP explanation count mismatch."
            )

        alerts = []

        for index in range(len(predictions)):

            predicted_class = int(
                predictions[index]
            )

            confidence = float(
                probabilities[index].max()
            )

            alert = self.create_alert(
                predicted_class=predicted_class,
                confidence=confidence,
                top_features=top_features[index],
                source=source,
                event_id=index,
                sequence=index + 1,
            )

            alerts.append(alert)

        dataframe = pd.DataFrame(alerts)

        LOGGER.info(
            "SOC alerts generated | records=%d | attacks=%d | benign=%d",
            len(dataframe),
            int(
                (dataframe["Detection"] == "ATTACK").sum()
            ),
            int(
                (dataframe["Detection"] == "BENIGN").sum()
            ),
        )

        return dataframe

    # =========================================================================
    # ATTACK QUEUE
    # =========================================================================

    def attack_queue(
        self,
        alerts: pd.DataFrame,
    ) -> pd.DataFrame:

        required = [
            "Detection",
            "Confidence",
            "Severity",
            "SOC_Priority",
        ]

        missing = [
            column
            for column in required
            if column not in alerts.columns
        ]

        if missing:

            raise ValueError(
                "Missing alert columns:\n"
                + "\n".join(missing)
            )

        queue = alerts[
            alerts["Detection"] == "ATTACK"
        ].copy()

        priority_order = {
            "P1": 1,
            "P2": 2,
            "P3": 3,
            "NONE": 4,
        }

        queue["_Priority_Order"] = (
            queue["SOC_Priority"]
            .map(priority_order)
            .fillna(99)
        )

        queue = queue.sort_values(
            by=[
                "_Priority_Order",
                "Confidence",
            ],
            ascending=[
                True,
                False,
            ],
        )

        queue = queue.drop(
            columns="_Priority_Order"
        )

        queue.insert(
            0,
            "Alert_Queue_Position",
            range(1, len(queue) + 1),
        )

        return queue.reset_index(
            drop=True
        )

    # =========================================================================
    # SAVE
    # =========================================================================

    def save_alerts(
        self,
        alerts: pd.DataFrame,
        filename: str = "zuka_soc_alerts.csv",
    ) -> Path:

        path = self.output_dir / filename

        alerts.to_csv(
            path,
            index=False,
        )

        LOGGER.info(
            "SOC alerts saved: %s",
            path,
        )

        return path

    # =========================================================================
    # REPORT
    # =========================================================================

    def save_report(
        self,
        alerts: pd.DataFrame,
        filename: str = "zuka_alert_engine_report.txt",
    ) -> Path:

        path = self.report_dir / filename

        total = len(alerts)

        attacks = int(
            (alerts["Detection"] == "ATTACK").sum()
        )

        benign = int(
            (alerts["Detection"] == "BENIGN").sum()
        )

        high = int(
            (alerts["Severity"] == "HIGH").sum()
        )

        medium = int(
            (alerts["Severity"] == "MEDIUM").sum()
        )

        low = int(
            (alerts["Severity"] == "LOW").sum()
        )

        report = f"""
================================================================================
ZUKA — SOC ALERT ENGINE REPORT
================================================================================

Total events       : {total}
Attack alerts      : {attacks}
Benign events      : {benign}
High severity      : {high}
Medium severity    : {medium}
Low severity       : {low}

Automated containment : DISABLED
Human analyst review  : REQUIRED

The alert engine converts model predictions and SHAP evidence
into structured SOC analyst records.

================================================================================
"""

        path.write_text(
            report.strip() + "\n",
            encoding="utf-8",
        )

        LOGGER.info(
            "SOC alert report saved: %s",
            path,
        )

        return path

    # =========================================================================
    # SELF TEST
    # =========================================================================

    def self_test(self) -> None:

        print("=" * 80)
        print("ZUKA — SOC ALERT ENGINE SELF TEST")
        print("=" * 80)

        predictions = np.array(
            [0, 9]
        )

        probabilities = np.array(
            [
                [0.9988, 0.0012],
                [0.0002, 0.9998],
            ]
        )

        top_features = [
            [
                {
                    "Feature": "Average Packet Size",
                    "Feature_Value": 37.0,
                    "SHAP_Value": 0.75,
                }
            ],
            [
                {
                    "Feature": "Destination Port",
                    "Feature_Value": 443.0,
                    "SHAP_Value": 1.21,
                },
                {
                    "Feature": "Flow Duration",
                    "Feature_Value": 1200.0,
                    "SHAP_Value": 0.91,
                },
                {
                    "Feature": "Total Fwd Packets",
                    "Feature_Value": 15.0,
                    "SHAP_Value": 0.72,
                },
            ],
        ]

        print()
        print("INPUT")
        print("-" * 80)
        print("Records  : 2")
        print("Classes  : benign + attack")
        print("✓ Input prepared")

        print()
        print("GENERATING ALERTS")
        print("-" * 80)

        alerts = self.create_alerts(
            predictions=predictions,
            probabilities=probabilities,
            top_features=top_features,
            source="ZUKA_SELF_TEST",
        )

        print(alerts[
            [
                "Predicted_Class",
                "Confidence",
                "Detection",
                "Severity",
                "SOC_Priority",
                "SOC_Response_Category",
            ]
        ].to_string(index=False))

        print()
        print("CREATING ATTACK QUEUE")
        print("-" * 80)

        queue = self.attack_queue(
            alerts
        )

        print(
            queue[
                [
                    "Alert_Queue_Position",
                    "Predicted_Class",
                    "Confidence",
                    "Severity",
                    "SOC_Priority",
                    "Top_Feature_1",
                ]
            ].to_string(index=False)
        )

        if len(queue) != 1:
            raise AssertionError(
                "Expected exactly one attack alert."
            )

        if queue.iloc[0]["SOC_Priority"] != "P1":
            raise AssertionError(
                "Expected P1 priority."
            )

        if queue.iloc[0]["Severity"] != "HIGH":
            raise AssertionError(
                "Expected HIGH severity."
            )

        print()
        print("✓ Attack queue verified")
        print("✓ Severity assignment verified")
        print("✓ SOC priority verified")
        print("✓ SHAP evidence attached")
        print("✓ Analyst recommendation generated")

        print()
        print("=" * 80)
        print("✓ SOC alert engine self-test completed")
        print("=" * 80)


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    engine = AlertEngine()

    engine.self_test()