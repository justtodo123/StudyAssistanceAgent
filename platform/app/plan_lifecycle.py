"""M9 计划生命周期服务：采纳、进度事件与确定性重规划。

Planner 只提建议；采纳是显式用户动作；进度事件驱动重规划；重规划只读权威
复习投影，不写 mastery、不写学习会话状态。
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from .models import (
    GoalPlanConstraints,
    GoalPlanRequest,
    GoalPlanResponse,
    PlanProgressEvent,
    PlanProgressRequest,
    PlanReplanRequest,
)

# 进度事件词表：completed 是完成，skipped / overdue 是偏差信号
RECORDED_EVENTS = frozenset({"completed", "skipped", "overdue"})
DEVIATION_EVENTS = frozenset({"skipped", "overdue"})
# 偏差任务数达到该阈值即触发重规划（跳过 + 逾期）
REPLAN_DEVIATION_THRESHOLD = 3


class PlanNotFoundError(LookupError):
    """计划 ID 不存在。"""


class IllegalPlanProgressEventError(ValueError):
    """进度事件不在 completed / skipped / overdue 词表内。"""


class PlanLifecycleService:
    """采纳 / 进度 / 重规划的编排。"""

    def __init__(self, store, goal_planner, review_scheduler=None) -> None:
        self._store = store
        self._planner = goal_planner
        # 只读逾期投影来源；缺省表示不把复习逾期计入偏差信号。
        self._review_scheduler = review_scheduler

    # ── 查询 ────────────────────────────────────────────────────────────────

    def get(self, plan_id: str) -> dict[str, Any]:
        return self._require_plan(plan_id)

    # ── 采纳 ────────────────────────────────────────────────────────────────

    def adopt(self, plan_id: str) -> dict[str, Any]:
        plan = self._require_plan(plan_id)
        plan["state"] = "adopted"
        plan["adopted_at"] = datetime.now().isoformat()
        plan["updated_at"] = plan["adopted_at"]
        self._store.save_plan(plan)
        return plan

    # ── 进度 ────────────────────────────────────────────────────────────────

    def record_progress(self, req: PlanProgressRequest) -> PlanProgressEvent:
        if req.event not in RECORDED_EVENTS:
            raise IllegalPlanProgressEventError(
                "progress event must be completed, skipped or overdue"
            )
        self._require_plan(req.plan_id)
        event_id = hashlib.sha256(
            f"{req.plan_id}|{req.task_id}|{req.event}".encode("utf-8")
        ).hexdigest()[:16]
        event = {
            "event_id": event_id,
            "plan_id": req.plan_id,
            "task_id": req.task_id,
            "event": req.event,
            "occurred_at": datetime.now().isoformat(),
        }
        # 幂等：同 task 同 event 重复记录被忽略（INSERT OR IGNORE）
        self._store.save_progress_event(event)
        return PlanProgressEvent(**event)

    # ── 重规划 ──────────────────────────────────────────────────────────────

    def replan(self, plan_id: str, req: PlanReplanRequest | None = None) -> dict[str, Any]:
        """按偏差（跳过 + 逾期任务 ≥ 3）或目标/约束变化确定性重规划。

        `req` 提供显式覆盖；任何与已存计划不同的字段都构成「目标/约束变化」，
        单独即可触发重规划。两个条件都不满足时原样返回当前计划。
        """
        plan = self._require_plan(plan_id)
        events = self._store.list_progress_events(plan_id)
        current = _plan_to_request(plan)
        target = _apply_override(current, req)
        changed = target != current
        deviated = self._deviated_task_ids(plan, events)
        if not changed and len(deviated) < REPLAN_DEVIATION_THRESHOLD:
            # 阈值未到，不重规划，返回当前计划
            return plan

        # 用与首次生成相同的记录形状，避免重规划后的记录丢失 goal / tasks 等字段
        generated = self._planner.generate(target)
        record = _response_to_record(generated)
        previous = _current_revision(plan)
        record["plan_id"] = plan_id
        record["state"] = "replanned"
        record["parent_revision_id"] = previous
        record["revision_id"] = previous + 1
        record["adopted_at"] = plan.get("adopted_at")
        record["created_at"] = plan.get("created_at", "")
        record["updated_at"] = datetime.now().isoformat()
        # 旧 revision 只读保留，新 revision 追加为链尾
        record["revisions"] = list(plan.get("revisions", [])) + record["revisions"]
        record["revisions"][-1]["revision_id"] = previous + 1
        record["progress_events"] = events
        record["replan_reason"] = _replan_reason(changed, len(deviated))
        self._store.save_plan(record)
        return record

    def _deviated_task_ids(
        self, plan: dict[str, Any], events: list[dict[str, Any]]
    ) -> set[str]:
        """偏差任务集合：显式 skipped/overdue 事件 ∪ 当前已逾期的计划任务。

        按 task_id 去重，避免同一任务既被显式记为 overdue 又由复习历史推导出逾期
        而重复计数。
        """
        deviated = {e["task_id"] for e in events if e["event"] in DEVIATION_EVENTS}
        deviated |= self._overdue_task_ids(plan)
        return deviated

    def _overdue_task_ids(self, plan: dict[str, Any]) -> set[str]:
        """计划任务中当前已逾期（days_overdue > 0）的 task_id。

        只读复习排程的逾期投影，不写 mastery、不写会话状态，也不构建 chunk 索引。
        """
        if self._review_scheduler is None:
            return set()
        overdue = self._review_scheduler.overdue_by_file()
        return {t["task_id"] for t in plan.get("tasks", []) if t.get("file") in overdue}

    # ── 内部 ────────────────────────────────────────────────────────────────

    def persist_generated(self, response: GoalPlanResponse) -> None:
        """把首次生成的计划持久化（state=generated），供采纳/进度/重规划使用。

        幂等：plan_id 由 goal + 目标日期 + 课程 + 约束确定性派生，同一请求重复生成会
        命中同一 ID。此时保留已存记录（含采纳状态、进度与 revision 链），不覆盖——
        否则重复提交同一 Goal 会静默重置计划状态，而 progress_events 仍留在表里。
        """
        if self._store.get_plan(response.plan_id) is not None:
            return
        record = _response_to_record(response)
        self._store.save_plan(record)

    def _require_plan(self, plan_id: str) -> dict[str, Any]:
        plan = self._store.get_plan(plan_id)
        if plan is None:
            raise PlanNotFoundError(f"plan {plan_id!r} not found")
        return plan


def _current_revision(plan: dict[str, Any]) -> int:
    """当前修订号；早期记录未持久化 revision_id 时回落到 1。"""
    return int(plan.get("revision_id", 1))


def _replan_reason(changed: bool, deviated_count: int) -> str:
    """记录触发本次重规划的原因，便于审计重规划不是随机发生。"""
    reasons: list[str] = []
    if changed:
        reasons.append("goal_or_constraint_changed")
    if deviated_count >= REPLAN_DEVIATION_THRESHOLD:
        reasons.append(f"deviated_tasks={deviated_count}")
    return "+".join(reasons)


def _apply_override(
    request: GoalPlanRequest, override: PlanReplanRequest | None
) -> GoalPlanRequest:
    """把显式覆盖合并进已存请求；未提供的字段保持原值。

    经 `model_validate` 重新校验，避免嵌套 constraints 以裸 dict 混入模型。
    """
    if override is None:
        return request
    updates = override.model_dump(exclude_none=True)
    if not updates:
        return request
    return GoalPlanRequest.model_validate({**request.model_dump(), **updates})


def _response_to_record(response: GoalPlanResponse) -> dict[str, Any]:
    revision = response.revisions[0] if response.revisions else None
    tasks = []
    if revision is not None:
        for day in revision.days:
            for task in day.tasks:
                tasks.append(
                    {
                        "task_id": task.task_id,
                        "topic": task.topic,
                        "file": task.file,
                        "difficulty": task.difficulty,
                        "estimated_minutes": task.estimated_minutes,
                        "priority": task.priority,
                        "reviewed": task.reviewed,
                    }
                )
    now = datetime.now().isoformat()
    return {
        "plan_id": response.plan_id,
        "schema_version": response.schema_version,
        "state": response.state,
        # 必须持久化：重规划的 parent/next revision 前向链以它为基准
        "revision_id": response.revision_id,
        "goal": revision.goal if revision else "",
        "target_date": response.target_date,
        "total_days": response.total_days,
        "total_hours": response.total_hours,
        # 请求回显，重规划据此保真还原范围
        "course": response.course,
        "hours_per_day": response.hours_per_day,
        "constraints": response.constraints.model_dump(),
        "parent_revision_id": response.parent_revision_id,
        "adopted_at": response.adopted_at,
        "created_at": now,
        "updated_at": now,
        "revisions": [r.model_dump() for r in response.revisions],
        "tasks": tasks,
    }


def _plan_to_request(plan: dict[str, Any]) -> GoalPlanRequest:
    """从已存计划记录还原生成该计划的请求（含课程/学时/约束）。"""
    raw = plan.get("constraints") or {}
    return GoalPlanRequest(
        goal=plan.get("goal") or "",
        course=plan.get("course"),
        target_date=plan.get("target_date") or None,
        hours_per_day=float(plan.get("hours_per_day", 2.0)),
        constraints=GoalPlanConstraints(
            required_topics=list(raw.get("required_topics", [])),
            excluded_topics=list(raw.get("excluded_topics", [])),
        ),
    )
