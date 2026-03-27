import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import os

print("--- Initializing SentinelGIS Time-Series Pipeline (XGBoost) ---")

# Step 1: Load Data
df = pd.read_csv('data/historical_cases_clean.csv')
df['Date'] = pd.to_datetime(df['Date'])
df['Year'] = df['Date'].dt.year
df['Month'] = df['Date'].dt.month

# Standardize Strings
df['State'] = df['State'].str.title().str.strip()
df['District'] = df['District'].str.title().str.strip()
df['Disease'] = df['Disease'].str.title().str.strip()

# Create YearMonth Period
df['YearMonth'] = df['Date'].dt.to_period('M')

# Group cases per disease per district per month
monthly_data = df.groupby(['State', 'District', 'Disease', 'Year', 'Month', 'YearMonth']).agg({
    'Cases': 'sum'
}).reset_index()

# Step 2: Time-Series Padding (Fill in missing months with 0s)
print("Engineering Time-Series features...")
# Get global min and max months
min_month = monthly_data['YearMonth'].min()
max_month = monthly_data['YearMonth'].max()
all_months = pd.period_range(min_month, max_month, freq='M')

# Create a master framework of all possible combinations
states_districts_diseases = monthly_data[['State', 'District', 'Disease']].drop_duplicates()
master_idx = pd.MultiIndex.from_product(
    [states_districts_diseases['State'].unique(), 
     states_districts_diseases['District'].unique(), 
     states_districts_diseases['Disease'].unique(), 
     all_months],
    names=['State', 'District', 'Disease', 'YearMonth']
)

# Filter combinations to only those that actually appeared in reality to save extreme sparsity
# But we need time-continuity within a State/District/Disease pair
pair_idx = pd.MultiIndex.from_frame(states_districts_diseases)
master_df_filtered = master_idx.to_frame(index=False)
master_df_filtered = master_df_filtered[master_df_filtered.set_index(['State', 'District', 'Disease']).index.isin(pair_idx)]

# Merge master framework with actual data
full_ts = pd.merge(master_df_filtered, monthly_data, on=['State', 'District', 'Disease', 'YearMonth'], how='left')
full_ts['Cases'] = full_ts['Cases'].fillna(0)
full_ts['Month'] = full_ts['YearMonth'].dt.month
full_ts['Year'] = full_ts['YearMonth'].dt.year

# Sort chronologically and create Lags
full_ts = full_ts.sort_values(by=['State', 'District', 'Disease', 'YearMonth'])

# Group by region/disease to calculate temporal shifts
grouped = full_ts.groupby(['State', 'District', 'Disease'])
full_ts['Cases_Lag1'] = grouped['Cases'].shift(1).fillna(0)
full_ts['Cases_Lag2'] = grouped['Cases'].shift(2).fillna(0)
full_ts['Cases_Lag3'] = grouped['Cases'].shift(3).fillna(0)

# Target Variable: Cases in the NEXT month (Future)
full_ts['Target_Cases'] = grouped['Cases'].shift(-1)

# Drop the last month since we can't train on an unknown future target
full_ts = full_ts.dropna(subset=['Target_Cases'])

# Step 3: Define Risk Classes (Target Encoding)
def categorize_risk(cases):
    if cases > 100: return "High"
    if cases > 20: return "Medium"
    if cases > 0: return "Low"
    return "None"

full_ts['Risk'] = full_ts['Target_Cases'].apply(categorize_risk)

# Remove "None" class entirely if we only want to predict outbreaks vs no outbreaks?
# If we have 99% "None", the model will predict "None" always. 
# We should filter the data to only rows where there was SOME activity in the last 3 months
full_ts['Rolling_Sum'] = full_ts['Cases'] + full_ts['Cases_Lag1'] + full_ts['Cases_Lag2']
ml_df = full_ts[full_ts['Rolling_Sum'] > 0].copy()

if len(ml_df) < 100:
    # Fallback to absolute full_ts if dataset is tiny
    ml_df = full_ts.copy()

print(f"Generated Training Dataset with {len(ml_df)} spatial-temporal sequences.")

# Step 4: Encoding Categorical Features
le_state = LabelEncoder()
le_district = LabelEncoder()
le_disease = LabelEncoder()
le_target = LabelEncoder()

# Fit encodings safely
ml_df['State_Enc'] = le_state.fit_transform(ml_df['State'].astype(str))
ml_df['District_Enc'] = le_district.fit_transform(ml_df['District'].astype(str))
ml_df['Disease_Enc'] = le_disease.fit_transform(ml_df['Disease'].astype(str))
ml_df['Target_Enc'] = le_target.fit_transform(ml_df['Risk'])

# Save Dataset for Inference later
ml_df.to_csv('data/district_ml_dataset.csv', index=False)
print("Saved baseline historical inference table to data/district_ml_dataset.csv")

# Feature Matrix
features = ['Month', 'State_Enc', 'District_Enc', 'Disease_Enc', 'Cases_Lag1', 'Cases_Lag2', 'Cases_Lag3']
X = ml_df[features]
y = ml_df['Target_Enc']

print(f"Target Risk Distribution:\n{ml_df['Risk'].value_counts()}")

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Step 5: Advanced Model Training (Random Forest for robust tabular accuracy)
print("Training High-Accuracy Random Forest Classifier...")
rf_model = RandomForestClassifier(
    n_estimators=150,
    max_depth=10,
    random_state=42,
    n_jobs=-1,
    class_weight='balanced'
)

rf_model.fit(X_train, y_train)

# Evaluation
y_pred = rf_model.predict(X_test)
print("\n--- Model Evaluation ---")
print(f"Algorithm: RandomForestClassifier")
print(f"Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%\n")
print(classification_report(y_test, y_pred, target_names=le_target.classes_))

# Save the state-of-the-art model and encoders
os.makedirs('model', exist_ok=True)
joblib.dump(rf_model, 'model/rf_district_model.pkl')
joblib.dump({
    'state': le_state,
    'district': le_district,
    'disease': le_disease,
    'target': le_target
}, 'model/district_encoders.pkl')

print("--- Model Pipeline Execution Complete! Saved into model/ ---")
