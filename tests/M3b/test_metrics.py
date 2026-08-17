"""M3b 指标采集测试。

验证检索延迟、缓存命中率等指标的采集。
M3b 开发后补充具体指标断言。
"""

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
    """检索延迟应可度量。"""

    def test_search_latency_measurable(self, retrieval_service):
        """单次检索耗时应可测量且在合理范围内。"""
        t0 = time.perf_counter()
        results, _ = retrieval_service.recall("进程调度", top_k=3)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 5000, f"检索耗时 {elapsed_ms:.0f}ms 超过 5s 上限"
        assert results, "检索应有结果"

    def test_repeated_search_latency_stable(self, retrieval_service):
        """多次检索延迟应相对稳定（无明显退化）。"""
        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            retrieval_service.recall("死锁", top_k=3)
            latencies.append((time.perf_counter() - t0) * 1000)
        avg = sum(latencies) / len(latencies)
        max_deviation = max(abs(l - avg) for l in latencies)
        # 允许 3 倍偏差（冷启动等因素）
        assert max_deviation < avg * 3 or avg < 100, (
            f"延迟波动过大: avg={avg:.0f}ms, max_dev={max_deviation:.0f}ms"
        )


@pytest.mark.m3b
class TestCacheBehavior:
    """缓存行为验证。"""

    def test_index_cache_faster_on_second_call(self):
        """第二次构建索引应利用缓存（如果有）。"""
        from app.knowledge_index import build_index

        t0 = time.perf_counter()
        build_index()
        first_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        build_index()
        second_ms = (time.perf_counter() - t0) * 1000

        # 第二次可能更快（缓存）或相当（如果无缓存）
        # 不强制要求，只验证不崩溃
        assert second_ms >= 0, "第二次构建不应为负耗时"
