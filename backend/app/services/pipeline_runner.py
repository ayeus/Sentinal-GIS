import sys
import os
from contextlib import contextmanager

# Ensure we can import from the 'data' and 'app' directories
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

try:
    import fcntl
except ImportError:  # Windows: fall back to an in-process lock only
    fcntl = None
import threading

from data import scraper
from data import pdf_extractor
from data import clean_data
import json
from datetime import datetime, timezone

from app.config import PIPELINE_LOCK_FILE, SCRAPE_STATUS_PATH
from app.services import ml_trainer

_THREAD_LOCK = threading.Lock()


@contextmanager
def _pipeline_lock():
    """
    Yields True if this caller holds the pipeline lock, False if another
    thread or worker process is already extracting/retraining. Every Gunicorn
    worker runs its own scheduler, so the lock has to span processes.
    """
    if not _THREAD_LOCK.acquire(blocking=False):
        yield False
        return
    handle = None
    try:
        if fcntl is not None:
            PIPELINE_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
            handle = open(PIPELINE_LOCK_FILE, "w")
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                yield False
                return
        yield True
    finally:
        if handle is not None:
            handle.close()  # closing the descriptor releases the flock
        _THREAD_LOCK.release()


def auto_process_new_pdfs():
    """
    Checks for any new unextracted PDFs in idsp_pdfs/.
    If found, extracts them, cleans the data, and retrains the model automatically.
    """
    with _pipeline_lock() as acquired:
        if not acquired:
            return {"status": "busy", "message": "Pipeline is already running; new PDFs will be picked up by that run or the next check."}

        print("🔍 [Auto-Watcher] Checking for new unextracted IDSP PDFs...")
        try:
            new_rows = pdf_extractor.extract_batch()
            if new_rows > 0:
                print(f"📄 [Auto-Watcher] Extracted {new_rows} new records from new PDF(s).")
                print("🧹 [Auto-Watcher] Cleaning and standardizing dataset...")
                total_clean = clean_data.main()
                print(f"📊 [Auto-Watcher] Clean dataset now has {total_clean} records. Triggering ML retraining...")
                if not ml_trainer.retrain_model():
                    return {"status": "error", "error": "Data was ingested but model retraining failed. Check server logs.", "new_records": new_rows, "total_clean": total_clean}
                print("🎉 [Auto-Watcher] ML Model successfully retrained with latest PDF data!")
                return {"status": "retrained", "new_records": new_rows, "total_clean": total_clean}
            else:
                return {"status": "idle", "message": "No new PDFs to process."}
        except Exception as e:
            print(f"❌ [Auto-Watcher] Error during auto-processing: {e}")
            return {"status": "error", "error": str(e)}

def run_pipeline():
    print("="*50)
    print("🚀 AUTOMATED FULL PIPELINE STARTED")
    print("="*50)
    
    # 1. Scrape PDFs from IDSP portal, and record the outcome so the UI can
    #    show whether automatic updates are actually working
    status = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        print("\n--- Phase 1: Scraping IDSP Portal for New Bulletins ---")
        status.update({"ok": True, **(scraper.main() or {})})
    except Exception as e:
        print(f"Phase 1 Scraper Notice: {e}")
        # Keep the stored reason short and readable; the full error is in the server log
        status.update({"ok": False, "error": type(e).__name__})
    try:
        SCRAPE_STATUS_PATH.write_text(json.dumps(status, indent=2))
    except OSError as e:
        print(f"Could not record scrape status: {e}")
        
    # 2. Extract, Clean & Retrain if new PDFs found
    result = auto_process_new_pdfs()
    
    print("\n" + "="*50)
    print("✅ AUTOMATED PIPELINE COMPLETED")
    print("="*50)
    return result

if __name__ == "__main__":
    run_pipeline()
