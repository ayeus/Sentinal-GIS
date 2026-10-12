"""
Live signals: fetches WHO Disease Outbreak News (official notices) and news
feeds (media reports, unverified), tags each item with Indian states and
diseases by keyword, and aggregates them for the Live Intel views.

These are text mentions, not confirmed outbreaks: a state is "flagged" because
a headline names it. Feeds, gazetteer and keyword lists come from
app/resources/realtime.json.
"""
import calendar
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Dict, List, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

from app.config import (
    LIVE_FEED_CACHE_SECONDS,
    LIVE_FEED_MAX_ENTRIES,
    LIVE_FEED_TIMEOUT_SECONDS,
    LIVE_MAX_AGE_DAYS,
    LIVE_MAX_ALERTS,
    LIVE_SUMMARY_MAX_CHARS,
    load_realtime_config,
)

_USER_AGENT = "SentinelGIS/1.0 (+disease surveillance feed reader)"

_cache_lock = threading.Lock()
_alert_cache = {"alerts": None, "fetched_at": 0.0, "feed_status": {}}


@lru_cache(maxsize=1)
def get_config() -> dict:
    return load_realtime_config()


def _term_pattern(terms) -> re.Pattern:
    """Whole-word matcher, so 'goa' does not hit 'goal' and 'flu' does not hit 'influence'."""
    parts = []
    for term in sorted(terms, key=len, reverse=True):
        escaped = re.escape(term.lower()).replace(r"\&", "(?:&|and)").replace(r"\ ", r"\s+")
        parts.append(escaped)
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?:e?s)?(?![a-z0-9])")


@lru_cache(maxsize=1)
def _matchers() -> dict:
    cfg = get_config()
    return {
        "alert": _term_pattern(cfg["alert_keywords"]),
        "generic": _term_pattern(cfg["generic_outbreak_keywords"]),
        "country": _term_pattern([cfg["country_keyword"]]),
        "states": [(state, _term_pattern([state])) for state in cfg["states"]]
                  + [(state, _term_pattern([alias])) for alias, state in cfg.get("state_aliases", {}).items()],
        "cities": [(state, _term_pattern([city])) for city, state in cfg["city_to_state"].items()],
        "diseases": [(disease, _term_pattern(kws)) for disease, kws in cfg["disease_keywords"].items()],
    }


def _plain_text(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def _published_at(entry) -> Optional[str]:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not parsed:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc).isoformat()


def extract_locations(text: str) -> List[str]:
    text = text.lower()
    m = _matchers()
    found = []
    for state, pattern in m["states"]:
        if state not in found and pattern.search(text):
            found.append(state)
    for state, pattern in m["cities"]:
        if state not in found and pattern.search(text):
            found.append(state)
    return found


def extract_diseases(text: str) -> List[str]:
    """Extract disease names from text using keyword matching."""
    text = text.lower()
    m = _matchers()
    found = [disease for disease, pattern in m["diseases"] if pattern.search(text)]
    if not found and m["generic"].search(text):
        found.append(get_config()["generic_outbreak_label"])
    return found


def _entries(feed: dict) -> List[dict]:
    """Normalised entries (title, link, summary, published, published_at) for one feed."""
    response = requests.get(
        feed["url"], timeout=LIVE_FEED_TIMEOUT_SECONDS, headers={"User-Agent": _USER_AGENT}
    )
    response.raise_for_status()

    if feed.get("type") == "who_don":
        entries = []
        for item in response.json().get("value", []):
            published = item.get("PublicationDateAndTime") or item.get("PublicationDate") or ""
            try:
                moment = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                moment = None
            entries.append({
                "title": item.get("Title", ""),
                "link": feed["item_url"].format(id=item.get("DonId") or item.get("UrlName", "")),
                "summary": _plain_text(item.get("Summary") or item.get("Overview") or ""),
                "published": moment.strftime("%d %b %Y") if moment else "",
                "published_at": moment.isoformat() if moment else None,
            })
        return entries

    parsed = feedparser.parse(response.content)
    return [{
        "title": getattr(entry, "title", ""),
        "link": getattr(entry, "link", ""),
        "summary": _plain_text(getattr(entry, "summary", "")),
        "published": getattr(entry, "published", ""),
        "published_at": _published_at(entry),
    } for entry in parsed.entries]


def _fetch_feed(feed: dict) -> List[Dict]:
    m = _matchers()
    official = bool(feed.get("official"))

    oldest = (datetime.now(timezone.utc) - timedelta(days=LIVE_MAX_AGE_DAYS)).isoformat()

    alerts = []
    for entry in _entries(feed)[:LIVE_FEED_MAX_ENTRIES]:
        title, link, summary = entry["title"], entry["link"], entry["summary"]
        # Undated or old items are not live signals
        if not entry["published_at"] or entry["published_at"] < oldest:
            continue
        # News aggregators repeat the headline as the summary
        if summary.lower().startswith(title.lower()[:60]):
            summary = ""
        text = f"{title} {summary}".lower()

        # Official outbreak notices are relevant by definition; news items must mention an outbreak term
        if not official and not m["alert"].search(text):
            continue

        locations = extract_locations(text)
        mentions_country = bool(m["country"].search(text))
        if len(summary) > LIVE_SUMMARY_MAX_CHARS:
            summary = summary[:LIVE_SUMMARY_MAX_CHARS].rstrip() + "..."

        alerts.append({
            "title": title,
            "link": link,
            "published": entry["published"],
            "published_at": entry["published_at"],
            "summary": summary,
            "source": feed["name"],
            "official": official,
            "is_priority": mentions_country or len(locations) > 0,
            "locations": locations,
            "diseases": [d for d in extract_diseases(text) if d != get_config()["generic_outbreak_label"]],
        })
    return alerts


def get_alerts(force_refresh: bool = False) -> List[Dict]:
    """
    Latest alerts across all feeds, newest first. Results are cached for
    LIVE_FEED_CACHE_SECONDS so the three live endpoints share one upstream fetch.
    """
    with _cache_lock:
        fresh = (time.time() - _alert_cache["fetched_at"]) < LIVE_FEED_CACHE_SECONDS
        if _alert_cache["alerts"] is not None and fresh and not force_refresh:
            return _alert_cache["alerts"]

        alerts, any_success, feed_status = [], False, {}
        for feed in get_config()["feeds"]:
            try:
                items = _fetch_feed(feed)
                alerts.extend(items)
                any_success = True
                feed_status[feed["name"]] = {"ok": True, "items": len(items)}
            except Exception as e:
                print(f"Error fetching feed {feed['name']}: {e}")
                feed_status[feed["name"]] = {"ok": False, "items": 0}
        _alert_cache["feed_status"] = feed_status

        # If every feed is down, keep serving the last good snapshot instead of an empty map
        if not any_success and _alert_cache["alerts"] is not None:
            return _alert_cache["alerts"]

        alerts.sort(key=lambda a: a["published_at"] or "", reverse=True)
        alerts = alerts[:LIVE_MAX_ALERTS]
        if any_success:
            _alert_cache["alerts"] = alerts
            _alert_cache["fetched_at"] = time.time()
        return alerts


def severity_levels() -> List[dict]:
    """Severity bands ordered from most to least severe."""
    return sorted(get_config()["severity_levels"], key=lambda lvl: lvl["min_alerts"], reverse=True)


def _severity_for(count: int) -> dict:
    levels = severity_levels()
    for level in levels:
        if count >= level["min_alerts"]:
            return level
    return levels[-1]


def get_geo_alerts() -> dict:
    """Alerts aggregated per state with severity, color and detected diseases."""
    cfg = get_config()
    alerts = get_alerts()
    state_data: Dict[str, dict] = {}

    for alert in alerts:
        if not alert.get("locations"):
            continue

        diseases = extract_diseases(alert["title"] + " " + (alert.get("summary") or ""))

        for loc in alert["locations"]:
            entry = state_data.setdefault(loc, {
                "state": loc,
                "count": 0,
                "alerts": [],
                "diseases": [],
                "danger_types": [],
            })
            entry["count"] += 1
            entry["alerts"].append({
                "title": alert["title"],
                "link": alert["link"],
                "published": alert.get("published", ""),
                "source": alert.get("source", ""),
                "official": alert.get("official", False),
                "summary": alert.get("summary", ""),
                "diseases": diseases,
            })
            for d in diseases:
                if d not in entry["diseases"]:
                    entry["diseases"].append(d)

    for entry in state_data.values():
        level = _severity_for(entry["count"])
        entry["severity"] = level["key"]
        entry["color"] = level["color"]
        entry["danger_types"] = entry["diseases"] or [cfg["default_danger_label"]]

    return {
        "states": state_data,
        "total_alerts": len(alerts),
        "severity_levels": severity_levels(),
        "sources": [{
            "name": feed["name"], "official": bool(feed.get("official")),
            **_alert_cache["feed_status"].get(feed["name"], {"ok": False, "items": 0}),
        } for feed in cfg["feeds"]],
        "max_age_days": LIVE_MAX_AGE_DAYS,
        "fetched_at": fetched_at(),
        "timestamp": datetime.now().isoformat(),
    }


def fetched_at():
    """When the feeds were last fetched successfully (ISO, UTC), or None."""
    stamp = _alert_cache["fetched_at"]
    return datetime.fromtimestamp(stamp, tz=timezone.utc).isoformat(timespec="seconds") if stamp else None


def get_guidance(disease: str) -> dict:
    """Curated, source-cited guidance for a disease. `available` is False when none has been curated."""
    cfg = get_config()
    lookup = {name.lower(): (name, entry) for name, entry in cfg["guidance"].items()}
    match = lookup.get((disease or "").strip().lower())
    if not match:
        return {"available": False, "disease": disease, "diseases_covered": sorted(cfg["guidance"])}
    name, entry = match
    return {"available": True, "disease": name, **entry, "disclaimer": cfg["guidance_disclaimer"]}
