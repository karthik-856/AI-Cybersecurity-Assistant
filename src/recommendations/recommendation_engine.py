"""
ZUKA — SOC Recommendation Engine

Converts structured SOC alerts into analyst-ready:
    - risk assessments
    - investigation steps
    - recommended actions
    - escalation guidance
    - analyst questions

Safety design:
    - No automatic containment
    - No automatic blocking
    - No automatic isolation
    - Human analyst approval is required
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd


LOGGER = logging.getLogger("zuka.recommendations")


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "results" / "tables" / "recommendations"
)

DEFAULT_REPORT_DIR = (
    PROJECT_ROOT / "results" / "reports" / "recommendations"
)


# =============================================================================
# RECOMMENDATION ENGINE
# =============================================================================

class RecommendationEngine:
    """
    ZUKA analyst recommendation engine.
    """

    REQUIRED_COLUMNS = [
        "Alert_ID",
        "Predicted_Class",
        "Confidence",
        "Detection",
        "Severity",
        "SOC_Priority",
        "SOC_Response_Category",
        "XAI_Explanation",
        "Analyst_Recommendation",
    ]

    BENIGN_CLASS = 0

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
            "ZUKA RecommendationEngine initialized"
        )

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate_alert_data(
        self,
        alerts: pd.DataFrame,
    ) -> None:

        missing = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in alerts.columns
        ]

        if missing:
            raise ValueError(
                "Missing required alert columns:\n"
                + "\n".join(missing)
            )

        LOGGER.info(
            "Alert schema validated | records=%d",
            len(alerts),
        )

    # =========================================================================
    # RISK
    # =========================================================================

    def risk_level(
        self,
        predicted_class: int,
        confidence: float,
        severity: str,
        priority: str,
    ) -> str:

        if predicted_class == self.BENIGN_CLASS:
            return "NO_SECURITY_RISK"

        if severity == "HIGH" and priority == "P1":
            return "CRITICAL_REVIEW"

        if severity == "MEDIUM" or priority == "P2":
            return "ELEVATED_REVIEW"

        return "LOW_CONFIDENCE_REVIEW"

    # =========================================================================
    # INVESTIGATION STEPS
    # =========================================================================

    def investigation_steps(
        self,
        predicted_class: int,
        severity: str,
    ) -> str:

        if predicted_class == self.BENIGN_CLASS:

            return (
                "1. No immediate security response is required. "
                "2. Retain the event for monitoring and audit purposes."
            )

        steps = [
            "1. Review the source and destination network-flow context.",
            "2. Correlate the event with surrounding network and security telemetry.",
            "3. Check whether similar events occurred from the same source.",
            "4. Review the SHAP explanatory features for consistency with the detection.",
            f"5. Investigate predicted attack class {predicted_class} in the relevant incident context.",
        ]

        if severity == "HIGH":

            steps.append(
                "6. Because this is a high-severity alert, prioritize analyst investigation."
            )

        elif severity == "MEDIUM":

            steps.append(
                "6. Validate the alert against additional telemetry before escalation."
            )

        else:

            steps.append(
                "6. Treat the detection cautiously until corroborating evidence is available."
            )

        return " ".join(steps)

    # =========================================================================
    # RECOMMENDATION
    # =========================================================================

    def recommendation(
        self,
        predicted_class: int,
        confidence: float,
        severity: str,
        priority: str,
    ) -> str:

        if predicted_class == self.BENIGN_CLASS:

            return (
                "No security action is recommended. "
                "Continue normal monitoring."
            )

        if severity == "HIGH" and priority == "P1":

            return (
                "Immediately investigate and correlate the alert "
                "with other security telemetry. Review the affected "
                "flow context and determine whether escalation or "
                "containment is justified. Any containment action "
                "must be approved by an authorized analyst."
            )

        if severity == "MEDIUM":

            return (
                "Perform analyst review and correlate the event "
                "with additional telemetry before escalation. "
                "Escalate if corroborating evidence is identified."
            )

        return (
            "Validate the detection against additional telemetry "
            "before escalation or containment."
        )

    # =========================================================================
    # ESCALATION
    # =========================================================================

    def escalation_guidance(
        self,
        predicted_class: int,
        severity: str,
        priority: str,
    ) -> str:

        if predicted_class == self.BENIGN_CLASS:

            return "NO_ESCALATION"

        if priority == "P1":

            return (
                "Escalate to the responsible SOC analyst or incident "
                "response team for immediate review."
            )

        if priority == "P2":

            return (
                "Escalate for analyst review if corroborating evidence "
                "indicates malicious activity."
            )

        return (
            "Do not escalate solely on this detection; validate first."
        )

    # =========================================================================
    # ANALYST QUESTIONS
    # =========================================================================

    def analyst_questions(
        self,
        predicted_class: int,
    ) -> str:

        if predicted_class == self.BENIGN_CLASS:

            return (
                "Is there any surrounding telemetry indicating that "
                "this apparently benign event requires additional review?"
            )

        return (
            "1. What happened?\n"
            "2. Why was this event detected?\n"
            "3. Which model features contributed to the detection?\n"
            "4. Are there similar events from the same source?\n"
            "5. Is there corroborating security telemetry?\n"
            "6. Should this alert be escalated?"
        )

    # =========================================================================
    # SINGLE RECORD
    # =========================================================================

    def generate_recommendation(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:

        predicted_class = int(
            alert["Predicted_Class"]
        )

        confidence = float(
            alert["Confidence"]
        )

        severity = str(
            alert["Severity"]
        )

        priority = str(
            alert["SOC_Priority"]
        )

        risk = self.risk_level(
            predicted_class,
            confidence,
            severity,
            priority,
        )

        steps = self.investigation_steps(
            predicted_class,
            severity,
        )

        recommendation = self.recommendation(
            predicted_class,
            confidence,
            severity,
            priority,
        )

        escalation = self.escalation_guidance(
            predicted_class,
            severity,
            priority,
        )

        questions = self.analyst_questions(
            predicted_class,
        )

        return {
            "Alert_ID": alert["Alert_ID"],
            "Predicted_Class": predicted_class,
            "Confidence": confidence,
            "Severity": severity,
            "SOC_Priority": priority,
            "Risk_Level": risk,
            "Investigation_Steps": steps,
            "Recommendation": recommendation,
            "Escalation_Guidance": escalation,
            "Analyst_Questions": questions,
            "Human_Approval_Required": "YES",
            "Automated_Containment": "DISABLED",
        }

    # =========================================================================
    # BATCH
    # =========================================================================

    def generate_recommendations(
        self,
        alerts: pd.DataFrame,
    ) -> pd.DataFrame:

        self.validate_alert_data(alerts)

        records = alerts.to_dict(
            orient="records"
        )

        recommendations = [
            self.generate_recommendation(record)
            for record in records
        ]

        result = pd.DataFrame(
            recommendations
        )

        LOGGER.info(
            "Recommendations generated | records=%d",
            len(result),
        )

        return result

    # =========================================================================
    # COMBINE WITH ALERTS
    # =========================================================================

    def create_analyst_view(
        self,
        alerts: pd.DataFrame,
    ) -> pd.DataFrame:

        recommendations = self.generate_recommendations(
            alerts
        )

        recommendation_columns = [
            "Alert_ID",
            "Risk_Level",
            "Investigation_Steps",
            "Recommendation",
            "Escalation_Guidance",
            "Analyst_Questions",
            "Human_Approval_Required",
            "Automated_Containment",
        ]

        base = alerts.copy()

        result = base.merge(
            recommendations[
                recommendation_columns
            ],
            on="Alert_ID",
            how="left",
        )

        return result

    # =========================================================================
    # SAVE
    # =========================================================================

    def save_recommendations(
        self,
        recommendations: pd.DataFrame,
        filename: str = "zuka_recommendations.csv",
    ) -> Path:

        path = self.output_dir / filename

        recommendations.to_csv(
            path,
            index=False,
        )

        LOGGER.info(
            "Recommendations saved: %s",
            path,
        )

        return path

    # =========================================================================
    # SUMMARY
    # =========================================================================

    def create_summary(
        self,
        recommendations: pd.DataFrame,
    ) -> pd.DataFrame:

        if recommendations.empty:

            return pd.DataFrame(
                columns=[
                    "Risk_Level",
                    "Alert_Count",
                    "Mean_Confidence",
                ]
            )

        summary = (
            recommendations
            .groupby("Risk_Level")
            .agg(
                Alert_Count=("Alert_ID", "count"),
                Mean_Confidence=("Confidence", "mean"),
            )
            .reset_index()
        )

        return summary

    # =========================================================================
    # REPORT
    # =========================================================================

    def save_report(
        self,
        recommendations: pd.DataFrame,
        filename: str = "zuka_recommendation_engine_report.txt",
    ) -> Path:

        path = self.report_dir / filename

        total = len(recommendations)

        critical = int(
            (
                recommendations["Risk_Level"]
                == "CRITICAL_REVIEW"
            ).sum()
        )

        elevated = int(
            (
                recommendations["Risk_Level"]
                == "ELEVATED_REVIEW"
            ).sum()
        )

        low = int(
            (
                recommendations["Risk_Level"]
                == "LOW_CONFIDENCE_REVIEW"
            ).sum()
        )

        benign = int(
            (
                recommendations["Risk_Level"]
                == "NO_SECURITY_RISK"
            ).sum()
        )

        report = f"""
================================================================================
ZUKA — RECOMMENDATION ENGINE REPORT
================================================================================

Alerts processed        : {total}
Critical review         : {critical}
Elevated review         : {elevated}
Low-confidence review   : {low}
No security risk        : {benign}

Human approval required : YES
Automated containment   : DISABLED

The recommendation engine provides investigation guidance,
risk interpretation, escalation guidance and analyst questions.

It does not automatically block, isolate, terminate or contain
network activity.

================================================================================
"""

        path.write_text(
            report.strip() + "\n",
            encoding="utf-8",
        )

        LOGGER.info(
            "Recommendation report saved: %s",
            path,
        )

        return path

    # =========================================================================
    # SELF TEST
    # =========================================================================

    def self_test(self) -> None:

        print("=" * 80)
        print("ZUKA — RECOMMENDATION ENGINE SELF TEST")
        print("=" * 80)

        test_alerts = pd.DataFrame(
            [
                {
                    "Alert_ID": "TEST-BENIGN-001",
                    "Predicted_Class": 0,
                    "Confidence": 0.9988,
                    "Detection": "BENIGN",
                    "Severity": "NONE",
                    "SOC_Priority": "NONE",
                    "SOC_Response_Category": "NO_ACTION",
                    "XAI_Explanation": (
                        "Benign model prediction."
                    ),
                    "Analyst_Recommendation": (
                        "No action required."
                    ),
                },
                {
                    "Alert_ID": "TEST-ATTACK-001",
                    "Predicted_Class": 9,
                    "Confidence": 0.9998,
                    "Detection": "ATTACK",
                    "Severity": "HIGH",
                    "SOC_Priority": "P1",
                    "SOC_Response_Category": (
                        "INVESTIGATE_AND_CORRELATE"
                    ),
                    "XAI_Explanation": (
                        "Attack class 9 supported by SHAP evidence."
                    ),
                    "Analyst_Recommendation": (
                        "Immediately investigate."
                    ),
                },
                {
                    "Alert_ID": "TEST-LOW-001",
                    "Predicted_Class": 13,
                    "Confidence": 0.50,
                    "Detection": "ATTACK",
                    "Severity": "LOW",
                    "SOC_Priority": "P3",
                    "SOC_Response_Category": (
                        "VALIDATE_BEFORE_ESCALATION"
                    ),
                    "XAI_Explanation": (
                        "Low-confidence attack detection."
                    ),
                    "Analyst_Recommendation": (
                        "Validate before escalation."
                    ),
                },
            ]
        )

        print()
        print("INPUT")
        print("-" * 80)
        print(f"Test alerts: {len(test_alerts)}")
        print("✓ Alert input prepared")

        print()
        print("GENERATING RECOMMENDATIONS")
        print("-" * 80)

        recommendations = self.generate_recommendations(
            test_alerts
        )

        print(
            recommendations[
                [
                    "Alert_ID",
                    "Predicted_Class",
                    "Confidence",
                    "Risk_Level",
                    "Human_Approval_Required",
                    "Automated_Containment",
                ]
            ].to_string(index=False)
        )

        # ---------------------------------------------------------------------
        # Assertions
        # ---------------------------------------------------------------------

        benign = recommendations[
            recommendations["Alert_ID"]
            == "TEST-BENIGN-001"
        ].iloc[0]

        attack = recommendations[
            recommendations["Alert_ID"]
            == "TEST-ATTACK-001"
        ].iloc[0]

        low = recommendations[
            recommendations["Alert_ID"]
            == "TEST-LOW-001"
        ].iloc[0]

        if benign["Risk_Level"] != "NO_SECURITY_RISK":
            raise AssertionError(
                "Benign risk classification failed."
            )

        if attack["Risk_Level"] != "CRITICAL_REVIEW":
            raise AssertionError(
                "P1 risk classification failed."
            )

        if low["Risk_Level"] != "LOW_CONFIDENCE_REVIEW":
            raise AssertionError(
                "Low-confidence risk classification failed."
            )

        if not all(
            recommendations[
                "Human_Approval_Required"
            ] == "YES"
        ):
            raise AssertionError(
                "Human approval policy failed."
            )

        if not all(
            recommendations[
                "Automated_Containment"
            ] == "DISABLED"
        ):
            raise AssertionError(
                "Automated containment safety policy failed."
            )

        if not all(
            recommendations[
                "Investigation_Steps"
            ].astype(str).str.len() > 0
        ):
            raise AssertionError(
                "Investigation guidance missing."
            )

        if not all(
            recommendations[
                "Recommendation"
            ].astype(str).str.len() > 0
        ):
            raise AssertionError(
                "Recommendations missing."
            )

        print()
        print("✓ Risk assessment verified")
        print("✓ Investigation guidance verified")
        print("✓ Recommendation generation verified")
        print("✓ Escalation guidance verified")
        print("✓ Analyst questions verified")
        print("✓ Human approval policy verified")
        print("✓ Automated containment remains disabled")

        print()
        print("=" * 80)
        print("✓ Recommendation engine self-test completed")
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

    engine = RecommendationEngine()

    engine.self_test()