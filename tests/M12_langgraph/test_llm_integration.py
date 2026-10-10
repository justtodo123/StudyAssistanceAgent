"""Tests for LLM integration in LangGraph graph nodes.

Covers:
- GraphLLM basic contract (sync wrapper, fallback on failure)
- LLM-based intent classification in the assistance router
- LLM-based remediation hints in evaluate_node
- Deterministic fallback when LLM is None or returns None
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.graphs import LANGGRAPH_AVAILABLE

pytestmark = pytest.mark.skipif(
    not LANGGRAPH_AVAILABLE,
    reason="langgraph is not installed",
)


class _FakeLLM:
    """Minimal stand-in for GraphLLM that returns a canned response."""

    def __init__(self, response: str | None = "study") -> None:
        self._response = response
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str | None:
        self.calls.append(prompt)
        return self._response


class TestGraphLLMContract:
    def test_empty_prompt_returns_none(self):
        from app.graphs.llm import GraphLLM

        llm = GraphLLM(api_key="test-key-at-least-32-bytes-long-xxxx")
        assert llm.complete("") is None
        assert llm.complete("   ") is None

    def test_constructor_rejects_empty_key(self):
        from app.graphs.llm import GraphLLM

        with pytest.raises(ValueError, match="api_key"):
            GraphLLM(api_key="")

    def test_max_tokens_capped(self):
        from app.graphs.llm import GraphLLM

        llm = GraphLLM(api_key="test-key-at-least-32-bytes-long-xxxx", max_tokens=9999)
        assert llm._max_tokens == 512

    def test_complete_returns_none_on_sdk_failure(self):
        from app.graphs.llm import GraphLLM

        llm = GraphLLM(api_key="test-key-at-least-32-bytes-long-xxxx")
        with patch.object(llm, "_get_client", return_value=None):
            result = llm.complete("What is scheduling?")
        assert result is None


class TestLLMIntentClassification:
    def test_llm_classifies_study_intent(self):
        from app.graphs.assistance_graph import router_node

        fake_llm = _FakeLLM("study")
        state = {"intent": "general", "question": "什么是进程调度？"}
        result = router_node(state, llm=fake_llm)
        assert result["intent"] == "study"
        assert len(fake_llm.calls) == 1

    def test_llm_classifies_plan_intent(self):
        from app.graphs.assistance_graph import router_node

        fake_llm = _FakeLLM("plan")
        state = {"intent": "general", "question": "怎么安排期末考试复习？"}
        result = router_node(state, llm=fake_llm)
        assert result["intent"] == "plan"

    def test_llm_failure_falls_back_to_api_intent(self):
        from app.graphs.assistance_graph import router_node

        fake_llm = _FakeLLM(response=None)
        state = {"intent": "general", "question": "什么是TCP？"}
        result = router_node(state, llm=fake_llm)
        assert result["intent"] == "general"

    def test_explicit_api_intent_skips_llm(self):
        from app.graphs.assistance_graph import router_node

        fake_llm = _FakeLLM("plan")
        state = {"intent": "study", "question": "怎么安排复习？"}
        result = router_node(state, llm=fake_llm)
        assert result["intent"] == "study"
        assert len(fake_llm.calls) == 0

    def test_no_llm_uses_api_intent(self):
        from app.graphs.assistance_graph import router_node

        state = {"intent": "plan", "question": "安排学习计划"}
        result = router_node(state, llm=None)
        assert result["intent"] == "plan"

    def test_invalid_llm_response_falls_back(self):
        from app.graphs.assistance_graph import router_node

        fake_llm = _FakeLLM("nonsense_garbage")
        state = {"intent": "general", "question": "test question"}
        result = router_node(state, llm=fake_llm)
        assert result["intent"] == "general"

    def test_empty_question_skips_llm(self):
        from app.graphs.assistance_graph import router_node

        fake_llm = _FakeLLM("study")
        state = {"intent": "general", "question": ""}
        result = router_node(state, llm=fake_llm)
        assert result["intent"] == "general"
        assert len(fake_llm.calls) == 0


class TestLLMRemediation:
    def _make_state(self) -> dict:
        return {
            "questions": [
                {
                    "id": "q1",
                    "question": "SJF 的全称是什么",
                    "type": "concept",
                    "answer": "Shortest Job First",
                    "source_file": "knowledge/os/sched.md",
                    "source_title": "调度",
                    "tags": ["scheduling"],
                    "difficulty": "easy",
                    "attempt_count": 0,
                    "correct": None,
                }
            ],
            "current_index": 0,
            "current_answer": "我不知道",
            "explanation": "SJF 是一种调度算法",
        }

    def test_llm_hint_used_when_available(self):
        from app.graphs.nodes.study import evaluate_node

        fake_llm = _FakeLLM("想想看，SJF 中的 S 代表什么")
        state = self._make_state()
        result = evaluate_node(state, llm=fake_llm)
        assert "想想看" in result["remediation"]
        assert result["state"] == "awaiting_answer"

    def test_llm_none_falls_back_to_template(self):
        from app.graphs.nodes.study import evaluate_node

        state = self._make_state()
        result = evaluate_node(state, llm=None)
        assert result["remediation"].startswith("提示")
        assert result["state"] == "awaiting_answer"

    def test_llm_failure_falls_back_to_template(self):
        from app.graphs.nodes.study import evaluate_node

        fake_llm = _FakeLLM(response=None)
        state = self._make_state()
        result = evaluate_node(state, llm=fake_llm)
        assert result["remediation"].startswith("提示")

    def test_correct_answer_skips_llm(self):
        from app.graphs.nodes.study import evaluate_node

        fake_llm = _FakeLLM("should not be called")
        state = self._make_state()
        state["current_answer"] = "Shortest Job First"
        result = evaluate_node(state, llm=fake_llm)
        assert result["remediation"] == ""
        assert len(fake_llm.calls) == 0

    def test_max_attempts_skips_llm_hint(self):
        from app.graphs.nodes.study import evaluate_node

        fake_llm = _FakeLLM("should not be called for max attempts")
        state = self._make_state()
        state["questions"][0]["attempt_count"] = 1
        result = evaluate_node(state, llm=fake_llm)
        assert "完整参考" in result["remediation"] or result["remediation"].startswith("提示")


class TestLLMInGraphContainer:
    def test_container_accepts_llm(self):
        from app.graphs.dependencies import GraphContainer

        fake_llm = _FakeLLM()
        container = GraphContainer(
            recall=MagicMock(),
            qa_service=MagicMock(),
            quiz_service=MagicMock(),
            review_scheduler=MagicMock(),
            goal_planner=MagicMock(),
            plan_lifecycle=MagicMock(),
            llm=fake_llm,
        )
        assert container.llm is fake_llm

    def test_container_llm_defaults_to_none(self):
        from app.graphs.dependencies import GraphContainer

        container = GraphContainer(
            recall=MagicMock(),
            qa_service=MagicMock(),
            quiz_service=MagicMock(),
            review_scheduler=MagicMock(),
            goal_planner=MagicMock(),
            plan_lifecycle=MagicMock(),
        )
        assert container.llm is None

    def test_limits_includes_llm_fields(self):
        from app.graphs.config import LangGraphLimits, validate_limits

        limits = LangGraphLimits()
        assert limits.max_llm_tokens == 256
        assert limits.max_llm_timeout_s == 30.0
        validate_limits(limits)

    def test_limits_reject_oversized_llm_tokens(self):
        from app.graphs.config import LangGraphLimits, validate_limits

        limits = LangGraphLimits(max_llm_tokens=9999)
        with pytest.raises(ValueError, match="max_llm_tokens"):
            validate_limits(limits)
