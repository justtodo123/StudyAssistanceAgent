"""M4 retrieval-priority checks for expanded course corpus."""

from __future__ import annotations

import pytest


@pytest.mark.m4
class TestRetrievalContentPriority:
    """Course questions should favor notes over navigation and interview material."""

    def test_course_question_prefers_course_note(self, retrieval_service):
        results, _ = retrieval_service.recall("AVL树的四种旋转方式分别是什么", top_k=3)
        assert results
        assert results[0].file == "knowledge/ds/avl-balanced-trees.md"

    def test_interview_question_prefers_interview_bank(self, retrieval_service):
        results, _ = retrieval_service.recall("面试时如何回答 AVL 树旋转", top_k=3)
        assert results
        assert "knowledge/interview/" in results[0].file
