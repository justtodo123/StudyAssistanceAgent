"""Plan-lifecycle LangGraph — formalises the deviation → replan flow.

Graph structure::

    START → check_deviation
      → (deviation_triggered) → retrieve_grounding → generate_plan → END
      → (not triggered) → END

The *check_deviation* node reads the plan's progress events and counts
unconsumed deviations.  If the threshold is met the graph retrieves
grounding chunks and calls ``PlanLifecycleService.replan``.
"""

from __future__ import annotations

from functools import partial
from typing import Any

from .dependencies import GraphContainer
from .nodes.plan import (
    check_deviation_node,
    generate_plan_node,
    retrieve_grounding_node,
)
from .state import PlanState


def _route_after_check(state: PlanState) -> str:
    if state.get("deviation_triggered"):
        return "replan"
    return "skip"


def build_plan_graph(container: GraphContainer) -> Any:
    """Compile and return the plan-lifecycle graph."""
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(PlanState)

    check_fn = partial(
        check_deviation_node,
        plan_lifecycle=container.plan_lifecycle,
    )
    grounding_fn = partial(
        retrieve_grounding_node,
        recall=container.recall,
    )
    generate_fn = partial(
        generate_plan_node,
        plan_lifecycle=container.plan_lifecycle,
    )

    graph.add_node("check_deviation", check_fn)
    graph.add_node("retrieve_grounding", grounding_fn)
    graph.add_node("generate_plan", generate_fn)

    graph.add_edge(START, "check_deviation")

    graph.add_conditional_edges(
        "check_deviation",
        _route_after_check,
        {
            "replan": "retrieve_grounding",
            "skip": END,
        },
    )

    graph.add_edge("retrieve_grounding", "generate_plan")
    graph.add_edge("generate_plan", END)

    return graph.compile()
