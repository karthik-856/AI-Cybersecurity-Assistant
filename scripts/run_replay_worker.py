"""
Standalone Dataset Replay Worker for Production Deployment
Runs the ZUKA replay loop as an isolated background service, preventing
duplicate executions when FastAPI is scaled across multiple Uvicorn workers.
"""

import logging
import signal
import sys
import time

from backend.app.replay.replay_worker import replay_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("zuka.standalone_worker")

def handle_shutdown(signum, frame):
    logger.info("Received termination signal. Shutting down replay worker...")
    if hasattr(replay_worker, "stop"):
        replay_worker.stop()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    logger.info("Starting ZUKA standalone dataset replay worker...")
    replay_worker.start()
    
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
