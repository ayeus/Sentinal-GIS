"""
Advanced Analytics API endpoints for SentinelGIS Phase 3.
- /api/trends: Monthly disease trend data for seasonal charts
- /api/anomalies: Flag districts with statistically abnormal case counts
- /api/co-occurrence: Disease correlation matrix across districts
- /api/cfr: Case Fatality Rate per district
"""
from fastapi import APIRouter
from typing import Optional
import pandas as pd
import numpy as np
from app.data_loader import load_historical_data

router = APIRouter(prefix="/api", tags=["Advanced Analytics"])

df = load_historical_data()


# ─── 1. SEASONAL TREND CHART ────────────────────────────────────────────────
@router.get("/trends")
def get_trends(disease: Optional[str] = None, state: Optional[str] = None, district: Optional[str] = None):
    """
    Returns monthly aggregated case counts for trend/seasonal chart visualization.
    """
    if df.empty:
        return {"trends": []}

    filtered = df.copy()
    if disease:
        filtered = filtered[filtered['Disease'].str.lower() == disease.lower()]
    if state:
        filtered = filtered[filtered['State'].str.lower() == state.lower()]
    if district:
        filtered = filtered[filtered['District'].str.lower() == district.lower()]

    filtered['YearMonth'] = filtered['Date'].dt.to_period('M').astype(str)
    filtered['Cases'] = pd.to_numeric(filtered['Cases'], errors='coerce').fillna(0)
    filtered['Deaths'] = pd.to_numeric(filtered['Deaths'], errors='coerce').fillna(0)

    monthly = filtered.groupby('YearMonth').agg(
        Cases=('Cases', 'sum'),
        Deaths=('Deaths', 'sum')
    ).reset_index()

    monthly = monthly.sort_values('YearMonth')

    return {
        "trends": monthly.to_dict(orient='records'),
        "total_months": len(monthly)
    }


# ─── 2. ANOMALY DETECTION ───────────────────────────────────────────────────
@router.get("/anomalies")
def get_anomalies(disease: Optional[str] = None, year: Optional[int] = None):
    """
    Detect districts with statistically abnormal case counts using Z-score.
    A district is flagged if its case count is >1.5 standard deviations above the mean.
    """
    if df.empty:
        return {"anomalies": []}

    filtered = df.copy()
    filtered['Cases'] = pd.to_numeric(filtered['Cases'], errors='coerce').fillna(0)

    if disease:
        filtered = filtered[filtered['Disease'].str.lower() == disease.lower()]
    if year:
        filtered = filtered[filtered['Date'].dt.year == year]

    grouped = filtered.groupby(['State', 'District']).agg(
        Cases=('Cases', 'sum')
    ).reset_index()

    if grouped.empty or grouped['Cases'].std() == 0:
        return {"anomalies": [], "message": "Not enough data for anomaly detection"}

    mean_cases = grouped['Cases'].mean()
    std_cases = grouped['Cases'].std()

    grouped['z_score'] = ((grouped['Cases'] - mean_cases) / std_cases).round(2)
    grouped['is_anomaly'] = grouped['z_score'] > 1.5

    anomalies = grouped[grouped['is_anomaly']].sort_values('z_score', ascending=False)

    def severity(z):
        if z > 3.0: return "Critical"
        if z > 2.0: return "Severe"
        return "Warning"

    anomalies['severity'] = anomalies['z_score'].apply(severity)

    return {
        "anomalies": anomalies[['State', 'District', 'Cases', 'z_score', 'severity']].to_dict(orient='records'),
        "mean_cases": round(mean_cases, 1),
        "std_cases": round(std_cases, 1),
        "total_flagged": len(anomalies)
    }


# ─── 3. DISEASE CO-OCCURRENCE ───────────────────────────────────────────────
@router.get("/co-occurrence")
def get_co_occurrence(year: Optional[int] = None):
    """
    Returns a correlation matrix showing which diseases tend to appear together
    in the same districts. Uses Pearson correlation on district-level case counts.
    """
    if df.empty:
        return {"matrix": [], "diseases": []}

    filtered = df.copy()
    filtered['Cases'] = pd.to_numeric(filtered['Cases'], errors='coerce').fillna(0)

    if year:
        filtered = filtered[filtered['Date'].dt.year == year]

    pivot = filtered.pivot_table(
        index=['State', 'District'],
        columns='Disease',
        values='Cases',
        aggfunc='sum',
        fill_value=0
    )

    # Only keep diseases with at least 3 district occurrences
    valid_cols = pivot.columns[pivot.gt(0).sum() >= 3]
    pivot = pivot[valid_cols]

    if pivot.empty or len(valid_cols) < 2:
        return {"matrix": [], "diseases": [], "message": "Not enough disease variety for correlation"}

    corr = pivot.corr().round(2)

    diseases = corr.columns.tolist()
    matrix = []
    for d1 in diseases:
        for d2 in diseases:
            matrix.append({
                "disease1": d1,
                "disease2": d2,
                "correlation": float(corr.loc[d1, d2])
            })

    return {
        "diseases": diseases,
        "matrix": matrix
    }


# ─── 4. CASE FATALITY RATE ──────────────────────────────────────────────────
@router.get("/cfr")
def get_cfr(disease: Optional[str] = None, year: Optional[int] = None):
    """
    Compute Case Fatality Rate (Deaths / Cases * 100) per district.
    """
    if df.empty:
        return {"cfr_data": []}

    filtered = df.copy()
    filtered['Cases'] = pd.to_numeric(filtered['Cases'], errors='coerce').fillna(0)
    filtered['Deaths'] = pd.to_numeric(filtered['Deaths'], errors='coerce').fillna(0)

    if disease:
        filtered = filtered[filtered['Disease'].str.lower() == disease.lower()]
    if year:
        filtered = filtered[filtered['Date'].dt.year == year]

    grouped = filtered.groupby(['State', 'District']).agg(
        Cases=('Cases', 'sum'),
        Deaths=('Deaths', 'sum')
    ).reset_index()

    # Only include districts with at least 1 case
    grouped = grouped[grouped['Cases'] > 0]
    grouped['cfr'] = (grouped['Deaths'] / grouped['Cases'] * 100).round(2)

    def cfr_severity(rate):
        if rate > 5: return "Critical"
        if rate > 2: return "High"
        if rate > 0: return "Moderate"
        return "None"

    grouped['severity'] = grouped['cfr'].apply(cfr_severity)

    return {
        "cfr_data": grouped[['State', 'District', 'Cases', 'Deaths', 'cfr', 'severity']].to_dict(orient='records'),
        "avg_cfr": round(grouped['cfr'].mean(), 2) if not grouped.empty else 0
    }


# ─── 5. DISTRICT DETAIL (for click panel) ───────────────────────────────────
@router.get("/district-detail")
def get_district_detail(state: str, district: str):
    """
    Full breakdown for a single district: monthly trends, all diseases, top stats.
    """
    if df.empty:
        return {"detail": {}}

    filtered = df.copy()
    filtered['Cases'] = pd.to_numeric(filtered['Cases'], errors='coerce').fillna(0)
    filtered['Deaths'] = pd.to_numeric(filtered['Deaths'], errors='coerce').fillna(0)

    d_data = filtered[
        (filtered['State'].str.lower() == state.lower()) &
        (filtered['District'].str.lower() == district.lower())
    ]

    if d_data.empty:
        return {"detail": {}, "message": "No data found for this district"}

    # Disease breakdown
    disease_breakdown = d_data.groupby('Disease').agg(
        Cases=('Cases', 'sum'),
        Deaths=('Deaths', 'sum')
    ).reset_index().sort_values('Cases', ascending=False).to_dict(orient='records')

    # Monthly trend
    d_data['YearMonth'] = d_data['Date'].dt.to_period('M').astype(str)
    monthly = d_data.groupby('YearMonth').agg(
        Cases=('Cases', 'sum'),
        Deaths=('Deaths', 'sum')
    ).reset_index().sort_values('YearMonth').to_dict(orient='records')

    total_cases = int(d_data['Cases'].sum())
    total_deaths = int(d_data['Deaths'].sum())
    cfr = round(total_deaths / total_cases * 100, 2) if total_cases > 0 else 0

    return {
        "detail": {
            "state": state,
            "district": district,
            "total_cases": total_cases,
            "total_deaths": total_deaths,
            "cfr": cfr,
            "disease_breakdown": disease_breakdown,
            "monthly_trend": monthly,
            "data_points": len(d_data)
        }
    }
