"""Unit tests for LangGraph node functions."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.graphs import LANGGRAPH_AVAILABLE

pytestmark = pytest.mark.skipif(
    not LANGGRAPH_AVAILABLE,
    reason="langgraph is not installed",
)


class TestRetrievalNode:
    def test_retrieve_with_query(self, mock_recall):
        from app.graphs.nodes.retrieval import retrieve_node
        from app.models import RetrievalChunk

        chunk = RetrievalChunk(
            id="c1",
            file="knowledge/os/sched.md",
            title="调度",
            course="os",
            tags=["cpu"],
            difficulty="medium",
            updated="2026-01-01",
            content="test content",
            score=0.9,
        )
        mock_recall.recall.return_value = ([chunk], "hybrid")

        state = {"question": "进程调度", "course": "os"}
        result = retrieve_node(state, recall=mock_recall)

        assert result["retrieval_mode"] == "hybrid"
        assert len(result["retrieval_results"]) == 1
        assert result["retrieval_results"][0]["file"] == "knowledge/os/sched.md"
        mock_recall.recall.assert_called_once()

    def test_retrieve_empty_query(self, mock_recall):
        from app.graphs.nodes.retrieval import retrieve_node

        state = {"question": "", "course": "os"}
        result = retrieve_node(state, recall=mock_recall)

        assert result["retrieval_results"] == []
        assert result["retrieval_mode"] == "no_query"
        mock_recall.recall.assert_not_called()

    def test_retrieve_uses_topic_fallback(self, mock_recall):
        from app.graphs.nodes.retrieval import retrieve_node

        mock_recall.recall.return_value = ([], "keyword-only")
        state = {"topic": "内存管理"}
        result = retrieve_node(state, recall=mock_recall)

        mock_recall.recall.assert_called_once()
        call_args = mock_recall.recall.call_args
        assert call_args[0][0] == "内存管理"


class TestStudyNodes:
    def test_initialize_node(self, mock_qa_service, mock_quiz_service):
        from app.graphs.nodes.study import initialize_node

        state = {
            "course": "os",
            "topic": "进程调度",
            "question_count": 2,
            "use_llm": False,
        }
        result = initialize_node(
            state,
            qa_service=mock_qa_service,
            quiz_service=mock_quiz_service,
        )

        assert result["state"] == "awaiting_answer"
        assert result["explanation"]
        assert len(result["questions"]) == 2
        assert result["questions"][0]["id"] == "q1"
        assert result["current_index"] == 0
        mock_qa_service.answer.assert_called_once()
        mock_quiz_service.generate.assert_called()

    def test_initialize_node_no_questions(self, mock_qa_service, mock_quiz_service):
        from app.graphs.nodes.study import initialize_node
        from app.models import QuizResponse

        mock_quiz_service.generate.return_value = QuizResponse(
            quiz_name="empty",
            course="os",
            generated_at="2026-01-01",
            count=0,
            questions=[],
            summary={},
        )

        state = {"course": "os", "topic": "冷门主题", "question_count": 1}
        result = initialize_node(
            state,
            qa_service=mock_qa_service,
            quiz_service=mock_quiz_service,
        )

        assert result["state"] == "completed"
        assert result["questions"] == []

    def test_evaluate_node_correct(self):
        from app.graphs.nodes.study import evaluate_node

        state = {
            "questions": [
                {
                    "id": "q1",
                    "question": "请列举三种进程调度算法",
                    "type": "example",
                    "answer": "FCFS、SJF、RR",
                    "source_file": "",
                    "source_title": "",
                    "tags": ["scheduling"],
                    "difficulty": "medium",
                    "attempt_count": 0,
                    "correct": None,
                }
            ],
            "current_index": 0,
            "current_answer": "FCFS SJF RR",
            "explanation": "进程调度算法包括FCFS、SJF和RR",
        }
        result = evaluate_node(state)

        assert result["last_evaluation"]["correct"] is True
        assert result["questions"][0]["attempt_count"] == 1

    def test_evaluate_node_incorrect_first_attempt(self):
        from app.graphs.nodes.study import evaluate_node

        state = {
            "questions": [
                {
                    "id": "q1",
                    "question": "请列举三种进程调度算法",
                    "type": "example",
                    "answer": "FCFS、SJF、RR",
                    "source_file": "",
                    "source_title": "",
                    "tags": ["scheduling"],
                    "difficulty": "medium",
                    "attempt_count": 0,
                    "correct": None,
                }
            ],
            "current_index": 0,
            "current_answer": "完全无关的回答",
            "explanation": "进程调度算法包括FCFS、SJF和RR",
        }
        result = evaluate_node(state)

        assert result["last_evaluation"]["correct"] is False
        assert result["remediation"]
        assert result["questions"][0]["attempt_count"] == 1

    def test_advance_node_next_question(self, mock_review_scheduler):
        from app.graphs.nodes.study import advance_node

        state = {
            "questions": [
                {"id": "q1", "correct": True, "attempt_count": 1},
                {"id": "q2", "correct": None, "attempt_count": 0},
            ],
            "current_index": 0,
            "last_evaluation": {"correct": True},
        }
        result = advance_node(
            state,
            review_scheduler=mock_review_scheduler,
            course="os",
            session_id="test",
        )

        assert result["current_index"] == 1
        assert result["state"] == "awaiting_answer"

    def test_advance_node_complete(self, mock_review_scheduler):
        from app.graphs.nodes.study import advance_node

        state = {
            "questions": [
                {"id": "q1", "correct": True, "attempt_count": 1},
            ],
            "current_index": 0,
            "last_evaluation": {"correct": True},
            "sources": [{"file": "knowledge/os/sched.md"}],
            "topic": "进程调度",
        }
        result = advance_node(
            state,
            review_scheduler=mock_review_scheduler,
            course="os",
            session_id="test",
        )

        assert result["state"] == "completed"
        assert result["score"] is not None


class TestPlanNodes:
    def test_check_deviation_not_triggered(self, mock_plan_lifecycle):
        from app.graphs.nodes.plan import check_deviation_node

        mock_plan_lifecycle.get.return_value = {
            "plan_id": "p1",
            "progress_events": [
                {"task_id": "t1", "event": "skipped"},
            ],
            "deviation_ledger": [],
        }

        state = {"plan_id": "p1"}
        result = check_deviation_node(state, plan_lifecycle=mock_plan_lifecycle)

        assert result["deviation_count"] == 1
        assert result["deviation_triggered"] is False

    def test_check_deviation_triggered(self, mock_plan_lifecycle):
        from app.graphs.nodes.plan import check_deviation_node

        mock_plan_lifecycle.get.return_value = {
            "plan_id": "p1",
            "progress_events": [
                {"task_id": "t1", "event": "skipped"},
                {"task_id": "t2", "event": "overdue"},
                {"task_id": "t3", "event": "skipped"},
            ],
            "deviation_ledger": [],
        }

        state = {"plan_id": "p1"}
        result = check_deviation_node(state, plan_lifecycle=mock_plan_lifecycle)

        assert result["deviation_count"] == 3
        assert result["deviation_triggered"] is True

    def test_check_deviation_plan_not_found(self, mock_plan_lifecycle):
        from app.graphs.nodes.plan import check_deviation_node

        mock_plan_lifecycle.get.side_effect = LookupError("not found")

        state = {"plan_id": "nonexistent"}
        result = check_deviation_node(state, plan_lifecycle=mock_plan_lifecycle)

        assert result["deviation_count"] == 0
        assert result["deviation_triggered"] is False

    def test_generate_plan_node(self, mock_plan_lifecycle):
        from app.graphs.nodes.plan import generate_plan_node

        state = {
            "plan_id": "p1",
            "goal": "学习进程调度",
            "course": "os",
        }
        result = generate_plan_node(state, plan_lifecycle=mock_plan_lifecycle)

        mock_plan_lifecycle.replan.assert_called_once()
        assert result["generated_plan"] is not None

    def test_retrieve_grounding_node(self, mock_recall):
        from app.graphs.nodes.plan import retrieve_grounding_node
        from app.models import RetrievalChunk

        chunk = RetrievalChunk(
            id="g1",
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

        state = {"goal": "进程调度", "course": "os"}
        result = retrieve_grounding_node(state, recall=mock_recall)

        assert len(result["grounding_chunks"]) == 1
