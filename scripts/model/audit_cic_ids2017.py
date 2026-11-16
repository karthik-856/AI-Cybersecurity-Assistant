from pathlib import Path
import csv
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "CIC-IDS2017"

EXPECTED_FEATURES = 78


def inspect_header(path: Path):
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)

    cleaned = [str(c).strip() for c in header]

    duplicates = []
    seen = {}

    for col in cleaned:
        if col in seen:
            duplicates.append(col)
        seen[col] = seen.get(col, 0) + 1

    label_matches = [
        (i, repr(col))
        for i, col in enumerate(header)
        if str(col).strip().lower() == "label"
    ]

    return header, cleaned, duplicates, label_matches


def count_rows(path: Path):
    count = 0

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.reader(f)

        # Skip header
        next(reader, None)

        for _ in reader:
            count += 1

    return count


def label_distribution(path: Path):
    counts = {}

    # Discover the actual label column position from the header.
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)

        cleaned = [str(c).strip() for c in header]

        label_indexes = [
            i for i, col in enumerate(cleaned)
            if col.lower() == "label"
        ]

        if not label_indexes:
            raise RuntimeError(
                f"Could not find Label column in {path.name}. "
                f"Last columns: {cleaned[-5:]}"
            )

        label_index = label_indexes[-1]

        for row in reader:
            if not row:
                continue

            value = row[label_index].strip() if label_index < len(row) else ""

            if not value:
                value = "<EMPTY>"

            counts[value] = counts.get(value, 0) + 1

    return counts


def main():
    files = sorted(RAW_DIR.glob("*.csv"))

    if not files:
        raise SystemExit(f"No CSV files found in {RAW_DIR}")

    print("=" * 90)
    print("ZUKA CIC-IDS2017 RAW DATASET AUDIT")
    print("=" * 90)
    print(f"Root: {ROOT}")
    print(f"Raw directory: {RAW_DIR}")
    print(f"Files found: {len(files)}")
    print()

    total_rows = 0

    for path in files:
        print("-" * 90)
        print(f"FILE: {path.name}")

        header, cleaned, duplicates, label_matches = inspect_header(path)

        print(f"Columns found: {len(header)}")
        print(f"Label column matches: {label_matches}")

        if len(header) - 1 == EXPECTED_FEATURES:
            print("Schema: 78 features + Label")
        else:
            print(
                f"WARNING: expected {EXPECTED_FEATURES + 1} columns, "
                f"found {len(header)}"
            )

        if duplicates:
            print(f"Duplicate columns after stripping: {duplicates}")
        else:
            print("Duplicate columns after stripping: none")

        rows = count_rows(path)
        total_rows += rows

        print(f"Rows: {rows:,}")

        print("Labels:")
        try:
            labels = label_distribution(path)

            for label, count in sorted(
                labels.items(),
                key=lambda x: (-x[1], x[0])
            ):
                print(f"  {label}: {count:,}")

        except Exception as exc:
            print(f"  ERROR reading labels: {exc}")

        print()

    print("=" * 90)
    print(f"TOTAL RAW CIC ROWS: {total_rows:,}")
    print("=" * 90)


if __name__ == "__main__":
    main()
