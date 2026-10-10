"""LangGraph Multi-Agent orchestration (optional dependency).

All imports from this package are lazy: if *langgraph* is not installed the
flag :data:`LANGGRAPH_AVAILABLE` is ``False`` and the graph builders are
``None``.  The FastAPI application checks the flag before registering v2
endpoints so the default startup path is unaffected.
"""

from __future__ import annotations

try:
    import langgraph  # noqa: F401
    from langgraph.graph import StateGraph

    LANGGRAPH_AVAILABLE = True
    _LANGGRAPH_IMPORT_ERROR: str | None = None
except Exception as exc:  # pragma: no cover - exercised only without langgraph
    LANGGRAPH_AVAILABLE = False
    StateGraph = None  # type: ignore[assignment,misc]
    _LANGGRAPH_IMPORT_ERROR = str(exc)
