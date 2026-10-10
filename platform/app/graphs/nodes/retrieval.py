"""Shared retrieval node — wraps :class:`MultiRecallService`.

Used by both the study graph (to fetch explanation sources) and the plan
graph (to ground replan with knowledge chunks).  The Retrieval Agent in
the multi-agent topology is this single node; Tutor and Planner both
route through it so knowledge access is centralised.
"""

from __future__ import annotations

from typing import Any

from ...retrieval import MultiRecallService, RetrievalScope


def retrieve_node(
    state: dict[str, Any],
    *,
    recall: MultiRecallService,
    scope: RetrievalScope = RetrievalScope.DEFAULT_ONLY,
    top_k: int = 5,
) -> dict[str, Any]:
    """Run multi-recall retrieval and store results in state.

    Reads ``question`` (or ``topic``) and ``course`` from *state*; writes
    ``retrieval_results`` and ``retrieval_mode``.
    """
    query = state.get("question") or state.get("topic") or ""
    course = state.get("course")
    if not query:
        return {"retrieval_results": [], "retrieval_mode": "no_query"}

    chunks, mode = recall.recall(
        query,
        top_k=min(top_k, 20),
        course=course,
        scope=scope,
    )
    return {
        "retrieval_results": [chunk.model_dump() for chunk in chunks],
        "retrieval_mode": mode,
    }
