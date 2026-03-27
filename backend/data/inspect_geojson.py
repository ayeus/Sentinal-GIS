import json
import os

GEOJSON_PATH = '/Users/aayushnmadeo/Documents/SentinalGIS/frontend/public/india_districts.geojson'

def inspect_geojson():
    if not os.path.exists(GEOJSON_PATH):
        print(f"GeoJSON not found at {GEOJSON_PATH}")
        return

    print("Loading GeoJSON...")
    with open(GEOJSON_PATH, 'r') as f:
        data = json.load(f)
        
    features = data.get('features', [])
    print(f"Loaded {len(features)} features (districts).")
    
    if features:
        props = features[0].get('properties', {})
        print("Property keys:", list(props.keys()))
        print("Sample properties:")
        for k, v in props.items():
            print(f"  {k}: {v}")

if __name__ == '__main__':
    inspect_geojson()
