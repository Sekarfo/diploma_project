"""Simple in-memory per-user rate limiter for AI analysis calls.

The backend runs with --workers 1 (see docker/backend/Dockerfile), so a
process-local dict is sufficient. If the deployment ever scales to multiple
workers, swap this for a Redis-backed counter.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: float


class AIRateLimiter:
    def __init__(self, *, limit: int, window_seconds: float) -> None:
        self._limit = int(limit)
        self._window = float(window_seconds)
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, user_id: str) -> RateLimitDecision:
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            bucket = self._hits.setdefault(user_id, deque())
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self._limit:
                retry_after = max(0.0, bucket[0] + self._window - now)
                return RateLimitDecision(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )
            bucket.append(now)
            return RateLimitDecision(
                allowed=True,
                remaining=self._limit - len(bucket),
                retry_after_seconds=0.0,
            )


# 5 requests per 3 minutes per user — matches the product spec.
ai_analysis_limiter = AIRateLimiter(limit=5, window_seconds=180.0)
