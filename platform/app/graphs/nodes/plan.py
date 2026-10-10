"""Plan-lifecycle graph nodes — wrap GoalPlannerService, PlanLifecycleService.

The plan graph checks deviation, optionally retrieves grounding chunks,
and triggers replan through the existing deterministic services.
"""

from __future__ import annotations

from typing import Any

from ...goal_planner import GoalPlannerService
from ...models import GoalPlanConstraints, GoalPlanRequest, PlanReplanRequest
from ...plan_lifecycle import (
    REPLAN_DEVIATION_THRESHOLD,
    PlanLifecycleService,
)
from ...retrieval import MultiRecallService, RetrievalScope


def check_deviation_node(
    state: dict[str, Any],
    *,
    plan_lifecycle: PlanLifecycleService,
) -> dict[str, Any]:
    """Check whether the plan has enough deviation to trigger replan.

    Reads ``plan_id`` from state; writes ``deviation_count`` and
    ``deviation_triggered``.
    """
    plan_id = state.get("plan_id", "")
    if not plan_id:
        return {"deviation_count": 0, "deviation_triggered": False}

    try:
        plan = plan_lifecycle.get(plan_id)
    except LookupError:
        return {"deviation_count": 0, "deviation_triggered": False}

    events = plan.get("progress_events") or []
    deviated_ids: set[str] = set()
    for event in events:
        if event.get("event") in {"skipped", "overdue"}:
            deviated_ids.add(event.get("task_id", ""))
    deviated_ids.discard("")

    consumed: set[str] = set()
    for entry in plan.get("deviation_ledger") or []:
        consumed.update(entry.get("consumed_task_ids") or [])
    unconsumed = deviated_ids - consumed

    count = len(unconsumed)
    return {
        "deviation_count": count,
        "deviation_triggered": count >= REPLAN_DEVIATION_THRESHOLD,
    }


def retrieve_grounding_node(
    state: dict[str, Any],
    *,
    recall: MultiRecallService,
) -> dict[str, Any]:
    """Retrieve knowledge chunks to ground the replan."""
    goal = state.get("goal") or ""
    course = state.get("course")
    if not goal:
        return {"grounding_chunks": []}

    chunks, _mode = recall.recall(
        goal,
        top_k=5,
        course=course,
        scope=RetrievalScope.DEFAULT_ONLY,
    )
    return {"grounding_chunks": [chunk.model_dump() for chunk in chunks]}


def generate_plan_node(
    state: dict[str, Any],
    *,
    plan_lifecycle: PlanLifecycleService,
) -> dict[str, Any]:
    """Run replan through the lifecycle service and store the result."""
    plan_id = state.get("plan_id", "")
    if not plan_id:
        return {"generated_plan": None}

    replan_req = PlanReplanRequest(
        goal=state.get("goal"),
        course=state.get("course"),
        target_date=state.get("target_date"),
        hours_per_day=state.get("hours_per_day"),
        constraints=(
            GoalPlanConstraints(**state["constraints"])
            if state.get("constraints")
            else None
        ),
    )

    try:
        result = plan_lifecycle.replan(plan_id, replan_req)
    except LookupError:
        return {"generated_plan": None}

    return {"generated_plan": result}
