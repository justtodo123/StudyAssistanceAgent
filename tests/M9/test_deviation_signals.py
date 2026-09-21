"""M9 偏差信号测试：逾期投影、跳过+逾期阈值、目标/约束变化触发重规划。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app import review_scheduler as review_scheduler_module
from app.goal_planner import GoalPlannerService
from app.learning_store import ReviewHistoryRepositoryAdapter, SqliteLearningStore
from app.models import (
    GoalPlanConstraints,
    GoalPlanRequest,
    PlanProgressRequest,
    PlanReplanRequest,
)
from app.plan_lifecycle import PlanLifecycleService, PlanNotFoundError
from app.review_scheduler import ReviewSchedulerService


pytestmark = pytest.mark.m9

OVERDUE_FILE = "knowledge/os/process-management.md"


class _StubReviewScheduler:
    """只提供逾期投影的桩，让重规划测试不依赖真实时钟与复习历史。"""

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


def _record(service, plan_id, tasks, event: str):
    for task in tasks:
        service.record_progress(
            PlanProgressRequest(plan_id=plan_id, task_id=task.task_id, event=event)
        )


# ── 阈值与去重 ────────────────────────────────────────────────────────────────


def test_overdue_events_count_toward_replan_threshold():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner)
    tasks = _tasks(response)

    _record(service, response.plan_id, tasks[:2], "overdue")
    assert service.replan(response.plan_id)["state"] == "generated"

    _record(service, response.plan_id, tasks[2:3], "overdue")
    replanned = service.replan(response.plan_id)
    assert replanned["state"] == "replanned"
    assert replanned["replan_reason"] == "deviated_tasks=3"


def test_skipped_and_overdue_combine_toward_threshold():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner)
    tasks = _tasks(response)

    _record(service, response.plan_id, tasks[:2], "skipped")
    _record(service, response.plan_id, tasks[2:3], "overdue")
    replanned = service.replan(response.plan_id)
    assert replanned["state"] == "replanned"
    assert replanned["replan_reason"] == "deviated_tasks=3"


def test_same_task_counted_once_across_event_kinds():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner)
    tasks = _tasks(response)

    # 同一 task 既 skipped 又 overdue 只算一个偏差任务：2 个偏差任务不足阈值
    _record(service, response.plan_id, tasks[:2], "skipped")
    _record(service, response.plan_id, tasks[:1], "overdue")
    assert service.replan(response.plan_id)["state"] == "generated"

    _record(service, response.plan_id, tasks[2:3], "skipped")
    assert service.replan(response.plan_id)["state"] == "replanned"


def test_completed_events_never_count_as_deviation():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner)
    tasks = _tasks(response)

    _record(service, response.plan_id, tasks[:5], "completed")
    assert service.replan(response.plan_id)["state"] == "generated"


# ── 复习逾期投影 ──────────────────────────────────────────────────────────────


def test_review_overdue_projection_triggers_replan_without_events():
    store = SqliteLearningStore(":memory:")
    planner = GoalPlannerService(review_history={})
    response = planner.generate(GoalPlanRequest(goal="两周内掌握进程调度", course="os"))
    tasks = _tasks(response)
    overdue = {t.file: 7 for t in tasks[:3]}
    service = PlanLifecycleService(
        store, planner, review_scheduler=_StubReviewScheduler(overdue)
    )
    service.persist_generated(response)

    assert store.list_progress_events(response.plan_id) == []
    replanned = service.replan(response.plan_id)
    assert replanned["state"] == "replanned"
    assert replanned["replan_reason"] == "deviated_tasks=3"


def test_overdue_projection_ignores_files_outside_the_plan():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(
        store, overdue={"knowledge/ds/sorting.md": 30, "knowledge/co/cache.md": 12}
    )
    response = _generate(service, planner, course="os")
    # 逾期文件不属于本计划任务 → 不构成偏差
    assert service.replan(response.plan_id)["state"] == "generated"


def test_overdue_projection_does_not_build_chunk_index(tmp_path, monkeypatch):
    """逾期投影只读复习历史，不得把 chunk 索引拉进计划路径（输入有界）。"""
    monkeypatch.setattr(
        review_scheduler_module, "_HISTORY_PATH", tmp_path / "review_history.json"
    )
    store = SqliteLearningStore(":memory:")
    scheduler = ReviewSchedulerService(ReviewHistoryRepositoryAdapter(store))
    past = datetime.now() - timedelta(days=30)
    store.save_review(
        OVERDUE_FILE,
        {
            "file": OVERDUE_FILE,
            "course": "os",
            "review_count": 1,
            "last_reviewed": past.isoformat(),
            "next_review": (past + timedelta(days=1)).isoformat(),
            "interval_days": 1,
        },
    )

    def _boom(*args, **kwargs):
        raise AssertionError("overdue projection must not build the chunk index")

    monkeypatch.setattr(review_scheduler_module, "build_index_cached", _boom)
    overdue = scheduler.overdue_by_file()
    assert overdue[OVERDUE_FILE] >= 29


def test_overdue_projection_matches_get_due_days_overdue(tmp_path, monkeypatch):
    """两条路径必须共用同一套 days_overdue 语义。"""
    monkeypatch.setattr(
        review_scheduler_module, "_HISTORY_PATH", tmp_path / "review_history.json"
    )
    store = SqliteLearningStore(":memory:")
    scheduler = ReviewSchedulerService(ReviewHistoryRepositoryAdapter(store))
    past = datetime.now() - timedelta(days=10)
    store.save_review(
        OVERDUE_FILE,
        {
            "file": OVERDUE_FILE,
            "course": "os",
            "review_count": 2,
            "last_reviewed": past.isoformat(),
            "next_review": (past + timedelta(days=4)).isoformat(),
            "interval_days": 4,
        },
    )
    monkeypatch.setattr(review_scheduler_module, "build_index_cached", lambda: [])
    due = {e.file: e.days_overdue for e in scheduler.get_due().entries}
    assert scheduler.overdue_by_file() == {OVERDUE_FILE: due[OVERDUE_FILE]}
    assert due[OVERDUE_FILE] == 6


# ── 目标 / 约束变化 ───────────────────────────────────────────────────────────


def test_goal_change_alone_triggers_replan():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner)

    replanned = service.replan(
        response.plan_id, PlanReplanRequest(goal="一周内攻克死锁与进程调度")
    )
    assert replanned["state"] == "replanned"
    assert replanned["replan_reason"] == "goal_or_constraint_changed"
    assert replanned["revisions"][-1]["goal"] == "一周内攻克死锁与进程调度"
    assert replanned["revision_id"] == response.revision_id + 1


def test_identical_override_does_not_trigger_replan():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os", hours_per_day=1.5)

    unchanged = service.replan(
        response.plan_id,
        PlanReplanRequest(course="os", hours_per_day=1.5, goal=response.revisions[0].goal),
    )
    assert unchanged["state"] == "generated"


def test_constraint_change_is_applied_not_dropped():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")
    assert "死锁" in {t.topic for t in _tasks(response)}

    replanned = service.replan(
        response.plan_id,
        PlanReplanRequest(constraints=GoalPlanConstraints(excluded_topics=["死锁"])),
    )
    topics = {
        t["topic"] for day in replanned["revisions"][-1]["days"] for t in day["tasks"]
    }
    assert "死锁" not in topics
    assert replanned["constraints"]["excluded_topics"] == ["死锁"]


def test_replan_preserves_course_hours_and_target():
    """回归：重规划不得丢掉课程/学时/目标日期（旧实现只回传 goal + target_date）。"""
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os", hours_per_day=1.0)

    _record(service, response.plan_id, _tasks(response)[:3], "skipped")
    replanned = service.replan(response.plan_id)

    assert replanned["course"] == "os"
    assert replanned["hours_per_day"] == 1.0
    assert replanned["target_date"] == response.target_date
    files = {
        t["file"] for day in replanned["revisions"][-1]["days"] for t in day["tasks"]
    }
    assert files and all(f.startswith("knowledge/os/") for f in files)


def test_replan_retains_previous_revisions_read_only():
    """旧 revision 只读保留，新 revision 追加为链尾。"""
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")

    _record(service, response.plan_id, _tasks(response)[:3], "skipped")
    first = service.replan(response.plan_id)
    assert [r["revision_id"] for r in first["revisions"]] == [1, 2]
    original_days = first["revisions"][0]["days"]

    service.replan(response.plan_id, PlanReplanRequest(goal="改为一周攻克死锁"))
    stored = store.get_plan(response.plan_id)
    assert [r["revision_id"] for r in stored["revisions"]] == [1, 2, 3]
    assert stored["revisions"][0]["days"] == original_days
    assert stored["parent_revision_id"] == 2
    assert stored["revision_id"] == 3


def test_replanned_record_keeps_goal_and_tasks():
    """回归：重规划后的记录必须与首次生成同形，否则再次重规划会丢 goal/tasks。"""
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")

    _record(service, response.plan_id, _tasks(response)[:3], "skipped")
    first = service.replan(response.plan_id)
    assert first["goal"]
    assert first["tasks"] and all("task_id" in t for t in first["tasks"])

    # 第二次重规划读回同一记录，必须仍能构造请求而不是崩在空 goal 上
    second = service.replan(response.plan_id, PlanReplanRequest(hours_per_day=1.5))
    assert second["state"] == "replanned"
    assert second["revision_id"] == 3
    assert second["hours_per_day"] == 1.5


def test_replan_is_deterministic_for_same_state():
    def run():
        store = SqliteLearningStore(":memory:")
        service, planner = _service(store)
        response = _generate(service, planner, course="os")
        _record(service, response.plan_id, _tasks(response)[:3], "skipped")
        return service.replan(response.plan_id)

    first, second = run(), run()
    assert first["revision_id"] == second["revision_id"] == 2
    assert first["replan_reason"] == second["replan_reason"]
    assert first["revisions"][-1]["days"] == second["revisions"][-1]["days"]


def test_replanned_plan_keeps_parent_chain_and_adoption():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner)
    service.adopt(response.plan_id)
    _record(service, response.plan_id, _tasks(response)[:3], "skipped")

    replanned = service.replan(response.plan_id)
    assert replanned["parent_revision_id"] == response.revision_id
    assert replanned["adopted_at"]
    assert replanned["state"] == "replanned"


# ── 事件词表 ──────────────────────────────────────────────────────────────────


def test_unknown_progress_event_is_rejected():
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner)
    with pytest.raises(ValueError):
        service.record_progress(
            PlanProgressRequest(
                plan_id=response.plan_id, task_id="whatever", event="postponed"
            )
        )
    assert store.list_progress_events(response.plan_id) == []


def test_progress_rejects_unknown_plan():
    store = SqliteLearningStore(":memory:")
    service, _planner = _service(store)
    with pytest.raises(PlanNotFoundError):
        service.record_progress(
            PlanProgressRequest(plan_id="missing", task_id="t", event="skipped")
        )


def test_adopt_and_replan_reject_unknown_plan():
    store = SqliteLearningStore(":memory:")
    service, _planner = _service(store)
    with pytest.raises(PlanNotFoundError):
        service.adopt("missing")
    with pytest.raises(PlanNotFoundError):
        service.replan("missing")
    with pytest.raises(PlanNotFoundError):
        service.get("missing")


def test_regenerating_same_goal_keeps_existing_plan_state():
    """幂等：同一 Goal/约束重复生成命中同一 plan_id，不得重置采纳与进度。"""
    store = SqliteLearningStore(":memory:")
    service, planner = _service(store)
    response = _generate(service, planner, course="os")
    service.adopt(response.plan_id)
    _record(service, response.plan_id, _tasks(response)[:3], "skipped")
    replanned = service.replan(response.plan_id)
    assert replanned["revision_id"] == 2

    # 重复提交同一请求：plan_id 相同，必须保留已存记录而不是回到 revision 1
    again = planner.generate(
        GoalPlanRequest(goal="两周内掌握进程调度", course="os")
    )
    assert again.plan_id == response.plan_id
    service.persist_generated(again)
    stored = store.get_plan(response.plan_id)
    assert stored["state"] == "replanned"
    assert stored["revision_id"] == 2
    assert stored["adopted_at"]
    assert len(store.list_progress_events(response.plan_id)) == 3
