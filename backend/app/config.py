"""
Central configuration for the SentinelGIS backend.

Every tunable value lives here and can be overridden with an environment
variable of the same name, so nothing else in the codebase needs a literal
path, URL, threshold or interval.
"""
import json
import os
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    return Path(raw).expanduser().resolve() if raw else default


# ─── Directories ────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BACKEND_DIR.parent

DATA_DIR = _env_path("SENTINEL_DATA_DIR", BACKEND_DIR / "data")
MODEL_DIR = _env_path("SENTINEL_MODEL_DIR", BACKEND_DIR / "model")
PDF_DIR = _env_path("SENTINEL_PDF_DIR", BACKEND_DIR / "idsp_pdfs")
PROCESSED_PDFS_FILE = _env_path("SENTINEL_PROCESSED_PDFS_FILE", BACKEND_DIR / "processed_pdfs.txt")
PIPELINE_LOCK_FILE = _env_path("SENTINEL_PIPELINE_LOCK_FILE", DATA_DIR / ".pipeline.lock")

# Canonical dataset file paths
CLEAN_DATA_PATH = DATA_DIR / "historical_cases_clean.csv"
RAW_DATA_PATH = DATA_DIR / "historical_cases_raw.csv"
ADJACENCY_PATH = DATA_DIR / "district_adjacency.csv"
DISTRICT_GAZETTEER_PATH = DATA_DIR / "districts.csv"
DATA_QUALITY_PATH = DATA_DIR / "data_quality.json"
SCRAPE_STATUS_PATH = DATA_DIR / "scrape_status.json"


# Frontend assets (build dir for unified single-service deployment, district map for adjacency)
FRONTEND_DIR = _env_path("SENTINEL_FRONTEND_DIR", WORKSPACE_DIR / "frontend")
FRONTEND_BUILD_DIR = FRONTEND_DIR / "build"
DISTRICT_GEOJSON_PATH = _env_path("SENTINEL_DISTRICT_GEOJSON", FRONTEND_DIR / "public" / "india_districts.geojson")
STATE_GEOJSON_PATH = _env_path("SENTINEL_STATE_GEOJSON", FRONTEND_DIR / "public" / "data" / "india_states_full.geojson")
# Boundary source used by build_boundaries.py ({level} = ADM1 for states, ADM2 for districts)
BOUNDARY_API_URL = os.getenv("BOUNDARY_API_URL", "https://www.geoboundaries.org/api/current/gbOpen/IND/{level}/")
BOUNDARY_CACHE_DIR = _env_path("BOUNDARY_CACHE_DIR", WORKSPACE_DIR / "data" / "raw" / "boundaries")
# Property keys holding the state / district names in the district GeoJSON
GEOJSON_STATE_KEY = os.getenv("GEOJSON_STATE_KEY", "NAME_1")
GEOJSON_DISTRICT_KEY = os.getenv("GEOJSON_DISTRICT_KEY", "NAME_2")

# ─── Server ─────────────────────────────────────────────────────────────────
PORT = _env_int("PORT", 8000)
HOST = os.getenv("HOST", "0.0.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# CORS configuration
# Defaults to permissive origins for seamless deployment, can be narrowed via comma-separated ALLOWED_ORIGINS env var
_allowed_env = os.getenv("ALLOWED_ORIGINS", "*")
if _allowed_env.strip() == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [origin.strip() for origin in _allowed_env.split(",") if origin.strip()]

# Admin endpoints (PDF upload, pipeline trigger). When ADMIN_API_KEY is set,
# callers must send it in the X-API-Key header; when empty the endpoints stay open.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()
MAX_UPLOAD_MB = _env_int("MAX_UPLOAD_MB", 25)

# ─── Reported burden bands (cases reported per district in the selected period) ─
# Descriptive only: these bands summarise what was reported, they are not predictions.
RISK_HIGH_CASES = _env_int("RISK_HIGH_CASES", 100)
RISK_MEDIUM_CASES = _env_int("RISK_MEDIUM_CASES", 20)
TOP_HOTSPOTS = _env_int("TOP_HOTSPOTS", 5)
# Default look-back of the "latest weeks" views, counted back from the newest bulletin
RECENT_WEEKS_DEFAULT = _env_int("RECENT_WEEKS_DEFAULT", 12)
# Data older than this many days is flagged as stale everywhere in the UI
DATA_STALE_AFTER_DAYS = _env_int("DATA_STALE_AFTER_DAYS", 21)

# Spread vectors (origin district case counts)
SPREAD_MIN_CASES = _env_int("SPREAD_MIN_CASES", 5)
SPREAD_HIGH_CASES = _env_int("SPREAD_HIGH_CASES", 100)
SPREAD_MEDIUM_CASES = _env_int("SPREAD_MEDIUM_CASES", 15)

# Analytics
ANOMALY_Z_THRESHOLD = _env_float("ANOMALY_Z_THRESHOLD", 1.5)
ANOMALY_Z_SEVERE = _env_float("ANOMALY_Z_SEVERE", 2.0)
ANOMALY_Z_CRITICAL = _env_float("ANOMALY_Z_CRITICAL", 3.0)
CFR_CRITICAL_PCT = _env_float("CFR_CRITICAL_PCT", 5.0)
CFR_HIGH_PCT = _env_float("CFR_HIGH_PCT", 2.0)
CO_OCCURRENCE_MIN_DISTRICTS = _env_int("CO_OCCURRENCE_MIN_DISTRICTS", 3)

# ─── Outbreak forecasting ───────────────────────────────────────────────────
# P(at least one outbreak of a disease is reported in a district within the horizon)
FORECAST_HORIZON_WEEKS = _env_int("FORECAST_HORIZON_WEEKS", 4)
# Diseases with fewer reported outbreaks than this are not modelled (too little signal)
FORECAST_MIN_DISEASE_OUTBREAKS = _env_int("FORECAST_MIN_DISEASE_OUTBREAKS", 80)
# Risk tiers by forecast probability, highest first; anything below the last is "Minimal"
FORECAST_TIERS = [
    ("High", _env_float("FORECAST_TIER_HIGH", 0.20)),
    ("Medium", _env_float("FORECAST_TIER_MEDIUM", 0.08)),
    ("Low", _env_float("FORECAST_TIER_LOW", 0.03)),
]
# Weeks of the most recent labelled data held out for the final, untouched evaluation
FORECAST_HOLDOUT_WEEKS = _env_int("FORECAST_HOLDOUT_WEEKS", 16)
FORECAST_RANDOM_STATE = _env_int("FORECAST_RANDOM_STATE", 42)
FORECAST_MODEL_PATH = MODEL_DIR / "outbreak_forecaster.pkl"
FORECAST_OUTPUT_PATH = DATA_DIR / "forecast_latest.csv"
MODEL_CARD_PATH = DATA_DIR / "model_card.json"

# ─── Ingestion pipeline ─────────────────────────────────────────────────────
ENABLE_SCHEDULER = _env_bool("ENABLE_SCHEDULER", True)
PDF_WATCH_INTERVAL_SECONDS = _env_int("PDF_WATCH_INTERVAL_SECONDS", 60)
# Bulletins are weekly but published irregularly, so the portal is checked every day
SCRAPE_CRON_DAY_OF_WEEK = os.getenv("SCRAPE_CRON_DAY_OF_WEEK", "*")
SCRAPE_CRON_HOUR = _env_int("SCRAPE_CRON_HOUR", 2)
SCRAPE_CRON_MINUTE = _env_int("SCRAPE_CRON_MINUTE", 0)
STARTUP_CHECK_DELAY_SECONDS = _env_int("STARTUP_CHECK_DELAY_SECONDS", 30)
# Interval used by the standalone realtime_pipeline.py loop
REALTIME_LOOP_SECONDS = _env_int("REALTIME_LOOP_SECONDS", 1800)

IDSP_BULLETIN_URL = os.getenv(
    "IDSP_BULLETIN_URL",
    "https://idsp.mohfw.gov.in/index4.php?lang=1&level=0&linkid=406&lid=3689",
)
SCRAPER_MAX_DOCUMENTS = _env_int("SCRAPER_MAX_DOCUMENTS", 400)
SCRAPER_TIMEOUT_SECONDS = _env_int("SCRAPER_TIMEOUT_SECONDS", 15)
SCRAPER_DELAY_SECONDS = _env_float("SCRAPER_DELAY_SECONDS", 1.0)

# ─── Real-time news intelligence ────────────────────────────────────────────
# Feeds, gazetteer, keyword lists, severity bands and advisories are data, not
# code: edit the JSON file (or point REALTIME_CONFIG_PATH at another one).
DISTRICT_ALIASES_PATH = _env_path("DISTRICT_ALIASES_PATH", BACKEND_DIR / "app" / "resources" / "district_aliases.json")
REALTIME_CONFIG_PATH = _env_path("REALTIME_CONFIG_PATH", BACKEND_DIR / "app" / "resources" / "realtime.json")
LIVE_FEED_CACHE_SECONDS = _env_int("LIVE_FEED_CACHE_SECONDS", 300)
LIVE_FEED_TIMEOUT_SECONDS = _env_int("LIVE_FEED_TIMEOUT_SECONDS", 20)
# Items older than this are not "live" and are dropped
LIVE_MAX_AGE_DAYS = _env_int("LIVE_MAX_AGE_DAYS", 30)
LIVE_FEED_MAX_ENTRIES = _env_int("LIVE_FEED_MAX_ENTRIES", 40)
LIVE_MAX_ALERTS = _env_int("LIVE_MAX_ALERTS", 60)
LIVE_SUMMARY_MAX_CHARS = _env_int("LIVE_SUMMARY_MAX_CHARS", 200)


def load_realtime_config() -> dict:
    with open(REALTIME_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
