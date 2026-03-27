import os
import glob
import pandas as pd
import pdfplumber
import time

PDF_DIR = "idsp_pdfs"
OUTPUT_CSV = "historical_cases_raw.csv"

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

def main():
    print(f"Starting Continuous PDF Extraction from {PDF_DIR} (waiting for up to 150 files)...")
    
    while True:
        # Processed tracking to avoid re-running on the same PDFs repeatedly
        processed_files = set()
        if os.path.exists('processed_pdfs.txt'):
            with open('processed_pdfs.txt', 'r') as f:
                processed_files = set(f.read().splitlines())

        if len(processed_files) >= 150:
            print(f"Completed! {len(processed_files)} PDFs have been successfully parsed.")
            break

        pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
        # Some downloaded files might end with .part or be incomplete if they are actively downloading,
        # but requests/urllib usually saves the full .pdf when complete. So we just filter based on name.
        new_pdfs = [f for f in pdf_files if os.path.basename(f) not in processed_files]
        
        if not new_pdfs:
            print(f"[{len(processed_files)}/150 processed] Waiting for new PDFs to download... (sleeping for 5s)")
            time.sleep(5)
            continue

        print(f"Found {len(new_pdfs)} new PDFs to process. Parsing now...")
        all_extracted_rows = []
        
        for pdf_path in new_pdfs:
            # SAFETY CHECK: If the file was modified in the last 2 seconds, 
            # the scraper is probably still writing it. Skip it for this loop.
            try:
                if time.time() - os.path.getmtime(pdf_path) < 2:
                    continue
            except Exception:
                continue

            rows = extract_tables_from_pdf(pdf_path)
            
            # If rows is None, pdfplumber crashed (usually file corruption or mid-download)
            # We skip adding it to processed_pdfs.txt so it tries again next loop!
            if rows is None:
                continue
                
            if rows:
                all_extracted_rows.extend(rows)
                
            with open('processed_pdfs.txt', 'a') as f:
                f.write(os.path.basename(pdf_path) + '\n')

        if all_extracted_rows:
            # Standardize columns by finding the maximum row length
            max_cols = max(len(row) for row in all_extracted_rows)
            cols = [f"Col_{i}" for i in range(max_cols)]
            
            # Pad shorter rows with empty strings so pandas doesn't crash
            padded_rows = [row + [""] * (max_cols - len(row)) for row in all_extracted_rows]
            
            df = pd.DataFrame(padded_rows, columns=cols)
            
            # Append to csv
            if os.path.exists(OUTPUT_CSV):
                df.to_csv(OUTPUT_CSV, mode='a', header=False, index=False)
            else:
                df.to_csv(OUTPUT_CSV, index=False)
                
            print(f"Added {len(all_extracted_rows)} rows into {OUTPUT_CSV}! Continuing to monitor...")
        else:
            print("No valid tables found in this batch. Continuing to monitor...")
            
        time.sleep(1) # Small pause before next check

if __name__ == "__main__":
    main()
