"""
Manual training entry point: retrains the district risk model from
data/historical_cases_clean.csv and prints a hold-out evaluation report.

    python ml_pipeline.py

Uses the same feature engineering and hyperparameters (app/config.py) as the
automated retraining that runs after every new IDSP bulletin.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.ml_trainer import retrain_model

if __name__ == "__main__":
    print("--- Initializing SentinelGIS Time-Series Pipeline (Random Forest) ---")
    ok = retrain_model(evaluate=True)
    print("--- Model Pipeline Execution Complete! ---" if ok else "--- Model Pipeline Failed ---")
    sys.exit(0 if ok else 1)
