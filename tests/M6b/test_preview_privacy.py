"""M6b end-to-end canaries for preview privacy boundaries."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.llm_client import (
    ModelTurn,
    ModelUsage,
    ProviderError,
    ProviderErrorCode,
    ToolCall,
    ToolExecutionResult,
)
from app.preview_service import PREVIEW_PATH, PreviewService, build_preview_router
from app.protocols import ToolContext, ToolError, ToolResult, ToolSpec
from app.tool_registry import ToolRegistry


pytestmark = pytest.mark.m6b
_TOKEN = "preview-token-that-is-at-least-thirty-two-bytes"
_API_KEY = "anthropic-api-key-private-canary"
_PROXY_CREDENTIAL = "proxy-user:proxy-password-private-canary"
_SENSITIVE_CANARIES = (
    "private-prompt-boundary-canary",
    "private-query-boundary-canary",
    "private-tool-body-boundary-canary",
    "private-quiz-body-boundary-canary",
    "private-review-body-boundary-canary",
    r"C:\\Users\\private-user\\notes.md",
    "/home/private-user/notes.md",
    r"\\private-server\private-share\notes.md",
    "../../private-parent/notes.md",
    "provider-exception-private-canary",
    "provider-header-private-canary",
    "provider-body-private-canary",
    _API_KEY,
    _TOKEN,
    _PROXY_CREDENTIAL,
    "inbound-token-private-canary",
)


@dataclass
class _Conversation:
    prompt: str
    results: list[ToolExecutionResult]


class _BoundaryClient:
    def __init__(
        self,
        *,
        final_answer: str = "safe final answer",
        provider_error: ProviderError | None = None,
    ) -> None:
        self.final_answer = final_answer
        self.provider_error = provider_error
        self.turn = 0
        self.visible_messages: list[str] = []

    def new_conversation(self, prompt: str) -> _Conversation:
        self.visible_messages.append(prompt)
        return _Conversation(prompt, [])

    async def count_tokens(
        self,
        conversation: Any,
        tools: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> int:
        del conversation, tools, timeout
        return 1

    async def create_turn(
        self,
        conversation: _Conversation,
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        timeout: float,
    ) -> ModelTurn:
        del tools, max_tokens, timeout
        if self.provider_error is not None:
            raise self.provider_error
        self.turn += 1
        if self.turn == 1:
            return ModelTurn(
                text="",
                tool_calls=(
                    ToolCall(
                        "provider-call-private-canary",
                        "retrieve",
                        {"question": "private-query-boundary-canary"},
                    ),
                ),
                stop_reason="tool_use",
                usage=ModelUsage(input_tokens=1, output_tokens=1),
                latency_ms=1.0,
            )
        self.visible_messages.extend(result.content for result in conversation.results)
        return ModelTurn(
            text=self.final_answer,
            tool_calls=(),
            stop_reason="end_turn",
            usage=ModelUsage(input_tokens=1, output_tokens=1),
            latency_ms=1.0,
        )

    def append_tool_result(
        self,
        conversation: _Conversation,
        result: ToolExecutionResult,
    ) -> None:
        conversation.results.append(result)

    async def close(self) -> None:
        return None


class _BoundaryTool:
    spec = ToolSpec(
        name="retrieve",
        description="retrieve",
        input_schema={
            "type": "object",
            "properties": {"question": {"type": "string", "minLength": 1}},
            "required": ["question"],
            "additionalProperties": False,
        },
    )

    def __init__(self, result: ToolResult) -> None:
        self.result = result

    def execute(
        self,
        context: ToolContext,
        arguments: Mapping[str, Any],
    ) -> ToolResult:
        del arguments
        return ToolResult(
            data=self.result.data,
            error=self.result.error,
            correlation_id=context.correlation_id,
        )


def _registry(result: ToolResult) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_BoundaryTool(result), lambda tool_result: tool_result.data)
    return registry


def _service(client: _BoundaryClient, result: ToolResult) -> PreviewService:
    return PreviewService(
        token=_TOKEN,
        provider_key=_API_KEY,
        registry=_registry(result),
        client_factory=lambda key: client,
        hmac_key=b"h" * 32,
    )


def _app(service: PreviewService) -> FastAPI:
    app = FastAPI()
    app.include_router(build_preview_router(service))
    return app


def _assert_absent(value: Any, canaries: Sequence[str] = _SENSITIVE_CANARIES) -> None:
    serialized = str(value)
    for canary in canaries:
        assert canary not in serialized


def _assert_logs_absent(caplog: pytest.LogCaptureFixture) -> None:
    _assert_absent(caplog.text)
    for record in caplog.records:
        _assert_absent(record.getMessage())
        _assert_absent(record.__dict__)


def test_sensitive_inputs_cross_only_required_provider_boundary(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", f"https://{_PROXY_CREDENTIAL}@proxy.invalid")
    tool_body = {
        "content": "private-tool-body-boundary-canary",
        "quiz": "private-quiz-body-boundary-canary",
        "review": "private-review-body-boundary-canary",
        "paths": [
            r"C:\\Users\\private-user\\notes.md",
            "/home/private-user/notes.md",
            r"\\private-server\private-share\notes.md",
            "../../private-parent/notes.md",
        ],
    }
    client = _BoundaryClient()
    service = _service(client, ToolResult(data=tool_body))

    with caplog.at_level(logging.DEBUG), TestClient(_app(service)) as http:
        response = http.post(
            PREVIEW_PATH,
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={"prompt": "private-prompt-boundary-canary"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "private-prompt-boundary-canary" in client.visible_messages
    assert any("private-tool-body-boundary-canary" in item for item in client.visible_messages)
    _assert_absent(response.text)
    _assert_absent(response.json()["agent_trace"])
    _assert_logs_absent(caplog)
    _assert_absent(_app(service).openapi())


def test_provider_failure_exposes_only_stable_reason(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = _BoundaryClient(
        provider_error=ProviderError(
            ProviderErrorCode.UNAVAILABLE,
            retryable=False,
            status_code=529,
        )
    )
    result = ToolResult(
        error=ToolError(
            "TOOL_INTERNAL",
            "provider-body-private-canary",
            retryable=False,
        )
    )
    service = _service(client, result)

    with caplog.at_level(logging.DEBUG), TestClient(_app(service)) as http:
        response = http.post(
            PREVIEW_PATH,
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={"prompt": "private-prompt-boundary-canary"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "terminated"
    assert response.json()["termination_reason"] == "provider_unavailable"
    _assert_absent(response.text)
    _assert_logs_absent(caplog)


def test_http_error_envelopes_and_openapi_exclude_secrets(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = _service(_BoundaryClient(), ToolResult(data={}))
    missing_provider = PreviewService(
        token=_TOKEN,
        provider_key="",
        registry=_registry(ToolResult(data={})),
        client_factory=lambda key: _BoundaryClient(),
        hmac_key=b"h" * 32,
    )

    with caplog.at_level(logging.DEBUG), TestClient(_app(service)) as http:
        unauthorized = http.post(
            PREVIEW_PATH,
            headers={"Authorization": "Bearer inbound-token-private-canary"},
            json={"prompt": "private-prompt-boundary-canary"},
        )
        invalid = http.post(
            PREVIEW_PATH,
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={
                "prompt": "private-prompt-boundary-canary",
                "unexpected": "private-query-boundary-canary",
            },
        )
        openapi = http.get("/openapi.json")
    with TestClient(_app(missing_provider)) as http:
        unavailable = http.post(
            PREVIEW_PATH,
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={"prompt": "private-prompt-boundary-canary"},
        )

    assert unauthorized.status_code == 401
    assert invalid.status_code == 422
    assert unavailable.status_code == 503
    assert openapi.status_code == 200
    _assert_absent(unauthorized.text)
    _assert_absent(invalid.text)
    _assert_absent(unavailable.text)
    _assert_absent(openapi.text)
    _assert_logs_absent(caplog)


def test_lazy_sdk_factory_receives_api_key_without_logging_secrets(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from app.llm_client import AnthropicLLMClient

    captured: dict[str, Any] = {}

    class OfflineClient:
        async def close(self) -> None:
            return None

    def factory(**kwargs: Any) -> OfflineClient:
        captured.update(kwargs)
        return OfflineClient()

    sdk = SimpleNamespace(AsyncAnthropic=factory)
    monkeypatch.setenv("HTTPS_PROXY", f"https://{_PROXY_CREDENTIAL}@proxy.invalid")
    monkeypatch.setattr("app.llm_client.importlib.import_module", lambda name: sdk)
    adapter = AnthropicLLMClient(_API_KEY)

    with caplog.at_level(logging.DEBUG):
        client = adapter._get_client()
        asyncio.run(adapter.close())

    assert isinstance(client, OfflineClient)
    assert captured == {
        "api_key": _API_KEY,
        "max_retries": 0,
        "timeout": 60.0,
    }
    _assert_logs_absent(caplog)


def test_openapi_declares_sanitized_validation_envelope() -> None:
    service = _service(_BoundaryClient(), ToolResult(data={}))

    operation = _app(service).openapi()["paths"][PREVIEW_PATH]["post"]

    assert "422" in operation["responses"]
    schema = operation["responses"]["422"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/PreviewHttpError")
    _assert_absent(operation)


def test_overload_envelope_excludes_secrets() -> None:
    async def scenario() -> None:
        gate = asyncio.Event()

        class BlockingClient(_BoundaryClient):
            async def count_tokens(
                self,
                conversation: Any,
                tools: Sequence[Mapping[str, Any]],
                *,
                timeout: float,
            ) -> int:
                del conversation, tools, timeout
                await gate.wait()
                return 1

        service = PreviewService(
            token=_TOKEN,
            provider_key=_API_KEY,
            registry=_registry(ToolResult(data={})),
            client_factory=lambda key: BlockingClient(),
            semaphore_wait_seconds=0.01,
            hmac_key=b"h" * 32,
        )
        request = service.run
        from app.preview_service import PreviewRequest

        preview = PreviewRequest(prompt="private-prompt-boundary-canary")
        first = asyncio.create_task(request(preview, f"Bearer {_TOKEN}"))
        second = asyncio.create_task(request(preview, f"Bearer {_TOKEN}"))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        try:
            with pytest.raises(Exception) as raised:
                await request(preview, f"Bearer {_TOKEN}")
            error = raised.value
            assert getattr(error, "status_code", None) == 429
            _assert_absent(getattr(error, "detail", {}))
            _assert_absent(getattr(error, "headers", {}))
        finally:
            gate.set()
            await asyncio.gather(first, second)

    asyncio.run(scenario())
