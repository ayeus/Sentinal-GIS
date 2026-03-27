from fastapi import APIRouter
from typing import Optional
import pandas as pd
from app.data_loader import load_historical_data

router = APIRouter(prefix="/api", tags=["Current Status"])

# Load historical data into memory mapping
df = load_historical_data()

@router.get("/years")
def get_available_years():
    """Return the list of years for which historical data exists."""
    if df.empty:
        return {"years": []}
    years = sorted(df['Date'].dt.year.unique().tolist())
    return {"years": years}

@router.get("/diseases")
def get_available_diseases():
    """Return a list of all unique diseases available in the historical dataset"""
    if df.empty:
        return {"diseases": []}
    
    unique_diseases = sorted([str(d) for d in df['Disease'].unique() if pd.notna(d)])
    return {"diseases": unique_diseases}


@router.get("/current-status")
def get_current_status(disease: Optional[str] = None, year: Optional[int] = None):
    """
    Return the total historical breakdown of a specific disease (or all) 
    grouped by State and District for mapping/choropleth functionality.
    """
    if df.empty:
        return {"data": [], "message": "No data available"}
        
    filtered = df.copy()
    
    if disease:
        filtered = filtered[filtered['Disease'].str.lower() == disease.lower()]
        
    if year:
        filtered = filtered[filtered['Date'].dt.year == year]
        
    # Standardize types and sum cases/deaths per district
    # Fill NA to zero before sum
    filtered['Cases'] = pd.to_numeric(filtered['Cases'], errors='coerce').fillna(0)
    filtered['Deaths'] = pd.to_numeric(filtered['Deaths'], errors='coerce').fillna(0)
    
    grouped = filtered.groupby(['State', 'District']).agg(
        {'Cases': 'sum', 'Deaths': 'sum'}
    ).reset_index()
    
    # Map Cases to 'Risk' levels for seamless MapView integration
    def get_risk(c):
        if c > 100: return "High"
        if c > 20: return "Medium"
        if c > 0: return "Low"
        return None

    def get_confidence(c):
        """
        Compute a meaningful confidence score (0.5–1.0) based on how strongly
        the case count falls within its risk tier.
        - High (>100): 0.50 at 101 cases, scaling toward 0.95 at 500+ cases.
        - Medium (21–100): 0.50 at 21 cases, 0.90 at 100 cases.
        - Low (1–20):  0.50 at 1 case, 0.90 at 20 cases.
        """
        import math
        if c > 100:
            # Logistic-like scale: saturates quickly after 300 cases
            return round(min(0.98, 0.50 + 0.48 * (1 - math.exp(-c / 180))), 2)
        elif c > 20:
            return round(0.50 + 0.40 * ((c - 20) / 80), 2)
        elif c > 0:
            return round(0.50 + 0.40 * (c / 20), 2)
        return 0.0
        
    grouped['risk'] = grouped['Cases'].apply(get_risk)
    grouped['confidence'] = grouped['Cases'].apply(get_confidence)
    
    results = grouped.to_dict(orient='records')
    top_districts = grouped.sort_values(by='Cases', ascending=False).head(5).to_dict(orient='records')
    
    return {
        "status": "success",
        "total_cases": int(grouped['Cases'].sum()),
        "total_deaths": int(grouped['Deaths'].sum()),
        "top_hotspots": top_districts,
        "region_data": results
    }
