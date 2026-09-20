"""M9 计划生命周期测试：采纳、进度、重规划。"""

from __future__ import annotations

import pytest

from app.goal_planner import GoalPlannerService
from app.learning_store import SqliteLearningStore
from app.models import GoalPlanRequest, PlanProgressRequest
from app.plan_lifecycle import PlanLifecycleService


pytestmark = pytest.mark.m9


@pytest.fixture
def lifecycle(tmp_path):
    store = SqliteLearningStore(":memory:")
    planner = GoalPlannerService(review_history={})
    service = PlanLifecycleService(store, planner)
    return service, store, planner


def _generate_and_persist(lifecycle, planner, goal="两周内掌握进程调度"):
    resp = planner.generate(GoalPlanRequest(goal=goal))
    lifecycle.persist_generated(resp)
    return resp


def test_adopt_transitions_state(lifecycle):
    service, store, planner = lifecycle
    resp = _generate_and_persist(service, planner)
    plan = service.adopt(resp.plan_id)
    assert plan["state"] == "adopted"
    assert plan["adopted_at"]
    assert store.get_plan(resp.plan_id)["state"] == "adopted"


def test_progress_event_is_idempotent(lifecycle):
    service, store, planner = lifecycle
    resp = _generate_and_persist(service, planner)
    task = resp.revisions[0].days[0].tasks[0]
    req = PlanProgressRequest(plan_id=resp.plan_id, task_id=task.task_id, event="completed")
    first = service.record_progress(req)
    second = service.record_progress(req)
    assert first.event_id == second.event_id
    assert len(store.list_progress_events(resp.plan_id)) == 1


def test_replan_requires_three_skips(lifecycle):
    service, store, planner = lifecycle
    resp = _generate_and_persist(service, planner)
    tasks = [t for day in resp.revisions[0].days for t in day.tasks]
    # 不足 3 个跳过不重规划
    service.record_progress(
        PlanProgressRequest(plan_id=resp.plan_id, task_id=tasks[0].task_id, event="skipped")
    )
    unchanged = service.replan(resp.plan_id)
    assert unchanged["state"] == "generated"

    # 累计 3 个跳过触发重规划
    for task in tasks[1:3]:
        service.record_progress(
            PlanProgressRequest(plan_id=resp.plan_id, task_id=task.task_id, event="skipped")
        )
    replanned = service.replan(resp.plan_id)
    assert replanned["state"] == "replanned"
    assert replanned["parent_revision_id"] == resp.revision_id
    assert replanned["revision_id"] == resp.revision_id + 1


def test_planner_does_not_write_study_sessions(lifecycle):
    service, store, planner = lifecycle
    resp = _generate_and_persist(service, planner)
    service.adopt(resp.plan_id)
    # plan 生命周期表不触碰 study_sessions / review_history
    assert store.get(resp.plan_id) is None  # study_sessions 无此记录
    assert store.get_review(resp.plan_id) is None  # review_history 无此记录
