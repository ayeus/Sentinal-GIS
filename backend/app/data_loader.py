import json
from pathlib import Path

def load_geojson():
    """
    Load India states GeoJSON for frontend mapping
    """
    geojson_path = Path("data/india_states.geojson")

    if not geojson_path.exists():
        raise FileNotFoundError(f"GeoJSON not found at {geojson_path}")

    with open(geojson_path, "r") as f:
        geojson = json.load(f)

    return geojson
