"""Shared fixtures for M12 LangGraph tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.graphs import LANGGRAPH_AVAILABLE
from app.graphs.config import LangGraphLimits
from app.graphs.dependencies import GraphContainer


pytestmark = pytest.mark.skipif(
    not LANGGRAPH_AVAILABLE,
    reason="langgraph is not installed",
)


@pytest.fixture
def limits() -> LangGraphLimits:
    return LangGraphLimits()


@pytest.fixture
def mock_recall():
    recall = MagicMock()
    recall.recall.return_value = ([], "keyword-only")
    return recall


@pytest.fixture
def mock_qa_service():
    service = MagicMock()
    from app.models import QaResponse, RetrievalChunk

    service.answer.return_value = QaResponse(
        question="test",
        answer="进程调度算法包括 FCFS、SJF 和 RR。",
        mode="keyword-only",
        sources=[
            RetrievalChunk(
                id="test-1",
                file="knowledge/os/process-scheduling.md",
                title="进程调度",
                course="os",
                tags=["scheduling"],
                difficulty="medium",
                updated="2026-01-01",
                content="进程调度算法",
                score=0.8,
            )
        ],
    )
    return service


@pytest.fixture
def mock_quiz_service():
    service = MagicMock()
    from app.models import QuizQuestion, QuizResponse

    service.generate.return_value = QuizResponse(
        quiz_name="test",
        course="os",
        generated_at="2026-01-01",
        count=2,
        questions=[
            QuizQuestion(
                question="请列举三种进程调度算法",
                type="example",
                answer="FCFS、SJF、RR",
                source_file="knowledge/os/process-scheduling.md",
                source_title="进程调度",
                tags=["scheduling"],
                difficulty="medium",
            ),
            QuizQuestion(
                question="SJF 的全称是什么",
                type="concept",
                answer="Shortest Job First",
                source_file="knowledge/os/process-scheduling.md",
                source_title="进程调度",
                tags=["scheduling"],
                difficulty="easy",
            ),
        ],
        summary={},
    )
    return service


@pytest.fixture
def mock_review_scheduler():
    scheduler = MagicMock()
    scheduler.log_review.return_value = {
        "file": "knowledge/os/process-scheduling.md",
        "course": "os",
        "review_count": 1,
    }
    return scheduler


@pytest.fixture
def mock_goal_planner():
    return MagicMock()


@pytest.fixture
def mock_plan_lifecycle():
    lifecycle = MagicMock()
    lifecycle.get.return_value = {
        "plan_id": "test-plan",
        "state": "adopted",
        "progress_events": [],
        "deviation_ledger": [],
        "tasks": [],
    }
    lifecycle.replan.return_value = {
        "plan_id": "test-plan",
        "state": "replanned",
        "revision_id": 2,
    }
    return lifecycle


@pytest.fixture
def graph_container(
    mock_recall,
    mock_qa_service,
    mock_quiz_service,
    mock_review_scheduler,
    mock_goal_planner,
    mock_plan_lifecycle,
    limits,
):
    return GraphContainer(
        recall=mock_recall,
        qa_service=mock_qa_service,
        quiz_service=mock_quiz_service,
        review_scheduler=mock_review_scheduler,
        goal_planner=mock_goal_planner,
        plan_lifecycle=mock_plan_lifecycle,
        limits=limits,
    )
