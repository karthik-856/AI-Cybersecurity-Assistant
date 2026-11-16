"""
================================================================================
ZUKA — CIC-IDS2017 SOC REPLAY RUNNER
================================================================================

Purpose:
    Replay prepared CIC-IDS2017 test flows through the real ZUKA SOC pipeline.

Flow:

    CIC-IDS2017 test.csv
            ↓
    Chunked replay
            ↓
    ZUKA SOCPipeline
            ↓
    XGBoost Detection
            ↓
    SHAP Explainability
            ↓
    Alert Engine
            ↓
    Recommendation Engine
            ↓
    SQLite SOC Database

Important:
    - This is a dataset replay/testing mechanism.
    - It is NOT genuine live network capture.
    - Label_ID is never sent to the model.
    - No manual 78-feature entry is required.
    - Automated containment remains disabled.
    - Human analyst approval remains required.
================================================================================
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd


# =============================================================================
# PROJECT PATH
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# =============================================================================
# ZUKA PIPELINE
# =============================================================================

from pipeline.soc_pipeline import SOCPipeline


# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================

DEFAULT_DATASET = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "CIC-IDS2017_splits"
    / "test.csv"
)

DEFAULT_CHUNK_SIZE = 10

DEFAULT_INTERVAL = 3.0

DEFAULT_MAX_RECORDS = 100


# =============================================================================
# REPLAY RUNNER
# =============================================================================

class CICIDS2017Replay:
    """
    Replay CIC-IDS2017 test flows through the real ZUKA SOC pipeline.
    """

    def __init__(
        self,
        dataset_path: Path = DEFAULT_DATASET,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        interval_seconds: float = DEFAULT_INTERVAL,
        max_records: int = DEFAULT_MAX_RECORDS,
    ) -> None:

        self.dataset_path = Path(dataset_path)

        self.chunk_size = int(chunk_size)

        self.interval_seconds = float(interval_seconds)

        self.max_records = int(max_records)

        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"CIC-IDS2017 dataset not found: "
                f"{self.dataset_path}"
            )

        if self.chunk_size <= 0:
            raise ValueError(
                "chunk_size must be greater than zero."
            )

        if self.interval_seconds < 0:
            raise ValueError(
                "interval_seconds cannot be negative."
            )

        if self.max_records <= 0:
            raise ValueError(
                "max_records must be greater than zero."
            )

        print("=" * 80)
        print("ZUKA — CIC-IDS2017 SOC REPLAY")
        print("=" * 80)

        print(
            f"Dataset       : {self.dataset_path}"
        )

        print(
            f"Chunk size    : {self.chunk_size}"
        )

        print(
            f"Interval      : {self.interval_seconds} seconds"
        )

        print(
            f"Max records   : {self.max_records}"
        )

        print("=" * 80)

        self.pipeline = SOCPipeline()

    # -------------------------------------------------------------------------
    # DATA VALIDATION
    # -------------------------------------------------------------------------

    def validate_dataset(self) -> None:
        """
        Verify the dataset structure before replay.
        """

        print()
        print("DATASET VALIDATION")
        print("-" * 80)

        header = pd.read_csv(
            self.dataset_path,
            nrows=0,
        )

        columns = list(header.columns)

        print(
            f"Columns found : {len(columns)}"
        )

        if "Label_ID" not in columns:
            raise ValueError(
                "Expected Label_ID column was not found."
            )

        model_columns = [
            column
            for column in columns
            if column != "Label_ID"
        ]

        print(
            f"Model columns : {len(model_columns)}"
        )

        if len(model_columns) != 78:
            raise ValueError(
                f"Expected 78 model features, "
                f"found {len(model_columns)}."
            )

        print("✓ Label_ID detected")

        print("✓ 78 model features detected")

        print("✓ Dataset structure verified")

    # -------------------------------------------------------------------------
    # REPLAY
    # -------------------------------------------------------------------------

    def run(self) -> None:
        """
        Replay records through SOCPipeline.
        """

        self.validate_dataset()

        print()
        print("STARTING REPLAY")
        print("-" * 80)

        processed_records = 0

        chunk_number = 0

        try:

            reader = pd.read_csv(
                self.dataset_path,
                chunksize=self.chunk_size,
            )

            for chunk in reader:

                if processed_records >= self.max_records:
                    break

                chunk_number += 1

                remaining = (
                    self.max_records
                    - processed_records
                )

                if len(chunk) > remaining:

                    chunk = chunk.iloc[:remaining].copy()

                # -------------------------------------------------------------
                # LABEL_ID IS DATASET GROUND TRUTH ONLY.
                #
                # NEVER SEND IT TO THE MODEL.
                # -------------------------------------------------------------

                if "Label_ID" in chunk.columns:

                    dataset_labels = (
                        chunk["Label_ID"]
                        .copy()
                    )

                    chunk = chunk.drop(
                        columns=["Label_ID"]
                    )

                else:

                    dataset_labels = None

                print()
                print(
                    f"[REPLAY {chunk_number}] "
                    f"Processing {len(chunk)} flow records..."
                )

                # -------------------------------------------------------------
                # PROCESS THROUGH REAL ZUKA PIPELINE
                # -------------------------------------------------------------

                result = self.pipeline.process_batch(
                    chunk
                )

                processed_records += len(chunk)

                # -------------------------------------------------------------
                # DISPLAY BASIC RESULT
                # -------------------------------------------------------------

                print(
                    f"[REPLAY {chunk_number}] "
                    f"Processed total: {processed_records}"
                )

                if isinstance(result, pd.DataFrame):

                    if not result.empty:

                        print(
                            f"[REPLAY {chunk_number}] "
                            f"Pipeline output rows: {len(result)}"
                        )

                        if "Alert_ID" in result.columns:

                            print(
                                f"[REPLAY {chunk_number}] "
                                f"Alerts generated: {len(result)}"
                            )

                    else:

                        print(
                            f"[REPLAY {chunk_number}] "
                            "Pipeline returned no rows."
                        )

                else:

                    print(
                        f"[REPLAY {chunk_number}] "
                        f"Pipeline result type: "
                        f"{type(result).__name__}"
                    )

                if processed_records >= self.max_records:
                    break

                if self.interval_seconds > 0:

                    print(
                        f"[REPLAY {chunk_number}] "
                        f"Waiting {self.interval_seconds} seconds..."
                    )

                    time.sleep(
                        self.interval_seconds
                    )

        except KeyboardInterrupt:

            print()
            print("Replay stopped by analyst.")

        finally:

            self.pipeline.close()

        print()
        print("=" * 80)
        print("ZUKA SOC REPLAY COMPLETED")
        print("=" * 80)

        print(
            f"Records processed: {processed_records}"
        )

        print()
        print(
            "The dashboard can now read the persisted "
            "SOC alerts from data/zuka_soc.db."
        )


# =============================================================================
# COMMAND-LINE INTERFACE
# =============================================================================

def parse_arguments() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Replay CIC-IDS2017 flows through "
            "the ZUKA SOC pipeline."
        )
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default=str(DEFAULT_DATASET),
        help="Path to CIC-IDS2017 test.csv",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Number of flow records processed per replay batch.",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL,
        help="Seconds between replay batches.",
    )

    parser.add_argument(
        "--max-records",
        type=int,
        default=DEFAULT_MAX_RECORDS,
        help="Maximum number of records to replay.",
    )

    return parser.parse_args()


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    args = parse_arguments()

    replay = CICIDS2017Replay(
        dataset_path=Path(args.dataset),
        chunk_size=args.chunk_size,
        interval_seconds=args.interval,
        max_records=args.max_records,
    )

    replay.run()


if __name__ == "__main__":
    main()