from fastapi import APIRouter
from typing import Optional
import pandas as pd
import os

router = APIRouter(prefix="/api", tags=["Disease Spread"])

ADJACENCY_PATH = "data/district_adjacency.csv"
CLEAN_DATA_PATH = "data/historical_cases_clean.csv"

@router.get("/spread-risk")
def get_spread_risk(disease: Optional[str] = None, year: Optional[int] = None):
    """
    Returns spread vectors showing which districts are at risk of receiving
    a disease from an actively infected neighboring district.
    
    Response format:
    {
      "vectors": [
        {
          "origin_district": ..., "origin_state": ...,
          "origin_lat": ..., "origin_lon": ...,
          "dest_district": ..., "dest_state": ...,
          "dest_lat": ..., "dest_lon": ...,
          "origin_cases": ..., "spread_risk": "High|Medium|Low"
        }, ...
      ]
    }
    """
    if not os.path.exists(ADJACENCY_PATH):
        return {"vectors": [], "error": "Adjacency matrix not found. Run build_adjacency.py first."}

    if not os.path.exists(CLEAN_DATA_PATH):
        return {"vectors": [], "error": "Historical data not found."}

    adj = pd.read_csv(ADJACENCY_PATH)
    hist = pd.read_csv(CLEAN_DATA_PATH)
    hist['Date'] = pd.to_datetime(hist['Date'])

    # Filter by disease/year
    if disease:
        hist = hist[hist['Disease'].str.lower() == disease.lower()]
    if year:
        hist = hist[hist['Date'].dt.year == year]

    if hist.empty:
        return {"vectors": [], "message": f"No outbreaks found for {disease}/{year}"}

    # Sum all cases per district (the "source" of potential spread)
    # Normalize district names for joining
    def norm(s):
        return str(s).strip().title() if s else ""

    hist['District'] = hist['District'].apply(norm)
    hist['State'] = hist['State'].apply(norm)

    district_cases = hist.groupby(['State', 'District'])['Cases'].sum().reset_index()
    district_cases.columns = ['State', 'District', 'TotalCases']

    # Merge origin cases into adjacency table
    adj['origin_district'] = adj['origin_district'].apply(norm)
    adj['origin_state'] = adj['origin_state'].apply(norm)
    adj['dest_district'] = adj['dest_district'].apply(norm)
    adj['dest_state'] = adj['dest_state'].apply(norm)

    merged = adj.merge(
        district_cases,
        left_on=['origin_district', 'origin_state'],
        right_on=['District', 'State'],
        how='inner'
    )

    # Only generate spread vectors where source has a non-trivial outbreak
    merged = merged[merged['TotalCases'] > 5]

    if merged.empty:
        return {"vectors": [], "message": "No significant outbreaks to propagate spread from."}

    # Assign spread risk levels based on origin case count
    def spread_risk(cases):
        if cases > 100: return "High"
        if cases > 15: return "Medium"
        return "Low"

    merged['spread_risk'] = merged['TotalCases'].apply(spread_risk)
    merged['origin_cases'] = merged['TotalCases']

    vectors = merged[[
        'origin_district', 'origin_state', 'origin_lat', 'origin_lon',
        'dest_district', 'dest_state', 'dest_lat', 'dest_lon',
        'origin_cases', 'spread_risk'
    ]].to_dict(orient='records')

    return {
        "vectors": vectors,
        "total_vectors": len(vectors)
    }
