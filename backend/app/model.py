import joblib
import pandas as pd

def load_model():
    model = joblib.load("model/rf_spatial.pkl")
    encoder = joblib.load("model/label_encoder.pkl")
    return model, encoder



def predict_risk(model, encoder, year: int):
    try:
        # Load ML dataset
        df = pd.read_csv("data/final_ml_dataset.csv")

        # Check year exists
        if year not in df["year"].unique():
            return {
                "error": f"No data available for year {year}",
                "available_years": sorted(df["year"].unique().tolist())
            }

        # Filter year
        df_year = df[df["year"] == year].copy()

        features = ["cases_lag1", "cases_lag2", "spatial_lag_cases"]

        # Ensure required columns exist
        missing = [f for f in features if f not in df_year.columns]
        if missing:
            return {
                "error": "Missing feature columns",
                "missing": missing
            }

        X = df_year[features]

        # Predict
        preds = model.predict(X)
        probs = model.predict_proba(X)

        df_year["risk"] = encoder.inverse_transform(preds)
        df_year["confidence"] = probs.max(axis=1)

        return df_year[["state", "risk", "confidence"]].to_dict(orient="records")

    except Exception as e:
        # 🔥 THIS IS WHAT YOU WERE MISSING
        return {
            "error": "Internal prediction error",
            "details": str(e)
        }

