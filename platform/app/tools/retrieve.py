"""Deterministic retrieval tool adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..protocols import SideEffect, ToolCapability, ToolContext, ToolResult, ToolSpec
from ..retrieval import MultiRecallService, RetrievalScope
from .common import authorize, error_result, result_with_data, source_identity, validate_arguments


_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "minLength": 1},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
        "threshold": {"type": "number", "minimum": 0, "maximum": 1},
        "course": {"type": "string", "minLength": 1},
    },
    "required": ["question"],
    "additionalProperties": False,
}


class RetrieveTool:
    """Expose MultiRecallService without calling an HTTP handler or an LLM."""

    spec = ToolSpec(
        name="retrieve",
        description="Retrieve relevant knowledge chunks.",
        input_schema=_SCHEMA,
        capability=ToolCapability.READ,
        side_effect=SideEffect.NONE,
        idempotent=True,
    )

    def __init__(self, recall: MultiRecallService | None = None) -> None:
        self._recall = recall or MultiRecallService()

    def execute(self, context: ToolContext, arguments: Mapping[str, Any]) -> ToolResult:
        failure = authorize(context, self.spec)
        if failure:
            return failure
        validation = validate_arguments(arguments, self.spec.input_schema)
        if validation:
            return ToolResult(error=validation, correlation_id=context.correlation_id)
        try:
            results, mode = self._recall.recall(
                arguments["question"],
                arguments.get("top_k", 5),
                arguments.get("threshold"),
                arguments.get("course"),
                RetrievalScope(context.source_scope),
            )
        except Exception:
            return error_result(context, "TOOL_EXECUTION_FAILED", "retrieval failed", retryable=True)
        try:
            data = {"results": [chunk.model_dump(mode="json") for chunk in results], "mode": mode}
            sources = tuple(source_identity(chunk.file) for chunk in results)
        except Exception:
            return error_result(context, "TOOL_RESULT_INVALID", "retrieval result is invalid")
        return result_with_data(context, data, sources=sources)


__all__ = ["RetrieveTool"]
