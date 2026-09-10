import sys
from pathlib import Path

# Ensure backend root is always in sys.path regardless of execution directory
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

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
from app.services.pipeline_runner import run_pipeline, auto_process_new_pdfs
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
from contextlib import asynccontextmanager

# Configure Scheduler
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Background watcher: checks for new unextracted PDFs every 60 seconds
    scheduler.add_job(auto_process_new_pdfs, "interval", seconds=60)
    # 2. Weekly scheduled scraper
    scheduler.add_job(run_pipeline, "cron", day_of_week="sun", hour=2, minute=0)
    scheduler.start()
    print("✅ APScheduler started: Continuous PDF watcher active (checks every 60s) + Weekly IDSP scraper (Sundays 2:00 AM).")
    yield
    # Shutdown scheduler when app stops
    scheduler.shutdown()
    print("🛑 APScheduler stopped.")

app = FastAPI(
    title="SentinelGIS – Disease Surveillance API",
    version="1.0.0",
    description="AI-powered spatio-temporal disease risk prediction backend",
    lifespan=lifespan
)

from app.config import ALLOWED_ORIGINS, FRONTEND_BUILD_DIR

# ✅ Dynamic CORS configuration for development and cloud deployments
if ALLOWED_ORIGINS == ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# 🔹 Load ML model & geo data ONCE at startup
model, encoder = load_model()
geojson = load_geojson()

# 🔹 Health check endpoint for cloud monitoring (Render, AWS, Railway)
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "SentinelGIS API"}

# 🔹 Root route: serves React UI if build exists, otherwise API status
@app.get("/")
def root():
    if FRONTEND_BUILD_DIR.exists() and (FRONTEND_BUILD_DIR / "index.html").exists():
        from fastapi.responses import FileResponse
        return FileResponse(str(FRONTEND_BUILD_DIR / "index.html"))
    return {"status": "API is running", "docs": "/docs"}


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

# 🔹 Admin API for Pipeline & PDF Upload
from fastapi import BackgroundTasks, UploadFile, File
import shutil
from pathlib import Path

@app.post("/api/admin/trigger-pipeline")
def trigger_pipeline(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline)
    return {"message": "Automated data pipeline triggered in the background. Check server logs for progress."}

@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a new IDSP PDF outbreak report.
    Automatically extracts the tables, cleans the dataset, and retrains the ML model.
    """
    if not file.filename.lower().endswith(".pdf"):
        return {"status": "error", "message": "Only PDF files are supported"}
    
    upload_dir = Path("idsp_pdfs")
    upload_dir.mkdir(exist_ok=True)
    destination = upload_dir / file.filename
    
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    print(f"📥 Received uploaded PDF: {file.filename}. Triggering auto-processing & retraining...")
    result = auto_process_new_pdfs()
    return {
        "status": "success",
        "file": file.filename,
        "pipeline": result
    }

# 🔹 Production Static Files Serving & SPA Fallback
# If frontend build exists, serve it seamlessly on the same port
if FRONTEND_BUILD_DIR.exists() and (FRONTEND_BUILD_DIR / "index.html").exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    if (FRONTEND_BUILD_DIR / "static").exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_BUILD_DIR / "static")), name="static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't hijack API or documentation routes
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return None
        candidate = FRONTEND_BUILD_DIR / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(FRONTEND_BUILD_DIR / "index.html"))


