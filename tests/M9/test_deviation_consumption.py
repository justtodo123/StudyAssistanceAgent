"""M9 偏差消费台账测试：未消费偏差触发、台账只追加、重复调用不再产生幻影 revision。

改造前偏差是累计的：一旦 ≥ 3 就永久上锁，之后每次 replan 都追加一个内容与上一个
revision 逐字节相同的新 revision。这里钉住消费语义的边界。
"""

from __future__ import annotations

import json

import pytest

from app.goal_planner import GoalPlannerService
from app.learning_store import SqliteLearningStore
from app.models import (
    GoalPlanRequest,
    PlanProgressRequest,
    PlanReplanRequest,
)
from app.plan_lifecycle import DEVIATION_LEDGER_KEY, PlanLifecycleService


pytestmark = pytest.mark.m9


class _StubReviewScheduler:
    """只提供逾期投影的桩，让测试不依赖真实时钟与复习历史。"""

    def __init__(self, overdue: dict[str, int] | None = None) -> None:
        self._overdue = overdue or {}

    def overdue_by_file(self) -> dict[str, int]:
        return dict(self._overdue)


def _service(store, overdue: dict[str, int] | None = None):
    planner = GoalPlannerService(review_history={})
    service = PlanLifecycleService(
        store, planner, review_scheduler=_StubReviewScheduler(overdue)
    )
    return service, planner


def _generate(service, planner, **kwargs):
    goal = kwargs.pop("goal", "两周内掌握进程调度")
    response = planner.generate(GoalPlanRequest(goal=goal, **kwargs))
    service.persist_generated(response)
    return response


def _tasks(response):
    return [t for day in response.revisions[0].days for t in day.tasks]


def _skip(service, plan_id, tasks):
    for task in tasks:
        service.record_progress(
            PlanProgressRequest(plan_id=plan_id, task_id=task.task_id, event="skipped")
        )


def _fingerprint(store, plan_id) -> str:
    return json.dumps(store.get_plan(plan_id), sort_keys=True)


def _ledger(store, plan_id) -> list[dict]:
    return store.get_plan(plan_id).get(DEVIATION_LEDGER_KEY) or []


# ── 重复调用不再产生幻影 revision ─────────────────────────────────────────────


def test_repeat_replan_after_consumption_is_a_no_op():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")
    tasks = _tasks(response)

    _skip(service, response.plan_id, tasks[:3])
    first = service.replan(response.plan_id)
    assert first["state"] == "replanned"
    assert first["revision_id"] == 2

    before = _fingerprint(store, response.plan_id)
    second = service.replan(response.plan_id)
    assert second["revision_id"] == 2
    assert second == first
    # 未触发 ⇒ 不写盘，存库字节不变
    assert _fingerprint(store, response.plan_id) == before
    assert len(_ledger(store, response.plan_id)) == 1


def test_new_deviation_batch_advances_exactly_one_revision():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")
    tasks = _tasks(response)
    assert len(tasks) >= 6

    _skip(service, response.plan_id, tasks[:3])
    assert service.replan(response.plan_id)["revision_id"] == 2

    # 在从未偏差过的任务上产生 3 个新偏差 → 只推进一个 revision
    _skip(service, response.plan_id, tasks[3:6])
    third = service.replan(response.plan_id)
    assert third["revision_id"] == 3
    assert third["parent_revision_id"] == 2
    assert third["replan_reason"] == "deviated_tasks=3"

    # 再调一次不再追加
    assert service.replan(response.plan_id)["revision_id"] == 3


def test_persistent_overdue_projection_stops_producing_revisions():
    store = SqliteLearningStore(":memory:")
    planner = GoalPlannerService(review_history={})
    response = planner.generate(GoalPlanRequest(goal="两周内掌握进程调度", course="os"))
    tasks = _tasks(response)
    overdue = {t.file: 9 for t in tasks[:3]}
    service = PlanLifecycleService(
        store, planner, review_scheduler=_StubReviewScheduler(overdue)
    )
    service.persist_generated(response)

    assert service.replan(response.plan_id)["revision_id"] == 2
    # 逾期条件持续存在，但已被消费
    assert service.replan(response.plan_id)["revision_id"] == 2
    assert len(_ledger(store, response.plan_id)) == 1


def test_consumed_deviation_never_triggers_again():
    """刻意取舍：已消费的偏差任务即使再次逾期也不再触发。

    宁可漏报「复发偏差」，也不产内容相同的幻影 revision。这条取舍写进测试，
    避免以后被当成 bug 顺手改掉。
    """
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")
    tasks = _tasks(response)

    _skip(service, response.plan_id, tasks[:3])
    assert service.replan(response.plan_id)["revision_id"] == 2

    relapsed = PlanLifecycleService(
        store,
        planner,
        review_scheduler=_StubReviewScheduler({t.file: 30 for t in tasks[:3]}),
    )
    assert relapsed.replan(response.plan_id)["revision_id"] == 2


# ── 目标/约束变化不吞未达阈值的偏差 ───────────────────────────────────────────


def test_goal_change_does_not_consume_subthreshold_deviation():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")
    tasks = _tasks(response)

    _skip(service, response.plan_id, tasks[:2])
    changed = service.replan(
        response.plan_id, PlanReplanRequest(goal="一周内攻克死锁与进程调度")
    )
    assert changed["revision_id"] == 2
    assert changed["replan_reason"] == "goal_or_constraint_changed"
    # 纯变更不消费任何偏差
    assert _ledger(store, response.plan_id)[-1]["consumed_task_ids"] == []

    # 未达阈值的 2 个偏差保留：再 1 个就到 3
    _skip(service, response.plan_id, tasks[2:3])
    third = service.replan(response.plan_id)
    assert third["revision_id"] == 3
    assert third["replan_reason"] == "deviated_tasks=3"


def test_adoption_does_not_disturb_the_consumption_window():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")
    tasks = _tasks(response)

    service.adopt(response.plan_id)
    _skip(service, response.plan_id, tasks[:3])
    assert service.replan(response.plan_id)["revision_id"] == 2

    service.adopt(response.plan_id)
    after = service.replan(response.plan_id)
    assert after["revision_id"] == 2
    assert after["adopted_at"]


# ── 台账形状 ──────────────────────────────────────────────────────────────────


def test_ledger_records_one_entry_per_produced_revision():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")
    tasks = _tasks(response)

    _skip(service, response.plan_id, tasks[:3])
    service.replan(response.plan_id)
    _skip(service, response.plan_id, tasks[3:6])
    service.replan(response.plan_id)
    service.replan(response.plan_id, PlanReplanRequest(goal="改为一周攻克死锁"))

    ledger = _ledger(store, response.plan_id)
    assert [e["revision_id"] for e in ledger] == [2, 3, 4]
    assert [e["trigger"] for e in ledger] == [
        "deviated_tasks=3",
        "deviated_tasks=3",
        "goal_or_constraint_changed",
    ]

    # 消费单调：task_id 跨条目不重复，且并集正好是那 6 个偏差任务
    seen: set[str] = set()
    for entry in ledger:
        ids = entry["consumed_task_ids"]
        assert ids == sorted(ids)
        assert not (set(ids) & seen)
        seen |= set(ids)
    assert seen == {t.task_id for t in tasks[:6]}


def test_first_generation_writes_no_ledger_key():
    """首次生成不写台账键：缺键即空集，旧记录因此无需迁移。"""
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")
    assert DEVIATION_LEDGER_KEY not in store.get_plan(response.plan_id)


def test_legacy_record_without_ledger_triggers_once_then_converges():
    """改造前的旧记录（无台账键）行为与今天一致，首次重规划后自愈。"""
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")
    tasks = _tasks(response)

    _skip(service, response.plan_id, tasks[:3])
    legacy = store.get_plan(response.plan_id)
    legacy.pop(DEVIATION_LEDGER_KEY, None)
    store.save_plan(legacy)
    assert DEVIATION_LEDGER_KEY not in store.get_plan(response.plan_id)

    first = service.replan(response.plan_id)
    assert first["revision_id"] == 2
    assert _ledger(store, response.plan_id)[0]["consumed_task_ids"] == sorted(
        {t.task_id for t in tasks[:3]}
    )

    # 自愈：台账已建立，再调不追加
    assert service.replan(response.plan_id)["revision_id"] == 2


def test_replan_is_deterministic_across_consumption():
    def run():
        store = SqliteLearningStore(":memory:")
        service, planner = _service(store)
        response = _generate(service, planner, course="os")
        tasks = _tasks(response)
        _skip(service, response.plan_id, tasks[:3])
        service.replan(response.plan_id)
        _skip(service, response.plan_id, tasks[3:6])
        return service.replan(response.plan_id), _ledger(store, response.plan_id)

    first, first_ledger = run()
    second, second_ledger = run()
    assert first["revision_id"] == second["revision_id"] == 3
    assert first["replan_reason"] == second["replan_reason"]
    assert first["revisions"][-1]["days"] == second["revisions"][-1]["days"]
    assert first_ledger == second_ledger
