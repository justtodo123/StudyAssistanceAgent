"""M6b tests for the provider-neutral Anthropic Messages adapter."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.llm_client import (
    MAX_TURN_OUTPUT_TOKENS,
    MODEL_ID,
    AnthropicLLMClient,
    ProviderError,
    ProviderErrorCode,
    ToolExecutionResult,
)


pytestmark = pytest.mark.m6b


class _APIError(Exception):
    pass


class _APIConnectionError(_APIError):
    pass


class _APITimeoutError(_APIConnectionError):
    pass


class _AuthenticationError(_APIError):
    pass


class _APIStatusError(_APIError):
    def __init__(
        self,
        status_code: int,
        retry_after: str | None = None,
        *,
        message: str = "raw-provider-canary",
        headers: dict[str, str] | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        response_headers = dict(headers or {})
        if retry_after is not None:
            response_headers["retry-after"] = retry_after
        self.response = SimpleNamespace(
            headers=response_headers,
            text=body,
        )
        self.body = body


class _Messages:
    def __init__(self) -> None:
        self.count_requests: list[dict[str, Any]] = []
        self.create_requests: list[dict[str, Any]] = []
        self.count_result: Any = SimpleNamespace(input_tokens=321)
        self.create_result: Any = SimpleNamespace(
            content=[],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=0, output_tokens=0),
            _request_id=None,
        )
        self.count_failure: BaseException | None = None
        self.create_failure: BaseException | None = None

    async def count_tokens(self, **request: Any) -> Any:
        self.count_requests.append(request)
        if self.count_failure is not None:
            raise self.count_failure
        return self.count_result

    async def create(self, **request: Any) -> Any:
        self.create_requests.append(request)
        if self.create_failure is not None:
            raise self.create_failure
        return self.create_result


class _Client:
    def __init__(self) -> None:
        self.messages = _Messages()
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _sdk() -> Any:
    return SimpleNamespace(
        APIError=_APIError,
        APIConnectionError=_APIConnectionError,
        APITimeoutError=_APITimeoutError,
        AuthenticationError=_AuthenticationError,
        APIStatusError=_APIStatusError,
    )


def _adapter() -> tuple[AnthropicLLMClient, _Client]:
    adapter = AnthropicLLMClient("server-side-test-key")
    client = _Client()
    adapter._sdk = _sdk()
    adapter._client = client
    return adapter, client


def _tools() -> tuple[dict[str, Any], ...]:
    return (
        {
            "type": "custom",
            "name": "retrieve",
            "description": "retrieve",
            "strict": True,
            "input_schema": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    )


def test_count_and_create_share_the_frozen_request_contract() -> None:
    adapter, client = _adapter()
    conversation = adapter.new_conversation("private prompt")
    client.messages.create_result = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="safe answer")],
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=22,
            output_tokens=7,
            cache_creation_input_tokens=3,
            cache_read_input_tokens=4,
        ),
        _request_id="provider-request-id",
    )

    count = asyncio.run(adapter.count_tokens(conversation, _tools(), timeout=2.5))
    turn = asyncio.run(
        adapter.create_turn(
            conversation,
            _tools(),
            max_tokens=MAX_TURN_OUTPUT_TOKENS,
            timeout=7.5,
        )
    )

    assert count == 321
    count_request = client.messages.count_requests[0]
    create_request = client.messages.create_requests[0]
    for request in (count_request, create_request):
        assert request["model"] == MODEL_ID
        assert request["thinking"] == {"type": "adaptive"}
        assert request["tool_choice"] == {
            "type": "auto",
            "disable_parallel_tool_use": True,
        }
        assert request["tools"] == list(_tools())
    assert count_request["timeout"] == 2.5
    assert "max_tokens" not in count_request
    assert "output_config" not in count_request
    assert create_request["timeout"] == 7.5
    assert create_request["max_tokens"] == MAX_TURN_OUTPUT_TOKENS
    assert create_request["output_config"] == {"effort": "low"}
    assert turn.text == "safe answer"
    assert turn.stop_reason == "end_turn"
    assert turn.request_id == "provider-request-id"
    assert turn.usage.input_tokens == 22
    assert turn.usage.output_tokens == 7
    assert turn.usage.cache_creation_input_tokens == 3
    assert turn.usage.cache_read_input_tokens == 4


def test_native_blocks_are_normalized_and_fully_replayed() -> None:
    adapter, client = _adapter()
    conversation = adapter.new_conversation("prompt")
    client.messages.create_result = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="thinking",
                thinking="private reasoning",
                signature="signed",
            ),
            SimpleNamespace(type="text", text="before "),
            SimpleNamespace(
                type="tool_use",
                id="call-1",
                name="retrieve",
                input={"question": "process"},
            ),
            SimpleNamespace(type="redacted_thinking", data="opaque"),
            SimpleNamespace(type="text", text="after"),
        ],
        stop_reason="tool_use",
        usage=SimpleNamespace(input_tokens=10, output_tokens=11),
        _request_id=None,
    )

    turn = asyncio.run(
        adapter.create_turn(conversation, _tools(), max_tokens=128, timeout=1.0)
    )
    adapter.append_tool_result(
        conversation,
        ToolExecutionResult(call_id="call-1", content='{"results":[]}'),
    )
    asyncio.run(adapter.count_tokens(conversation, _tools(), timeout=1.0))

    assert turn.text == "before after"
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].call_id == "call-1"
    assert turn.tool_calls[0].name == "retrieve"
    assert turn.tool_calls[0].arguments == {"question": "process"}
    replay = client.messages.count_requests[0]["messages"]
    assert replay[1] == {
        "role": "assistant",
        "content": [
            {
                "type": "thinking",
                "thinking": "private reasoning",
                "signature": "signed",
            },
            {"type": "text", "text": "before "},
            {
                "type": "tool_use",
                "id": "call-1",
                "name": "retrieve",
                "input": {"question": "process"},
            },
            {"type": "redacted_thinking", "data": "opaque"},
            {"type": "text", "text": "after"},
        ],
    }
    assert replay[2] == {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call-1",
                "content": '{"results":[]}',
                "is_error": False,
            }
        ],
    }


def test_provider_errors_are_stable_typed_and_sanitized() -> None:
    adapter, client = _adapter()
    conversation = adapter.new_conversation("prompt")
    client.messages.create_failure = _APIStatusError(429, "1.25")

    with pytest.raises(ProviderError) as raised:
        asyncio.run(
            adapter.create_turn(conversation, _tools(), max_tokens=128, timeout=1.0)
        )

    error = raised.value
    assert error.code is ProviderErrorCode.RATE_LIMIT
    assert error.retryable is True
    assert error.status_code == 429
    assert error.retry_after == 1.25
    assert str(error) == "rate_limit"
    assert "raw-provider-canary" not in str(error)


def test_raw_provider_exception_metadata_is_not_exposed() -> None:
    exception_canary = "provider-exception-private-canary"
    header_canary = "provider-header-private-canary"
    body_canary = "provider-body-private-canary"
    adapter, client = _adapter()
    client.messages.create_failure = _APIStatusError(
        529,
        message=exception_canary,
        headers={"x-provider-private": header_canary},
        body={"error": body_canary},
    )

    with pytest.raises(ProviderError) as raised:
        asyncio.run(
            adapter.create_turn(
                adapter.new_conversation("prompt"),
                _tools(),
                max_tokens=128,
                timeout=1.0,
            )
        )

    error = raised.value
    assert error.code is ProviderErrorCode.UNAVAILABLE
    assert error.retryable is True
    assert error.status_code == 529
    assert error.retry_after is None
    serialized = str(error)
    assert exception_canary not in serialized
    assert header_canary not in serialized
    assert body_canary not in serialized
    assert exception_canary not in error.__dict__
    assert header_canary not in str(error.__dict__)
    assert body_canary not in str(error.__dict__)


@pytest.mark.parametrize(
    ("failure", "code", "retryable"),
    [
        (_APITimeoutError(), ProviderErrorCode.TIMEOUT, True),
        (_APIConnectionError(), ProviderErrorCode.CONNECTION, True),
        (_AuthenticationError(), ProviderErrorCode.AUTH, False),
        (_APIStatusError(400), ProviderErrorCode.REJECTED, False),
        (_APIStatusError(529), ProviderErrorCode.UNAVAILABLE, True),
        (_APIError(), ProviderErrorCode.UNKNOWN, False),
    ],
)
def test_provider_exception_mapping(
    failure: Exception,
    code: ProviderErrorCode,
    retryable: bool,
) -> None:
    adapter, client = _adapter()
    client.messages.count_failure = failure

    with pytest.raises(ProviderError) as raised:
        asyncio.run(
            adapter.count_tokens(
                adapter.new_conversation("prompt"),
                _tools(),
                timeout=1.0,
            )
        )

    assert raised.value.code is code
    assert raised.value.retryable is retryable


def test_cancellation_is_not_mapped_to_provider_failure() -> None:
    adapter, client = _adapter()
    client.messages.count_failure = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            adapter.count_tokens(
                adapter.new_conversation("prompt"),
                _tools(),
                timeout=1.0,
            )
        )


def test_adapter_rejects_invalid_limits_and_foreign_conversations() -> None:
    adapter, _ = _adapter()
    conversation = adapter.new_conversation("prompt")

    with pytest.raises(ValueError, match="hard limit"):
        asyncio.run(
            adapter.create_turn(
                conversation,
                _tools(),
                max_tokens=MAX_TURN_OUTPUT_TOKENS + 1,
                timeout=1.0,
            )
        )
    with pytest.raises(TypeError, match="another LLM adapter"):
        asyncio.run(adapter.count_tokens(object(), _tools(), timeout=1.0))
    with pytest.raises(ValueError, match="non-empty"):
        adapter.new_conversation("")


def test_close_releases_the_lazy_client() -> None:
    adapter, client = _adapter()

    asyncio.run(adapter.close())
    asyncio.run(adapter.close())

    assert client.closed is True
    assert adapter._client is None


def test_sdk_client_initialization_failure_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    canary = "sdk-init-private-canary"

    class _BrokenSDK:
        def AsyncAnthropic(self, **kwargs: Any) -> Any:
            raise RuntimeError(canary)

    adapter = AnthropicLLMClient("server-side-test-key")
    monkeypatch.setattr("app.llm_client.importlib.import_module", lambda name: _BrokenSDK())

    with pytest.raises(ProviderError) as raised:
        asyncio.run(
            adapter.count_tokens(
                adapter.new_conversation("prompt"),
                _tools(),
                timeout=1.0,
            )
        )

    error = raised.value
    assert error.code is ProviderErrorCode.UNAVAILABLE
    assert error.retryable is False
    assert canary not in str(error)
    assert canary not in str(error.__dict__)
    assert adapter._client is None


@pytest.mark.parametrize(
    "count_result",
    [
        SimpleNamespace(),
        SimpleNamespace(input_tokens="12"),
        SimpleNamespace(input_tokens=-1),
        SimpleNamespace(input_tokens=True),
        {"input_tokens": 12},
        None,
    ],
)
def test_token_count_structure_errors_are_stable(count_result: Any) -> None:
    adapter, client = _adapter()
    client.messages.count_result = count_result

    with pytest.raises(ProviderError) as raised:
        asyncio.run(
            adapter.count_tokens(
                adapter.new_conversation("prompt"),
                _tools(),
                timeout=1.0,
            )
        )

    assert raised.value.code is ProviderErrorCode.UNKNOWN
    assert raised.value.retryable is False
    assert "input_tokens" not in str(raised.value)


@pytest.mark.parametrize(
    "create_result",
    [
        SimpleNamespace(
            content="provider-content-canary",
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        ),
        SimpleNamespace(
            content=[SimpleNamespace(type="text", text={"secret": "provider-text-canary"})],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        ),
        SimpleNamespace(
            content=[SimpleNamespace(type="tool_use", id="call-1", name="retrieve", input="bad")],
            stop_reason="tool_use",
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        ),
        SimpleNamespace(
            content=[SimpleNamespace(type="text", text="ok")],
            stop_reason="end_turn",
            usage=None,
        ),
        SimpleNamespace(
            content=[SimpleNamespace(type="text", text="ok")],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens="1", output_tokens=1),
        ),
    ],
)
def test_message_block_and_usage_parse_errors_are_sanitized(create_result: Any) -> None:
    adapter, client = _adapter()
    client.messages.create_result = create_result
    conversation = adapter.new_conversation("private prompt")

    with pytest.raises(ProviderError) as raised:
        asyncio.run(
            adapter.create_turn(conversation, _tools(), max_tokens=128, timeout=1.0)
        )

    error = raised.value
    assert error.code is ProviderErrorCode.UNKNOWN
    assert error.retryable is False
    serialized = str(error)
    assert "provider-content-canary" not in serialized
    assert "provider-text-canary" not in serialized
    assert "private prompt" not in serialized
    assert conversation.messages == [{"role": "user", "content": "private prompt"}]

