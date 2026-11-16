"""
ZUKA - AI Cybersecurity SOC Assistant
=====================================

Module:
    src/ingestion/traffic_collector.py

Purpose:
    Automatic network-flow ingestion for the ZUKA cybersecurity assistant.

Responsibilities:
    1. Accept network-flow records automatically.
    2. Support CSV/test-mode ingestion during development.
    3. Validate incoming flow records.
    4. Normalize basic metadata.
    5. Produce a standard flow DataFrame for preprocessing.
    6. Avoid manual 78-feature entry.

Important:
    This module DOES NOT perform attack detection.
    Detection is handled by:
        src/detection/xgboost_detector.py

Pipeline:
    Network Traffic
          ↓
    TrafficCollector
          ↓
    FeaturePipeline
          ↓
    XGBoost Detector
          ↓
    SHAP
          ↓
    Alert Engine
          ↓
    Recommendation Engine
          ↓
    ZUKA Assistant
          ↓
    SOC Dashboard
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Optional

import pandas as pd


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger("zuka.ingestion")

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_BATCH_SIZE = 1000

SUPPORTED_FILE_EXTENSIONS = {
    ".csv",
    ".parquet",
}


# ============================================================================
# DATA STRUCTURE
# ============================================================================

@dataclass
class FlowBatch:
    """
    Standard container returned by the traffic collector.

    Attributes
    ----------
    data:
        Network-flow records.

    source:
        Name of the source that produced the records.

    batch_id:
        Sequential batch identifier.

    collected_at:
        Timestamp associated with collection.

    """

    data: pd.DataFrame
    source: str
    batch_id: int
    collected_at: pd.Timestamp


# ============================================================================
# TRAFFIC COLLECTOR
# ============================================================================

class TrafficCollector:
    """
    Automatic network-flow ingestion component for ZUKA.

    The collector deliberately does not know anything about the ML model.
    Its job is only to obtain and standardize incoming traffic records.

    Supported development sources:

        CSV
        Parquet
        Pandas DataFrame
        Python iterable/generator

    Future live sources can be connected through `stream_provider`.

    Examples
    --------
    CSV:

        collector = TrafficCollector()
        flows = collector.read_csv("flows.csv")

    DataFrame:

        collector = TrafficCollector()
        flows = collector.collect_dataframe(df)

    Streaming:

        collector = TrafficCollector()

        for batch in collector.stream(provider):
            process(batch.data)
    """

    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        source_name: str = "automatic_network_input",
    ) -> None:

        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")

        self.batch_size = batch_size
        self.source_name = source_name

        self._batch_counter = 0

        logger.info(
            "ZUKA TrafficCollector initialized | source=%s | batch_size=%d",
            self.source_name,
            self.batch_size,
        )

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================

    def _next_batch_id(self) -> int:
        """Return the next sequential batch ID."""

        self._batch_counter += 1
        return self._batch_counter

    @staticmethod
    def _validate_dataframe(data: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and clean a collected flow DataFrame.

        This method intentionally does not impose the 78 model features.
        Feature engineering/validation belongs to feature_pipeline.py.
        """

        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                "Traffic data must be provided as a pandas DataFrame."
            )

        if data.empty:
            raise ValueError("Received an empty traffic-flow dataset.")

        cleaned = data.copy()

        # Remove completely empty columns.
        empty_columns = [
            column
            for column in cleaned.columns
            if cleaned[column].isna().all()
        ]

        if empty_columns:
            cleaned = cleaned.drop(columns=empty_columns)

        # Remove duplicate column names.
        if cleaned.columns.duplicated().any():
            duplicated = cleaned.columns[
                cleaned.columns.duplicated()
            ].tolist()

            raise ValueError(
                f"Duplicate column names detected: {duplicated}"
            )

        # Reset index so downstream modules receive predictable records.
        cleaned = cleaned.reset_index(drop=True)

        return cleaned

    def _create_batch(
        self,
        data: pd.DataFrame,
        source: Optional[str] = None,
    ) -> FlowBatch:
        """Convert a DataFrame into the standard ZUKA FlowBatch."""

        cleaned = self._validate_dataframe(data)

        return FlowBatch(
            data=cleaned,
            source=source or self.source_name,
            batch_id=self._next_batch_id(),
            collected_at=pd.Timestamp.now(tz="UTC"),
        )

    # ========================================================================
    # CSV INGESTION
    # ========================================================================

    def read_csv(
        self,
        file_path: str | Path,
        source_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Read network-flow records from CSV.

        This is primarily intended for:
            - CIC-IDS2017 testing
            - offline replay
            - development
            - validation

        It does NOT represent the final live-network collector.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Traffic input file not found: {path}"
            )

        if path.suffix.lower() != ".csv":
            raise ValueError(
                f"Expected a CSV file, received: {path.suffix}"
            )

        logger.info("Reading traffic CSV: %s", path)

        data = pd.read_csv(path)

        data = self._validate_dataframe(data)

        logger.info(
            "CSV ingestion completed | records=%d | features=%d",
            len(data),
            len(data.columns),
        )

        return data

    # ========================================================================
    # PARQUET INGESTION
    # ========================================================================

    def read_parquet(
        self,
        file_path: str | Path,
    ) -> pd.DataFrame:
        """
        Read network-flow records from Parquet.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Traffic input file not found: {path}"
            )

        if path.suffix.lower() != ".parquet":
            raise ValueError(
                f"Expected a Parquet file, received: {path.suffix}"
            )

        logger.info("Reading traffic Parquet: %s", path)

        data = pd.read_parquet(path)

        data = self._validate_dataframe(data)

        logger.info(
            "Parquet ingestion completed | records=%d | features=%d",
            len(data),
            len(data.columns),
        )

        return data

    # ========================================================================
    # DATAFRAME INGESTION
    # ========================================================================

    def collect_dataframe(
        self,
        data: pd.DataFrame,
        source_name: Optional[str] = None,
    ) -> FlowBatch:
        """
        Accept already-collected network-flow records.

        This is useful when another application, collector, API,
        packet parser, or flow exporter provides a DataFrame.
        """

        batch = self._create_batch(
            data=data,
            source=source_name,
        )

        logger.info(
            "DataFrame collected | batch=%d | source=%s | records=%d",
            batch.batch_id,
            batch.source,
            len(batch.data),
        )

        return batch

    # ========================================================================
    # BATCH GENERATOR
    # ========================================================================

    def create_batches(
        self,
        data: pd.DataFrame,
        source_name: Optional[str] = None,
    ) -> Iterator[FlowBatch]:
        """
        Split collected traffic records into manageable batches.

        This allows ZUKA to process traffic continuously instead of
        requiring the entire dataset to be loaded into memory at once.
        """

        cleaned = self._validate_dataframe(data)

        source = source_name or self.source_name

        total_records = len(cleaned)

        for start in range(0, total_records, self.batch_size):

            end = min(
                start + self.batch_size,
                total_records,
            )

            batch_data = cleaned.iloc[start:end].copy()

            yield self._create_batch(
                data=batch_data,
                source=source,
            )

    # ========================================================================
    # STREAM PROVIDER
    # ========================================================================

    def stream(
        self,
        stream_provider: Callable[[], pd.DataFrame],
        interval_seconds: float = 1.0,
        max_batches: Optional[int] = None,
    ) -> Iterator[FlowBatch]:
        """
        Continuously collect traffic from an external provider.

        Parameters
        ----------
        stream_provider:
            Function that returns newly collected network-flow records.

        interval_seconds:
            Delay between collection cycles.

        max_batches:
            Maximum number of batches.
            None means continue until stopped.

        Example
        -------
        def get_network_flows():
            return some_network_flow_source()

        collector = TrafficCollector()

        for batch in collector.stream(
            get_network_flows,
            interval_seconds=1,
        ):
            process(batch.data)
        """

        if interval_seconds < 0:
            raise ValueError(
                "interval_seconds cannot be negative."
            )

        batches_processed = 0

        logger.info(
            "Starting ZUKA traffic stream | source=%s",
            self.source_name,
        )

        while True:

            if (
                max_batches is not None
                and batches_processed >= max_batches
            ):
                break

            try:

                incoming_data = stream_provider()

                if incoming_data is None:
                    logger.debug(
                        "Traffic provider returned no data."
                    )

                elif not isinstance(
                    incoming_data,
                    pd.DataFrame,
                ):
                    raise TypeError(
                        "stream_provider must return a "
                        "pandas DataFrame."
                    )

                elif incoming_data.empty:
                    logger.debug(
                        "Traffic provider returned an empty batch."
                    )

                else:

                    for batch in self.create_batches(
                        incoming_data,
                        source_name=self.source_name,
                    ):

                        batches_processed += 1

                        logger.info(
                            "Stream batch collected | batch=%d | records=%d",
                            batch.batch_id,
                            len(batch.data),
                        )

                        yield batch

                        if (
                            max_batches is not None
                            and batches_processed >= max_batches
                        ):
                            break

            except KeyboardInterrupt:
                logger.info(
                    "ZUKA traffic stream stopped by user."
                )
                break

            except Exception:
                logger.exception(
                    "Error while collecting network traffic."
                )
                raise

            if (
                max_batches is None
                or batches_processed < max_batches
            ):
                time.sleep(interval_seconds)

        logger.info(
            "ZUKA traffic stream stopped | batches=%d",
            batches_processed,
        )


# ============================================================================
# CIC-IDS2017 TEST HELPER
# ============================================================================

def load_cic_ids2017_test_sample(
    file_path: str | Path,
    sample_size: int = 10,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Load a small CIC-IDS2017 sample for development/testing.

    This function is NOT the live detection mechanism.

    It allows us to test the exact same ingestion interface before
    connecting ZUKA to a real network-flow source.
    """

    if sample_size <= 0:
        raise ValueError(
            "sample_size must be greater than zero."
        )

    collector = TrafficCollector(
        source_name="CIC-IDS2017_test",
    )

    data = collector.read_csv(file_path)

    sample_size = min(
        sample_size,
        len(data),
    )

    sample = data.sample(
        n=sample_size,
        random_state=random_state,
    ).reset_index(drop=True)

    logger.info(
        "CIC-IDS2017 test sample prepared | records=%d",
        len(sample),
    )

    return sample


# ============================================================================
# BASIC SELF-TEST
# ============================================================================

if __name__ == "__main__":

    print("=" * 80)
    print("ZUKA — TRAFFIC COLLECTOR SELF TEST")
    print("=" * 80)

    demo_data = pd.DataFrame(
        {
            "Destination Port": [80, 443],
            "Flow Duration": [1000, 2500],
            "Total Fwd Packets": [10, 20],
            "Total Backward Packets": [8, 15],
        }
    )

    collector = TrafficCollector(
        batch_size=1,
        source_name="ZUKA_SELF_TEST",
    )

    batches = list(
        collector.create_batches(
            demo_data,
        )
    )

    print(f"Input records : {len(demo_data)}")
    print(f"Batches       : {len(batches)}")

    for batch in batches:
        print(
            f"Batch {batch.batch_id}: "
            f"{len(batch.data)} record(s)"
        )

    print()
    print("✓ TrafficCollector self-test completed")