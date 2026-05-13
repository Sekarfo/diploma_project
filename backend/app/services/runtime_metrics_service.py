from __future__ import annotations

import time
from collections import defaultdict, deque
from functools import lru_cache
from threading import Lock


class RuntimeMetricsService:
    def __init__(self, max_samples: int = 5000, max_endpoint_count: int = 20) -> None:
        self._max_endpoint_count = max_endpoint_count
        self._lock = Lock()
        self._started_at = time.time()
        self._samples: deque[dict[str, object]] = deque(maxlen=max_samples)
        self._total_requests = 0
        self._total_errors = 0

    @staticmethod
    def _percentile(values: list[float], p: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        if len(ordered) == 1:
            return float(ordered[0])
        index = (len(ordered) - 1) * p
        lower = int(index)
        upper = min(lower + 1, len(ordered) - 1)
        if lower == upper:
            return float(ordered[lower])
        weight = index - lower
        return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)

    def record(self, *, method: str, path: str, status_code: int, latency_ms: float) -> None:
        sample = {
            "method": str(method),
            "path": str(path),
            "status_code": int(status_code),
            "latency_ms": float(latency_ms),
        }
        with self._lock:
            self._total_requests += 1
            if int(status_code) >= 500:
                self._total_errors += 1
            self._samples.append(sample)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            total_requests = int(self._total_requests)
            total_errors = int(self._total_errors)
            samples = list(self._samples)
            uptime_seconds = float(time.time() - self._started_at)

        latency_values = [float(sample["latency_ms"]) for sample in samples]
        error_rate = float(total_errors / total_requests) if total_requests > 0 else 0.0

        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for sample in samples:
            key = f"{sample['method']} {sample['path']}"
            grouped[key].append(sample)

        endpoint_rows: list[dict[str, float | int | str | None]] = []
        for key, endpoint_samples in grouped.items():
            endpoint_latencies = [float(item["latency_ms"]) for item in endpoint_samples]
            endpoint_errors = sum(1 for item in endpoint_samples if int(item["status_code"]) >= 500)
            endpoint_rows.append(
                {
                    "endpoint": key,
                    "requests": int(len(endpoint_samples)),
                    "error_rate": float(endpoint_errors / len(endpoint_samples)) if endpoint_samples else 0.0,
                    "latency_ms_p50": self._percentile(endpoint_latencies, 0.50),
                    "latency_ms_p95": self._percentile(endpoint_latencies, 0.95),
                }
            )

        endpoint_rows.sort(key=lambda row: int(row["requests"]), reverse=True)
        endpoint_rows = endpoint_rows[: self._max_endpoint_count]

        return {
            "uptime_seconds": uptime_seconds,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": error_rate,
            "latency_ms_p50": self._percentile(latency_values, 0.50),
            "latency_ms_p95": self._percentile(latency_values, 0.95),
            "endpoints": endpoint_rows,
        }


@lru_cache(maxsize=1)
def get_runtime_metrics_service() -> RuntimeMetricsService:
    return RuntimeMetricsService()
