from __future__ import annotations

import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "CIC-IDS2017"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "zuka_unified" / "cic_ids2017"

METADATA_PATH = OUTPUT_DIR / "metadata.json"


# =============================================================================
# EXPECTED CIC-IDS2017 SCHEMA
# =============================================================================

EXPECTED_FEATURE_COUNT = 78
LABEL_COLUMN = "Label"


# =============================================================================
# ZUKA NORMALIZED ATTACK TAXONOMY
# =============================================================================

LABEL_MAP = {
    "BENIGN": "BENIGN",

    "DDoS": "DDOS",
    "DDOS": "DDOS",

    "PortScan": "PORT_SCAN",
    "PORTSCAN": "PORT_SCAN",

    "Bot": "MALWARE",

    "Infiltration": "INFILTRATION",

    "Web Attack - Brute Force": "BRUTE_FORCE",
    "Web Attack – Brute Force": "BRUTE_FORCE",

    "Web Attack - XSS": "WEB_ATTACK",
    "Web Attack – XSS": "WEB_ATTACK",

    "Web Attack - Sql Injection": "WEB_ATTACK",
    "Web Attack – Sql Injection": "WEB_ATTACK",

    "FTP-Patator": "BRUTE_FORCE",
    "SSH-Patator": "BRUTE_FORCE",

    "DoS Hulk": "DOS",
    "DoS GoldenEye": "DOS",
    "DoS slowloris": "DOS",
    "DoS Slowhttptest": "DOS",

    "Heartbleed": "EXPLOIT",
}


# =============================================================================
# UTILITIES
# =============================================================================

def clean_column_name(value: object) -> str:
    """
    Clean whitespace/BOM characters without deleting duplicate columns.
    """
    value = str(value)

    # Remove BOM
    value = value.replace("\ufeff", "")

    # Normalize surrounding whitespace
    value = value.strip()

    # Collapse repeated internal whitespace
    value = re.sub(r"\s+", " ", value)

    return value


def make_unique_columns(columns: list[object]) -> list[str]:
    """
    Make column names deterministic and unique.

    IMPORTANT:
    Duplicate CIC column names are preserved as separate positional
    features.

    Example:
        Fwd Header Length
        Fwd Header Length

    becomes:

        Fwd Header Length
        Fwd Header Length.1

    This is intentional because CIC-IDS2017 contains 78 ML feature
    columns plus the Label column.
    """
    result: list[str] = []
    seen: dict[str, int] = {}

    for raw_column in columns:
        base = clean_column_name(raw_column)

        if base not in seen:
            seen[base] = 0
            result.append(base)
            continue

        seen[base] += 1
        unique_name = f"{base}.{seen[base]}"

        # Extra safety if a naturally occurring column already has
        # that generated name.
        while unique_name in seen:
            seen[base] += 1
            unique_name = f"{base}.{seen[base]}"

        seen[unique_name] = 0
        result.append(unique_name)

    return result


def normalize_label(value: object) -> str:
    """
    Normalize CIC label text while preserving the original label separately.
    """
    if pd.isna(value):
        return ""

    label = str(value)

    # Handle common encoding replacement artifacts.
    label = label.replace("\ufffd", "-")

    # Normalize whitespace.
    label = re.sub(r"\s+", " ", label.strip())

    return label


def normalize_zuka_label(label: str) -> str:
    """
    Convert original CIC label to the common ZUKA attack taxonomy.
    """
    if label in LABEL_MAP:
        return LABEL_MAP[label]

    # Defensive normalization for encoding/spacing variations.
    compact = label.replace("–", "-")
    compact = re.sub(r"\s+", " ", compact).strip()

    if compact in LABEL_MAP:
        return LABEL_MAP[compact]

    # Explicit fallback.
    return "OTHER_ATTACK"


def convert_features_to_numeric(
    df: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    """
    Convert all ML features to numeric values.

    Invalid numeric values become NaN and are subsequently removed.
    """
    for column in feature_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Replace +/- infinity with NaN.
    df[feature_columns] = df[feature_columns].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    return df


def validate_feature_schema(
    feature_columns: list[str],
    filename: str,
) -> None:
    """
    Ensure every CIC file produces exactly 78 ML features.

    The Label column must NOT be part of feature_columns.
    """

    # Label must NOT be included in the ML feature list.
    if LABEL_COLUMN in feature_columns:
        raise RuntimeError(
            f"{filename}: label column '{LABEL_COLUMN}' was incorrectly "
            f"included in ML features."
        )

    # CIC-IDS2017 must contain exactly 78 ML features.
    if len(feature_columns) != EXPECTED_FEATURE_COUNT:
        raise RuntimeError(
            f"{filename}: expected exactly "
            f"{EXPECTED_FEATURE_COUNT} ML features after column "
            f"normalization, found {len(feature_columns)}.\n\n"
            f"Features found:\n"
            + "\n".join(
                f"{i + 1:02d}. {column}"
                for i, column in enumerate(feature_columns)
            )
        )

# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 90)
    print("ZUKA CIC-IDS2017 NORMALIZATION")
    print("=" * 90)
    print(f"Input : {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")

    if not INPUT_DIR.exists():
        raise FileNotFoundError(
            f"CIC input directory does not exist: {INPUT_DIR}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_files = sorted(INPUT_DIR.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {INPUT_DIR}"
        )

    print(f"Files : {len(csv_files)}")
    print()

    # -------------------------------------------------------------------------
    # Global statistics
    # -------------------------------------------------------------------------

    total_input_rows = 0
    total_output_rows = 0
    total_removed_rows = 0

    all_label_counts: dict[str, int] = {}
    all_zuka_counts: dict[str, int] = {}

    canonical_features: list[str] | None = None

    processed_files: list[dict] = []

    global_start = time.time()

    # -------------------------------------------------------------------------
    # Process each CIC CSV
    # -------------------------------------------------------------------------

    for index, csv_path in enumerate(csv_files, start=1):

        file_start = time.time()

        print("-" * 90)
        print(
            f"[{index}/{len(csv_files)}] Processing: "
            f"{csv_path.name}"
        )

        # ---------------------------------------------------------------------
        # Read file
        # ---------------------------------------------------------------------

        df = pd.read_csv(
            csv_path,
            encoding="utf-8-sig",
            low_memory=False,
        )

        input_rows = len(df)

        print(f"Input rows: {input_rows:,}")

        total_input_rows += input_rows

        # ---------------------------------------------------------------------
        # Normalize column names
        # ---------------------------------------------------------------------

        df.columns = make_unique_columns(
            list(df.columns)
        )

        # ---------------------------------------------------------------------
        # Label validation
        # ---------------------------------------------------------------------

        if LABEL_COLUMN not in df.columns:

            # Defensive case where the label has an unexpected case.
            possible_labels = [
                column
                for column in df.columns
                if clean_column_name(column).lower() == "label"
            ]

            if len(possible_labels) == 1:
                df = df.rename(
                    columns={
                        possible_labels[0]: LABEL_COLUMN
                    }
                )
            else:
                raise RuntimeError(
                    f"{csv_path.name}: could not locate Label column."
                )

        # ---------------------------------------------------------------------
        # IMPORTANT:
        # Preserve ALL 78 feature columns.
        #
        # Do NOT drop Fwd Header Length.1.
        # ---------------------------------------------------------------------

        feature_columns = [
            column
            for column in df.columns
            if column != LABEL_COLUMN
        ]

        validate_feature_schema(
            feature_columns,
            csv_path.name,
        )

        # ---------------------------------------------------------------------
        # Establish canonical feature order
        # ---------------------------------------------------------------------

        if canonical_features is None:

            canonical_features = feature_columns.copy()

            print()
            print("Canonical 78-feature schema established.")

            for feature_number, feature in enumerate(
                canonical_features,
                start=1,
            ):
                print(
                    f"  {feature_number:02d}. {feature}"
                )

            print()

        else:

            if feature_columns != canonical_features:

                # More useful error than a generic mismatch.
                differences = []

                max_len = max(
                    len(feature_columns),
                    len(canonical_features),
                )

                for position in range(max_len):

                    expected = (
                        canonical_features[position]
                        if position < len(canonical_features)
                        else "<missing>"
                    )

                    actual = (
                        feature_columns[position]
                        if position < len(feature_columns)
                        else "<missing>"
                    )

                    if expected != actual:
                        differences.append(
                            {
                                "position": position + 1,
                                "expected": expected,
                                "actual": actual,
                            }
                        )

                raise RuntimeError(
                    f"{csv_path.name}: feature order/schema does not "
                    f"match the canonical CIC-IDS2017 schema.\n"
                    f"Differences:\n"
                    f"{json.dumps(differences, indent=2)}"
                )

        # ---------------------------------------------------------------------
        # Preserve original label
        # ---------------------------------------------------------------------

        df["original_label"] = (
            df[LABEL_COLUMN]
            .map(normalize_label)
        )

        # ---------------------------------------------------------------------
        # Create normalized ZUKA attack class
        # ---------------------------------------------------------------------

        df["zuka_attack_class"] = (
            df["original_label"]
            .map(normalize_zuka_label)
        )

        # ---------------------------------------------------------------------
        # Convert 78 ML features to numeric
        # ---------------------------------------------------------------------

        df = convert_features_to_numeric(
            df,
            canonical_features,
        )

        # ---------------------------------------------------------------------
        # Remove invalid rows
        # ---------------------------------------------------------------------

        valid_mask = (
            df[canonical_features]
            .notna()
            .all(axis=1)
        )

        removed_rows = int((~valid_mask).sum())

        df = df.loc[valid_mask].copy()

        # ---------------------------------------------------------------------
        # Remove exact duplicate rows within the file.
        #
        # Do not remove based on only the duplicate header name.
        # ---------------------------------------------------------------------

       # -------------------------------------------------------------------------
# Do NOT remove duplicate flow observations at normalization time.
#
# Identical feature vectors can represent legitimate repeated network
# activity, including repeated attack flows. Dataset-quality analysis and
# any optional deduplication will be handled separately during training
# preparation.
# -------------------------------------------------------------------------

        duplicate_rows = 0  

        # ---------------------------------------------------------------------
        # Final column order
        # ---------------------------------------------------------------------

        output_columns = (
            canonical_features
            + [
                LABEL_COLUMN,
                "original_label",
                "zuka_attack_class",
            ]
        )

        df = df[output_columns]

        # ---------------------------------------------------------------------
        # Final validation
        # ---------------------------------------------------------------------

        if len(canonical_features) != 78:
            raise RuntimeError(
                f"Internal schema error: "
                f"{len(canonical_features)} features."
            )

        if len(df.columns) != 81:
            raise RuntimeError(
                f"{csv_path.name}: expected 81 output columns "
                f"(78 features + Label + original_label + "
                f"zuka_attack_class), found {len(df.columns)}."
            )

        # ---------------------------------------------------------------------
        # Save normalized file
        # ---------------------------------------------------------------------

        output_path = OUTPUT_DIR / csv_path.name

        df.to_csv(
            output_path,
            index=False,
        )

        output_rows = len(df)

        total_output_rows += output_rows
        total_removed_rows += removed_rows + duplicate_rows

        # ---------------------------------------------------------------------
        # Statistics
        # ---------------------------------------------------------------------

        original_counts = (
            df["original_label"]
            .value_counts()
            .to_dict()
        )

        zuka_counts = (
            df["zuka_attack_class"]
            .value_counts()
            .to_dict()
        )

        for label, count in original_counts.items():
            all_label_counts[label] = (
                all_label_counts.get(label, 0)
                + int(count)
            )

        for label, count in zuka_counts.items():
            all_zuka_counts[label] = (
                all_zuka_counts.get(label, 0)
                + int(count)
            )

        elapsed = time.time() - file_start

        processed_files.append(
            {
                "file": csv_path.name,
                "input_rows": input_rows,
                "output_rows": output_rows,
                "removed_invalid_rows": removed_rows,
                "removed_duplicate_rows": duplicate_rows,
                "features": len(canonical_features),
                "output_columns": len(df.columns),
                "seconds": round(elapsed, 2),
            }
        )

        print(f"Output rows: {output_rows:,}")
        print(f"Invalid rows removed: {removed_rows:,}")
        print(f"Duplicate rows removed: {duplicate_rows:,}")
        print(f"Features: {len(canonical_features)}")
        print(f"Output columns: {len(df.columns)}")
        print(f"Saved: {output_path}")
        print(f"Time: {elapsed:.2f} seconds")

    # =========================================================================
    # METADATA
    # =========================================================================

    total_seconds = time.time() - global_start

    metadata = {
        "dataset": "CIC-IDS2017",
        "source_directory": str(INPUT_DIR),
        "output_directory": str(OUTPUT_DIR),

        "raw_files": len(csv_files),

        "raw_rows": total_input_rows,
        "normalized_rows": total_output_rows,
        "removed_rows": total_removed_rows,

        "features": EXPECTED_FEATURE_COUNT,

        "output_columns": (
            EXPECTED_FEATURE_COUNT
            + 3
        ),

        "label_column": LABEL_COLUMN,

        "additional_columns": [
            "original_label",
            "zuka_attack_class",
        ],

        "duplicate_header_handling": {
            "preserve_duplicate_feature_positions": True,
            "example": [
                "Fwd Header Length",
                "Fwd Header Length.1",
            ],
            "dropped_duplicate_feature": False,
        },

        "zuka_taxonomy": sorted(
            set(all_zuka_counts.keys())
        ),

        "original_label_counts": dict(
            sorted(
                all_label_counts.items(),
                key=lambda item: item[0],
            )
        ),

        "zuka_attack_class_counts": dict(
            sorted(
                all_zuka_counts.items(),
                key=lambda item: item[0],
            )
        ),

        "files": processed_files,

        "processing_seconds": round(
            total_seconds,
            2,
        ),
    }

    with open(
        METADATA_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================

    print()
    print("=" * 90)
    print("CIC-IDS2017 NORMALIZATION COMPLETE")
    print("=" * 90)

    print(
        f"Raw rows       : {total_input_rows:,}"
    )

    print(
        f"Normalized rows: {total_output_rows:,}"
    )

    print(
        f"Removed rows   : {total_removed_rows:,}"
    )

    print(
        f"ML features    : {EXPECTED_FEATURE_COUNT}"
    )

    print(
        f"Output columns : {EXPECTED_FEATURE_COUNT + 3}"
    )

    print()
    print("ZUKA attack classes:")

    for label, count in sorted(
        all_zuka_counts.items()
    ):
        print(
            f"  {label:<20} {count:,}"
        )

    print()
    print(
        f"Metadata: {METADATA_PATH}"
    )

    print(
        f"Time: {total_seconds:.2f} seconds"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()