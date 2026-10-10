"""Study-session LangGraph — replaces the imperative FSM in study_session.py.

The graph is invoked in two phases that mirror the v1 API:

* **create** — ``START → initialize → END``.  The *initialize* node calls
  ``QaService`` for an explanation and ``QuizService`` for questions, then
  writes the session state (``awaiting_answer`` or ``completed``).
* **submit** — ``START → evaluate → conditional → advance → END``.  The
  *evaluate* node grades the answer; conditional edges route to *advance*
  (correct or max attempts) or back to ``awaiting_answer`` (retry).

Nodes wrap the same deterministic services as v1 — the graph only
formalises the routing.
"""

from __future__ import annotations

from functools import partial
from typing import Any

from ..study_session import STATE_AWAITING_ANSWER, STATE_COMPLETED

from .dependencies import GraphContainer
from .nodes.study import advance_node, evaluate_node, initialize_node
from .state import StudyState


def _route_after_evaluate(state: StudyState) -> str:
    """Decide where to go after evaluation.

    * correct → advance (move to next question or complete)
    * wrong + attempts < MAX_ATTEMPTS → awaiting_answer (retry, no advance)
    * wrong + attempts >= MAX_ATTEMPTS → advance (show full explanation, move on)
    """
    questions = state.get("questions") or []
    current_index = state.get("current_index", 0)
    last_eval = state.get("last_evaluation") or {}

    if last_eval.get("correct"):
        return "advance"

    if current_index < len(questions):
        q = questions[current_index]
        if q.get("attempt_count", 0) < 2:
            return "retry"

    return "advance"


def _route_after_initialize(state: StudyState) -> str:
    """After initialization, go to awaiting_answer or directly to completed."""
    if state.get("state") == STATE_COMPLETED:
        return "complete"
    return "awaiting"


def build_study_graph(container: GraphContainer) -> Any:
    """Compile and return the study-session graph.

    The returned object is a compiled LangGraph ``StateGraph`` that can be
    invoked with ``.invoke(state)``.
    """
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(StudyState)

    init_fn = partial(
        initialize_node,
        qa_service=container.qa_service,
        quiz_service=container.quiz_service,
    )
    advance_fn = partial(
        advance_node,
        review_scheduler=container.review_scheduler,
    )

    graph.add_node("initialize", init_fn)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("advance", advance_fn)

    graph.add_edge(START, "initialize")

    graph.add_conditional_edges(
        "initialize",
        _route_after_initialize,
        {
            "awaiting": END,
            "complete": END,
        },
    )

    graph.add_conditional_edges(
        "evaluate",
        _route_after_evaluate,
        {
            "advance": "advance",
            "retry": END,
        },
    )

    graph.add_edge("advance", END)

    return graph.compile()


def build_submit_graph(container: GraphContainer) -> Any:
    """Compile the submit-answer sub-graph (evaluate → conditional → advance)."""
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(StudyState)

    advance_fn = partial(
        advance_node,
        review_scheduler=container.review_scheduler,
    )

    graph.add_node("evaluate", evaluate_node)
    graph.add_node("advance", advance_fn)

    graph.add_edge(START, "evaluate")

    graph.add_conditional_edges(
        "evaluate",
        _route_after_evaluate,
        {
            "advance": "advance",
            "retry": END,
        },
    )

    graph.add_edge("advance", END)

    return graph.compile()
