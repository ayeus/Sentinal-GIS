"""
Builds the map layers and the district gazetteer from open boundary data.

Source: geoBoundaries (https://www.geoboundaries.org), gbOpen release
  - ADM2 districts: 2021 boundaries from the Local Government Directory, ODbL 1.0
  - ADM1 states/UTs: DataMeet India community, CC BY 2.5 IN

Outputs (paths from backend/app/config.py):
  frontend/public/india_districts.geojson     district polygons (NAME_1 = state, NAME_2 = district)
  frontend/public/data/india_states_full.geojson   state polygons (NAME_1)
  backend/data/districts.csv                  gazetteer: state, district, centroid
  backend/data/district_adjacency.csv         neighbouring district pairs

Run once, or again when district boundaries change:
    pip install shapely requests
    python build_boundaries.py
"""
import csv
import json
import sys
import unicodedata
from pathlib import Path

import requests
from shapely.geometry import mapping, shape
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.config import (
    ADJACENCY_PATH,
    BOUNDARY_API_URL,
    BOUNDARY_CACHE_DIR,
    DISTRICT_GAZETTEER_PATH,
    DISTRICT_GEOJSON_PATH,
    GEOJSON_DISTRICT_KEY,
    GEOJSON_STATE_KEY,
    STATE_GEOJSON_PATH,
)

# Simplified polygons leave slivers between neighbours, so "touching" is
# tested with a small tolerance (degrees; 0.02° is roughly 2 km)
ADJACENCY_TOLERANCE_DEG = 0.02
COORD_DECIMALS = 4  # ~11 m, plenty for a national choropleth


def ascii_name(name: str) -> str:
    """'Karnātaka' -> 'Karnataka' (the source uses transliteration diacritics)."""
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().strip()


def fetch_layer(level: str) -> dict:
    """Download (and cache) the simplified geoBoundaries layer for ADM1 / ADM2."""
    BOUNDARY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = BOUNDARY_CACHE_DIR / f"{level}.simplified.geojson"
    if not cached.exists():
        meta = requests.get(BOUNDARY_API_URL.format(level=level), timeout=60)
        meta.raise_for_status()
        meta = meta.json()
        print(f"Downloading {level}: {meta['boundarySource']} ({meta['boundaryYearRepresented']}, {meta['boundaryLicense']})")
        data = requests.get(meta["simplifiedGeometryGeoJSON"], timeout=300)
        data.raise_for_status()
        cached.write_bytes(data.content)
    with open(cached, "r", encoding="utf-8") as f:
        return json.load(f)


def _round(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], COORD_DECIMALS), round(coords[1], COORD_DECIMALS)]
    return [_round(c) for c in coords]


def _feature(geom, properties):
    geometry = mapping(geom)
    return {"type": "Feature", "properties": properties,
            "geometry": {"type": geometry["type"], "coordinates": _round(geometry["coordinates"])}}


def _write_geojson(path, features):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, separators=(",", ":"))
    print(f"Wrote {len(features)} features to {path} ({path.stat().st_size / 1e6:.1f} MB)")


def build():
    states = [(ascii_name(f["properties"]["shapeName"]), shape(f["geometry"]).buffer(0))
              for f in fetch_layer("ADM1")["features"]]
    state_geoms = [g for _, g in states]

    # The district layer carries no state attribute: place each district in the
    # state that contains most of it
    districts = []
    for f in fetch_layer("ADM2")["features"]:
        geom = shape(f["geometry"]).buffer(0)
        overlaps = [geom.intersection(sg).area for sg in state_geoms]
        if max(overlaps) > 0:
            state = states[overlaps.index(max(overlaps))][0]
        else:
            point = geom.representative_point()
            state = min(states, key=lambda s: s[1].distance(point))[0]
        centroid = geom.representative_point()
        districts.append({
            "state": state, "district": ascii_name(f["properties"]["shapeName"]),
            "geom": geom, "lat": round(centroid.y, 5), "lon": round(centroid.x, 5),
        })
    districts.sort(key=lambda d: (d["state"], d["district"]))

    _write_geojson(STATE_GEOJSON_PATH, [_feature(g, {GEOJSON_STATE_KEY: name}) for name, g in sorted(states, key=lambda s: s[0])])
    _write_geojson(DISTRICT_GEOJSON_PATH, [
        _feature(d["geom"], {GEOJSON_STATE_KEY: d["state"], GEOJSON_DISTRICT_KEY: d["district"]}) for d in districts
    ])

    with open(DISTRICT_GAZETTEER_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "district", "lat", "lon"])
        writer.writerows([d["state"], d["district"], d["lat"], d["lon"]] for d in districts)
    print(f"Wrote {len(districts)} districts to {DISTRICT_GAZETTEER_PATH}")

    print("Computing district adjacency...")
    geoms = [d["geom"] for d in districts]
    tree = STRtree(geoms)
    pairs = set()
    for i, geom in enumerate(geoms):
        for j in tree.query(geom.buffer(ADJACENCY_TOLERANCE_DEG), predicate="intersects"):
            if i != int(j):
                pairs.add((min(i, int(j)), max(i, int(j))))

    with open(ADJACENCY_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["origin_district", "origin_state", "origin_lat", "origin_lon",
                         "dest_district", "dest_state", "dest_lat", "dest_lon"])
        for i, j in sorted(pairs):
            a, b = districts[i], districts[j]
            writer.writerow([a["district"], a["state"], a["lat"], a["lon"],
                             b["district"], b["state"], b["lat"], b["lon"]])
    print(f"Wrote {len(pairs)} adjacent district pairs to {ADJACENCY_PATH}")


if __name__ == "__main__":
    build()
