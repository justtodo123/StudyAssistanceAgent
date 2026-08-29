"""M6b tests for the explicit read-only preview tool registry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from app.models import RetrievalChunk, ReviewDueResponse
from app.protocols import (
    SideEffect,
    ToolCapability,
    ToolContext,
    ToolResult,
    ToolSpec,
)
from app.tool_registry import ToolRegistry, ToolRegistryError
from app.tools import RetrieveTool, ReviewDueTool


pytestmark = pytest.mark.m6b


class _Recall:
    def recall(self, *args: Any) -> tuple[list[RetrievalChunk], str]:
        del args
        return [
            RetrievalChunk(
                id="internal-id",
                file="extra://notes-1/week-01.md",
                title="Week 1",
                course="os",
                tags=["process"],
                difficulty="medium",
                updated="2026-08-28",
                content="model-visible content",
                score=0.75,
            )
        ], "keyword"


class _Review:
    def get_due(self, course: str | None = None) -> ReviewDueResponse:
        return ReviewDueResponse(
            course=course,
            checked_at="private-clock-value",
            total_due=0,
            entries=[],
            summary={"internal": "not-visible"},
        )


class _Tool:
    def __init__(self, spec: ToolSpec, result: ToolResult | None = None) -> None:
        self.spec = spec
        self.result = result or ToolResult(data={})
        self.calls = 0

    def execute(
        self,
        context: ToolContext,
        arguments: Mapping[str, Any],
    ) -> ToolResult:
        del arguments
        self.calls += 1
        return ToolResult(
            data=self.result.data,
            sources=self.result.sources,
            error=self.result.error,
            side_effect=self.result.side_effect,
            correlation_id=context.correlation_id,
        )


def _context() -> ToolContext:
    return ToolContext(
        learner_id="learner",
        source_scope="DEFAULT_PLUS_EXTRAS",
        correlation_id="request-1",
        permissions=frozenset({"read"}),
    )


def test_schemas_are_strict_deterministic_and_detached() -> None:
    registry = ToolRegistry()
    registry.register(ReviewDueTool(_Review()))
    registry.register(RetrieveTool(_Recall()))

    first = registry.schemas()
    first[0]["input_schema"]["properties"]["injected"] = {"type": "string"}
    second = registry.schemas()

    assert [item["name"] for item in second] == ["retrieve", "review_due"]
    assert all(item["type"] == "custom" and item["strict"] is True for item in second)
    assert "injected" not in second[0]["input_schema"]["properties"]


def test_duplicate_and_non_read_only_registrations_are_rejected() -> None:
    registry = ToolRegistry()
    registry.register(RetrieveTool(_Recall()))
    with pytest.raises(ToolRegistryError, match="duplicate"):
        registry.register(RetrieveTool(_Recall()))

    write_tool = _Tool(
        ToolSpec(
            name="review_log",
            description="write",
            input_schema={"type": "object"},
            capability=ToolCapability.WRITE,
            side_effect=SideEffect.DOMAIN_WRITE,
        )
    )
    with pytest.raises(ToolRegistryError, match="allowlist"):
        ToolRegistry().register(write_tool, lambda result: result.data)


def test_registry_revalidates_arguments_before_tool_execution() -> None:
    tool = _Tool(
        ToolSpec(
            name="retrieve",
            description="retrieve",
            input_schema={
                "type": "object",
                "properties": {"question": {"type": "string", "minLength": 1}},
                "required": ["question"],
                "additionalProperties": False,
            },
        )
    )
    registry = ToolRegistry()
    registry.register(tool, lambda result: result.data)

    result = registry.execute("retrieve", _context(), {})

    assert result.error is not None
    assert result.error.code == "TOOL_ARGUMENTS_INVALID"
    assert tool.calls == 0


def test_retrieve_projection_exposes_only_allowlisted_fields_and_logical_source() -> None:
    registry = ToolRegistry()
    registry.register(RetrieveTool(_Recall()))

    result = registry.execute("retrieve", _context(), {"question": "process"})

    assert result.ok
    assert result.data == {
        "mode": "keyword",
        "results": [
            {
                "title": "Week 1",
                "course": "os",
                "tags": ["process"],
                "difficulty": "medium",
                "updated": "2026-08-28",
                "content": "model-visible content",
                "score": 0.75,
                "source": {
                    "source_id": "notes-1",
                    "logical_uri": "week-01.md",
                    "document_id": result.sources[0].document_id,
                },
            }
        ],
    }
    encoded = repr(result.data)
    assert "internal-id" not in encoded
    assert "extra://" not in encoded


def test_review_projection_excludes_clock_and_summary_metadata() -> None:
    registry = ToolRegistry()
    registry.register(ReviewDueTool(_Review()))

    result = registry.execute("review_due", _context(), {"course": "os"})

    assert result.ok
    assert result.data == {"course": "os", "total_due": 0, "entries": []}
    assert "private-clock-value" not in repr(result.data)
    assert "internal" not in repr(result.data)


def test_unknown_tool_has_stable_safe_error() -> None:
    result = ToolRegistry().execute(
        r"C:\private\tool",
        _context(),
        {"secret": "canary"},
    )

    assert result.error is not None
    assert result.error.code == "TOOL_UNKNOWN"
    assert "private" not in result.error.message
    assert "canary" not in result.error.message
