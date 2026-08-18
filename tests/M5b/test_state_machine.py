"""Study session state-machine tests."""

from __future__ import annotations

import pytest

from app.models import QuizQuestion, StudySessionAnswerRequest, StudySessionCreateRequest
from app.study_session import IllegalSessionStateError, SessionNotFoundError
from tests.M5b.helpers import make_service


@pytest.mark.m5b
class TestCreateSession:
    def test_create_reaches_awaiting_answer_with_trace(self):
        service, qa, quiz, scheduler = make_service()
        session = service.create(
            StudySessionCreateRequest(topic="死锁", course="os")
        )
        assert session.state == "awaiting_answer"
        assert session.explanation
        assert session.sources[0].file == "knowledge/os/deadlock.md"
        assert session.questions[0].id == "q1"
        assert session.current_question_id == "q1"
        assert qa.calls == 1
        assert quiz.calls >= 1
        assert scheduler.logged == []
        steps = [item.step for item in session.tool_trace]
        assert steps[:4] == ["create", "qa", "explain", "quiz"]
        assert "answer" not in session.questions[0].model_dump()

    def test_create_without_questions_completes_and_logs_review(self):
        service, _qa, quiz, scheduler = make_service(questions=[])
        quiz.questions = []
        session = service.create(
            StudySessionCreateRequest(topic="死锁", course="os")
        )
        assert session.state == "completed"
        assert session.review is not None
        assert scheduler.logged
        assert any(item.status == "fallback" for item in session.tool_trace)


@pytest.mark.m5b
class TestAnswerFlow:
    def test_correct_answer_completes_and_logs_review(self):
        service, _qa, _quiz, scheduler = make_service()
        created = service.create(StudySessionCreateRequest(topic="死锁", course="os"))
        result = service.submit_answer(
            created.session_id,
            StudySessionAnswerRequest(answer="互斥、占有并等待、不可剥夺、循环等待"),
        )
        assert result.state == "completed"
        assert result.last_evaluation is not None
        assert result.last_evaluation.correct is True
        assert result.score == 1.0
        assert result.review is not None
        assert scheduler.logged[0].file == "knowledge/os/deadlock.md"
        assert [item.step for item in result.tool_trace][-2:] == ["evaluate", "review-log"]

    def test_first_wrong_answer_stays_open_with_hint(self):
        service, _qa, _quiz, scheduler = make_service()
        created = service.create(StudySessionCreateRequest(topic="死锁", course="os"))
        result = service.submit_answer(
            created.session_id,
            StudySessionAnswerRequest(answer="不知道"),
        )
        assert result.state == "awaiting_answer"
        assert result.attempt_count == 1
        assert result.last_evaluation is not None
        assert result.last_evaluation.correct is False
        assert result.last_evaluation.reference_answer == ""
        assert result.remediation
        assert scheduler.logged == []

    def test_second_wrong_answer_returns_full_explanation_and_completes(self):
        service, _qa, _quiz, scheduler = make_service()
        created = service.create(StudySessionCreateRequest(topic="死锁", course="os"))
        service.submit_answer(
            created.session_id,
            StudySessionAnswerRequest(answer="不知道"),
        )
        result = service.submit_answer(
            created.session_id,
            StudySessionAnswerRequest(answer="还是不知道"),
        )
        assert result.state == "completed"
        assert result.attempt_count == 2
        assert result.score == 0.0
        assert "完整参考" in result.remediation
        assert result.last_evaluation is not None
        assert result.last_evaluation.reference_answer
        assert scheduler.logged

    def test_second_question_starts_after_first_correct_answer(self):
        questions = [
            QuizQuestion(
                question="死锁四个条件？",
                type="example",
                answer="互斥、占有并等待、不可剥夺、循环等待",
                source_file="knowledge/os/deadlock.md",
                tags=["死锁"],
            ),
            QuizQuestion(
                question="如何预防死锁？",
                type="example",
                answer="破坏四个必要条件之一",
                source_file="knowledge/os/deadlock.md",
                tags=["死锁"],
            ),
        ]
        service, _qa, _quiz, scheduler = make_service(questions=questions)
        created = service.create(
            StudySessionCreateRequest(topic="死锁", course="os", question_count=2)
        )
        assert len(created.questions) == 2
        first = service.submit_answer(
            created.session_id,
            StudySessionAnswerRequest(answer="互斥、占有并等待、不可剥夺、循环等待"),
        )
        assert first.state == "awaiting_answer"
        assert first.current_question_id == "q2"
        assert scheduler.logged == []
        second = service.submit_answer(
            created.session_id,
            StudySessionAnswerRequest(answer="破坏四个必要条件之一"),
        )
        assert second.state == "completed"
        assert second.score == 1.0
        assert scheduler.logged


@pytest.mark.m5b
class TestIllegalTransitions:
    def test_unknown_session_raises(self):
        service, *_ = make_service()
        with pytest.raises(SessionNotFoundError):
            service.get("missing")

    def test_answer_after_complete_raises(self):
        service, *_ = make_service()
        created = service.create(StudySessionCreateRequest(topic="死锁", course="os"))
        service.submit_answer(
            created.session_id,
            StudySessionAnswerRequest(answer="互斥、占有并等待、不可剥夺、循环等待"),
        )
        with pytest.raises(IllegalSessionStateError, match="completed"):
            service.submit_answer(
                created.session_id,
                StudySessionAnswerRequest(answer="再次提交"),
            )
