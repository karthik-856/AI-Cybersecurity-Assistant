"""
ZUKA — SHAP Explainability Engine

Provides SHAP-based explanations for the ZUKA XGBoost
cybersecurity detection model.

Responsibilities
----------------
1. Load a native XGBoost model.
2. Validate the 78-feature model schema.
3. Create a SHAP TreeExplainer.
4. Generate multiclass SHAP values.
5. Extract top explanatory features.
6. Generate human-readable explanations.
7. Support single and batch explanations.
8. Provide a self-test for PyCharm execution.

Expected model
--------------
XGBoost multiclass classifier
14 classes
78 features

The model is loaded from native XGBoost JSON format rather
than the previously corrupted joblib artifact.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import shap
import xgboost as xgb


# =============================================================================
# LOGGER
# =============================================================================

LOGGER = logging.getLogger("zuka.xai")


def _configure_logging() -> None:
    """
    Configure logging when this module is executed directly.
    """
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )


# =============================================================================
# DEFAULT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "multiclass"
    / "xgb_model.json"
)

DEFAULT_RESULTS_DIR = (
    PROJECT_ROOT
    / "results"
    / "tables"
    / "xai"
)

DEFAULT_REPORTS_DIR = (
    PROJECT_ROOT
    / "results"
    / "reports"
    / "xai"
)


# =============================================================================
# VERIFIED CIC-IDS2017 FEATURE SCHEMA
# =============================================================================

MODEL_FEATURE_NAMES = [
    "Destination Port",
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Max",
    "Fwd Packet Length Min",
    "Fwd Packet Length Mean",
    "Fwd Packet Length Std",
    "Bwd Packet Length Max",
    "Bwd Packet Length Min",
    "Bwd Packet Length Mean",
    "Bwd Packet Length Std",
    "Flow Bytes/s",
    "Flow Packets/s",
    "Flow IAT Mean",
    "Flow IAT Std",
    "Flow IAT Max",
    "Flow IAT Min",
    "Fwd IAT Total",
    "Fwd IAT Mean",
    "Fwd IAT Std",
    "Fwd IAT Max",
    "Fwd IAT Min",
    "Bwd IAT Total",
    "Bwd IAT Mean",
    "Bwd IAT Std",
    "Bwd IAT Max",
    "Bwd IAT Min",
    "Fwd PSH Flags",
    "Bwd PSH Flags",
    "Fwd URG Flags",
    "Bwd URG Flags",
    "Fwd Header Length",
    "Bwd Header Length",
    "Fwd Packets/s",
    "Bwd Packets/s",
    "Min Packet Length",
    "Max Packet Length",
    "Packet Length Mean",
    "Packet Length Std",
    "Packet Length Variance",
    "FIN Flag Count",
    "SYN Flag Count",
    "RST Flag Count",
    "PSH Flag Count",
    "ACK Flag Count",
    "URG Flag Count",
    "CWE Flag Count",
    "ECE Flag Count",
    "Down/Up Ratio",
    "Average Packet Size",
    "Avg Fwd Segment Size",
    "Avg Bwd Segment Size",
    "Fwd Header Length.1",
    "Fwd Avg Bytes/Bulk",
    "Fwd Avg Packets/Bulk",
    "Fwd Avg Bulk Rate",
    "Bwd Avg Bytes/Bulk",
    "Bwd Avg Packets/Bulk",
    "Bwd Avg Bulk Rate",
    "Subflow Fwd Packets",
    "Subflow Fwd Bytes",
    "Subflow Bwd Packets",
    "Subflow Bwd Bytes",
    "Init_Win_bytes_forward",
    "Init_Win_bytes_backward",
    "act_data_pkt_fwd",
    "min_seg_size_forward",
    "Active Mean",
    "Active Std",
    "Active Max",
    "Active Min",
    "Idle Mean",
    "Idle Std",
    "Idle Max",
    "Idle Min",
]


# =============================================================================
# SHAP EXPLAINER
# =============================================================================

class SHAPExplainer:
    """
    SHAP explainability engine for the ZUKA XGBoost detector.
    """

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        feature_names: Iterable[str] | None = None,
        output_dir: str | Path = DEFAULT_RESULTS_DIR,
        report_dir: str | Path = DEFAULT_REPORTS_DIR,
    ) -> None:

        self.model_path = Path(model_path)

        self.feature_names = list(
            feature_names
            if feature_names is not None
            else MODEL_FEATURE_NAMES
        )

        self.output_dir = Path(output_dir)
        self.report_dir = Path(report_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        self.model: Any = None
        self.explainer: Any = None
        self.shap_values: np.ndarray | None = None

        self._validate_feature_schema()
        self._load_model()
        self._create_explainer()

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def _validate_feature_schema(self) -> None:
        """
        Validate that the configured model schema contains exactly 78 features.
        """

        if len(self.feature_names) != 78:
            raise ValueError(
                f"ZUKA expects 78 model features, "
                f"but received {len(self.feature_names)}."
            )

        if len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError(
                "Duplicate feature names detected in model schema."
            )

        LOGGER.info(
            "Feature schema validated | features=%d",
            len(self.feature_names),
        )

    # =========================================================================
    # MODEL LOADING
    # =========================================================================

    def _load_model(self) -> None:
        """
        Load the native XGBoost JSON model.
        """

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"XGBoost model not found: {self.model_path}"
            )

        LOGGER.info(
            "Loading native XGBoost model: %s",
            self.model_path,
        )

        self.model = xgb.XGBClassifier()

        self.model.load_model(str(self.model_path))

        LOGGER.info(
            "Native XGBoost model loaded successfully | type=%s",
            type(self.model).__name__,
        )

        # ---------------------------------------------------------------------
        # Validate feature count
        # ---------------------------------------------------------------------

        model_feature_count = getattr(
            self.model,
            "n_features_in_",
            None,
        )

        if model_feature_count is not None:
            if model_feature_count != len(self.feature_names):
                raise ValueError(
                    "Model feature count does not match feature schema: "
                    f"model={model_feature_count}, "
                    f"schema={len(self.feature_names)}"
                )

        # ---------------------------------------------------------------------
        # Validate classes
        # ---------------------------------------------------------------------

        classes = getattr(self.model, "classes_", None)

        if classes is not None:
            LOGGER.info(
                "Model classes verified | classes=%s",
                classes.tolist(),
            )

    # =========================================================================
    # SHAP EXPLAINER
    # =========================================================================

    def _create_explainer(self) -> None:
        """
        Create a SHAP TreeExplainer for the XGBoost model.
        """

        LOGGER.info("Creating SHAP TreeExplainer")

        self.explainer = shap.TreeExplainer(self.model)

        LOGGER.info("SHAP TreeExplainer created successfully")

    # =========================================================================
    # INPUT VALIDATION
    # =========================================================================

    def _prepare_input(
        self,
        X: pd.DataFrame | np.ndarray,
    ) -> pd.DataFrame:
        """
        Convert input into a validated DataFrame using the
        verified 78-feature schema.
        """

        if isinstance(X, pd.DataFrame):

            missing = [
                feature
                for feature in self.feature_names
                if feature not in X.columns
            ]

            if missing:
                raise ValueError(
                    "Missing required model features:\n"
                    + "\n".join(missing)
                )

            data = X[self.feature_names].copy()

        elif isinstance(X, np.ndarray):

            if X.ndim == 1:
                X = X.reshape(1, -1)

            if X.ndim != 2:
                raise ValueError(
                    "NumPy input must be a 2-dimensional array."
                )

            if X.shape[1] != len(self.feature_names):
                raise ValueError(
                    "Input feature count mismatch: "
                    f"received={X.shape[1]}, "
                    f"expected={len(self.feature_names)}"
                )

            data = pd.DataFrame(
                X,
                columns=self.feature_names,
            )

        else:

            raise TypeError(
                "X must be a pandas DataFrame or NumPy ndarray."
            )

        # Convert values to numeric.
        data = data.apply(
            pd.to_numeric,
            errors="coerce",
        )

        if data.isnull().any().any():
            raise ValueError(
                "Input contains missing or non-numeric feature values."
            )

        return data

    # =========================================================================
    # SHAP CALCULATION
    # =========================================================================

    def explain(
        self,
        X: pd.DataFrame | np.ndarray,
    ) -> np.ndarray:
        """
        Generate SHAP values.

        Returns
        -------
        numpy.ndarray

        Expected multiclass shape:

            (samples, features, classes)

        For ZUKA:

            (N, 78, 14)
        """

        data = self._prepare_input(X)

        LOGGER.info(
            "Calculating SHAP values | records=%d | features=%d",
            len(data),
            len(self.feature_names),
        )

        raw_values = self.explainer.shap_values(data)

        shap_array = self._normalize_shap_output(raw_values)

        self.shap_values = shap_array

        LOGGER.info(
            "SHAP values calculated | shape=%s",
            shap_array.shape,
        )

        return shap_array

    # =========================================================================
    # SHAP OUTPUT NORMALIZATION
    # =========================================================================

    def _normalize_shap_output(
        self,
        raw_values: Any,
    ) -> np.ndarray:
        """
        Normalize SHAP output across SHAP versions.

        ZUKA ultimately uses:

            samples × features × classes
        """

        # Newer SHAP versions can return an Explanation object.
        if isinstance(raw_values, shap.Explanation):
            values = raw_values.values
        else:
            values = raw_values

        # Some versions can return a list:
        # [class_0_array, class_1_array, ...]
        if isinstance(values, list):

            arrays = [
                np.asarray(value)
                for value in values
            ]

            values = np.stack(
                arrays,
                axis=-1,
            )

        values = np.asarray(values)

        # Binary/single-output safety.
        if values.ndim == 2:

            values = values[:, :, np.newaxis]

        if values.ndim != 3:
            raise ValueError(
                "Unexpected SHAP output dimensions: "
                f"{values.shape}"
            )

        expected_features = len(self.feature_names)

        if values.shape[1] != expected_features:

            # Some SHAP versions may return
            # (samples, classes, features).
            if values.shape[2] == expected_features:

                values = np.transpose(
                    values,
                    (0, 2, 1),
                )

            else:

                raise ValueError(
                    "SHAP feature dimension mismatch: "
                    f"shape={values.shape}, "
                    f"expected_features={expected_features}"
                )

        return values

    # =========================================================================
    # PREDICTION
    # =========================================================================

    def predict(
        self,
        X: pd.DataFrame | np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:

        data = self._prepare_input(X)

        predictions = self.model.predict(data)

        probabilities = self.model.predict_proba(data)

        return (
            np.asarray(predictions),
            np.asarray(probabilities),
        )

    # =========================================================================
    # TOP FEATURES
    # =========================================================================

    def top_features(
        self,
        X: pd.DataFrame | np.ndarray,
        top_n: int = 10,
    ) -> list[list[dict[str, Any]]]:
        """
        Return the strongest SHAP features for each prediction.

        Positive SHAP:
            supports the predicted class.

        Negative SHAP:
            opposes the predicted class.
        """

        if top_n <= 0:
            raise ValueError("top_n must be greater than zero.")

        data = self._prepare_input(X)

        predictions, _ = self.predict(data)

        values = self.explain(data)

        results: list[list[dict[str, Any]]] = []

        for row_index, predicted_class in enumerate(predictions):

            class_index = int(predicted_class)

            if class_index >= values.shape[2]:
                raise ValueError(
                    f"Predicted class {class_index} is outside "
                    f"SHAP class dimension {values.shape[2]}."
                )

            class_shap = values[
                row_index,
                :,
                class_index,
            ]

            absolute_shap = np.abs(class_shap)

            ranked_indices = np.argsort(
                absolute_shap
            )[::-1][:top_n]

            row_features: list[dict[str, Any]] = []

            for feature_index in ranked_indices:

                feature_index = int(feature_index)

                row_features.append(
                    {
                        "Feature": self.feature_names[feature_index],
                        "Feature_Value": float(
                            data.iloc[
                                row_index,
                                feature_index,
                            ]
                        ),
                        "SHAP_Value": float(
                            class_shap[feature_index]
                        ),
                        "Absolute_SHAP": float(
                            absolute_shap[feature_index]
                        ),
                    }
                )

            results.append(row_features)

        return results

    # =========================================================================
    # HUMAN-READABLE EXPLANATION
    # =========================================================================

    def generate_explanation(
        self,
        X: pd.DataFrame | np.ndarray,
        top_n: int = 5,
    ) -> list[str]:
        """
        Generate analyst-readable explanations.
        """

        predictions, probabilities = self.predict(X)

        feature_groups = self.top_features(
            X,
            top_n=top_n,
        )

        explanations: list[str] = []

        for index, predicted_class in enumerate(predictions):

            confidence = float(
                probabilities[index].max()
            )

            features = feature_groups[index]

            feature_text = ", ".join(
                item["Feature"]
                for item in features
            )

            explanation = (
                f"ZUKA classified the network flow as "
                f"attack class {int(predicted_class)} "
                f"with {confidence * 100:.2f}% confidence. "
                f"The principal SHAP explanatory features are: "
                f"{feature_text}. "
                f"These features represent model evidence "
                f"associated with the prediction and should "
                f"be validated against surrounding network "
                f"and security telemetry."
            )

            explanations.append(explanation)

        return explanations

    # =========================================================================
    # DATAFRAME OUTPUT
    # =========================================================================

    def create_explanation_table(
        self,
        X: pd.DataFrame | np.ndarray,
        top_n: int = 5,
    ) -> pd.DataFrame:
        """
        Create a flat analyst-ready explanation table.
        """

        data = self._prepare_input(X)

        predictions, probabilities = self.predict(data)

        top_groups = self.top_features(
            data,
            top_n=top_n,
        )

        rows: list[dict[str, Any]] = []

        for index, predicted_class in enumerate(predictions):

            confidence = float(
                probabilities[index].max()
            )

            row: dict[str, Any] = {
                "Sample_Index": index,
                "Predicted_Class": int(predicted_class),
                "Confidence": confidence,
            }

            for rank, feature in enumerate(
                top_groups[index],
                start=1,
            ):

                row[f"Top_Feature_{rank}"] = feature[
                    "Feature"
                ]

                row[f"Top_Feature_{rank}_Value"] = feature[
                    "Feature_Value"
                ]

                row[f"Top_Feature_{rank}_SHAP"] = feature[
                    "SHAP_Value"
                ]

            rows.append(row)

        return pd.DataFrame(rows)

    # =========================================================================
    # SAVE RESULTS
    # =========================================================================

    def save_explanations(
        self,
        X: pd.DataFrame | np.ndarray,
        filename: str = "zuka_shap_explanations.csv",
        top_n: int = 5,
    ) -> Path:
        """
        Save explanation table to CSV.
        """

        output_path = self.output_dir / filename

        table = self.create_explanation_table(
            X,
            top_n=top_n,
        )

        table.to_csv(
            output_path,
            index=False,
        )

        LOGGER.info(
            "SHAP explanation table saved: %s",
            output_path,
        )

        return output_path

    # =========================================================================
    # SELF TEST
    # =========================================================================

    def self_test(
        self,
        X_test: pd.DataFrame | np.ndarray,
        sample_size: int = 2,
    ) -> None:
        """
        Run an end-to-end SHAP self-test.
        """

        print()
        print("=" * 80)
        print("ZUKA — SHAP EXPLAINER SELF TEST")
        print("=" * 80)

        print()
        print("MODEL")
        print("-" * 80)
        print(f"Model path    : {self.model_path}")
        print(f"Feature count : {len(self.feature_names)}")

        data = self._prepare_input(X_test)

        sample = data.iloc[
            :min(sample_size, len(data))
        ].copy()

        print()
        print("INPUT")
        print("-" * 80)
        print(f"Records  : {len(sample)}")
        print(f"Features : {sample.shape[1]}")

        if sample.shape[1] != 78:
            raise AssertionError(
                "Expected 78 features."
            )

        print("✓ 78-feature schema accepted")

        print()
        print("MODEL PREDICTION")
        print("-" * 80)

        predictions, probabilities = self.predict(
            sample
        )

        for index in range(len(sample)):

            print(
                f"Record {index + 1}: "
                f"class={int(predictions[index])} | "
                f"confidence={probabilities[index].max():.6f}"
            )

        print("✓ Prediction test successful")

        print()
        print("SHAP CALCULATION")
        print("-" * 80)

        values = self.explain(sample)

        print(f"SHAP shape: {values.shape}")

        expected_shape = (
            len(sample),
            78,
            probabilities.shape[1],
        )

        if values.shape != expected_shape:
            raise AssertionError(
                "Unexpected SHAP shape: "
                f"{values.shape}; "
                f"expected={expected_shape}"
            )

        print("✓ Multiclass SHAP structure verified")

        print()
        print("TOP FEATURES")
        print("-" * 80)

        top = self.top_features(
            sample,
            top_n=5,
        )

        for index, features in enumerate(top):

            print(
                f"Record {index + 1}"
            )

            for rank, feature in enumerate(
                features,
                start=1,
            ):

                print(
                    f"  {rank}. "
                    f"{feature['Feature']} | "
                    f"SHAP={feature['SHAP_Value']:.6f}"
                )

        print()
        print("HUMAN-READABLE EXPLANATION")
        print("-" * 80)

        explanations = self.generate_explanation(
            sample,
            top_n=5,
        )

        for index, explanation in enumerate(
            explanations,
            start=1,
        ):

            print(
                f"{index}. {explanation}"
            )

        print()
        print("=" * 80)
        print("✓ SHAP explainer self-test completed")
        print("=" * 80)


# =============================================================================
# DIRECT EXECUTION / PYCHARM SELF TEST
# =============================================================================

if __name__ == "__main__":

    _configure_logging()

    print("=" * 80)
    print("ZUKA — SHAP EXPLAINER")
    print("=" * 80)

    print()
    print("CHECKING MODEL")
    print("-" * 80)
    print(f"Path: {DEFAULT_MODEL_PATH}")

    if not DEFAULT_MODEL_PATH.exists():

        raise FileNotFoundError(
            "Native XGBoost model not found:\n"
            f"{DEFAULT_MODEL_PATH}\n\n"
            "Place xgb_model.json in:\n"
            "models/multiclass/"
        )

    # -------------------------------------------------------------------------
    # Load a tiny synthetic schema-compatible sample.
    #
    # This is ONLY for checking that the SHAP pipeline itself works.
    # It is not presented as real network traffic.
    # -------------------------------------------------------------------------

    print()
    print("CREATING SELF-TEST INPUT")
    print("-" * 80)

    rng = np.random.default_rng(42)

    test_data = pd.DataFrame(
        rng.normal(
            0,
            1,
            size=(2, 78),
        ),
        columns=MODEL_FEATURE_NAMES,
    )

    # Values that should remain non-negative for common
    # flow-count/length fields.
    for column in [
        "Destination Port",
        "Flow Duration",
        "Total Fwd Packets",
        "Total Backward Packets",
        "Total Length of Fwd Packets",
        "Total Length of Bwd Packets",
    ]:

        test_data[column] = np.abs(
            test_data[column]
        )

    # -------------------------------------------------------------------------
    # Initialize explainer.
    # -------------------------------------------------------------------------

    explainer = SHAPExplainer(
        model_path=DEFAULT_MODEL_PATH,
        feature_names=MODEL_FEATURE_NAMES,
    )

    # -------------------------------------------------------------------------
    # Run self-test.
    # -------------------------------------------------------------------------

    explainer.self_test(
        test_data,
        sample_size=2,
    )