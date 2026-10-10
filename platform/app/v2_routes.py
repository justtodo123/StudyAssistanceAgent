"""v2 API routes — LangGraph-powered endpoints parallel to v1.

These endpoints are only registered when ``SA_LANGRAPH_ENABLED=true`` and
``langgraph`` is importable.  They use the same request/response models as
v1 where possible, so clients can migrate incrementally.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .errors import ErrorCode, http_error
from .graphs import LANGGRAPH_AVAILABLE
from .graphs.config import LangGraphLimits
from .graphs.dependencies import GraphContainer
from .models import (
    StudySessionAnswerRequest,
    StudySessionCreateRequest,
    StudySessionResponse,
    StudyQuestionView,
    StudySessionSource,
)


def build_v2_router(container: GraphContainer) -> APIRouter:
    """Build the v2 API router with LangGraph-backed endpoints."""
    router = APIRouter(prefix="/api/v2")
    graph_states: dict[str, dict[str, Any]] = {}

    @router.post("/study-sessions")
    def create_study_session(req: StudySessionCreateRequest) -> dict[str, Any]:
        if not LANGGRAPH_AVAILABLE:
            raise http_error(
                ErrorCode.INTERNAL_ERROR,
                "langgraph is not installed",
            )
        graph = container.study_graph
        session_id = uuid.uuid4().hex
        initial_state = {
            "session_id": session_id,
            "course": req.course,
            "topic": req.topic.strip(),
            "question_count": req.question_count,
            "use_llm": req.use_llm,
        }
        result = graph.invoke(initial_state)
        graph_states[session_id] = result
        return _study_state_to_response(result)

    @router.post("/study-sessions/{session_id}/answers")
    def submit_answer(
        session_id: str,
        req: StudySessionAnswerRequest,
    ) -> dict[str, Any]:
        if not LANGGRAPH_AVAILABLE:
            raise http_error(
                ErrorCode.INTERNAL_ERROR,
                "langgraph is not installed",
            )

        existing = graph_states.get(session_id)
        if existing is None:
            raise http_error(
                ErrorCode.SESSION_NOT_FOUND,
                f"session {session_id} not found",
            )

        graph = container.submit_graph
        initial_state = {
            **existing,
            "current_answer": req.answer,
        }
        result = graph.invoke(initial_state)
        graph_states[session_id] = result
        return _study_state_to_response(result)

    @router.post("/plans/{plan_id}/replan-grounded")
    def replan_grounded(plan_id: str) -> dict[str, Any]:
        if not LANGGRAPH_AVAILABLE:
            raise http_error(
                ErrorCode.INTERNAL_ERROR,
                "langgraph is not installed",
            )
        graph = container.plan_graph
        initial_state = {"plan_id": plan_id}
        result = graph.invoke(initial_state)
        return {
            "plan_id": plan_id,
            "deviation_count": result.get("deviation_count", 0),
            "deviation_triggered": result.get("deviation_triggered", False),
            "generated_plan": result.get("generated_plan"),
            "grounding_chunks": result.get("grounding_chunks", []),
        }

    @router.post("/assist")
    def assist(req: dict[str, Any]) -> dict[str, Any]:
        if not LANGGRAPH_AVAILABLE:
            raise http_error(
                ErrorCode.INTERNAL_ERROR,
                "langgraph is not installed",
            )
        graph = container.assistance_graph
        initial_state = {
            "intent": req.get("intent", "general"),
            "question": req.get("question", ""),
            "course": req.get("course"),
        }
        result = graph.invoke(initial_state)
        return {
            "intent": result.get("intent", "general"),
            "retrieval_mode": result.get("retrieval_mode", ""),
            "results": result.get("retrieval_results", []),
        }

    return router


def _study_state_to_response(state: dict[str, Any]) -> dict[str, Any]:
    """Convert graph state to a StudySessionResponse-compatible dict."""
    questions_raw = state.get("questions") or []
    sources_raw = state.get("sources") or []
    trace_raw = state.get("tool_trace") or []

    questions = [
        StudyQuestionView(
            id=q.get("id", ""),
            question=q.get("question", ""),
            type=q.get("type", ""),
            source_file=q.get("source_file", ""),
            source_title=q.get("source_title", ""),
            difficulty=q.get("difficulty", ""),
            tags=q.get("tags", []),
        )
        for q in questions_raw
    ]
    sources = [
        StudySessionSource(
            file=s.get("file", ""),
            title=s.get("title", ""),
            course=s.get("course", ""),
        )
        for s in sources_raw
    ]

    current_id = None
    answerable_states = {"awaiting_answer", "remediation"}
    if questions and state.get("state") in answerable_states:
        idx = state.get("current_index", 0)
        if idx < len(questions):
            current_id = questions[idx].id

    return {
        "session_id": state.get("session_id", ""),
        "course": state.get("course", ""),
        "topic": state.get("topic", ""),
        "state": state.get("state", "created"),
        "explanation": state.get("explanation", ""),
        "sources": sources,
        "questions": questions,
        "current_question_id": current_id,
        "attempt_count": _current_attempts(questions_raw, state.get("current_index", 0)),
        "score": state.get("score"),
        "last_evaluation": state.get("last_evaluation"),
        "remediation": state.get("remediation", ""),
        "review": state.get("review"),
        "tool_trace": trace_raw,
        "created_at": "",
        "updated_at": "",
    }


def _current_attempts(questions: list[dict[str, Any]], current_index: int) -> int:
    if not questions:
        return 0
    if current_index < len(questions):
        return questions[current_index].get("attempt_count", 0)
    return questions[-1].get("attempt_count", 0)
