from fastapi import APIRouter
from typing import Optional

import pandas as pd

from app.config import SPREAD_MIN_CASES, load_realtime_config
from app.data_loader import filter_period, load_adjacency, load_historical_data
from app.services.risk import spread_risk

router = APIRouter(prefix="/api", tags=["Disease Spread"])

@router.get("/spread-risk")
def get_spread_risk(disease: Optional[str] = None, year: Optional[int] = None, weeks: Optional[int] = None):
    """
    Geographic exposure, not a prediction: for every district that reported an
    outbreak in the period, the districts that share a border with it. Only
    meaningful for diseases that can move between districts, so diseases
    listed as non-transmissible in app/resources/realtime.json are excluded.
    """
    adj = load_adjacency()
    if adj is None:
        return {"vectors": [], "error": "Adjacency matrix not found. Run build_adjacency.py first."}

    hist = load_historical_data()
    if hist.empty:
        return {"vectors": [], "error": "Historical data not found."}

    # The adjacency frame is a shared cache: work on a copy
    adj = adj.copy()

    non_transmissible = {d.lower() for d in load_realtime_config().get("non_transmissible_diseases", [])}
    if disease and disease.lower() in non_transmissible:
        return {"vectors": [], "applicable": False,
                "message": f"{disease} does not spread from district to district, so neighbouring districts are not at added risk."}

    # Filter by disease/period
    hist = filter_period(hist, year=year, weeks=weeks)
    if disease:
        hist = hist[hist['Disease'].str.lower() == disease.lower()]
    else:
        hist = hist[~hist['Disease'].str.lower().isin(non_transmissible)]

    if hist.empty:
        return {"vectors": [], "message": "No outbreaks of a transmissible disease were reported for these filters."}

    # Sum all cases per district (the "source" of potential spread). Outbreak
    # records and the adjacency table share the gazetteer's district names.
    district_cases = hist.groupby(['State', 'District'])['Cases'].sum().reset_index()
    district_cases.columns = ['State', 'District', 'TotalCases']

    # Adjacency is stored once per pair: both ends can be the source
    reverse = adj.rename(columns={
        'origin_district': 'dest_district', 'origin_state': 'dest_state', 'origin_lat': 'dest_lat', 'origin_lon': 'dest_lon',
        'dest_district': 'origin_district', 'dest_state': 'origin_state', 'dest_lat': 'origin_lat', 'dest_lon': 'origin_lon',
    })
    adj = pd.concat([adj, reverse], ignore_index=True)

    merged = adj.merge(
        district_cases,
        left_on=['origin_district', 'origin_state'],
        right_on=['District', 'State'],
        how='inner'
    )

    # Only generate spread vectors where source has a non-trivial outbreak
    merged = merged[merged['TotalCases'] > SPREAD_MIN_CASES]

    if merged.empty:
        return {"vectors": [], "message": "No significant outbreaks to propagate spread from."}

    # Assign spread risk levels based on origin case count
    merged['spread_risk'] = merged['TotalCases'].apply(spread_risk)
    merged['origin_cases'] = merged['TotalCases'].astype(int)
    merged = merged.sort_values('origin_cases', ascending=False)

    vectors = merged[[
        'origin_district', 'origin_state', 'origin_lat', 'origin_lon',
        'dest_district', 'dest_state', 'dest_lat', 'dest_lon',
        'origin_cases', 'spread_risk'
    ]].to_dict(orient='records')

    return {
        "vectors": vectors,
        "total_vectors": len(vectors)
    }
