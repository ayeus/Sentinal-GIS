"""
Outbreak forecast endpoints. Everything served here is read from artefacts
written by the trainer (app/services/ml_trainer.py): the forecast table and
the model card holding the hold-out evidence.
"""
from datetime import date
from typing import Optional

import numpy as np
from fastapi import APIRouter

from app.config import DATA_STALE_AFTER_DAYS, FORECAST_TIERS
from app.data_loader import load_forecast, load_model_card

router = APIRouter(prefix="/api", tags=["Forecast"])

TIER_ORDER = [name for name, _ in FORECAST_TIERS] + ["Minimal"]


def _window(card):
    """Forecast window plus how it relates to today."""
    forecast = dict(card["forecast"])
    today = date.today()
    start, end = date.fromisoformat(forecast["window_start"]), date.fromisoformat(forecast["window_end"])
    forecast["status"] = "upcoming" if today < start else ("current" if today <= end else "expired")
    forecast["days_since_window_end"] = max(0, (today - end).days)
    data_age = (today - date.fromisoformat(forecast["based_on_week_end"])).days
    forecast["data_age_days"] = data_age
    forecast["is_stale"] = data_age > DATA_STALE_AFTER_DAYS
    return forecast


@router.get("/forecast")
def get_forecast(disease: Optional[str] = None, state: Optional[str] = None, district: Optional[str] = None,
                 include_minimal: bool = False):
    """
    Probability that IDSP reports an outbreak in each district during the
    forecast window. With a disease: one row per district for that disease.
    Without: each district's highest-probability disease. With a state and
    district: every forecast disease for that one district.
    """
    table, card = load_forecast(), load_model_card()
    if table is None or card is None:
        return {"available": False, "results": [],
                "message": "No forecast yet. It is produced when the model is trained on ingested bulletins."}

    rows = table
    if state:
        rows = rows[rows["State"].str.lower() == state.lower()]
    if district:
        rows = rows[rows["District"].str.lower() == district.lower()]
    if disease:
        rows = rows[rows["Disease"].str.lower() == disease.lower()]
        if rows.empty:
            return {
                "available": True, "results": [], "window": _window(card),
                "modelled": False,
                "message": f"'{disease}' is not forecast: it has too few reported outbreaks to model reliably. "
                           f"Forecast diseases: {', '.join(card['diseases_modelled'])}.",
            }
    elif not district:
        rows = rows.loc[rows.groupby(["State", "District"])["probability"].idxmax()]

    tier_counts = {tier: int((rows["tier"] == tier).sum()) for tier in TIER_ORDER}
    if not include_minimal:
        rows = rows[rows["tier"] != "Minimal"]
    rows = rows.sort_values("probability", ascending=False)

    results = rows.replace({np.nan: None}).rename(columns={"tier": "risk"}).to_dict(orient="records")
    return {
        "available": True,
        "modelled": True,
        "window": _window(card),
        "horizon_weeks": card["horizon_weeks"],
        "tier_counts": tier_counts,
        "tiers": card["evaluation"]["tiers"],
        "results": results,
    }


@router.get("/model-card")
def get_model_card():
    """The evidence behind the forecast: how the model was built, tested and where it fails."""
    card = load_model_card()
    if card is None:
        return {"available": False, "message": "No model has been trained yet."}
    return {"available": True, **card, "forecast": _window(card)}
