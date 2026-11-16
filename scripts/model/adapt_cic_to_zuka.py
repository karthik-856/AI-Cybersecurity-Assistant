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
    / "cic_ids2017"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "common"
    / "cic_ids2017"
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

# Features that cannot physically be negative.
NON_NEGATIVE_FEATURES = COMMON_COLUMNS.copy()


def numeric(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def adapt_file(path: Path) -> tuple[pd.DataFrame, int]:
    print(f"\nProcessing: {path.name}")

    df = pd.read_csv(
        path,
        low_memory=False,
    )

    required = [
        "Flow Duration",
        "Total Fwd Packets",
        "Total Backward Packets",
        "Total Length of Fwd Packets",
        "Total Length of Bwd Packets",
        "Flow Packets/s",
        "Fwd Packets/s",
        "Bwd Packets/s",
        "Fwd Packet Length Mean",
        "Bwd Packet Length Mean",
        "Fwd IAT Mean",
        "Bwd IAT Mean",
        "zuka_attack_class",
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

    # --------------------------------------------------------
    # Unit normalization
    #
    # CIC duration and IAT fields are in microseconds.
    # ZUKA common schema stores them in seconds.
    # --------------------------------------------------------

    duration_sec = (
        numeric(df, "Flow Duration")
        / 1_000_000.0
    )

    src_packets = numeric(
        df,
        "Total Fwd Packets",
    )

    dst_packets = numeric(
        df,
        "Total Backward Packets",
    )

    src_bytes = numeric(
        df,
        "Total Length of Fwd Packets",
    )

    dst_bytes = numeric(
        df,
        "Total Length of Bwd Packets",
    )

    result = pd.DataFrame(index=df.index)

    result["duration_sec"] = duration_sec

    result["src_packets"] = src_packets
    result["dst_packets"] = dst_packets

    result["src_bytes"] = src_bytes
    result["dst_bytes"] = dst_bytes

    result["flow_packet_rate"] = numeric(
        df,
        "Flow Packets/s",
    )

    result["src_packet_rate"] = numeric(
        df,
        "Fwd Packets/s",
    )

    result["dst_packet_rate"] = numeric(
        df,
        "Bwd Packets/s",
    )

    # Derive directional byte rates in bytes/sec.
    result["src_byte_rate"] = safe_divide(
        src_bytes,
        duration_sec,
    )

    result["dst_byte_rate"] = safe_divide(
        dst_bytes,
        duration_sec,
    )

    result["src_packet_size_mean"] = numeric(
        df,
        "Fwd Packet Length Mean",
    )

    result["dst_packet_size_mean"] = numeric(
        df,
        "Bwd Packet Length Mean",
    )

    result["src_iat_mean_sec"] = (
        numeric(df, "Fwd IAT Mean")
        / 1_000_000.0
    )

    result["dst_iat_mean_sec"] = (
        numeric(df, "Bwd IAT Mean")
        / 1_000_000.0
    )

    # --------------------------------------------------------
    # Labels / provenance
    # --------------------------------------------------------

    result["zuka_attack_class"] = (
        df["zuka_attack_class"]
        .astype("string")
        .str.strip()
    )

    if "original_label" in df.columns:
        result["original_attack_category"] = (
            df["original_label"]
            .astype("string")
            .str.strip()
        )
    else:
        result["original_attack_category"] = (
            result["zuka_attack_class"]
        )

    result["label"] = (
        result["zuka_attack_class"]
        .ne("BENIGN")
        .astype("int8")
    )

    result["dataset_name"] = "CIC-IDS2017"
    result["dataset_split"] = "source_file"
    result["source_file"] = path.name

    # CIC processed files do not expose these fields.
    # Do NOT fabricate them.
    result["source_ip"] = pd.NA
    result["destination_ip"] = pd.NA
    result["source_port"] = pd.NA
    result["destination_port"] = pd.NA
    result["protocol"] = pd.NA

    # --------------------------------------------------------
    # Quality validation
    # --------------------------------------------------------

    values = result[
        COMMON_COLUMNS
    ].to_numpy(dtype=float)

    finite_mask = np.isfinite(values).all(axis=1)

    negative_mask = (
        result[NON_NEGATIVE_FEATURES]
        .lt(0)
        .any(axis=1)
        .to_numpy()
    )

    valid_mask = (
        finite_mask
        & ~negative_mask
    )

    invalid_rows = int((~valid_mask).sum())

    if invalid_rows:
        negative_rows = int(negative_mask.sum())
        nonfinite_rows = int((~finite_mask).sum())

        print(
            f"  Invalid common-schema rows: {invalid_rows:,}"
        )
        print(
            f"    Negative-domain rows : {negative_rows:,}"
        )
        print(
            f"    Non-finite rows       : {nonfinite_rows:,}"
        )

    result = result.loc[valid_mask].copy()

    # --------------------------------------------------------
    # Final column order
    # --------------------------------------------------------

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

    return result, invalid_rows


def main() -> None:
    print("=" * 100)
    print("ZUKA - CIC-IDS2017 -> COMMON SCHEMA")
    print("=" * 100)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = sorted(
        f
        for f in INPUT_DIR.glob("*.csv")
        if f.name != "cic_label_mapping.csv"
    )

    if not files:
        raise FileNotFoundError(
            f"No normalized CIC files found in {INPUT_DIR}"
        )

    total_input = 0
    total_output = 0
    total_rejected = 0

    for path in files:
        # Read source row count separately so the report is exact.
        source_rows = len(
            pd.read_csv(
                path,
                usecols=["zuka_attack_class"],
            )
        )

        result, rejected = adapt_file(path)

        output = OUTPUT_DIR / path.name

        result.to_csv(
            output,
            index=False,
            encoding="utf-8",
        )

        print(
            f"  Input rows    : {source_rows:,}"
        )
        print(
            f"  Rejected rows : {rejected:,}"
        )
        print(
            f"  Output rows   : {len(result):,}"
        )
        print(
            f"  Output        : {output}"
        )

        total_input += source_rows
        total_output += len(result)
        total_rejected += rejected

    print("\n" + "=" * 100)
    print("CIC COMMON-SCHEMA ADAPTATION COMPLETE")
    print("=" * 100)

    print(
        f"Input rows    : {total_input:,}"
    )

    print(
        f"Rejected rows : {total_rejected:,}"
    )

    print(
        f"Output rows   : {total_output:,}"
    )

    print(
        f"Output folder : {OUTPUT_DIR}"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()