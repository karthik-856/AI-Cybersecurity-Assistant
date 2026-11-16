from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb  # type: ignore[reportMissingImports]
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SPLIT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "splits"
)

MODEL_DIR = (
    PROJECT_ROOT
    / "models"
    / "zuka_unified_xgboost"
)

TRAIN_FILE = SPLIT_DIR / "train.csv"
VALIDATION_FILE = SPLIT_DIR / "validation.csv"
TEST_FILE = SPLIT_DIR / "test.csv"

MODEL_FILE = MODEL_DIR / "model.json"
LABEL_ENCODER_FILE = MODEL_DIR / "label_encoder.json"
FEATURE_SCHEMA_FILE = MODEL_DIR / "feature_schema.json"
METRICS_FILE = MODEL_DIR / "metrics.json"
CLASSIFICATION_REPORT_FILE = (
    MODEL_DIR / "classification_report.csv"
)
CONFUSION_MATRIX_FILE = (
    MODEL_DIR / "confusion_matrix.csv"
)
FEATURE_IMPORTANCE_FILE = (
    MODEL_DIR / "feature_importance.csv"
)
TRAINING_METADATA_FILE = (
    MODEL_DIR / "training_metadata.json"
)


TARGET_COLUMN = "zuka_attack_class"

FEATURES = [
    "duration_sec",
    "src_packets",
    "dst_packets",
    "src_bytes",
    "dst_bytes",
    "flow_packet_rate",
    "src_packet_rate",
    "dst_packet_rate",
    "src_byte_rate",
    "dst_byte_rate",
    "src_packet_size_mean",
    "dst_packet_size_mean",
    "src_iat_mean_sec",
    "dst_iat_mean_sec",
]

RANDOM_STATE = 20260907

N_ESTIMATORS = 1200
LEARNING_RATE = 0.08
MAX_DEPTH = 8
MIN_CHILD_WEIGHT = 2
SUBSAMPLE = 0.85
COLSAMPLE_BYTREE = 0.85

EARLY_STOPPING_ROUNDS = 60


EXPECTED_CLASSES = [
    "BACKDOOR",
    "BENIGN",
    "BRUTE_FORCE",
    "DDOS",
    "DOS",
    "EXPLOIT",
    "FUZZING",
    "INFILTRATION",
    "MALWARE",
    "OTHER_ATTACK",
    "PORT_SCAN",
    "RECONNAISSANCE",
    "WEB_ATTACK",
]


def load_split(path: Path, name: str) -> pd.DataFrame:

    if not path.exists():
        raise FileNotFoundError(
            f"{name} dataset not found:\n{path}"
        )

    print(
        f"Loading {name}: {path.name}"
    )

    df = pd.read_csv(
        path,
        low_memory=False,
    )

    print(
        f"  Rows: {len(df):,}"
    )

    return df


def validate_split(
    df: pd.DataFrame,
    name: str,
) -> None:

    print(
        f"\nValidating {name}..."
    )

    required = [
        TARGET_COLUMN,
        *FEATURES,
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{name} is missing columns:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing
            )
        )

    if df.empty:
        raise ValueError(
            f"{name} is empty."
        )

    X = df[FEATURES].apply(
        pd.to_numeric,
        errors="coerce",
    )

    if X.isna().any().any():
        null_count = int(
            X.isna().sum().sum()
        )
        raise ValueError(
            f"{name} contains "
            f"{null_count:,} invalid/null feature values."
        )

    values = X.to_numpy(
        dtype=np.float32
    )

    if not np.isfinite(values).all():
        raise ValueError(
            f"{name} contains infinite feature values."
        )

    if (values < 0).any():
        raise ValueError(
            f"{name} contains negative feature values."
        )

    classes = set(
        df[TARGET_COLUMN]
        .dropna()
        .astype(str)
        .unique()
    )

    expected = set(
        EXPECTED_CLASSES
    )

    unknown = classes - expected

    if unknown:
        raise ValueError(
            f"{name} contains unknown classes: "
            f"{sorted(unknown)}"
        )

    missing_classes = expected - classes

    if missing_classes:
        raise ValueError(
            f"{name} is missing classes: "
            f"{sorted(missing_classes)}"
        )

    print(
        f"  Features: {len(FEATURES)}"
    )

    print(
        f"  Classes: {len(classes)}"
    )

    print(
        "  PASS"
    )


def prepare_features(
    df: pd.DataFrame,
) -> pd.DataFrame:

    return df[
        FEATURES
    ].astype(
        np.float32
    )


def print_class_distribution(
    y: pd.Series,
    name: str,
) -> None:

    print(
        f"\n{name} class distribution:"
    )

    counts = (
        y.value_counts()
        .sort_index()
    )

    for label, count in counts.items():
        percentage = (
            count
            / len(y)
            * 100
        )

        print(
            f"  {label:<18}"
            f"{count:>12,}"
            f"  ({percentage:6.2f}%)"
        )


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list[str],
) -> dict:

    return {
        "accuracy": float(
            accuracy_score(
                y_true,
                y_pred,
            )
        ),
        "precision_macro": float(
            precision_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),
        "recall_macro": float(
            recall_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),
        "f1_macro": float(
            f1_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),
        "precision_weighted": float(
            precision_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0,
            )
        ),
        "recall_weighted": float(
            recall_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0,
            )
        ),
        "f1_weighted": float(
            f1_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0,
            )
        ),
        "classification_report": classification_report(
            y_true,
            y_pred,
            labels=np.arange(
                len(class_names)
            ),
            target_names=class_names,
            output_dict=True,
            zero_division=0,
        ),
    }


def save_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list[str],
) -> None:

    matrix = confusion_matrix(
        y_true,
        y_pred,
        labels=np.arange(
            len(class_names)
        ),
    )

    matrix_df = pd.DataFrame(
        matrix,
        index=class_names,
        columns=class_names,
    )

    matrix_df.index.name = (
        "actual_class"
    )

    matrix_df.to_csv(
        CONFUSION_MATRIX_FILE
    )


def save_classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list[str],
) -> None:

    report = classification_report(
        y_true,
        y_pred,
        labels=np.arange(
            len(class_names)
        ),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    report_df = (
        pd.DataFrame(report)
        .transpose()
    )

    report_df.to_csv(
        CLASSIFICATION_REPORT_FILE
    )


def save_feature_importance(
    model: xgb.XGBClassifier,
) -> None:

    importance = model.feature_importances_

    result = pd.DataFrame(
        {
            "feature": FEATURES,
            "importance": importance,
        }
    )

    result["importance_percentage"] = (
        result["importance"]
        / result["importance"].sum()
        * 100
    )

    result = result.sort_values(
        "importance",
        ascending=False,
    )

    result.to_csv(
        FEATURE_IMPORTANCE_FILE,
        index=False,
    )


def main() -> None:

    start_time = time.time()

    print("=" * 100)
    print("ZUKA - UNIFIED XGBOOST TRAINING")
    print("=" * 100)

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ------------------------------------------------------------------
    # LOAD
    # ------------------------------------------------------------------

    train_df = load_split(
        TRAIN_FILE,
        "TRAIN",
    )

    validation_df = load_split(
        VALIDATION_FILE,
        "VALIDATION",
    )

    test_df = load_split(
        TEST_FILE,
        "TEST",
    )

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    validate_split(
        train_df,
        "TRAIN",
    )

    validate_split(
        validation_df,
        "VALIDATION",
    )

    validate_split(
        test_df,
        "TEST",
    )

    # ------------------------------------------------------------------
    # FEATURES
    # ------------------------------------------------------------------

    print(
        "\nPreparing ML features..."
    )

    X_train = prepare_features(
        train_df
    )

    X_validation = prepare_features(
        validation_df
    )

    X_test = prepare_features(
        test_df
    )

    y_train_text = (
        train_df[TARGET_COLUMN]
        .astype(str)
    )

    y_validation_text = (
        validation_df[TARGET_COLUMN]
        .astype(str)
    )

    y_test_text = (
        test_df[TARGET_COLUMN]
        .astype(str)
    )

    # ------------------------------------------------------------------
    # LABEL ENCODING
    # ------------------------------------------------------------------

    print(
        "\nCreating label encoder..."
    )

    encoder = LabelEncoder()

    encoder.fit(
        EXPECTED_CLASSES
    )

    y_train = encoder.transform(
        y_train_text
    )

    y_validation = encoder.transform(
        y_validation_text
    )

    y_test = encoder.transform(
        y_test_text
    )

    class_names = (
        encoder.classes_.tolist()
    )

    print(
        "Class mapping:"
    )

    for index, name in enumerate(
        class_names
    ):
        print(
            f"  {index:2d} -> {name}"
        )

    print_class_distribution(
        y_train_text,
        "TRAIN",
    )

    print_class_distribution(
        y_validation_text,
        "VALIDATION",
    )

    print_class_distribution(
        y_test_text,
        "TEST",
    )

    # ------------------------------------------------------------------
    # CLASS WEIGHTS
    # ------------------------------------------------------------------

    print(
        "\nCalculating class-aware training weights..."
    )

    sample_weights = compute_sample_weight(
        class_weight="balanced",
        y=y_train,
    )

    print(
        f"  Weight minimum: "
        f"{sample_weights.min():.6f}"
    )

    print(
        f"  Weight maximum: "
        f"{sample_weights.max():.6f}"
    )

    # ------------------------------------------------------------------
    # MODEL
    # ------------------------------------------------------------------

    print(
        "\nCreating XGBoost multiclass model..."
    )

    model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=len(class_names),
        n_estimators=N_ESTIMATORS,
        learning_rate=LEARNING_RATE,
        max_depth=MAX_DEPTH,
        min_child_weight=MIN_CHILD_WEIGHT,
        subsample=SUBSAMPLE,
        colsample_bytree=COLSAMPLE_BYTREE,
        tree_method="hist",
        eval_metric="mlogloss",
        random_state=RANDOM_STATE,
        n_jobs=-1,
        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
    )

    print(
        "\nTraining configuration:"
    )

    print(
        f"  Estimators           : {N_ESTIMATORS}"
    )
    print(
        f"  Learning rate        : {LEARNING_RATE}"
    )
    print(
        f"  Max depth            : {MAX_DEPTH}"
    )
    print(
        f"  Min child weight     : {MIN_CHILD_WEIGHT}"
    )
    print(
        f"  Subsample            : {SUBSAMPLE}"
    )
    print(
        f"  Column subsampling   : {COLSAMPLE_BYTREE}"
    )
    print(
        f"  Early stopping       : "
        f"{EARLY_STOPPING_ROUNDS}"
    )
    print(
        f"  Tree method          : hist"
    )
    print(
        f"  Number of classes    : "
        f"{len(class_names)}"
    )
    print(
        f"  Number of features   : "
        f"{len(FEATURES)}"
    )

    print(
        "\nStarting training..."
    )

    model.fit(
        X_train,
        y_train,
        sample_weight=sample_weights,
        eval_set=[
            (
                X_train,
                y_train,
            ),
            (
                X_validation,
                y_validation,
            ),
        ],
        verbose=50,
    )

    # ------------------------------------------------------------------
    # PREDICTIONS
    # ------------------------------------------------------------------

    print(
        "\nGenerating validation predictions..."
    )

    validation_probabilities = (
        model.predict_proba(
            X_validation
        )
    )

    validation_predictions = (
        np.argmax(
            validation_probabilities,
            axis=1,
        )
    )

    print(
        "Generating test predictions..."
    )

    test_probabilities = (
        model.predict_proba(
            X_test
        )
    )

    test_predictions = (
        np.argmax(
            test_probabilities,
            axis=1,
        )
    )

    # ------------------------------------------------------------------
    # METRICS
    # ------------------------------------------------------------------

    print(
        "\nCalculating validation metrics..."
    )

    validation_metrics = calculate_metrics(
        y_validation,
        validation_predictions,
        class_names,
    )

    print(
        "\nCalculating test metrics..."
    )

    test_metrics = calculate_metrics(
        y_test,
        test_predictions,
        class_names,
    )

    print("\n" + "=" * 100)
    print("VALIDATION RESULTS")
    print("=" * 100)

    print(
        f"Accuracy          : "
        f"{validation_metrics['accuracy']:.6f}"
    )

    print(
        f"Macro Precision   : "
        f"{validation_metrics['precision_macro']:.6f}"
    )

    print(
        f"Macro Recall      : "
        f"{validation_metrics['recall_macro']:.6f}"
    )

    print(
        f"Macro F1          : "
        f"{validation_metrics['f1_macro']:.6f}"
    )

    print(
        f"Weighted F1       : "
        f"{validation_metrics['f1_weighted']:.6f}"
    )

    print("\n" + "=" * 100)
    print("TEST RESULTS")
    print("=" * 100)

    print(
        f"Accuracy          : "
        f"{test_metrics['accuracy']:.6f}"
    )

    print(
        f"Macro Precision   : "
        f"{test_metrics['precision_macro']:.6f}"
    )

    print(
        f"Macro Recall      : "
        f"{test_metrics['recall_macro']:.6f}"
    )

    print(
        f"Macro F1          : "
        f"{test_metrics['f1_macro']:.6f}"
    )

    print(
        f"Weighted F1       : "
        f"{test_metrics['f1_weighted']:.6f}"
    )

    # ------------------------------------------------------------------
    # ARTIFACTS
    # ------------------------------------------------------------------

    print(
        "\nSaving model artifacts..."
    )

    model.save_model(
        MODEL_FILE
    )

    label_mapping = {
        "classes": class_names,
        "class_to_index": {
            name: int(index)
            for index, name in enumerate(
                class_names
            )
        },
    }

    with open(
        LABEL_ENCODER_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            label_mapping,
            file,
            indent=2,
        )

    feature_schema = {
        "feature_count": len(FEATURES),
        "features": FEATURES,
        "target": TARGET_COLUMN,
        "excluded_columns": [
            "dataset_name",
            "dataset_split",
            "source_file",
            "original_attack_category",
            "label",
            "synthetic",
            "source_ip",
            "destination_ip",
            "source_port",
            "destination_port",
            "protocol",
            "unified_row_id",
            "ml_split",
        ],
    }

    with open(
        FEATURE_SCHEMA_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            feature_schema,
            file,
            indent=2,
        )

    metrics = {
        "validation": validation_metrics,
        "test": test_metrics,
    }

    with open(
        METRICS_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metrics,
            file,
            indent=2,
        )

    save_classification_report(
        y_test,
        test_predictions,
        class_names,
    )

    save_confusion_matrix(
        y_test,
        test_predictions,
        class_names,
    )

    save_feature_importance(
        model
    )

    # ------------------------------------------------------------------
    # TRAINING METADATA
    # ------------------------------------------------------------------

    elapsed = (
        time.time()
        - start_time
    )

    training_metadata = {
        "model": "XGBoost",
        "objective": "multi:softprob",
        "class_count": len(class_names),
        "classes": class_names,
        "feature_count": len(FEATURES),
        "features": FEATURES,
        "random_state": RANDOM_STATE,
        "hyperparameters": {
            "n_estimators": N_ESTIMATORS,
            "learning_rate": LEARNING_RATE,
            "max_depth": MAX_DEPTH,
            "min_child_weight": MIN_CHILD_WEIGHT,
            "subsample": SUBSAMPLE,
            "colsample_bytree": COLSAMPLE_BYTREE,
            "tree_method": "hist",
            "eval_metric": "mlogloss",
            "early_stopping_rounds": (
                EARLY_STOPPING_ROUNDS
            ),
        },
        "training_rows": int(
            len(train_df)
        ),
        "validation_rows": int(
            len(validation_df)
        ),
        "test_rows": int(
            len(test_df)
        ),
        "class_weighting": (
            "balanced sample weights"
        ),
        "best_iteration": (
            int(model.best_iteration)
            if hasattr(model, "best_iteration")
            else None
        ),
        "early_stopping_enabled": True,
        "training_seconds": round(
            elapsed,
            2,
        ),
    }

    with open(
        TRAINING_METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            training_metadata,
            file,
            indent=2,
        )

    # ------------------------------------------------------------------
    # COMPLETE
    # ------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("UNIFIED XGBOOST TRAINING COMPLETE")
    print("=" * 100)

    print(
        f"Model             : {MODEL_FILE}"
    )

    print(
        f"Label mapping     : "
        f"{LABEL_ENCODER_FILE}"
    )

    print(
        f"Feature schema    : "
        f"{FEATURE_SCHEMA_FILE}"
    )

    print(
        f"Metrics            : "
        f"{METRICS_FILE}"
    )

    print(
        f"Classification     : "
        f"{CLASSIFICATION_REPORT_FILE}"
    )

    print(
        f"Confusion matrix   : "
        f"{CONFUSION_MATRIX_FILE}"
    )

    print(
        f"Feature importance : "
        f"{FEATURE_IMPORTANCE_FILE}"
    )

    print(
        f"Training metadata  : "
        f"{TRAINING_METADATA_FILE}"
    )

    print(
        f"\nBest iteration: "
        f"{training_metadata['best_iteration']}"
    )

    print(
        f"Training time: "
        f"{elapsed / 60:.2f} minutes"
    )

    print(
        "\nThe model was trained exclusively "
        "on the 14 ZUKA common features."
    )

    print(
        "No dataset identifiers, IP addresses, "
        "ports, protocol, or synthetic flags "
        "were used as ML features."
    )

    print("=" * 100)


if __name__ == "__main__":
    main()