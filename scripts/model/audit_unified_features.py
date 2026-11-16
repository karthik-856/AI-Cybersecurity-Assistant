from pathlib import Path
import pandas as pd


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


def normalize(name: str) -> str:
    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace(".", "_")
    )


def find_cic_file():
    files = sorted(
        f for f in CIC_DIR.glob("*.csv")
        if f.name != "cic_label_mapping.csv"
    )

    if not files:
        raise FileNotFoundError(
            f"No normalized CIC CSV files found in {CIC_DIR}"
        )

    return files[0]


def main():
    print("=" * 100)
    print("ZUKA UNIFIED FEATURE COMPATIBILITY AUDIT")
    print("=" * 100)

    cic_file = find_cic_file()

    unsw_files = sorted(
        UNSW_DIR.glob("UNSW_NB15_*_normalized.csv")
    )

    if not unsw_files:
        raise FileNotFoundError(
            f"No normalized UNSW files found in {UNSW_DIR}"
        )

    # Read headers only.
    cic_columns = pd.read_csv(
        cic_file,
        nrows=0,
    ).columns.tolist()

    unsw_columns = pd.read_csv(
        unsw_files[0],
        nrows=0,
    ).columns.tolist()

    print("\nCIC source:")
    print(f"  {cic_file.name}")
    print(f"  Columns: {len(cic_columns)}")

    print("\nUNSW source:")
    print(f"  {unsw_files[0].name}")
    print(f"  Columns: {len(unsw_columns)}")

    cic_norm = {
        normalize(c): c
        for c in cic_columns
    }

    unsw_norm = {
        normalize(c): c
        for c in unsw_columns
    }

    exact_common = sorted(
        set(cic_norm) & set(unsw_norm)
    )

    print("\n" + "-" * 100)
    print("EXACT NORMALIZED COLUMN NAME OVERLAP")
    print("-" * 100)

    if exact_common:
        for name in exact_common:
            print(
                f"{cic_norm[name]:35s} <-> {unsw_norm[name]}"
            )
    else:
        print("No exact normalized-name overlap found.")

    print("\n" + "-" * 100)
    print("CIC MODEL FEATURES")
    print("-" * 100)

    cic_excluded = {
        "label",
        "label_id",
        "attack_cat",
        "zuka_attack_class",
        "original_attack_category",
        "dataset_name",
        "dataset_split",
    }

    for column in cic_columns:
        if normalize(column) not in cic_excluded:
            print(column)

    print("\n" + "-" * 100)
    print("UNSW COLUMNS")
    print("-" * 100)

    for column in unsw_columns:
        print(column)

    print("\n" + "-" * 100)
    print("LIKELY SEMANTIC FEATURE PAIRS")
    print("-" * 100)

    semantic_pairs = [
        ("flow_duration", "dur"),

        ("total_fwd_packets", "spkts"),
        ("total_backward_packets", "dpkts"),

        ("total_length_of_fwd_packets", "sbytes"),
        ("total_length_of_bwd_packets", "dbytes"),

        ("flow_packets_per_second", "rate"),

        ("fwd_packet_length_mean", "smean"),
        ("bwd_packet_length_mean", "dmean"),

        ("fwd_iat_mean", "sinpkt"),
        ("bwd_iat_mean", "dinpkt"),

        ("fwd_header_length", None),
        ("bwd_header_length", None),

        ("destination_port", None),
        ("protocol", "proto"),
    ]

    for cic_name, unsw_name in semantic_pairs:
        cic_match = None
        unsw_match = None

        cic_target = normalize(cic_name)
        if cic_target in cic_norm:
            cic_match = cic_norm[cic_target]

        if unsw_name is not None:
            unsw_target = normalize(unsw_name)
            if unsw_target in unsw_norm:
                unsw_match = unsw_norm[unsw_target]

        print(
            f"CIC: {cic_match or '[not found]':35s} "
            f"<-> UNSW: {unsw_match or '[not found]'}"
        )

    print("\n" + "-" * 100)
    print("IMPORTANT DATASET-SPECIFIC FEATURES")
    print("-" * 100)

    print("\nCIC-specific examples:")
    for column in cic_columns:
        n = normalize(column)
        if n not in unsw_norm:
            print(f"  CIC ONLY:  {column}")

    print("\nUNSW-specific examples:")
    for column in unsw_columns:
        n = normalize(column)
        if n not in cic_norm:
            print(f"  UNSW ONLY: {column}")

    print("\n" + "=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)
    print(
        "\nNo feature mapping has been created yet. "
        "This audit intentionally does not assume semantic equivalence."
    )


if __name__ == "__main__":
    main()