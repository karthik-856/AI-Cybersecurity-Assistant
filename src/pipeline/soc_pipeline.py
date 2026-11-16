"""
================================================================================
ZUKA — AI CYBERSECURITY SOC PIPELINE
================================================================================

Central orchestration layer for the ZUKA SOC system.

Pipeline:

    TrafficCollector
          ↓
    FeaturePipeline
          ↓
    XGBoostDetector
          ↓
    SHAPExplainer
          ↓
    AlertEngine
          ↓
    RecommendationEngine
          ↓
    AlertStore
          ↓
    SOC Analyst

Safety:
    - Human analyst approval required
    - Automated containment disabled
    - No automatic blocking
    - No automatic isolation
    - Persistent alert history
    - Resolved alerts removed from active queue
      but retained in historical storage

Testing:
    The self-test uses a schema-compatible synthetic record only
    to verify the software pipeline. It is not presented as live
    network traffic.
================================================================================
"""

from __future__ import annotations

import gc
import logging
import time
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

import numpy as np
import pandas as pd


# =============================================================================
# ZUKA MODULES
# =============================================================================

from src.ingestion.traffic_collector import (
    FlowBatch,
    TrafficCollector,
)

from src.preprocessing.feature_pipeline import (
    MODEL_FEATURE_NAMES,
    FeaturePipeline,
)

from src.detection.xgboost_detector import (
    XGBoostDetector,
)

from src.xai.shap_explainer import (
    SHAPExplainer,
)

from src.alerts.alert_engine import (
    AlertEngine,
)

from src.recommendations.recommendation_engine import (
    RecommendationEngine,
)

from src.storage.alert_store import (
    AlertStore,
)


# =============================================================================
# LOGGER
# =============================================================================

LOGGER = logging.getLogger("zuka.pipeline")


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "multiclass"
    / "xgb_model.json"
)

DEFAULT_DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "zuka_soc.db"
)


# =============================================================================
# SOC PIPELINE
# =============================================================================

class SOCPipeline:
    """
    Main ZUKA SOC orchestration pipeline.
    """

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        database_path: str | Path = DEFAULT_DATABASE_PATH,
        feature_names: Optional[list[str]] = None,
        fill_missing: bool = False,
        collector_batch_size: int = 10,
    ) -> None:

        self.model_path = Path(model_path)
        self.database_path = Path(database_path)

        # ---------------------------------------------------------------------
        # Feature schema
        # ---------------------------------------------------------------------

        self.feature_names = list(
            feature_names
            if feature_names is not None
            else MODEL_FEATURE_NAMES
        )

        if len(self.feature_names) != 78:
            raise ValueError(
                "ZUKA requires exactly 78 model features. "
                f"Received {len(self.feature_names)}."
            )

        if len(set(self.feature_names)) != 78:
            raise ValueError(
                "ZUKA model feature schema contains duplicate names."
            )

        # ---------------------------------------------------------------------
        # Model
        # ---------------------------------------------------------------------

        if not self.model_path.exists():
            raise FileNotFoundError(
                "ZUKA XGBoost model was not found:\n"
                f"{self.model_path}"
            )

        # ---------------------------------------------------------------------
        # Ingestion
        # ---------------------------------------------------------------------

        self.collector = TrafficCollector(
            batch_size=collector_batch_size,
            source_name="automatic_network_input",
        )

        # ---------------------------------------------------------------------
        # Preprocessing
        # ---------------------------------------------------------------------

        self.feature_pipeline = FeaturePipeline(
            feature_names=self.feature_names,
            fill_missing=fill_missing,
        )

        # ---------------------------------------------------------------------
        # Detection
        # ---------------------------------------------------------------------

        self.detector = XGBoostDetector(
            model_path=self.model_path,
            feature_names=self.feature_names,
        )

        # ---------------------------------------------------------------------
        # Explainability
        #
        # IMPORTANT:
        # SHAPExplainer accepts model_path, not model=.
        # ---------------------------------------------------------------------

        self.explainer = SHAPExplainer(
            model_path=self.model_path,
            feature_names=self.feature_names,
        )

        # ---------------------------------------------------------------------
        # Alerting
        # ---------------------------------------------------------------------

        self.alert_engine = AlertEngine()

        # ---------------------------------------------------------------------
        # Recommendations
        # ---------------------------------------------------------------------

        self.recommendation_engine = (
            RecommendationEngine()
        )

        # ---------------------------------------------------------------------
        # Persistent storage
        # ---------------------------------------------------------------------

        self.alert_store = AlertStore(
            database_path=self.database_path,
        )

        # ---------------------------------------------------------------------
        # Runtime state
        # ---------------------------------------------------------------------

        self._sequence = 0
        self._closed = False

        LOGGER.info(
            "ZUKA SOC Pipeline initialized | "
            "features=%d | model=%s | database=%s",
            len(self.feature_names),
            self.model_path,
            self.database_path,
        )


    # =========================================================================
    # INPUT NORMALIZATION
    # =========================================================================

    @staticmethod
    def _normalize_input(
        data: Any,
    ) -> tuple[pd.DataFrame, str]:

        if isinstance(data, FlowBatch):

            return (
                data.data.copy(),
                data.source,
            )

        if isinstance(data, pd.DataFrame):

            return (
                data.copy(),
                "automatic_network_input",
            )

        if isinstance(data, pd.Series):

            return (
                data.to_frame().T,
                "automatic_network_input",
            )

        if isinstance(data, dict):

            return (
                pd.DataFrame([data]),
                "automatic_network_input",
            )

        raise TypeError(
            "Unsupported input type: "
            f"{type(data).__name__}. "
            "Expected FlowBatch, DataFrame, Series, or dict."
        )


    # =========================================================================
    # FEATURE PREPARATION
    # =========================================================================

    def _prepare_features(
        self,
        data: Any,
        source: Optional[str] = None,
    ) -> tuple[pd.DataFrame, str]:

        raw_data, detected_source = (
            self._normalize_input(data)
        )

        if raw_data.empty:
            raise ValueError(
                "Cannot process an empty network-flow batch."
            )

        final_source = (
            source
            if source is not None
            else detected_source
        )

        processed = self.feature_pipeline.transform(
            raw_data,
            source=final_source,
        )

        features = processed.features.copy()

        if len(features.columns) != 78:
            raise RuntimeError(
                "FeaturePipeline produced "
                f"{len(features.columns)} features instead of 78."
            )

        if list(features.columns) != self.feature_names:
            raise RuntimeError(
                "Feature order does not match the trained "
                "XGBoost model schema."
            )

        if len(features) != len(raw_data):
            raise RuntimeError(
                "Feature preprocessing changed the record count."
            )

        return (
            features,
            final_source,
        )


    # =========================================================================
    # XGBOOST PREDICTION
    # =========================================================================

    def _predict(
        self,
        features: pd.DataFrame,
    ) -> tuple[np.ndarray, np.ndarray]:

        result = self.detector.predict(
            features
        )

        # ---------------------------------------------------------------------
        # Structured detector result
        # ---------------------------------------------------------------------

        if isinstance(result, dict):

            predictions = result.get(
                "predicted_class"
            )

            if predictions is None:
                predictions = result.get(
                    "prediction"
                )

            probabilities = result.get(
                "probabilities"
            )

            if probabilities is None:
                probabilities = result.get(
                    "probability"
                )

            if predictions is None:
                raise RuntimeError(
                    "XGBoostDetector did not return "
                    "a predicted class."
                )

            if probabilities is None:
                raise RuntimeError(
                    "XGBoostDetector did not return "
                    "prediction probabilities."
                )

            predictions = np.asarray(
                predictions,
                dtype=int,
            ).reshape(-1)

            probabilities = np.asarray(
                probabilities,
                dtype=float,
            )

        # ---------------------------------------------------------------------
        # Raw detector prediction
        # ---------------------------------------------------------------------

        else:

            predictions = np.asarray(
                result,
                dtype=int,
            ).reshape(-1)

            probabilities = np.asarray(
                self.detector.predict_proba(
                    features
                ),
                dtype=float,
            )

        # ---------------------------------------------------------------------
        # Probability shape
        # ---------------------------------------------------------------------

        if probabilities.ndim == 1:

            probabilities = probabilities.reshape(
                1,
                -1,
            )

        if len(predictions) != len(probabilities):
            raise RuntimeError(
                "Prediction/probability record count mismatch: "
                f"{len(predictions)} vs "
                f"{len(probabilities)}."
            )

        if len(predictions) != len(features):
            raise RuntimeError(
                "Prediction/input record count mismatch: "
                f"{len(predictions)} vs "
                f"{len(features)}."
            )

        return (
            predictions,
            probabilities,
        )


    # =========================================================================
    # SHAP
    # =========================================================================

    def _get_shap_features(
        self,
        features: pd.DataFrame,
        predictions: np.ndarray,
        top_n: int = 5,
    ) -> list[list[dict[str, Any]]]:

        if len(predictions) != len(features):
            raise RuntimeError(
                "Prediction count does not match "
                "feature count before SHAP."
            )

        explanations = (
            self.explainer.top_features(
                features,
                top_n=top_n,
            )
        )

        if len(explanations) != len(features):
            raise RuntimeError(
                "SHAP explanation count does not match "
                "input record count."
            )

        return explanations


    # =========================================================================
    # CREATE ALERT
    # =========================================================================

    def _create_alert(
        self,
        predicted_class: int,
        confidence: float,
        top_features: list[dict[str, Any]],
        source: str,
        event_id: Optional[str] = None,
    ) -> dict[str, Any]:

        self._sequence += 1

        return self.alert_engine.create_alert(
            predicted_class=predicted_class,
            confidence=confidence,
            top_features=top_features,
            source=source,
            event_id=event_id,
            sequence=self._sequence,
        )


    # =========================================================================
    # RECOMMENDATION
    # =========================================================================

    def _add_recommendation(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:

        recommendation = (
            self.recommendation_engine
            .generate_recommendation(
                alert
            )
        )

        combined = dict(alert)

        combined.update(
            recommendation
        )

        return combined


    # =========================================================================
    # STORE
    # =========================================================================

    def _persist_alert(
        self,
        alert: dict[str, Any],
    ) -> bool:

        inserted = self.alert_store.add_alert(
            alert
        )

        if inserted:

            LOGGER.info(
                "Alert stored | alert_id=%s",
                alert.get("Alert_ID"),
            )

        return inserted


    # =========================================================================
    # PROCESS ONE EVENT
    # =========================================================================

    def process_event(
        self,
        event: Any,
        source: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> dict[str, Any]:

        if self._closed:
            raise RuntimeError(
                "ZUKA SOC Pipeline is already closed."
            )

        raw_data, detected_source = (
            self._normalize_input(event)
        )

        if len(raw_data) != 1:
            raise ValueError(
                "process_event() requires exactly one record. "
                f"Received {len(raw_data)}."
            )

        final_source = (
            source
            if source is not None
            else detected_source
        )

        features, final_source = (
            self._prepare_features(
                raw_data,
                source=final_source,
            )
        )

        predictions, probabilities = (
            self._predict(
                features
            )
        )

        predicted_class = int(
            predictions[0]
        )

        confidence = float(
            np.max(
                probabilities[0]
            )
        )

        shap_features = (
            self._get_shap_features(
                features,
                predictions,
                top_n=5,
            )
        )

        alert = self._create_alert(
            predicted_class=predicted_class,
            confidence=confidence,
            top_features=shap_features[0],
            source=final_source,
            event_id=event_id,
        )

        alert = self._add_recommendation(
            alert
        )

        stored = self._persist_alert(
            alert
        )

        result = dict(alert)

        result["Stored"] = stored

        return result


    # =========================================================================
    # PROCESS BATCH
    # =========================================================================

    def process_batch(
        self,
        data: Any,
        source: Optional[str] = None,
    ) -> list[dict[str, Any]]:

        if self._closed:
            raise RuntimeError(
                "ZUKA SOC Pipeline is already closed."
            )

        raw_data, detected_source = (
            self._normalize_input(data)
        )

        final_source = (
            source
            if source is not None
            else detected_source
        )

        features, final_source = (
            self._prepare_features(
                raw_data,
                source=final_source,
            )
        )

        predictions, probabilities = (
            self._predict(
                features
            )
        )

        shap_features = (
            self._get_shap_features(
                features,
                predictions,
                top_n=5,
            )
        )

        results: list[dict[str, Any]] = []

        for index in range(len(features)):

            predicted_class = int(
                predictions[index]
            )

            confidence = float(
                np.max(
                    probabilities[index]
                )
            )

            alert = self._create_alert(
                predicted_class=predicted_class,
                confidence=confidence,
                top_features=shap_features[index],
                source=final_source,
            )

            alert = self._add_recommendation(
                alert
            )

            stored = self._persist_alert(
                alert
            )

            result = dict(alert)

            result["Stored"] = stored

            results.append(
                result
            )

        LOGGER.info(
            "SOC batch processed | records=%d | source=%s",
            len(results),
            final_source,
        )

        return results


    # =========================================================================
    # FLOW BATCH
    # =========================================================================

    def process_flow_batch(
        self,
        batch: FlowBatch,
    ) -> list[dict[str, Any]]:

        if not isinstance(
            batch,
            FlowBatch,
        ):
            raise TypeError(
                "process_flow_batch() requires a FlowBatch."
            )

        return self.process_batch(
            batch.data,
            source=batch.source,
        )


    # =========================================================================
    # COLLECTED DATAFRAME
    # =========================================================================

    def process_collected_dataframe(
        self,
        data: pd.DataFrame,
        source: str = "automatic_network_input",
    ) -> list[dict[str, Any]]:

        batch = self.collector.collect_dataframe(
            data,
            source_name=source,
        )

        return self.process_flow_batch(
            batch
        )


    # =========================================================================
    # CONTINUOUS STREAM
    # =========================================================================

    def stream(
        self,
        stream_provider: Callable[
            [],
            pd.DataFrame,
        ],
        interval_seconds: float = 1.0,
        max_batches: Optional[int] = None,
    ) -> Iterator[list[dict[str, Any]]]:

        if interval_seconds < 0:
            raise ValueError(
                "interval_seconds must be >= 0."
            )

        if max_batches is not None and max_batches <= 0:
            raise ValueError(
                "max_batches must be greater than zero."
            )

        batch_count = 0

        LOGGER.info(
            "ZUKA SOC stream started."
        )

        try:

            while True:

                if (
                    max_batches is not None
                    and batch_count >= max_batches
                ):
                    break

                incoming_data = (
                    stream_provider()
                )

                if incoming_data is None:

                    time.sleep(
                        interval_seconds
                    )

                    continue

                if not isinstance(
                    incoming_data,
                    pd.DataFrame,
                ):
                    raise TypeError(
                        "stream_provider must return "
                        "a pandas DataFrame."
                    )

                if incoming_data.empty:

                    time.sleep(
                        interval_seconds
                    )

                    continue

                for batch in (
                    self.collector.create_batches(
                        incoming_data,
                        source_name=(
                            "automatic_network_input"
                        ),
                    )
                ):

                    results = (
                        self.process_flow_batch(
                            batch
                        )
                    )

                    batch_count += 1

                    yield results

                    if (
                        max_batches is not None
                        and batch_count >= max_batches
                    ):
                        break

                if (
                    max_batches is not None
                    and batch_count >= max_batches
                ):
                    break

                time.sleep(
                    interval_seconds
                )

        except KeyboardInterrupt:

            LOGGER.info(
                "ZUKA SOC stream interrupted by analyst."
            )

        finally:

            LOGGER.info(
                "ZUKA SOC stream stopped | batches=%d",
                batch_count,
            )


    # =========================================================================
    # ACTIVE ALERTS
    # =========================================================================

    def get_active_alerts(
        self,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Get currently active SOC alerts.

        AlertStore returns:
            NEW
            INVESTIGATING

        Important:
            AlertStore returns an empty DataFrame with no columns
            when there are no active alerts. Therefore this method
            safely returns that empty DataFrame without assuming
            an alert_id column exists.
        """

        alerts = (
            self.alert_store.get_active_alerts()
        )

        if alerts.empty:
            return alerts

        if limit is None:
            return alerts

        if limit <= 0:
            return alerts.iloc[0:0].copy()

        return alerts.head(
            int(limit)
        )


    # =========================================================================
    # ALERT HISTORY
    # =========================================================================

    def get_alerts(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:

        return self.alert_store.get_alerts(
            status=status,
            limit=limit,
        )


    # =========================================================================
    # GET ONE ALERT
    # =========================================================================

    def get_alert(
        self,
        alert_id: str,
    ) -> Optional[dict[str, Any]]:

        return self.alert_store.get_alert(
            alert_id
        )


    # =========================================================================
    # UPDATE STATUS
    # =========================================================================

    def update_alert_status(
        self,
        alert_id: str,
        status: str,
        analyst: str = "SOC_ANALYST",
        notes: Optional[str] = None,
    ) -> bool:

        return self.alert_store.update_status(
            alert_id=alert_id,
            status=status,
            analyst=analyst,
            notes=notes,
        )


    # =========================================================================
    # ANALYST ACTION
    # =========================================================================

    def record_analyst_action(
        self,
        alert_id: str,
        action: str,
        analyst: str = "SOC_ANALYST",
        notes: Optional[str] = None,
    ) -> bool:

        self.alert_store.record_action(
            alert_id=alert_id,
            action=action,
            analyst=analyst,
            notes=notes,
        )

        history = (
            self.alert_store.get_action_history(
                alert_id
            )
        )

        return not history.empty


    # =========================================================================
    # ACTION HISTORY
    # =========================================================================

    def get_action_history(
        self,
        alert_id: str,
    ) -> pd.DataFrame:

        return self.alert_store.get_action_history(
            alert_id
        )


    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_statistics(
        self,
    ) -> dict[str, Any]:

        return self.alert_store.get_statistics()


    # =========================================================================
    # SELF TEST
    # =========================================================================

    def self_test(
        self,
    ) -> bool:

        print()
        print("=" * 80)
        print("ZUKA — SOC PIPELINE SELF TEST")
        print("=" * 80)

        # ---------------------------------------------------------------------
        # Schema-compatible test input
        # ---------------------------------------------------------------------

        test_data = pd.DataFrame(
            {
                feature: [1.0]
                for feature in self.feature_names
            }
        )

        print()
        print("INITIALIZATION")
        print("-" * 80)

        print("✓ Pipeline initialized")
        print("✓ 78-feature schema configured")

        # ---------------------------------------------------------------------
        # Detection
        # ---------------------------------------------------------------------

        print()
        print("PROCESSING EVENT")
        print("-" * 80)

        result = self.process_event(
            test_data,
            source="ZUKA_SELF_TEST",
        )

        print(
            f"Predicted class : "
            f"{result.get('Predicted_Class')}"
        )

        print(
            f"Confidence      : "
            f"{float(result.get('Confidence', 0.0)):.6f}"
        )

        print(
            f"Detection       : "
            f"{result.get('Detection')}"
        )

        print(
            f"Severity        : "
            f"{result.get('Severity')}"
        )

        print(
            f"SOC Priority    : "
            f"{result.get('SOC_Priority')}"
        )

        print(
            f"Stored          : "
            f"{result.get('Stored')}"
        )

        if not result.get("Alert_ID"):
            raise RuntimeError(
                "Alert_ID was not generated."
            )

        print(
            "✓ XGBoost detection verified"
        )

        # ---------------------------------------------------------------------
        # SHAP
        # ---------------------------------------------------------------------

        print()
        print("XAI")
        print("-" * 80)

        top_features = [
            result.get("Top_Feature_1"),
            result.get("Top_Feature_2"),
            result.get("Top_Feature_3"),
        ]

        top_features = [
            feature
            for feature in top_features
            if feature is not None
        ]

        print(
            f"SHAP features available: "
            f"{len(top_features)}"
        )

        if not top_features:
            raise RuntimeError(
                "No SHAP features were attached to the alert."
            )

        for index, feature in enumerate(
            top_features,
            start=1,
        ):

            print(
                f"Top feature {index}   : "
                f"{feature}"
            )

        print(
            "✓ SHAP feature extraction verified"
        )

        # ---------------------------------------------------------------------
        # Recommendation
        # ---------------------------------------------------------------------

        print()
        print("RECOMMENDATION")
        print("-" * 80)

        print(
            f"Risk level      : "
            f"{result.get('Risk_Level')}"
        )

        print(
            f"Human approval  : "
            f"{result.get('Human_Approval_Required')}"
        )

        print(
            f"Containment     : "
            f"{result.get('Automated_Containment')}"
        )

        if (
            result.get(
                "Human_Approval_Required"
            )
            != "YES"
        ):
            raise RuntimeError(
                "Human approval requirement failed."
            )

        if (
            result.get(
                "Automated_Containment"
            )
            != "DISABLED"
        ):
            raise RuntimeError(
                "Automated containment safety policy failed."
            )

        print(
            "✓ Recommendation engine verified"
        )

        # ---------------------------------------------------------------------
        # Persistence
        # ---------------------------------------------------------------------

        print()
        print("PERSISTENT STORAGE")
        print("-" * 80)

        alert_id = result["Alert_ID"]

        stored_alert = (
            self.get_alert(
                alert_id
            )
        )

        if stored_alert is None:
            raise RuntimeError(
                "Alert was not persisted in SQLite."
            )

        print("Alert retrieved")

        database_status = stored_alert.get(
            "status"
        )

        print(
            f"Status           : "
            f"{database_status}"
        )

        if database_status != "NEW":
            raise RuntimeError(
                "New alert did not receive NEW status."
            )

        print(
            "✓ AlertStore persistence verified"
        )

        # ---------------------------------------------------------------------
        # Active queue
        # ---------------------------------------------------------------------

        active_alerts = (
            self.get_active_alerts()
        )

        print(
            f"Active alerts    : "
            f"{len(active_alerts)}"
        )

        if active_alerts.empty:
            raise RuntimeError(
                "New alert is not present in active queue."
            )

        if "alert_id" not in active_alerts.columns:
            raise RuntimeError(
                "Active alert DataFrame is missing alert_id."
            )

        if not (
            active_alerts["alert_id"]
            == alert_id
        ).any():
            raise RuntimeError(
                "New alert is not present in active queue."
            )

        print(
            "✓ Active alert queue verified"
        )

        # ---------------------------------------------------------------------
        # Investigation
        # ---------------------------------------------------------------------

        print()
        print("ANALYST WORKFLOW")
        print("-" * 80)

        updated = (
            self.update_alert_status(
                alert_id=alert_id,
                status="INVESTIGATING",
                analyst="SOC_ANALYST",
                notes=(
                    "ZUKA self-test investigation."
                ),
            )
        )

        if not updated:
            raise RuntimeError(
                "Failed to set INVESTIGATING status."
            )

        investigating = (
            self.get_alert(
                alert_id
            )
        )

        if investigating is None:
            raise RuntimeError(
                "Alert disappeared during investigation."
            )

        if (
            investigating.get("status")
            != "INVESTIGATING"
        ):
            raise RuntimeError(
                "INVESTIGATING status was not persisted."
            )

        print(
            "✓ INVESTIGATING status verified"
        )

        # ---------------------------------------------------------------------
        # Analyst action
        # ---------------------------------------------------------------------

        action_recorded = (
            self.record_analyst_action(
                alert_id=alert_id,
                action="SELF_TEST_REVIEW",
                analyst="SOC_ANALYST",
                notes=(
                    "ZUKA pipeline self-test."
                ),
            )
        )

        if not action_recorded:
            raise RuntimeError(
                "Analyst action was not recorded."
            )

        print(
            "✓ Analyst action recorded"
        )

        # ---------------------------------------------------------------------
        # Resolve
        # ---------------------------------------------------------------------

        resolved = (
            self.update_alert_status(
                alert_id=alert_id,
                status="RESOLVED",
                analyst="SOC_ANALYST",
                notes=(
                    "ZUKA self-test resolved."
                ),
            )
        )

        if not resolved:
            raise RuntimeError(
                "Failed to resolve alert."
            )

        resolved_alert = (
            self.get_alert(
                alert_id
            )
        )

        if resolved_alert is None:
            raise RuntimeError(
                "Resolved alert could not be retrieved."
            )

        if (
            resolved_alert.get("status")
            != "RESOLVED"
        ):
            raise RuntimeError(
                "RESOLVED status was not persisted."
            )

        print(
            "✓ RESOLVED status verified"
        )

        # ---------------------------------------------------------------------
        # Active queue after resolution
        #
        # FIX:
        # AlertStore returns an empty DataFrame with no columns when
        # no active alerts exist. Therefore test .empty FIRST.
        # ---------------------------------------------------------------------

        active_after_resolve = (
            self.get_active_alerts()
        )

        print(
            f"Active after resolve : "
            f"{len(active_after_resolve)}"
        )

        if not active_after_resolve.empty:

            if "alert_id" not in active_after_resolve.columns:
                raise RuntimeError(
                    "Active alert DataFrame is missing alert_id."
                )

            still_active = (
                active_after_resolve[
                    active_after_resolve["alert_id"]
                    == alert_id
                ]
            )

            if not still_active.empty:
                raise RuntimeError(
                    "Resolved alert is still present "
                    "in the active queue."
                )

        print(
            "✓ Resolved alert removed from active queue"
        )

        # ---------------------------------------------------------------------
        # Historical retention
        # ---------------------------------------------------------------------

        history_alerts = (
            self.get_alerts(
                limit=100
            )
        )

        if history_alerts.empty:
            raise RuntimeError(
                "Alert history unexpectedly empty."
            )

        if "alert_id" not in history_alerts.columns:
            raise RuntimeError(
                "Alert history is missing alert_id."
            )

        historical_match = (
            history_alerts[
                history_alerts["alert_id"]
                == alert_id
            ]
        )

        if historical_match.empty:
            raise RuntimeError(
                "Resolved alert was removed from history."
            )

        print(
            "✓ Resolved alert retained in history"
        )

        # ---------------------------------------------------------------------
        # Analyst history
        # ---------------------------------------------------------------------

        history = (
            self.get_action_history(
                alert_id
            )
        )

        print(
            f"Analyst actions : "
            f"{len(history)}"
        )

        if history.empty:
            raise RuntimeError(
                "Analyst action history was not retained."
            )

        print(
            "✓ Analyst action history verified"
        )

        # ---------------------------------------------------------------------
        # Statistics
        # ---------------------------------------------------------------------

        print()
        print("STATISTICS")
        print("-" * 80)

        statistics = (
            self.get_statistics()
        )

        if not isinstance(
            statistics,
            dict,
        ):
            raise RuntimeError(
                "SOC statistics did not return a dictionary."
            )

        for key, value in statistics.items():

            print(
                f"{key} : {value}"
            )

        print(
            "✓ SOC statistics verified"
        )

        # ---------------------------------------------------------------------
        # Complete
        # ---------------------------------------------------------------------

        print()
        print("=" * 80)
        print("✓ ZUKA SOC PIPELINE SELF-TEST COMPLETED")
        print("=" * 80)

        return True


    # =========================================================================
    # CLOSE
    # =========================================================================

    def close(
        self,
    ) -> None:

        if self._closed:
            return

        LOGGER.info(
            "ZUKA SOC Pipeline closing."
        )

        self.detector = None
        self.explainer = None

        gc.collect()

        self._closed = True

        LOGGER.info(
            "ZUKA SOC Pipeline closed."
        )


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

    print("=" * 80)
    print("ZUKA — SOC PIPELINE")
    print("=" * 80)

    test_database = (
        PROJECT_ROOT
        / "data"
        / "zuka_soc_pipeline_self_test.db"
    )

    pipeline: Optional[SOCPipeline] = None

    try:

        pipeline = SOCPipeline(
            model_path=DEFAULT_MODEL_PATH,
            database_path=test_database,
        )

        pipeline.self_test()

    except Exception:

        LOGGER.exception(
            "ZUKA SOC Pipeline self-test failed."
        )

        raise

    finally:

        if pipeline is not None:
            pipeline.close()

        gc.collect()

        try:

            if test_database.exists():
                test_database.unlink()

            print(
                "Self-test database cleaned up."
            )

        except PermissionError:

            print(
                "Warning: self-test database is still "
                "in use and could not be deleted."
            )