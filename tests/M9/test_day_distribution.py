"""M9 分日的**每日容量**不变量（`goal_planner._distribute`）。

已证实缺陷的回归：`total_days`（请求窗口）曾被当成硬截断，排不完的任务被**一次性倾倒**进一个
不设上限的「第 `total_days + 1` 天」。实测（2026-09-22，14 天窗口；倍数的**分母是该天的可用容量**，
即 `hours_per_day × 60 − 10` 复习缓冲）：

| 请求 | 溢出天 | 当日可用容量 | 倍数 |
| --- | --- | --- | --- |
| 默认（全部课程，2 小时/天） | 114 个任务 / 3890 分钟 | 110（120 − 10） | 35.4× |
| 全部课程，1 小时/天 | 128 个任务 / 4590 分钟 | 50（60 − 10） | 91.8× |
| 全部课程，0.5 小时/天 | 128 个任务 / 4590 分钟 | 20（30 − 10） | 229.5× |
| `os`，1 小时/天 | 6 个任务 / 190 分钟 | 50（60 − 10） | 3.8× |
| 全部课程，8 小时/天 | **无溢出**（12 天内排完） | 470（480 − 10） | — |

这不是「计划变长了」，而是某一天的时长静默违反 `hours_per_day`。探针集内最高 **229.5 倍**
（`0.5 小时/天`）。倍数**依赖分母口径**，引用时必须连分母一起引用：同一个默认请求对
`hours_per_day × 60` 是 32.4×、对声明的每日上界（`hours_per_day × 60 + 10`）是 29.9×。
缺陷在低容量下最重；容量足够时（8 小时/天）根本不触发。

声明口径（判据来自 `review-plan` 技能与 `models.py`，不是本测试自造）：

- `hours_per_day` 是每日**容量**（预算），不是目标、也不是硬截断——`SKILL.md` 明写「每日容量：
  `hours_per_day × 60` 分钟」，且唯一声明的每日上界是「每天学习时间不超过 `hours_per_day × 60
  + 10` 分钟」。
- `target_date` 是**视野**而非硬期限——偏差模型正是以「可能偏离它」为前提。
- 计划**允许超过视野**：`review_plan.py` 里「剩余任务追加到最后一天（如果超出天数）」是唯一的
  正面声明，M9 逐字继承。故超出**窗口**合法，超出**每日容量**不合法。

因此本文件钉住的是：窗口是起点，容量才是硬约束；追加的天与窗口内的天受**同一**容量约束。

**这条保证的已知边界（不得读成「永不超容量」）**：`_distribute` 里 `and day_tasks` 守卫保证每天
的**第一个**任务必被放入，故单条任务本身长于当日容量时，该天必然超出。最小原子任务是 25 分钟，
故**第 2 天起**（当日容量扣了复习缓冲，`hours_per_day × 60 − 10 < 25`，即
`hours_per_day < 35/60 ≈ 0.5833`）**每一天**都踩到这条守卫，容量保证在该区间内**完全空转**。
**第 1 天不扣缓冲**（`if d > 0` 才减 `REVIEW_BUFFER_MINUTES`），容量是 `hours_per_day × 60`，
只有当日首条任务本身就超过它时才超出——要靠最小任务保证则需 `hours_per_day < 25/60 ≈ 0.4167`。
`0.5 小时/天`（合法下界）下默认请求（全部课程）实测 142 天，其中 120 天超出声明的每日上界
（`0.5 × 60 + 10 = 40` 分钟），最大 60 分钟；第 1 天也在其中，因为该请求的首条任务是 50 分钟 > 30。
残留的准确表述是「每天至多**一条**任务造成超出」，不是「不超出」。
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
    """旧代码下整组必红：溢出天装着全部余量，任务数远大于 1。

    注意这是**整组**意义上的回归，不是逐参数都有效：8 个参数化里只有 5 个能区分修复前后。
    `os-2.0` / `os-8.0` / `None-8.0` 的任务集在 14 天窗口内就排完了，旧代码从不进入那个不设上限的
    溢出天分支，输出与修复后**逐字节相同**，故这三个用例对本次修复不构成证据。
    """
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
    """超出**窗口**是声明允许的；本用例把它钉成事实，以免被误当成缺陷改回去。

    目标日期**相对今天**推导，不写死。写死的日期会随日历流逝而变成过去，窗口缩到 0 乃至负数，
    在**没有任何代码改动**的情况下把本文件（进而整个套件）变红——曾写死 `2026-10-06`，
    到那天起必红。

    实测它**能**区分修复前后：旧代码把余量倒进一个日期恰为 `start + total_days`（即目标日期当天）
    的溢出天，故 `last > target` 为假；修复后逐日追加，末日晚于目标日期，故为真。
    """
    target = date.today() + timedelta(days=14)
    plan = _plan(course=_ALL_COURSES, hours_per_day=1.0, target_date=str(target))
    days = _days(plan)
    last = datetime.strptime(days[-1].date, "%Y-%m-%d").date()

    # 两边都取自**同一次**时钟读数：`target` 在上面一次性算出，断言时不再读第二次表。若在断言处
    # 再取一次 `date.today()`，它与 planner 内部的 `datetime.now()` 跨过午夜就会差一天，那是在测
    # 时钟不是测语义。（`target` 本身是 `date.today()` 派生的，这点不必回避。）
    assert last > target, "计划必须排到请求目标日期之后——窗口是视野，不是截断"


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
    """`total_days` 必须与逐日明细自洽。

    这条性质**修复前就成立**：`total_days=len(days)` 自首个 planner 提交（`afd14d3`）起如此，
    本次修复没有碰那一行。故本用例**不能**区分修复前后，它对「修复前必红」没有贡献。
    修复改变的是天数的**值**（默认请求 15 → 52），不是 `total_days` 的**语义**。
    """
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


def test_capacity_guarantee_is_vacuous_below_the_smallest_task() -> None:
    """`hours_per_day=0.5`（合法下界）下容量保证**完全空转**——本修复不消除的残留。

    最小原子任务是 25 分钟，而**第 2 天起**的当日可用容量只有 `30 − 10 = 20` 分钟，于是
    `and day_tasks` 守卫在那里的**每一天**都触发（第 1 天不扣缓冲，容量 30；本请求的首条任务是
    50 分钟，故第 1 天也超出，但那是任务选择的结果，不是这条 25 分钟的推理保证的）。实测默认请求
    （全部课程）142 天里 120 天超出声明的每日上界（`0.5 × 60 + 10 = 40` 分钟），最大 60 分钟。
    本用例把这个已知边界钉住，好让它**可见**，而不是被读成「已修好」。

    残留的准确表述是「每天至多**一条**任务造成超出」，不是「不超出」；第 2 天起的失效带是
    `hours_per_day × 60 − 10 < 25`，即 `hours_per_day < 35/60 ≈ 0.5833`。
    """
    plan = _plan(course=_ALL_COURSES, hours_per_day=0.5)
    days = _days(plan)
    declared_ceiling = int(0.5 * 60) + 10

    over = [day for day in days if day.total_minutes > declared_ceiling]
    assert over, "0.5 小时/天下应当存在超限的天，否则本用例失去意义"
    # 每天至多一条任务造成超出——这是守卫的直接后果，不是巧合。
    assert all(len(day.tasks) == 1 for day in over)
    # 保证在该区间内完全空转：超限的天占绝大多数，不是零星例外。
    assert len(over) > len(days) // 2
