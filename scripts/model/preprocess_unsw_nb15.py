from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# ZUKA - UNSW-NB15 preprocessing
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "UNSW-NB15"
TRAIN_TEST_DIR = RAW_DIR / "Training and Testing Sets"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "unsw_nb15"
)

TRAIN_FILE = TRAIN_TEST_DIR / "UNSW_NB15_training-set.csv"
TEST_FILE = TRAIN_TEST_DIR / "UNSW_NB15_testing-set.csv"


# ------------------------------------------------------------
# Original UNSW -> ZUKA attack taxonomy
# ------------------------------------------------------------

ATTACK_MAPPING = {
    "Normal": "BENIGN",
    "Generic": "OTHER_ATTACK",
    "Exploits": "EXPLOIT",
    "Fuzzers": "FUZZING",
    "DoS": "DOS",
    "Reconnaissance": "RECONNAISSANCE",
    "Analysis": "OTHER_ATTACK",
    "Backdoor": "BACKDOOR",
    "Shellcode": "MALWARE",
    "Worms": "MALWARE",
}


# ------------------------------------------------------------
# Columns that are categorical in the UNSW train/test files.
# Everything else is handled as numeric where appropriate.
# ------------------------------------------------------------

CATEGORICAL_COLUMNS = {
    "proto",
    "service",
    "state",
}


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def clean_column_name(name: str) -> str:
    """Normalize a column name without changing its meaning."""
    name = str(name).replace("\ufeff", "")
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_").lower()


def normalize_attack_category(value) -> str:
    """Normalize UNSW attack category text."""
    if pd.isna(value):
        return "UNKNOWN"

    value = str(value).replace("\ufeff", "").strip()

    # Normalize common whitespace variations.
    value = re.sub(r"\s+", " ", value)

    return value


def load_dataset(path: Path, dataset_split: str) -> pd.DataFrame:
    print(f"\nLoading {dataset_split}:")
    print(f"  {path}")

    if not path.exists():
        raise FileNotFoundError(f"UNSW file not found: {path}")

    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        low_memory=False,
    )

    print(f"  Rows loaded: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")

    # Clean column names.
    df.columns = [clean_column_name(c) for c in df.columns]

    required = {
        "id",
        "attack_cat",
        "label",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{dataset_split} is missing required columns: {sorted(missing)}"
        )

    df["dataset_name"] = "UNSW-NB15"
    df["dataset_split"] = dataset_split

    # Preserve original attack category.
    df["original_attack_category"] = (
        df["attack_cat"]
        .map(normalize_attack_category)
    )

    # Binary label as integer.
    df["label"] = pd.to_numeric(
        df["label"],
        errors="coerce",
    )

    if df["label"].isna().any():
        bad = int(df["label"].isna().sum())
        raise ValueError(
            f"{dataset_split}: {bad} rows have invalid binary labels."
        )

    df["label"] = df["label"].astype("int8")

    invalid_labels = sorted(set(df["label"].unique()) - {0, 1})

    if invalid_labels:
        raise ValueError(
            f"{dataset_split}: unexpected label values: {invalid_labels}"
        )

    # Normalized ZUKA taxonomy.
    df["zuka_attack_class"] = (
        df["original_attack_category"]
        .map(ATTACK_MAPPING)
        .fillna("OTHER_ATTACK")
    )

    # Explicit validation.
    expected_categories = set(ATTACK_MAPPING.keys())
    observed_categories = set(
        df["original_attack_category"].dropna().unique()
    )

    unknown_categories = observed_categories - expected_categories

    if unknown_categories:
        raise ValueError(
            "Unexpected UNSW attack categories detected: "
            f"{sorted(unknown_categories)}"
        )

    # Numeric conversion.
    for column in df.columns:
        if column in CATEGORICAL_COLUMNS:
            continue

        if column in {
            "attack_cat",
            "original_attack_category",
            "zuka_attack_class",
            "dataset_name",
            "dataset_split",
        }:
            continue

        converted = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        # Keep the conversion if it is genuinely numeric.
        if converted.notna().mean() >= 0.95:
            df[column] = converted

    # Remove rows with non-finite numeric values.
    numeric_columns = df.select_dtypes(
        include=[np.number]
    ).columns.tolist()

    if numeric_columns:
        numeric_values = df[numeric_columns].to_numpy(dtype=float)

        finite_mask = np.isfinite(numeric_values).all(axis=1)

        invalid_numeric_rows = int((~finite_mask).sum())

        if invalid_numeric_rows:
            print(
                f"  Removing invalid numeric rows: "
                f"{invalid_numeric_rows:,}"
            )
            df = df.loc[finite_mask].copy()

    # Normalize categorical values.
    for column in CATEGORICAL_COLUMNS:
        if column in df.columns:
            df[column] = (
                df[column]
                .astype("string")
                .fillna("UNKNOWN")
                .str.strip()
            )

    # Preserve attack_cat as the original dataset terminology.
    df["attack_cat"] = (
        df["attack_cat"]
        .astype("string")
        .fillna("Unknown")
        .str.strip()
    )

    # Ensure ID is numeric where possible.
    if "id" in df.columns:
        df["id"] = pd.to_numeric(
            df["id"],
            errors="coerce",
        )

    # Final integrity checks.
    if df["zuka_attack_class"].isna().any():
        raise ValueError(
            f"{dataset_split}: null ZUKA attack classes remain."
        )

    if df["label"].isna().any():
        raise ValueError(
            f"{dataset_split}: null labels remain."
        )

    print(f"  Rows after validation: {len(df):,}")

    return df


def save_dataset(df: pd.DataFrame, filename: str) -> None:
    path = OUTPUT_DIR / filename

    print(f"\nSaving:")
    print(f"  {path}")

    df.to_csv(
        path,
        index=False,
        encoding="utf-8",
    )

    print(f"  Saved rows: {len(df):,}")
    print(f"  Saved columns: {len(df.columns)}")


def build_mapping_file() -> None:
    rows = []

    for original, normalized in ATTACK_MAPPING.items():
        rows.append(
            {
                "original_attack_category": original,
                "zuka_attack_class": normalized,
            }
        )

    mapping_df = pd.DataFrame(rows)

    path = OUTPUT_DIR / "attack_mapping.csv"

    mapping_df.to_csv(
        path,
        index=False,
        encoding="utf-8",
    )


def build_metadata(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> None:

    combined = pd.concat(
        [train_df, test_df],
        ignore_index=True,
    )

    class_counts = (
        combined["zuka_attack_class"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    original_category_counts = (
        combined["original_attack_category"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    label_counts = (
        combined["label"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    numeric_columns = combined.select_dtypes(
        include=[np.number]
    ).columns.tolist()

    metadata = {
        "dataset": "UNSW-NB15",
        "source_files": [
            TRAIN_FILE.name,
            TEST_FILE.name,
        ],
        "training_rows": int(len(train_df)),
        "testing_rows": int(len(test_df)),
        "combined_rows": int(len(combined)),
        "columns": int(len(combined.columns)),
        "numeric_columns": int(len(numeric_columns)),
        "categorical_columns": sorted(
            [
                column
                for column in CATEGORICAL_COLUMNS
                if column in combined.columns
            ]
        ),
        "binary_label_counts": {
            str(k): int(v)
            for k, v in label_counts.items()
        },
        "original_attack_categories": {
            str(k): int(v)
            for k, v in original_category_counts.items()
        },
        "zuka_attack_classes": {
            str(k): int(v)
            for k, v in class_counts.items()
        },
        "attack_mapping": ATTACK_MAPPING,
        "preprocessing_steps": [
            "Column name normalization",
            "UTF-8 BOM removal",
            "UNSW attack category normalization",
            "Original attack category preservation",
            "ZUKA attack taxonomy mapping",
            "Binary label validation",
            "Numeric conversion where applicable",
            "Non-finite numeric value removal",
            "Categorical value normalization",
            "Raw source files left untouched",
        ],
        "network_metadata_note": (
            "The labeled UNSW-NB15 training/testing files do not expose "
            "source IP and destination IP columns. ZUKA does not fabricate "
            "network identity metadata. Raw 49-column UNSW files remain "
            "available separately for future validated metadata handling."
        ),
    }

    path = OUTPUT_DIR / "metadata.json"

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metadata,
            f,
            indent=2,
        )

    print(f"\nMetadata saved:")
    print(f"  {path}")


def print_summary(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> None:

    combined = pd.concat(
        [train_df, test_df],
        ignore_index=True,
    )

    print("\n")
    print("=" * 90)
    print("ZUKA UNSW-NB15 PREPROCESSING SUMMARY")
    print("=" * 90)

    print(f"Training rows : {len(train_df):,}")
    print(f"Testing rows  : {len(test_df):,}")
    print(f"Combined rows : {len(combined):,}")
    print(f"Columns       : {len(combined.columns):,}")

    print("\nOriginal UNSW categories:")
    print(
        combined["original_attack_category"]
        .value_counts()
        .to_string()
    )

    print("\nZUKA attack classes:")
    print(
        combined["zuka_attack_class"]
        .value_counts()
        .to_string()
    )

    print("\nBinary labels:")
    print(
        combined["label"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nRequired columns present:")
    required = [
        "id",
        "attack_cat",
        "label",
        "original_attack_category",
        "zuka_attack_class",
        "dataset_name",
        "dataset_split",
    ]

    for column in required:
        print(
            f"  {'OK' if column in combined.columns else 'MISSING'} "
            f"{column}"
        )

    print("\nZUKA preprocessing completed successfully.")
    print("=" * 90)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main() -> None:
    print("=" * 90)
    print("ZUKA - UNSW-NB15 PREPROCESSING")
    print("=" * 90)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    train_df = load_dataset(
        TRAIN_FILE,
        "training",
    )

    test_df = load_dataset(
        TEST_FILE,
        "testing",
    )

    save_dataset(
        train_df,
        "UNSW_NB15_training_normalized.csv",
    )

    save_dataset(
        test_df,
        "UNSW_NB15_testing_normalized.csv",
    )

    build_mapping_file()

    build_metadata(
        train_df,
        test_df,
    )

    print_summary(
        train_df,
        test_df,
    )


if __name__ == "__main__":
    main()