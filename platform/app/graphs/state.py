"""Shared state schemas for LangGraph graphs.

Each graph owns a :class:`typing.TypedDict` that LangGraph threads through
every node.  Fields use plain types so the state is serialisable for
checkpointing.  Nodes read and write these fields; conditional edges read
them to decide routing.
"""

from __future__ import annotations

from typing import Any, TypedDict


class StudyState(TypedDict, total=False):
    """State threaded through the study-session graph.

    The graph replaces the imperative FSM inside
    :mod:`app.study_session` — nodes call the same deterministic services
    (``QaService``, ``QuizService``, ``evaluate_answer``) but the routing
    is expressed as LangGraph edges.
    """

    session_id: str
    course: str
    topic: str
    question_count: int
    use_llm: bool
    principal_id: str | None

    explanation: str
    sources: list[dict[str, Any]]
    questions: list[dict[str, Any]]
    current_index: int
    state: str

    current_answer: str
    last_evaluation: dict[str, Any] | None
    remediation: str
    score: float | None
    attempt_count: int
    tool_trace: list[dict[str, Any]]


class PlanState(TypedDict, total=False):
    """State threaded through the plan-lifecycle graph."""

    plan_id: str
    goal: str | None
    course: str | None
    target_date: str | None
    hours_per_day: float | None
    constraints: dict[str, Any] | None

    deviation_count: int
    deviation_triggered: bool
    grounding_chunks: list[dict[str, Any]]
    generated_plan: dict[str, Any] | None


class AssistanceState(TypedDict, total=False):
    """Top-level state for the multi-agent router graph."""

    intent: str
    question: str
    course: str | None
    principal_id: str | None

    retrieval_results: list[dict[str, Any]]
    retrieval_mode: str
    result: dict[str, Any] | None
