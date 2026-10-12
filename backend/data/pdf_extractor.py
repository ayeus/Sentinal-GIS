"""
Extracts outbreak records from IDSP Weekly Outbreak Report PDFs.

Each bulletin lists outbreaks as table rows keyed by a Unique ID such as
`KL/CNR/2023/10/207` (state / district code / year / reporting week / serial).
Three sections share that layout: outbreaks of the reporting week, outbreaks
reported late, and follow-ups of earlier outbreaks (same ID, updated counts).

The PDFs shade individual text lines with filled rectangles. pdfplumber treats
those as table borders and shatters every row, so we keep only hairline
rectangles (the real cell borders) before detecting tables.
"""
import sys
from pathlib import Path

# Allow running this file directly (python data/pdf_extractor.py) as well as importing it
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import csv
import glob
import os
import re
import time
from datetime import date

import pdfplumber

from app import config

PDF_DIR = str(config.PDF_DIR)
OUTPUT_CSV = str(config.RAW_DATA_PATH)
PROCESSED_FILE = str(config.PROCESSED_PDFS_FILE)

RAW_COLUMNS = [
    "outbreak_id", "state", "district", "disease", "cases", "deaths",
    "start_date", "report_date", "status", "comments",
    "bulletin_year", "bulletin_week", "week_start", "week_end", "source_file",
]

# e.g. KL/CNR/2023/10/207 (tolerates stray spaces introduced by line wraps)
ID_PATTERN = re.compile(r"^([A-Z]{2})\s*/\s*([A-Z0-9]{2,5})\s*/\s*(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,5})$")
UNREADABLE_GRACE_SECONDS = 600
DATE_PATTERN = re.compile(r"^\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{2,4}$")
STATUS_PATTERN = re.compile(r"under\s+(control|surveillance|investigation)|completed", re.I)
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}
_DAY = r"(\d{1,2})\s*(?:st|nd|rd|th)?"
WEEK_RANGE_PATTERN = re.compile(
    _DAY + r"\s+([A-Za-z]+)\s*,?\s*(\d{4})?\s*(?:to|-|–)\s*" + _DAY + r"\s+([A-Za-z]+)\s*,?\s*(\d{4})", re.I)


def _is_border(obj) -> bool:
    """Drop filled rectangles (text shading); keep hairline rectangles (cell borders)."""
    return not (obj["object_type"] == "rect" and obj["width"] > 1.5 and obj["height"] > 1.5)


def _cell(value) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\n", " ")).strip()


def _parse_week_range(text: str):
    """Reporting period printed on the cover page: '(7th July 2025 to 13th July 2025)'."""
    match = WEEK_RANGE_PATTERN.search(re.sub(r"\s+", " ", text or ""))
    if not match:
        return None, None
    d1, m1, y1, d2, m2, y2 = match.groups()
    try:
        month1, month2, year2 = MONTHS[m1.lower()], MONTHS[m2.lower()], int(y2)
        # A missing start year belongs to the end year, unless the week spans New Year
        year1 = int(y1) if y1 else (year2 - 1 if month1 > month2 else year2)
        return date(year1, month1, int(d1)), date(year2, month2, int(d2))
    except (KeyError, ValueError):
        return None, None


def _parse_row(row):
    """Map one table row to an outbreak record, or None if it is not an outbreak row."""
    cells = [_cell(c) for c in row]
    id_index = next((i for i, c in enumerate(cells) if ID_PATTERN.match(c)), None)
    if id_index is None:
        return None

    rest = cells[id_index + 1:]
    if len(rest) < 6:
        return None
    state, district, disease, cases, deaths = rest[:5]
    tail = rest[5:]

    # After the death count: start date, (reporting date), status, comments.
    # The late-reported and follow-up sections omit the reporting date.
    dates, status, comments = [], "", ""
    for i, value in enumerate(tail):
        if not status and len(dates) < 2 and (DATE_PATTERN.match(value) or value in ("", "???", "-", "NA")):
            dates.append(value if DATE_PATTERN.match(value) else "")
        elif not status and STATUS_PATTERN.search(value) and len(value) < 40:
            status = value
        else:
            comments = " ".join(v for v in tail[i:] if v)
            break

    return {
        "outbreak_id": re.sub(r"\s+", "", cells[id_index]),
        "state": state, "district": district, "disease": disease,
        "cases": cases, "deaths": deaths,
        "start_date": dates[0] if dates else "",
        "report_date": dates[1] if len(dates) > 1 else "",
        "status": status, "comments": comments,
    }


def extract_tables_from_pdf(pdf_path):
    """Returns a list of outbreak records, or None if the PDF could not be read."""
    name = os.path.basename(pdf_path)
    print(f"Extracting: {name}")
    records = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            cover_text = " ".join((page.extract_text() or "") for page in pdf.pages[:2])
            week_start, week_end = _parse_week_range(cover_text)

            for page in pdf.pages:
                for table in page.filter(_is_border).extract_tables():
                    for row in table:
                        record = _parse_row(row)
                        if record:
                            records.append(record)
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None  # Return None so we know it crashed and DON'T mark it as processed yet

    # The bulletin's own week: the IDs of new outbreaks carry it, so take the latest
    # (follow-up rows carry older weeks)
    stamps = []
    for record in records:
        _, _, year, week, _ = ID_PATTERN.match(record["outbreak_id"]).groups()
        stamps.append((int(year), int(week)))
    if week_end and stamps:
        in_year = [s for s in stamps if s[0] == week_end.year]
        stamps = in_year or stamps
    bulletin_year, bulletin_week = max(stamps) if stamps else ("", "")

    for record in records:
        record.update({
            "bulletin_year": bulletin_year, "bulletin_week": bulletin_week,
            "week_start": week_start.isoformat() if week_start else "",
            "week_end": week_end.isoformat() if week_end else "",
            "source_file": name,
        })
    return records


def _raw_file_is_current() -> bool:
    """False when the raw CSV is missing or was written by the old positional extractor."""
    if not os.path.exists(OUTPUT_CSV) or os.path.getsize(OUTPUT_CSV) == 0:
        return False
    with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
        return next(csv.reader(f), None) == RAW_COLUMNS


def extract_batch():
    print(f"Starting Batch PDF Extraction from {PDF_DIR}...")

    appending = _raw_file_is_current()
    processed_files = set()
    if appending and os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            processed_files = set(f.read().splitlines())
    elif not appending:
        # Raw data in an old/unknown layout: rebuild it from every PDF on disk
        print("Raw dataset missing or in a legacy layout: re-extracting all PDFs.")
        open(PROCESSED_FILE, 'w').close()

    pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    new_pdfs = [f for f in pdf_files if os.path.basename(f) not in processed_files]

    if not new_pdfs:
        print(f"[{len(processed_files)} processed] No new PDFs found.")
        return 0

    print(f"Found {len(new_pdfs)} new PDFs to process. Parsing now...")
    all_records, done = [], []

    for pdf_path in new_pdfs:
        records = extract_tables_from_pdf(pdf_path)
        if records is None:
            # A file still being written will be retried; an old unreadable one is
            # corrupt, so stop retrying it on every pass (it shows up in the
            # data-quality report as a PDF without records)
            if time.time() - os.path.getmtime(pdf_path) > UNREADABLE_GRACE_SECONDS:
                print(f"  ⚠️ {os.path.basename(pdf_path)} is unreadable and will be skipped. Re-download it to retry.")
                done.append(os.path.basename(pdf_path))
            continue
        if not records:
            print(f"  ⚠️ No outbreak rows recognised in {os.path.basename(pdf_path)}")
        all_records.extend(records)
        done.append(os.path.basename(pdf_path))

    if all_records or not appending:
        with open(OUTPUT_CSV, 'a' if appending else 'w', newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=RAW_COLUMNS)
            if not appending:
                writer.writeheader()
            writer.writerows(all_records)

    # Mark as processed only after the rows are safely on disk
    with open(PROCESSED_FILE, 'a') as f:
        for name in done:
            f.write(name + '\n')

    if all_records:
        print(f"Added {len(all_records)} rows into {OUTPUT_CSV}!")
    else:
        print("No valid tables found in this batch.")
    return len(all_records)


def main():
    print(f"Starting Continuous PDF Extraction from {PDF_DIR}...")
    while True:
        extract_batch()
        time.sleep(config.PDF_WATCH_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
