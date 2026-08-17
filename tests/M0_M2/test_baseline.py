"""M0-M2 基线回归测试：提炼自 platform/tests/ 的核心断言。

目的：固化已完成功能的关键验证点，作为后续阶段的回归基线。
新增阶段不应修改本文件；如需扩展回归，在 tests/regression/ 中新增。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))

from app.knowledge_index import _parse_frontmatter, _split_headings  # noqa: E402
from app.models import QaRequest, QuizRequest, ReviewLogRequest  # noqa: E402
from app.review_scheduler import INTERVAL_SEQUENCE  # noqa: E402


# ── 知识库索引 ────────────────────────────────────────────────────────────────


class TestKnowledgeIndex:
    """知识库索引构建与解析。"""

    def test_index_builds(self, knowledge_chunks):
        assert len(knowledge_chunks) >= 30, (
            f"知识库应有 ≥30 个切片，实际 {len(knowledge_chunks)}"
        )

    def test_all_courses_present(self, knowledge_chunks):
        courses = {c.course for c in knowledge_chunks}
        assert {"os", "ds", "co"}.issubset(courses), f"缺少课程，实际: {courses}"

    def test_frontmatter_has_required_fields(self, knowledge_chunks):
        for chunk in knowledge_chunks[:10]:
            assert chunk.file, "file 不应为空"
            assert chunk.course, f"{chunk.file} 缺少 course"
            assert chunk.title, f"{chunk.file} 缺少 title"

    def test_split_headings_multiple_sections(self):
        text = "## A\n内容a\n## B\n内容b\n"
        sections = _split_headings(text)
        assert [t for t, _ in sections] == ["A", "B"]


# ── BM25 检索 ─────────────────────────────────────────────────────────────────


class TestBm25Search:
    """BM25 关键词检索。"""

    def test_tokenizer_handles_cjk_and_english(self):
        from app.bm25 import _tokenize

        toks = _tokenize("读者写者问题如何用PV操作实现")
        assert "pv" in toks
        assert "读者" in toks

    def test_recall_finds_scheduling(self, retrieval_service):
        results, mode = retrieval_service.recall("进程调度算法", top_k=5)
        assert results
        assert any("scheduling" in r.file or "调度" in r.title for r in results)


# ── 多路召回 ───────────────────────────────────────────────────────────────────


class TestMultiRecall:
    """多路召回 + RRF 融合。"""

    def test_hybrid_mode(self, retrieval_service):
        results, mode = retrieval_service.recall("虚拟内存", top_k=3)
        assert mode in ("hybrid", "keyword-only")
        assert len(results) >= 1

    def test_course_filter(self, retrieval_service):
        results, _ = retrieval_service.recall("排序", top_k=5, course="ds")
        for r in results:
            assert r.course == "ds" or "knowledge/ds/" in r.file

    def test_file_dedup(self, retrieval_service):
        results, _ = retrieval_service.recall("进程", top_k=10)
        files = [r.file for r in results]
        assert len(files) == len(set(files)), "结果中不应有重复文件"


# ── 问答服务 ───────────────────────────────────────────────────────────────────


class TestQaService:
    """问答服务（降级模式）。"""

    def test_fallback_returns_sources(self, qa_service):
        resp = qa_service.answer(
            QaRequest(question="什么是死锁", course="os", use_llm=False)
        )
        assert resp.sources
        assert "出处" in resp.answer

    def test_source_paths_valid(self, qa_service):
        resp = qa_service.answer(
            QaRequest(question="快速排序", course="ds", use_llm=False)
        )
        for s in resp.sources:
            assert s.file.startswith("knowledge/")


# ── 测验生成 ───────────────────────────────────────────────────────────────────


class TestQuizGenerator:
    """测验生成服务。"""

    def test_generates_questions(self, quiz_service):
        resp = quiz_service.generate(QuizRequest(course="os", count=3))
        assert resp.count >= 1

    def test_filter_by_topics(self, quiz_service):
        resp = quiz_service.generate(
            QuizRequest(course="os", count=5, topics=["进程"])
        )
        for q in resp.questions:
            assert "进程" in q.tags or "进程" in q.question

    def test_nonexistent_course_empty(self, quiz_service):
        resp = quiz_service.generate(QuizRequest(course="xxx"))
        assert resp.count == 0


# ── 复习排程 ───────────────────────────────────────────────────────────────────


class TestReviewScheduler:
    """复习排程服务。"""

    def test_interval_progression(self, isolated_scheduler):
        req = ReviewLogRequest(file="knowledge/os/test.md", course="os")
        intervals = []
        for _ in range(5):
            result = isolated_scheduler.log_review(req)
            intervals.append(result["interval_days"])
        assert intervals == [1, 2, 4, 8, 16]

    def test_get_due_empty(self, isolated_scheduler):
        resp = isolated_scheduler.get_due()
        assert resp.total_due == 0


# ── 复习计划 ───────────────────────────────────────────────────────────────────


class TestReviewPlan:
    """复习计划生成。"""

    def test_plan_has_entries(self, review_plan_service):
        from app.models import ReviewPlanRequest

        plan = review_plan_service.generate(ReviewPlanRequest(course="os"))
        assert plan.summary["total_entries"] >= 10

    def test_plan_dedup(self, review_plan_service):
        from app.models import ReviewPlanRequest

        plan = review_plan_service.generate(ReviewPlanRequest(course="os"))
        all_files = [t.file for d in plan.days for t in d.tasks]
        assert len(all_files) == len(set(all_files))
