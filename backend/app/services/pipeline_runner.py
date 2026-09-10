import sys
import os
import time

# Ensure we can import from the 'data' and 'app' directories
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from data import scraper
from data import pdf_extractor
from data import clean_data
from app.services import ml_trainer

def auto_process_new_pdfs():
    """
    Checks for any new unextracted PDFs in idsp_pdfs/.
    If found, extracts them, cleans the data, and retrains the model automatically.
    """
    print("🔍 [Auto-Watcher] Checking for new unextracted IDSP PDFs...")
    try:
        new_rows = pdf_extractor.extract_batch()
        if new_rows > 0:
            print(f"📄 [Auto-Watcher] Extracted {new_rows} new records from new PDF(s).")
            print("🧹 [Auto-Watcher] Cleaning and standardizing dataset...")
            total_clean = clean_data.main()
            print(f"📊 [Auto-Watcher] Clean dataset now has {total_clean} records. Triggering ML retraining...")
            ml_trainer.retrain_model()
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
    
    # 1. Scrape PDFs from IDSP portal
    try:
        print("\n--- Phase 1: Scraping IDSP Portal for New Bulletins ---")
        scraper.main()
    except Exception as e:
        print(f"Phase 1 Scraper Notice: {e}")
        
    # 2. Extract, Clean & Retrain if new PDFs found
    result = auto_process_new_pdfs()
    
    print("\n" + "="*50)
    print("✅ AUTOMATED PIPELINE COMPLETED")
    print("="*50)
    return result

if __name__ == "__main__":
    run_pipeline()
