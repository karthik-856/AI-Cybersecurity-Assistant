from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ZUKA_ROOT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
)

CIC_DIR = ZUKA_ROOT / "common" / "cic_ids2017"
UNSW_DIR = ZUKA_ROOT / "common" / "unsw_nb15"
CUSTOM_DIR = ZUKA_ROOT / "custom_zuka"

OUTPUT_DIR = ZUKA_ROOT / "unified"

OUTPUT_FILE = OUTPUT_DIR / "zuka_unified_flows.csv"
CLASS_FILE = OUTPUT_DIR / "class_distribution.csv"
DATASET_FILE = OUTPUT_DIR / "dataset_distribution.csv"
METADATA_FILE = OUTPUT_DIR / "metadata.json"


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

PROVENANCE_COLUMNS = [
    "dataset_name",
    "dataset_split",
    "source_file",
    "zuka_attack_class",
    "original_attack_category",
    "label",
]

NETWORK_METADATA = [
    "source_ip",
    "destination_ip",
    "source_port",
    "destination_port",
    "protocol",
]

FINAL_COLUMNS = [
    *PROVENANCE_COLUMNS,
    "synthetic",
    *COMMON_FEATURES,
    *NETWORK_METADATA,
]


def load_cic() -> pd.DataFrame:
    files = sorted(
        f
        for f in CIC_DIR.glob("*.csv")
        if f.name != "cic_label_mapping.csv"
    )

    if not files:
        raise FileNotFoundError(
            f"No CIC common-schema files found: {CIC_DIR}"
        )

    frames = []

    for path in files:
        print(f"  CIC: {path.name}")

        df = pd.read_csv(
            path,
            low_memory=False,
        )

        df["dataset_name"] = "CIC-IDS2017"
        df["dataset_split"] = "source_file"
        df["source_file"] = path.name
        df["synthetic"] = False

        frames.append(
            normalize_columns(df)
        )

    return pd.concat(
        frames,
        ignore_index=True,
    )


def load_unsw() -> pd.DataFrame:
    files = sorted(
        UNSW_DIR.glob(
            "UNSW_NB15_*_normalized.csv"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No UNSW common-schema files found: {UNSW_DIR}"
        )

    frames = []

    for path in files:
        print(f"  UNSW: {path.name}")

        df = pd.read_csv(
            path,
            low_memory=False,
        )

        df["dataset_name"] = "UNSW-NB15"

        if "training" in path.name.lower():
            df["dataset_split"] = "train_source"
        elif "testing" in path.name.lower():
            df["dataset_split"] = "test_source"
        else:
            df["dataset_split"] = "source_file"

        df["source_file"] = path.name
        df["synthetic"] = False

        frames.append(
            normalize_columns(df)
        )

    return pd.concat(
        frames,
        ignore_index=True,
    )


def load_custom() -> pd.DataFrame:
    path = CUSTOM_DIR / "custom_zuka_flows.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"Custom ZUKA dataset not found: {path}"
        )

    print(f"  Custom ZUKA: {path.name}")

    df = pd.read_csv(
        path,
        low_memory=False,
    )

    df["dataset_name"] = "Custom-ZUKA"
    df["dataset_split"] = "synthetic"
    df["source_file"] = path.name

    if "synthetic" not in df.columns:
        df["synthetic"] = True
    else:
        df["synthetic"] = (
            df["synthetic"]
            .astype(bool)
        )

    return normalize_columns(df)


def normalize_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    # Required classification columns.
    required = [
        "zuka_attack_class",
        "original_attack_category",
        "label",
    ]

    for column in required:
        if column not in df.columns:
            raise ValueError(
                f"Required column missing: {column}"
            )

    # Metadata columns may legitimately be absent
    # in datasets where the original source did not
    # provide them.
    for column in NETWORK_METADATA:
        if column not in df.columns:
            df[column] = pd.NA

    for feature in COMMON_FEATURES:
        if feature not in df.columns:
            raise ValueError(
                f"Common feature missing: {feature}"
            )

        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce",
        )

    df["zuka_attack_class"] = (
        df["zuka_attack_class"]
        .astype("string")
        .str.strip()
    )

    df["original_attack_category"] = (
        df["original_attack_category"]
        .astype("string")
        .str.strip()
    )

    df["label"] = pd.to_numeric(
        df["label"],
        errors="coerce",
    )

    df["synthetic"] = (
        df["synthetic"]
        .fillna(False)
        .astype(bool)
    )

    return df[FINAL_COLUMNS].copy()


def validate_frame(
    df: pd.DataFrame,
    dataset_name: str,
) -> None:

    print(
        f"\nValidating {dataset_name}..."
    )

    missing = [
        column
        for column in FINAL_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{dataset_name}: missing columns: {missing}"
        )

    feature_nulls = int(
        df[COMMON_FEATURES]
        .isna()
        .sum()
        .sum()
    )

    if feature_nulls:
        raise ValueError(
            f"{dataset_name}: "
            f"{feature_nulls:,} null feature values."
        )

    feature_values = df[
        COMMON_FEATURES
    ].to_numpy()

    if not pd.api.types.is_numeric_dtype(
        df["duration_sec"]
    ):
        raise ValueError(
            f"{dataset_name}: non-numeric features detected."
        )

    if not (
        pd.notna(feature_values).all()
    ):
        raise ValueError(
            f"{dataset_name}: null feature values detected."
        )

    if not (
        abs(feature_values) != float("inf")
    ).all():
        raise ValueError(
            f"{dataset_name}: infinite feature values detected."
        )

    negative = (
        df[COMMON_FEATURES]
        .lt(0)
        .sum()
        .sum()
    )

    if int(negative) != 0:
        raise ValueError(
            f"{dataset_name}: "
            f"{int(negative):,} negative feature values."
        )

    invalid_labels = set(
        df["zuka_attack_class"]
        .dropna()
        .unique()
    ) - {
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

    if invalid_labels:
        raise ValueError(
            f"{dataset_name}: unknown ZUKA classes: "
            f"{sorted(invalid_labels)}"
        )

    print(
        f"  Rows: {len(df):,}"
    )

    print(
        f"  Feature nulls: {feature_nulls:,}"
    )

    print(
        f"  Negative features: {int(negative):,}"
    )

    print("  PASS")


def build_class_distribution(
    df: pd.DataFrame,
) -> pd.DataFrame:

    result = (
        df.groupby(
            [
                "dataset_name",
                "zuka_attack_class",
            ],
            dropna=False,
        )
        .size()
        .reset_index(
            name="row_count"
        )
    )

    totals = (
        df.groupby(
            "zuka_attack_class"
        )
        .size()
        .reset_index(
            name="total_count"
        )
    )

    result = result.merge(
        totals,
        on="zuka_attack_class",
        how="left",
    )

    result["dataset_percentage"] = (
        result["row_count"]
        / result.groupby("dataset_name")[
            "row_count"
        ].transform("sum")
        * 100
    )

    result["overall_percentage"] = (
        result["total_count"]
        / len(df)
        * 100
    )

    return result.sort_values(
        [
            "zuka_attack_class",
            "dataset_name",
        ]
    )


def build_dataset_distribution(
    df: pd.DataFrame,
) -> pd.DataFrame:

    result = (
        df.groupby(
            "dataset_name"
        )
        .agg(
            rows=(
                "zuka_attack_class",
                "size",
            ),
            unique_classes=(
                "zuka_attack_class",
                "nunique",
            ),
            synthetic_rows=(
                "synthetic",
                "sum",
            ),
        )
        .reset_index()
    )

    result["percentage"] = (
        result["rows"]
        / len(df)
        * 100
    )

    return result


def check_duplicates(
    df: pd.DataFrame,
) -> tuple[int, int]:

    # Exact duplicate detection across the
    # normalized data content.
    duplicate_mask = df.duplicated(
        subset=[
            "dataset_name",
            "source_file",
            "zuka_attack_class",
            *COMMON_FEATURES,
            *NETWORK_METADATA,
        ],
        keep=False,
    )

    duplicate_rows = int(
        duplicate_mask.sum()
    )

    duplicate_groups = int(
        df.loc[
            duplicate_mask,
            [
                "dataset_name",
                "source_file",
                "zuka_attack_class",
                *COMMON_FEATURES,
                *NETWORK_METADATA,
            ],
        ]
        .drop_duplicates()
        .shape[0]
    )

    return duplicate_rows, duplicate_groups


def save_metadata(
    df: pd.DataFrame,
    duplicate_rows: int,
    duplicate_groups: int,
) -> None:

    metadata = {
        "dataset_name": "ZUKA Unified Dataset",
        "dataset_type": "multi-source",
        "source_datasets": [
            "CIC-IDS2017",
            "UNSW-NB15",
            "Custom-ZUKA",
        ],
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "common_feature_count": len(
            COMMON_FEATURES
        ),
        "common_features": COMMON_FEATURES,
        "network_metadata": NETWORK_METADATA,
        "provenance_columns": PROVENANCE_COLUMNS,
        "synthetic_rows": int(
            df["synthetic"].sum()
        ),
        "real_benchmark_rows": int(
            (~df["synthetic"]).sum()
        ),
        "duplicate_rows_detected": duplicate_rows,
        "duplicate_groups_detected": duplicate_groups,
        "classes": sorted(
            df["zuka_attack_class"]
            .unique()
            .tolist()
        ),
        "class_distribution": {
            key: int(value)
            for key, value in (
                df["zuka_attack_class"]
                .value_counts()
                .to_dict()
                .items()
            )
        },
        "important_note": (
            "Custom-ZUKA rows are synthetic and are explicitly "
            "marked synthetic=True. CIC-IDS2017 and UNSW-NB15 "
            "rows are benchmark-source records."
        ),
        "integration_policy": (
            "Datasets are normalized into the ZUKA common schema. "
            "Unavailable network metadata is retained as null "
            "rather than fabricated."
        ),
    }

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


def main() -> None:

    print("=" * 100)
    print("ZUKA - UNIFIED DATASET BUILDER")
    print("=" * 100)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nLoading datasets...")

    cic = load_cic()
    unsw = load_unsw()
    custom = load_custom()

    validate_frame(
        cic,
        "CIC-IDS2017",
    )

    validate_frame(
        unsw,
        "UNSW-NB15",
    )

    validate_frame(
        custom,
        "Custom-ZUKA",
    )

    print("\nCombining datasets...")

    unified = pd.concat(
        [
            cic,
            unsw,
            custom,
        ],
        ignore_index=True,
    )

    # Stable row identifier for the unified
    # dataset. This is NOT a network packet ID.
    unified.insert(
        0,
        "unified_row_id",
        range(
            1,
            len(unified) + 1,
        ),
    )

    # Final deterministic ordering.
    unified = unified.sort_values(
        [
            "dataset_name",
            "source_file",
            "zuka_attack_class",
        ],
        kind="stable",
    ).reset_index(
        drop=True
    )

    # Reassign stable IDs after sorting.
    unified["unified_row_id"] = range(
        1,
        len(unified) + 1,
    )

    duplicate_rows, duplicate_groups = (
        check_duplicates(unified)
    )

    print("\nDuplicate analysis:")
    print(
        f"  Duplicate rows detected : "
        f"{duplicate_rows:,}"
    )
    print(
        f"  Duplicate groups        : "
        f"{duplicate_groups:,}"
    )

    print("\nFinal unified dimensions:")
    print(
        f"  Rows    : {len(unified):,}"
    )
    print(
        f"  Columns : {len(unified.columns)}"
    )

    # Save the main dataset.
    unified.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    # Distribution reports.
    class_distribution = (
        build_class_distribution(
            unified
        )
    )

    dataset_distribution = (
        build_dataset_distribution(
            unified
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

    save_metadata(
        unified,
        duplicate_rows,
        duplicate_groups,
    )

    print("\n" + "=" * 100)
    print("ZUKA UNIFIED DATASET COMPLETE")
    print("=" * 100)

    print(
        f"Unified dataset : {OUTPUT_FILE}"
    )

    print(
        f"Class report    : {CLASS_FILE}"
    )

    print(
        f"Dataset report  : {DATASET_FILE}"
    )

    print(
        f"Metadata        : {METADATA_FILE}"
    )

    print(
        f"Total rows      : {len(unified):,}"
    )

    print(
        f"Total classes   : "
        f"{unified['zuka_attack_class'].nunique()}"
    )

    print(
        f"Synthetic rows  : "
        f"{int(unified['synthetic'].sum()):,}"
    )

    print(
        f"Benchmark rows  : "
        f"{int((~unified['synthetic']).sum()):,}"
    )

    print("\nDataset distribution:")
    print(
        dataset_distribution.to_string(
            index=False
        )
    )

    print("\nOverall class distribution:")
    print(
        unified[
            "zuka_attack_class"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("=" * 100)


if __name__ == "__main__":
    main()