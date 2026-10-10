"""Top-level multi-agent assistance graph — routes by intent.

Graph structure::

    START → router
      → (study) → study_retrieve → END
      → (plan)  → plan_retrieve  → END
      → (general) → general_retrieve → END

When ``GraphLLM`` is available the router asks the model to classify
``question`` into *study / plan / general*; on any failure it falls back
to the deterministic intent supplied by the API request.
"""

from __future__ import annotations

from functools import partial
from typing import Any

from ..retrieval import RetrievalScope

from .dependencies import GraphContainer
from .llm import GraphLLM
from .nodes.retrieval import retrieve_node
from .state import AssistanceState

_INTENT_PROMPT = (
    "Classify the following student question into exactly one category. "
    "Reply with ONLY one word: study, plan, or general.\n\n"
    "- study: questions about a specific CS topic concept (e.g. OS scheduling, "
    "sorting algorithms, TCP handshake)\n"
    "- plan: questions about study planning, time management, exam preparation "
    "strategy\n"
    "- general: anything else\n\n"
    "Question: {question}\n"
    "Category:"
)

_VALID_INTENTS = {"study", "plan", "general"}


def _classify_intent(llm: GraphLLM, question: str) -> str | None:
    prompt = _INTENT_PROMPT.format(question=question[:500])
    response = llm.complete(prompt)
    if response is None:
        return None
    cleaned = response.strip().lower().rstrip(".")
    for intent in _VALID_INTENTS:
        if intent in cleaned:
            return intent
    return None


def router_node(
    state: AssistanceState,
    *,
    llm: GraphLLM | None = None,
) -> dict[str, Any]:
    """Classify intent — LLM when available, else pass-through from API."""
    api_intent = state.get("intent", "general")
    if api_intent not in _VALID_INTENTS:
        api_intent = "general"

    question = state.get("question", "").strip()
    if llm is not None and question and api_intent == "general":
        classified = _classify_intent(llm, question)
        if classified is not None:
            return {"intent": classified}

    return {"intent": api_intent}


def _route_by_intent(state: AssistanceState) -> str:
    return state.get("intent", "general")


def build_assistance_graph(container: GraphContainer) -> Any:
    """Compile and return the top-level assistance router graph."""
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(AssistanceState)

    router = partial(router_node, llm=container.llm)
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

    graph.add_node("router", router)
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
