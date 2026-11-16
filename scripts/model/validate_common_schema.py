from __future__ import annotations

from pathlib import Path

import pandas as pd

from zuka_common_schema import (
    CIC_MAPPING,
    COMMON_FEATURES,
    UNSW_MAPPING,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CIC_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "cic_ids2017"
)

UNSW_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "unsw_nb15"
)


def main() -> None:
    print("=" * 100)
    print("ZUKA COMMON SCHEMA VALIDATION")
    print("=" * 100)

    cic_files = sorted(
        f
        for f in CIC_DIR.glob("*.csv")
        if f.name != "cic_label_mapping.csv"
    )

    unsw_files = sorted(
        UNSW_DIR.glob("UNSW_NB15_*_normalized.csv")
    )

    if not cic_files:
        raise FileNotFoundError("No normalized CIC files found.")

    if not unsw_files:
        raise FileNotFoundError("No normalized UNSW files found.")

    cic_columns = set(
        pd.read_csv(cic_files[0], nrows=0).columns
    )

    unsw_columns = set(
        pd.read_csv(unsw_files[0], nrows=0).columns
    )

    print("\nCommon ZUKA features:")
    print("-" * 100)

    errors = []

    for feature in COMMON_FEATURES:
        name = feature.name

        cic = CIC_MAPPING[name]
        unsw = UNSW_MAPPING[name]

        cic_source = cic["source"]
        unsw_source = unsw["source"]

        cic_ok = (
            cic_source is None
            or cic_source in cic_columns
        )

        unsw_ok = (
            unsw_source is None
            or unsw_source in unsw_columns
        )

        status = "OK" if cic_ok and unsw_ok else "ERROR"

        print(
            f"{status:5s} "
            f"{name:25s} "
            f"CIC={str(cic_source):35s} "
            f"UNSW={str(unsw_source):20s}"
        )

        if not cic_ok:
            errors.append(
                f"CIC missing source column: {cic_source}"
            )

        if not unsw_ok:
            errors.append(
                f"UNSW missing source column: {unsw_source}"
            )

    print("\n" + "-" * 100)
    print("TRANSFORMATIONS")
    print("-" * 100)

    for feature in COMMON_FEATURES:
        name = feature.name

        print(f"\n{name}")

        print(
            f"  CIC : {CIC_MAPPING[name]['transform']}"
        )

        print(
            f"  UNSW: {UNSW_MAPPING[name]['transform']}"
        )

    print("\n" + "-" * 100)
    print("LABEL COLUMNS")
    print("-" * 100)

    required_labels = [
        "zuka_attack_class",
        "original_attack_category",
        "label",
        "dataset_name",
        "dataset_split",
    ]

    for column in required_labels:
        cic_ok = column in cic_columns
        unsw_ok = column in unsw_columns

        print(
            f"{'OK' if cic_ok else 'MISSING':7s} "
            f"CIC  {column}"
        )

        print(
            f"{'OK' if unsw_ok else 'MISSING':7s} "
            f"UNSW {column}"
        )

    print("\n" + "-" * 100)
    print("RESULT")
    print("-" * 100)

    if errors:
        print("SCHEMA VALIDATION FAILED")

        for error in errors:
            print(f"  - {error}")

        raise SystemExit(1)

    print(
        f"All {len(COMMON_FEATURES)} common features "
        "have valid source mappings or explicit derivations."
    )

    print(
        "\nNo data has been modified."
    )

    print("=" * 100)


if __name__ == "__main__":
    main()