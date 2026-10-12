"""
Outbreak forecasting.

Question answered: for a district and a disease, how likely is it that IDSP
reports at least one outbreak during the next FORECAST_HORIZON_WEEKS weeks?

Why this framing: the source data are weekly bulletins of *reported outbreaks*,
not routine case counts. A district-disease series is mostly silence with
occasional events, so the honest, learnable target is the probability of an
event, not a case number.

Leak-free by construction:
  * every feature at reference week t uses only bulletins up to and including t
  * weeks whose bulletin we do not have are excluded from rates (never counted
    as "no outbreak") and a label is only built when all horizon weeks exist
  * evaluation is strictly forward in time: tuning on earlier blocks, final
    numbers on a later hold-out block the model never saw
"""
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.config import (
    FORECAST_HORIZON_WEEKS,
    FORECAST_MIN_DISEASE_OUTBREAKS,
    FORECAST_TIERS,
)

WINDOWS = (4, 12, 26, 52)       # look-back windows, in weeks
SEASON_HALF_WIDTH = 4           # weeks either side of the target period's mid-week
MAX_WEEKS_SINCE = 104


def _monday(d) -> date:
    d = pd.Timestamp(d).date()
    return d - timedelta(days=d.weekday())


class Panel:
    """Weekly outbreak counts on a continuous week grid: [week, district, disease]."""

    def __init__(self, outbreaks: pd.DataFrame, gazetteer: pd.DataFrame, adjacency: pd.DataFrame,
                 covered_weeks, diseases=None):
        self.districts = list(zip(gazetteer["state"], gazetteer["district"]))
        self.district_index = {d: i for i, d in enumerate(self.districts)}
        self.lat = gazetteer["lat"].to_numpy(float)
        self.lon = gazetteer["lon"].to_numpy(float)

        covered = sorted({_monday(w) for w in covered_weeks})
        self.first_week = covered[0]
        self.n_weeks = (covered[-1] - self.first_week).days // 7 + 1
        self.weeks = [self.first_week + timedelta(days=7 * i) for i in range(self.n_weeks)]
        self.covered = np.zeros(self.n_weeks, dtype=bool)
        for w in covered:
            self.covered[(w - self.first_week).days // 7] = True

        df = outbreaks.copy()
        df["_week"] = [(_monday(w) - self.first_week).days // 7 for w in df["WeekStart"]]
        df["_district"] = [self.district_index.get(k, -1) for k in zip(df["State"], df["District"])]
        df = df[(df["_district"] >= 0) & (df["_week"] >= 0) & (df["_week"] < self.n_weeks)]

        if diseases is None:
            counts = df["Disease"].value_counts()
            diseases = sorted(counts[counts >= FORECAST_MIN_DISEASE_OUTBREAKS].index)
        self.diseases = list(diseases)
        disease_index = {d: i for i, d in enumerate(self.diseases)}

        n_d, n_k = len(self.districts), len(self.diseases)
        self.events = np.zeros((self.n_weeks, n_d, n_k), dtype=np.float32)   # outbreaks reported
        self.cases = np.zeros((self.n_weeks, n_d, n_k), dtype=np.float32)
        self.any_events = np.zeros((self.n_weeks, n_d), dtype=np.float32)    # all diseases, modelled or not
        for week, district, disease, cases in zip(df["_week"], df["_district"], df["Disease"], df["Cases"]):
            self.any_events[week, district] += 1
            k = disease_index.get(disease)
            if k is not None:
                self.events[week, district, k] += 1
                self.cases[week, district, k] += cases

        # Neighbour adjacency matrix and state membership
        self.neighbours = np.zeros((n_d, n_d), dtype=np.float32)
        for a, b in zip(zip(adjacency["origin_state"], adjacency["origin_district"]),
                        zip(adjacency["dest_state"], adjacency["dest_district"])):
            i, j = self.district_index.get(a), self.district_index.get(b)
            if i is not None and j is not None:
                self.neighbours[i, j] = self.neighbours[j, i] = 1
        states = sorted({s for s, _ in self.districts})
        self.state_of = np.array([states.index(s) for s, _ in self.districts])
        self.state_matrix = (self.state_of[:, None] == np.arange(len(states))[None, :]).astype(np.float32)

        # Cumulative sums along time make every window sum O(1)
        pad = lambda a: np.concatenate([np.zeros((1,) + a.shape[1:], a.dtype), np.cumsum(a, axis=0)])
        self._cum_events, self._cum_cases = pad(self.events), pad(self.cases)
        self._cum_any, self._cum_covered = pad(self.any_events), pad(self.covered.astype(np.float32))

    # ── window helpers (weeks t-w+1 … t inclusive) ──────────────────────────
    def _window(self, cum, t, w):
        return cum[t + 1] - cum[max(0, t + 1 - w)]

    def _rate(self, cum, t, w):
        coverage = self._window(self._cum_covered, t, w)
        return self._window(cum, t, w) / coverage if coverage > 0 else np.full(cum.shape[1:], np.nan, np.float32)

    def label_available(self, t) -> bool:
        """True when every bulletin of the horizon after week t was ingested."""
        end = t + FORECAST_HORIZON_WEEKS
        return end < self.n_weeks and bool(self.covered[t + 1:end + 1].all())

    def labels(self, t):
        return (self.events[t + 1:t + 1 + FORECAST_HORIZON_WEEKS].sum(axis=0) > 0).astype(np.int8)

    def reference_weeks(self):
        """Weeks with a bulletin and at least a quarter of history behind them."""
        return [t for t in range(self.n_weeks) if self.covered[t] and self._cum_covered[t + 1] >= 12]

    def features(self, t) -> pd.DataFrame:
        """One row per (district, disease) describing everything known at the end of week t."""
        n_d, n_k = len(self.districts), len(self.diseases)
        cols = {}

        for w in WINDOWS:
            pair = self._rate(self._cum_events, t, w)                       # [district, disease]
            cols[f"pair_rate_{w}w"] = pair
            cols[f"neighbour_rate_{w}w"] = self.neighbours @ np.nan_to_num(pair) if not np.isnan(pair).all() else pair
            state = (self.state_matrix.T @ np.nan_to_num(pair))              # [state, disease]
            cols[f"state_rate_{w}w"] = state[self.state_of] if not np.isnan(pair).all() else pair
            cols[f"district_any_rate_{w}w"] = np.repeat(self._rate(self._cum_any, t, w)[:, None], n_k, axis=1)
        cols["national_rate_12w"] = np.repeat(np.nansum(cols["pair_rate_12w"], axis=0)[None, :], n_d, axis=0)
        cols["pair_cases_12w"] = self._window(self._cum_cases, t, 12)

        # Lifetime frequency of the pair, and how long since it last reported
        coverage_so_far = self._cum_covered[t + 1]
        cols["pair_rate_lifetime"] = self._cum_events[t + 1] / coverage_so_far
        history = self.events[:t + 1] > 0
        last_seen = np.where(history.any(axis=0), t - (history.shape[0] - 1 - np.argmax(history[::-1], axis=0)), MAX_WEEKS_SINCE)
        cols["weeks_since_last"] = np.minimum(last_seen, MAX_WEEKS_SINCE).astype(np.float32)

        # Seasonality: how often the disease was reported at this time of year, in
        # everything seen so far (state level and district level)
        target_mid = self.weeks[t] + timedelta(days=7 * (FORECAST_HORIZON_WEEKS + 1) // 2)
        target_woy = target_mid.isocalendar()[1]
        woy = np.array([w.isocalendar()[1] for w in self.weeks[:t + 1]])
        distance = np.abs(woy - target_woy)
        in_season = (np.minimum(distance, 52 - distance) <= SEASON_HALF_WIDTH) & self.covered[:t + 1]
        if in_season.any():
            seasonal = self.events[:t + 1][in_season].sum(axis=0) / in_season.sum()
            cols["season_pair_rate"] = seasonal
            cols["season_state_rate"] = (self.state_matrix.T @ seasonal)[self.state_of]
        else:
            cols["season_pair_rate"] = cols["season_state_rate"] = np.full((n_d, n_k), np.nan, np.float32)

        angle = 2 * np.pi * target_woy / 52.0
        frame = pd.DataFrame({name: np.asarray(values, dtype=np.float32).reshape(-1) for name, values in cols.items()})
        frame["season_sin"], frame["season_cos"] = np.float32(np.sin(angle)), np.float32(np.cos(angle))
        frame["lat"] = np.repeat(self.lat, n_k).astype(np.float32)
        frame["lon"] = np.repeat(self.lon, n_k).astype(np.float32)
        frame["disease_code"] = np.tile(np.arange(n_k), n_d).astype(np.int16)
        return frame

    def index_frame(self) -> pd.DataFrame:
        """State / District / Disease for each row of features()."""
        n_k = len(self.diseases)
        return pd.DataFrame({
            "State": np.repeat([s for s, _ in self.districts], n_k),
            "District": np.repeat([d for _, d in self.districts], n_k),
            "Disease": np.tile(self.diseases, len(self.districts)),
        })


def build_dataset(panel: Panel, weeks):
    """Stack features (and labels where known) for the given reference weeks."""
    frames, labels, week_ids = [], [], []
    for t in weeks:
        frame = panel.features(t)
        frames.append(frame)
        week_ids.append(np.full(len(frame), t, dtype=np.int32))
        labels.append(panel.labels(t).reshape(-1) if panel.label_available(t) else np.full(len(frame), -1, np.int8))
    return pd.concat(frames, ignore_index=True), np.concatenate(labels), np.concatenate(week_ids)


def tier_for(probability: float) -> str:
    for name, threshold in FORECAST_TIERS:
        if probability >= threshold:
            return name
    return "Minimal"
