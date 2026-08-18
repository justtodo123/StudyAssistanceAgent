"""Lightweight process-local metrics and structured logging helpers."""

from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict, deque
from statistics import fmean
from typing import Any

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)


class MetricsRegistry:
    """Collect bounded, non-sensitive metrics for health checks and diagnostics."""

    def __init__(self, max_samples: int = 200) -> None:
        self.max_samples = max_samples
        self._lock = threading.RLock()
        self._latencies: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=self.max_samples)
        )
        self._requests: dict[str, int] = defaultdict(int)
        self._result_counts: dict[str, int] = defaultdict(int)
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_status = "unknown"
        self._index_size = 0

    def record(
        self,
        operation: str,
        duration_ms: float,
        result_count: int,
        *,
        cache_hit: bool | None = None,
    ) -> None:
        duration = round(max(0.0, duration_ms), 3)
        with self._lock:
            self._latencies[operation].append(duration)
            self._requests[operation] += 1
            self._result_counts[operation] += max(0, result_count)
            if cache_hit is not None:
                if cache_hit:
                    self._cache_hits += 1
                else:
                    self._cache_misses += 1
                self._cache_status = "warm" if cache_hit else "cold"

    def record_index_cache(self, *, hit: bool, index_size: int) -> None:
        with self._lock:
            self._index_size = max(0, index_size)
            self._cache_status = "warm" if hit else "cold"
            if hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1

    def set_index_size(self, index_size: int) -> None:
        with self._lock:
            self._index_size = max(0, index_size)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            all_samples = [sample for values in self._latencies.values() for sample in values]
            avg = fmean(all_samples) if all_samples else 0.0
            return {
                "index_size": self._index_size,
                "cache_status": self._cache_status,
                "avg_latency_ms": round(avg, 3),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "requests": dict(self._requests),
            }

    def reset(self) -> None:
        with self._lock:
            self._latencies.clear()
            self._requests.clear()
            self._result_counts.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self._cache_status = "unknown"
            self._index_size = 0


metrics = MetricsRegistry()


def log_operation(
    operation: str,
    *,
    duration_ms: float,
    result_count: int,
    course: str | None = None,
    mode: str | None = None,
    cache_hit: bool | None = None,
) -> None:
    """Emit a JSON log containing only safe, bounded operation metadata."""
    payload: dict[str, Any] = {
        "event": operation,
        "duration_ms": round(max(0.0, duration_ms), 3),
        "result_count": max(0, result_count),
    }
    if course:
        payload["course"] = course
    if mode:
        payload["mode"] = mode
    if cache_hit is not None:
        payload["cache_hit"] = cache_hit
    logger.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))
