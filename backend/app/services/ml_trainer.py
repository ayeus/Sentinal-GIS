import os
import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier

def retrain_model():
    print("="*40)
    print("🚀 Starting End-to-End ML Model Retraining...")
    print("="*40)
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    clean_csv_path = os.path.join(BASE_DIR, "data", "historical_cases_clean.csv")
    dataset_path = os.path.join(BASE_DIR, "data", "district_ml_dataset.csv")
    model_dir = os.path.join(BASE_DIR, "model")
    model_path = os.path.join(model_dir, "rf_district_model.pkl")
    encoders_path = os.path.join(model_dir, "district_encoders.pkl")

    if not os.path.exists(clean_csv_path):
        print(f"Error: {clean_csv_path} not found.")
        return False

    print(f"Loading cleaned historical data from {clean_csv_path}...")
    df = pd.read_csv(clean_csv_path)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month

    # Standardize Strings
    df['State'] = df['State'].astype(str).str.title().str.strip()
    df['District'] = df['District'].astype(str).str.title().str.strip()
    df['Disease'] = df['Disease'].astype(str).str.title().str.strip()
    df['YearMonth'] = df['Date'].dt.to_period('M')

    # Monthly aggregation
    monthly_data = df.groupby(['State', 'District', 'Disease', 'Year', 'Month', 'YearMonth']).agg({
        'Cases': 'sum'
    }).reset_index()

    if monthly_data.empty:
        print("No monthly aggregated records found.")
        return False

    # Time-series padding
    min_month = monthly_data['YearMonth'].min()
    max_month = monthly_data['YearMonth'].max()
    all_months = pd.period_range(min_month, max_month, freq='M')

    states_districts_diseases = monthly_data[['State', 'District', 'Disease']].drop_duplicates()
    master_idx = pd.MultiIndex.from_product(
        [states_districts_diseases['State'].unique(), 
         states_districts_diseases['District'].unique(), 
         states_districts_diseases['Disease'].unique(), 
         all_months],
        names=['State', 'District', 'Disease', 'YearMonth']
    )

    pair_idx = pd.MultiIndex.from_frame(states_districts_diseases)
    master_df_filtered = master_idx.to_frame(index=False)
    master_df_filtered = master_df_filtered[master_df_filtered.set_index(['State', 'District', 'Disease']).index.isin(pair_idx)]

    full_ts = pd.merge(master_df_filtered, monthly_data, on=['State', 'District', 'Disease', 'YearMonth'], how='left')
    full_ts['Cases'] = full_ts['Cases'].fillna(0)
    full_ts['Month'] = full_ts['YearMonth'].dt.month
    full_ts['Year'] = full_ts['YearMonth'].dt.year
    full_ts = full_ts.sort_values(by=['State', 'District', 'Disease', 'YearMonth'])

    # Shift for lags
    grouped = full_ts.groupby(['State', 'District', 'Disease'])
    full_ts['Cases_Lag1'] = grouped['Cases'].shift(1).fillna(0)
    full_ts['Cases_Lag2'] = grouped['Cases'].shift(2).fillna(0)
    full_ts['Cases_Lag3'] = grouped['Cases'].shift(3).fillna(0)
    full_ts['Target_Cases'] = grouped['Cases'].shift(-1)
    full_ts = full_ts.dropna(subset=['Target_Cases'])

    def categorize_risk(cases):
        if cases > 100: return "High"
        if cases > 20: return "Medium"
        if cases > 0: return "Low"
        return "None"

    full_ts['Risk'] = full_ts['Target_Cases'].apply(categorize_risk)
    full_ts['Rolling_Sum'] = full_ts['Cases'] + full_ts['Cases_Lag1'] + full_ts['Cases_Lag2']
    ml_df = full_ts[full_ts['Rolling_Sum'] > 0].copy()

    if len(ml_df) < 50:
        ml_df = full_ts.copy()

    # Encoders
    le_state = LabelEncoder()
    le_district = LabelEncoder()
    le_disease = LabelEncoder()
    le_target = LabelEncoder()

    ml_df['State_Enc'] = le_state.fit_transform(ml_df['State'].astype(str))
    ml_df['District_Enc'] = le_district.fit_transform(ml_df['District'].astype(str))
    ml_df['Disease_Enc'] = le_disease.fit_transform(ml_df['Disease'].astype(str))
    ml_df['Target_Enc'] = le_target.fit_transform(ml_df['Risk'])

    # Save feature matrix
    ml_df.to_csv(dataset_path, index=False)
    print(f"Updated features saved to {dataset_path}")

    # Retrain Random Forest
    features = ['Month', 'State_Enc', 'District_Enc', 'Disease_Enc', 'Cases_Lag1', 'Cases_Lag2', 'Cases_Lag3']
    X = ml_df[features]
    y = ml_df['Target_Enc']

    print(f"Fitting RandomForestClassifier on {len(X)} records...")
    rf = RandomForestClassifier(n_estimators=150, max_depth=10, random_state=42, n_jobs=-1, class_weight='balanced')
    rf.fit(X, y)

    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(rf, model_path)
    joblib.dump({
        'state': le_state,
        'district': le_district,
        'disease': le_disease,
        'target': le_target
    }, encoders_path)

    print(f"✅ Model and encoders successfully updated at {model_path}")
    return True

if __name__ == "__main__":
    retrain_model()

