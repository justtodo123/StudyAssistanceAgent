"""Concrete health endpoint assertions for M3b observability."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.mark.m3b
class TestEnhancedHealth:
    def test_health_returns_basic_fields(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert isinstance(data["vector_engine"], str)
        assert isinstance(data["knowledge_root"], str)

    def test_health_shows_vector_engine(self, test_client):
        data = test_client.get("/health").json()
        assert data["vector_engine"] in {
            "sqlite",
            "linear",
            "sqlite-unavailable",
            "linear-unavailable",
        }

    def test_health_shows_knowledge_root(self, test_client):
        data = test_client.get("/health").json()
        assert data["knowledge_root"].endswith("knowledge")

    def test_health_shows_index_stats(self, test_client):
        data = test_client.get("/health").json()
        assert isinstance(data["index_size"], int)
        assert data["index_size"] > 0
        assert data["cache_status"] in {"cold", "warm", "unknown"}

    def test_health_shows_latency_stats(self, test_client):
        for _ in range(3):
            response = test_client.post(
                "/api/v1/search", json={"question": "\u6d4b\u8bd5", "top_k": 1}
            )
            assert response.status_code == 200

        data = test_client.get("/health").json()
        assert isinstance(data["avg_latency_ms"], (int, float))
        assert data["avg_latency_ms"] >= 0
