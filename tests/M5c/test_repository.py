"""Repository save/load tests."""

from __future__ import annotations

import pytest

from app.models import StudySessionCreateRequest
from tests.M5c.helpers import make_persistent_service, make_store, sample_review


@pytest.mark.m5c
class TestSessionRepository:
    def test_save_and_get_round_trip(self, tmp_path):
        service, store, _scheduler = make_persistent_service(tmp_path)
        created = service.create(StudySessionCreateRequest(topic="死锁", course="os"))
        loaded = store.get(created.session_id)
        assert loaded is not None
        assert loaded["state"] == "awaiting_answer"
        assert loaded["topic"] == "死锁"
        assert loaded["questions"][0]["question"]["answer"]

    def test_missing_session_returns_none(self, tmp_path):
        store = make_store(tmp_path)
        assert store.get("missing") is None


@pytest.mark.m5c
class TestReviewRepository:
    def test_save_and_get_review(self, tmp_path):
        store = make_store(tmp_path)
        entry = sample_review()
        store.save_review(entry["file"], entry)
        loaded = store.get_review(entry["file"])
        assert loaded is not None
        assert loaded["review_count"] == 2
        assert store.all()[entry["file"]]["interval_days"] == 2

    def test_identical_review_save_is_idempotent(self, tmp_path):
        store = make_store(tmp_path)
        entry = sample_review()
        first = store.save_review(entry["file"], entry)
        second = store.save_review(entry["file"], dict(entry))
        assert first == second
        assert store.get_review(entry["file"])["review_count"] == 2
