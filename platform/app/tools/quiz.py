"""Deterministic quiz preview tool adapter."""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Mapping
from typing import Any

from ..models import QuizRequest
from ..protocols import SideEffect, ToolCapability, ToolContext, ToolResult, ToolSpec
from ..quiz import QuizService
from .common import authorize, error_result, result_with_data, validate_arguments


_SCHEMA = {
    "type": "object",
    "properties": {
        "course": {"type": "string", "minLength": 1},
        "count": {"type": "integer", "minimum": 1, "maximum": 20},
        "difficulty": {"type": "string", "minLength": 1},
        "topics": {"type": "array"},
    },
    "required": ["course"],
    "additionalProperties": False,
}


class QuizTool:
    """Generate a repeatable, read-only quiz preview."""

    spec = ToolSpec(
        name="quiz_preview",
        description="Generate a deterministic quiz preview from the default pack.",
        input_schema=_SCHEMA,
        capability=ToolCapability.READ,
        side_effect=SideEffect.NONE,
        idempotent=True,
    )

    def __init__(self, quiz: QuizService | None = None) -> None:
        self._quiz = quiz or QuizService()

    def execute(self, context: ToolContext, arguments: Mapping[str, Any]) -> ToolResult:
        failure = authorize(context, self.spec)
        if failure:
            return failure
        validation = validate_arguments(arguments, self.spec.input_schema)
        if validation:
            return ToolResult(error=validation, correlation_id=context.correlation_id)
        try:
            normalized = json.dumps(dict(arguments), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            seed = hashlib.sha256(normalized.encode("utf-8")).digest()
            response = self._quiz.generate(QuizRequest(**dict(arguments)), rng=random.Random(seed))
        except Exception:
            return error_result(context, "TOOL_EXECUTION_FAILED", "quiz generation failed", retryable=True)
        # generated_at is deliberately excluded: it is not part of deterministic tool data.
        data = response.model_dump(mode="json", exclude={"generated_at"})
        return result_with_data(context, data)


__all__ = ["QuizTool"]
