"""Single source of truth for the descriptive bands applied to reported case counts."""
from app.config import (
    RISK_HIGH_CASES,
    RISK_MEDIUM_CASES,
    SPREAD_HIGH_CASES,
    SPREAD_MEDIUM_CASES,
)


def categorize_risk(cases) -> str:
    """Reported-burden band for a district: how many cases were reported, not a prediction."""
    if cases > RISK_HIGH_CASES: return "High"
    if cases > RISK_MEDIUM_CASES: return "Medium"
    if cases > 0: return "Low"
    return "None"


def spread_risk(origin_cases) -> str:
    if origin_cases > SPREAD_HIGH_CASES: return "High"
    if origin_cases > SPREAD_MEDIUM_CASES: return "Medium"
    return "Low"
