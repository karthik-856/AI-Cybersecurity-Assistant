"""
ZUKA - AI Cybersecurity SOC Assistant
=====================================

Module:
    src/preprocessing/feature_pipeline.py

Purpose:
    Convert collected network-flow records into the exact feature
    representation required by the trained XGBoost detector.

Responsibilities:
    1. Validate incoming flow data.
    2. Recover the verified 78-feature model schema.
    3. Preserve feature names and feature order.
    4. Validate numeric values.
    5. Handle missing/non-finite values safely.
    6. Produce model-ready feature matrices.

Important:
    This module does NOT perform attack detection.
    This module does NOT generate alerts.
    This module does NOT generate SHAP explanations.

Pipeline:

    TrafficCollector
          ↓
    FeaturePipeline
          ↓
    XGBoostDetector
          ↓
    SHAP
          ↓
    Alert Engine
          ↓
    Recommendation Engine
          ↓
    ZUKA
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger("zuka.preprocessing")

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


# ============================================================================
# MODEL FEATURE SCHEMA
# ============================================================================

# These are the verified 78 features used by the trained XGBoost model.
#
# IMPORTANT:
# Keep this order unchanged.
#
# This schema is intentionally explicit so that the real application does
# not accidentally replace feature names with positional names such as:
#
#     0, 1, 2, ..., 77
#
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


# ============================================================================
# DATA STRUCTURE
# ============================================================================

@dataclass
class ProcessedFlowBatch:
    """
    Container for model-ready flow data.

    Attributes
    ----------
    features:
        DataFrame containing exactly the 78 model features.

    original_data:
        Original collected records.

    source:
        Source name.

    record_count:
        Number of processed records.
    """

    features: pd.DataFrame
    original_data: pd.DataFrame
    source: str
    record_count: int


# ============================================================================
# FEATURE PIPELINE
# ============================================================================

class FeaturePipeline:
    """
    ZUKA network-flow preprocessing pipeline.

    The central guarantee of this class is:

        incoming DataFrame
                 ↓
        validation
                 ↓
        exact 78-feature selection
                 ↓
        exact feature ordering
                 ↓
        numeric conversion
                 ↓
        finite-value validation
                 ↓
        model-ready DataFrame
    """

    def __init__(
        self,
        feature_names: Optional[Sequence[str]] = None,
        fill_missing: bool = False,
    ) -> None:

        if feature_names is None:
            feature_names = MODEL_FEATURE_NAMES

        self.feature_names = list(feature_names)
        self.fill_missing = fill_missing

        self._validate_schema()

        logger.info(
            "FeaturePipeline initialized | features=%d",
            len(self.feature_names),
        )

    # ========================================================================
    # SCHEMA VALIDATION
    # ========================================================================

    def _validate_schema(self) -> None:
        """Validate the configured feature schema."""

        if len(self.feature_names) != 78:
            raise ValueError(
                "ZUKA model schema must contain exactly 78 features. "
                f"Received {len(self.feature_names)}."
            )

        if len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError(
                "Duplicate feature names detected in model schema."
            )

        if not all(
            isinstance(name, str)
            and name.strip()
            for name in self.feature_names
        ):
            raise ValueError(
                "Every feature name must be a non-empty string."
            )

    # ========================================================================
    # FEATURE NAME ACCESS
    # ========================================================================

    def get_feature_names(self) -> list[str]:
        """Return a copy of the verified 78-feature schema."""

        return self.feature_names.copy()

    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================

    @staticmethod
    def _validate_input(
        flow_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Validate the basic input DataFrame."""

        if not isinstance(flow_df, pd.DataFrame):
            raise TypeError(
                "flow_df must be a pandas DataFrame."
            )

        if flow_df.empty:
            raise ValueError(
                "Received an empty network-flow DataFrame."
            )

        if flow_df.columns.duplicated().any():

            duplicated = flow_df.columns[
                flow_df.columns.duplicated()
            ].tolist()

            raise ValueError(
                f"Duplicate input columns detected: {duplicated}"
            )

        return flow_df.copy()

    # ========================================================================
    # REQUIRED FEATURE CHECK
    # ========================================================================

    def find_missing_features(
        self,
        flow_df: pd.DataFrame,
    ) -> list[str]:
        """Return model features missing from the incoming DataFrame."""

        return [
            feature
            for feature in self.feature_names
            if feature not in flow_df.columns
        ]

    def find_extra_features(
        self,
        flow_df: pd.DataFrame,
    ) -> list[str]:
        """Return input columns that are not model features."""

        return [
            column
            for column in flow_df.columns
            if column not in self.feature_names
        ]

    # ========================================================================
    # MODEL FEATURE EXTRACTION
    # ========================================================================

    def select_model_features(
        self,
        flow_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Select exactly the 78 model features.

        Feature order is explicitly controlled here.
        """

        flow_df = self._validate_input(flow_df)

        missing = self.find_missing_features(flow_df)

        if missing:

            logger.error(
                "Missing model features: %s",
                missing,
            )

            raise ValueError(
                "Incoming network-flow data is missing required "
                "model features:\n"
                + "\n".join(missing)
            )

        # IMPORTANT:
        # Explicitly select using feature names and order.
        #
        # Never use:
        #
        #     flow_df.iloc[:, :78]
        #
        # because live input column order may differ.
        selected = flow_df.loc[
            :,
            self.feature_names,
        ].copy()

        return selected

    # ========================================================================
    # NUMERIC CONVERSION
    # ========================================================================

    def convert_to_numeric(
        self,
        features: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Convert model features to numeric values.

        Values that cannot be converted become NaN and are subsequently
        handled by validate_numeric_features().
        """

        numeric = features.copy()

        for column in self.feature_names:

            numeric[column] = pd.to_numeric(
                numeric[column],
                errors="coerce",
            )

        return numeric

    # ========================================================================
    # NON-FINITE VALUE VALIDATION
    # ========================================================================

    def validate_numeric_features(
        self,
        features: pd.DataFrame,
    ) -> None:
        """Reject NaN and infinite values unless filling is enabled."""

        numeric_array = features.to_numpy(
            dtype=np.float64,
        )

        nan_count = int(
            np.isnan(numeric_array).sum()
        )

        inf_count = int(
            np.isinf(numeric_array).sum()
        )

        if nan_count == 0 and inf_count == 0:
            return

        if self.fill_missing:

            logger.warning(
                "Non-finite values detected | NaN=%d | Inf=%d",
                nan_count,
                inf_count,
            )

            return

        raise ValueError(
            "Network-flow data contains invalid numeric values. "
            f"NaN={nan_count}, Inf={inf_count}. "
            "The feature pipeline will not silently invent values."
        )

    # ========================================================================
    # OPTIONAL SAFE VALUE CLEANING
    # ========================================================================

    def clean_numeric_features(
        self,
        features: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Optionally replace invalid values.

        This is disabled by default.

        If enabled:
            NaN → 0
            +Inf → 0
            -Inf → 0

        In production, this behavior should eventually be aligned with
        the exact preprocessing used during model training.
        """

        cleaned = features.copy()

        if not self.fill_missing:
            return cleaned

        cleaned = cleaned.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        cleaned = cleaned.fillna(0)

        return cleaned

    # ========================================================================
    # COMPLETE PROCESSING PIPELINE
    # ========================================================================

    def transform(
        self,
        flow_df: pd.DataFrame,
        source: str = "automatic_network_input",
    ) -> ProcessedFlowBatch:
        """
        Transform incoming network-flow records into model-ready data.
        """

        logger.info(
            "Starting feature preprocessing | source=%s | records=%d",
            source,
            len(flow_df),
        )

        original_data = self._validate_input(
            flow_df,
        )

        # Step 1 — exact feature selection
        features = self.select_model_features(
            original_data,
        )

        # Step 2 — numeric conversion
        features = self.convert_to_numeric(
            features,
        )

        # Step 3 — optional cleaning
        features = self.clean_numeric_features(
            features,
        )

        # Step 4 — validation
        self.validate_numeric_features(
            features,
        )

        # Step 5 — final order verification
        if list(features.columns) != self.feature_names:

            raise RuntimeError(
                "CRITICAL: Final feature order does not match "
                "the ZUKA model schema."
            )

        logger.info(
            "Feature preprocessing completed | records=%d | features=%d",
            len(features),
            len(features.columns),
        )

        return ProcessedFlowBatch(
            features=features,
            original_data=original_data,
            source=source,
            record_count=len(features),
        )

    # ========================================================================
    # XGBOOST COMPATIBILITY
    # ========================================================================

    def prepare_for_model(
        self,
        flow_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Convenience method returning only the model-ready DataFrame.
        """

        processed = self.transform(
            flow_df,
        )

        return processed.features


# ============================================================================
# CIC-IDS2017 TEST HELPER
# ============================================================================

def prepare_cic_ids2017_sample(
    csv_path: str | Path,
    sample_size: int = 10,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Prepare a CIC-IDS2017 test sample for pipeline validation.

    This is for development/testing only.

    It does not represent live network ingestion.
    """

    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(
            f"CIC-IDS2017 file not found: {path}"
        )

    data = pd.read_csv(path)

    if data.empty:
        raise ValueError(
            "CIC-IDS2017 file contains no records."
        )

    # Remove label column if present.
    #
    # The trained model receives features only.
    label_candidates = [
        "Label",
        "Label_ID",
        "label",
        "label_id",
    ]

    columns_to_remove = [
        column
        for column in label_candidates
        if column in data.columns
    ]

    if columns_to_remove:
        data = data.drop(
            columns=columns_to_remove,
        )

    if sample_size > len(data):
        sample_size = len(data)

    sample = data.sample(
        n=sample_size,
        random_state=random_state,
    ).reset_index(drop=True)

    pipeline = FeaturePipeline()

    processed = pipeline.prepare_for_model(
        sample,
    )

    logger.info(
        "CIC-IDS2017 sample prepared | records=%d | features=%d",
        len(processed),
        len(processed.columns),
    )

    return processed


# ============================================================================
# SELF TEST
# ============================================================================

if __name__ == "__main__":

    print("=" * 80)
    print("ZUKA — FEATURE PIPELINE SELF TEST")
    print("=" * 80)

    print()
    print("MODEL FEATURE SCHEMA")
    print("-" * 80)

    print(
        f"Number of features: {len(MODEL_FEATURE_NAMES)}"
    )

    print()
    print("FIRST 10 FEATURES")
    print("-" * 80)

    for index, feature in enumerate(
        MODEL_FEATURE_NAMES[:10],
        start=1,
    ):
        print(
            f"{index:2d}. {feature}"
        )

    # Create synthetic test data using the REAL feature names.
    demo_data = pd.DataFrame(
        {
            feature: [1.0, 2.0]
            for feature in MODEL_FEATURE_NAMES
        }
    )

    pipeline = FeaturePipeline()

    result = pipeline.transform(
        demo_data,
        source="ZUKA_SELF_TEST",
    )

    print()
    print("PIPELINE RESULT")
    print("-" * 80)

    print(
        f"Input records       : {len(demo_data)}"
    )

    print(
        f"Output records      : {result.record_count}"
    )

    print(
        f"Output features     : {len(result.features.columns)}"
    )

    print(
        f"Output shape        : {result.features.shape}"
    )

    print(
        f"Feature order valid : "
        f"{list(result.features.columns) == MODEL_FEATURE_NAMES}"
    )

    print()
    print("FEATURE NAME CHECK")
    print("-" * 80)

    positional_names = [
        str(index)
        for index in range(78)
    ]

    if list(result.features.columns) == positional_names:
        raise RuntimeError(
            "ERROR: Positional feature names detected."
        )

    print(
        "✓ Real feature names preserved"
    )

    print(
        "✓ Exact 78-feature schema preserved"
    )

    print(
        "✓ Exact feature order preserved"
    )

    print(
        "✓ Numeric validation passed"
    )

    print()
    print("✓ FeaturePipeline self-test completed")