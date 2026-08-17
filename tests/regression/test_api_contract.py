"""API 契约稳定性回归测试。

验证全部 API 端点的请求/响应 schema 不因阶段迭代而破坏。
每阶段开发完成后运行。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


class TestHealthEndpoint:
    """GET /health"""

    def test_status_200(self, test_client):
        resp = test_client.get("/health")
        assert resp.status_code == 200

    def test_has_status_field(self, test_client):
        data = test_client.get("/health").json()
        assert "status" in data
        assert data["status"] == "UP"


class TestSearchEndpoint:
    """POST /api/v1/search"""

    def test_returns_results(self, test_client):
        resp = test_client.post(
            "/api/v1/search",
            json={"question": "进程调度", "top_k": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "mode" in data

    def test_course_filter(self, test_client):
        resp = test_client.post(
            "/api/v1/search",
            json={"question": "排序", "course": "ds", "top_k": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        for r in data["results"]:
            assert "knowledge/ds/" in r["file"] or r["course"] == "ds"

    def test_empty_query_handled(self, test_client):
        resp = test_client.post(
            "/api/v1/search",
            json={"question": "", "top_k": 3},
        )
        # 不应 500
        assert resp.status_code in (200, 400, 422)


class TestQaEndpoint:
    """POST /api/v1/qa"""

    def test_returns_answer_and_sources(self, test_client):
        resp = test_client.post(
            "/api/v1/qa",
            json={"question": "什么是死锁", "course": "os", "use_llm": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert data["sources"], "应有出处"

    def test_sources_have_file_field(self, test_client):
        resp = test_client.post(
            "/api/v1/qa",
            json={"question": "快速排序", "course": "ds", "use_llm": False},
        )
        data = resp.json()
        for s in data["sources"]:
            assert "file" in s
            assert s["file"].startswith("knowledge/")


class TestQuizEndpoint:
    """POST /api/v1/quiz"""

    def test_returns_questions(self, test_client):
        resp = test_client.post(
            "/api/v1/quiz",
            json={"course": "os", "count": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "questions" in data
        assert len(data["questions"]) >= 1


class TestReviewPlanEndpoint:
    """POST /api/v1/review-plan"""

    def test_returns_plan(self, test_client):
        resp = test_client.post(
            "/api/v1/review-plan",
            json={"course": "os"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "days" in data
        assert "summary" in data


class TestReviewLogEndpoint:
    """POST /api/v1/review-log"""

    def test_log_creates_entry(self, test_client):
        resp = test_client.post(
            "/api/v1/review-log",
            json={"file": "knowledge/os/test-regression.md", "course": "os"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "review_count" in data
        assert "interval_days" in data


class TestReviewDueEndpoint:
    """GET /api/v1/review-due"""

    def test_returns_due_list(self, test_client):
        resp = test_client.get("/api/v1/review-due")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_due" in data
        assert "entries" in data
