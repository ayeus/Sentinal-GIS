import os
import time
import subprocess
import pandas as pd
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPER_SCRIPT = os.path.join(BASE_DIR, "data", "scraper.py")
EXTRACTOR_SCRIPT = os.path.join(BASE_DIR, "data", "pdf_extractor.py")
CLEANER_SCRIPT = os.path.join(BASE_DIR, "data", "clean_data.py")
CSV_PATH = os.path.join(BASE_DIR, "data", "historical_cases_clean.csv")

def run_step(script_path, name):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting {name}...")
    try:
        result = subprocess.run(["python3", script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {name} completed successfully.")
            return True
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {name} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error running {name}: {e}")
        return False

def check_for_new_data():
    """Simple check to see if CSV was modified in the last loop."""
    if not os.path.exists(CSV_PATH):
        return True
    mtime = os.path.getmtime(CSV_PATH)
    return (time.time() - mtime) < 60  # If modified in last 60s

def main_loop():
    print("=== SentinelGIS Real-Time Pipeline Started ===")
    print("Watching for new IDSP bulletins and news alerts...")
    
    while True:
        # Step 1: Scrape
        run_step(SCRAPER_SCRIPT, "Scraper")
        
        # Step 2: Extract
        run_step(EXTRACTOR_SCRIPT, "PDF Extractor")
        
        # Step 3: Clean
        run_step(CLEANER_SCRIPT, "Data Cleaner")
        
        if check_for_new_data():
            print(f"[{datetime.now().strftime('%H:%M:%S')}] New data detected! Retraining ML model...")
            retrainer_script = os.path.join(BASE_DIR, "app", "services", "ml_trainer.py")
            run_step(retrainer_script, "ML Model Retrainer")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ML Model retraining complete! APIs and forecasts updated.")

        time.sleep(1800) # Every 30 mins

if __name__ == "__main__":
    main_loop()
