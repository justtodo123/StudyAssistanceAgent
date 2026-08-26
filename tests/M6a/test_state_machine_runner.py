"""Focused tests for the thin StudySession state-machine runner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from app.models import (
    QuizQuestion,
    StudySessionAnswerRequest,
    StudySessionCreateRequest,
    StudySessionResponse,
)
from app.protocols import (
    ProtocolValidationError,
    Runner,
    RunnerContext,
    RunnerEvent,
    RunnerEventType,
    RunnerStatus,
)
from app.runners import StateMachineRunner
from app.study_session import SessionNotFoundError, StudySessionService
from tests.M5b.helpers import (
    FakeQaService,
    FakeQuizService,
    FakeReviewScheduler,
    make_service,
)


pytestmark = pytest.mark.m6a


@dataclass
class _ServiceSpy:
    response: StudySessionResponse
    create_calls: list[StudySessionCreateRequest]
    get_calls: list[str]
    submit_calls: list[tuple[str, StudySessionAnswerRequest]]

    def create(self, request: StudySessionCreateRequest) -> StudySessionResponse:
        self.create_calls.append(request)
        return self.response

    def get(self, run_id: str) -> StudySessionResponse:
        self.get_calls.append(run_id)
        if run_id != self.response.session_id:
            raise SessionNotFoundError(run_id)
        return self.response

    def submit_answer(self, run_id: str, request: StudySessionAnswerRequest) -> StudySessionResponse:
        self.submit_calls.append((run_id, request))
        return self.response


def _context(**input_data: Any) -> RunnerContext:
    return RunnerContext(
        learner_id="learner-1",
        correlation_id="request-1",
        permissions=frozenset({"run"}),
        input=input_data,
    )


def _response(*, state: str = "awaiting_answer") -> StudySessionResponse:
    return StudySessionResponse(
        session_id="session-1",
        course="os",
        topic="deadlock",
        state=state,
        explanation="deadlock explanation",
        sources=[],
        questions=[],
        current_question_id="q1" if state == "awaiting_answer" else None,
        attempt_count=0,
        tool_trace=[],
        created_at="2026-08-26T00:00:00",
        updated_at="2026-08-26T00:00:00",
    )


def test_runner_context_input_is_backward_compatible_and_json_safe() -> None:
    legacy = RunnerContext(learner_id="learner-1")

    assert legacy.input == {}
    with pytest.raises(ProtocolValidationError, match="object"):
        RunnerContext(learner_id="learner-1", input=[])  # type: ignore[arg-type]
    with pytest.raises(ProtocolValidationError, match="JSON serializable"):
        RunnerContext(learner_id="learner-1", input={"invalid": object()})


def test_runner_satisfies_protocol_and_delegates_start_get_resume() -> None:
    response = _response()
    service = _ServiceSpy(response, [], [], [])
    runner = StateMachineRunner(service)
    context = _context(topic="deadlock", course="os", question_count=1, use_llm=False)

    assert isinstance(runner, Runner)
    started = runner.start(context)
    fetched = runner.get(context, response.session_id)
    resumed = runner.resume(context, response.session_id)

    assert started.ok and fetched.ok and resumed.ok
    assert started.snapshot.run_id == response.session_id
    assert started.snapshot.status is RunnerStatus.WAITING
    assert started.snapshot.waiting_for == "q1"
    assert started.snapshot.state == {
        "session_id": "session-1",
        "course": "os",
        "topic": "deadlock",
        "current_question_id": "q1",
    }
    assert fetched.snapshot == resumed.snapshot
    assert len(service.create_calls) == 1
    assert service.get_calls == [response.session_id, response.session_id]


def test_start_uses_durable_domain_ids_not_correlation_ids() -> None:
    service, _qa, _quiz, _scheduler = make_service()
    runner = StateMachineRunner(service)
    context = _context(topic="deadlock", course="os")

    first = runner.start(context)
    second = runner.start(context)

    assert first.ok and second.ok
    assert first.snapshot.run_id != second.snapshot.run_id
    assert first.snapshot.run_id != context.correlation_id


def test_continue_payload_is_strict_and_delegated_once() -> None:
    response = _response()
    service = _ServiceSpy(response, [], [], [])
    runner = StateMachineRunner(service)
    context = _context()

    invalid = runner.step(
        context,
        response.session_id,
        RunnerEvent(RunnerEventType.CONTINUE, {"answer": "four conditions"}),
    )
    valid = runner.step(
        context,
        response.session_id,
        RunnerEvent(
            RunnerEventType.CONTINUE,
            {"question_id": "q1", "answer": "four conditions"},
        ),
    )

    assert not invalid.ok
    assert invalid.error is not None
    assert invalid.error.code == "RUN_EVENT_INVALID"
    assert valid.ok
    assert len(service.submit_calls) == 1
    run_id, request = service.submit_calls[0]
    assert run_id == response.session_id
    assert request.question_id == "q1"
    assert request.answer == "four conditions"


def test_complete_only_observes_an_already_completed_session() -> None:
    active = _ServiceSpy(_response(), [], [], [])
    completed = _ServiceSpy(_response(state="completed"), [], [], [])

    early = StateMachineRunner(active).step(
        _context(), "session-1", RunnerEvent(RunnerEventType.COMPLETE)
    )
    observed = StateMachineRunner(completed).step(
        _context(), "session-1", RunnerEvent(RunnerEventType.COMPLETE)
    )

    assert not early.ok
    assert early.error is not None
    assert early.error.code == "RUN_EVENT_INVALID"
    assert observed.ok
    assert observed.snapshot.status is RunnerStatus.COMPLETED
    assert active.submit_calls == []
    assert completed.submit_calls == []


@pytest.mark.parametrize("event_type", [RunnerEventType.CANCEL, RunnerEventType.FAIL])
def test_control_events_do_not_create_fake_durable_terminal_states(event_type: RunnerEventType) -> None:
    response = _response()
    service = _ServiceSpy(response, [], [], [])
    result = StateMachineRunner(service).step(_context(), response.session_id, RunnerEvent(event_type))

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "RUN_CONTROL_UNSUPPORTED"
    assert result.snapshot.status is RunnerStatus.WAITING
    assert service.submit_calls == []


def test_cancelled_context_returns_current_durable_snapshot() -> None:
    response = _response()
    service = _ServiceSpy(response, [], [], [])
    context = RunnerContext(learner_id="learner-1", cancelled=True)

    result = StateMachineRunner(service).get(context, response.session_id)

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "RUN_CONTROL_UNSUPPORTED"
    assert result.snapshot.status is RunnerStatus.WAITING
    assert service.get_calls == [response.session_id]


@pytest.mark.parametrize(
    "input_data",
    [
        {},
        {"topic": "deadlock", "course": "network"},
        {"topic": "deadlock", "course": "os", "question_count": 3},
        {"topic": "deadlock", "course": "os", "unexpected": True},
    ],
)
def test_start_rejects_invalid_domain_input(input_data: dict[str, Any]) -> None:
    response = _response()
    service = _ServiceSpy(response, [], [], [])

    result = StateMachineRunner(service).start(_context(**input_data))

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "RUN_INPUT_INVALID"
    assert service.create_calls == []


def test_unknown_run_is_safe_and_does_not_expose_lookup_details() -> None:
    response = _response()
    service = _ServiceSpy(response, [], [], [])

    result = StateMachineRunner(service).get(_context(), "missing-session")

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "RUN_NOT_FOUND"
    assert "missing-session" not in result.error.message


def test_real_domain_lifecycle_keeps_revision_stable_for_duplicate_answer() -> None:
    service, _qa, _quiz, scheduler = make_service()
    runner = StateMachineRunner(service)
    started = runner.start(_context(topic="deadlock", course="os"))
    question_id = started.snapshot.waiting_for
    assert question_id is not None
    event = RunnerEvent(
        RunnerEventType.CONTINUE,
        {
            "question_id": question_id,
            "answer": "互斥、占有并等待、不可剥夺、循环等待",
        },
    )

    completed = runner.step(_context(), started.snapshot.run_id, event)
    duplicate = runner.step(_context(), started.snapshot.run_id, event)
    fetched = runner.get(_context(), started.snapshot.run_id)

    assert completed.ok
    assert completed.snapshot.status is RunnerStatus.COMPLETED
    assert not duplicate.ok
    assert duplicate.error is not None
    assert duplicate.error.code == "RUN_EVENT_INVALID"
    assert fetched.snapshot == completed.snapshot
    assert len(scheduler.logged) == 1


def test_sqlite_backed_runner_recovers_snapshot_across_service_instances(
    tmp_path: Path,
) -> None:
    from app.learning_store import SqliteLearningStore

    database = tmp_path / "learning_state.sqlite3"
    first_scheduler = FakeReviewScheduler()
    first_service = StudySessionService(
        qa_service=FakeQaService(),
        quiz_service=FakeQuizService(),
        review_scheduler=first_scheduler,
        session_repository=SqliteLearningStore(database),
    )
    first_runner = StateMachineRunner(first_service)
    started = first_runner.start(_context(topic="deadlock", course="os"))

    second_service = StudySessionService(
        qa_service=FakeQaService(),
        quiz_service=FakeQuizService(),
        review_scheduler=FakeReviewScheduler(),
        session_repository=SqliteLearningStore(database),
    )
    recovered = StateMachineRunner(second_service).resume(
        _context(),
        started.snapshot.run_id,
    )

    assert recovered.ok
    assert recovered.snapshot == started.snapshot
    assert recovered.output.session_id == started.snapshot.run_id


def test_no_question_session_completes_during_start() -> None:
    service, _qa, quiz, scheduler = make_service()
    quiz.questions = []
    runner = StateMachineRunner(service)

    result = runner.start(_context(topic="deadlock", course="os"))

    assert result.ok
    assert result.snapshot.status is RunnerStatus.COMPLETED
    assert result.snapshot.waiting_for is None
    assert len(scheduler.logged) == 1


def test_two_question_domain_progression_is_owned_by_service() -> None:
    questions = [
        QuizQuestion(
            question="死锁产生的四个必要条件是什么？",
            type="example",
            answer="互斥、占有并等待、不可剥夺、循环等待",
            source_file="knowledge/os/deadlock.md",
        ),
        QuizQuestion(
            question="死锁预防的基本思路是什么？",
            type="example",
            answer="破坏死锁的一个必要条件",
            source_file="knowledge/os/deadlock.md",
        ),
    ]
    service, _qa, _quiz, scheduler = make_service(questions=questions)
    runner = StateMachineRunner(service)
    started = runner.start(_context(topic="deadlock", course="os", question_count=2))

    first = runner.step(
        _context(),
        started.snapshot.run_id,
        RunnerEvent(
            RunnerEventType.CONTINUE,
            {"question_id": "q1", "answer": "互斥、占有并等待、不可剥夺、循环等待"},
        ),
    )
    second = runner.step(
        _context(),
        started.snapshot.run_id,
        RunnerEvent(
            RunnerEventType.CONTINUE,
            {"question_id": "q2", "answer": "破坏死锁的一个必要条件"},
        ),
    )

    assert first.ok and second.ok
    assert first.snapshot.status is RunnerStatus.WAITING
    assert first.snapshot.waiting_for == "q2"
    assert second.snapshot.status is RunnerStatus.COMPLETED
    assert len(scheduler.logged) == 1
