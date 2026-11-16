"""
ZUKA - SHAP / XAI Explanation Generator
========================================

Purpose
-------
Generate real SHAP explanations for the trained unified ZUKA XGBoost model.

Inputs
------
models/zuka_unified_xgboost/
    model.json
    label_encoder.json
    feature_schema.json

data/processed/zuka_unified/splits/
    test.csv

Outputs
-------
results/xai/zuka_unified/
    shap_metadata.json
    shap_global_importance.csv
    shap_class_importance.csv
    shap_test_predictions.csv
    shap_event_explanations.csv
    shap_summary.csv

Notes
-----
- SHAP is calculated from the actual trained XGBoost model.
- Only the 14 ZUKA common ML features are used.
- Dataset identifiers, IPs, ports, protocol, and synthetic flags are NOT
  passed to the model or SHAP.
- SHAP is calculated on a configurable sample rather than all 327k test rows
  by default, because full multiclass SHAP can be computationally expensive.
- No explanation text is hard-coded to a particular attack class.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import xgboost as xgb  # type: ignore[reportMissingImports]


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

MODEL_DIR = ROOT / "models" / "zuka_unified_xgboost"
TEST_PATH = ROOT / "data" / "processed" / "zuka_unified" / "splits" / "test.csv"
OUTPUT_DIR = ROOT / "results" / "xai" / "zuka_unified"

MODEL_PATH = MODEL_DIR / "model.json"
LABEL_ENCODER_PATH = MODEL_DIR / "label_encoder.json"
FEATURE_SCHEMA_PATH = MODEL_DIR / "feature_schema.json"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Number of test rows used for SHAP calculation.
# Increase after the first successful run if desired.
SHAP_SAMPLE_SIZE = 5000

# Number of top positive/negative features stored per event.
TOP_FEATURES_PER_EVENT = 5

# Only keep these predictions in the detailed event explanation file.
# Set to None to keep every sampled event.
DETAILED_ATTACK_ONLY = True

RANDOM_STATE = 20260907


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_feature_schema(schema: dict) -> list[str]:
    """
    Accept common feature_schema.json structures.
    """
    if isinstance(schema, list):
        return [str(x) for x in schema]

    for key in ("features", "feature_names", "ml_features", "columns"):
        value = schema.get(key)
        if isinstance(value, list):
            return [str(x) for x in value]

    raise ValueError(
        f"Could not find feature names in {FEATURE_SCHEMA_PATH}. "
        f"Expected one of: features, feature_names, ml_features, columns."
    )


def normalize_label_mapping(mapping: dict) -> dict[int, str]:
    """
    Accept either:
      {"0": "BACKDOOR", ...}
    or:
      {"classes": ["BACKDOOR", ...]}
    """
    if "classes" in mapping and isinstance(mapping["classes"], list):
        return {i: str(v) for i, v in enumerate(mapping["classes"])}

    result = {}
    for key, value in mapping.items():
        try:
            result[int(key)] = str(value)
        except (TypeError, ValueError):
            continue

    if not result:
        raise ValueError(
            f"Could not parse label mapping from {LABEL_ENCODER_PATH}."
        )

    return result


def get_shap_matrix_for_class(
    shap_values,
    class_index: int,
    n_rows: int,
    n_features: int,
    n_classes: int,
) -> np.ndarray:
    """
    Normalize SHAP's different multiclass return formats into:

        rows x features

    for one predicted/selected class.
    """
    # Newer SHAP commonly returns:
    # (rows, features, classes)
    if isinstance(shap_values, np.ndarray):
        arr = shap_values

        if arr.ndim == 3:
            if arr.shape == (n_rows, n_features, n_classes):
                return arr[:, :, class_index]

            if arr.shape == (n_rows, n_classes, n_features):
                return arr[:, class_index, :]

        # Binary/single-output fallback
        if arr.ndim == 2 and arr.shape == (n_rows, n_features):
            return arr

    # Older SHAP may return a list:
    # [array(rows, features), ...]
    if isinstance(shap_values, list):
        if len(shap_values) == n_classes:
            return np.asarray(shap_values[class_index])

        if len(shap_values) == 1:
            return np.asarray(shap_values[0])

    raise ValueError(
        "Unsupported SHAP output shape/type. "
        f"type={type(shap_values)}, "
        f"shape={getattr(shap_values, 'shape', None)}"
    )


def top_contributions(
    values: np.ndarray,
    feature_names: list[str],
    row_values: np.ndarray,
    top_n: int,
) -> list[dict]:
    """
    Return strongest positive and negative contributions.
    """
    records = []

    positive_indices = np.argsort(values)[::-1][:top_n]
    negative_indices = np.argsort(values)[:top_n]

    for idx in positive_indices:
        records.append(
            {
                "feature": feature_names[idx],
                "feature_value": float(row_values[idx]),
                "shap_value": float(values[idx]),
                "direction": "supports_prediction",
            }
        )

    for idx in negative_indices:
        records.append(
            {
                "feature": feature_names[idx],
                "feature_value": float(row_values[idx]),
                "shap_value": float(values[idx]),
                "direction": "opposes_prediction",
            }
        )

    # Sort by absolute contribution after combining both directions.
    records.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    return records[: top_n * 2]


def main() -> None:
    started = time.time()

    print("=" * 100)
    print("ZUKA - SHAP / XAI EXPLANATION GENERATION")
    print("=" * 100)

    # -----------------------------------------------------------------------
    # Validate files
    # -----------------------------------------------------------------------

    required = [
        MODEL_PATH,
        LABEL_ENCODER_PATH,
        FEATURE_SCHEMA_PATH,
        TEST_PATH,
    ]

    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Load model metadata
    # -----------------------------------------------------------------------

    print("\nLoading model...")
    model = xgb.XGBClassifier()
    model.load_model(str(MODEL_PATH))

    label_mapping = normalize_label_mapping(load_json(LABEL_ENCODER_PATH))
    schema = load_json(FEATURE_SCHEMA_PATH)
    feature_names = normalize_feature_schema(schema)

    print(f"  Model: {MODEL_PATH}")
    print(f"  Features: {len(feature_names)}")
    print(f"  Classes: {len(label_mapping)}")

    if len(feature_names) != 14:
        raise ValueError(
            f"Expected exactly 14 ZUKA common features, found {len(feature_names)}."
        )

    # -----------------------------------------------------------------------
    # Load test data
    # -----------------------------------------------------------------------

    print("\nLoading TEST data...")
    df = pd.read_csv(TEST_PATH, low_memory=False)

    missing = [f for f in feature_names if f not in df.columns]
    if missing:
        raise ValueError(f"Missing model features in test data: {missing}")

    X_all = df[feature_names].apply(pd.to_numeric, errors="coerce")

    if X_all.isna().any().any():
        bad = X_all.columns[X_all.isna().any()].tolist()
        raise ValueError(f"NaN values found in model features: {bad}")

    if not np.isfinite(X_all.to_numpy(dtype=np.float64)).all():
        raise ValueError("Infinite values found in model features.")

    # -----------------------------------------------------------------------
    # Predictions on the complete test set
    # -----------------------------------------------------------------------

    print("\nGenerating test predictions...")
    probabilities_all = model.predict_proba(X_all)
    predictions_all = np.argmax(probabilities_all, axis=1)

    predicted_confidence_all = probabilities_all[
        np.arange(len(predictions_all)), predictions_all
    ]

    predicted_labels_all = [
        label_mapping.get(int(i), f"CLASS_{int(i)}")
        for i in predictions_all
    ]

    actual_labels_all = (
        df["zuka_attack_class"].astype(str).tolist()
        if "zuka_attack_class" in df.columns
        else [None] * len(df)
    )

    prediction_frame = pd.DataFrame(
        {
            "test_row_index": np.arange(len(df)),
            "predicted_class_id": predictions_all,
            "predicted_class": predicted_labels_all,
            "confidence": predicted_confidence_all,
            "actual_class": actual_labels_all,
        }
    )

    prediction_frame.to_csv(
        OUTPUT_DIR / "shap_test_predictions.csv",
        index=False,
    )

    # -----------------------------------------------------------------------
    # Select SHAP sample
    # -----------------------------------------------------------------------

    n_sample = min(SHAP_SAMPLE_SIZE, len(df))

    rng = np.random.default_rng(RANDOM_STATE)
    sample_indices = np.sort(
        rng.choice(len(df), size=n_sample, replace=False)
    )

    X = X_all.iloc[sample_indices].reset_index(drop=True)
    sample_df = df.iloc[sample_indices].reset_index(drop=True)

    probabilities = probabilities_all[sample_indices]
    predictions = predictions_all[sample_indices]
    confidences = predicted_confidence_all[sample_indices]

    print(f"\nSHAP sample size: {n_sample}")
    print("Creating TreeExplainer...")

    # TreeExplainer uses the trained tree model directly.
    explainer = shap.TreeExplainer(model)

    print("Calculating SHAP values...")
    shap_values = explainer.shap_values(X, check_additivity=False)

    n_rows = len(X)
    n_features = len(feature_names)
    n_classes = len(label_mapping)

    # -----------------------------------------------------------------------
    # Global feature importance
    # -----------------------------------------------------------------------

    print("\nCalculating global SHAP importance...")

    # Aggregate absolute SHAP contribution over the class dimension.
    if isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        if shap_values.shape == (n_rows, n_features, n_classes):
            global_abs = np.abs(shap_values).mean(axis=(0, 2))
        elif shap_values.shape == (n_rows, n_classes, n_features):
            global_abs = np.abs(shap_values).mean(axis=(0, 1))
        else:
            raise ValueError(
                f"Unexpected 3D SHAP shape: {shap_values.shape}"
            )
    elif isinstance(shap_values, list):
        stacked = np.stack(
            [np.asarray(v) for v in shap_values],
            axis=2,
        )
        global_abs = np.abs(stacked).mean(axis=(0, 2))
    else:
        arr = np.asarray(shap_values)
        global_abs = np.abs(arr).mean(axis=0)

    global_importance = pd.DataFrame(
        {
            "feature": feature_names,
            "mean_abs_shap": global_abs,
        }
    ).sort_values("mean_abs_shap", ascending=False)

    global_importance["rank"] = np.arange(1, len(global_importance) + 1)

    global_importance.to_csv(
        OUTPUT_DIR / "shap_global_importance.csv",
        index=False,
    )

    # -----------------------------------------------------------------------
    # Per-class SHAP importance
    # -----------------------------------------------------------------------

    print("Calculating per-class SHAP importance...")

    class_rows = []

    for class_id in range(n_classes):
        class_label = label_mapping.get(class_id, f"CLASS_{class_id}")

        class_shap = get_shap_matrix_for_class(
            shap_values,
            class_id,
            n_rows,
            n_features,
            n_classes,
        )

        importance = np.abs(class_shap).mean(axis=0)

        for feature, value in zip(feature_names, importance):
            class_rows.append(
                {
                    "class_id": class_id,
                    "class": class_label,
                    "feature": feature,
                    "mean_abs_shap": float(value),
                }
            )

    class_importance = pd.DataFrame(class_rows)
    class_importance["rank"] = (
        class_importance
        .groupby("class")["mean_abs_shap"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    class_importance = class_importance.sort_values(
        ["class_id", "rank"]
    )

    class_importance.to_csv(
        OUTPUT_DIR / "shap_class_importance.csv",
        index=False,
    )

    # -----------------------------------------------------------------------
    # Per-event explanation
    # -----------------------------------------------------------------------

    print("Generating per-event explanations...")

    event_rows = []

    for row_pos in range(n_rows):
        predicted_class_id = int(predictions[row_pos])
        predicted_class = label_mapping.get(
            predicted_class_id,
            f"CLASS_{predicted_class_id}",
        )

        if DETAILED_ATTACK_ONLY and predicted_class == "BENIGN":
            continue

        class_shap = get_shap_matrix_for_class(
            shap_values,
            predicted_class_id,
            n_rows,
            n_features,
            n_classes,
        )

        row_shap = class_shap[row_pos]
        row_values = X.iloc[row_pos].to_numpy(dtype=float)

        contributions = top_contributions(
            row_shap,
            feature_names,
            row_values,
            TOP_FEATURES_PER_EVENT,
        )

        positives = [
            c for c in contributions
            if c["direction"] == "supports_prediction"
        ]
        negatives = [
            c for c in contributions
            if c["direction"] == "opposes_prediction"
        ]

        record = {
            "test_row_index": int(sample_indices[row_pos]),
            "predicted_class_id": predicted_class_id,
            "predicted_class": predicted_class,
            "confidence": float(confidences[row_pos]),
            "actual_class": (
                str(sample_df.iloc[row_pos]["zuka_attack_class"])
                if "zuka_attack_class" in sample_df.columns
                else None
            ),
            "top_supporting_features": json.dumps(
                positives,
                separators=(",", ":"),
            ),
            "top_opposing_features": json.dumps(
                negatives,
                separators=(",", ":"),
            ),
        }

        # Store the top individual contributions in explicit columns too.
        for i, contribution in enumerate(contributions, start=1):
            record[f"feature_{i}"] = contribution["feature"]
            record[f"feature_{i}_value"] = contribution["feature_value"]
            record[f"feature_{i}_shap"] = contribution["shap_value"]
            record[f"feature_{i}_direction"] = contribution["direction"]

        # Preserve genuine network metadata if available.
        for column in (
            "source_ip",
            "destination_ip",
            "source_port",
            "destination_port",
            "protocol",
            "dataset_name",
            "original_attack_category",
            "scenario",
            "synthetic",
        ):
            if column in sample_df.columns:
                record[column] = sample_df.iloc[row_pos][column]

        event_rows.append(record)

    event_explanations = pd.DataFrame(event_rows)

    event_explanations.to_csv(
        OUTPUT_DIR / "shap_event_explanations.csv",
        index=False,
    )

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    attack_predictions = prediction_frame[
        prediction_frame["predicted_class"] != "BENIGN"
    ]

    summary_rows = []

    for class_id, class_label in label_mapping.items():
        subset = prediction_frame[
            prediction_frame["predicted_class"] == class_label
        ]

        actual_subset = prediction_frame[
            prediction_frame["actual_class"] == class_label
        ]

        summary_rows.append(
            {
                "class_id": class_id,
                "class": class_label,
                "sampled_rows": int(
                    (predictions == class_id).sum()
                ),
                "test_predictions": int(len(subset)),
                "actual_test_rows": int(len(actual_subset)),
                "mean_prediction_confidence": (
                    float(subset["confidence"].mean())
                    if len(subset)
                    else 0.0
                ),
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(
        OUTPUT_DIR / "shap_summary.csv",
        index=False,
    )

    # -----------------------------------------------------------------------
    # Metadata
    # -----------------------------------------------------------------------

    elapsed = time.time() - started

    metadata = {
        "tool": "SHAP TreeExplainer",
        "model": str(MODEL_PATH),
        "test_dataset": str(TEST_PATH),
        "output_directory": str(OUTPUT_DIR),
        "test_rows": int(len(df)),
        "shap_sample_rows": int(n_sample),
        "feature_count": int(len(feature_names)),
        "features": feature_names,
        "class_count": int(len(label_mapping)),
        "classes": [
            label_mapping[i] for i in sorted(label_mapping)
        ],
        "detailed_attack_only": DETAILED_ATTACK_ONLY,
        "top_features_per_event": TOP_FEATURES_PER_EVENT,
        "random_state": RANDOM_STATE,
        "ml_features_only": True,
        "excluded_from_ml": [
            "dataset_name",
            "source_ip",
            "destination_ip",
            "source_port",
            "destination_port",
            "protocol",
            "synthetic",
            "zuka_attack_class",
            "original_attack_category",
        ],
        "runtime_seconds": round(elapsed, 2),
    }

    with (OUTPUT_DIR / "shap_metadata.json").open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "=" * 100)
    print("ZUKA SHAP / XAI GENERATION COMPLETE")
    print("=" * 100)
    print(f"Test rows             : {len(df):,}")
    print(f"SHAP rows analyzed    : {n_sample:,}")
    print(f"Features              : {len(feature_names)}")
    print(f"Classes               : {len(label_mapping)}")
    print(f"Detailed explanations : {len(event_explanations):,}")
    print(f"Runtime               : {elapsed / 60:.2f} minutes")
    print()
    print(f"Output directory      : {OUTPUT_DIR}")
    print()
    print("Generated:")
    print("  shap_metadata.json")
    print("  shap_global_importance.csv")
    print("  shap_class_importance.csv")
    print("  shap_test_predictions.csv")
    print("  shap_event_explanations.csv")
    print("  shap_summary.csv")
    print("=" * 100)


if __name__ == "__main__":
    main()
