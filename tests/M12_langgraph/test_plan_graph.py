"""Tests for the plan-lifecycle LangGraph."""

from __future__ import annotations

import pytest

from app.graphs import LANGGRAPH_AVAILABLE

pytestmark = pytest.mark.skipif(
    not LANGGRAPH_AVAILABLE,
    reason="langgraph is not installed",
)


class TestPlanGraph:
    def test_graph_compiles(self, graph_container):
        graph = graph_container.plan_graph
        assert graph is not None

    def test_no_deviation_skips_replan(self, graph_container, mock_plan_lifecycle):
        mock_plan_lifecycle.get.return_value = {
            "plan_id": "p1",
            "progress_events": [
                {"task_id": "t1", "event": "skipped"},
            ],
            "deviation_ledger": [],
        }

        result = graph_container.plan_graph.invoke({"plan_id": "p1"})

        assert result["deviation_count"] == 1
        assert result["deviation_triggered"] is False
        assert result.get("generated_plan") is None
        mock_plan_lifecycle.replan.assert_not_called()

    def test_deviation_triggers_replan(self, graph_container, mock_plan_lifecycle):
        mock_plan_lifecycle.get.return_value = {
            "plan_id": "p1",
            "progress_events": [
                {"task_id": "t1", "event": "skipped"},
                {"task_id": "t2", "event": "overdue"},
                {"task_id": "t3", "event": "skipped"},
            ],
            "deviation_ledger": [],
        }

        result = graph_container.plan_graph.invoke({
            "plan_id": "p1",
            "goal": "学习操作系统",
            "course": "os",
        })

        assert result["deviation_count"] == 3
        assert result["deviation_triggered"] is True
        assert result["generated_plan"] is not None
        mock_plan_lifecycle.replan.assert_called_once()

    def test_empty_plan_id(self, graph_container):
        result = graph_container.plan_graph.invoke({"plan_id": ""})

        assert result["deviation_count"] == 0
        assert result["deviation_triggered"] is False
