import pandas as pd
import joblib

def load_rf_model():
    model = joblib.load("model/rf_district_model.pkl")
    encoders = joblib.load("model/district_encoders.pkl")
    return model, encoders

def predict_risk(year: int, disease: str = None):
    try:
        model, encoders = load_rf_model()
        
        df = pd.read_csv("data/district_ml_dataset.csv")

        if disease:
            df = df[df['Disease'].str.lower() == disease.lower()]

        available_years = sorted(df["Year"].unique().tolist())
        if year not in available_years:
            return {
                "error": f"No baseline feature data available for year {year}",
                "available_years": available_years
            }

        df_target = df[df["Year"] == year].copy()

        if df_target.empty:
            return {"error": f"No data after filtering for {year} / {disease}"}

        features = ['Month', 'State_Enc', 'District_Enc', 'Disease_Enc', 'Cases_Lag1', 'Cases_Lag2', 'Cases_Lag3']
        X = df_target[features]

        preds = model.predict(X)
        probs = model.predict_proba(X)

        df_target["predicted_risk_enc"] = preds
        df_target["confidence"] = probs.max(axis=1)
        
        le_target = encoders['target']
        df_target["risk"] = le_target.inverse_transform(preds)

        # A district might have multiple months in a year. 
        # For the dashboard annual map, we take the highest risk recorded for that district over the year.
        # Assign numeric weights to risk to easily find the max.
        risk_weights = {"High": 3, "Medium": 2, "Low": 1, "None": 0}
        df_target["risk_weight"] = df_target["risk"].map(risk_weights)

        # Find the row with the maximum risk weight for each District
        idx_max = df_target.groupby(['State', 'District'])['risk_weight'].idxmax()
        highest_risk_df = df_target.loc[idx_max]

        results = highest_risk_df[["State", "District", "risk", "confidence"]]
        return results.to_dict(orient="records")

    except Exception as e:
        return {"error": f"Inference failed: {str(e)}"}