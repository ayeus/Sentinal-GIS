import os
from pathlib import Path

# Base directory for the backend application
BACKEND_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BACKEND_DIR.parent

# Data and Model directories
DATA_DIR = BACKEND_DIR / "data"
MODEL_DIR = BACKEND_DIR / "model"
PDF_DIR = BACKEND_DIR / "idsp_pdfs"
PROCESSED_PDFS_FILE = BACKEND_DIR / "processed_pdfs.txt"

# Canonical dataset file paths
CLEAN_DATA_PATH = DATA_DIR / "historical_cases_clean.csv"
RAW_DATA_PATH = DATA_DIR / "historical_cases_raw.csv"
ADJACENCY_PATH = DATA_DIR / "district_adjacency.csv"
DISTRICT_ML_PATH = DATA_DIR / "district_ml_dataset.csv"
FINAL_ML_DATASET_PATH = DATA_DIR / "final_ml_dataset.csv"
GEOJSON_PATH = DATA_DIR / "india_states.geojson"

# Canonical model and encoder paths
RF_DISTRICT_MODEL_PATH = MODEL_DIR / "rf_district_model.pkl"
DISTRICT_ENCODERS_PATH = MODEL_DIR / "district_encoders.pkl"
RF_SPATIAL_MODEL_PATH = MODEL_DIR / "rf_spatial.pkl"
LABEL_ENCODER_PATH = MODEL_DIR / "label_encoder.pkl"

# Frontend build directory (for optional unified single-service static deployment)
FRONTEND_BUILD_DIR = WORKSPACE_DIR / "frontend" / "build"

# Server configuration
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# CORS configuration
# Defaults to permissive origins for seamless deployment, can be narrowed via comma-separated ALLOWED_ORIGINS env var
_allowed_env = os.getenv("ALLOWED_ORIGINS", "*")
if _allowed_env.strip() == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [origin.strip() for origin in _allowed_env.split(",") if origin.strip()]
