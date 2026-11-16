from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

COMMON_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "common"
)

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


def load_dataset_files():
    cic_files = sorted(
        (COMMON_DIR / "cic_ids2017").glob("*.csv")
    )

    unsw_files = sorted(
        (COMMON_DIR / "unsw_nb15").glob("*.csv")
    )

    return cic_files, unsw_files


def audit_file(path: Path) -> dict:
    df = pd.read_csv(
        path,
        usecols=[
            "dataset_name",
            "zuka_attack_class",
            "label",
            *FEATURES,
        ],
        low_memory=False,
    )

    result = {
        "file": path.name,
        "dataset": str(df["dataset_name"].iloc[0]),
        "rows": len(df),
        "columns": len(df.columns),
    }

    numeric = df[FEATURES].apply(
        pd.to_numeric,
        errors="coerce",
    )

    result["null_values"] = int(
        numeric.isna().sum().sum()
    )

    result["infinite_values"] = int(
        np.isinf(
            numeric.to_numpy(
                dtype=float
            )
        ).sum()
    )

    result["negative_values"] = int(
        (numeric < 0).sum().sum()
    )

    result["zero_duration"] = int(
        (numeric["duration_sec"] == 0).sum()
    )

    result["zero_packets"] = int(
        (
            (numeric["src_packets"] == 0)
            & (numeric["dst_packets"] == 0)
        ).sum()
    )

    return result


def main():
    print("=" * 100)
    print("ZUKA COMMON DATASET QUALITY AUDIT")
    print("=" * 100)

    cic_files, unsw_files = load_dataset_files()

    files = cic_files + unsw_files

    if not files:
        raise FileNotFoundError(
            f"No common-schema files found in {COMMON_DIR}"
        )

    results = []

    for path in files:
        result = audit_file(path)
        results.append(result)

        print(
            f"\n{result['dataset']}: {result['file']}"
        )
        print(
            f"  Rows              : {result['rows']:,}"
        )
        print(
            f"  Null values       : {result['null_values']:,}"
        )
        print(
            f"  Infinite values   : {result['infinite_values']:,}"
        )
        print(
            f"  Negative values   : {result['negative_values']:,}"
        )
        print(
            f"  Zero duration     : {result['zero_duration']:,}"
        )
        print(
            f"  Zero packets      : {result['zero_packets']:,}"
        )

    # --------------------------------------------------------
    # Combined feature statistics
    # --------------------------------------------------------

    print("\n" + "-" * 100)
    print("COMBINED FEATURE STATISTICS")
    print("-" * 100)

    combined_parts = []

    for path in files:
        combined_parts.append(
            pd.read_csv(
                path,
                usecols=[
                    "dataset_name",
                    "zuka_attack_class",
                    *FEATURES,
                ],
                low_memory=False,
            )
        )

    combined = pd.concat(
        combined_parts,
        ignore_index=True,
    )

    for feature in FEATURES:
        values = pd.to_numeric(
            combined[feature],
            errors="coerce",
        )

        finite = values[
            np.isfinite(values)
        ]

        if len(finite) == 0:
            print(
                f"{feature:25s} NO VALID VALUES"
            )
            continue

        print(
            f"{feature:25s} "
            f"min={finite.min():.6g} "
            f"median={finite.median():.6g} "
            f"max={finite.max():.6g}"
        )

    # --------------------------------------------------------
    # Dataset-specific class distribution
    # --------------------------------------------------------

    print("\n" + "-" * 100)
    print("CLASS DISTRIBUTION BY DATASET")
    print("-" * 100)

    print(
        combined.groupby(
            [
                "dataset_name",
                "zuka_attack_class",
            ]
        ).size().to_string()
    )

    # --------------------------------------------------------
    # Feature availability
    # --------------------------------------------------------

    print("\n" + "-" * 100)
    print("FEATURE AVAILABILITY")
    print("-" * 100)

    for feature in FEATURES:
        values = pd.to_numeric(
            combined[feature],
            errors="coerce",
        )

        valid = np.isfinite(
            values.to_numpy(dtype=float)
        ).sum()

        print(
            f"{feature:25s} "
            f"{valid:,}/{len(combined):,} "
            f"({valid / len(combined) * 100:.2f}%)"
        )

    print("\n" + "-" * 100)
    print("FINAL RESULT")
    print("-" * 100)

    total_nulls = sum(
        r["null_values"]
        for r in results
    )

    total_infinite = sum(
        r["infinite_values"]
        for r in results
    )

    total_negative = sum(
        r["negative_values"]
        for r in results
    )

    if total_nulls:
        print(
            f"WARNING: {total_nulls:,} null feature values found."
        )

    if total_infinite:
        print(
            f"WARNING: {total_infinite:,} infinite feature values found."
        )

    if total_negative:
        print(
            f"WARNING: {total_negative:,} negative feature values found."
        )

    if not total_nulls and not total_infinite and not total_negative:
        print(
            "PASS: No null, infinite, or negative common-feature values."
        )

    print(
        f"\nTotal common-schema rows: {len(combined):,}"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()