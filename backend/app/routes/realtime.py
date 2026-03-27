import feedparser
import requests
from datetime import datetime
from fastapi import APIRouter
from typing import List, Dict

router = APIRouter(prefix="/api/live", tags=["Real-Time Feed"])

# Trusted news feeds for disease alerts
FEEDS = [
    "https://news.google.com/rss/search?q=disease+outbreak+India&hl=en-IN&gl=IN&ceid=IN:en",
    "https://www.who.int/rss-feeds/news-english.xml"
]

# List of Indian states and common districts for basic NER
STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", 
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", 
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", 
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu & Kashmir", "Ladakh"
]

@router.get("/alerts")
def get_live_alerts() -> List[Dict]:
    """
    Fetches real-time disease alerts from WHO and Google News RSS.
    Filters for relevant mentions of outbreaks in India.
    """
    alerts = []
    
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                title_desc = (entry.title + " " + (entry.summary if hasattr(entry, 'summary') else "")).lower()
                
                # Simple keyword filtering for outbreaks
                keywords = ["outbreak", "cases", "virus", "infection", "alert", "health", "epidemic", "fever", "nipah", "dengue", "cholera"]
                if any(k in title_desc for k in keywords):
                    # Find specific location mentions
                    found_locations = []
                    for s in STATES:
                        if s.lower() in title_desc:
                            found_locations.append(s)
                    
                    # Highlight if it mentions India
                    is_india = "india" in title_desc or "india" in entry.link.lower() or len(found_locations) > 0
                    
                    alerts.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.published if hasattr(entry, 'published') else "Just now",
                        "summary": entry.summary[:200] + "..." if hasattr(entry, 'summary') else "",
                        "source": "Google News" if "google" in url else "WHO",
                        "is_priority": is_india,
                        "locations": found_locations
                    })
        except Exception as e:
            print(f"Error parsing feed {url}: {e}")

    # Return top 20 most recent alerts
    return sorted(alerts, key=lambda x: x.get('published', ''), reverse=True)[:20]

@router.get("/signals")
def get_live_signals():
    """
    Returns a mapping of locations mentioned in recent news to signal strength.
    Used for front-end "Live Validation" badges.
    """
    alerts = get_live_alerts()
    signals = {}
    
    for alert in alerts:
        if not alert["is_priority"]: continue
        
        # Give higher weight to alerts mentioning specific locations
        weight = 0.8 if alert["source"] == "WHO" else 0.5
        for loc in alert["locations"]:
            signals[loc] = max(signals.get(loc, 0), weight)
            
    return {"signals": signals, "timestamp": datetime.now().isoformat()}

DISEASE_KEYWORDS = {
    "Dengue": ["dengue"],
    "Malaria": ["malaria"],
    "Cholera": ["cholera"],
    "Nipah": ["nipah"],
    "COVID-19": ["covid", "coronavirus", "sars-cov"],
    "Influenza": ["influenza", "flu", "h1n1", "h5n1", "bird flu", "avian flu"],
    "Typhoid": ["typhoid"],
    "Chikungunya": ["chikungunya"],
    "Tuberculosis": ["tuberculosis", "tb "],
    "Zika": ["zika"],
    "Hepatitis": ["hepatitis"],
    "Measles": ["measles"],
    "Leptospirosis": ["leptospirosis", "lepto"],
    "Japanese Encephalitis": ["japanese encephalitis", "je "],
    "Plague": ["plague"],
    "Ebola": ["ebola"],
    "HMPV": ["hmpv", "metapneumovirus"],
}

def _extract_diseases(text: str) -> list:
    """Extract disease names from text using keyword matching."""
    text_lower = text.lower()
    found = []
    for disease, keywords in DISEASE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(disease)
    if not found:
        # Generic fallback
        generic = ["outbreak", "epidemic", "virus", "infection", "fever", "disease"]
        for g in generic:
            if g in text_lower:
                found.append("Outbreak Alert")
                break
    return found


@router.get("/geo-alerts")
def get_geo_alerts():
    """
    Returns alert data aggregated by Indian state for map visualization.
    Each state gets: alert count, color intensity, diseases detected, and list of alerts.
    """
    alerts = get_live_alerts()
    state_data = {}

    for alert in alerts:
        if not alert.get("locations"):
            continue

        # Extract disease types from title + summary
        alert_text = alert["title"] + " " + (alert.get("summary") or "")
        diseases = _extract_diseases(alert_text)

        for loc in alert["locations"]:
            if loc not in state_data:
                state_data[loc] = {
                    "state": loc,
                    "count": 0,
                    "alerts": [],
                    "diseases": [],
                    "danger_types": [],
                }
            state_data[loc]["count"] += 1
            state_data[loc]["alerts"].append({
                "title": alert["title"],
                "link": alert["link"],
                "published": alert.get("published", ""),
                "source": alert.get("source", ""),
                "summary": alert.get("summary", ""),
                "diseases": diseases,
            })
            # Aggregate unique diseases for this state
            for d in diseases:
                if d not in state_data[loc]["diseases"]:
                    state_data[loc]["diseases"].append(d)

    # Assign severity color and danger type label based on alert count
    for loc in state_data:
        count = state_data[loc]["count"]
        diseases = state_data[loc]["diseases"]

        if count >= 5:
            state_data[loc]["severity"] = "critical"
            state_data[loc]["color"] = "#dc2626"   # red-600
        elif count >= 3:
            state_data[loc]["severity"] = "high"
            state_data[loc]["color"] = "#ea580c"   # orange-600
        elif count >= 2:
            state_data[loc]["severity"] = "medium"
            state_data[loc]["color"] = "#d97706"   # amber-600
        else:
            state_data[loc]["severity"] = "low"
            state_data[loc]["color"] = "#eab308"   # yellow-500

        # Set danger type summary
        if diseases:
            state_data[loc]["danger_types"] = diseases
        else:
            state_data[loc]["danger_types"] = ["General Health Alert"]

    return {
        "states": state_data,
        "total_alerts": len(alerts),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/advisor")
def get_health_advisor(disease: str, location: str):
    """
    Simulated AI Health Advisor. 
    In a production app, this would call Gemini/GPT API.
    For this demo, it returns structured medical intelligence.
    """
    guidelines = {
        "Dengue": {
            "causes": "Stagnant water accumulation post-monsoon leading to Aedes mosquito breeding.",
            "prevention": "Eliminate open water containers, use mosquito nets/repellents, and wear long sleeves.",
            "suggestion": "Mass fogging in district clusters and rapid diagnostic testing at primary health centers."
        },
        "Malaria": {
            "causes": "Anopheles mosquito proliferation in rural/forested areas with poor drainage.",
            "prevention": "IRS (Indoor Residual Spraying) and LLIN (Long-Lasting Insecticidal Nets).",
            "suggestion": "Proactive screening of migrant workers and aggressive treatment of confirmed cases."
        },
        "Cholera": {
            "causes": "Contamination of drinking water sources with Vibrio cholerae bacteria, often after flooding.",
            "prevention": "Ensure water chlorination, promote handwashing with soap, and boil all drinking water.",
            "suggestion": "Distribution of ORS (Oral Rehydration Salts) and setting up mobile sanitation units."
        }
    }
    
    advice = guidelines.get(disease, {
        "causes": "Localized clinical transmission within the community.",
        "prevention": "Standard hygiene practices and early screening.",
        "suggestion": "Increase clinical surveillance and report all new cases to local authorities."
    })
    
    return {
        "disease": disease,
        "location": location,
        **advice,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
