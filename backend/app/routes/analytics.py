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

from app.config import (
    ANOMALY_Z_CRITICAL,
    ANOMALY_Z_SEVERE,
    ANOMALY_Z_THRESHOLD,
    CFR_CRITICAL_PCT,
    CFR_HIGH_PCT,
    CO_OCCURRENCE_MIN_DISTRICTS,
)
from app.data_loader import filter_period, load_data_quality, load_historical_data

router = APIRouter(prefix="/api", tags=["Advanced Analytics"])


# ─── 1. SEASONAL TREND CHART ────────────────────────────────────────────────
@router.get("/trends")
def get_trends(disease: Optional[str] = None, state: Optional[str] = None, district: Optional[str] = None):
    """
    Returns monthly aggregated case counts for trend/seasonal chart visualization.
    """
    df = load_historical_data()
    if df.empty:
        return {"trends": []}

    filtered = df
    if disease:
        filtered = filtered[filtered['Disease'].str.lower() == disease.lower()]
    if state:
        filtered = filtered[filtered['State'].str.lower() == state.lower()]
    if district:
        filtered = filtered[filtered['District'].str.lower() == district.lower()]

    monthly = filtered.assign(YearMonth=filtered['WeekStart'].dt.to_period('M').astype(str)).groupby('YearMonth').agg(
        Cases=('Cases', 'sum'),
        Deaths=('Deaths', 'sum'),
        Outbreaks=('Cases', 'size'),
    )

    # Months are listed across the whole span with the number of bulletins we
    # hold for each: a month without bulletins is unknown (null), not zero
    quality = load_data_quality() or {}
    weeks = quality.get("coverage", {}).get("bulletin_weeks", [])
    bulletins = {}
    for label in weeks:
        month = pd.Timestamp.fromisocalendar(int(label[:4]), int(label[6:]), 1).strftime('%Y-%m')
        bulletins[month] = bulletins.get(month, 0) + 1

    trends = []
    if bulletins:
        for period in pd.period_range(min(bulletins), max(bulletins), freq='M'):
            month = str(period)
            covered = bulletins.get(month, 0)
            row = monthly.loc[month] if month in monthly.index else None
            trends.append({
                "YearMonth": month,
                "Bulletins": covered,
                "Cases": (int(row['Cases']) if row is not None else 0) if covered else None,
                "Deaths": (int(row['Deaths']) if row is not None else 0) if covered else None,
                "Outbreaks": (int(row['Outbreaks']) if row is not None else 0) if covered else None,
            })

    return {
        "trends": trends,
        "total_months": len(trends),
        "months_without_data": sum(1 for t in trends if not t["Bulletins"]),
    }


# ─── 2. ANOMALY DETECTION ───────────────────────────────────────────────────
@router.get("/anomalies")
def get_anomalies(disease: Optional[str] = None, year: Optional[int] = None, weeks: Optional[int] = None):
    """
    Detect districts with statistically abnormal case counts using Z-score.
    A district is flagged if its case count is more than ANOMALY_Z_THRESHOLD standard deviations above the mean.
    """
    df = load_historical_data()
    if df.empty:
        return {"anomalies": []}

    filtered = df.copy()

    if disease:
        filtered = filtered[filtered['Disease'].str.lower() == disease.lower()]
    filtered = filter_period(filtered, year=year, weeks=weeks)

    grouped = filtered.groupby(['State', 'District']).agg(
        Cases=('Cases', 'sum')
    ).reset_index()

    if grouped.empty or grouped['Cases'].std() == 0:
        return {"anomalies": [], "message": "Not enough data for anomaly detection"}

    mean_cases = grouped['Cases'].mean()
    std_cases = grouped['Cases'].std()

    grouped['z_score'] = ((grouped['Cases'] - mean_cases) / std_cases).round(2)
    grouped['is_anomaly'] = grouped['z_score'] > ANOMALY_Z_THRESHOLD

    anomalies = grouped[grouped['is_anomaly']].sort_values('z_score', ascending=False)

    def severity(z):
        if z > ANOMALY_Z_CRITICAL: return "Critical"
        if z > ANOMALY_Z_SEVERE: return "Severe"
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
def get_co_occurrence(year: Optional[int] = None, weeks: Optional[int] = None):
    """
    Returns a correlation matrix showing which diseases tend to appear together
    in the same districts. Uses Pearson correlation on district-level case counts.
    """
    df = load_historical_data()
    if df.empty:
        return {"matrix": [], "diseases": []}

    filtered = df.copy()

    filtered = filter_period(filtered, year=year, weeks=weeks)

    pivot = filtered.pivot_table(
        index=['State', 'District'],
        columns='Disease',
        values='Cases',
        aggfunc='sum',
        fill_value=0
    )

    # Only keep diseases seen in at least CO_OCCURRENCE_MIN_DISTRICTS districts
    valid_cols = pivot.columns[pivot.gt(0).sum() >= CO_OCCURRENCE_MIN_DISTRICTS]
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
def get_cfr(disease: Optional[str] = None, year: Optional[int] = None, weeks: Optional[int] = None):
    """
    Compute Case Fatality Rate (Deaths / Cases * 100) per district.
    """
    df = load_historical_data()
    if df.empty:
        return {"cfr_data": []}

    filtered = df.copy()

    if disease:
        filtered = filtered[filtered['Disease'].str.lower() == disease.lower()]
    filtered = filter_period(filtered, year=year, weeks=weeks)

    grouped = filtered.groupby(['State', 'District']).agg(
        Cases=('Cases', 'sum'),
        Deaths=('Deaths', 'sum')
    ).reset_index()

    # Only include districts with at least 1 case
    grouped = grouped[grouped['Cases'] > 0]
    grouped['cfr'] = (grouped['Deaths'] / grouped['Cases'] * 100).round(2)

    def cfr_severity(rate):
        if rate > CFR_CRITICAL_PCT: return "Critical"
        if rate > CFR_HIGH_PCT: return "High"
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
    df = load_historical_data()
    if df.empty:
        return {"detail": {}}

    d_data = df[
        (df['State'].str.lower() == state.lower()) &
        (df['District'].str.lower() == district.lower())
    ].copy()

    if d_data.empty:
        return {"detail": {}, "message": "No data found for this district"}

    # Disease breakdown
    disease_breakdown = d_data.groupby('Disease').agg(
        Cases=('Cases', 'sum'),
        Deaths=('Deaths', 'sum')
    ).reset_index().sort_values('Cases', ascending=False).to_dict(orient='records')

    # Monthly trend
    d_data['YearMonth'] = d_data['WeekStart'].dt.to_period('M').astype(str)
    monthly = d_data.groupby('YearMonth').agg(
        Cases=('Cases', 'sum'),
        Deaths=('Deaths', 'sum')
    ).reset_index().sort_values('YearMonth').to_dict(orient='records')

    recent = d_data.sort_values('WeekStart', ascending=False).head(8)
    recent_outbreaks = [{
        "week_start": r.WeekStart.strftime('%Y-%m-%d'), "disease": r.Disease, "cases": int(r.Cases),
        "deaths": int(r.Deaths), "status": r.Status if isinstance(r.Status, str) else "", "outbreak_id": r.OutbreakID,
    } for r in recent.itertuples()]

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
            "recent_outbreaks": recent_outbreaks,
            "first_week": d_data['WeekStart'].min().strftime('%Y-%m-%d'),
            "latest_week": d_data['WeekStart'].max().strftime('%Y-%m-%d'),
            "data_points": len(d_data)
        }
    }
