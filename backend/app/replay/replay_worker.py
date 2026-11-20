"""Random dataset inference on the API host, independent of browser timers."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import logging
import random
import threading

from backend.app.database.session import SessionLocal
from backend.app.detection.workload import model_task_lock
from backend.app.replay.replay_service import DEFAULT_REPLAY_FILE, replay_dataset

logger = logging.getLogger("zuka.replay_worker")
REPLAY_INTERVAL_SECONDS = 15
DATASET_PATH = str(DEFAULT_REPLAY_FILE)


class DatasetReplayWorker:
    def __init__(self, interval_seconds=REPLAY_INTERVAL_SECONDS, dataset_path=DATASET_PATH):
        if interval_seconds <= 0:
            raise ValueError("Replay interval must be positive.")
        self.interval_seconds = interval_seconds
        self.dataset_path = dataset_path
        self._stop_event = threading.Event()
        self._thread = None
        self._row_count = None
        self._lock = threading.Lock()
        self._processed = 0
        self._alerts = 0
        self._last_processed_at = None
        self._last_error = None

    def snapshot(self):
        with self._lock:
            return {
                "running": bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set()),
                "interval_seconds": self.interval_seconds,
                "dataset_rows": self._row_count,
                "processed_events": self._processed,
                "generated_alerts": self._alerts,
                "last_processed_at": self._last_processed_at,
                "error": self._last_error,
            }

    def _load_dataset_metadata(self):
        if self._row_count is None:
            with open(self.dataset_path, encoding="utf-8-sig", newline="") as source:
                self._row_count = sum(1 for _ in csv.DictReader(source))
        if not self._row_count:
            raise ValueError("Replay dataset is empty.")

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            try:
                self._load_dataset_metadata()
            except (OSError, ValueError):
                self._last_error = "The replay dataset is unavailable. Check server logs."
                logger.exception("Unable to load the replay dataset.")
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, name="zuka-dataset-replay-worker", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self._process_random_row()
            except Exception:
                with self._lock:
                    self._last_error = "Dataset detection failed. Check server logs."
                logger.exception("Dataset detection failed.")
            self._stop_event.wait(self.interval_seconds)

    def _process_random_row(self):
        self._load_dataset_metadata()
        # Share the one loaded model and avoid overlap with analyst requests.
        if not model_task_lock.acquire(blocking=False):
            return None
        db = None
        try:
            db = SessionLocal()
            result = replay_dataset(csv_path=self.dataset_path,
                start_row=random.randrange(self._row_count), max_rows=1, include_xai=True, db=db)
            if not result.get("processed_rows"):
                raise ValueError("No dataset row was processed.")
            row = result["results"][0]
            with self._lock:
                self._processed += 1
                self._alerts += bool(row.get("alert_id"))
                self._last_processed_at = datetime.now(timezone.utc).isoformat()
                self._last_error = None
            logger.info("Random dataset detection: event=%s class=%s alert=%s",
                row.get("network_event_id"), row.get("predicted_class"), row.get("alert_id"))
            return row
        except Exception:
            if db is not None:
                db.rollback()
            raise
        finally:
            if db is not None:
                db.close()
            model_task_lock.release()


replay_worker = DatasetReplayWorker()
