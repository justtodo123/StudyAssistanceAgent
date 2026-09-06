"""M6b tests for the isolated authenticated preview HTTP service."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.llm_client import ModelTurn, ModelUsage, ToolCall, ToolExecutionResult
from app.preview_agent import PreviewLimits
from app.preview_service import PREVIEW_PATH, PreviewRequest, PreviewService, build_preview_router
from app.protocols import ToolContext, ToolResult, ToolSpec
from app.tool_registry import ToolRegistry


pytestmark = pytest.mark.m6b
_TOKEN = "preview-token-that-is-at-least-thirty-two-bytes"


@dataclass
class _Conversation:
    prompt: str


class _Client:
    def __init__(
        self,
        answer: str = "safe answer",
        *,
        gate: asyncio.Event | None = None,
        close_failure: BaseException | None = None,
    ) -> None:
        self.answer = answer
        self.gate = gate
        self.close_failure = close_failure
        self.closed = False

    def new_conversation(self, prompt: str) -> _Conversation:
        return _Conversation(prompt)

    async def count_tokens(
        self,
        conversation: Any,
        tools: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> int:
        del conversation, tools, timeout
        if self.gate is not None:
            await self.gate.wait()
        return 1

    async def create_turn(
        self,
        conversation: Any,
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        timeout: float,
    ) -> ModelTurn:
        del conversation, tools, max_tokens, timeout
        return ModelTurn(
            text=self.answer,
            tool_calls=(),
            stop_reason="end_turn",
            usage=ModelUsage(input_tokens=1, output_tokens=1),
            latency_ms=1.0,
        )

    def append_tool_result(
        self,
        conversation: Any,
        result: ToolExecutionResult,
    ) -> None:
        del conversation, result

    async def close(self) -> None:
        self.closed = True
        if self.close_failure is not None:
            raise self.close_failure


class _Tool:
    spec = ToolSpec(
        name="retrieve",
        description="retrieve",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    )

    def __init__(self) -> None:
        self.contexts: list[ToolContext] = []

    def execute(
        self,
        context: ToolContext,
        arguments: Mapping[str, Any],
    ) -> ToolResult:
        del arguments
        self.contexts.append(context)
        return ToolResult(data={}, correlation_id=context.correlation_id)


class _BlockingTool(_Tool):
    def __init__(self) -> None:
        super().__init__()
        self.release = threading.Event()
        self._lock = threading.Lock()
        self.started = 0
        self.active = 0
        self.max_active = 0

    def execute(
        self,
        context: ToolContext,
        arguments: Mapping[str, Any],
    ) -> ToolResult:
        del arguments
        with self._lock:
            self.started += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if not self.release.wait(timeout=5):
                raise AssertionError("blocking tool was not released")
            return ToolResult(data={}, correlation_id=context.correlation_id)
        finally:
            with self._lock:
                self.active -= 1

    def counts(self) -> tuple[int, int, int]:
        with self._lock:
            return self.started, self.active, self.max_active


class _ToolClient(_Client):
    def __init__(self, call_id: str) -> None:
        super().__init__()
        self.call_id = call_id
        self.turns = 0
        self.results: list[ToolExecutionResult] = []

    async def create_turn(
        self,
        conversation: Any,
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        timeout: float,
    ) -> ModelTurn:
        del conversation, tools, max_tokens, timeout
        self.turns += 1
        if self.turns == 1:
            return ModelTurn(
                text="",
                tool_calls=(ToolCall(self.call_id, "retrieve", {}),),
                stop_reason="tool_use",
                usage=ModelUsage(input_tokens=1, output_tokens=1),
                latency_ms=1.0,
            )
        return ModelTurn(
            text="should-not-run",
            tool_calls=(),
            stop_reason="end_turn",
            usage=ModelUsage(input_tokens=1, output_tokens=1),
            latency_ms=1.0,
        )

    def append_tool_result(
        self,
        conversation: Any,
        result: ToolExecutionResult,
    ) -> None:
        del conversation
        self.results.append(result)


async def _wait_for_tool_count(
    tool: _BlockingTool,
    expected: int,
    *,
    timeout: float = 1.0,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while tool.counts()[0] != expected:
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError("tool did not reach expected execution count")
        await asyncio.sleep(0.005)


def _registry(tool: _Tool | None = None) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(tool or _Tool(), lambda result: result.data)
    return registry


def _service(
    factory: Any,
    *,
    provider_key: str = "provider-key",
    limits: PreviewLimits = PreviewLimits(),
    wait: float = 0.25,
    registry: ToolRegistry | None = None,
) -> PreviewService:
    return PreviewService(
        token=_TOKEN,
        provider_key=provider_key,
        registry=registry or _registry(),
        client_factory=factory,
        limits=limits,
        semaphore_wait_seconds=wait,
        hmac_key=b"h" * 32,
    )


def _app(service: PreviewService) -> FastAPI:
    app = FastAPI()
    app.include_router(build_preview_router(service))
    return app


def test_router_is_fresh_and_does_not_modify_unrelated_openapi() -> None:
    default = FastAPI()
    service = _service(lambda key: _Client())
    enabled = _app(service)

    assert PREVIEW_PATH not in default.openapi()["paths"]
    assert PREVIEW_PATH in enabled.openapi()["paths"]
    assert PREVIEW_PATH not in default.openapi()["paths"]


def test_authentication_precedes_provider_configuration_disclosure() -> None:
    app = _app(_service(lambda key: _Client(), provider_key=""))

    with TestClient(app) as client:
        unauthorized = client.post(PREVIEW_PATH, json={"prompt": "question"})
        unavailable = client.post(
            PREVIEW_PATH,
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={"prompt": "question"},
        )

    assert unauthorized.status_code == 401
    assert unauthorized.json() == {
        "detail": {
            "error": {
                "code": "PREVIEW_UNAUTHORIZED",
                "message": "preview authorization failed",
                "retryable": False,
            }
        }
    }
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"]["error"]["code"] == "PREVIEW_PROVIDER_NOT_CONFIGURED"


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "Basic value",
        "Bearer",
        "Bearer ",
        f"Bearer {_TOKEN} suffix",
    ],
)
def test_malformed_or_missing_bearer_is_rejected(authorization: str | None) -> None:
    headers = {} if authorization is None else {"Authorization": authorization}

    with TestClient(_app(_service(lambda key: _Client()))) as client:
        response = client.post(PREVIEW_PATH, headers=headers, json={"prompt": "question"})

    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "PREVIEW_UNAUTHORIZED"


def test_success_envelope_is_sanitized_and_client_is_closed() -> None:
    created: list[_Client] = []

    def factory(key: str) -> _Client:
        assert key == "provider-key"
        client = _Client()
        created.append(client)
        return client

    with TestClient(_app(_service(factory))) as client:
        response = client.post(
            PREVIEW_PATH,
            headers={"Authorization": f"bearer {_TOKEN}"},
            json={"prompt": "private-prompt-canary", "learner_id": "learner"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["answer"] == "safe answer"
    assert body["termination_reason"] == "completed"
    assert body["agent_trace"][-1]["request_id_hmac"]
    assert len(body["agent_trace"][-1]["request_id_hmac"]) == 64
    assert "private-prompt-canary" not in response.text
    assert created[0].closed is True


def test_tool_context_uses_read_scope_learner_and_hmac_correlation() -> None:
    tool = _Tool()
    registry = _registry(tool)

    class ToolClient(_Client):
        def __init__(self) -> None:
            super().__init__()
            self.turns = 0

        async def create_turn(
            self,
            conversation: Any,
            tools: Sequence[Mapping[str, Any]],
            *,
            max_tokens: int,
            timeout: float,
        ) -> ModelTurn:
            del conversation, tools, max_tokens, timeout
            self.turns += 1
            if self.turns == 1:
                return ModelTurn(
                    text="",
                    tool_calls=(ToolCall("provider-call-id", "retrieve", {}),),
                    stop_reason="tool_use",
                    usage=ModelUsage(input_tokens=1, output_tokens=1),
                    latency_ms=1.0,
                )
            return await super().create_turn(
                None,
                (),
                max_tokens=1,
                timeout=1.0,
            )

    async def scenario() -> None:
        service = _service(lambda key: ToolClient(), registry=registry)
        response = await service.run(
            PreviewRequest(prompt="private-prompt-canary", learner_id="learner-canary"),
            f"Bearer {_TOKEN}",
        )

        assert response.status == "completed"
        assert len(tool.contexts) == 1
        context = tool.contexts[0]
        assert context.learner_id == "learner-canary"
        assert context.source_scope == "DEFAULT_PLUS_EXTRAS"
        assert context.permissions == frozenset({"read"})
        assert len(context.correlation_id) == 64
        assert context.correlation_id == response.agent_trace[-1]["request_id_hmac"]
        assert context.correlation_id != "provider-call-id"
        serialized = response.model_dump_json()
        assert "private-prompt-canary" not in serialized
        assert "learner-canary" not in serialized
        assert "provider-call-id" not in serialized

    asyncio.run(scenario())


def test_request_validation_forbids_extra_fields() -> None:
    with TestClient(_app(_service(lambda key: _Client()))) as client:
        response = client.post(
            PREVIEW_PATH,
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={"prompt": "question", "unexpected": True},
        )

    assert response.status_code == 422


def test_capacity_overload_returns_retry_after() -> None:
    async def scenario() -> None:
        gate = asyncio.Event()
        service = _service(lambda key: _Client(gate=gate), wait=0.01)
        request = PreviewRequest(prompt="question")
        first = asyncio.create_task(service.run(request, f"Bearer {_TOKEN}"))
        second = asyncio.create_task(service.run(request, f"Bearer {_TOKEN}"))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        try:
            with pytest.raises(Exception) as raised:
                await service.run(request, f"Bearer {_TOKEN}")
            error = raised.value
            assert getattr(error, "status_code", None) == 429
            assert getattr(error, "headers", None) == {"Retry-After": "1"}
        finally:
            gate.set()
            await asyncio.gather(first, second)

    asyncio.run(scenario())


def test_close_failure_is_suppressed_and_still_releases_capacity() -> None:
    created = 0

    def factory(key: str) -> _Client:
        nonlocal created
        del key
        created += 1
        if created == 1:
            return _Client(close_failure=RuntimeError("close-secret-canary"))
        return _Client()

    async def scenario() -> None:
        service = _service(factory, wait=0.01)
        request = PreviewRequest(prompt="question")
        first = await service.run(request, f"Bearer {_TOKEN}")
        second = await service.run(request, f"Bearer {_TOKEN}")

        assert first.status == "completed"
        assert second.status == "completed"
        assert "close-secret-canary" not in first.model_dump_json()
        assert "close-secret-canary" not in second.model_dump_json()

    asyncio.run(scenario())


def test_semaphore_wait_counts_against_total_deadline() -> None:
    async def scenario() -> None:
        gate = asyncio.Event()
        admitted = asyncio.Event()
        created = 0

        def factory(key: str) -> _Client:
            nonlocal created
            del key
            created += 1
            if created == 2:
                admitted.set()
            return _Client(gate=gate)

        limits = PreviewLimits(deadline_seconds=0.1)
        service = _service(factory, limits=limits, wait=0.25)
        request = PreviewRequest(prompt="question")
        authorization = f"Bearer {_TOKEN}"
        first = asyncio.create_task(service.run(request, authorization))
        second = asyncio.create_task(service.run(request, authorization))
        await asyncio.wait_for(admitted.wait(), timeout=1.0)
        result = await service.run(request, authorization)
        assert result.status == "terminated"
        assert result.termination_reason == "deadline_exceeded"
        gate.set()
        await asyncio.gather(first, second)

    asyncio.run(scenario())


def test_request_capacity_release_does_not_release_tool_work_capacity() -> None:
    async def scenario() -> None:
        tool = _BlockingTool()
        created: list[_ToolClient] = []

        def factory(key: str) -> _ToolClient:
            del key
            client = _ToolClient(f"call-{len(created) + 1}")
            created.append(client)
            return client

        service = _service(
            factory,
            limits=PreviewLimits(tool_timeout_seconds=0.05),
            registry=_registry(tool),
        )
        request = PreviewRequest(prompt="question")
        authorization = f"Bearer {_TOKEN}"

        first = asyncio.create_task(service.run(request, authorization))
        second = asyncio.create_task(service.run(request, authorization))
        await _wait_for_tool_count(tool, 2)
        first_result, second_result = await asyncio.gather(first, second)
        assert first_result.termination_reason == "tool_timeout"
        assert second_result.termination_reason == "tool_timeout"
        assert tool.counts() == (2, 2, 2)

        third_result = await service.run(request, authorization)
        assert third_result.termination_reason == "tool_timeout"
        assert tool.counts() == (2, 2, 2)
        assert len(created) == 3
        assert [client.turns for client in created] == [1, 1, 1]
        assert all(client.results == [] for client in created)

        tool.release.set()
        deadline = asyncio.get_running_loop().time() + 1.0
        while tool.counts()[1] != 0:
            if asyncio.get_running_loop().time() >= deadline:
                raise AssertionError("timed-out tool workers did not finish")
            await asyncio.sleep(0.005)

        recovered = await service.run(request, authorization)
        assert recovered.status == "completed"
        assert recovered.tool_call_count == 1
        assert tool.counts() == (3, 0, 2)

    asyncio.run(scenario())


def test_constructor_rejects_relaxed_service_limits() -> None:
    with pytest.raises(ValueError, match="at least 32"):
        PreviewService(
            token="short",
            provider_key="key",
            registry=_registry(),
        )
    with pytest.raises(ValueError, match="frozen at two"):
        PreviewService(
            token=_TOKEN,
            provider_key="key",
            registry=_registry(),
            capacity=3,
        )
    with pytest.raises(ValueError, match="hard limit"):
        PreviewService(
            token=_TOKEN,
            provider_key="key",
            registry=_registry(),
            semaphore_wait_seconds=0.3,
        )
