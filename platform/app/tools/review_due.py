"""Read-only review-due tool adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..protocols import SideEffect, ToolCapability, ToolContext, ToolResult, ToolSpec
from ..review_scheduler import ReviewSchedulerService
from .common import authorize, error_result, result_with_data, validate_arguments


_SCHEMA = {
    "type": "object",
    "properties": {"course": {"type": "string", "minLength": 1}},
    "required": [],
    "additionalProperties": False,
}


class ReviewDueTool:
    """Read due reviews without mutating review history."""

    spec = ToolSpec(
        name="review_due",
        description="List due review entries.",
        input_schema=_SCHEMA,
        capability=ToolCapability.READ,
        side_effect=SideEffect.NONE,
        idempotent=True,
    )

    def __init__(self, scheduler: ReviewSchedulerService | None = None) -> None:
        self._scheduler = scheduler or ReviewSchedulerService()

    def execute(self, context: ToolContext, arguments: Mapping[str, Any]) -> ToolResult:
        failure = authorize(context, self.spec)
        if failure:
            return failure
        validation = validate_arguments(arguments, self.spec.input_schema)
        if validation:
            return ToolResult(error=validation, correlation_id=context.correlation_id)
        try:
            response = self._scheduler.get_due(arguments.get("course"))
        except Exception:
            return error_result(context, "TOOL_EXECUTION_FAILED", "review lookup failed", retryable=True)
        return result_with_data(context, response.model_dump(mode="json"))


__all__ = ["ReviewDueTool"]
