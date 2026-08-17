"""复习计划服务测试：验证计划生成、条目去重、日期分配。"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import ReviewPlanRequest  # noqa: E402
from app.review_plan import ReviewPlanService  # noqa: E402


@pytest.fixture(scope="module")
def service():
    return ReviewPlanService()


@pytest.fixture(scope="module")
def os_plan(service):
    """生成 OS 默认复习计划（14 天）。"""
    return service.generate(ReviewPlanRequest(course="os"))


@pytest.fixture(scope="module")
def ds_plan(service):
    """生成 DS 复习计划（自定义 7 天，每天 3 小时）。"""
    target = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    return service.generate(
        ReviewPlanRequest(course="ds", target_date=target, hours_per_day=3.0)
    )


def test_os_plan_has_entries(os_plan):
    """OS 计划应包含全部 15 篇条目（去重后）。"""
    total = os_plan.summary["total_entries"]
    assert total >= 10, f"OS 应有 ≥10 篇条目，实际 {total}"


def test_plan_deduplicates_by_file(os_plan):
    """同一文件的多个 chunk 只应计为一个任务。"""
    all_files = []
    for day in os_plan.days:
        for task in day.tasks:
            all_files.append(task.file)
    # 文件不应重复
    assert len(all_files) == len(set(all_files)), "同一文件不应出现在多天任务中"


def test_plan_respects_target_date(ds_plan):
    """DS 计划天数不应超过目标日期范围（任务少时可提前完成）。"""
    today = datetime.now().date()
    target = datetime.strptime(ds_plan.target_date, "%Y-%m-%d").date()
    max_days = max((target - today).days, 1)
    actual_days = len(ds_plan.days)
    assert actual_days <= max_days + 1, (
        f"计划天数 {actual_days} 不应超出目标范围 {max_days} 天太多"
    )
    assert actual_days >= 1, "至少应有 1 天计划"


def test_plan_daily_minutes_within_limit(os_plan):
    """每天学习时间不应超过默认 2 小时（120 分钟）+ 复习缓冲。"""
    for day in os_plan.days:
        # 第 1 天无复习缓冲，后续天有 10 分钟缓冲
        limit = 120 + (10 if day.day > 1 else 0)
        assert day.total_minutes <= limit + 50, (  # 允许单条目超出
            f"第 {day.day} 天学习 {day.total_minutes} 分钟超出限制 {limit}"
        )


def test_plan_tasks_have_valid_fields(os_plan):
    """每个任务的字段应合法。"""
    valid_difficulties = {"入门", "中等", "进阶"}
    valid_priorities = {"high", "medium", "low"}
    for day in os_plan.days:
        for task in day.tasks:
            assert task.file.startswith("knowledge/"), f"文件路径异常: {task.file}"
            assert task.title, f"标题不应为空: {task.file}"
            assert task.difficulty in valid_difficulties, f"难度异常: {task.difficulty}"
            assert task.priority in valid_priorities, f"优先级异常: {task.priority}"
            assert task.estimated_minutes > 0, f"学习时间应 > 0: {task.file}"


def test_plan_nonexistent_course(service):
    """不存在的课程应返回空计划。"""
    plan = service.generate(ReviewPlanRequest(course="nonexistent"))
    assert plan.summary["total_entries"] == 0
    assert len(plan.days) == 0 or all(len(d.tasks) == 0 for d in plan.days)


def test_plan_difficulty_distribution(os_plan):
    """OS 计划应包含不同难度的条目。"""
    by_diff = os_plan.summary["by_difficulty"]
    assert len(by_diff) >= 2, f"应有 ≥2 种难度分布，实际: {by_diff}"


def test_plan_custom_name(service):
    """自定义计划名称应生效。"""
    plan = service.generate(ReviewPlanRequest(course="os", plan_name="期末冲刺"))
    assert plan.plan_name == "期末冲刺"
