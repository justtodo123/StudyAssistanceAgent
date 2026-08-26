"""Shared helpers for deterministic, provider-neutral tools."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ..protocols import SourceIdentity, Tool, ToolContext, ToolError, ToolResult, ToolSpec


def error_result(context: ToolContext, code: str, message: str, *, retryable: bool = False) -> ToolResult:
    """Build a safe structured failure without exposing implementation details."""
    return ToolResult(
        error=ToolError(code=code, message=message, retryable=retryable),
        correlation_id=context.correlation_id,
    )


def authorize(context: ToolContext, spec: ToolSpec) -> ToolResult | None:
    """Return a failure when the invocation is not authorized or is cancelled."""
    if context.cancelled:
        return error_result(context, "TOOL_CANCELLED", "tool invocation was cancelled")
    if not context.correlation_id:
        return error_result(context, "TOOL_CONTEXT_INVALID", "correlation id is required")
    if not context.source_scope:
        return error_result(context, "TOOL_CONTEXT_INVALID", "source scope is required")
    if context.source_scope not in {"DEFAULT_ONLY", "DEFAULT_PLUS_EXTRAS"}:
        return error_result(context, "TOOL_SCOPE_INVALID", "source scope is invalid")
    if not context.allows(spec):
        return error_result(context, "TOOL_NOT_AUTHORIZED", "tool capability is not authorized")
    return None


def validate_arguments(arguments: Mapping[str, Any], schema: Mapping[str, Any]) -> ToolError | None:
    """Validate the small strict schemas used by M6a tools."""
    if not isinstance(arguments, Mapping):
        return ToolError("TOOL_ARGUMENTS_INVALID", "arguments must be an object")
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if set(arguments) - set(properties):
        return ToolError("TOOL_ARGUMENTS_INVALID", "arguments contain unsupported fields")
    missing = [key for key in required if key not in arguments]
    if missing:
        return ToolError("TOOL_ARGUMENTS_INVALID", "required arguments are missing")
    for key, value in arguments.items():
        rule = properties[key]
        kind = rule.get("type")
        valid = {
            "string": isinstance(value, str),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
            "array": isinstance(value, list),
        }.get(kind, True)
        if not valid:
            return ToolError("TOOL_ARGUMENTS_INVALID", "argument type is invalid")
        if isinstance(value, str) and "minLength" in rule and len(value) < rule["minLength"]:
            return ToolError("TOOL_ARGUMENTS_INVALID", "argument value is invalid")
        if isinstance(value, (int, float)) and "minimum" in rule and value < rule["minimum"]:
            return ToolError("TOOL_ARGUMENTS_INVALID", "argument value is invalid")
        if isinstance(value, (int, float)) and "maximum" in rule and value > rule["maximum"]:
            return ToolError("TOOL_ARGUMENTS_INVALID", "argument value is invalid")
    return None


def result_with_data(context: ToolContext, data: Any, *, sources: tuple[SourceIdentity, ...] = ()) -> ToolResult:
    """Return JSON-safe tool data and preserve the request correlation id."""
    try:
        json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return error_result(context, "TOOL_RESULT_INVALID", "tool result is not JSON-safe")
    return ToolResult(data=data, sources=sources, correlation_id=context.correlation_id)


def source_identity(file: str) -> SourceIdentity:
    """Convert a public provenance path to a logical source identity."""
    if file.startswith("extra://"):
        source_id, separator, logical_uri = file.removeprefix("extra://").partition("/")
        if not separator:
            raise ValueError("invalid extra-source provenance")
        return SourceIdentity(source_id, logical_uri)
    prefix = "knowledge/"
    return SourceIdentity("knowledge-pack", file[len(prefix):] if file.startswith(prefix) else file)


__all__ = ["Tool", "authorize", "error_result", "result_with_data", "source_identity", "validate_arguments"]
