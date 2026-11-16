from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "unified"
    / "zuka_unified_flows.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "splits"
)

TRAIN_FILE = OUTPUT_DIR / "train.csv"
VALIDATION_FILE = OUTPUT_DIR / "validation.csv"
TEST_FILE = OUTPUT_DIR / "test.csv"
METADATA_FILE = OUTPUT_DIR / "split_metadata.json"
CLASS_FILE = OUTPUT_DIR / "split_class_distribution.csv"
DATASET_FILE = OUTPUT_DIR / "split_dataset_distribution.csv"


RANDOM_STATE = 20260907

TRAIN_SIZE = 0.80
VALIDATION_SIZE = 0.10
TEST_SIZE = 0.10


TARGET_COLUMN = "zuka_attack_class"

COMMON_FEATURES = [
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

NETWORK_METADATA = [
    "source_ip",
    "destination_ip",
    "source_port",
    "destination_port",
    "protocol",
]


REQUIRED_COLUMNS = [
    "unified_row_id",
    "dataset_name",
    "dataset_split",
    "source_file",
    "zuka_attack_class",
    "original_attack_category",
    "label",
    "synthetic",
    *COMMON_FEATURES,
    *NETWORK_METADATA,
]


def normalize_for_hash(value) -> str:
    """
    Convert a value into a deterministic representation.

    This is used only for grouping identical flow signatures.
    It does not modify the actual dataset.
    """
    if pd.isna(value):
        return "<NULL>"

    if isinstance(value, float):
        return format(value, ".12g")

    return str(value).strip()


def create_flow_signature(df: pd.DataFrame) -> pd.Series:
    """
    Create a deterministic flow signature.

    IMPORTANT:
    dataset_name and source_file are deliberately NOT included.

    This means an equivalent flow appearing in CIC, UNSW, or
    Custom-ZUKA is kept in the same split.

    zuka_attack_class is also deliberately NOT included so that
    identical feature patterns with different labels cannot leak
    across train/test.
    """

    signature_columns = [
        *COMMON_FEATURES,
        *NETWORK_METADATA,
    ]

    normalized = df[
        signature_columns
    ].copy()

    for column in signature_columns:
        normalized[column] = normalized[column].map(
            normalize_for_hash
        )

    # Hash the complete normalized flow signature.
    return pd.util.hash_pandas_object(
        normalized,
        index=False,
    ).astype("uint64")


def validate_input(df: pd.DataFrame) -> None:

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Unified dataset is missing required columns:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing
            )
        )

    if df.empty:
        raise ValueError(
            "Unified dataset is empty."
        )

    null_features = int(
        df[COMMON_FEATURES]
        .isna()
        .sum()
        .sum()
    )

    if null_features:
        raise ValueError(
            f"Found {null_features:,} null values "
            "inside ML features."
        )

    numeric = df[
        COMMON_FEATURES
    ].apply(
        pd.to_numeric,
        errors="coerce",
    )

    if numeric.isna().any().any():
        raise ValueError(
            "One or more ML features contain "
            "non-numeric values."
        )

    values = numeric.to_numpy()

    if not np.isfinite(values).all():
        raise ValueError(
            "Infinite ML feature values detected."
        )

    if (values < 0).any():
        raise ValueError(
            "Negative ML feature values detected."
        )

    classes = set(
        df[TARGET_COLUMN]
        .dropna()
        .unique()
    )

    expected_classes = {
        "BENIGN",
        "BRUTE_FORCE",
        "DDOS",
        "DOS",
        "EXPLOIT",
        "INFILTRATION",
        "MALWARE",
        "PORT_SCAN",
        "WEB_ATTACK",
        "BACKDOOR",
        "FUZZING",
        "RECONNAISSANCE",
        "OTHER_ATTACK",
    }

    unknown = classes - expected_classes

    if unknown:
        raise ValueError(
            "Unknown ZUKA classes detected: "
            + ", ".join(
                sorted(unknown)
            )
        )


def build_groups(
    df: pd.DataFrame,
) -> pd.DataFrame:

    print("\nCreating leakage-prevention signatures...")

    df["_flow_signature"] = create_flow_signature(
        df
    )

    unique_groups = (
        df["_flow_signature"]
        .nunique()
    )

    print(
        f"  Total rows          : {len(df):,}"
    )

    print(
        f"  Unique flow groups  : {unique_groups:,}"
    )

    duplicate_rows = (
        len(df) - unique_groups
    )

    print(
        f"  Rows in repeated groups: "
        f"{duplicate_rows:,}"
    )

    # Each signature is assigned one dominant class.
    #
    # In the rare case that exactly the same feature signature
    # has multiple labels, we use the most frequent label as
    # the group's stratification label while keeping ALL rows
    # together in the same split.
    group_labels = (
        df.groupby(
            "_flow_signature",
            sort=False,
        )[TARGET_COLUMN]
        .agg(
            lambda x: x.value_counts().index[0]
        )
        .rename("group_class")
    )

    group_sizes = (
        df.groupby(
            "_flow_signature",
            sort=False,
        )
        .size()
        .rename("group_size")
    )

    groups = pd.concat(
        [
            group_labels,
            group_sizes,
        ],
        axis=1,
    ).reset_index()

    conflicting_groups = (
        df.groupby(
            "_flow_signature",
            sort=False,
        )[TARGET_COLUMN]
        .nunique()
        .gt(1)
        .sum()
    )

    print(
        f"  Conflicting-label groups: "
        f"{int(conflicting_groups):,}"
    )

    groups["group_class"] = (
        groups["group_class"]
        .astype(str)
    )

    return groups


def stratified_group_split(
    groups: pd.DataFrame,
) -> tuple[set[int], set[int], set[int]]:

    print("\nCreating stratified group split...")

    group_ids = groups[
        "_flow_signature"
    ].to_numpy()

    group_labels = groups[
        "group_class"
    ].to_numpy()

    # First: 80% train, 20% temporary.
    train_groups, temporary_groups = (
        train_test_split(
            group_ids,
            test_size=(
                VALIDATION_SIZE + TEST_SIZE
            ),
            random_state=RANDOM_STATE,
            stratify=group_labels,
        )
    )

    temporary_label_map = (
        groups.set_index(
            "_flow_signature"
        )["group_class"]
    )

    temporary_labels = np.array(
        [
            temporary_label_map.loc[group_id]
            for group_id in temporary_groups
        ]
    )

    # Split temporary 50/50 -> validation/test.
    validation_groups, test_groups = (
        train_test_split(
            temporary_groups,
            test_size=0.5,
            random_state=RANDOM_STATE,
            stratify=temporary_labels,
        )
    )

    return (
        set(train_groups),
        set(validation_groups),
        set(test_groups),
    )


def assign_splits(
    df: pd.DataFrame,
    train_groups: set[int],
    validation_groups: set[int],
    test_groups: set[int],
) -> pd.DataFrame:

    print("\nAssigning rows to splits...")

    signatures = df[
        "_flow_signature"
    ]

    split_array = np.empty(
        len(df),
        dtype=object,
    )

    for index, signature in enumerate(
        signatures
    ):
        if signature in train_groups:
            split_array[index] = "train"

        elif signature in validation_groups:
            split_array[index] = "validation"

        elif signature in test_groups:
            split_array[index] = "test"

        else:
            raise RuntimeError(
                "A row could not be assigned to a split."
            )

    df["ml_split"] = split_array

    return df


def report_class_distribution(
    df: pd.DataFrame,
) -> pd.DataFrame:

    result = (
        df.groupby(
            [
                "ml_split",
                TARGET_COLUMN,
            ],
            sort=True,
        )
        .size()
        .reset_index(
            name="row_count"
        )
    )

    totals = (
        df.groupby(
            "ml_split"
        )
        .size()
        .rename("split_total")
        .reset_index()
    )

    result = result.merge(
        totals,
        on="ml_split",
        how="left",
    )

    result["percentage"] = (
        result["row_count"]
        / result["split_total"]
        * 100
    )

    return result


def report_dataset_distribution(
    df: pd.DataFrame,
) -> pd.DataFrame:

    result = (
        df.groupby(
            [
                "ml_split",
                "dataset_name",
                "synthetic",
            ],
            sort=True,
        )
        .size()
        .reset_index(
            name="row_count"
        )
    )

    totals = (
        df.groupby(
            "ml_split"
        )
        .size()
        .rename("split_total")
        .reset_index()
    )

    result = result.merge(
        totals,
        on="ml_split",
        how="left",
    )

    result["percentage"] = (
        result["row_count"]
        / result["split_total"]
        * 100
    )

    return result


def verify_no_group_leakage(
    df: pd.DataFrame,
) -> None:

    print("\nChecking for group leakage...")

    leakage = (
        df.groupby(
            "_flow_signature"
        )["ml_split"]
        .nunique()
    )

    leaking_groups = int(
        (leakage > 1).sum()
    )

    if leaking_groups:
        raise RuntimeError(
            f"LEAKAGE DETECTED: "
            f"{leaking_groups:,} flow groups "
            "appear in multiple splits."
        )

    print(
        "  Group leakage: 0"
    )
    print(
        "  PASS"
    )


def build_metadata(
    df: pd.DataFrame,
    groups: pd.DataFrame,
) -> dict:

    split_counts = (
        df["ml_split"]
        .value_counts()
        .to_dict()
    )

    synthetic_counts = (
        df.groupby(
            "ml_split"
        )["synthetic"]
        .sum()
        .to_dict()
    )

    return {
        "dataset": "ZUKA Unified Dataset",
        "input_file": str(
            INPUT_FILE
        ),
        "output_directory": str(
            OUTPUT_DIR
        ),
        "random_state": RANDOM_STATE,
        "split_strategy": {
            "train": TRAIN_SIZE,
            "validation": VALIDATION_SIZE,
            "test": TEST_SIZE,
        },
        "method": (
            "Stratified group split using deterministic "
            "flow signatures."
        ),
        "leakage_policy": (
            "Rows with identical normalized flow signatures "
            "are assigned to exactly one ML split. "
            "Dataset name and attack class are excluded "
            "from the signature."
        ),
        "total_rows": int(len(df)),
        "unique_flow_groups": int(
            len(groups)
        ),
        "duplicate_rows": int(
            len(df) - len(groups)
        ),
        "split_counts": {
            key: int(value)
            for key, value in split_counts.items()
        },
        "synthetic_counts": {
            key: int(value)
            for key, value in synthetic_counts.items()
        },
        "classes": sorted(
            df[TARGET_COLUMN]
            .unique()
            .tolist()
        ),
        "common_features": COMMON_FEATURES,
        "network_metadata": NETWORK_METADATA,
        "source_datasets": sorted(
            df["dataset_name"]
            .unique()
            .tolist()
        ),
        "important_note": (
            "The split operation does not delete duplicate "
            "records. It keeps identical flow signatures "
            "together to prevent train/test leakage."
        ),
    }


def main() -> None:

    print("=" * 100)
    print("ZUKA - LEAKAGE-SAFE ML DATASET SPLITTER")
    print("=" * 100)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Unified dataset not found:\n{INPUT_FILE}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nLoading unified dataset...")
    print(
        f"  {INPUT_FILE}"
    )

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    print(
        f"  Loaded rows: {len(df):,}"
    )

    validate_input(df)

    print(
        "\nInput validation: PASS"
    )

    groups = build_groups(
        df
    )

    (
        train_groups,
        validation_groups,
        test_groups,
    ) = stratified_group_split(
        groups
    )

    print("\nGroup allocation:")
    print(
        f"  Train groups      : "
        f"{len(train_groups):,}"
    )
    print(
        f"  Validation groups : "
        f"{len(validation_groups):,}"
    )
    print(
        f"  Test groups       : "
        f"{len(test_groups):,}"
    )

    df = assign_splits(
        df,
        train_groups,
        validation_groups,
        test_groups,
    )

    verify_no_group_leakage(
        df
    )

    train_df = (
        df[df["ml_split"] == "train"]
        .copy()
    )

    validation_df = (
        df[df["ml_split"] == "validation"]
        .copy()
    )

    test_df = (
        df[df["ml_split"] == "test"]
        .copy()
    )

    # Remove internal leakage-control column.
    # It is not an ML feature and is not needed
    # by downstream model training.
    for frame in [
        train_df,
        validation_df,
        test_df,
    ]:
        frame.drop(
            columns=["_flow_signature"],
            inplace=True,
        )

    # Keep ml_split as provenance.
    final_column_order = [
        "unified_row_id",
        "ml_split",
        "dataset_name",
        "dataset_split",
        "source_file",
        "zuka_attack_class",
        "original_attack_category",
        "label",
        "synthetic",
        *COMMON_FEATURES,
        *NETWORK_METADATA,
    ]

    train_df = train_df[
        final_column_order
    ]

    validation_df = validation_df[
        final_column_order
    ]

    test_df = test_df[
        final_column_order
    ]

    print("\nFinal split sizes:")

    for name, frame in [
        ("TRAIN", train_df),
        ("VALIDATION", validation_df),
        ("TEST", test_df),
    ]:
        percentage = (
            len(frame)
            / len(df)
            * 100
        )

        print(
            f"  {name:<12} "
            f"{len(frame):>12,} "
            f"({percentage:6.2f}%)"
        )

    # Save datasets.
    print("\nWriting split files...")

    train_df.to_csv(
        TRAIN_FILE,
        index=False,
        encoding="utf-8",
    )

    validation_df.to_csv(
        VALIDATION_FILE,
        index=False,
        encoding="utf-8",
    )

    test_df.to_csv(
        TEST_FILE,
        index=False,
        encoding="utf-8",
    )

    class_distribution = (
        report_class_distribution(
            pd.concat(
                [
                    train_df,
                    validation_df,
                    test_df,
                ],
                ignore_index=True,
            )
        )
    )

    dataset_distribution = (
        report_dataset_distribution(
            pd.concat(
                [
                    train_df,
                    validation_df,
                    test_df,
                ],
                ignore_index=True,
            )
        )
    )

    class_distribution.to_csv(
        CLASS_FILE,
        index=False,
    )

    dataset_distribution.to_csv(
        DATASET_FILE,
        index=False,
    )

    metadata = build_metadata(
        df,
        groups,
    )

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
        )

    print("\n" + "=" * 100)
    print("LEAKAGE-SAFE SPLIT COMPLETE")
    print("=" * 100)

    print(
        f"Train      : {TRAIN_FILE}"
    )

    print(
        f"Validation : {VALIDATION_FILE}"
    )

    print(
        f"Test       : {TEST_FILE}"
    )

    print(
        f"Classes    : {CLASS_FILE}"
    )

    print(
        f"Datasets   : {DATASET_FILE}"
    )

    print(
        f"Metadata   : {METADATA_FILE}"
    )

    print("\nClass distribution:")
    print(
        class_distribution.to_string(
            index=False
        )
    )

    print("\nDataset distribution:")
    print(
        dataset_distribution.to_string(
            index=False
        )
    )

    print("\nNo model training was performed.")
    print(
        "The datasets are now ready for the unified "
        "XGBoost training module."
    )

    print("=" * 100)


if __name__ == "__main__":
    main()