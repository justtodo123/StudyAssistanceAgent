"""M9 分日的**每日容量**不变量（`goal_planner._distribute`）。

已证实缺陷的回归：`total_days`（请求窗口）曾被当成硬截断，排不完的任务被**一次性倾倒**进一个
不设上限的「第 `total_days + 1` 天」。实测（2026-09-22，14 天窗口）：

| 请求 | 溢出天 | 当日可用容量 |
| --- | --- | --- |
| 默认（全部课程，2 小时/天） | 114 个任务 / 3890 分钟 | 110（120 − 10 复习缓冲） |
| 全部课程，1 小时/天 | 128 个任务 / 4590 分钟 | 50（60 − 10） |
| `os`，1 小时/天 | 6 个任务 / 190 分钟 | 50（60 − 10） |

这不是「计划变长了」，而是某一天的时长静默违反 `hours_per_day`（最高 92 倍）。

声明口径（判据来自 `review-plan` 技能与 `models.py`，不是本测试自造）：

- `hours_per_day` 是每日**容量**（预算），不是目标、也不是硬截断——`SKILL.md` 明写「每日容量：
  `hours_per_day × 60` 分钟」，且唯一声明的每日上界是「每天学习时间不超过 `hours_per_day × 60
  + 10` 分钟」。
- `target_date` 是**视野**而非硬期限——偏差模型正是以「可能偏离它」为前提。
- 计划**允许超过视野**：`review_plan.py` 里「剩余任务追加到最后一天（如果超出天数）」是唯一的
  正面声明，M9 逐字继承。故超出**窗口**合法，超出**每日容量**不合法。

因此本文件钉住的是：窗口是起点，容量才是硬约束；追加的天与窗口内的天受**同一**容量约束。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.goal_planner import REVIEW_BUFFER_MINUTES, GoalPlannerService
from app.models import GoalPlanRequest


pytestmark = pytest.mark.m9

# 默认请求（无 course）覆盖全部课程，任务集最大——缺陷在它身上最明显。
_ALL_COURSES = None
_ONE_COURSE = "os"


def _plan(*, course=_ONE_COURSE, hours_per_day: float = 2.0, target_date: str | None = None):
    request = GoalPlanRequest(
        goal="两周内掌握进程调度与死锁",
        course=course,
        hours_per_day=hours_per_day,
        target_date=target_date,
    )
    return GoalPlannerService().generate(request)


def _days(plan) -> list:
    return plan.revisions[0].days


def _task_minutes(day) -> int:
    return sum(task.estimated_minutes for task in day.tasks)


def _available_minutes(day, daily_minutes: int) -> int:
    """该天的可用容量：第 2 天起扣除复习缓冲（与 `_distribute` 同式）。"""
    available = daily_minutes - (REVIEW_BUFFER_MINUTES if day.day > 1 else 0)
    return max(available, 0)


def _capacity_violations(days, daily_minutes: int) -> list[tuple[int, int, int]]:
    """返回真正违反每日容量的天：`(day, 任务分钟数, 容量)`。

    **刻意带一条例外**：`_distribute` 的 `and day_tasks` 守卫保证每天的第一个任务必被放入，
    故单条任务的时长若本身就超过当日容量，该天必然超出。这条例外是**声明过的**（见模块 docstring
    与 `_distribute` 的 docstring），故判据是「超出容量的天**恰好只装一个任务**」，而不是「绝不超出」。
    """
    violations = []
    for day in days:
        if not day.tasks:
            continue
        used = _task_minutes(day)
        available = _available_minutes(day, daily_minutes)
        if used > available and len(day.tasks) != 1:
            violations.append((day.day, used, available))
    return violations


# ── 缺陷回归：容量是硬约束 ────────────────────────────────────────────────────


@pytest.mark.parametrize("hours_per_day", (0.5, 1.0, 2.0, 8.0))
@pytest.mark.parametrize("course", (_ONE_COURSE, _ALL_COURSES))
def test_no_day_exceeds_the_daily_capacity(hours_per_day: float, course) -> None:
    """旧代码在此必失败：溢出天装着全部余量，任务数远大于 1。"""
    plan = _plan(course=course, hours_per_day=hours_per_day)

    assert _capacity_violations(_days(plan), int(hours_per_day * 60)) == []


def test_the_overflow_day_no_longer_exists_as_an_unbounded_dump() -> None:
    """默认请求（全部课程、2 小时/天）曾把余量全倒进最后一天。"""
    plan = _plan(course=_ALL_COURSES, hours_per_day=2.0)
    days = _days(plan)

    # 修复前：15 天，最后一天 114 个任务 / 3890 分钟，当日可用容量 110。
    assert plan.total_days > 15
    assert max(_task_minutes(day) for day in days) <= 2 * 60


# ── 窗口是起点，不是截断 ──────────────────────────────────────────────────────


def test_appended_days_continue_the_calendar_sequence() -> None:
    """追加的天必须是真实的连续日期，不是把余量塞进同一天。"""
    plan = _plan(course=_ALL_COURSES, hours_per_day=2.0)
    days = _days(plan)

    assert len(days) == plan.total_days
    assert [day.day for day in days] == list(range(1, len(days) + 1))
    start = datetime.strptime(days[0].date, "%Y-%m-%d").date()
    for index, day in enumerate(days):
        assert day.date == str(start + timedelta(days=index))


def test_plan_may_exceed_the_requested_window() -> None:
    """超出**窗口**是声明允许的；本用例把它钉成事实，以免被误当成缺陷改回去。"""
    target = date(2026, 10, 6)
    plan = _plan(course=_ALL_COURSES, hours_per_day=1.0, target_date=str(target))
    days = _days(plan)
    window = (target - datetime.strptime(days[0].date, "%Y-%m-%d").date()).days

    assert window >= 1
    assert plan.total_days > window


def test_a_plan_that_fits_the_window_gains_no_extra_day() -> None:
    """窗口够用时不得追加：容量约束不是「总是多排几天」。"""
    plan = _plan(course=_ONE_COURSE, hours_per_day=8.0)

    assert plan.total_days <= 14
    assert _capacity_violations(_days(plan), 8 * 60) == []


def test_appended_days_are_bounded_by_the_task_count() -> None:
    """每天至少装一个任务，故天数不可能超过「窗口 + 任务数」——防的是追加段不收敛。"""
    plan = _plan(course=_ALL_COURSES, hours_per_day=2.0)
    days = _days(plan)
    tasks = [task for day in days for task in day.tasks]

    assert plan.total_days <= 14 + len(tasks)
    assert len(tasks) > 0


# ── 报告出来的规模与逐日明细必须自洽 ─────────────────────────────────────────


def test_total_days_and_total_hours_match_the_day_list() -> None:
    """`total_days` 曾是与逐日明细不符的请求窗口值；现在它回报**真实**天数。"""
    plan = _plan(course=_ALL_COURSES, hours_per_day=2.0)
    days = _days(plan)
    task_minutes = sum(_task_minutes(day) for day in days)

    assert plan.total_days == len(days)
    assert plan.total_hours == round(task_minutes / 60, 1)


def test_each_day_minutes_include_the_review_buffer() -> None:
    """`total_minutes` 的构成口径：任务分钟数 + （第 2 天起且有任务时的）复习缓冲。"""
    plan = _plan(course=_ONE_COURSE, hours_per_day=2.0)

    for day in _days(plan):
        expected = _task_minutes(day)
        if day.day > 1 and day.tasks:
            expected += REVIEW_BUFFER_MINUTES
        assert day.total_minutes == expected


# ── 边界 ──────────────────────────────────────────────────────────────────────


def test_empty_task_set_still_yields_one_empty_day() -> None:
    """空语料不是本用例的靶子，但它必须不炸：保持既有的「1 个空天」行为。"""
    plan = GoalPlannerService().generate(
        GoalPlanRequest(goal="无匹配课程的目标", course="__no_such_course__")
    )
    days = _days(plan)

    assert len(days) == 1
    assert days[0].tasks == []
    assert plan.total_days == 1


def test_distribution_is_deterministic() -> None:
    """同一请求两次生成必须逐日相同——分日不得引入随机性。"""
    first = _days(_plan(course=_ALL_COURSES, hours_per_day=2.0))
    second = _days(_plan(course=_ALL_COURSES, hours_per_day=2.0))

    assert [day.model_dump() for day in first] == [day.model_dump() for day in second]


def test_single_oversized_task_is_the_only_documented_exception() -> None:
    """容量 20 分钟（`hours_per_day=0.5`）时进阶任务 50 分钟，该天必然超出——但只装**一个**任务。

    这是本修复**不**消除的残留，写在这里是为了让它可见而不是被当成「已修好」。
    """
    plan = _plan(course=_ONE_COURSE, hours_per_day=0.5)
    days = _days(plan)
    over = [
        day
        for day in days
        if day.tasks and _task_minutes(day) > _available_minutes(day, 30)
    ]

    assert over, "0.5 小时/天下应当存在装不下的任务，否则本用例失去意义"
    assert all(len(day.tasks) == 1 for day in over)
