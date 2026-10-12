import sys
from pathlib import Path

# Allow running this file directly (python data/scraper.py) as well as importing it
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

from app.config import (
    IDSP_BULLETIN_URL,
    PDF_DIR,
    SCRAPER_DELAY_SECONDS,
    SCRAPER_MAX_DOCUMENTS,
    SCRAPER_TIMEOUT_SECONDS,
)

URL = IDSP_BULLETIN_URL
DOWNLOAD_DIR = str(PDF_DIR)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SentinelGIS/1.0; public-health surveillance research)"}

def setup():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

def get_pdf_links(soup):
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        # We skip Google Drive links because they require manual clicks/API auth 
        # and instead just get the latest direct PDFs from the server.
        if href.endswith('.pdf'):
            links.append(urljoin(URL, href))
    return links

def download_file(url, filename, folder):
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath):
        print(f"Already downloaded: {filename}")
        return filepath
        
    print(f"Downloading from: {url}")
    try:
        # Note: Google Drive links might require gdown or manual extraction
        # This handles standard direct PDF downloads
        response = requests.get(url, stream=True, timeout=SCRAPER_TIMEOUT_SECONDS, headers=HEADERS)
        response.raise_for_status()
        
        # Download to a temp name so the PDF watcher never picks up a partial file
        tmp_path = filepath + ".part"
        with open(tmp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        # Error pages and truncated downloads must not enter the dataset
        with open(tmp_path, 'rb') as f:
            head = f.read(5)
            f.seek(max(0, os.path.getsize(tmp_path) - 1024))
            tail = f.read()
        if head != b"%PDF-" or b"%%EOF" not in tail:
            os.remove(tmp_path)
            print(f"Discarded {filename}: not a complete PDF")
            return None
        os.replace(tmp_path, filepath)
        print(f"Saved: {filename}")
        return filepath
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def main():
    setup()
    print(f"Fetching page: {URL}")
    response = requests.get(URL, timeout=SCRAPER_TIMEOUT_SECONDS, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    links = get_pdf_links(soup)
    print(f"Found {len(links)} outbreak document links.")
    
    links = links[:SCRAPER_MAX_DOCUMENTS]  # Most recent bulletins only
    print(f"Filtering to download the {len(links)} most recent weeks...")
    
    downloaded = 0
    for i, link in enumerate(links):
        filename = f"week_doc_{i+1}.pdf"
        
        # If it's a direct PDF link with a real name, try to extract it
        if link.endswith('.pdf'):
            parts = link.split('/')
            if parts[-1].endswith('.pdf'):
                filename = parts[-1]
                
        if os.path.exists(os.path.join(DOWNLOAD_DIR, filename)):
            continue  # Already have it: no request needed
        if download_file(link, filename, DOWNLOAD_DIR):
            downloaded += 1
        time.sleep(SCRAPER_DELAY_SECONDS) # Be polite to the server
        
    print(f"Done! {downloaded} new bulletin(s) saved to '{DOWNLOAD_DIR}'.")
    return {"links_found": len(links), "downloaded": downloaded}

if __name__ == "__main__":
    main()
