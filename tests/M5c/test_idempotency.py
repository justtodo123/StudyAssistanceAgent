"""Idempotent answer and review writes."""

from __future__ import annotations

import pytest

from app.learning_store import ReviewHistoryRepositoryAdapter
from app.models import ReviewLogRequest, StudySessionAnswerRequest, StudySessionCreateRequest
from app.review_scheduler import ReviewSchedulerService
from tests.M5c.helpers import make_persistent_service, make_store


@pytest.mark.m5c
class TestIdempotentWrites:
    def test_duplicate_answer_does_not_consume_another_attempt(self, tmp_path):
        service, store, _scheduler = make_persistent_service(tmp_path)
        created = service.create(StudySessionCreateRequest(topic="死锁", course="os"))
        first = service.submit_answer(
            created.session_id,
            StudySessionAnswerRequest(answer="不知道"),
        )
        second = service.submit_answer(
            created.session_id,
            StudySessionAnswerRequest(answer="不知道"),
        )
        assert first.state == "awaiting_answer"
        assert second.attempt_count == first.attempt_count == 1
        assert len(store.list_answer_attempts(created.session_id)) == 1

    def test_duplicate_review_from_same_session_does_not_increment(self, tmp_path):
        store = make_store(tmp_path)
        scheduler = ReviewSchedulerService(repository=ReviewHistoryRepositoryAdapter(store))
        req = ReviewLogRequest(
            file="knowledge/os/deadlock.md",
            course="os",
            source_session_id="session-1",
        )
        first = scheduler.log_review(req)
        second = scheduler.log_review(req)
        assert first["review_count"] == 1
        assert second["review_count"] == 1
        assert store.get_review(req.file)["review_count"] == 1

    def test_review_without_source_still_increments(self, tmp_path):
        store = make_store(tmp_path)
        scheduler = ReviewSchedulerService(repository=ReviewHistoryRepositoryAdapter(store))
        req = ReviewLogRequest(file="knowledge/os/deadlock.md", course="os")
        scheduler.log_review(req)
        again = scheduler.log_review(req)
        assert again["review_count"] == 2
