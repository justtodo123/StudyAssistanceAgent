"""Workbench learning loop uses official session and due APIs."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.M5b.helpers import make_service


@pytest.fixture
def workbench_client():
    service, qa, quiz, scheduler = make_service()
    with patch("app.main._study_sessions", service):
        yield TestClient(app), service, qa, quiz, scheduler


@pytest.mark.m5d
class TestWorkbenchFlow:
    def test_review_due_is_available(self, workbench_client):
        client, *_ = workbench_client
        response = client.get("/api/v1/review-due")
        assert response.status_code == 200
        payload = response.json()
        assert "entries" in payload
        assert "total_due" in payload

    def test_official_session_loop_completes(self, workbench_client):
        client, _service, _qa, _quiz, scheduler = workbench_client
        created = client.post(
            "/api/v1/study-sessions",
            json={"topic": "死锁", "course": "os", "question_count": 1, "use_llm": False},
        )
        assert created.status_code == 200
        session = created.json()
        assert session["state"] == "awaiting_answer"
        assert session["explanation"]
        assert session["sources"]
        assert session["questions"]

        answered = client.post(
            f"/api/v1/study-sessions/{session['session_id']}/answers",
            json={"answer": "互斥、占有并等待、不可剥夺、循环等待"},
        )
        assert answered.status_code == 200
        completed = answered.json()
        assert completed["state"] == "completed"
        assert completed["review"]["next_review"]
        assert scheduler.logged

    def test_workbench_page_still_served_during_session_use(self, workbench_client):
        client, *_ = workbench_client
        page = client.get("/")
        due = client.get("/api/v1/review-due")
        assert page.status_code == 200
        assert due.status_code == 200
        assert "今日待复习" in page.text
        assert "知识讲解" in page.text
        assert "下次复习" in page.text or "next-review" in page.text