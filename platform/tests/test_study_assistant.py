"""多轮工具编排集成测试：验证 QA → Quiz → Review-log 完整链路。

这是 M2d 的核心测试，演示三个服务的串联调用：
1. QA 检索知识 → 获取来源
2. Quiz 生成相关题目 → 基于同一主题
3. Review-log 记录复习 → 更新间隔重复
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import QaRequest, QuizRequest, ReviewLogRequest  # noqa: E402
from app.qa import QaService  # noqa: E402
from app.quiz import QuizService  # noqa: E402
from app.review_scheduler import ReviewSchedulerService  # noqa: E402


@pytest.fixture(scope="module")
def qa_service():
    return QaService()


@pytest.fixture(scope="module")
def quiz_service():
    return QuizService()


@pytest.fixture
def scheduler(tmp_path):
    history_path = tmp_path / "review_history.json"
    with patch("app.review_scheduler._HISTORY_PATH", history_path):
        yield ReviewSchedulerService()


class TestMultiToolChain:
    """模拟「学一个知识点」的完整工具调用链。"""

    def test_qa_returns_sources_for_topic(self, qa_service):
        """步骤 1：QA 检索应返回与主题相关的知识片段。"""
        resp = qa_service.answer(
            QaRequest(question="进程调度算法有哪些", course="os", use_llm=False)
        )
        assert resp.sources, "QA 应返回来源"
        assert any("调度" in s.title or "scheduling" in s.file for s in resp.sources)
        assert resp.answer, "QA 应返回回答"

    def test_quiz_generates_related_questions(self, quiz_service):
        """步骤 2：Quiz 应生成与主题相关的题目。"""
        resp = quiz_service.generate(
            QuizRequest(course="os", count=2, topics=["调度"])
        )
        assert resp.count >= 1, "应生成 ≥1 道题"
        for q in resp.questions:
            has_tag = "调度" in q.tags
            has_in_question = "调度" in q.question
            assert has_tag or has_in_question, f"题目应与 '调度' 相关: {q.question[:30]}"

    def test_full_chain_qa_to_quiz_to_review(
        self, qa_service, quiz_service, scheduler
    ):
        """完整链路：QA 检索 → Quiz 出题 → Review-log 记录。"""
        # ── 步骤 1：QA 检索 ──
        qa_resp = qa_service.answer(
            QaRequest(question="死锁产生的条件", course="os", use_llm=False)
        )
        assert qa_resp.sources, "QA 应返回来源"
        source_file = qa_resp.sources[0].file

        # ── 步骤 2：Quiz 出题（基于 QA 来源的主题）──
        quiz_resp = quiz_service.generate(
            QuizRequest(course="os", count=2, topics=["死锁"])
        )
        assert quiz_resp.count >= 1, "Quiz 应生成相关题目"

        # ── 步骤 3：Review-log 记录复习 ──
        log_resp = scheduler.log_review(
            ReviewLogRequest(file=source_file, course="os")
        )
        assert log_resp["review_count"] == 1
        assert log_resp["interval_days"] == 1  # 首次复习，1 天后

        # ── 步骤 4：查询待复习 ──
        due_resp = scheduler.get_due(course="os")
        # 刚记录的不应在待复习列表中（明天才到期）
        # 但如果有其他逾期条目会出现

    def test_source_file_links_qa_and_review(
        self, qa_service, scheduler
    ):
        """验证 QA 来源文件可以正确传递给 Review-log。"""
        # QA 检索
        qa_resp = qa_service.answer(
            QaRequest(question="分页和分段的区别", course="os", use_llm=False)
        )
        assert qa_resp.sources
        source = qa_resp.sources[0]

        # 用 QA 的来源文件记录复习
        log_resp = scheduler.log_review(
            ReviewLogRequest(file=source.file, course="os")
        )
        assert log_resp["file"] == source.file

        # 验证历史中有记录
        history = scheduler._load_history()
        assert source.file in history

    def test_qa_and_quiz_share_course_context(self, qa_service, quiz_service):
        """QA 和 Quiz 应在同一课程上下文中工作。"""
        course = "ds"
        topic = "排序"

        # QA 检索 DS 课程
        qa_resp = qa_service.answer(
            QaRequest(question="排序算法比较", course=course, use_llm=False)
        )
        if qa_resp.sources:
            assert all(s.course == course for s in qa_resp.sources)

        # Quiz 出 DS 课程题
        quiz_resp = quiz_service.generate(
            QuizRequest(course=course, count=2, topics=[topic])
        )
        if quiz_resp.questions:
            assert all(q.source_file.startswith(f"knowledge/{course}/") or
                       not q.source_file for q in quiz_resp.questions)

    def test_review_interval_progression(self, scheduler):
        """验证复习间隔随次数递增（模拟多次学习同一知识点）。"""
        file = "knowledge/os/synchronization.md"
        intervals = []
        for _ in range(5):
            result = scheduler.log_review(
                ReviewLogRequest(file=file, course="os")
            )
            intervals.append(result["interval_days"])

        # 间隔应递增
        assert intervals == [1, 2, 4, 8, 16]
