"""M9 确定性目标驱动计划生成测试（只验证生成，不涉及采纳/进度/重规划）。"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager

import pytest

from app.goal_planner import SCHEMA_VERSION, GoalPlannerService
from app.learning_store import SqliteLearningStore
from app.models import GoalPlanConstraints, GoalPlanRequest


pytestmark = pytest.mark.m9


def _request(**kwargs) -> GoalPlanRequest:
    defaults = {"goal": "两周内掌握进程调度与死锁"}
    defaults.update(kwargs)
    return GoalPlanRequest(**defaults)


def test_plan_is_deterministic_and_versioned(goal_planner_service):
    req = _request()
    first = goal_planner_service.generate(req)
    second = goal_planner_service.generate(req)

    assert first.plan_id == second.plan_id
    assert first.revision_id == second.revision_id == 1
    assert first.schema_version == SCHEMA_VERSION == "m9-goal-plan-v1"
    assert first.revisions[0].days == second.revisions[0].days


def test_plan_identity_separates_course_and_constraints(goal_planner_service):
    """同名 Goal 配不同课程/约束必须得到不同 plan_id，否则已存计划会被互相覆盖。"""
    base = goal_planner_service.generate(_request(course="os"))
    other_course = goal_planner_service.generate(_request(course="ds"))
    other_excluded = goal_planner_service.generate(
        _request(course="os", constraints=GoalPlanConstraints(excluded_topics=["死锁"]))
    )
    assert len({base.plan_id, other_course.plan_id, other_excluded.plan_id}) == 3


def test_plan_response_echoes_request_scope(goal_planner_service):
    req = _request(
        course="os",
        hours_per_day=1.5,
        constraints=GoalPlanConstraints(required_topics=["死锁"]),
    )
    plan = goal_planner_service.generate(req)
    assert plan.course == "os"
    assert plan.hours_per_day == 1.5
    assert plan.constraints.required_topics == ["死锁"]


def test_excluded_topics_are_removed(goal_planner_service):
    req = _request(constraints=GoalPlanConstraints(excluded_topics=["死锁"]))
    plan = goal_planner_service.generate(req)
    topics = [t.topic for day in plan.revisions[0].days for t in day.tasks]
    assert all("死锁" not in topic for topic in topics)


def test_required_topics_are_pinned_first(goal_planner_service):
    req = _request(constraints=GoalPlanConstraints(required_topics=["死锁"]))
    plan = goal_planner_service.generate(req)
    tasks = [t for day in plan.revisions[0].days for t in day.tasks]
    required = [t for t in tasks if t.topic == "死锁"]
    assert required, "required topic must be present"
    assert tasks[: len(required)] == required


def test_hours_per_day_bounds_are_enforced():
    with pytest.raises(Exception):
        GoalPlanRequest(goal="x", hours_per_day=0.1)
    with pytest.raises(Exception):
        GoalPlanRequest(goal="x", hours_per_day=9.0)


def test_unreviewed_tasks_are_ordered_first():
    # 用一份已复习历史，断言对应 topic 排后
    reviewed_file = "knowledge/os/process-management.md"
    service = GoalPlannerService(review_history={reviewed_file: {"review_count": 2}})
    plan = service.generate(_request(course="os"))
    tasks = [t for day in plan.revisions[0].days for t in day.tasks]
    reviewed = [t for t in tasks if t.file == reviewed_file]
    assert reviewed, "reviewed entry must be present"
    # 所有排在 reviewed 之前的任务必须都是未复习的
    idx = tasks.index(reviewed[0])
    assert all(not t.reviewed for t in tasks[:idx])


def test_tasks_are_deduplicated_to_topic_granularity(goal_planner_service):
    plan = goal_planner_service.generate(_request(course="os"))
    tasks = [t for day in plan.revisions[0].days for t in day.tasks]
    files = [t.file for t in tasks]
    assert len(files) == len(set(files)), "each knowledge entry appears once"


def test_planner_does_not_read_chunk_bodies(goal_planner_service):
    # Planner 只读 frontmatter 元数据；断言其模块不 import 内容切分/LLM 逻辑。
    import app.goal_planner as planner

    source = open(planner.__file__, encoding="utf-8").read()
    assert "split_headings" not in source
    assert "llm_client" not in source
    assert "content" not in source


def test_planner_does_not_write_state(tmp_path, monkeypatch):
    # 真守卫：真 store + 写入口全部 fail + 连接级 total_changes 审计 + 库快照比对。
    # 本用例此前是**空转**的——它构造了 Spy 却从未注入服务，`spy.saves == 0` 恒真；
    # 与 tests/M9/test_mastery_projection.py 的复合路径守卫互补。
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    store.save(
        {
            "session_id": "seed",
            "course": "os",
            "topic": "process",
            "state": "completed",
            "created_at": "2026-09-01T08:00:00",
            "updated_at": "2026-09-01T08:00:00",
            "answer_records": [
                {
                    "question_id": "q1",
                    "attempt_count": 1,
                    "answer_normalized": "seed",
                    "correct": True,
                    "feedback": "",
                    "created_at": "2026-09-01T08:01:00",
                }
            ],
        }
    )
    observer = sqlite3.connect(str(store.db_path))
    observer.execute("PRAGMA query_only=ON")
    before = "\n".join(observer.iterdump())
    deltas: list[int] = []
    original_connect = store._connect

    @contextmanager
    def audited_connect():
        with original_connect() as connection:
            started = connection.total_changes
            yield connection
            deltas.append(connection.total_changes - started)

    monkeypatch.setattr(store, "_connect", audited_connect)
    for name in ("save", "save_review", "save_plan", "save_progress_event"):
        monkeypatch.setattr(
            SqliteLearningStore, name, lambda *a, **k: pytest.fail("planner wrote state")
        )

    planner = GoalPlannerService(review_history=store.all_reviews())
    planner.generate(_request(course="os"))

    after = "\n".join(observer.iterdump())
    observer.close()
    assert hashlib.sha256(before.encode()).digest() == hashlib.sha256(after.encode()).digest()
    assert all(delta == 0 for delta in deltas)
