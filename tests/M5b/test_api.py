"""API contract tests for study sessions."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.M5b.helpers import make_service


@pytest.fixture
def api_bundle():
    service, qa, quiz, scheduler = make_service()
    with patch("app.main._study_sessions", service):
        yield TestClient(app), service, qa, quiz, scheduler


@pytest.mark.m5b
class TestStudySessionApi:
    def test_create_and_get_session(self, api_bundle):
        client, _service, _qa, _quiz, _scheduler = api_bundle
        created = client.post(
            "/api/v1/study-sessions",
            json={"topic": "死锁", "course": "os"},
        )
        assert created.status_code == 200
        payload = created.json()
        assert payload["state"] == "awaiting_answer"
        assert payload["sources"]
        assert payload["tool_trace"]
        fetched = client.get(f"/api/v1/study-sessions/{payload['session_id']}")
        assert fetched.status_code == 200
        assert fetched.json()["session_id"] == payload["session_id"]

    def test_answer_endpoint_completes_session(self, api_bundle):
        client, _service, _qa, _quiz, scheduler = api_bundle
        session_id = client.post(
            "/api/v1/study-sessions",
            json={"topic": "死锁", "course": "os"},
        ).json()["session_id"]
        answered = client.post(
            f"/api/v1/study-sessions/{session_id}/answers",
            json={"answer": "互斥、占有并等待、不可剥夺、循环等待"},
        )
        assert answered.status_code == 200
        data = answered.json()
        assert data["state"] == "completed"
        assert data["review"]["interval_days"] == 1
        assert scheduler.logged

    def test_missing_session_returns_404(self, api_bundle):
        client, *_ = api_bundle
        assert client.get("/api/v1/study-sessions/missing").status_code == 404
        assert (
            client.post(
                "/api/v1/study-sessions/missing/answers",
                json={"answer": "test"},
            ).status_code
            == 404
        )

    def test_answer_after_complete_returns_409(self, api_bundle):
        client, *_ = api_bundle
        session_id = client.post(
            "/api/v1/study-sessions",
            json={"topic": "死锁", "course": "os"},
        ).json()["session_id"]
        client.post(
            f"/api/v1/study-sessions/{session_id}/answers",
            json={"answer": "互斥、占有并等待、不可剥夺、循环等待"},
        )
        conflict = client.post(
            f"/api/v1/study-sessions/{session_id}/answers",
            json={"answer": "again"},
        )
        assert conflict.status_code == 409

    def test_invalid_course_returns_422(self, api_bundle):
        client, *_ = api_bundle
        resp = client.post(
            "/api/v1/study-sessions",
            json={"topic": "死锁", "course": "ml"},
        )
        assert resp.status_code == 422

    def test_create_works_without_llm(self, api_bundle):
        client, _service, qa, *_ = api_bundle
        resp = client.post(
            "/api/v1/study-sessions",
            json={"topic": "死锁", "course": "os", "use_llm": False},
        )
        assert resp.status_code == 200
        assert qa.calls == 1
        assert resp.json()["state"] in {"awaiting_answer", "completed"}
