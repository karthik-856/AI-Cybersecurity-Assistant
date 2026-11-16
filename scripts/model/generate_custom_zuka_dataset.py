from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# ZUKA CUSTOM SYNTHETIC DATASET GENERATOR
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "zuka_unified"
    / "custom_zuka"
)

OUTPUT_FILE = OUTPUT_DIR / "custom_zuka_flows.csv"
METADATA_FILE = OUTPUT_DIR / "metadata.json"

SEED = 20260907

BENIGN_ROWS = 30_000
ATTACK_ROWS_PER_CLASS = 7_500

ATTACK_CLASSES = [
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
]

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


# ============================================================
# RANDOM HELPERS
# ============================================================

rng = np.random.default_rng(SEED)
random.seed(SEED)


def clipped_normal(
    mean: float,
    std: float,
    size: int,
    minimum: float = 0.0,
    maximum: float | None = None,
) -> np.ndarray:
    values = rng.normal(mean, std, size)
    values = np.maximum(values, minimum)

    if maximum is not None:
        values = np.minimum(values, maximum)

    return values


def lognormal(
    mean: float,
    sigma: float,
    size: int,
    minimum: float = 0.0,
    maximum: float | None = None,
) -> np.ndarray:
    values = rng.lognormal(mean, sigma, size)
    values = np.maximum(values, minimum)

    if maximum is not None:
        values = np.minimum(values, maximum)

    return values


def integer_log_normal(
    mean: float,
    sigma: float,
    size: int,
    minimum: int = 1,
    maximum: int | None = None,
) -> np.ndarray:
    values = np.rint(
        rng.lognormal(mean, sigma, size)
    ).astype(np.int64)

    values = np.maximum(values, minimum)

    if maximum is not None:
        values = np.minimum(values, maximum)

    return values


def make_ips(
    count: int,
    private_network: str = "10",
) -> tuple[np.ndarray, np.ndarray]:

    src_second = rng.integers(1, 255, count)
    src_third = rng.integers(0, 255, count)
    src_fourth = rng.integers(1, 255, count)

    dst_second = rng.integers(1, 255, count)
    dst_third = rng.integers(0, 255, count)
    dst_fourth = rng.integers(1, 255, count)

    src = np.array(
        [
            f"{private_network}.{a}.{b}.{c}"
            for a, b, c in zip(
                src_second,
                src_third,
                src_fourth,
            )
        ],
        dtype=object,
    )

    dst = np.array(
        [
            f"192.168.{a}.{b}"
            for a, b in zip(
                dst_second % 255,
                dst_fourth,
            )
        ],
        dtype=object,
    )

    return src, dst


def make_ports(
    count: int,
    destination_low: int = 1,
    destination_high: int = 65535,
) -> tuple[np.ndarray, np.ndarray]:

    src_ports = rng.integers(
        1024,
        65535,
        count,
    )

    dst_ports = rng.integers(
        destination_low,
        destination_high + 1,
        count,
    )

    return src_ports, dst_ports


# ============================================================
# FLOW CONSTRUCTION
# ============================================================

def build_flow_features(
    duration: np.ndarray,
    src_packets: np.ndarray,
    dst_packets: np.ndarray,
    src_packet_size: np.ndarray,
    dst_packet_size: np.ndarray,
    src_iat: np.ndarray,
    dst_iat: np.ndarray,
) -> dict[str, np.ndarray]:

    duration = np.maximum(duration, 0.000001)

    src_packets = np.maximum(
        np.rint(src_packets).astype(np.int64),
        1,
    )

    dst_packets = np.maximum(
        np.rint(dst_packets).astype(np.int64),
        0,
    )

    src_packet_size = np.maximum(
        src_packet_size,
        0,
    )

    dst_packet_size = np.maximum(
        dst_packet_size,
        0,
    )

    src_bytes = np.rint(
        src_packets * src_packet_size
    ).astype(np.int64)

    dst_bytes = np.rint(
        dst_packets * dst_packet_size
    ).astype(np.int64)

    flow_packets = (
        src_packets + dst_packets
    )

    flow_packet_rate = (
        flow_packets / duration
    )

    src_packet_rate = (
        src_packets / duration
    )

    dst_packet_rate = (
        dst_packets / duration
    )

    src_byte_rate = (
        src_bytes / duration
    )

    dst_byte_rate = (
        dst_bytes / duration
    )

    return {
        "duration_sec": duration,
        "src_packets": src_packets,
        "dst_packets": dst_packets,
        "src_bytes": src_bytes,
        "dst_bytes": dst_bytes,
        "flow_packet_rate": flow_packet_rate,
        "src_packet_rate": src_packet_rate,
        "dst_packet_rate": dst_packet_rate,
        "src_byte_rate": src_byte_rate,
        "dst_byte_rate": dst_byte_rate,
        "src_packet_size_mean": src_packet_size,
        "dst_packet_size_mean": dst_packet_size,
        "src_iat_mean_sec": np.maximum(
            src_iat,
            0,
        ),
        "dst_iat_mean_sec": np.maximum(
            dst_iat,
            0,
        ),
    }


# ============================================================
# SCENARIO GENERATORS
# ============================================================

def generate_benign(count: int) -> dict:
    duration = lognormal(
        np.log(0.08),
        1.15,
        count,
        0.00001,
        120,
    )

    src_packets = integer_log_normal(
        np.log(4),
        0.9,
        count,
        1,
        5000,
    )

    dst_packets = integer_log_normal(
        np.log(4),
        0.95,
        count,
        0,
        5000,
    )

    src_size = clipped_normal(
        550,
        180,
        count,
        40,
        1500,
    )

    dst_size = clipped_normal(
        650,
        220,
        count,
        40,
        1500,
    )

    src_iat = duration / np.maximum(
        src_packets,
        1,
    )

    dst_iat = duration / np.maximum(
        dst_packets,
        1,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        src_iat,
        dst_iat,
    )


def generate_brute_force(count: int) -> dict:
    duration = lognormal(
        np.log(0.8),
        1.0,
        count,
        0.02,
        30,
    )

    src_packets = integer_log_normal(
        np.log(8),
        0.55,
        count,
        2,
        200,
    )

    dst_packets = integer_log_normal(
        np.log(7),
        0.55,
        count,
        1,
        200,
    )

    src_size = clipped_normal(
        420,
        100,
        count,
        40,
        1200,
    )

    dst_size = clipped_normal(
        500,
        130,
        count,
        40,
        1500,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / np.maximum(dst_packets, 1),
    )


def generate_ddos(count: int) -> dict:
    duration = lognormal(
        np.log(0.015),
        0.8,
        count,
        0.0001,
        5,
    )

    src_packets = integer_log_normal(
        np.log(45),
        1.0,
        count,
        5,
        10000,
    )

    dst_packets = integer_log_normal(
        np.log(5),
        0.9,
        count,
        0,
        1000,
    )

    src_size = clipped_normal(
        220,
        90,
        count,
        40,
        900,
    )

    dst_size = clipped_normal(
        100,
        50,
        count,
        40,
        600,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / np.maximum(dst_packets, 1),
    )


def generate_dos(count: int) -> dict:
    duration = lognormal(
        np.log(0.04),
        0.9,
        count,
        0.0001,
        20,
    )

    src_packets = integer_log_normal(
        np.log(30),
        0.9,
        count,
        2,
        10000,
    )

    dst_packets = integer_log_normal(
        np.log(8),
        0.8,
        count,
        0,
        3000,
    )

    src_size = clipped_normal(
        180,
        80,
        count,
        40,
        1000,
    )

    dst_size = clipped_normal(
        300,
        120,
        count,
        40,
        1500,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / np.maximum(dst_packets, 1),
    )


def generate_exploit(count: int) -> dict:
    duration = lognormal(
        np.log(0.25),
        1.0,
        count,
        0.001,
        20,
    )

    src_packets = integer_log_normal(
        np.log(15),
        0.8,
        count,
        2,
        1000,
    )

    dst_packets = integer_log_normal(
        np.log(20),
        0.8,
        count,
        1,
        2000,
    )

    src_size = clipped_normal(
        700,
        250,
        count,
        40,
        1800,
    )

    dst_size = clipped_normal(
        900,
        300,
        count,
        40,
        2500,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / dst_packets,
    )


def generate_infiltration(count: int) -> dict:
    duration = lognormal(
        np.log(8),
        1.0,
        count,
        0.05,
        120,
    )

    src_packets = integer_log_normal(
        np.log(50),
        0.9,
        count,
        3,
        10000,
    )

    dst_packets = integer_log_normal(
        np.log(70),
        0.9,
        count,
        3,
        15000,
    )

    src_size = clipped_normal(
        700,
        250,
        count,
        40,
        1800,
    )

    dst_size = clipped_normal(
        950,
        350,
        count,
        40,
        2500,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / dst_packets,
    )


def generate_malware(count: int) -> dict:
    duration = lognormal(
        np.log(2),
        1.0,
        count,
        0.01,
        120,
    )

    src_packets = integer_log_normal(
        np.log(25),
        0.9,
        count,
        2,
        5000,
    )

    dst_packets = integer_log_normal(
        np.log(18),
        0.9,
        count,
        1,
        5000,
    )

    src_size = clipped_normal(
        600,
        220,
        count,
        40,
        1800,
    )

    dst_size = clipped_normal(
        800,
        280,
        count,
        40,
        2500,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / dst_packets,
    )


def generate_port_scan(count: int) -> dict:
    duration = lognormal(
        np.log(0.004),
        0.8,
        count,
        0.00001,
        2,
    )

    src_packets = rng.integers(
        1,
        5,
        count,
    )

    dst_packets = rng.integers(
        0,
        4,
        count,
    )

    src_size = clipped_normal(
        60,
        25,
        count,
        40,
        200,
    )

    dst_size = clipped_normal(
        80,
        35,
        count,
        0,
        300,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / np.maximum(dst_packets, 1),
    )


def generate_web_attack(count: int) -> dict:
    duration = lognormal(
        np.log(0.15),
        0.9,
        count,
        0.001,
        30,
    )

    src_packets = integer_log_normal(
        np.log(12),
        0.7,
        count,
        2,
        1000,
    )

    dst_packets = integer_log_normal(
        np.log(18),
        0.7,
        count,
        1,
        2000,
    )

    src_size = clipped_normal(
        600,
        200,
        count,
        40,
        1800,
    )

    dst_size = clipped_normal(
        1000,
        350,
        count,
        40,
        3000,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / dst_packets,
    )


def generate_backdoor(count: int) -> dict:
    duration = lognormal(
        np.log(4),
        1.1,
        count,
        0.01,
        120,
    )

    src_packets = integer_log_normal(
        np.log(18),
        0.9,
        count,
        2,
        5000,
    )

    dst_packets = integer_log_normal(
        np.log(22),
        0.9,
        count,
        1,
        5000,
    )

    src_size = clipped_normal(
        450,
        170,
        count,
        40,
        1600,
    )

    dst_size = clipped_normal(
        500,
        190,
        count,
        40,
        1800,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / dst_packets,
    )


def generate_fuzzing(count: int) -> dict:
    duration = lognormal(
        np.log(0.08),
        0.9,
        count,
        0.001,
        20,
    )

    src_packets = integer_log_normal(
        np.log(35),
        0.9,
        count,
        2,
        5000,
    )

    dst_packets = integer_log_normal(
        np.log(25),
        0.9,
        count,
        1,
        5000,
    )

    src_size = clipped_normal(
        900,
        350,
        count,
        40,
        3000,
    )

    dst_size = clipped_normal(
        750,
        300,
        count,
        40,
        2500,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / dst_packets,
    )


def generate_reconnaissance(count: int) -> dict:
    duration = lognormal(
        np.log(0.02),
        0.9,
        count,
        0.00001,
        5,
    )

    src_packets = rng.integers(
        1,
        8,
        count,
    )

    dst_packets = rng.integers(
        0,
        6,
        count,
    )

    src_size = clipped_normal(
        100,
        40,
        count,
        40,
        400,
    )

    dst_size = clipped_normal(
        120,
        50,
        count,
        0,
        500,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / np.maximum(dst_packets, 1),
    )


def generate_other_attack(count: int) -> dict:
    duration = lognormal(
        np.log(0.7),
        1.1,
        count,
        0.001,
        120,
    )

    src_packets = integer_log_normal(
        np.log(20),
        1.0,
        count,
        1,
        5000,
    )

    dst_packets = integer_log_normal(
        np.log(15),
        1.0,
        count,
        0,
        5000,
    )

    src_size = clipped_normal(
        500,
        220,
        count,
        40,
        2000,
    )

    dst_size = clipped_normal(
        600,
        250,
        count,
        40,
        2200,
    )

    return build_flow_features(
        duration,
        src_packets,
        dst_packets,
        src_size,
        dst_size,
        duration / src_packets,
        duration / np.maximum(dst_packets, 1),
    )


GENERATORS = {
    "BENIGN": generate_benign,
    "BRUTE_FORCE": generate_brute_force,
    "DDOS": generate_ddos,
    "DOS": generate_dos,
    "EXPLOIT": generate_exploit,
    "INFILTRATION": generate_infiltration,
    "MALWARE": generate_malware,
    "PORT_SCAN": generate_port_scan,
    "WEB_ATTACK": generate_web_attack,
    "BACKDOOR": generate_backdoor,
    "FUZZING": generate_fuzzing,
    "RECONNAISSANCE": generate_reconnaissance,
    "OTHER_ATTACK": generate_other_attack,
}


# ============================================================
# MAIN GENERATION
# ============================================================

def generate_dataset() -> pd.DataFrame:
    rows = []

    counts = {
        "BENIGN": BENIGN_ROWS,
        **{
            attack: ATTACK_ROWS_PER_CLASS
            for attack in ATTACK_CLASSES
        },
    }

    for attack_class, count in counts.items():

        print(
            f"Generating {attack_class:<20} "
            f"{count:,} rows..."
        )

        features = GENERATORS[
            attack_class
        ](count)

        source_ip, destination_ip = make_ips(
            count
        )

        source_port, destination_port = make_ports(
            count
        )

        # Scenario-specific destination ports.
        if attack_class in {
            "BRUTE_FORCE",
            "BACKDOOR",
        }:
            common_ports = rng.choice(
                [21, 22, 23, 25, 3389],
                count,
            )
            destination_port = common_ports

        elif attack_class in {
            "WEB_ATTACK",
            "EXPLOIT",
            "INFILTRATION",
        }:
            destination_port = rng.choice(
                [80, 443, 8080, 8443],
                count,
            )

        elif attack_class in {
            "PORT_SCAN",
            "RECONNAISSANCE",
        }:
            destination_port = rng.integers(
                1,
                65536,
                count,
            )

        elif attack_class in {
            "DDOS",
            "DOS",
        }:
            destination_port = rng.choice(
                [53, 80, 443],
                count,
            )

        else:
            destination_port = destination_port

        protocol = rng.choice(
            ["TCP", "UDP"],
            count,
            p=[0.82, 0.18],
        )

        if attack_class in {
            "DDOS",
            "DOS",
            "PORT_SCAN",
            "RECONNAISSANCE",
        }:
            protocol = rng.choice(
                ["TCP", "UDP", "ICMP"],
                count,
                p=[0.55, 0.30, 0.15],
            )

        frame = pd.DataFrame(
            features
        )

        frame["dataset_name"] = "Custom-ZUKA"
        frame["dataset_split"] = "synthetic"
        frame["source_file"] = "custom_zuka_flows.csv"

        frame["zuka_attack_class"] = attack_class

        frame["original_attack_category"] = (
            attack_class
        )

        frame["label"] = (
            0 if attack_class == "BENIGN" else 1
        )

        frame["source_ip"] = source_ip
        frame["destination_ip"] = destination_ip
        frame["source_port"] = source_port
        frame["destination_port"] = destination_port
        frame["protocol"] = protocol

        frame["capture_source"] = (
            "synthetic_generation"
        )

        frame["synthetic"] = True

        frame["scenario"] = (
            attack_class.lower()
        )

        rows.append(frame)

    result = pd.concat(
        rows,
        ignore_index=True,
    )

    # Shuffle so classes are not ordered.
    result = result.sample(
        frac=1.0,
        random_state=SEED,
    ).reset_index(drop=True)

    # Stable synthetic event ID.
    result.insert(
        0,
        "event_id",
        np.arange(
            1,
            len(result) + 1,
            dtype=np.int64,
        ),
    )

    # Reorder columns.
    columns = [
        "event_id",
        "dataset_name",
        "dataset_split",
        "source_file",
        "synthetic",
        "scenario",
        "zuka_attack_class",
        "original_attack_category",
        "label",
        *COMMON_FEATURES,
        "source_ip",
        "destination_ip",
        "source_port",
        "destination_port",
        "protocol",
        "capture_source",
    ]

    result = result[columns]

    return result


def validate_dataset(df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("CUSTOM ZUKA DATASET VALIDATION")
    print("=" * 80)

    missing_columns = [
        column
        for column in (
            COMMON_FEATURES
            + [
                "zuka_attack_class",
                "dataset_name",
                "synthetic",
            ]
        )
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    feature_values = df[
        COMMON_FEATURES
    ].to_numpy(dtype=float)

    if not np.isfinite(
        feature_values
    ).all():
        raise ValueError(
            "Dataset contains non-finite values."
        )

    negative_counts = (
        df[COMMON_FEATURES]
        .lt(0)
        .sum()
    )

    negative_total = int(
        negative_counts.sum()
    )

    if negative_total:
        raise ValueError(
            "Dataset contains negative common-feature values:\n"
            f"{negative_counts[negative_counts > 0]}"
        )

    if not df["synthetic"].eq(True).all():
        raise ValueError(
            "Every custom ZUKA row must be marked synthetic=True."
        )

    if not df["dataset_name"].eq(
        "Custom-ZUKA"
    ).all():
        raise ValueError(
            "Unexpected dataset_name values."
        )

    print(
        f"Rows              : {len(df):,}"
    )

    print(
        f"Columns           : {len(df.columns)}"
    )

    print(
        f"Null values       : {int(df[COMMON_FEATURES].isna().sum().sum()):,}"
    )

    print(
        f"Infinite values   : 0"
    )

    print(
        f"Negative values   : {negative_total:,}"
    )

    print(
        f"Synthetic rows    : {int(df['synthetic'].sum()):,}"
    )

    print("\nClass distribution:")
    print(
        df["zuka_attack_class"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nFeature availability:")

    for feature in COMMON_FEATURES:
        available = int(
            df[feature].notna().sum()
        )

        percentage = (
            available / len(df) * 100
        )

        print(
            f"{feature:<25}"
            f"{available:,}/{len(df):,} "
            f"({percentage:.2f}%)"
        )

    print("\nPASS: Custom ZUKA dataset validation succeeded.")


def save_metadata(df: pd.DataFrame) -> None:

    metadata = {
        "dataset_name": "Custom-ZUKA",
        "dataset_type": "synthetic",
        "synthetic": True,
        "purpose": (
            "Synthetic flow-level cybersecurity dataset "
            "for ZUKA unified model development."
        ),
        "generation_seed": SEED,
        "total_rows": int(len(df)),
        "features": COMMON_FEATURES,
        "feature_count": len(COMMON_FEATURES),
        "network_metadata": [
            "source_ip",
            "destination_ip",
            "source_port",
            "destination_port",
            "protocol",
        ],
        "attack_classes": sorted(
            df[
                "zuka_attack_class"
            ].unique()
            .tolist()
        ),
        "class_distribution": {
            key: int(value)
            for key, value in (
                df[
                    "zuka_attack_class"
                ]
                .value_counts()
                .to_dict()
                .items()
            )
        },
        "source_note": (
            "This dataset is programmatically generated by ZUKA "
            "and must not be represented as real captured network traffic."
        ),
        "generation_method": (
            "Scenario-based statistical flow generation with "
            "class-specific packet, byte, duration, rate, "
            "inter-arrival-time, port and protocol distributions."
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

    print("=" * 80)
    print("ZUKA - CUSTOM DATASET GENERATOR")
    print("=" * 80)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = generate_dataset()

    validate_dataset(df)

    print("\nSaving dataset...")

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    save_metadata(df)

    print("\n" + "=" * 80)
    print("CUSTOM ZUKA DATASET CREATED")
    print("=" * 80)

    print(
        f"Dataset : {OUTPUT_FILE}"
    )

    print(
        f"Metadata: {METADATA_FILE}"
    )

    print(
        f"Rows    : {len(df):,}"
    )

    print(
        f"Columns : {len(df.columns)}"
    )

    print(
        "Synthetic: TRUE"
    )

    print("=" * 80)


if __name__ == "__main__":
    main()