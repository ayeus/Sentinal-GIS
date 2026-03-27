import joblib
import pandas as pd

def load_model():
    model = joblib.load("model/rf_spatial.pkl")
    encoder = joblib.load("model/label_encoder.pkl")
    return model, encoder



def predict_risk(model, encoder, year: int):
    try:
        # Load dataset
        df = pd.read_csv("data/final_ml_dataset.csv")

        if df.empty:
            return {"error": "Dataset is empty"}

        # Validate year column
        if "year" not in df.columns:
            return {"error": "Dataset missing 'year' column"}

        # Check if requested year exists
        available_years = sorted(df["year"].unique())

        if year not in available_years:
            return {
                "error": f"No data available for year {year}",
                "available_years": available_years
            }

        # Filter dataset by year
        df_year = df[df["year"] == year].copy()

        if df_year.empty:
            return {"error": f"No records found for year {year}"}

        # Required ML features
        features = ["cases_lag1", "cases_lag2", "spatial_lag_cases"]

        # Validate features
        missing_features = [f for f in features if f not in df_year.columns]

        if missing_features:
            return {
                "error": "Missing feature columns",
                "missing": missing_features
            }

        # Prepare feature matrix
        X = df_year[features]

        # Model prediction
        predictions = model.predict(X)
        probabilities = model.predict_proba(X)

        # Attach predictions
        df_year["risk"] = encoder.inverse_transform(predictions)
        df_year["confidence"] = probabilities.max(axis=1)

        # Clean output
        results = df_year[["state", "year", "risk", "confidence"]]

        return results.to_dict(orient="records")

    except Exception as e:
        return {
            "error": "Internal prediction error",
            "details": str(e)
        }