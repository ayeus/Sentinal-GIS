"""
Turns the raw rows extracted from IDSP bulletins into the clean outbreak table
used by the API and the forecasting model.

One row per outbreak (Unique ID). Every transformation is conservative and
traceable: reported names are kept next to the canonical ones, each date
carries the field it was taken from, and a data-quality report records what
could not be resolved instead of hiding it.
"""
import sys
from pathlib import Path

# Allow running this file directly (python data/clean_data.py) as well as importing it
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import os
import re
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from app.config import (
    CLEAN_DATA_PATH,
    DATA_QUALITY_PATH,
    PDF_DIR,
    RAW_DATA_PATH,
)
from app.services import gazetteer

# Define input and output paths
RAW_CSV_PATH = str(RAW_DATA_PATH)
CLEAN_CSV_PATH = str(CLEAN_DATA_PATH)

CLEAN_COLUMNS = [
    "Date", "State", "District", "Disease", "Cases", "Deaths",
    "ReportYear", "ReportWeek", "WeekStart", "Status", "OutbreakID",
    "ReportedDistrict", "ReportedDisease", "DistrictMatch", "DateSource", "SourceFile",
]

ID_PATTERN = re.compile(r"^([A-Z]{2})/([A-Z0-9]{2,5})/(\d{4})/(\d{1,2})/(\d{1,5})$")
# An outbreak can start well before it is reported, but not after, and not years before
MAX_REPORTING_LAG_DAYS = 180

# (canonical disease, substrings) checked in order against the label with all
# non-letters removed, which also undoes words split by line wraps in the PDF
DISEASE_RULES = [
    ("Cholera", ["cholera"]),
    ("Shigellosis", ["shigell"]),
    ("Acute Diarrheal Disease", ["diarr", "gastroenter", "dysent", "norovirus", "rotavirus"]),
    ("Food Poisoning", ["foodpoison", "foodborne", "mushroompoison"]),
    ("Chickenpox", ["chickenpox", "chikenpox", "varicella"]),
    ("Dengue", ["dengue"]),
    ("Chikungunya", ["chikungunya"]),
    ("Measles", ["measles"]),
    ("Rubella", ["rubella"]),
    ("Fever With Rash", ["feverwithrash"]),
    ("Hepatitis / Jaundice", ["hepatitis", "jaundice"]),
    ("Malaria", ["malaria"]),
    ("Mumps", ["mumps"]),
    ("Scrub Typhus", ["scrubtyphus"]),
    ("Rabies", ["rabies"]),
    ("Animal Bite", ["dogbite", "animalbite", "snakebite"]),
    ("Leptospirosis", ["lepto"]),
    ("Acute Encephalitis Syndrome / JE", ["encephali"]),
    ("Typhoid", ["typhoid", "entericfever"]),
    ("Diphtheria", ["diphtheria", "diptheria"]),
    ("Pertussis", ["pertussis", "whoopingcough"]),
    ("Zika Virus", ["zika"]),
    ("Mpox", ["mpox", "monkeypox"]),
    ("West Nile Fever", ["westnile"]),
    ("Nipah", ["nipah"]),
    ("Kyasanur Forest Disease", ["kyasanur"]),
    ("Crimean-Congo Hemorrhagic Fever", ["crimean", "cchf"]),
    ("Influenza", ["influenza", "hn"]),
    ("Leishmaniasis / Kala-Azar", ["leishmani", "kalaazar"]),
    ("Anthrax", ["anthrax"]),
    ("Melioidosis", ["melioid"]),
    ("Acute Flaccid Paralysis", ["flaccidparalysis"]),
    ("Hand, Foot and Mouth Disease", ["handfoot", "hfmd"]),
    ("Adenovirus", ["adenovirus"]),
    ("Fever of Unknown Origin", ["feverofunknown", "pyrexia", "unknownfever"]),
]


def clean_cases(val):
    if pd.isna(val):
        return 0
    numbers = re.findall(r'\d+', str(val))
    return int(numbers[0]) if numbers else 0


def parse_date(val):
    """dd-mm-yy / dd-mm-yyyy (also with / or . and stray spaces) -> date, else None."""
    match = re.search(r'(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{2,4})', str(val or ""))
    if not match:
        return None
    day, month, year = (int(g) for g in match.groups())
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def clean_disease(val):
    label = re.sub(r"\s+", " ", str(val or "")).strip()
    if not label or label.lower() == "nan":
        return "Unknown"
    k = re.sub(r"[^a-z]", "", label.lower())
    k = re.sub(r"^(suspected|suspect|probable|confirmed)", "", k)
    for disease, needles in DISEASE_RULES:
        if any(n in k for n in needles):
            return disease
    if k == "fever":
        return "Fever of Unknown Origin"
    return re.sub(r"^(Suspected|Probable)\s+", "", label.title())


def _week_start(year, week):
    """Monday of the IDSP reporting week (IDSP weeks follow ISO-8601 numbering)."""
    try:
        return date.fromisocalendar(int(year), int(week), 1)
    except ValueError:
        return None


def build_clean_frame(raw):
    """Returns (clean_df, quality_report) from the raw extraction table."""
    records, issues = [], {"bad_id": 0, "unknown_state": [], "unmatched_districts": {}}
    date_sources = {}

    for row in raw.to_dict(orient="records"):
        match = ID_PATTERN.match(str(row.get("outbreak_id", "")))
        if not match:
            issues["bad_id"] += 1
            continue
        # The ID carries the year and week the outbreak was reported in
        report_year, report_week = int(match.group(3)), int(match.group(4))
        week_start = _week_start(report_year, report_week)
        if week_start is None:
            issues["bad_id"] += 1
            continue
        week_end = week_start + timedelta(days=6)

        state = gazetteer.resolve_state(row.get("state"))
        if state is None:
            issues["unknown_state"].append(str(row.get("state")))
            continue

        reported_district = re.sub(r"\s+", " ", str(row.get("district") or "")).strip()
        district, how = gazetteer.resolve_district(state, reported_district)
        if district is None:
            district = reported_district.title()
            label = f"{state} | {reported_district}"
            issues["unmatched_districts"][label] = issues["unmatched_districts"].get(label, 0) + 1

        # Outbreak start date, validated against the reporting week
        start, source = None, "week_start"
        for field in ("start_date", "report_date"):
            parsed = parse_date(row.get(field))
            if parsed and week_end - timedelta(days=MAX_REPORTING_LAG_DAYS) <= parsed <= week_end:
                start, source = parsed, field
                break
        if start is None:
            start = week_start
        date_sources[source] = date_sources.get(source, 0) + 1

        records.append({
            "Date": start.isoformat(),
            "State": state,
            "District": district,
            "Disease": clean_disease(row.get("disease")),
            "Cases": clean_cases(row.get("cases")),
            "Deaths": clean_cases(row.get("deaths")),
            "ReportYear": report_year,
            "ReportWeek": report_week,
            "WeekStart": week_start.isoformat(),
            "Status": re.sub(r"\s+", " ", str(row.get("status") or "")).strip().title(),
            "OutbreakID": row["outbreak_id"],
            "ReportedDistrict": reported_district,
            "ReportedDisease": re.sub(r"\s+", " ", str(row.get("disease") or "")).strip(),
            "DistrictMatch": how,
            "DateSource": source,
            "SourceFile": row.get("source_file", ""),
            "_bulletin": (int(row.get("bulletin_year") or 0), int(row.get("bulletin_week") or 0)),
        })

    clean_df = pd.DataFrame(records, columns=CLEAN_COLUMNS + ["_bulletin"])
    # A follow-up row repeats an earlier outbreak with updated counts: keep the latest bulletin's figures
    before = len(clean_df)
    clean_df = (clean_df.sort_values("_bulletin").drop_duplicates("OutbreakID", keep="last")
                .drop(columns="_bulletin").sort_values(["WeekStart", "State", "District", "OutbreakID"])
                .reset_index(drop=True))

    quality = {
        "raw_rows": int(len(raw)),
        "outbreaks": int(len(clean_df)),
        "follow_up_rows_merged": int(before - len(clean_df)),
        "rows_dropped_invalid_id": issues["bad_id"],
        "rows_dropped_unknown_state": sorted(set(issues["unknown_state"])),
        "district_match": clean_df["DistrictMatch"].value_counts().to_dict() if len(clean_df) else {},
        "unmatched_districts": dict(sorted(issues["unmatched_districts"].items(), key=lambda kv: -kv[1])),
        "date_source": date_sources,
    }
    return clean_df, quality


def coverage_report(clean_df, raw):
    """Which reporting weeks the dataset actually contains: gaps are bulletins we do not have."""
    weeks = sorted({(int(y), int(w)) for y, w in zip(clean_df["ReportYear"], clean_df["ReportWeek"])})
    if not weeks:
        return {"weeks_covered": 0}
    # A week counts as covered only if its own bulletin was ingested (not merely
    # mentioned as a late-reported outbreak in a later one)
    bulletin_weeks = sorted({(int(y), int(w)) for y, w in zip(raw["bulletin_year"], raw["bulletin_week"]) if y and w})
    first, last = _week_start(*bulletin_weeks[0]), _week_start(*bulletin_weeks[-1])
    expected, cursor = [], first
    while cursor <= last:
        iso = cursor.isocalendar()
        expected.append((iso[0], iso[1]))
        cursor += timedelta(days=7)
    have = set(bulletin_weeks)
    missing = [f"{y}-W{w:02d}" for y, w in expected if (y, w) not in have]
    return {
        "first_week": f"{bulletin_weeks[0][0]}-W{bulletin_weeks[0][1]:02d}",
        "latest_week": f"{bulletin_weeks[-1][0]}-W{bulletin_weeks[-1][1]:02d}",
        "latest_week_start": last.isoformat(),
        "latest_week_end": (last + timedelta(days=6)).isoformat(),
        "bulletins_ingested": len(bulletin_weeks),
        "weeks_in_span": len(expected),
        "weeks_missing": len(missing),
        "missing_weeks": missing,
        "bulletin_weeks": [f"{y}-W{w:02d}" for y, w in bulletin_weeks],
    }


def main():
    print(f"Loading {RAW_CSV_PATH}...")
    try:
        raw = pd.read_csv(RAW_CSV_PATH, dtype=str).fillna("")
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return 0

    if "outbreak_id" not in raw.columns:
        print("Raw CSV is in the legacy positional layout. Run the PDF extractor to rebuild it.")
        return 0

    print(f"Loaded {len(raw)} raw rows. Cleaning data...")
    clean_df, quality = build_clean_frame(raw)

    quality["coverage"] = coverage_report(clean_df, raw)
    quality["pdfs_on_disk"] = len(list(Path(PDF_DIR).glob("*.pdf")))
    quality["pdfs_with_records"] = int(raw["source_file"].nunique())
    quality["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Save atomically, the API hot-reloads these files while serving
    for path, writer in ((CLEAN_CSV_PATH, lambda p: clean_df.to_csv(p, index=False)),
                         (str(DATA_QUALITY_PATH), lambda p: Path(p).write_text(json.dumps(quality, indent=2)))):
        tmp_path = path + ".tmp"
        writer(tmp_path)
        os.replace(tmp_path, path)

    print(f"\n=====================================")
    print(f"Data Cleaning Complete!")
    print(f"Total outbreaks: {len(clean_df)} (from {quality['raw_rows']} raw rows)")
    print(f"Coverage: {quality['coverage'].get('first_week')} to {quality['coverage'].get('latest_week')}, "
          f"{quality['coverage'].get('weeks_missing')} weeks missing")
    print(f"District match: {quality['district_match']}")
    print(f"Saved to: {CLEAN_CSV_PATH}")
    print(f"=====================================")
    return len(clean_df)

if __name__ == "__main__":
    main()
