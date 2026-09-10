import os
import glob
import pandas as pd
import pdfplumber
import time

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(DATA_DIR)
PDF_DIR = os.path.join(BACKEND_DIR, "idsp_pdfs")
OUTPUT_CSV = os.path.join(DATA_DIR, "historical_cases_raw.csv")
PROCESSED_FILE = os.path.join(BACKEND_DIR, "processed_pdfs.txt")

def extract_tables_from_pdf(pdf_path):
    print(f"Extracting: {os.path.basename(pdf_path)}")
    all_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract tables
                table = page.extract_table()
                if table:
                    # Filter out empty rows or headers
                    for row in table:
                        # Basic validation to see if row looks like disease data
                        # usually columns are: Sr.No, State, District, Disease, Cases, Deaths, Date, Status
                        clean_row = [str(cell).strip().replace('\n', ' ') if cell else "" for cell in row]
                        
                        # A valid row usually has > 5 columns and some numbers
                        if len(clean_row) >= 5 and clean_row[1] != "" and clean_row[3] != "":
                            # Check if the cases column has numbers
                            if any(char.isdigit() for char in clean_row[4:6]):
                                clean_row.append(os.path.basename(pdf_path)) # Add source file
                                all_data.append(clean_row)
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None  # Return None so we know it crashed and DON'T mark it as processed yet
        
    return all_data

def extract_batch():
    print(f"Starting Batch PDF Extraction from {PDF_DIR}...")
    
    processed_files = set()
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            processed_files = set(f.read().splitlines())

    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    new_pdfs = [f for f in pdf_files if os.path.basename(f) not in processed_files]
    
    if not new_pdfs:
        print(f"[{len(processed_files)} processed] No new PDFs found.")
        return 0

    print(f"Found {len(new_pdfs)} new PDFs to process. Parsing now...")
    all_extracted_rows = []
    
    for pdf_path in new_pdfs:
        rows = extract_tables_from_pdf(pdf_path)
        if rows is None:
            continue
            
        if rows:
            all_extracted_rows.extend(rows)
            
        with open(PROCESSED_FILE, 'a') as f:
            f.write(os.path.basename(pdf_path) + '\n')

    if all_extracted_rows:
        max_cols = max(len(row) for row in all_extracted_rows)
        cols = [f"Col_{i}" for i in range(max_cols)]
        padded_rows = [row + [""] * (max_cols - len(row)) for row in all_extracted_rows]
        df = pd.DataFrame(padded_rows, columns=cols)
        
        if os.path.exists(OUTPUT_CSV):
            df.to_csv(OUTPUT_CSV, mode='a', header=False, index=False)
        else:
            df.to_csv(OUTPUT_CSV, index=False)
            
        print(f"Added {len(all_extracted_rows)} rows into {OUTPUT_CSV}!")
        return len(all_extracted_rows)
    else:
        print("No valid tables found in this batch.")
        return 0

def main():
    print(f"Starting Continuous PDF Extraction from {PDF_DIR} (waiting for up to 150 files)...")
    while True:
        extract_batch()
        time.sleep(5)

if __name__ == "__main__":
    main()
