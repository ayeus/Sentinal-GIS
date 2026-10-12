"""
Standalone ingestion loop for running the pipeline outside the API process:
scrape IDSP bulletins -> extract PDFs -> clean -> retrain (only when new
records were extracted), every REALTIME_LOOP_SECONDS.

    python realtime_pipeline.py

The API already schedules the same pipeline itself; set ENABLE_SCHEDULER=false
on the API if you run this worker instead.
"""
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import REALTIME_LOOP_SECONDS
from app.services.pipeline_runner import run_pipeline


def main_loop():
    print("=== SentinelGIS Real-Time Pipeline Started ===")
    print(f"Watching for new IDSP bulletins every {REALTIME_LOOP_SECONDS}s...")

    while True:
        result = run_pipeline()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Pipeline result: {result}")
        time.sleep(REALTIME_LOOP_SECONDS)

if __name__ == "__main__":
    main_loop()
