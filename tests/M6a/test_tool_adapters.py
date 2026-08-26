"""Focused tests for deterministic M6a tool adapters."""

from __future__ import annotations

import random
from collections.abc import Mapping
from typing import Any

import pytest

from app.models import QuizQuestion, QuizResponse, RetrievalChunk, ReviewDueResponse
from app.protocols import SideEffect, Tool, ToolCapability, ToolContext, ToolSpec
from app.retrieval import RetrievalScope
from app.tools import QuizTool, RetrieveTool, ReviewDueTool


pytestmark = pytest.mark.m6a


class _RecallSpy:
    def __init__(self, chunks: list[RetrievalChunk] | None = None, *, failure: Exception | None = None) -> None:
        self.chunks = chunks or []
        self.failure = failure
        self.calls: list[tuple[Any, ...]] = []

    def recall(self, *args: Any) -> tuple[list[RetrievalChunk], str]:
        self.calls.append(args)
        if self.failure is not None:
            raise self.failure
        return self.chunks, "keyword"


class _QuizSpy:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls: list[tuple[Any, Any]] = []

    def generate(self, request: Any, *, rng: random.Random | None = None) -> QuizResponse:
        self.calls.append((request, rng))
        if self.failure is not None:
            raise self.failure
        assert rng is not None
        marker = rng.randrange(1_000_000)
        return QuizResponse(
            quiz_name=f"{request.course}-quiz",
            course=request.course,
            generated_at="changes-between-calls",
            count=1,
            questions=[
                QuizQuestion(
                    question=f"question-{marker}",
                    type="concept",
                    source_file="knowledge/os/process.md",
                )
            ],
            summary={"marker": marker},
        )


class _ReviewSpy:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.get_calls: list[str | None] = []
        self.log_calls = 0

    def get_due(self, course: str | None = None) -> ReviewDueResponse:
        self.get_calls.append(course)
        if self.failure is not None:
            raise self.failure
        return ReviewDueResponse(
            course=course,
            checked_at="2026-08-26T12:00:00",
            total_due=0,
            entries=[],
            summary={"due": 0},
        )

    def log_review(self, request: Any) -> None:
        self.log_calls += 1
        raise AssertionError("read-only adapter must not write review history")


def _context(
    *,
    scope: str = "DEFAULT_ONLY",
    permissions: frozenset[str] = frozenset({"read"}),
    correlation_id: str = "correlation-1",
    cancelled: bool = False,
) -> ToolContext:
    return ToolContext(
        learner_id="learner-1",
        source_scope=scope,
        correlation_id=correlation_id,
        permissions=permissions,
        cancelled=cancelled,
    )


def test_adapters_satisfy_runtime_tool_protocol_and_declare_exact_schemas() -> None:
    tools = (RetrieveTool(_RecallSpy()), QuizTool(_QuizSpy()), ReviewDueTool(_ReviewSpy()))

    assert all(isinstance(tool, Tool) for tool in tools)
    assert all(tool.spec.capability is ToolCapability.READ for tool in tools)
    assert all(tool.spec.side_effect is SideEffect.NONE for tool in tools)
    assert all(tool.spec.idempotent for tool in tools)
    assert RetrieveTool.spec.input_schema == {
        "type": "object",
        "properties": {
            "question": {"type": "string", "minLength": 1},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
            "threshold": {"type": "number", "minimum": 0, "maximum": 1},
            "course": {"type": "string", "minLength": 1},
        },
        "required": ["question"],
        "additionalProperties": False,
    }
    assert QuizTool.spec.input_schema["required"] == ["course"]
    assert ReviewDueTool.spec.input_schema["required"] == []
    assert all(tool.spec.input_schema["additionalProperties"] is False for tool in tools)


@pytest.mark.parametrize(
    ("context", "expected_code"),
    [
        (_context(cancelled=True), "TOOL_CANCELLED"),
        (_context(correlation_id=""), "TOOL_CONTEXT_INVALID"),
        (_context(scope=""), "TOOL_CONTEXT_INVALID"),
        (_context(scope="UNKNOWN"), "TOOL_SCOPE_INVALID"),
        (_context(permissions=frozenset()), "TOOL_NOT_AUTHORIZED"),
    ],
)
def test_authorization_stops_before_service_execution(context: ToolContext, expected_code: str) -> None:
    recall = _RecallSpy()
    result = RetrieveTool(recall).execute(context, {"question": "paging"})

    assert not result.ok
    assert result.error is not None
    assert result.error.code == expected_code
    assert result.correlation_id == context.correlation_id
    assert recall.calls == []


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"question": ""},
        {"question": "paging", "top_k": 0},
        {"question": "paging", "top_k": 21},
        {"question": "paging", "top_k": True},
        {"question": "paging", "threshold": -0.01},
        {"question": "paging", "threshold": 1.01},
        {"question": "paging", "unknown": "field"},
    ],
)
def test_retrieve_rejects_invalid_arguments_without_calling_service(arguments: Mapping[str, Any]) -> None:
    recall = _RecallSpy()
    result = RetrieveTool(recall).execute(_context(), arguments)

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "TOOL_ARGUMENTS_INVALID"
    assert recall.calls == []


def test_retrieve_returns_logical_sources_and_correlation_id() -> None:
    recall = _RecallSpy(
        [
            RetrievalChunk(id="1", file="knowledge/os/process.md", title="Process", content="default"),
            RetrievalChunk(id="2", file="extra://notes-1/week-01.md", title="Week 1", content="extra"),
        ]
    )
    result = RetrieveTool(recall).execute(
        _context(scope="DEFAULT_PLUS_EXTRAS", correlation_id="request-42"),
        {"question": "process", "top_k": 2, "threshold": 0.4, "course": "os"},
    )

    assert result.ok
    assert result.correlation_id == "request-42"
    assert recall.calls == [
        ("process", 2, 0.4, "os", RetrievalScope.DEFAULT_PLUS_EXTRAS)
    ]
    assert [(source.source_id, source.logical_uri) for source in result.sources] == [
        ("knowledge-pack", "os/process.md"),
        ("notes-1", "week-01.md"),
    ]


@pytest.mark.parametrize("file", [r"C:\\private\\notes.md", "extra://broken"])
def test_retrieve_rejects_unsafe_provenance_without_leaking_it(file: str) -> None:
    recall = _RecallSpy([RetrievalChunk(id="1", file=file, content="secret")])
    result = RetrieveTool(recall).execute(_context(), {"question": "secret"})

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "TOOL_RESULT_INVALID"
    assert file not in result.error.message
    assert "secret" not in result.error.message
    assert result.data is None


def test_service_exception_is_mapped_to_stable_safe_error() -> None:
    private_detail = r"failed at C:\\Users\\private\\knowledge"
    result = RetrieveTool(_RecallSpy(failure=RuntimeError(private_detail))).execute(
        _context(), {"question": "paging"}
    )

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "TOOL_EXECUTION_FAILED"
    assert result.error.retryable
    assert private_detail not in result.error.message


def test_quiz_is_repeatable_excludes_timestamp_and_preserves_global_rng() -> None:
    quiz = _QuizSpy()
    tool = QuizTool(quiz)
    arguments = {"course": "os", "count": 1, "topics": ["process"]}
    random.seed(8128)
    expected_next = random.random()
    random.seed(8128)

    first = tool.execute(_context(), arguments)
    second = tool.execute(_context(), arguments)
    actual_next = random.random()

    assert first.ok and second.ok
    assert first.data == second.data
    assert "generated_at" not in first.data
    assert actual_next == expected_next
    assert len(quiz.calls) == 2
    assert quiz.calls[0][1] is not quiz.calls[1][1]


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"course": ""},
        {"course": "os", "count": 0},
        {"course": "os", "count": 21},
        {"course": "os", "difficulty": 2},
        {"course": "os", "topics": "process"},
        {"course": "os", "extra": True},
    ],
)
def test_quiz_rejects_invalid_arguments(arguments: Mapping[str, Any]) -> None:
    quiz = _QuizSpy()
    result = QuizTool(quiz).execute(_context(), arguments)

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "TOOL_ARGUMENTS_INVALID"
    assert quiz.calls == []


def test_review_due_only_reads_and_preserves_correlation_id() -> None:
    scheduler = _ReviewSpy()
    result = ReviewDueTool(scheduler).execute(
        _context(correlation_id="review-request"), {"course": "os"}
    )

    assert result.ok
    assert result.correlation_id == "review-request"
    assert scheduler.get_calls == ["os"]
    assert scheduler.log_calls == 0


@pytest.mark.parametrize("arguments", [{"course": ""}, {"course": 1}, {"unexpected": True}])
def test_review_due_rejects_invalid_arguments(arguments: Mapping[str, Any]) -> None:
    scheduler = _ReviewSpy()
    result = ReviewDueTool(scheduler).execute(_context(), arguments)

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "TOOL_ARGUMENTS_INVALID"
    assert scheduler.get_calls == []


def test_future_review_log_tool_requires_write_domain_capability() -> None:
    future_spec = ToolSpec(
        name="review_log",
        description="Record a completed review.",
        input_schema={"type": "object"},
        capability=ToolCapability.WRITE,
        side_effect=SideEffect.DOMAIN_WRITE,
        idempotent=True,
    )

    assert future_spec.capability is ToolCapability.WRITE
    assert future_spec.side_effect is SideEffect.DOMAIN_WRITE
    assert not _context().allows(future_spec)
