"""
Downloads IDSP Weekly Outbreak Report PDFs.

The official index page (IDSP_BULLETIN_URL, on the NCDC website since the old
IDSP site was retired) lists one PDF per reporting week. The older IDSP page
layout, including its Google Drive links, is still understood. When the
official server cannot be reached, the Internet Archive's Wayback Machine is
used instead: its latest capture of the index page and its stored copies of
the same PDF files. Every file is recorded in
idsp_pdfs/manifest.json with the week it belongs to and where it came from.
"""
import sys
from pathlib import Path

# Allow running this file directly (python data/scraper.py) as well as importing it
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.config import (
    IDSP_BULLETIN_URL,
    PDF_DIR,
    SCRAPER_DELAY_SECONDS,
    SCRAPER_FIRST_YEAR,
    SCRAPER_MAX_DOCUMENTS,
    SCRAPER_TIMEOUT_SECONDS,
    PROCESSED_PDFS_FILE,
    SCRAPER_USE_ARCHIVE_FALLBACK,
)

URL = IDSP_BULLETIN_URL
DOWNLOAD_DIR = str(PDF_DIR)
MANIFEST_PATH = os.path.join(DOWNLOAD_DIR, "manifest.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SentinelGIS/1.0; public-health surveillance research)"}

# 'id_' returns the archived bytes unmodified; a bare timestamp resolves to the closest capture
WAYBACK_RAW = "https://web.archive.org/web/{timestamp}id_/{url}"
DRIVE_DOWNLOAD = "https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
ARCHIVE_TIMEOUT_SECONDS = 90


def setup():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _load_manifest() -> dict:
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_manifest(manifest: dict):
    tmp_path = MANIFEST_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    os.replace(tmp_path, MANIFEST_PATH)


def is_complete_pdf(path) -> bool:
    """True for a file that starts and ends like a PDF (rejects error pages and truncated downloads)."""
    try:
        with open(path, "rb") as f:
            head = f.read(5)
            f.seek(max(0, os.path.getsize(path) - 2048))
            tail = f.read()
    except OSError:
        return False
    return head == b"%PDF-" and b"%%EOF" in tail


# ── Index page ──────────────────────────────────────────────────────────────

def _latest_archived_index():
    """(html, capture timestamp) of the newest Wayback capture of the index page."""
    # A timestamp in the future resolves to the most recent capture of the URL
    page = requests.get(WAYBACK_RAW.format(timestamp="2099", url=URL),
                        timeout=ARCHIVE_TIMEOUT_SECONDS, headers=HEADERS)
    page.raise_for_status()
    match = re.search(r"/web/(\d{14})", page.url)
    if not match or not parse_index(page.content):
        raise RuntimeError("No usable archived copy of the IDSP index page was found")
    return page.content, match.group(1)


def fetch_index():
    """
    Returns (html, source) where source says where the index came from:
    {"origin": "portal"} or {"origin": "archive", "captured": "YYYY-MM-DD", "portal_error": ...}.
    """
    try:
        response = requests.get(URL, timeout=SCRAPER_TIMEOUT_SECONDS, headers=HEADERS)
        response.raise_for_status()
        return response.content, {"origin": "portal"}
    except requests.RequestException as e:
        if not SCRAPER_USE_ARCHIVE_FALLBACK:
            raise
        print(f"Official index unreachable ({type(e).__name__}); using the Internet Archive copy.")
        html, timestamp = _latest_archived_index()
        captured = datetime.strptime(timestamp[:8], "%Y%m%d").date().isoformat()
        return html, {"origin": "archive", "captured": captured, "portal_error": type(e).__name__}


# NCDC layout: the year and week are part of each file's address
NCDC_LINK_PATTERN = re.compile(r"/weekly_outbreaks/((?:19|20)\d{2})/week\s*(\d{1,2})[^/]*\.pdf$", re.I)


def parse_index(html):
    """
    [(year, week, url)] from the index page. Understands the NCDC page (year
    and week in each PDF's address) and the older IDSP table (one row per
    year, one link per week).
    """
    soup = BeautifulSoup(html, "html.parser")
    bulletins = []
    for link in soup.find_all("a", href=True):
        match = NCDC_LINK_PATTERN.search(link["href"].strip())
        if match:
            bulletins.append((int(match.group(1)), int(match.group(2)), urljoin(URL, link["href"].strip())))
    if bulletins:
        return bulletins

    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        year = cells[0].get_text(" ", strip=True)
        if not re.fullmatch(r"(19|20)\d\d", year):
            continue
        for link in cells[1].find_all("a", href=True):
            week = re.match(r"(\d{1,2})", link.get_text(strip=True))
            href = link["href"].strip()
            if week and (href.lower().endswith(".pdf") or "drive.google.com" in href):
                bulletins.append((int(year), int(week.group(1)), urljoin(URL, href)))
    return bulletins


# ── Downloading ─────────────────────────────────────────────────────────────

def _drive_file_id(url):
    match = re.search(r"/d/([A-Za-z0-9_-]{10,})", url) or re.search(r"[?&]id=([A-Za-z0-9_-]{10,})", url)
    return match.group(1) if match else None


def _stream_to(url, filepath, timeout):
    """Download to a temp name (so the PDF watcher never sees a partial file) and keep it only if it is a PDF."""
    tmp_path = filepath + ".part"
    try:
        response = requests.get(url, stream=True, timeout=timeout, headers=HEADERS)
        response.raise_for_status()
        with open(tmp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                f.write(chunk)
        if not is_complete_pdf(tmp_path):
            return False
        os.replace(tmp_path, filepath)
        return True
    except (requests.RequestException, OSError) as e:
        print(f"  download failed ({type(e).__name__}): {url[:100]}")
        return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def download_file(url, filepath, portal_reachable=True):
    """Fetch one bulletin. Returns the source it came from ('portal', 'google_drive', 'archive') or None."""
    file_id = _drive_file_id(url) if "drive.google.com" in url else None
    if file_id:
        ok = _stream_to(DRIVE_DOWNLOAD.format(file_id=file_id), filepath, ARCHIVE_TIMEOUT_SECONDS)
        return "google_drive" if ok else None
    if "drive.google.com" in url:
        return None  # a folder or other non-file link

    if portal_reachable and _stream_to(url, filepath, SCRAPER_TIMEOUT_SECONDS):
        return "portal"
    if SCRAPER_USE_ARCHIVE_FALLBACK and _stream_to(WAYBACK_RAW.format(timestamp="2", url=url), filepath, ARCHIVE_TIMEOUT_SECONDS):
        return "archive"
    return None


def bulletin_year_of(filepath):
    """Reporting year printed in the bulletin's own outbreak IDs, or None if it has no outbreak rows."""
    from data import pdf_extractor  # imported here: only needed when a file was actually downloaded
    bulletin = pdf_extractor.read_bulletin(filepath)
    return int(bulletin["year"]) if bulletin and bulletin["year"] else None


def main():
    setup()
    print(f"Fetching index: {URL}")
    html, index_source = fetch_index()
    bulletins = [b for b in parse_index(html) if b[0] >= SCRAPER_FIRST_YEAR]
    bulletins.sort(reverse=True)  # newest first
    print(f"Index ({index_source['origin']}) lists {len(bulletins)} weekly bulletins since {SCRAPER_FIRST_YEAR}.")
    if not bulletins:
        raise RuntimeError("The index page lists no weekly bulletins: its layout may have changed")

    manifest = _load_manifest()
    # Weeks already on disk, plus weeks whose link is known to point at the wrong document
    # (processed files may have been deleted after extraction: they still count as held)
    try:
        processed = set(Path(PROCESSED_PDFS_FILE).read_text().splitlines())
    except OSError:
        processed = set()
    held_weeks = {(entry["year"], entry["week"]) for entry in manifest.values()
                  if entry.get("rejected") or entry.get("file") in processed
                  or os.path.exists(os.path.join(DOWNLOAD_DIR, entry.get("file") or "-"))}
    portal_reachable = index_source["origin"] == "portal"
    downloaded, failed, changed = 0, [], False

    for year, week, url in bulletins:
        if downloaded >= SCRAPER_MAX_DOCUMENTS:
            break
        label = f"{year}-W{week:02d}"

        # Files fetched by earlier versions keep the server's own file name
        if (year, week) in held_weeks:
            continue
        legacy_path = os.path.join(DOWNLOAD_DIR, os.path.basename(urlparse(url).path))
        if legacy_path.lower().endswith(".pdf") and (os.path.basename(legacy_path) in processed or is_complete_pdf(legacy_path)):
            name = os.path.basename(legacy_path)
            if name not in manifest:
                manifest[name] = {"file": name, "year": year, "week": week, "url": url, "source": "portal"}
                changed = True
            continue

        filename = f"idsp_{year}_w{week:02d}.pdf"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        if is_complete_pdf(filepath):
            source = manifest.get(filename, {}).get("source", "unknown")
        else:
            print(f"Downloading {label}...")
            source = download_file(url, filepath, portal_reachable)
            time.sleep(SCRAPER_DELAY_SECONDS)  # Be polite to the servers
            if not source:
                failed.append(label)
                continue
            # The official index occasionally links a week to another year's bulletin
            actual_year = bulletin_year_of(filepath)
            if actual_year is not None and actual_year != year:
                os.remove(filepath)
                manifest[f"rejected:{label}"] = {
                    "file": None, "year": year, "week": week, "url": url,
                    "rejected": f"the index links this week to a {actual_year} bulletin",
                }
                changed = True
                failed.append(label)
                print(f"  rejected {label}: the linked document is a {actual_year} bulletin")
                continue
            downloaded += 1
        manifest[filename] = {
            "file": filename, "year": year, "week": week, "url": url, "source": source,
            "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        changed = True
        if downloaded % 10 == 0:
            _save_manifest(manifest)

    if changed:
        _save_manifest(manifest)
    newest = max((y, w) for y, w, _ in bulletins)
    print(f"Done! {downloaded} new bulletin(s) saved to '{DOWNLOAD_DIR}', {len(failed)} could not be fetched.")
    return {
        "index_source": index_source,
        "links_found": len(bulletins),
        "newest_week_listed": f"{newest[0]}-W{newest[1]:02d}",
        "downloaded": downloaded,
        "failed": failed[:50],
        "failed_count": len(failed),
    }

if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
