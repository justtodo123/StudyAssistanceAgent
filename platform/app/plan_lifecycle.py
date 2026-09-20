"""M9 计划生命周期服务：采纳、进度事件与确定性重规划。

Planner 只提建议；采纳是显式用户动作；进度事件驱动重规划；重规划只读权威
复习投影，不写 mastery、不写学习会话状态。
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from .models import (
    GoalPlanResponse,
    PlanProgressEvent,
    PlanProgressRequest,
)


class PlanLifecycleService:
    """采纳 / 进度 / 重规划的编排。"""

    def __init__(self, store, goal_planner) -> None:
        self._store = store
        self._planner = goal_planner

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
        if req.event not in {"completed", "skipped"}:
            raise ValueError("progress event must be completed or skipped")
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

    def replan(self, plan_id: str) -> dict[str, Any]:
        plan = self._require_plan(plan_id)
        events = self._store.list_progress_events(plan_id)
        skipped = [e for e in events if e["event"] == "skipped"]
        if len(skipped) < 3:
            # 阈值未到，不重规划，返回当前计划
            return plan

        req = _plan_to_request(plan)
        new_plan = self._planner.generate(req).model_dump()
        new_plan["plan_id"] = plan_id
        new_plan["state"] = "replanned"
        new_plan["parent_revision_id"] = plan.get("revision_id", 1)
        new_plan["revision_id"] = plan.get("revision_id", 1) + 1
        new_plan["adopted_at"] = plan.get("adopted_at")
        new_plan["created_at"] = plan.get("created_at", "")
        new_plan["updated_at"] = datetime.now().isoformat()
        new_plan["progress_events"] = events
        self._store.save_plan(new_plan)
        return new_plan

    # ── 内部 ────────────────────────────────────────────────────────────────

    def persist_generated(self, response: GoalPlanResponse) -> None:
        """把首次生成的计划持久化（state=generated），供采纳/进度/重规划使用。"""
        record = _response_to_record(response)
        self._store.save_plan(record)

    def _require_plan(self, plan_id: str) -> dict[str, Any]:
        plan = self._store.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"plan {plan_id!r} not found")
        return plan


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
        "goal": revision.goal if revision else "",
        "target_date": response.target_date,
        "total_days": response.total_days,
        "total_hours": response.total_hours,
        "parent_revision_id": response.parent_revision_id,
        "adopted_at": response.adopted_at,
        "created_at": now,
        "updated_at": now,
        "tasks": tasks,
    }


def _plan_to_request(plan: dict[str, Any]) -> Any:
    from .models import GoalPlanRequest

    return GoalPlanRequest(
        goal=plan.get("goal", ""),
        target_date=plan.get("target_date"),
    )
