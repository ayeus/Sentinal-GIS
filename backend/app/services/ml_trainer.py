"""
Trains, evaluates and publishes the outbreak forecaster.

Each run:
  1. tunes hyperparameters by forward-chaining validation on older data
  2. scores the chosen model once on the most recent labelled weeks, which
     took no part in tuning or fitting (the numbers shown in the app)
  3. refits on everything and forecasts the weeks after the latest bulletin
  4. writes the model, the forecast table and a model card with the evidence
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Allow running this file directly (python app/services/ml_trainer.py)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from app.config import (
    ADJACENCY_PATH,
    CLEAN_DATA_PATH,
    DATA_QUALITY_PATH,
    DISTRICT_GAZETTEER_PATH,
    FORECAST_HOLDOUT_WEEKS,
    FORECAST_HORIZON_WEEKS,
    FORECAST_MODEL_PATH,
    FORECAST_OUTPUT_PATH,
    FORECAST_RANDOM_STATE,
    FORECAST_TIERS,
    MODEL_CARD_PATH,
    MODEL_DIR,
)
from app.services.forecasting import Panel, build_dataset, tier_for

# Candidate settings, from more flexible to more regularised. Outbreak reports
# are sparse (about 1 in 100 district-disease-months), so small trees tend to win.
PARAM_GRID = [
    dict(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=100, l2_regularization=1.0),
    dict(max_iter=400, learning_rate=0.03, max_leaf_nodes=15, min_samples_leaf=200, l2_regularization=5.0),
    dict(max_iter=150, learning_rate=0.08, max_leaf_nodes=7, min_samples_leaf=200, l2_regularization=10.0),
    dict(max_iter=600, learning_rate=0.02, max_leaf_nodes=7, min_samples_leaf=300, l2_regularization=10.0),
]
VALIDATION_FOLDS = 3
MIN_LABELLED_WEEKS = 40
# Simple rules a model must beat to be worth using
BASELINES = {
    "pair_rate_lifetime": "Historical frequency of the disease in the district",
    "pair_rate_52w": "Frequency over the last 52 weeks",
    "season_state_rate": "Seasonal frequency of the disease in the state",
}
FEATURE_LABELS = {
    "pair_rate": "Past outbreaks of this disease in the district",
    "neighbour_rate": "Outbreaks in neighbouring districts",
    "state_rate": "Outbreaks elsewhere in the state",
    "district_any_rate": "All outbreaks reported by the district",
    "national_rate": "National activity of the disease",
    "pair_cases": "Recent case counts",
    "weeks_since_last": "Time since the last outbreak",
    "season": "Season (time of year)",
    "lat": "Geography", "lon": "Geography",
    "disease_code": "Disease",
}


def _fit(X, y, params):
    model = HistGradientBoostingClassifier(
        categorical_features=[list(X.columns).index("disease_code")],
        early_stopping=False, random_state=FORECAST_RANDOM_STATE, **params,
    )
    return model.fit(X, y)


def _scores(y_true, prob):
    """Ranking and calibration quality. The 'top 1%' figures mirror how the app is used: act on the short list."""
    k = max(1, int(len(y_true) * 0.01))
    top = np.argsort(-prob)[:k]
    positives = max(1, int(y_true.sum()))
    return {
        "average_precision": round(float(average_precision_score(y_true, prob)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, prob)), 4),
        "brier": round(float(brier_score_loss(y_true, np.clip(prob, 0, 1))), 5),
        "precision_top_1pct": round(float(y_true[top].mean()), 4),
        "recall_top_1pct": round(float(y_true[top].sum() / positives), 4),
    }


def _tier_table(y_true, prob):
    """What each risk tier meant in practice on the hold-out weeks."""
    bounds = [(name, threshold) for name, threshold in FORECAST_TIERS] + [("Minimal", 0.0)]
    rows, upper = [], 1.01
    total_positives = max(1, int(y_true.sum()))
    for name, lower in bounds:
        mask = (prob >= lower) & (prob < upper)
        n = int(mask.sum())
        rows.append({
            "tier": name,
            "min_probability": lower,
            "share_of_forecasts": round(n / len(prob), 4),
            "forecasts": n,
            "observed_outbreak_rate": round(float(y_true[mask].mean()), 4) if n else None,
            "mean_forecast_probability": round(float(prob[mask].mean()), 4) if n else None,
            "share_of_outbreaks_captured": round(float(y_true[mask].sum() / total_positives), 4),
        })
        upper = lower
    return rows


def _feature_group(name):
    for prefix, label in FEATURE_LABELS.items():
        if name.startswith(prefix):
            return label
    return name


def _load_inputs():
    clean = pd.read_csv(CLEAN_DATA_PATH)
    gazetteer = pd.read_csv(DISTRICT_GAZETTEER_PATH)
    adjacency = pd.read_csv(ADJACENCY_PATH)
    with open(DATA_QUALITY_PATH, "r", encoding="utf-8") as f:
        coverage = json.load(f)["coverage"]
    covered = [date.fromisocalendar(int(w[:4]), int(w[6:]), 1) for w in coverage["bulletin_weeks"]]
    return clean, gazetteer, adjacency, covered


def _atomic_write(path, writer):
    """Write via a temp file so API workers never read a half-written artefact."""
    tmp_path = f"{path}.tmp"
    writer(tmp_path)
    os.replace(tmp_path, path)


def _forecast_table(panel, model, t):
    """Forecast for the weeks after reference week t, with the facts behind each number."""
    features = panel.features(t)
    prob = model.predict_proba(features)[:, 1]
    table = panel.index_frame()
    table["probability"] = np.round(prob, 4)
    table["tier"] = [tier_for(p) for p in prob]

    def count(cum, weeks):
        return panel._window(cum, t, weeks)

    pair_52 = count(panel._cum_events, 52)
    pair_12 = count(panel._cum_events, 12)
    table["outbreaks_52w"] = pair_52.reshape(-1).astype(int)
    table["outbreaks_12w"] = pair_12.reshape(-1).astype(int)
    table["neighbour_outbreaks_12w"] = (panel.neighbours @ pair_12).reshape(-1).astype(int)
    table["state_outbreaks_12w"] = (panel.state_matrix.T @ pair_12)[panel.state_of].reshape(-1).astype(int)
    since = features["weeks_since_last"].to_numpy()
    ever = (panel._cum_events[t + 1] > 0).reshape(-1)
    table["weeks_since_last_outbreak"] = np.where(ever, since, np.nan)
    return table.sort_values("probability", ascending=False).reset_index(drop=True)


def retrain_model(evaluate: bool = False):
    print("="*40)
    print("🚀 Training outbreak forecaster...")
    print("="*40)

    for path in (CLEAN_DATA_PATH, DISTRICT_GAZETTEER_PATH, ADJACENCY_PATH, DATA_QUALITY_PATH):
        if not path.exists():
            print(f"Error: {path} not found.")
            return False

    clean, gazetteer, adjacency, covered = _load_inputs()
    panel = Panel(clean, gazetteer, adjacency, covered)
    if not panel.diseases:
        print("No disease has enough reported outbreaks to model.")
        return False

    horizon = FORECAST_HORIZON_WEEKS
    references = panel.reference_weeks()
    labelled = [t for t in references if panel.label_available(t)]
    if len(labelled) < MIN_LABELLED_WEEKS:
        print(f"Only {len(labelled)} labelled weeks; need {MIN_LABELLED_WEEKS} to train and evaluate honestly.")
        return False

    X, y, week = build_dataset(panel, labelled)
    print(f"{len(X):,} district-disease-weeks, {int(y.sum()):,} followed by an outbreak ({y.mean():.2%}).")

    # ── Forward-in-time split ───────────────────────────────────────────────
    holdout = labelled[-FORECAST_HOLDOUT_WEEKS:]
    # Training labels must be fully known before the hold-out starts
    development = [t for t in labelled if t + horizon < holdout[0]]
    folds = np.array_split(np.array(development), VALIDATION_FOLDS + 2)[2:]

    tuning = []
    for params in PARAM_GRID:
        fold_scores = []
        for fold in folds:
            train = np.isin(week, [t for t in development if t + horizon < fold[0]])
            test = np.isin(week, fold)
            model = _fit(X[train], y[train], params)
            fold_scores.append(average_precision_score(y[test], model.predict_proba(X[test])[:, 1]))
        tuning.append({"params": params, "validation_average_precision": round(float(np.mean(fold_scores)), 4)})
        print(f"  {params} -> validation AP {np.mean(fold_scores):.4f}")
    best = max(tuning, key=lambda r: r["validation_average_precision"])["params"]

    # ── One-shot evaluation on the untouched hold-out ───────────────────────
    dev_mask, hold_mask = np.isin(week, development), np.isin(week, holdout)
    model = _fit(X[dev_mask], y[dev_mask], best)
    X_hold, y_hold = X[hold_mask], y[hold_mask]
    prob_hold = model.predict_proba(X_hold)[:, 1]

    holdout_scores = _scores(y_hold, prob_hold)
    baselines = [
        {"name": label, **_scores(y_hold, np.nan_to_num(X_hold[column].to_numpy()))}
        for column, label in BASELINES.items()
    ]
    best_baseline = max(b["average_precision"] for b in baselines)

    disease_codes = X_hold["disease_code"].to_numpy()
    per_disease = []
    for code, disease in enumerate(panel.diseases):
        mask = disease_codes == code
        positives = int(y_hold[mask].sum())
        row = {"disease": disease, "outbreak_periods": positives}
        if 0 < positives < mask.sum():
            row["average_precision"] = round(float(average_precision_score(y_hold[mask], prob_hold[mask])), 4)
            row["roc_auc"] = round(float(roc_auc_score(y_hold[mask], prob_hold[mask])), 4)
            row["base_rate"] = round(float(y_hold[mask].mean()), 4)
        per_disease.append(row)

    # Which information the model leans on (drop in hold-out AP when shuffled)
    rng = np.random.default_rng(FORECAST_RANDOM_STATE)
    sample = np.union1d(np.flatnonzero(y_hold == 1), rng.choice(len(X_hold), size=min(40000, len(X_hold)), replace=False))
    importance = permutation_importance(
        model, X_hold.iloc[sample], y_hold[sample], scoring="average_precision",
        n_repeats=3, random_state=FORECAST_RANDOM_STATE,
    )
    grouped = {}
    for name, value in zip(X.columns, importance.importances_mean):
        grouped[_feature_group(name)] = grouped.get(_feature_group(name), 0.0) + max(0.0, float(value))
    total = sum(grouped.values()) or 1.0
    drivers = [{"factor": k, "share": round(v / total, 3)} for k, v in sorted(grouped.items(), key=lambda kv: -kv[1])]

    if evaluate:
        print("\n--- Hold-out evaluation (weeks the model never saw) ---")
        print(json.dumps(holdout_scores, indent=2))
        print(f"Best simple baseline AP: {best_baseline}")

    # ── Final model on all labelled weeks, forecast from the latest bulletin ─
    final_model = _fit(X, y, best)
    latest = references[-1]
    forecast = _forecast_table(panel, final_model, latest)
    window_start = panel.weeks[latest] + timedelta(days=7)
    window_end = window_start + timedelta(days=7 * horizon - 1)

    def week_label(t):
        iso = panel.weeks[t].isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

    card = {
        "model": "Gradient-boosted decision trees (scikit-learn HistGradientBoostingClassifier)",
        "target": f"At least one outbreak of the disease reported by IDSP for the district within {horizon} weeks",
        "horizon_weeks": horizon,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "diseases_modelled": panel.diseases,
        "districts": len(panel.districts),
        "training": {
            "rows": int(len(X)),
            "outbreak_periods": int(y.sum()),
            "base_rate": round(float(y.mean()), 4),
            "reference_weeks": len(labelled),
            "first_week": week_label(labelled[0]),
            "last_week": week_label(labelled[-1]),
            "hyperparameters": best,
            "tuning": tuning,
        },
        "evaluation": {
            "method": "Tuned on earlier weeks by forward-chaining validation; scored once on the most recent labelled weeks, which were excluded from tuning and fitting.",
            "holdout_first_week": week_label(holdout[0]),
            "holdout_last_week": week_label(holdout[-1]),
            "holdout_rows": int(hold_mask.sum()),
            "holdout_outbreak_periods": int(y_hold.sum()),
            "holdout_base_rate": round(float(y_hold.mean()), 4),
            "model": holdout_scores,
            "baselines": baselines,
            "lift_over_best_baseline": round(holdout_scores["average_precision"] / best_baseline, 2) if best_baseline else None,
            "tiers": _tier_table(y_hold, prob_hold),
            "per_disease": per_disease,
        },
        "drivers": drivers,
        "forecast": {
            "based_on_week": week_label(latest),
            "based_on_week_end": (panel.weeks[latest] + timedelta(days=6)).isoformat(),
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "tier_counts": forecast["tier"].value_counts().to_dict(),
        },
        "limitations": [
            "Trained on outbreaks that states reported to IDSP. Unreported or late-reported outbreaks are invisible to it.",
            "It predicts reporting, which mixes true disease activity with how thoroughly a state reports. States that report many outbreaks (Kerala, for example) are rated higher partly for that reason; a low rating in a state that reports little is weak evidence of safety.",
            "A forecast is a probability, not a certainty: most High-tier flags are not followed by a reported outbreak, and some outbreaks occur where risk was rated Minimal.",
            "Weeks without an ingested bulletin are excluded, so long gaps weaken seasonal and year-on-year signals.",
            "Rare diseases and diseases new to a district are predicted poorly; diseases with too few reports are not modelled at all.",
            "Decision support only. It does not replace field surveillance or the judgement of public-health officers.",
        ],
    }

    os.makedirs(MODEL_DIR, exist_ok=True)
    _atomic_write(FORECAST_MODEL_PATH, lambda p: joblib.dump(
        {"model": final_model, "features": list(X.columns), "diseases": panel.diseases}, p))
    _atomic_write(FORECAST_OUTPUT_PATH, lambda p: forecast.to_csv(p, index=False))
    _atomic_write(MODEL_CARD_PATH, lambda p: Path(p).write_text(json.dumps(card, indent=2)))

    print(f"Hold-out AP {holdout_scores['average_precision']} vs best baseline {best_baseline} "
          f"(ROC-AUC {holdout_scores['roc_auc']}).")
    print(f"✅ Forecast for {window_start} to {window_end} saved to {FORECAST_OUTPUT_PATH}")
    return True

if __name__ == "__main__":
    retrain_model(evaluate=True)
