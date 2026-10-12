import sys
from pathlib import Path

# Ensure backend root is always in sys.path regardless of execution directory
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import hmac
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import (
    ADMIN_API_KEY,
    ALLOWED_ORIGINS,
    ENABLE_SCHEDULER,
    FRONTEND_BUILD_DIR,
    MAX_UPLOAD_MB,
    PDF_DIR,
    PDF_WATCH_INTERVAL_SECONDS,
    SCRAPE_INTERVAL_HOURS,
    STARTUP_CHECK_DELAY_SECONDS,
)
from app.routes.forecast import router as forecast_router
from app.routes.current_status import router as status_router
from app.routes.spread import router as spread_router
from app.routes.analytics import router as analytics_router
from app.routes.realtime import router as realtime_router
from app.services.pipeline_runner import run_pipeline, auto_process_new_pdfs

# Configure Scheduler
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not ENABLE_SCHEDULER:
        print("ℹ️ APScheduler disabled (ENABLE_SCHEDULER=false).")
        yield
        return

    # 1. Background watcher: checks for new unextracted PDFs
    scheduler.add_job(auto_process_new_pdfs, "interval", seconds=PDF_WATCH_INTERVAL_SECONDS)
    # 2. Scheduled check of the IDSP portal for new bulletins
    scheduler.add_job(run_pipeline, "interval", hours=SCRAPE_INTERVAL_HOURS)
    # 3. One check shortly after start-up, so a fresh deployment does not wait for the nightly run
    scheduler.add_job(run_pipeline, "date", run_date=datetime.now() + timedelta(seconds=STARTUP_CHECK_DELAY_SECONDS))
    scheduler.start()
    print(
        f"✅ APScheduler started: PDF watcher every {PDF_WATCH_INTERVAL_SECONDS}s + "
        f"check for new IDSP bulletins every {SCRAPE_INTERVAL_HOURS:g}h (and at start-up)."
    )
    yield
    # Shutdown scheduler when app stops
    scheduler.shutdown()
    print("🛑 APScheduler stopped.")

app = FastAPI(
    title="SentinelGIS – Disease Surveillance API",
    version="1.0.0",
    description="District-level outbreak surveillance and forecasting from IDSP weekly outbreak reports",
    lifespan=lifespan
)

# ✅ Dynamic CORS configuration for development and cloud deployments
# (credentials cannot be combined with a wildcard origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOWED_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_admin(x_api_key: Optional[str] = Header(default=None)):
    """Guards admin endpoints when ADMIN_API_KEY is configured."""
    if ADMIN_API_KEY and not hmac.compare_digest(x_api_key or "", ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


# 🔹 Health check endpoint for cloud monitoring (Render, AWS, Railway)
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "SentinelGIS API"}

# 🔹 Root route: serves React UI if build exists, otherwise API status
@app.get("/")
def root():
    if (FRONTEND_BUILD_DIR / "index.html").exists():
        return FileResponse(str(FRONTEND_BUILD_DIR / "index.html"))
    return {"status": "API is running", "docs": "/docs"}


# 🔹 Forecast API
app.include_router(forecast_router)

# 🔹 Phase 2 API
app.include_router(status_router)

# 🔹 Phase 3 Spread API
app.include_router(spread_router)

# 🔹 Phase 3 Analytics API
app.include_router(analytics_router)

# 🔹 Phase 4 Real-Time API
app.include_router(realtime_router)

# 🔹 Admin API for Pipeline & PDF Upload
@app.post("/api/admin/trigger-pipeline", dependencies=[Depends(require_admin)])
def trigger_pipeline(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline)
    return {"message": "Automated data pipeline triggered in the background. Check server logs for progress."}

@app.post("/api/upload-pdf", dependencies=[Depends(require_admin)])
def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a new IDSP PDF outbreak report.
    Automatically extracts the tables, cleans the dataset, and retrains the ML model.
    """
    # Keep only the base name: the client controls this string
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    destination = PDF_DIR / filename
    # Written under a temp name so the PDF watcher never sees a partial file
    tmp_path = PDF_DIR / (filename + ".part")

    try:
        written = 0
        with open(tmp_path, "wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                if written == 0 and not chunk.startswith(b"%PDF-"):
                    raise HTTPException(status_code=400, detail="File is not a valid PDF")
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=413, detail=f"PDF exceeds the {MAX_UPLOAD_MB} MB upload limit")
                buffer.write(chunk)
        if written == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        os.replace(tmp_path, destination)
    finally:
        tmp_path.unlink(missing_ok=True)

    # Extraction is quick but retraining takes several minutes: run it after responding
    print(f"📥 Received uploaded PDF: {filename}. Processing & retraining in the background...")
    background_tasks.add_task(auto_process_new_pdfs)
    return {
        "status": "success",
        "file": filename,
        "pipeline": {
            "status": "processing",
            "message": "Bulletin saved. Its outbreaks are being extracted and the forecast retrained; "
                       "this takes several minutes. Reload the page afterwards.",
        },
    }

# 🔹 Production Static Files Serving & SPA Fallback
# If frontend build exists, serve it seamlessly on the same port
if (FRONTEND_BUILD_DIR / "index.html").exists():
    _BUILD_ROOT = FRONTEND_BUILD_DIR.resolve()

    if (FRONTEND_BUILD_DIR / "static").exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_BUILD_DIR / "static")), name="static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't hijack API or documentation routes
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json")) or full_path == "api":
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (_BUILD_ROOT / full_path).resolve()
        # Never serve anything outside the build directory
        if candidate.is_file() and _BUILD_ROOT in candidate.parents:
            return FileResponse(str(candidate))
        return FileResponse(str(_BUILD_ROOT / "index.html"))
