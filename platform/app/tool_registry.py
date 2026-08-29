"""Read-only tool registry for the isolated M6b preview."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .protocols import (
    SideEffect,
    SourceIdentity,
    Tool,
    ToolCapability,
    ToolContext,
    ToolResult,
)
from .tools.common import authorize, error_result, source_identity, validate_arguments

PREVIEW_TOOL_ALLOWLIST = frozenset({"quiz_preview", "retrieve", "review_due"})


class ToolRegistryError(ValueError):
    """Raised when a tool cannot safely enter the preview registry."""


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    """A tool paired with its explicit model-visible result projector."""

    tool: Tool
    project: Callable[[ToolResult], Any]


def _source_payload(source: SourceIdentity) -> dict[str, str]:
    return {
        "source_id": source.source_id,
        "logical_uri": source.logical_uri,
        "document_id": source.document_id,
    }


def _require_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("tool result must be an object")
    return value


def _project_retrieve(result: ToolResult) -> dict[str, Any]:
    data = _require_mapping(result.data)
    rows = data.get("results")
    if not isinstance(rows, list) or len(rows) != len(result.sources):
        raise ValueError("retrieval result shape is invalid")

    projected: list[dict[str, Any]] = []
    for row, source in zip(rows, result.sources, strict=True):
        item = _require_mapping(row)
        projected.append(
            {
                "title": str(item.get("title", "")),
                "course": str(item.get("course", "")),
                "tags": [str(tag) for tag in item.get("tags", []) if isinstance(tag, str)],
                "difficulty": str(item.get("difficulty", "")),
                "updated": str(item.get("updated", "")),
                "content": str(item.get("content", "")),
                "score": float(item.get("score", 0.0)),
                "source": _source_payload(source),
            }
        )
    return {"mode": str(data.get("mode", "")), "results": projected}


def _project_quiz(result: ToolResult) -> dict[str, Any]:
    data = _require_mapping(result.data)
    rows = data.get("questions")
    if not isinstance(rows, list):
        raise ValueError("quiz result shape is invalid")

    questions: list[dict[str, Any]] = []
    for row in rows:
        item = _require_mapping(row)
        projected: dict[str, Any] = {
            "question": str(item.get("question", "")),
            "type": str(item.get("type", "")),
            "answer": str(item.get("answer", "")),
            "tags": [str(tag) for tag in item.get("tags", []) if isinstance(tag, str)],
            "difficulty": str(item.get("difficulty", "")),
        }
        raw_file = item.get("source_file")
        if raw_file:
            projected["source"] = _source_payload(source_identity(str(raw_file)))
        questions.append(projected)
    return {
        "quiz_name": str(data.get("quiz_name", "")),
        "course": str(data.get("course", "")),
        "count": int(data.get("count", len(questions))),
        "questions": questions,
    }


def _project_review_due(result: ToolResult) -> dict[str, Any]:
    data = _require_mapping(result.data)
    rows = data.get("entries")
    if not isinstance(rows, list):
        raise ValueError("review result shape is invalid")

    entries: list[dict[str, Any]] = []
    for row in rows:
        item = _require_mapping(row)
        source = source_identity(str(item.get("file", "")))
        entries.append(
            {
                "title": str(item.get("title", "")),
                "course": str(item.get("course", "")),
                "last_reviewed": str(item.get("last_reviewed", "")),
                "review_count": int(item.get("review_count", 0)),
                "next_review": str(item.get("next_review", "")),
                "days_overdue": int(item.get("days_overdue", 0)),
                "interval_days": int(item.get("interval_days", 0)),
                "source": _source_payload(source),
            }
        )
    course = data.get("course")
    return {
        "course": str(course) if course is not None else None,
        "total_due": int(data.get("total_due", len(entries))),
        "entries": entries,
    }


DEFAULT_PROJECTORS: Mapping[str, Callable[[ToolResult], Any]] = MappingProxyType(
    {
        "quiz_preview": _project_quiz,
        "retrieve": _project_retrieve,
        "review_due": _project_review_due,
    }
)


class ToolRegistry:
    """Register and execute only explicitly approved, side-effect-free tools."""

    def __init__(self, registrations: Iterable[RegisteredTool] = ()) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        for registration in registrations:
            self.register(registration.tool, registration.project)

    def register(self, tool: Tool, project: Callable[[ToolResult], Any] | None = None) -> None:
        spec = tool.spec
        self._validate_spec(spec.name, spec.capability, spec.side_effect, spec.idempotent)
        if spec.name in self._tools:
            raise ToolRegistryError(f"duplicate preview tool: {spec.name}")
        projector = project or DEFAULT_PROJECTORS.get(spec.name)
        if projector is None:
            raise ToolRegistryError(f"preview tool has no result projector: {spec.name}")
        self._tools[spec.name] = RegisteredTool(tool=tool, project=projector)

    def get(self, name: str) -> Tool | None:
        registration = self._tools.get(name)
        return registration.tool if registration else None

    def schemas(self) -> tuple[dict[str, Any], ...]:
        """Return deterministic Anthropic custom-tool definitions."""
        definitions: list[dict[str, Any]] = []
        for name in sorted(self._tools):
            spec = self._tools[name].tool.spec
            schema = json.loads(
                json.dumps(spec.input_schema, ensure_ascii=False, sort_keys=True)
            )
            definitions.append(
                {
                    "type": "custom",
                    "name": spec.name,
                    "description": spec.description,
                    "strict": True,
                    "input_schema": schema,
                }
            )
        return tuple(definitions)

    def execute(
        self,
        name: str,
        context: ToolContext,
        arguments: Mapping[str, Any],
    ) -> ToolResult:
        registration = self._tools.get(name)
        if registration is None:
            return error_result(context, "TOOL_UNKNOWN", "tool is not available")

        spec = registration.tool.spec
        try:
            self._validate_spec(spec.name, spec.capability, spec.side_effect, spec.idempotent)
        except ToolRegistryError:
            return error_result(context, "TOOL_NOT_AUTHORIZED", "tool is not authorized")
        failure = authorize(context, spec)
        if failure:
            return failure
        validation = validate_arguments(arguments, spec.input_schema)
        if validation:
            return ToolResult(error=validation, correlation_id=context.correlation_id)

        try:
            result = registration.tool.execute(context, arguments)
        except Exception:
            return error_result(context, "TOOL_INTERNAL", "tool failed")
        if result.side_effect is not SideEffect.NONE:
            return error_result(context, "TOOL_NOT_AUTHORIZED", "tool returned a side effect")
        if not result.ok:
            return ToolResult(error=result.error, correlation_id=context.correlation_id)
        try:
            data = registration.project(result)
            json.dumps(data, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            return error_result(context, "TOOL_RESULT_INVALID", "tool result is invalid")
        return ToolResult(
            data=data,
            sources=result.sources,
            correlation_id=context.correlation_id,
        )

    @staticmethod
    def _validate_spec(
        name: str,
        capability: ToolCapability,
        side_effect: SideEffect,
        idempotent: bool,
    ) -> None:
        if name not in PREVIEW_TOOL_ALLOWLIST:
            raise ToolRegistryError(f"tool is not in the preview allowlist: {name}")
        if capability is not ToolCapability.READ:
            raise ToolRegistryError(f"preview tool is not read-only: {name}")
        if side_effect is not SideEffect.NONE:
            raise ToolRegistryError(f"preview tool declares a side effect: {name}")
        if not idempotent:
            raise ToolRegistryError(f"preview tool is not idempotent: {name}")


__all__ = [
    "DEFAULT_PROJECTORS",
    "PREVIEW_TOOL_ALLOWLIST",
    "RegisteredTool",
    "ToolRegistry",
    "ToolRegistryError",
]
