"""Provider-neutral model contracts and the Anthropic Messages adapter."""

from __future__ import annotations

import importlib
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

MODEL_ID = "claude-opus-5"
MAX_TURN_OUTPUT_TOKENS = 1024


class ProviderErrorCode(StrEnum):
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    AUTH = "auth"
    REJECTED = "rejected"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ProviderError(RuntimeError):
    """Stable provider failure without raw SDK response data."""

    def __init__(
        self,
        code: ProviderErrorCode,
        *,
        retryable: bool,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(code.value)
        self.code = code
        self.retryable = retryable
        self.status_code = status_code
        self.retry_after = retry_after


@dataclass(frozen=True, slots=True)
class ModelUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass(frozen=True, slots=True)
class ToolCall:
    call_id: str
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ModelTurn:
    text: str
    tool_calls: tuple[ToolCall, ...]
    stop_reason: str | None
    usage: ModelUsage
    latency_ms: float
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    call_id: str
    content: str
    is_error: bool = False


@runtime_checkable
class ModelConversation(Protocol):
    """Opaque request-local replay state owned by one LLM adapter."""


@runtime_checkable
class LLMClient(Protocol):
    def new_conversation(self, prompt: str) -> ModelConversation:
        ...

    async def count_tokens(
        self,
        conversation: ModelConversation,
        tools: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> int:
        ...

    async def create_turn(
        self,
        conversation: ModelConversation,
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        timeout: float,
    ) -> ModelTurn:
        ...

    def append_tool_result(
        self,
        conversation: ModelConversation,
        result: ToolExecutionResult,
    ) -> None:
        ...

    async def close(self) -> None:
        ...


class _AnthropicConversation:
    """Anthropic replay payload; never returned through API or trace models."""

    __slots__ = ("messages",)

    def __init__(self, prompt: str) -> None:
        self.messages: list[dict[str, Any]] = [
            {"role": "user", "content": prompt}
        ]


class AnthropicLLMClient:
    """Lazy official-SDK adapter with SDK retries disabled."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Anthropic API key is required")
        self._api_key = api_key
        self._client: Any | None = None
        self._sdk: Any | None = None

    def new_conversation(self, prompt: str) -> ModelConversation:
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("prompt must be non-empty")
        return _AnthropicConversation(prompt)

    async def count_tokens(
        self,
        conversation: ModelConversation,
        tools: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> int:
        state = self._state(conversation)
        client = self._get_client()
        request = self._common_request(state, tools)
        try:
            result = await client.messages.count_tokens(
                **request,
                timeout=timeout,
            )
            return self._parse_token_count(result)
        except Exception as exc:
            raise self._map_error(exc) from None

    async def create_turn(
        self,
        conversation: ModelConversation,
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        timeout: float,
    ) -> ModelTurn:
        if not 1 <= max_tokens <= MAX_TURN_OUTPUT_TOKENS:
            raise ValueError("max_tokens exceeds the M6b hard limit")
        state = self._state(conversation)
        client = self._get_client()
        request = self._common_request(state, tools)
        started = time.perf_counter()
        try:
            message = await client.messages.create(
                **request,
                max_tokens=max_tokens,
                output_config={"effort": "low"},
                timeout=timeout,
            )
            latency_ms = (time.perf_counter() - started) * 1000.0
            turn, replay_blocks = self._parse_message(message, latency_ms)
        except Exception as exc:
            raise self._map_error(exc) from None
        state.messages.append({"role": "assistant", "content": replay_blocks})
        return turn

    def append_tool_result(
        self,
        conversation: ModelConversation,
        result: ToolExecutionResult,
    ) -> None:
        state = self._state(conversation)
        state.messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": result.call_id,
                        "content": result.content,
                        "is_error": result.is_error,
                    }
                ],
            }
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                if self._sdk is None:
                    self._sdk = importlib.import_module("anthropic")
                self._client = self._sdk.AsyncAnthropic(
                    api_key=self._api_key,
                    max_retries=0,
                    timeout=60.0,
                )
            except ProviderError:
                self._client = None
                raise
            except Exception:
                self._client = None
                raise ProviderError(
                    ProviderErrorCode.UNAVAILABLE,
                    retryable=False,
                ) from None
        return self._client

    @staticmethod
    def _state(conversation: ModelConversation) -> _AnthropicConversation:
        if not isinstance(conversation, _AnthropicConversation):
            raise TypeError("conversation belongs to another LLM adapter")
        return conversation

    @staticmethod
    def _common_request(
        conversation: _AnthropicConversation,
        tools: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        return {
            "model": MODEL_ID,
            "messages": conversation.messages,
            "thinking": {"type": "adaptive"},
            "tool_choice": {
                "type": "auto",
                "disable_parallel_tool_use": True,
            },
            "tools": list(tools),
        }

    @staticmethod
    def _parse_token_count(result: Any) -> int:
        value = getattr(result, "input_tokens", None)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise TypeError("invalid token count")
        return value

    @staticmethod
    def _nonneg_int(value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise TypeError("invalid usage")
        return value

    @classmethod
    def _parse_message(cls, message: Any, latency_ms: float) -> tuple[ModelTurn, list[dict[str, Any]]]:
        content = getattr(message, "content", None)
        if content is None or isinstance(content, (str, bytes, bytearray, Mapping)):
            raise TypeError("invalid message content")
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        replay_blocks: list[dict[str, Any]] = []
        for block in content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text = getattr(block, "text", None)
                if not isinstance(text, str):
                    raise TypeError("invalid text block")
                text_parts.append(text)
                replay_blocks.append({"type": "text", "text": text})
            elif block_type == "tool_use":
                arguments = getattr(block, "input", None)
                if not isinstance(arguments, Mapping):
                    raise TypeError("invalid tool block")
                call_id = getattr(block, "id", None)
                name = getattr(block, "name", None)
                if not isinstance(call_id, str) or not isinstance(name, str):
                    raise TypeError("invalid tool block")
                normalized_arguments = dict(arguments)
                call = ToolCall(
                    call_id=call_id,
                    name=name,
                    arguments=normalized_arguments,
                )
                calls.append(call)
                replay_blocks.append(
                    {
                        "type": "tool_use",
                        "id": call.call_id,
                        "name": call.name,
                        "input": normalized_arguments,
                    }
                )
            elif block_type == "thinking":
                thinking = getattr(block, "thinking", None)
                signature = getattr(block, "signature", None)
                if not isinstance(thinking, str) or not isinstance(signature, str):
                    raise TypeError("invalid thinking block")
                replay_blocks.append(
                    {
                        "type": "thinking",
                        "thinking": thinking,
                        "signature": signature,
                    }
                )
            elif block_type == "redacted_thinking":
                data = getattr(block, "data", None)
                if not isinstance(data, str):
                    raise TypeError("invalid redacted thinking block")
                replay_blocks.append({"type": "redacted_thinking", "data": data})
        usage = getattr(message, "usage", None)
        if usage is None:
            raise TypeError("invalid usage")
        stop_reason = getattr(message, "stop_reason", None)
        if stop_reason is not None and not isinstance(stop_reason, str):
            raise TypeError("invalid stop reason")
        turn = ModelTurn(
            text="".join(text_parts),
            tool_calls=tuple(calls),
            stop_reason=stop_reason,
            usage=ModelUsage(
                input_tokens=cls._nonneg_int(getattr(usage, "input_tokens", 0)),
                output_tokens=cls._nonneg_int(getattr(usage, "output_tokens", 0)),
                cache_creation_input_tokens=cls._nonneg_int(
                    getattr(usage, "cache_creation_input_tokens", 0)
                ),
                cache_read_input_tokens=cls._nonneg_int(
                    getattr(usage, "cache_read_input_tokens", 0)
                ),
            ),
            latency_ms=latency_ms,
            request_id=getattr(message, "_request_id", None),
        )
        return turn, replay_blocks

    def _map_error(self, exc: Exception) -> ProviderError:
        if isinstance(exc, ProviderError):
            return exc
        sdk = self._sdk
        if sdk is None:
            return ProviderError(ProviderErrorCode.UNAVAILABLE, retryable=False)
        if isinstance(exc, sdk.APITimeoutError):
            return ProviderError(ProviderErrorCode.TIMEOUT, retryable=True)
        if isinstance(exc, sdk.APIConnectionError):
            return ProviderError(ProviderErrorCode.CONNECTION, retryable=True)
        if isinstance(exc, sdk.AuthenticationError):
            return ProviderError(
                ProviderErrorCode.AUTH,
                retryable=False,
                status_code=401,
            )
        if isinstance(exc, sdk.APIStatusError):
            status = int(getattr(exc, "status_code", 0))
            retryable = status in {408, 409, 429} or status >= 500
            retry_after = self._retry_after(exc) if retryable else None
            if status == 429:
                code = ProviderErrorCode.RATE_LIMIT
            elif status >= 500:
                code = ProviderErrorCode.UNAVAILABLE
            else:
                code = ProviderErrorCode.REJECTED
            return ProviderError(
                code,
                retryable=retryable,
                status_code=status or None,
                retry_after=retry_after,
            )
        return ProviderError(ProviderErrorCode.UNKNOWN, retryable=False)

    @staticmethod
    def _retry_after(exc: Any) -> float | None:
        try:
            raw = exc.response.headers.get("retry-after")
            value = float(raw)
        except (AttributeError, TypeError, ValueError):
            return None
        return value if value >= 0 else None


__all__ = [
    "AnthropicLLMClient",
    "LLMClient",
    "MAX_TURN_OUTPUT_TOKENS",
    "MODEL_ID",
    "ModelConversation",
    "ModelTurn",
    "ModelUsage",
    "ProviderError",
    "ProviderErrorCode",
    "ToolCall",
    "ToolExecutionResult",
]
