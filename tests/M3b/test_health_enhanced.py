"""M3b 增强健康检查测试。

验证 /health 端点返回更多运维信息。
M3b 开发后补充具体断言。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.mark.m3b
class TestEnhancedHealth:
    """增强健康检查端点。"""

    def test_health_returns_basic_fields(self, test_client):
        """health 端点应返回基本字段。"""
        resp = test_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] == "UP"

    def test_health_shows_vector_engine(self, test_client):
        """health 应显示向量引擎类型。"""
        resp = test_client.get("/health")
        data = resp.json()
        assert "vector_engine" in data

    def test_health_shows_knowledge_root(self, test_client):
        """health 应显示知识库路径。"""
        resp = test_client.get("/health")
        data = resp.json()
        assert "knowledge_root" in data

    @pytest.mark.m3b
    def test_health_shows_index_stats(self, test_client):
        """M3b: health 应显示索引统计（条目数、缓存状态）。"""
        resp = test_client.get("/health")
        data = resp.json()
        # M3b 开发后取消注释：
        # assert "index_size" in data, "应返回索引条目数"
        # assert "cache_status" in data, "应返回缓存状态"

    @pytest.mark.m3b
    def test_health_shows_latency_stats(self, test_client):
        """M3b: health 应包含延迟统计。"""
        # 先触发几次检索
        for _ in range(3):
            test_client.post("/api/v1/search", json={"question": "测试", "top_k": 1})

        resp = test_client.get("/health")
        data = resp.json()
        # M3b 开发后取消注释：
        # assert "avg_latency_ms" in data, "应返回平均延迟"
