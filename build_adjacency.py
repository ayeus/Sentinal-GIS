"""
Computes a district adjacency matrix from the India Districts GeoJSON.
Two districts are considered adjacent if their boundaries share an edge or a point (touching polygons).
Saves the result as data/district_adjacency.csv.
"""
import json
import csv
from shapely.geometry import shape

GEOJSON_PATH = "frontend/public/india_districts.geojson"
OUTPUT_PATH = "backend/data/district_adjacency.csv"

def build_adjacency():
    print("Loading GeoJSON...")
    with open(GEOJSON_PATH, "r") as f:
        data = json.load(f)

    features = data["features"]
    print(f"Loaded {len(features)} district features. Building adjacency...")

    # Build geometry + name index
    districts = []
    for feat in features:
        geom = shape(feat["geometry"])
        name = feat["properties"].get("NAME_2", "").strip().title()
        state = feat["properties"].get("NAME_1", "").strip().title()
        centroid = geom.centroid
        districts.append({
            "name": name,
            "state": state,
            "geom": geom,
            "lat": centroid.y,
            "lon": centroid.x
        })

    print("Computing pairwise adjacency (touching boundaries)...")
    adjacency = []
    n = len(districts)
    
    for i in range(n):
        for j in range(i + 1, n):
            try:
                if districts[i]["geom"].touches(districts[j]["geom"]):
                    adjacency.append({
                        "origin_district": districts[i]["name"],
                        "origin_state": districts[i]["state"],
                        "origin_lat": districts[i]["lat"],
                        "origin_lon": districts[i]["lon"],
                        "dest_district": districts[j]["name"],
                        "dest_state": districts[j]["state"],
                        "dest_lat": districts[j]["lat"],
                        "dest_lon": districts[j]["lon"],
                    })
            except Exception:
                continue  # Skip invalid geometries

    print(f"Found {len(adjacency)} adjacent district pairs.")
    
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "origin_district", "origin_state", "origin_lat", "origin_lon",
            "dest_district", "dest_state", "dest_lat", "dest_lon"
        ])
        writer.writeheader()
        writer.writerows(adjacency)
    
    print(f"Saved adjacency matrix to {OUTPUT_PATH}")

if __name__ == "__main__":
    build_adjacency()
