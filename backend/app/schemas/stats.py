from __future__ import annotations

from pydantic import BaseModel


class StatsResponse(BaseModel):
    total_jobs: int
    total_resumes: int


class RuntimeEndpointMetric(BaseModel):
    endpoint: str
    requests: int
    error_rate: float
    latency_ms_p50: float | None = None
    latency_ms_p95: float | None = None


class RuntimeStatsResponse(BaseModel):
    uptime_seconds: float
    total_requests: int
    total_errors: int
    error_rate: float
    latency_ms_p50: float | None = None
    latency_ms_p95: float | None = None
    endpoints: list[RuntimeEndpointMetric]
