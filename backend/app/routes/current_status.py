from datetime import date
from fastapi import APIRouter
from typing import Optional
import pandas as pd
from app.config import (
    DATA_STALE_AFTER_DAYS,
    RECENT_WEEKS_DEFAULT,
    RISK_HIGH_CASES,
    RISK_MEDIUM_CASES,
    TOP_HOTSPOTS,
)
from app.data_loader import filter_period, load_data_quality, load_historical_data, load_model_card, load_scrape_status
from app.services.risk import categorize_risk

router = APIRouter(prefix="/api", tags=["Surveillance"])


@router.get("/years")
def get_available_years():
    """Return the list of years for which historical data exists."""
    df = load_historical_data()
    if df.empty:
        return {"years": []}
    years = sorted(df['Date'].dt.year.unique().tolist())
    return {"years": years, "recent_weeks_default": RECENT_WEEKS_DEFAULT}

@router.get("/diseases")
def get_available_diseases():
    """All diseases in the dataset, most reported first, and which of them the forecaster covers."""
    df = load_historical_data()
    if df.empty:
        return {"diseases": [], "modelled": []}

    counts = df['Disease'].value_counts()
    card = load_model_card() or {}
    return {
        "diseases": [str(d) for d in counts.index if pd.notna(d)],
        "outbreak_counts": {str(d): int(n) for d, n in counts.items()},
        "modelled": card.get("diseases_modelled", []),
    }


@router.get("/data-status")
def get_data_status():
    """
    How current and how complete the surveillance data is. Shown throughout
    the UI so nobody mistakes an old bulletin for the present situation.
    """
    df = load_historical_data()
    quality = load_data_quality()
    if df.empty or not quality:
        return {"available": False, "message": "No outbreak data has been ingested yet."}

    coverage = quality.get("coverage", {})
    latest_end = date.fromisoformat(coverage["latest_week_end"])
    age_days = (date.today() - latest_end).days
    return {
        "available": True,
        "source": "IDSP Weekly Outbreak Reports, Ministry of Health & Family Welfare, Government of India",
        "source_url": "https://idsp.mohfw.gov.in",
        "outbreaks": int(len(df)),
        "total_cases": int(df['Cases'].sum()),
        "total_deaths": int(df['Deaths'].sum()),
        "states": int(df['State'].nunique()),
        "districts": int(df.groupby(['State', 'District']).ngroups),
        "diseases": int(df['Disease'].nunique()),
        "first_week": coverage.get("first_week"),
        "latest_week": coverage.get("latest_week"),
        "latest_week_start": coverage.get("latest_week_start"),
        "latest_week_end": coverage.get("latest_week_end"),
        "data_age_days": age_days,
        "is_stale": age_days > DATA_STALE_AFTER_DAYS,
        "stale_after_days": DATA_STALE_AFTER_DAYS,
        "bulletins_ingested": coverage.get("bulletins_ingested"),
        "weeks_in_span": coverage.get("weeks_in_span"),
        "weeks_missing": coverage.get("weeks_missing"),
        "missing_weeks": coverage.get("missing_weeks", []),
        "bulletin_weeks": coverage.get("bulletin_weeks", []),
        "pdfs_on_disk": quality.get("pdfs_on_disk"),
        "pdfs_with_records": quality.get("pdfs_with_records"),
        "district_match": quality.get("district_match", {}),
        "unmatched_districts": quality.get("unmatched_districts", {}),
        "date_source": quality.get("date_source", {}),
        "generated_at": quality.get("generated_at"),
        "last_portal_check": load_scrape_status(),
        "burden_bands": {"high_above_cases": RISK_HIGH_CASES, "medium_above_cases": RISK_MEDIUM_CASES},
    }


@router.get("/current-status")
def get_current_status(disease: Optional[str] = None, year: Optional[int] = None, weeks: Optional[int] = None):
    """
    Reported outbreaks of a disease (or all) per district, for a calendar year
    or for the latest `weeks` reporting weeks. `risk` is a descriptive band of
    the reported case total (see /api/data-status burden_bands), not a prediction.
    """
    df = load_historical_data()
    if df.empty:
        return {"region_data": [], "message": "No data available"}

    filtered = filter_period(df, year=year, weeks=weeks)
    if disease:
        filtered = filtered[filtered['Disease'].str.lower() == disease.lower()]

    grouped = filtered.groupby(['State', 'District']).agg(
        Cases=('Cases', 'sum'),
        Deaths=('Deaths', 'sum'),
        Outbreaks=('Cases', 'size'),
        LatestWeek=('WeekStart', 'max'),
        Diseases=('Disease', lambda s: ", ".join(s.value_counts().index[:3])),
    ).reset_index()

    def get_risk(c):
        risk = categorize_risk(c)
        return None if risk == "None" else risk

    grouped['risk'] = grouped['Cases'].apply(get_risk)
    grouped['LatestWeek'] = grouped['LatestWeek'].dt.strftime('%Y-%m-%d')
    grouped = grouped.sort_values(by='Cases', ascending=False)

    period = {}
    if not filtered.empty:
        period = {
            "from": filtered['WeekStart'].min().strftime('%Y-%m-%d'),
            "to": (filtered['WeekStart'].max() + pd.Timedelta(days=6)).strftime('%Y-%m-%d'),
        }

    return {
        "status": "success",
        "total_cases": int(grouped['Cases'].sum()),
        "total_deaths": int(grouped['Deaths'].sum()),
        "total_outbreaks": int(grouped['Outbreaks'].sum()),
        "period": period,
        "top_hotspots": grouped.head(TOP_HOTSPOTS).to_dict(orient='records'),
        "region_data": grouped.to_dict(orient='records'),
    }
