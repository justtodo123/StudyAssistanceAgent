from __future__ import annotations

import io
import json
import threading
import time
from pathlib import Path
from typing import Any, Mapping

import pytest

from app.errors import ErrorCode
from app.mcp_server import MCP_PROTOCOL_VERSION, McpLimits, McpServer
from app.protocols import SideEffect, ToolCapability, ToolContext, ToolResult, ToolSpec
from app.tool_registry import PREVIEW_TOOL_ALLOWLIST, ToolRegistry

pytestmark = pytest.mark.m10

_TOKEN = "m" * 32


class CountingTool:
    spec = ToolSpec(
        name="retrieve",
        description="Retrieve safe metadata.",
        input_schema={
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
            "additionalProperties": False,
        },
        capability=ToolCapability.READ,
        side_effect=SideEffect.NONE,
        idempotent=True,
    )

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, context: ToolContext, arguments: Mapping[str, Any]) -> ToolResult:
        self.calls += 1
        return ToolResult(
            data={"answer": "safe projected answer", "count": self.calls},
            correlation_id=context.correlation_id,
        )


def _registry() -> tuple[ToolRegistry, CountingTool]:
    tool = CountingTool()
    registry = ToolRegistry()
    registry.register(tool, lambda result: result.data)
    return registry, tool


def _server(*, initialized: bool = True, **overrides) -> tuple[McpServer, CountingTool]:
    registry, tool = _registry()
    values = {
        "token": _TOKEN,
        "registry": registry,
        "tool_names": frozenset({"retrieve"}),
        "manifest_digest": "a" * 64,
    }
    values.update(overrides)
    server = McpServer(**values)
    if initialized:
        token = values["token"]
        response = server.handle_line(_request("initialize", request_id="setup", token=token))
        assert response and "result" in response
        notification = json.loads(_request("notifications/initialized", token=token))
        notification.pop("id")
        assert server.handle_line(json.dumps(notification)) is None
    return server, tool


def _request(
    method: str,
    *,
    request_id: object = 1,
    params: dict[str, Any] | None = None,
    token: str = _TOKEN,
) -> str:
    if method == "initialize" and params is None:
        params = {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "m10-test", "version": "1"},
        }
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }
    payload["params"]["_meta"] = {"authorization": f"Bearer {token}"}
    return json.dumps(payload)


def test_the_server_requires_a_long_utf8_token_and_a_nonempty_read_allowlist() -> None:
    registry, _ = _registry()
    with pytest.raises(ValueError):
        McpServer(token="m" * 31, registry=registry, tool_names=frozenset({"retrieve"}))
    with pytest.raises(ValueError):
        McpServer(token=_TOKEN, registry=registry, tool_names=frozenset())
    with pytest.raises(ValueError):
        McpServer(token=_TOKEN, registry=registry, tool_names=frozenset({"log_review"}))

    assert {"retrieve"}.issubset(PREVIEW_TOOL_ALLOWLIST)


def test_initialize_exposes_only_the_minimal_tool_capability() -> None:
    server, _ = _server(initialized=False)

    response = server.handle_line(_request("initialize", request_id="init"))

    assert response["id"] == "init"
    result = response["result"]
    assert result["protocolVersion"] == MCP_PROTOCOL_VERSION
    assert result["capabilities"] == {"tools": {"listChanged": False}}
    assert result["knowledgePack"] == {"manifestDigest": "a" * 64}
    assert "resources" not in result["capabilities"]




def test_tools_are_unavailable_until_the_initialize_handshake_finishes() -> None:
    server, tool = _server(initialized=False)

    before = server.handle_line(_request("tools/list"))
    assert before["error"]["code"] == -32600
    assert tool.calls == 0

    assert "result" in server.handle_line(_request("initialize"))
    still_before = server.handle_line(_request("tools/list", request_id=2))
    assert still_before["error"]["code"] == -32600

    notification = json.loads(_request("notifications/initialized"))
    notification.pop("id")
    assert server.handle_line(json.dumps(notification)) is None
    assert "result" in server.handle_line(_request("tools/list", request_id=3))


def test_initialize_and_request_ids_follow_the_json_rpc_contract() -> None:
    server, _ = _server(initialized=False)
    malformed = _request("initialize", params={})
    assert server.handle_line(malformed)["error"]["code"] == -32602

    assert "result" in server.handle_line(_request("initialize", request_id=None))
    duplicate = server.handle_line(_request("initialize", request_id=2))
    assert duplicate["error"]["code"] == -32600

    other, _ = _server(initialized=False)
    invalid_id = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": {"bad": True},
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
                "_meta": {"authorization": f"Bearer {_TOKEN}"},
            },
        }
    )
    assert other.handle_line(invalid_id)["error"]["code"] == -32600

def test_tools_list_is_deterministic_strictly_read_only_and_nonempty() -> None:
    server, _ = _server()

    response = server.handle_line(_request("tools/list"))
    tools = response["result"]["tools"]

    assert tools
    assert [tool["name"] for tool in tools] == ["retrieve"]
    assert all(tool["name"] in PREVIEW_TOOL_ALLOWLIST for tool in tools)
    encoded = json.dumps(tools).lower()
    assert "log_review" not in encoded
    assert "sqlite" not in encoded
    assert "lancedb" not in encoded
    assert "qdrant" not in encoded


def test_tools_call_reaches_the_registry_and_returns_projected_data() -> None:
    server, tool = _server()

    response = server.handle_line(
        _request("tools/call", params={"name": "retrieve", "arguments": {"question": "paging"}})
    )

    assert tool.calls == 1
    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"] == {"answer": "safe projected answer", "count": 1}
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]


@pytest.mark.parametrize("name", ["log_review", "unknown", "sqlite_query"])
def test_unknown_or_write_like_tools_return_the_frozen_permission_code(name: str) -> None:
    server, tool = _server()

    response = server.handle_line(
        _request("tools/call", params={"name": name, "arguments": {}})
    )

    assert tool.calls == 0
    assert response["error"]["data"]["code"] == ErrorCode.TOOL_PERMISSION_DENIED.value
    assert response["error"]["data"]["retryable"] is False


def test_missing_or_wrong_authentication_fails_before_tool_execution() -> None:
    server, tool = _server()
    missing = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    wrong = _request("tools/list").replace(_TOKEN, "wrong-secret-that-is-long-enough-000")

    for line in (missing, wrong):
        response = server.handle_line(line)
        assert response["error"]["data"]["code"] == ErrorCode.TOOL_PERMISSION_DENIED.value
    assert tool.calls == 0


def test_request_response_and_deadline_budgets_return_the_frozen_budget_code() -> None:
    registry, _ = _registry()
    request_server = McpServer(
        token=_TOKEN,
        registry=registry,
        tool_names=frozenset({"retrieve"}),
        limits=McpLimits(max_request_bytes=32),
    )
    response = request_server.handle_line(_request("tools/list"))
    assert response["error"]["data"]["code"] == ErrorCode.BUDGET_EXCEEDED.value

    with pytest.raises(ValueError):
        McpLimits(max_response_bytes=191)

    response_server, _ = _server(initialized=False, limits=McpLimits(max_response_bytes=192))
    response = response_server.handle_line(_request("initialize"))
    assert response["error"]["data"]["code"] == ErrorCode.BUDGET_EXCEEDED.value
    assert len(json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode()) <= 192

    deadline_server, _ = _server()
    ticks = iter((0.0, 6.0, 6.0))
    deadline_server._monotonic = lambda: next(ticks)
    response = deadline_server.handle_line(_request("tools/list"))
    assert response["error"]["data"]["code"] == ErrorCode.BUDGET_EXCEEDED.value


def test_invalid_frames_are_sanitized_and_request_ids_are_preserved() -> None:
    server, _ = _server()

    assert server.handle_line("not-json")["error"]["code"] == -32700
    assert server.handle_line("[]")["error"]["code"] == -32600
    invalid = json.dumps({"jsonrpc": "1.0", "id": "kept", "method": "tools/list"})
    assert server.handle_line(invalid)["id"] == "kept"
    assert server.handle_line(_request("missing/method"))["error"]["code"] == -32601
    assert server.handle_line(json.dumps({"jsonrpc": "2.0", "method": "tools/list"})) is None


def test_serve_writes_only_newline_delimited_json_frames() -> None:
    server, _ = _server()
    stdin = io.StringIO(_request("initialize") + "\n" + _request("tools/list", request_id=2) + "\n")
    stdout = io.StringIO()

    server.serve(stdin, stdout)

    lines = stdout.getvalue().splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["id"] for line in lines] == [1, 2]
    assert all(isinstance(json.loads(line), dict) and json.loads(line)["jsonrpc"] == "2.0" for line in lines)


def test_a_blocking_read_tool_is_cut_off_at_the_deadline() -> None:
    registry = ToolRegistry()
    finished = threading.Event()

    class BlockingTool(CountingTool):
        def execute(self, context: ToolContext, arguments: Mapping[str, Any]) -> ToolResult:
            finished.wait(1.0)
            return ToolResult(data={"late": True}, correlation_id=context.correlation_id)

    tool = BlockingTool()
    registry.register(tool, lambda result: result.data)
    server = McpServer(
        token=_TOKEN,
        registry=registry,
        tool_names=frozenset({"retrieve"}),
        limits=McpLimits(deadline_seconds=0.01),
    )
    initialize = server.handle_line(_request("initialize", token=_TOKEN))
    assert initialize and "result" in initialize
    notification = json.loads(_request("notifications/initialized", token=_TOKEN))
    notification.pop("id")
    server.handle_line(json.dumps(notification))

    started = time.monotonic()
    response = server.handle_line(
        _request("tools/call", params={"name": "retrieve", "arguments": {"question": "slow"}}, token=_TOKEN)
    )
    elapsed = time.monotonic() - started
    finished.set()

    assert elapsed < 0.5
    assert response["error"]["data"]["code"] == ErrorCode.BUDGET_EXCEEDED.value


def test_protocol_outputs_never_echo_tokens_paths_or_internal_exceptions(tmp_path: Path) -> None:
    secret = "secret-token-sentinel"
    path = str(tmp_path / "private.sqlite")
    server, _ = _server(token=_TOKEN + secret)
    request = _request("tools/list", token=_TOKEN + secret)

    responses = [
        server.handle_line(request),
        server.handle_line(path),
        server.handle_line(_request("tools/call", params={"name": path, "arguments": {}}).replace(_TOKEN, _TOKEN + secret)),
    ]
    encoded = json.dumps(responses, ensure_ascii=False)

    assert secret not in encoded
    assert path not in encoded
    assert "Traceback" not in encoded


def test_the_mcp_module_has_no_listener_provider_backend_or_domain_write_imports() -> None:
    import ast

    source = (Path(__file__).parents[2] / "platform" / "app" / "mcp_server.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.casefold()
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").casefold()
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert imports
    for forbidden in (
        "fastapi",
        "uvicorn",
        "socket",
        "llm_client",
        "learning_store",
        "vector_store",
        "sqlite3",
        "lancedb",
        "qdrant",
        "runner_service",
        "runner_authority",
    ):
        assert all(forbidden not in imported for imported in imports)
    assert "log_review" not in source
