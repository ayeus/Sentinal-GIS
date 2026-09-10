import json
import os
import time
from pathlib import Path
import pandas as pd

# Global cache for hot-reload
_DATA_CACHE = {
    "df": None,
    "last_mtime": 0
}

from app.config import GEOJSON_PATH, CLEAN_DATA_PATH

def load_geojson():
    """
    Load India states GeoJSON for frontend mapping
    """
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(f"GeoJSON not found at {GEOJSON_PATH}")

    with open(GEOJSON_PATH, "r") as f:
        geojson = json.load(f)

    return geojson

def load_historical_data():
    """
    Load the cleaned historical outbreak data with HOT-RELOAD support.
    Checks file modification time before returning cached data.
    """
    global _DATA_CACHE
    
    if not CLEAN_DATA_PATH.exists():
        return pd.DataFrame(columns=['Date', 'State', 'District', 'Disease', 'Cases', 'Deaths'])
        
    current_mtime = os.path.getmtime(CLEAN_DATA_PATH)
    
    # Reload if first time or file has changed
    if _DATA_CACHE["df"] is None or current_mtime > _DATA_CACHE["last_mtime"]:
        df = pd.read_csv(CLEAN_DATA_PATH)
        df['Date'] = pd.to_datetime(df['Date'])
        _DATA_CACHE["df"] = df
        _DATA_CACHE["last_mtime"] = current_mtime
        print(f"[{time.strftime('%H:%M:%S')}] Data hot-reloaded from CSV.")
        
    return _DATA_CACHE["df"]
