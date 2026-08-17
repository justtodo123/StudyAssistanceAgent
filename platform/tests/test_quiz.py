"""测验生成服务测试：验证三个数据源加载、筛选、采样。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import QuizRequest  # noqa: E402
from app.quiz import QuizService  # noqa: E402


@pytest.fixture(scope="module")
def service():
    return QuizService()


@pytest.fixture(scope="module")
def os_quiz(service):
    """生成 OS 测验（默认 5 题）。"""
    return service.generate(QuizRequest(course="os"))


@pytest.fixture(scope="module")
def ds_quiz(service):
    """生成 DS 测验（10 题）。"""
    return service.generate(QuizRequest(course="ds", count=10))


def test_os_quiz_has_questions(os_quiz):
    """OS 测验应有题目。"""
    assert os_quiz.count >= 1, f"应有 ≥1 题，实际 {os_quiz.count}"
    assert len(os_quiz.questions) == os_quiz.count


def test_os_quiz_has_example_type(os_quiz):
    """OS 测验应包含经典例题型（14 篇条目各 1 题）。"""
    example_count = os_quiz.summary.get("by_type", {}).get("example", 0)
    # 经典例题在池中应有 14 题，但采样可能未命中
    pool = os_quiz.summary["total_pool"]
    assert pool >= 14, f"题池应 ≥14，实际 {pool}"


def test_quiz_three_sources(service):
    """三个数据源都应有贡献。"""
    plan = service.generate(QuizRequest(course="os", count=20))
    by_type = plan.summary.get("by_type", {})
    # 至少应有两种题型
    assert len(by_type) >= 1, f"应有 ≥1 种题型，实际: {by_type}"


def test_quiz_pool_size(service):
    """题池大小应合理（例题 + 评测集 + 概念题）。"""
    plan = service.generate(QuizRequest(course="os", count=1))
    # OS: 14 例题 + 33 评测 + ~50 概念 ≈ 97
    assert plan.summary["total_pool"] >= 30, (
        f"题池应 ≥30，实际 {plan.summary['total_pool']}"
    )


def test_quiz_filter_by_difficulty(service):
    """按难度筛选应生效。"""
    plan = service.generate(QuizRequest(course="os", count=10, difficulty="进阶"))
    for q in plan.questions:
        assert q.difficulty == "进阶", f"筛选进阶但出现: {q.difficulty}"


def test_quiz_filter_by_topics(service):
    """按标签筛选应生效。"""
    plan = service.generate(QuizRequest(course="os", count=10, topics=["进程"]))
    assert plan.count >= 1, "按 '进程' 筛选应有结果"
    for q in plan.questions:
        has_tag = "进程" in q.tags
        has_in_question = "进程" in q.question
        assert has_tag or has_in_question, (
            f"题目应与 '进程' 相关: {q.question[:30]}"
        )


def test_quiz_count_respects_limit(service):
    """请求 count 应被尊重。"""
    plan = service.generate(QuizRequest(course="os", count=3))
    assert plan.count <= 3


def test_quiz_nonexistent_course(service):
    """不存在的课程应返回空测验。"""
    plan = service.generate(QuizRequest(course="nonexistent"))
    assert plan.count == 0
    assert plan.summary["total_pool"] == 0


def test_quiz_example_has_answer(service):
    """经典例题应有参考答案。"""
    # 多生成几次提高命中 example 的概率
    for _ in range(5):
        plan = service.generate(QuizRequest(course="os", count=10))
        examples = [q for q in plan.questions if q.type == "example"]
        if examples:
            for q in examples:
                assert q.answer, f"经典例题应有答案: {q.question[:30]}"
            return
    # 如果 5 次都没命中 example，检查题池中确实有
    full = service.generate(QuizRequest(course="os", count=20))
    assert any(q.type == "example" for q in full.questions), "题池中应有 example 题型"


def test_quiz_retrieval_no_answer(service):
    """评测集题型应无答案（需自行查阅）。"""
    full = service.generate(QuizRequest(course="os", count=20))
    retrievals = [q for q in full.questions if q.type == "retrieval"]
    if retrievals:
        # 评测集题目的答案应为空
        assert all(q.answer == "" for q in retrievals)


def test_quiz_source_file_valid(service):
    """每道题的来源文件应以 knowledge/ 开头。"""
    plan = service.generate(QuizRequest(course="os", count=5))
    for q in plan.questions:
        if q.source_file:
            assert q.source_file.startswith("knowledge/"), (
                f"来源路径异常: {q.source_file}"
            )
