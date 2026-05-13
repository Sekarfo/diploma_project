from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api import router as api_router
from backend.app.services import ensure_postgres_schema
from backend.app.services.errors import DatabaseUnavailableError
from backend.app.services.runtime_metrics_service import get_runtime_metrics_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="Job-Resume Ranking MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")


@app.on_event("startup")
def startup_initialize_services() -> None:
    try:
        ensure_postgres_schema()
    except DatabaseUnavailableError as exc:
        logging.warning("PostgreSQL schema initialization skipped: %s", exc)


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


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui")
