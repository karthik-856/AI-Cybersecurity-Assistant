from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "unsw_nb15"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "common"
    / "unsw_nb15"
)

COMMON_COLUMNS = [
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


def numeric(
    df: pd.DataFrame,
    column: str,
) -> pd.Series:
    return pd.to_numeric(
        df[column],
        errors="coerce",
    )


def safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def adapt_file(path: Path) -> pd.DataFrame:
    print(f"\nProcessing: {path.name}")

    df = pd.read_csv(
        path,
        low_memory=False,
    )

    required = [
        "id",
        "dur",
        "proto",
        "spkts",
        "dpkts",
        "sbytes",
        "dbytes",
        "rate",
        "sload",
        "dload",
        "smean",
        "dmean",
        "sinpkt",
        "dinpkt",
        "attack_cat",
        "original_attack_category",
        "label",
        "zuka_attack_class",
        "dataset_name",
        "dataset_split",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{path.name}: missing required columns: {missing}"
        )

    result = pd.DataFrame(index=df.index)

    duration_sec = numeric(df, "dur")

    src_packets = numeric(df, "spkts")
    dst_packets = numeric(df, "dpkts")

    src_bytes = numeric(df, "sbytes")
    dst_bytes = numeric(df, "dbytes")

    result["duration_sec"] = duration_sec

    result["src_packets"] = src_packets
    result["dst_packets"] = dst_packets

    result["src_bytes"] = src_bytes
    result["dst_bytes"] = dst_bytes

    result["flow_packet_rate"] = numeric(
        df,
        "rate",
    )

    # Derived directional packet rates.
    result["src_packet_rate"] = np.where(
    duration_sec > 0,
    src_packets / duration_sec,
    0.0,
)

    result["dst_packet_rate"] = np.where(
        duration_sec > 0,
        dst_packets / duration_sec,
        0.0,
    )

    # UNSW sload/dload are already directional loads.
    result["src_byte_rate"] = (
    numeric(df, "sload") / 8.0
)
    result["dst_byte_rate"] = (
    numeric(df, "dload") / 8.0
)

    result["src_packet_size_mean"] = numeric(
        df,
        "smean",
    )

    result["dst_packet_size_mean"] = numeric(
        df,
        "dmean",
    )

    # UNSW sinpkt/dinpkt are already in milliseconds
    # in the standard UNSW-NB15 representation.
    result["src_iat_mean_sec"] = (
        numeric(df, "sinpkt") / 1000.0
    )

    result["dst_iat_mean_sec"] = (
        numeric(df, "dinpkt") / 1000.0
    )

    # --------------------------------------------------------
    # Labels
    # --------------------------------------------------------

    result["zuka_attack_class"] = (
        df["zuka_attack_class"]
        .astype("string")
        .str.strip()
    )

    result["original_attack_category"] = (
        df["original_attack_category"]
        .astype("string")
        .str.strip()
    )

    result["label"] = pd.to_numeric(
        df["label"],
        errors="coerce",
    ).astype("int8")

    result["dataset_name"] = "UNSW-NB15"

    result["dataset_split"] = (
        df["dataset_split"]
        .astype("string")
        .str.strip()
    )

    result["source_file"] = path.name

    # --------------------------------------------------------
    # Network metadata actually available in UNSW.
    # The labeled train/test files do not contain source IP,
    # destination IP, source port, or destination port.
    #
    # Therefore we intentionally leave these null rather than
    # trying to join the GT/raw files without a validated key.
    # --------------------------------------------------------

    result["source_ip"] = pd.NA
    result["destination_ip"] = pd.NA
    result["source_port"] = pd.NA
    result["destination_port"] = pd.NA

    # Protocol IS explicitly available in the labeled files.
    result["protocol"] = (
        df["proto"]
        .astype("string")
        .str.strip()
    )

    return result


def main() -> None:
    print("=" * 100)
    print("ZUKA - UNSW-NB15 -> COMMON SCHEMA")
    print("=" * 100)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = sorted(
        INPUT_DIR.glob(
            "UNSW_NB15_*_normalized.csv"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No normalized UNSW files found in {INPUT_DIR}"
        )

    total_rows = 0

    for path in files:
        result = adapt_file(path)

        values = result[
            COMMON_COLUMNS
        ].to_numpy(dtype=float)

        finite_mask = np.isfinite(values).all(axis=1)

        removed = int((~finite_mask).sum())

        if removed:
            print(
                f"  Removing non-finite common-schema rows: "
                f"{removed:,}"
            )

        result = result.loc[finite_mask].copy()

        columns = [
            "dataset_name",
            "dataset_split",
            "source_file",
            "zuka_attack_class",
            "original_attack_category",
            "label",
            *COMMON_COLUMNS,
            "source_ip",
            "destination_ip",
            "source_port",
            "destination_port",
            "protocol",
        ]

        result = result[columns]

        output = OUTPUT_DIR / path.name

        result.to_csv(
            output,
            index=False,
            encoding="utf-8",
        )

        print(
            f"  Input rows : {len(result) + removed:,}"
        )
        print(
            f"  Output rows: {len(result):,}"
        )
        print(
            f"  Output     : {output}"
        )

        total_rows += len(result)

    print("\n" + "=" * 100)
    print("UNSW COMMON-SCHEMA ADAPTATION COMPLETE")
    print("=" * 100)
    print(f"Files processed: {len(files)}")
    print(f"Total rows     : {total_rows:,}")
    print(f"Output folder  : {OUTPUT_DIR}")


if __name__ == "__main__":
    main()