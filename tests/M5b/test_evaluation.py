"""Deterministic answer evaluation tests."""

from __future__ import annotations

import pytest

from app.models import QuizQuestion
from app.study_session import evaluate_answer


def _question(answer: str = "互斥、占有并等待、不可剥夺、循环等待", tags: list[str] | None = None) -> QuizQuestion:
    return QuizQuestion(
        question="死锁产生的四个必要条件是什么？",
        type="example",
        answer=answer,
        source_file="knowledge/os/deadlock.md",
        source_title="死锁",
        tags=tags or ["死锁"],
    )


@pytest.mark.m5b
class TestEvaluateAnswer:
    def test_exact_reference_is_correct(self):
        result = evaluate_answer(
            "互斥、占有并等待、不可剥夺、循环等待",
            _question(),
            "死锁四个条件",
        )
        assert result.correct is True
        assert result.method == "deterministic"

    def test_empty_answer_is_incorrect(self):
        result = evaluate_answer("   ", _question(), "死锁四个条件")
        assert result.correct is False
        assert result.feedback == "empty answer"

    def test_unrelated_answer_is_incorrect(self):
        result = evaluate_answer("先来先服务", _question(), "死锁四个条件")
        assert result.correct is False

    def test_question_without_answer_uses_explanation(self):
        question = _question(answer="")
        result = evaluate_answer(
            "死锁需要互斥、占有并等待、不可剥夺和循环等待",
            question,
            "死锁需要互斥、占有并等待、不可剥夺和循环等待四个条件。",
        )
        assert result.correct is True
