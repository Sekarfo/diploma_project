from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app.api import router as api_router
from backend.app.limiter import limiter
from backend.app.services import ensure_postgres_schema
from backend.app.services.errors import DatabaseUnavailableError
from backend.app.services.runtime_metrics_service import get_runtime_metrics_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Job-Resume Ranking MVP", version="0.1.0")

# Attach limiter so slowapi decorators work on the router
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS (Fix #10) ─────────────────────────────────────────────────────────────
_cors_origins_raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost,http://localhost:80")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

app.include_router(api_router)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")


# ── Request ID middleware (Fix #11) ───────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Runtime metrics middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def collect_runtime_metrics(request: Request, call_next):
    if request.url.path.startswith("/ui"):
        return await call_next(request)

    metrics_service = get_runtime_metrics_service()
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency_ms = float((time.perf_counter() - started) * 1000.0)
        metrics_service.record(
            method=request.method,
            path=request.url.path,
            status_code=500,
            latency_ms=latency_ms,
        )
        raise

    latency_ms = float((time.perf_counter() - started) * 1000.0)
    metrics_service.record(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=latency_ms,
    )
    return response


# ── Startup (Fix #7: preload artifacts) ──────────────────────────────────────
@app.on_event("startup")
def startup_initialize_services() -> None:
    # 1. Ensure DB schema exists
    try:
        ensure_postgres_schema()
        logger.info("PostgreSQL schema verified.")
    except DatabaseUnavailableError as exc:
        logger.warning("PostgreSQL schema initialization skipped: %s", exc)

    # 2. Preload ML artifacts so first request doesn't stall
    try:
        from backend.app.api.routes import get_shortlist_service
        get_shortlist_service().artifact_service.get_artifacts()
        logger.info("ML artifacts preloaded successfully.")
    except Exception as exc:
        logger.warning("ML artifact preload failed (will retry on first request): %s", exc)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui")
