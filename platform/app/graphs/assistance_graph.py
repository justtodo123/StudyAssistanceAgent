"""Top-level multi-agent assistance graph — routes by intent.

Graph structure::

    START → router
      → (study) → study_retrieve → END
      → (plan)  → plan_retrieve  → END
      → (general) → general_retrieve → END

The router is deterministic — the intent comes from the API endpoint,
not from an LLM classifier.  Each branch calls the shared retrieval
node with different parameters, demonstrating the multi-agent
shared-state pattern without rewriting existing services.
"""

from __future__ import annotations

from functools import partial
from typing import Any

from ..retrieval import RetrievalScope

from .dependencies import GraphContainer
from .nodes.retrieval import retrieve_node
from .state import AssistanceState


def router_node(state: AssistanceState) -> dict[str, Any]:
    """Validate the intent and pass through — routing is done by conditional edges."""
    intent = state.get("intent", "general")
    if intent not in {"study", "plan", "general"}:
        intent = "general"
    return {"intent": intent}


def _route_by_intent(state: AssistanceState) -> str:
    return state.get("intent", "general")


def build_assistance_graph(container: GraphContainer) -> Any:
    """Compile and return the top-level assistance router graph."""
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(AssistanceState)

    study_retrieve = partial(
        retrieve_node,
        recall=container.recall,
        scope=RetrievalScope.DEFAULT_ONLY,
        top_k=5,
    )
    plan_retrieve = partial(
        retrieve_node,
        recall=container.recall,
        scope=RetrievalScope.DEFAULT_ONLY,
        top_k=5,
    )
    general_retrieve = partial(
        retrieve_node,
        recall=container.recall,
        scope=RetrievalScope.DEFAULT_PLUS_EXTRAS,
        top_k=5,
    )

    graph.add_node("router", router_node)
    graph.add_node("study_retrieve", study_retrieve)
    graph.add_node("plan_retrieve", plan_retrieve)
    graph.add_node("general_retrieve", general_retrieve)

    graph.add_edge(START, "router")

    graph.add_conditional_edges(
        "router",
        _route_by_intent,
        {
            "study": "study_retrieve",
            "plan": "plan_retrieve",
            "general": "general_retrieve",
        },
    )

    graph.add_edge("study_retrieve", END)
    graph.add_edge("plan_retrieve", END)
    graph.add_edge("general_retrieve", END)

    return graph.compile()
