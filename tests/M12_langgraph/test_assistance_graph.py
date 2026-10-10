"""Tests for the top-level assistance router graph."""

from __future__ import annotations

import pytest

from app.graphs import LANGGRAPH_AVAILABLE
from app.models import RetrievalChunk

pytestmark = pytest.mark.skipif(
    not LANGGRAPH_AVAILABLE,
    reason="langgraph is not installed",
)


class TestAssistanceGraph:
    def test_graph_compiles(self, graph_container):
        graph = graph_container.assistance_graph
        assert graph is not None

    def test_study_intent(self, graph_container, mock_recall):
        chunk = RetrievalChunk(
            id="r1",
            file="knowledge/os/sched.md",
            title="调度",
            course="os",
            tags=[],
            difficulty="medium",
            updated="2026-01-01",
            content="content",
            score=0.8,
        )
        mock_recall.recall.return_value = ([chunk], "hybrid")

        result = graph_container.assistance_graph.invoke({
            "intent": "study",
            "question": "进程调度",
            "course": "os",
        })

        assert result["intent"] == "study"
        assert result["retrieval_mode"] == "hybrid"
        assert len(result["retrieval_results"]) == 1

    def test_plan_intent(self, graph_container, mock_recall):
        mock_recall.recall.return_value = ([], "keyword-only")

        result = graph_container.assistance_graph.invoke({
            "intent": "plan",
            "question": "制定学习计划",
            "course": "os",
        })

        assert result["intent"] == "plan"
        mock_recall.recall.assert_called_once()

    def test_general_intent(self, graph_container, mock_recall):
        mock_recall.recall.return_value = ([], "keyword-only")

        result = graph_container.assistance_graph.invoke({
            "intent": "general",
            "question": "什么是操作系统",
        })

        assert result["intent"] == "general"

    def test_invalid_intent_defaults_to_general(self, graph_container, mock_recall):
        mock_recall.recall.return_value = ([], "keyword-only")

        result = graph_container.assistance_graph.invoke({
            "intent": "invalid",
            "question": "test",
        })

        assert result["intent"] == "general"

    def test_empty_question(self, graph_container, mock_recall):
        result = graph_container.assistance_graph.invoke({
            "intent": "study",
            "question": "",
        })

        assert result["retrieval_results"] == []
        assert result["retrieval_mode"] == "no_query"
