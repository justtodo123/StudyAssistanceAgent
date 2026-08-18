"""Restart recovery and corrupt-database fallback."""

from __future__ import annotations

import pytest

from app.models import StudySessionAnswerRequest, StudySessionCreateRequest
from app.study_session import StudySessionService
from tests.M5b.helpers import FakeQaService, FakeQuizService, FakeReviewScheduler
from tests.M5c.helpers import make_persistent_service, make_store


@pytest.mark.m5c
class TestRestartRecovery:
    def test_new_service_restores_open_session(self, tmp_path):
        first, store, _scheduler = make_persistent_service(tmp_path)
        created = first.create(StudySessionCreateRequest(topic="死锁", course="os"))
        restored = StudySessionService(
            qa_service=FakeQaService(),
            quiz_service=FakeQuizService(),
            review_scheduler=FakeReviewScheduler(),
            session_repository=store,
        )
        loaded = restored.get(created.session_id)
        assert loaded.state == "awaiting_answer"
        assert loaded.explanation == created.explanation
        assert loaded.questions[0].question == created.questions[0].question

    def test_restored_session_can_accept_answer(self, tmp_path):
        first, store, scheduler = make_persistent_service(tmp_path)
        created = first.create(StudySessionCreateRequest(topic="死锁", course="os"))
        restored = StudySessionService(
            qa_service=FakeQaService(),
            quiz_service=FakeQuizService(),
            review_scheduler=scheduler,
            session_repository=store,
        )
        result = restored.submit_answer(
            created.session_id,
            StudySessionAnswerRequest(answer="互斥、占有并等待、不可剥夺、循环等待"),
        )
        assert result.state == "completed"
        assert store.get(created.session_id)["state"] == "completed"


@pytest.mark.m5c
class TestCorruptDatabaseFallback:
    def test_garbage_file_is_quarantined_and_replaced(self, tmp_path):
        db_path = tmp_path / "learning_state.sqlite3"
        db_path.write_bytes(b"this is not a sqlite database")
        store = make_store(tmp_path)
        store.save({"session_id": "abc", "course": "os", "topic": "x", "state": "created", "created_at": "t", "updated_at": "t"})
        assert store.get("abc")["session_id"] == "abc"
        assert (tmp_path / "learning_state.sqlite3.corrupt").exists()
