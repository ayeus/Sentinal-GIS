from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Existing imports (kept)
from app.model import load_model, predict_risk
from app.data_loader import load_geojson

# New imports (Phase 2 & 7)
from app.routes.predict import router as predict_router
from app.routes.current_status import router as status_router
from app.routes.spread import router as spread_router
from app.routes.analytics import router as analytics_router
from app.routes.realtime import router as realtime_router

app = FastAPI(
    title="SentinelGIS – Disease Surveillance API",
    version="1.0.0",
    description="AI-powered spatio-temporal disease risk prediction backend"
)

# ✅ CORS (frontend friendly)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173"  # Vite support
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Load ML model & geo data ONCE at startup
model, encoder = load_model()
geojson = load_geojson()

# 🔹 Basic health check
@app.get("/")
def root():
    return {"status": "API is running"}

# 🔹 Existing endpoint (kept)
@app.get("/risk-map")
def get_risk_map(year: int):
    return predict_risk(model, encoder, year)

# 🔹 Existing endpoint (kept)
@app.get("/geojson")
def get_geojson():
    return geojson

# 🔹 Phase 7 API (added)
app.include_router(predict_router)

# 🔹 Phase 2 API (added)
app.include_router(status_router)

# 🔹 Phase 3 Spread API (added)
app.include_router(spread_router)

# 🔹 Phase 3 Analytics API (added)
app.include_router(analytics_router)

# 🔹 Phase 4 Real-Time API (added)
app.include_router(realtime_router)
