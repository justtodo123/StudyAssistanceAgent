"""LangGraph-specific limits and validation.

Mirrors the pattern used by :class:`app.preview_agent.PreviewLimits` and
:class:`app.plan_ai_adapter.PlanAILimits` — frozen defaults that can only
be tightened via environment variables, never relaxed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LangGraphLimits:
    """Resource budgets for LangGraph graph execution."""

    max_nodes_per_graph: int = 50
    max_graph_invocations_per_request: int = 10
    node_timeout_seconds: float = 30.0
    max_retrieval_top_k: int = 20
    max_remediation_attempts: int = 2


_DEFAULTS = LangGraphLimits()


def validate_limits(limits: LangGraphLimits) -> None:
    """Ensure limits do not exceed the frozen defaults."""
    if limits.max_nodes_per_graph > _DEFAULTS.max_nodes_per_graph:
        raise ValueError(
            f"max_nodes_per_graph ({limits.max_nodes_per_graph}) "
            f"exceeds frozen limit ({_DEFAULTS.max_nodes_per_graph})"
        )
    if limits.max_graph_invocations_per_request > _DEFAULTS.max_graph_invocations_per_request:
        raise ValueError(
            f"max_graph_invocations_per_request "
            f"({limits.max_graph_invocations_per_request}) "
            f"exceeds frozen limit ({_DEFAULTS.max_graph_invocations_per_request})"
        )
    if limits.node_timeout_seconds > _DEFAULTS.node_timeout_seconds:
        raise ValueError(
            f"node_timeout_seconds ({limits.node_timeout_seconds}) "
            f"exceeds frozen limit ({_DEFAULTS.node_timeout_seconds})"
        )
    if limits.max_retrieval_top_k > _DEFAULTS.max_retrieval_top_k:
        raise ValueError(
            f"max_retrieval_top_k ({limits.max_retrieval_top_k}) "
            f"exceeds frozen limit ({_DEFAULTS.max_retrieval_top_k})"
        )
    if limits.max_remediation_attempts > _DEFAULTS.max_remediation_attempts:
        raise ValueError(
            f"max_remediation_attempts ({limits.max_remediation_attempts}) "
            f"exceeds frozen limit ({_DEFAULTS.max_remediation_attempts})"
        )
