"""Tests for the study-session LangGraph."""

from __future__ import annotations

import pytest

from app.graphs import LANGGRAPH_AVAILABLE

pytestmark = pytest.mark.skipif(
    not LANGGRAPH_AVAILABLE,
    reason="langgraph is not installed",
)


class TestStudyGraph:
    def test_graph_compiles(self, graph_container):
        graph = graph_container.study_graph
        assert graph is not None

    def test_create_session_flow(self, graph_container):
        result = graph_container.study_graph.invoke({
            "course": "os",
            "topic": "进程调度",
            "question_count": 2,
            "use_llm": False,
        })

        assert result["state"] == "awaiting_answer"
        assert result["explanation"]
        assert len(result["questions"]) == 2
        assert result["current_index"] == 0

    def test_create_session_no_questions(self, graph_container, mock_quiz_service):
        from app.models import QuizResponse

        mock_quiz_service.generate.return_value = QuizResponse(
            quiz_name="empty",
            course="os",
            generated_at="2026-01-01",
            count=0,
            questions=[],
            summary={},
        )

        result = graph_container.study_graph.invoke({
            "course": "os",
            "topic": "冷门主题",
            "question_count": 1,
        })

        assert result["state"] == "completed"

    def test_submit_graph_compiles(self, graph_container):
        graph = graph_container.submit_graph
        assert graph is not None

    def test_submit_correct_answer(self, graph_container):
        result = graph_container.submit_graph.invoke({
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
                },
            ],
            "current_index": 0,
            "current_answer": "FCFS SJF RR",
            "explanation": "进程调度算法包括FCFS、SJF和RR",
            "course": "os",
            "session_id": "test",
            "sources": [],
            "topic": "进程调度",
        })

        assert result["last_evaluation"]["correct"] is True
        assert result["state"] == "completed"

    def test_submit_wrong_answer_retry(self, graph_container):
        result = graph_container.submit_graph.invoke({
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
                },
            ],
            "current_index": 0,
            "current_answer": "完全不相关的回答",
            "explanation": "进程调度算法包括FCFS、SJF和RR",
        })

        assert result["last_evaluation"]["correct"] is False
        assert result["state"] == "awaiting_answer"
        assert result["remediation"]
