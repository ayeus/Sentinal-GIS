from fastapi import FastAPI
from app.model import load_model, predict_risk
from app.data_loader import load_geojson
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Disease Surveillance API",
    version="1.0"
)

# ✅ ADD THIS BLOCK
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model and data at startup
model, encoder = load_model()
geojson = load_geojson()

@app.get("/")
def root():
    return {"status": "API is running"}

@app.get("/risk-map")
def get_risk_map(year: int):
    return predict_risk(model, encoder, year)

@app.get("/geojson")
def get_geojson():
    return geojson

