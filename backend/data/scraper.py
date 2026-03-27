import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re

URL = "https://idsp.mohfw.gov.in/index4.php?lang=1&level=0&linkid=406&lid=3689"
DOWNLOAD_DIR = "idsp_pdfs"

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
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Saved: {filename}")
        return filepath
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def main():
    setup()
    print(f"Fetching page: {URL}")
    response = requests.get(URL)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    links = get_pdf_links(soup)
    print(f"Found {len(links)} outbreak document links.")
    
    print(f"Filtering to download the {len(links[:150])} most recent weeks...")
    
    for i, link in enumerate(links[:150]): # Limiting to 150 (latest 3 years) per user request
        filename = f"week_doc_{i+1}.pdf"
        
        # If it's a direct PDF link with a real name, try to extract it
        if link.endswith('.pdf'):
            parts = link.split('/')
            if parts[-1].endswith('.pdf'):
                filename = parts[-1]
                
        download_file(link, filename, DOWNLOAD_DIR)
        time.sleep(1) # Be polite to the server
        
    print(f"Done! Check the '{DOWNLOAD_DIR}' folder.")
    print("Next step: We will use 'pdfplumber' to extract tables from these PDFs.")

if __name__ == "__main__":
    main()
