import json
import os
import threading
import time
from datetime import timedelta

import pandas as pd

from app.config import (
    ADJACENCY_PATH,
    CLEAN_DATA_PATH,
    DATA_QUALITY_PATH,
    SCRAPE_STATUS_PATH,
    FORECAST_OUTPUT_PATH,
    MODEL_CARD_PATH,
)

# Global caches for hot-reload, keyed by file path -> (mtime, object)
_CACHE = {}
_CACHE_LOCK = threading.Lock()

HISTORICAL_COLUMNS = ['Date', 'State', 'District', 'Disease', 'Cases', 'Deaths', 'WeekStart']


def _load_cached(path, loader, label):
    """Return the cached object for `path`, re-reading it whenever the file changes on disk."""
    current_mtime = os.path.getmtime(path)
    with _CACHE_LOCK:
        cached = _CACHE.get(path)
        if cached is None or current_mtime != cached[0]:
            _CACHE[path] = (current_mtime, loader(path))
            print(f"[{time.strftime('%H:%M:%S')}] {label} hot-reloaded from disk.")
        return _CACHE[path][1]


def _read_historical(path):
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df['WeekStart'] = pd.to_datetime(df['WeekStart'], errors='coerce')
    df['Cases'] = pd.to_numeric(df['Cases'], errors='coerce').fillna(0).astype(int)
    df['Deaths'] = pd.to_numeric(df['Deaths'], errors='coerce').fillna(0).astype(int)
    return df


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_historical_data():
    """
    Load the cleaned outbreak table with HOT-RELOAD support.
    Checks file modification time before returning cached data, so call this
    per request (never at import time) to see data added by the pipeline.
    The returned frame is shared: copy before mutating.
    """
    if not CLEAN_DATA_PATH.exists():
        return pd.DataFrame(columns=HISTORICAL_COLUMNS)
    return _load_cached(CLEAN_DATA_PATH, _read_historical, "Outbreak data")


def filter_period(df, year=None, weeks=None):
    """
    Restrict outbreaks to a calendar year (by outbreak start date) or to the
    latest `weeks` reporting weeks, counted back from the newest bulletin.
    """
    if weeks and not df.empty:
        cutoff = df['WeekStart'].max() - timedelta(weeks=int(weeks) - 1)
        return df[df['WeekStart'] >= cutoff]
    if year:
        return df[df['Date'].dt.year == int(year)]
    return df


def load_adjacency():
    """District adjacency table (hot-reloaded, shared: copy before mutating). None if missing."""
    if not ADJACENCY_PATH.exists():
        return None
    return _load_cached(ADJACENCY_PATH, pd.read_csv, "Adjacency")


def load_forecast():
    """Latest forecast table written by the trainer. None until a model has been trained."""
    if not FORECAST_OUTPUT_PATH.exists():
        return None
    return _load_cached(FORECAST_OUTPUT_PATH, pd.read_csv, "Forecast")


def load_model_card():
    if not MODEL_CARD_PATH.exists():
        return None
    return _load_cached(MODEL_CARD_PATH, _read_json, "Model card")


def load_data_quality():
    if not DATA_QUALITY_PATH.exists():
        return None
    return _load_cached(DATA_QUALITY_PATH, _read_json, "Data quality report")


def load_scrape_status():
    """Outcome of the last automatic check of the IDSP portal, or None if it never ran."""
    if not SCRAPE_STATUS_PATH.exists():
        return None
    return _load_cached(SCRAPE_STATUS_PATH, _read_json, "Scrape status")
