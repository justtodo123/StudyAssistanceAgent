"""Minimal authenticated, read-only JSON-RPC server over stdio for M10.

This module has no listener and is not imported by the FastAPI application.  A
caller must explicitly construct it with an existing read-only ``ToolRegistry``.
"""

from __future__ import annotations

import hmac
import json
import os
import threading
import time
from dataclasses import dataclass
from io import TextIOBase
from typing import Any, Mapping

from .errors import ErrorCode
from .protocols import SideEffect, ToolCapability, ToolContext
from .source_manifest import canonical_json
from .tool_registry import PREVIEW_TOOL_ALLOWLIST, ToolRegistry

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "study-assistance-agent"
SERVER_VERSION = "m10-v1"

_PERMISSION_ERROR = -32001
_BUDGET_ERROR = -32002
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
_INTERNAL_ERROR = -32603
_PARSE_ERROR = -32700


@dataclass(frozen=True, slots=True)
class McpLimits:
    max_request_bytes: int = 64 * 1024
    max_response_bytes: int = 128 * 1024
    deadline_seconds: float = 5.0

    def __post_init__(self) -> None:
        if not 0 < self.max_request_bytes <= 64 * 1024:
            raise ValueError("MCP request budget may only be tightened")
        # A smaller value cannot even carry the frozen BUDGET_EXCEEDED envelope.
        if not 192 <= self.max_response_bytes <= 128 * 1024:
            raise ValueError("MCP response budget must fit the minimal error frame")
        if not 0 < self.deadline_seconds <= 5.0:
            raise ValueError("MCP deadline may only be tightened")


class McpServer:
    """Serve a fixed subset of the existing read-only tool registry."""

    def __init__(
        self,
        *,
        token: str,
        registry: ToolRegistry,
        tool_names: frozenset[str],
        manifest_digest: str = "",
        limits: McpLimits = McpLimits(),
        monotonic=time.monotonic,
    ) -> None:
        if not isinstance(token, str) or len(token.encode("utf-8")) < 32:
            raise ValueError("MCP token must contain at least 32 UTF-8 bytes")
        names = frozenset(tool_names)
        if not names or not names.issubset(PREVIEW_TOOL_ALLOWLIST):
            raise ValueError("MCP tools must be a non-empty preview allowlist subset")
        for name in names:
            tool = registry.get(name)
            if tool is None:
                raise ValueError("MCP tool is not registered")
            spec = tool.spec
            if (
                spec.capability is not ToolCapability.READ
                or spec.side_effect is not SideEffect.NONE
                or not spec.idempotent
            ):
                raise ValueError("MCP tool is not read-only and idempotent")
        self._token = token
        self._registry = registry
        self._tool_names = names
        self._manifest_digest = manifest_digest
        self._limits = limits
        self._monotonic = monotonic
        self._initialize_responded = False
        self._initialized = False

    def handle_line(self, line: str | bytes) -> dict[str, Any] | None:
        started = self._monotonic()
        raw = line.encode("utf-8") if isinstance(line, str) else line
        if len(raw) > self._limits.max_request_bytes:
            return self._error(None, _BUDGET_ERROR, ErrorCode.BUDGET_EXCEEDED, "request budget exceeded")
        try:
            request = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error(None, _PARSE_ERROR, "PARSE_ERROR", "invalid JSON")
        if not isinstance(request, dict):
            return self._error(None, _INVALID_REQUEST, "INVALID_REQUEST", "request must be an object")
        has_id = "id" in request
        request_id = request.get("id")
        if has_id and not self._valid_request_id(request_id):
            return self._error(None, _INVALID_REQUEST, "INVALID_REQUEST", "invalid request id")
        if request.get("jsonrpc") != JSONRPC_VERSION or not isinstance(request.get("method"), str):
            return self._error(request_id, _INVALID_REQUEST, "INVALID_REQUEST", "invalid JSON-RPC request")
        params = request.get("params", {})
        if not isinstance(params, dict):
            return self._error(request_id, _INVALID_PARAMS, "INVALID_PARAMS", "params must be an object")
        if not self._authenticated(params):
            return None if not has_id else self._error(
                request_id,
                _PERMISSION_ERROR,
                ErrorCode.TOOL_PERMISSION_DENIED,
                "tool permission denied",
            )
        clean_params = {key: value for key, value in params.items() if key != "_meta"}
        method = request["method"]
        if not has_id:
            if method == "notifications/initialized" and self._initialize_responded and not clean_params:
                self._initialized = True
            return None
        try:
            response = self._dispatch(request_id, method, clean_params, started)
        except Exception:
            response = self._error(request_id, _INTERNAL_ERROR, "INTERNAL_ERROR", "internal error")
        if self._monotonic() - started > self._limits.deadline_seconds:
            response = self._error(
                request_id,
                _BUDGET_ERROR,
                ErrorCode.BUDGET_EXCEEDED,
                "deadline budget exceeded",
            )
        encoded = canonical_json(response)
        if len(encoded) > self._limits.max_response_bytes:
            response = self._error(
                request_id,
                _BUDGET_ERROR,
                ErrorCode.BUDGET_EXCEEDED,
                "response budget exceeded",
            )
            if len(canonical_json(response)) > self._limits.max_response_bytes:
                raise RuntimeError("MCP response budget cannot carry the error frame")
        return response

    def serve(self, stdin: TextIOBase, stdout: TextIOBase) -> None:
        """Read newline-delimited requests and write protocol frames only."""
        for line in stdin:
            response = self.handle_line(line)
            if response is None:
                continue
            stdout.write(canonical_json(response).decode("utf-8") + "\n")
            stdout.flush()

    @staticmethod
    def _valid_request_id(request_id: object) -> bool:
        return request_id is None or (isinstance(request_id, (str, int, float)) and not isinstance(request_id, bool))

    def _authenticated(self, params: Mapping[str, Any]) -> bool:
        meta = params.get("_meta")
        if not isinstance(meta, Mapping):
            return False
        authorization = meta.get("authorization")
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            return False
        supplied = authorization[7:]
        return hmac.compare_digest(supplied.encode("utf-8"), self._token.encode("utf-8"))

    def _dispatch(
        self,
        request_id: object,
        method: str,
        params: Mapping[str, Any],
        started: float,
    ) -> dict[str, Any]:
        if method == "initialize":
            if self._initialize_responded:
                return self._error(request_id, _INVALID_REQUEST, "INVALID_REQUEST", "already initialized")
            if (
                params.get("protocolVersion") != MCP_PROTOCOL_VERSION
                or not isinstance(params.get("capabilities"), Mapping)
                or not isinstance(params.get("clientInfo"), Mapping)
            ):
                return self._error(request_id, _INVALID_PARAMS, "INVALID_PARAMS", "invalid initialize params")
            self._initialize_responded = True
            return self._result(
                request_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "knowledgePack": {"manifestDigest": self._manifest_digest},
                },
            )
        if not self._initialized:
            return self._error(request_id, _INVALID_REQUEST, "INVALID_REQUEST", "MCP is not initialized")
        if method == "tools/list":
            if params:
                return self._error(request_id, _INVALID_PARAMS, "INVALID_PARAMS", "tools/list has no params")
            definitions = []
            for schema in self._registry.schemas():
                if schema["name"] not in self._tool_names:
                    continue
                definitions.append(
                    {
                        "name": schema["name"],
                        "description": schema["description"],
                        "inputSchema": schema["input_schema"],
                    }
                )
            return self._result(request_id, {"tools": definitions})
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(name, str) or not isinstance(arguments, Mapping):
                return self._error(request_id, _INVALID_PARAMS, "INVALID_PARAMS", "invalid tool call")
            if name not in self._tool_names:
                return self._error(
                    request_id,
                    _PERMISSION_ERROR,
                    ErrorCode.TOOL_PERMISSION_DENIED,
                    "tool permission denied",
                )
            context = ToolContext(
                learner_id=None,
                source_scope="DEFAULT_ONLY",
                correlation_id=f"mcp-{request_id}",
                permissions=frozenset({"read"}),
                budget={"deadline_ms": int(self._limits.deadline_seconds * 1000)},
            )
            remaining = self._limits.deadline_seconds - (self._monotonic() - started)
            if remaining <= 0:
                return self._error(
                    request_id, _BUDGET_ERROR, ErrorCode.BUDGET_EXCEEDED, "deadline budget exceeded"
                )
            result = self._execute_bounded(name, context, arguments, remaining)
            if result is None:
                return self._error(
                    request_id, _BUDGET_ERROR, ErrorCode.BUDGET_EXCEEDED, "deadline budget exceeded"
                )
            if not result.ok:
                error = result.error
                if error is None:
                    return self._error(request_id, _INTERNAL_ERROR, "INTERNAL_ERROR", "internal error")
                if error.code in {"TOOL_UNKNOWN", "TOOL_NOT_AUTHORIZED"}:
                    return self._error(
                        request_id,
                        _PERMISSION_ERROR,
                        ErrorCode.TOOL_PERMISSION_DENIED,
                        "tool permission denied",
                    )
                return self._result(
                    request_id,
                    {
                        "content": [{"type": "text", "text": error.message}],
                        "isError": True,
                        "error": {"code": error.code, "retryable": error.retryable},
                    },
                )
            if self._monotonic() - started > self._limits.deadline_seconds:
                return self._error(
                    request_id, _BUDGET_ERROR, ErrorCode.BUDGET_EXCEEDED, "deadline budget exceeded"
                )
            structured = result.data
            text = canonical_json(structured).decode("utf-8")
            return self._result(
                request_id,
                {
                    "content": [{"type": "text", "text": text}],
                    "structuredContent": structured,
                    "isError": False,
                },
            )
        return self._error(request_id, _METHOD_NOT_FOUND, "METHOD_NOT_FOUND", "method not found")


    def _execute_bounded(
        self,
        name: str,
        context: ToolContext,
        arguments: Mapping[str, Any],
        timeout: float,
    ):
        """Bound a synchronous read tool without blocking the stdio loop forever.

        Python cannot cancel a running thread.  A timed-out daemon is abandoned,
        but read-only registration plus result projection means it cannot publish a
        late protocol response or perform an approved domain write.
        """
        box: dict[str, Any] = {}

        def run() -> None:
            box["result"] = self._registry.execute(name, context, arguments)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            return None
        return box.get("result")

    @staticmethod
    def _result(request_id: object, result: Mapping[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": dict(result)}

    @staticmethod
    def _error(
        request_id: object,
        rpc_code: int,
        code: str | ErrorCode,
        message: str,
    ) -> dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": {
                "code": rpc_code,
                "message": message,
                "data": {"code": str(code), "retryable": code is ErrorCode.BUDGET_EXCEEDED},
            },
        }


def _strict_enabled(raw: str | None) -> bool:
    if raw is None or raw.strip().lower() in {"0", "false", "no"}:
        return False
    if raw.strip().lower() in {"1", "true", "yes"}:
        return True
    raise ValueError("SA_MCP_ENABLED must be a strict boolean")


def build_default_server() -> McpServer:
    """Build the explicit local stdio surface from the application's read services."""
    if not _strict_enabled(os.getenv("SA_MCP_ENABLED")):
        raise RuntimeError("MCP is disabled")
    token = os.getenv("SA_MCP_TOKEN", "")

    # Importing the application assembly does not start a listener.  It gives this
    # explicit process the same read services as Search/Quiz/ReviewDue without a
    # second retrieval or scheduling authority.
    from .knowledge_pack_manifest import build_knowledge_pack_manifest
    from .main import _quiz, _recall, _review_scheduler
    from .sources.markdown_pack import MarkdownPackSource
    from .tools.quiz import QuizTool
    from .tools.retrieve import RetrieveTool
    from .tools.review_due import ReviewDueTool

    registry = ToolRegistry()
    registry.register(RetrieveTool(_recall))
    registry.register(QuizTool(_quiz))
    registry.register(ReviewDueTool(_review_scheduler))
    manifest = build_knowledge_pack_manifest(MarkdownPackSource().materialize())
    return McpServer(
        token=token,
        registry=registry,
        tool_names=PREVIEW_TOOL_ALLOWLIST,
        manifest_digest=manifest.manifest_digest,
    )


def main() -> int:
    """Run the explicitly enabled stdio server; never opens a network listener."""
    import sys

    build_default_server().serve(sys.stdin, sys.stdout)  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["MCP_PROTOCOL_VERSION", "McpLimits", "McpServer"]
