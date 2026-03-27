import pandas as pd
import numpy as np
import re
import os

# Define input and output paths
RAW_CSV_PATH = 'historical_cases_raw.csv'
CLEAN_CSV_PATH = 'historical_cases_clean.csv'

def clean_cases(val):
    if pd.isna(val):
        return 0
    val = str(val).strip()
    # Extract only numbers
    numbers = re.findall(r'\d+', val)
    if numbers:
        return int(numbers[0])
    return 0

def clean_date(val):
    if pd.isna(val):
        return np.nan
    val = str(val).strip()
    # Match patterns like DD-MM-YYYY, DD/MM/YYYY, DD-MM-YY
    match = re.search(r'(\d{2})[-/](\d{2})[-/](\d{2,4})', val)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = "20" + year # Assuming 2000s
        try:
            # Ensure day and month are valid enough for pandas
            return pd.to_datetime(f"{year}-{month}-{day}", errors='coerce').strftime('%Y-%m-%d')
        except:
            return np.nan
    return np.nan

def clean_disease(val):
    if pd.isna(val):
        return 'Unknown'
    val = str(val).strip().title()
    
    # Standardize common disease names
    if 'Chickenpox' in val or 'Chicken Pox' in val or 'Chikenpox' in val: return 'Chickenpox'
    if 'Dengue' in val: return 'Dengue'
    if 'Malaria' in val: return 'Malaria'
    if 'Chikungunya' in val: return 'Chikungunya'
    if 'Measles' in val: return 'Measles'
    if 'Rubella' in val: return 'Rubella'
    if 'Diarrh' in val or 'Gastro' in val or 'Dysenter' in val or 'Dysentr' in val: return 'Acute Diarrheal Disease'
    if 'Food Poison' in val or 'Food Borne' in val or 'Mushroom' in val or 'Chemical' in val: return 'Food Poisoning'
    if 'Typhoid' in val: return 'Typhoid'
    if 'Hepatitis' in val or 'Jaundice' in val: return 'Hepatitis/Jaundice'
    if 'Rabies' in val or 'Bite' in val: return 'Rabies'
    if 'Cholera' in val: return 'Cholera'
    if 'Scrub Typhus' in val: return 'Scrub Typhus'
    if 'Influenza' in val or 'H1N1' in val or 'H3N2' in val: return 'Influenza'
    if 'Fever' in val and 'Rash' in val: return 'Fever With Rash'
    if 'Fever' in val and 'Unknown' in val or 'Pyrexia' in val or val == 'Fever': return 'Fever of Unknown Origin'
    if 'Leishmani' in val or 'Kala' in val: return 'Leishmaniasis / Kala-Azar'
    if 'Encephali' in val: return 'Encephalitis Sydrome / JE'
    if 'West Nile' in val: return 'West Nile Fever'
    if 'Adeno' in val: return 'Adenovirus'
    if 'Crimean' in val: return 'Crimean-Congo Hemorrhagic Fever'
    if 'Mumps' in val: return 'Mumps'
    if 'Anthrax' in val: return 'Anthrax'
    if 'Lepto' in val: return 'Leptospirosis'
    
    return val

def main():
    print(f"Loading {RAW_CSV_PATH}...")
    try:
        # Read the messy CSV without headers, setting dtype=str to avoid warnings
        # Use simple pandas read_csv, it usually aligns what it can.
        df = pd.read_csv(RAW_CSV_PATH, header=0, dtype=str, on_bad_lines='skip')
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    print(f"Loaded {len(df)} raw rows. Cleaning data...")

    clean_data = []

    for index, row in df.iterrows():
        # The structure is roughly:
        # Col_1: State
        # Col_2: District
        # Col_3: Disease
        # Col_4: Cases
        # Col_5: Deaths
        # Col_6: Outbreak Start Date
        
        try:
            state = str(row.get('Col_1', '')).strip()
            district = str(row.get('Col_2', '')).strip()
            disease_raw = str(row.get('Col_3', '')).strip()
            cases_raw = row.get('Col_4', '')
            deaths_raw = row.get('Col_5', '')
            date_raw = row.get('Col_6', '')

            # If state or district is completely empty or just nan, skip
            if not state or state.lower() == 'nan' or not district or district.lower() == 'nan':
                continue
                
            cases = clean_cases(cases_raw)
            deaths = clean_cases(deaths_raw)
            date = clean_date(date_raw)
            disease = clean_disease(disease_raw)

            clean_data.append({
                'Date': date,
                'State': state.title(),
                'District': district.title(),
                'Disease': disease,
                'Cases': cases,
                'Deaths': deaths
            })
        except Exception as e:
            # Skip unparseable rows
            continue

    # Convert to new DataFrame
    clean_df = pd.DataFrame(clean_data)
    
    # Drop rows without a valid date
    clean_df = clean_df.dropna(subset=['Date'])
    
    # Sort by date
    clean_df = clean_df.sort_values(by=['Date', 'State', 'District'])

    # Save to clean CSV
    clean_df.to_csv(CLEAN_CSV_PATH, index=False)
    
    print(f"\n=====================================")
    print(f"Data Cleaning Complete!")
    print(f"Total valid outbreaks parsed: {len(clean_df)}")
    print(f"Saved to: {CLEAN_CSV_PATH}")
    print(f"Unique Diseases found: {len(clean_df['Disease'].unique())}")
    print(f"=====================================")
    
    # Print sample of the clean data
    print("\nSAMPLE DATA:")
    print(clean_df.head(10))

if __name__ == "__main__":
    main()
