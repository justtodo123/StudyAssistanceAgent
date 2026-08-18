"""M5c helpers for SQLite learning-state tests."""

from __future__ import annotations

import json
from pathlib import Path

from app.learning_store import SqliteLearningStore
from app.models import QuizQuestion
from app.study_session import StudySessionService
from tests.M5b.helpers import FakeQaService, FakeQuizService, FakeReviewScheduler


def make_store(tmp_path: Path, json_history: Path | None = None) -> SqliteLearningStore:
    return SqliteLearningStore(tmp_path / "learning_state.sqlite3", json_history_path=json_history)


def make_persistent_service(tmp_path: Path) -> tuple[StudySessionService, SqliteLearningStore, FakeReviewScheduler]:
    store = make_store(tmp_path)
    scheduler = FakeReviewScheduler()
    service = StudySessionService(
        qa_service=FakeQaService(),
        quiz_service=FakeQuizService(),
        review_scheduler=scheduler,
        session_repository=store,
    )
    return service, store, scheduler


def sample_review(file_key: str = "knowledge/os/deadlock.md", count: int = 2) -> dict:
    return {
        "file": file_key,
        "course": "os",
        "review_count": count,
        "last_reviewed": "2026-08-17T10:00:00",
        "next_review": "2026-08-19T10:00:00",
        "interval_days": 2,
    }


def write_json_history(path: Path, entries: dict) -> None:
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
