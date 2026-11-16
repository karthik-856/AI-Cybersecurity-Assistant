"""
ZUKA — XGBoost Detection Engine

Real-world detection layer:

Traffic Collector
        ↓
Feature Pipeline
        ↓
78 verified features
        ↓
XGBoost Detector
        ↓
Prediction + Probability + Confidence
        ↓
XAI / Alert Engine
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd
import xgboost as xgb


# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("zuka.detection")

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


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

BENIGN_CLASS_ID = 0


# =============================================================================
# DETECTION RESULT
# =============================================================================

@dataclass
class DetectionResult:
    predicted_class: int
    confidence: float
    detection: str
    probabilities: np.ndarray


# =============================================================================
# XGBOOST DETECTOR
# =============================================================================

class XGBoostDetector:

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        feature_names: Optional[Sequence[str]] = None,
        benign_class_id: int = BENIGN_CLASS_ID,
    ) -> None:

        self.model_path = Path(model_path)

        self.feature_names = (
            list(feature_names)
            if feature_names is not None
            else None
        )

        self.benign_class_id = benign_class_id

        self.model: Optional[xgb.XGBClassifier] = None

        self._load_model()
        self._validate_model()

        if self.feature_names is not None:
            self._validate_feature_schema()

    # =========================================================================
    # LOAD NATIVE XGBOOST MODEL
    # =========================================================================

    def _load_model(self) -> None:

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"XGBoost model not found:\n{self.model_path}"
            )

        logger.info(
            "Loading native XGBoost model: %s",
            self.model_path,
        )

        try:

            self.model = xgb.XGBClassifier()

            self.model.load_model(
                str(self.model_path)
            )

        except Exception as exc:

            raise RuntimeError(
                "Failed to load native XGBoost model.\n"
                f"Model: {self.model_path}\n"
                f"Original error: {exc}"
            ) from exc

        logger.info(
            "Native XGBoost model loaded successfully | type=%s",
            type(self.model).__name__,
        )

    # =========================================================================
    # MODEL VALIDATION
    # =========================================================================

    def _validate_model(self) -> None:

        if self.model is None:
            raise RuntimeError(
                "XGBoost model was not loaded."
            )

        if not hasattr(self.model, "predict"):
            raise TypeError(
                "Model does not provide predict()."
            )

        if not hasattr(self.model, "predict_proba"):
            raise TypeError(
                "Model does not provide predict_proba()."
            )

        if not hasattr(self.model, "classes_"):
            raise AttributeError(
                "Model does not contain classes_."
            )

        self.classes_ = np.asarray(
            self.model.classes_
        )

        if not hasattr(
            self.model,
            "n_features_in_",
        ):
            raise AttributeError(
                "Model does not contain n_features_in_."
            )

        self.model_feature_count = int(
            self.model.n_features_in_
        )

        logger.info(
            "Model validated | features=%d | classes=%s",
            self.model_feature_count,
            self.classes_.tolist(),
        )

    # =========================================================================
    # FEATURE SCHEMA
    # =========================================================================

    def _validate_feature_schema(self) -> None:

        if len(self.feature_names) != 78:
            raise ValueError(
                "ZUKA expects exactly 78 model features. "
                f"Received {len(self.feature_names)}."
            )

        if self.model_feature_count != len(
            self.feature_names
        ):
            raise ValueError(
                "Model/schema feature mismatch: "
                f"model={self.model_feature_count}, "
                f"schema={len(self.feature_names)}"
            )

        if len(set(self.feature_names)) != len(
            self.feature_names
        ):
            raise ValueError(
                "Duplicate feature names detected."
            )

        logger.info(
            "Feature schema verified | features=%d",
            len(self.feature_names),
        )

    # =========================================================================
    # INPUT VALIDATION
    # =========================================================================

    def _validate_input(
        self,
        features: pd.DataFrame,
    ) -> pd.DataFrame:

        if not isinstance(
            features,
            pd.DataFrame,
        ):
            raise TypeError(
                "Detector input must be pandas.DataFrame."
            )

        if features.empty:
            raise ValueError(
                "Detector received an empty DataFrame."
            )

        if self.feature_names is None:
            raise RuntimeError(
                "Feature schema has not been configured."
            )

        missing = [
            name
            for name in self.feature_names
            if name not in features.columns
        ]

        if missing:

            raise ValueError(
                "Missing required model features:\n"
                + "\n".join(missing)
            )

        # IMPORTANT:
        # Select using the real feature names.
        # Never convert the names to "0", "1", ..., "77".

        model_input = features.loc[
            :,
            self.feature_names,
        ].copy()

        for feature in self.feature_names:

            model_input[feature] = pd.to_numeric(
                model_input[feature],
                errors="coerce",
            )

        values = model_input.to_numpy(
            dtype=np.float64
        )

        if np.isnan(values).any():

            raise ValueError(
                "Input contains NaN values."
            )

        if np.isinf(values).any():

            raise ValueError(
                "Input contains infinite values."
            )

        if model_input.shape[1] != 78:

            raise ValueError(
                "Expected 78 model features, "
                f"received {model_input.shape[1]}."
            )

        return model_input

    # =========================================================================
    # PREDICT
    # =========================================================================

    def predict(
        self,
        features: pd.DataFrame,
    ) -> np.ndarray:

        model_input = self._validate_input(
            features
        )

        predictions = self.model.predict(
            model_input
        )

        return np.asarray(
            predictions
        ).reshape(-1)

    # =========================================================================
    # PROBABILITIES
    # =========================================================================

    def predict_proba(
        self,
        features: pd.DataFrame,
    ) -> np.ndarray:

        model_input = self._validate_input(
            features
        )

        probabilities = self.model.predict_proba(
            model_input
        )

        probabilities = np.asarray(
            probabilities,
            dtype=np.float64,
        )

        if probabilities.ndim != 2:

            raise RuntimeError(
                f"Unexpected probability shape: "
                f"{probabilities.shape}"
            )

        if probabilities.shape[1] != len(
            self.classes_
        ):

            raise RuntimeError(
                "Probability/class mismatch."
            )

        return probabilities

    # =========================================================================
    # CONFIDENCE
    # =========================================================================

    @staticmethod
    def calculate_confidence(
        probabilities: np.ndarray,
    ) -> np.ndarray:

        return np.max(
            probabilities,
            axis=1,
        )

    # =========================================================================
    # BENIGN / ATTACK
    # =========================================================================

    def classify_detection(
        self,
        predictions: np.ndarray,
    ) -> np.ndarray:

        predictions = np.asarray(
            predictions
        ).reshape(-1)

        return np.where(
            predictions == self.benign_class_id,
            "BENIGN",
            "ATTACK",
        )

    # =========================================================================
    # COMPLETE DETECTION
    # =========================================================================

    def detect(
        self,
        features: pd.DataFrame,
    ) -> pd.DataFrame:

        model_input = self._validate_input(
            features
        )

        predictions = np.asarray(
            self.model.predict(
                model_input
            )
        ).reshape(-1)

        probabilities = np.asarray(
            self.model.predict_proba(
                model_input
            ),
            dtype=np.float64,
        )

        confidence = self.calculate_confidence(
            probabilities
        )

        detection = self.classify_detection(
            predictions
        )

        results = pd.DataFrame(
            {
                "Predicted_Class": predictions.astype(
                    int
                ),
                "Confidence": confidence,
                "Detection": detection,
            }
        )

        logger.info(
            "Detection completed | records=%d | attacks=%d | benign=%d",
            len(results),
            int(
                (results["Detection"] == "ATTACK").sum()
            ),
            int(
                (results["Detection"] == "BENIGN").sum()
            ),
        )

        return results

    # =========================================================================
    # DETAILED DETECTION
    # =========================================================================

    def detect_with_probabilities(
        self,
        features: pd.DataFrame,
    ) -> pd.DataFrame:

        results = self.detect(
            features
        )

        probabilities = self.predict_proba(
            features
        )

        probability_data = {}

        for index, class_id in enumerate(
            self.classes_
        ):

            probability_data[
                f"Probability_Class_{class_id}"
            ] = probabilities[:, index]

        probability_df = pd.DataFrame(
            probability_data
        )

        return pd.concat(
            [
                results,
                probability_df,
            ],
            axis=1,
        )

    # =========================================================================
    # SINGLE FLOW
    # =========================================================================

    def detect_single(
        self,
        features: pd.DataFrame,
    ) -> DetectionResult:

        if len(features) != 1:

            raise ValueError(
                "detect_single() requires exactly one record."
            )

        predictions = self.predict(
            features
        )

        probabilities = self.predict_proba(
            features
        )

        confidence = self.calculate_confidence(
            probabilities
        )

        detection = self.classify_detection(
            predictions
        )

        return DetectionResult(
            predicted_class=int(
                predictions[0]
            ),
            confidence=float(
                confidence[0]
            ),
            detection=str(
                detection[0]
            ),
            probabilities=probabilities[0],
        )


# =============================================================================
# SELF TEST
# =============================================================================

if __name__ == "__main__":

    print("=" * 80)
    print("ZUKA — XGBOOST DETECTOR SELF TEST")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Import the verified feature schema
    # -------------------------------------------------------------------------

    from src.preprocessing.feature_pipeline import (
        MODEL_FEATURE_NAMES,
    )

    print()
    print("MODEL")
    print("-" * 80)

    print(
        f"Model path: {DEFAULT_MODEL_PATH}"
    )

    print(
        f"Feature count: {len(MODEL_FEATURE_NAMES)}"
    )

    # -------------------------------------------------------------------------
    # Create detector
    # -------------------------------------------------------------------------

    detector = XGBoostDetector(
        model_path=DEFAULT_MODEL_PATH,
        feature_names=MODEL_FEATURE_NAMES,
    )

    print()
    print("MODEL INFORMATION")
    print("-" * 80)

    print(
        f"Model type : "
        f"{type(detector.model).__name__}"
    )

    print(
        f"Features   : "
        f"{detector.model_feature_count}"
    )

    print(
        f"Classes    : "
        f"{detector.classes_.tolist()}"
    )

    # -------------------------------------------------------------------------
    # SOFTWARE-ONLY INTERFACE TEST
    #
    # This verifies that the detector can accept the expected
    # 78-column DataFrame.
    #
    # It is NOT real network traffic.
    # -------------------------------------------------------------------------

    demo_data = pd.DataFrame(
        np.zeros(
            (
                2,
                len(MODEL_FEATURE_NAMES),
            ),
            dtype=np.float64,
        ),
        columns=MODEL_FEATURE_NAMES,
    )

    print()
    print("INPUT VALIDATION")
    print("-" * 80)

    print(
        f"Records  : {len(demo_data)}"
    )

    print(
        f"Features : {demo_data.shape[1]}"
    )

    print(
        "✓ 78-feature schema accepted"
    )

    # -------------------------------------------------------------------------
    # DETECTION
    # -------------------------------------------------------------------------

    print()
    print("RUNNING DETECTION")
    print("-" * 80)

    results = detector.detect(
        demo_data
    )

    print(results.to_string(index=False))

    # -------------------------------------------------------------------------
    # PROBABILITY TEST
    # -------------------------------------------------------------------------

    print()
    print("PROBABILITY TEST")
    print("-" * 80)

    detailed = detector.detect_with_probabilities(
        demo_data
    )

    print(
        f"Probability columns: "
        f"{len(detector.classes_)}"
    )

    print(
        "✓ Probability generation successful"
    )

    # -------------------------------------------------------------------------
    # SINGLE RECORD TEST
    # -------------------------------------------------------------------------

    print()
    print("SINGLE RECORD TEST")
    print("-" * 80)

    single = detector.detect_single(
        demo_data.iloc[[0]]
    )

    print(
        f"Predicted class : "
        f"{single.predicted_class}"
    )

    print(
        f"Confidence      : "
        f"{single.confidence:.6f}"
    )

    print(
        f"Detection       : "
        f"{single.detection}"
    )

    # -------------------------------------------------------------------------
    # FINAL ASSERTIONS
    # -------------------------------------------------------------------------

    assert len(results) == 2

    assert results.shape[1] == 3

    assert "Predicted_Class" in results.columns

    assert "Confidence" in results.columns

    assert "Detection" in results.columns

    assert np.all(
        results["Confidence"].between(
            0.0,
            1.0,
        )
    )

    assert detector.model_feature_count == 78

    assert len(detector.classes_) == 14

    print()
    print("=" * 80)
    print("✓ XGBoost detector self-test completed")
    print("=" * 80)