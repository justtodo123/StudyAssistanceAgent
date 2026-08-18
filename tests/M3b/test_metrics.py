"""Latency and cache metric assertions for M3b observability."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.mark.m3b
class TestRetrievalLatency:
    def test_search_latency_measurable(self, retrieval_service):
        started = time.perf_counter()
        results, _ = retrieval_service.recall("\u8fdb\u7a0b\u8c03\u5ea6", top_k=3)
        elapsed_ms = (time.perf_counter() - started) * 1000
        assert elapsed_ms < 5000
        assert results

    def test_repeated_search_latency_stable(self, retrieval_service):
        latencies = []
        for _ in range(5):
            started = time.perf_counter()
            retrieval_service.recall("\u6b7b\u9501", top_k=3)
            latencies.append((time.perf_counter() - started) * 1000)
        average = sum(latencies) / len(latencies)
        max_deviation = max(abs(latency - average) for latency in latencies)
        assert max_deviation < average * 3 or average < 100


@pytest.mark.m3b
class TestCacheBehavior:
    def test_index_cache_build_does_not_fail(self):
        from app.knowledge_index import build_index

        started = time.perf_counter()
        first = build_index()
        first_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        second = build_index()
        second_ms = (time.perf_counter() - started) * 1000

        assert first
        assert len(second) == len(first)
        assert first_ms >= 0
        assert second_ms >= 0


@pytest.mark.m3b
def test_repeated_search_updates_cache_metrics():
    from app.observability import metrics
    from app.retrieval import MultiRecallService

    metrics.reset()
    service = MultiRecallService()
    service.recall("\u6b7b\u9501", top_k=3)
    service.recall("\u6b7b\u9501", top_k=3)

    snapshot = metrics.snapshot()
    assert snapshot["cache_misses"] >= 1
    assert snapshot["cache_hits"] >= 1
    assert snapshot["avg_latency_ms"] >= 0
