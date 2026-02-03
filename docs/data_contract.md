# Data Contract (Draft)

## Core Modeling Table

Name: `panel_monthly` (Parquet)

Primary key: `district_id`, `month`

Columns:
- district_id: stable district identifier used across datasets (string)
- district_name: display name (string)
- state: fixed to Tamil Nadu (string)
- month: YYYY-MM (string)
- cases: dengue case count for the month (int)
- deaths: dengue deaths for the month (int, optional)
- population: district population (int, optional)
- climate_*: monthly climate variables (float, optional)
- centroid_lat: district centroid latitude (float)
- centroid_lon: district centroid longitude (float)

Derived features (computed, not stored in raw ingest):
- lag_1, lag_2, lag_3: cases lagged by 1–3 months
- seas_sin, seas_cos: seasonal Fourier terms
- neigh_lag_1: mean cases of neighboring districts (lagged)
- dist_to_hotspot: distance to current hotspot centroid (optional)

Targets:
- target_1m: cases at t+1
- target_3m: cases at t+3
- risk_label_1m: Low/Medium/High based on quantiles

## Raw Inputs

- Disease cases: district-week or district-month table
- Boundaries: district polygons (GeoJSON/Shapefile)
- Climate: gridded climate data, aggregated to district-month

## Alignment Rules

- All temporal data aggregated to month start (YYYY-MM)
- District naming reconciled via mapping table
- Spatial joins performed in EPSG:4326, area-weighted where needed
