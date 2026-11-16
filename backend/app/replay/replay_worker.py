from __future__ import annotations

import csv
import logging
import random
import threading

from backend.app.database.session import SessionLocal
from backend.app.replay.replay_service import DEFAULT_REPLAY_FILE, replay_dataset


logger = logging.getLogger("zuka.replay_worker")


REPLAY_INTERVAL_SECONDS = 5
DATASET_PATH = str(DEFAULT_REPLAY_FILE)


class DatasetReplayWorker:
    """
    Background worker for ZUKA dataset replay.

    Every cycle, one random row from the unified test dataset
    is selected and processed through the existing ZUKA
    detection pipeline.

    This is dataset replay only.
    It does not capture live network traffic.
    """

    def __init__(
        self,
        interval_seconds: int = REPLAY_INTERVAL_SECONDS,
        dataset_path: str = DATASET_PATH,
    ):
        self.interval_seconds = interval_seconds
        self.dataset_path = dataset_path

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        self._row_count: int | None = None
        self._actual_classes: list[str] | None = None

    def start(self) -> None:
        """Start the replay worker once."""

        if self._thread is not None and self._thread.is_alive():
            logger.info(
                "ZUKA dataset replay worker is already running."
            )
            return

        self._load_dataset_metadata()

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="zuka-dataset-replay-worker",
            daemon=True,
        )

        self._thread.start()

        logger.info(
            "ZUKA RANDOM dataset replay worker started. "
            "Interval=%s seconds, rows=%s",
            self.interval_seconds,
            self._row_count,
        )

    def stop(self) -> None:
        """Stop the replay worker."""

        self._stop_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2)

        logger.info(
            "ZUKA random dataset replay worker stopped."
        )

    def _load_dataset_metadata(self) -> None:
        """Load row count and actual labels once."""

        if self._row_count is not None:
            return

        actual_classes: list[str] = []

        with open(
            self.dataset_path,
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                actual_classes.append(
                    str(
                        row.get(
                            "zuka_attack_class",
                            "UNKNOWN",
                        )
                    )
                )

        self._actual_classes = actual_classes
        self._row_count = len(actual_classes)

        logger.info(
            "ZUKA replay dataset loaded: %s rows.",
            self._row_count,
        )

    def _run(self) -> None:
        """Continuously process random dataset rows."""

        while not self._stop_event.is_set():

            try:
                self._process_random_row()

            except Exception:
                logger.exception(
                    "Unexpected error in ZUKA dataset replay worker."
                )

            self._stop_event.wait(
                self.interval_seconds
            )

    def _process_random_row(self) -> None:
        """Select and process exactly one random row."""

        if not self._row_count:
            logger.warning(
                "ZUKA replay dataset contains no rows."
            )
            self._stop_event.set()
            return

        random_row = random.randrange(
            self._row_count
        )

        actual_class = "UNKNOWN"

        if self._actual_classes is not None:
            actual_class = self._actual_classes[
                random_row
            ]

        db = SessionLocal()

        try:
            result = replay_dataset(
                start_row=random_row,
                max_rows=1,
                include_xai=True,
                db=db,
            )

            processed_rows = result.get(
                "processed_rows",
                0,
            )

            if processed_rows == 0:
                logger.warning(
                    "Random replay selected row %s, "
                    "but no row was processed.",
                    random_row,
                )
                return

            row_result = result["results"][0]

            logger.info(
                "ZUKA RANDOM REPLAY | "
                "row=%s | dataset=%s | "
                "actual=%s | predicted=%s | "
                "confidence=%.4f | attack=%s | "
                "severity=%s | event=%s | alert=%s",
                row_result.get("row_index"),
                row_result.get("dataset_name"),
                actual_class,
                row_result.get("predicted_class"),
                float(
                    row_result.get("confidence") or 0
                ),
                row_result.get("is_attack"),
                row_result.get("severity"),
                row_result.get("network_event_id"),
                row_result.get("alert_id"),
            )

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()


replay_worker = DatasetReplayWorker()
