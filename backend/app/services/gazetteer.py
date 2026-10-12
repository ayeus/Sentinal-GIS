"""
Resolves state and district names as written in IDSP bulletins to the
canonical names of the boundary layer (data/districts.csv), so every record
joins cleanly to the map and to the district adjacency table.

Resolution order for districts: exact name -> curated alias -> parent district
(for districts newer than the boundaries) -> conservative fuzzy match. Anything
else stays unmatched and is reported, never guessed.
"""
import csv
import difflib
import json
import re
from functools import lru_cache

from app.config import DISTRICT_ALIASES_PATH, DISTRICT_GAZETTEER_PATH

# A fuzzy match must be this similar, and clearly better than the runner-up
FUZZY_CUTOFF = 0.88
FUZZY_MARGIN = 0.04


def key(name) -> str:
    """Comparison key: lowercase letters and digits only ('Thiruvanan thapuram' == 'Thiruvananthapuram')."""
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


@lru_cache(maxsize=1)
def _tables():
    with open(DISTRICT_GAZETTEER_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    states = {key(r["state"]): r["state"] for r in rows}
    districts = {}  # state -> {key: canonical district}
    for r in rows:
        index = districts.setdefault(r["state"], {})
        name = r["district"]
        index[key(name)] = name
    # 'Khargone (West Nimar)' and 'Kadapa(YSR)' also answer to each part,
    # unless that part is ambiguous within the state ('Warangal (R)' / 'Warangal (U)')
    for state, index in districts.items():
        parts = {}
        for name in list(index.values()):
            if "(" in name:
                for part in re.split(r"[()]", name):
                    if len(key(part)) > 2:
                        parts.setdefault(key(part), set()).add(name)
        for part_key, names in parts.items():
            if len(names) == 1 and part_key not in index:
                index[part_key] = next(iter(names))

    with open(DISTRICT_ALIASES_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    for reported, target in raw.get("states", {}).items():
        if key(target) not in states:
            raise ValueError(f"district_aliases.json: '{target}' is not a state in the gazetteer")
        states[key(reported.replace("&", " and "))] = states[key(target)]
    aliases = {}
    for kind in ("renamed", "parent"):
        for source, target in raw[kind].items():
            state, reported = source.split("|", 1)
            if key(target) not in districts.get(state, {}):
                raise ValueError(f"district_aliases.json: '{target}' is not a district of {state} in the gazetteer")
            aliases[(state, key(reported))] = (target, "alias" if kind == "renamed" else "parent")
    return states, districts, aliases


def all_districts():
    """[(state, district)] for every district of the boundary layer."""
    _, districts, _ = _tables()
    return sorted({(state, name) for state, index in districts.items() for name in index.values()})


def resolve_state(reported):
    """Canonical state/UT name, or None if the text is not recognisably a state."""
    states, _, _ = _tables()
    text = re.sub(r"\(.*?\)", "", str(reported or "")).replace("&", " and ")
    k = key(text)
    k = re.sub(r"^the", "", k)
    if k in states:
        return states[k]
    match = difflib.get_close_matches(k, list(states), n=1, cutoff=0.8)
    return states[match[0]] if match else None


def resolve_district(state, reported):
    """
    Returns (canonical_district, how) where how is one of
    exact | alias | parent | fuzzy | none. With 'none' the first element is None.
    """
    _, districts, aliases = _tables()
    index = districts.get(state, {})
    text = str(reported or "")

    candidates = [text]
    if "(" in text:  # 'Cannanore (Kannur)', 'Darrang (Mangaldoi)': try each part too
        candidates += [part for part in re.split(r"[()]", text) if len(key(part)) > 2]

    for how_exact, table in (("alias", None), ("exact", index)):
        for candidate in candidates:
            k = key(candidate)
            if table is None:
                if (state, k) in aliases:
                    return aliases[(state, k)]
            elif k in table:
                return table[k], how_exact

    k = key(text)
    scored = sorted(((difflib.SequenceMatcher(None, k, other).ratio(), other) for other in index), reverse=True)
    if scored and scored[0][0] >= FUZZY_CUTOFF:
        runner_up = next((s for s, other in scored[1:] if index[other] != index[scored[0][1]]), 0)
        if scored[0][0] - runner_up >= FUZZY_MARGIN:
            return index[scored[0][1]], "fuzzy"
    return None, "none"
