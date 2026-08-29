"""Budget-bounded read-only orchestration for the M6b Agent Preview."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import random
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from .llm_client import (
    MAX_TURN_OUTPUT_TOKENS,
    MODEL_ID,
    LLMClient,
    ModelUsage,
    ProviderError,
    ProviderErrorCode,
    ToolExecutionResult,
)
from .protocols import SourceIdentity, ToolContext, ToolResult
from .tool_registry import ToolRegistry

_INPUT_USD_PER_MILLION = 15.0
_OUTPUT_USD_PER_MILLION = 75.0


@dataclass(frozen=True, slots=True)
class PreviewLimits:
    """M6b limits; callers may only provide values at or below these defaults."""

    deadline_seconds: float = 45.0
    model_timeout_seconds: float = 20.0
    token_count_timeout_seconds: float = 3.0
    tool_timeout_seconds: float = 2.0
    max_model_turns: int = 4
    max_tool_calls: int = 3
    max_input_tokens: int = 12_000
    max_output_tokens: int = 4_096
    max_turn_output_tokens: int = MAX_TURN_OUTPUT_TOKENS
    max_cost_usd: float = 0.20
    max_prompt_bytes: int = 8 * 1024
    max_tool_result_bytes: int = 12 * 1024
    max_total_tool_result_bytes: int = 24 * 1024
    max_answer_bytes: int = 8 * 1024
    max_retries: int = 1
    retry_min_seconds: float = 0.2
    retry_max_seconds: float = 0.5
    retry_after_cap_seconds: float = 2.0


@dataclass(frozen=True, slots=True)
class PreviewUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class PreviewResult:
    status: Literal["completed", "terminated"]
    termination_reason: str
    answer: str | None
    sources: tuple[SourceIdentity, ...]
    agent_trace: tuple[Mapping[str, Any], ...]
    usage: PreviewUsage
    model_turn_count: int
    tool_call_count: int


@dataclass(slots=True)
class _RunState:
    started: float
    usage: ModelUsage = field(default_factory=ModelUsage)
    turns: int = 0
    calls: int = 0
    tool_result_bytes: int = 0
    sources: list[SourceIdentity] = field(default_factory=list)
    fingerprints: set[str] = field(default_factory=set)
    trace: list[Mapping[str, Any]] = field(default_factory=list)




class ToolWorkLimiter:
    """Bound synchronous preview work until the worker actually finishes."""

    def __init__(self, capacity: int = 2) -> None:
        if capacity != 2:
            raise ValueError("preview tool-work capacity is frozen at two")
        self._semaphore = asyncio.Semaphore(capacity)
        self._workers: set[asyncio.Task[Any]] = set()

    async def execute(
        self,
        function: Callable[..., Any],
        *args: Any,
        timeout: float,
    ) -> Any:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
        try:
            worker = asyncio.create_task(asyncio.to_thread(function, *args))
        except BaseException:
            self._semaphore.release()
            raise
        self._workers.add(worker)
        worker.add_done_callback(self._worker_done)
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError
        return await asyncio.wait_for(asyncio.shield(worker), timeout=remaining)

    def _worker_done(self, worker: asyncio.Task[Any]) -> None:
        self._workers.discard(worker)
        try:
            worker.exception()
        except (asyncio.CancelledError, Exception):
            pass
        self._semaphore.release()

class PreviewAgent:
    """Run one request-local native tool-use conversation with hard limits."""

    def __init__(
        self,
        client: LLMClient,
        registry: ToolRegistry,
        *,
        limits: PreviewLimits = PreviewLimits(),
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        jitter: Callable[[float, float], float] = random.uniform,
        cancelled: Callable[[], bool] = lambda: False,
        tool_work_limiter: ToolWorkLimiter | None = None,
    ) -> None:
        self._client = client
        self._registry = registry
        self._limits = limits
        self._monotonic = monotonic
        self._sleep = sleep
        self._jitter = jitter
        self._cancelled = cancelled
        self._tool_work_limiter = tool_work_limiter or ToolWorkLimiter()
        _validate_limits(limits)

    @staticmethod
    def validate_limits(limits: PreviewLimits) -> None:
        """Validate limit overrides without constructing a provider client."""
        _validate_limits(limits)

    async def run(self, prompt: str, context: ToolContext) -> PreviewResult:
        state = _RunState(started=self._monotonic())
        if not isinstance(prompt, str) or not prompt:
            return self._terminated(state, "invalid_prompt")
        if len(prompt.encode("utf-8")) > self._limits.max_prompt_bytes:
            return self._terminated(state, "prompt_budget")
        if self._is_cancelled(context):
            return self._terminated(state, "cancelled")

        conversation = self._client.new_conversation(prompt)
        tools = self._registry.schemas()
        while state.turns < self._limits.max_model_turns:
            guard = self._guard(state, context)
            if guard:
                return self._terminated(state, guard)

            count_timeout = self._operation_timeout(
                state, self._limits.token_count_timeout_seconds
            )
            if count_timeout <= 0:
                return self._terminated(state, "deadline_exceeded")
            try:
                input_tokens = await asyncio.wait_for(
                    self._client.count_tokens(
                        conversation,
                        tools,
                        timeout=count_timeout,
                    ),
                    timeout=count_timeout,
                )
            except asyncio.CancelledError:
                raise
            except ProviderError as exc:
                return self._terminated(state, _provider_reason(exc.code))
            except TimeoutError:
                return self._terminated(state, "provider_timeout")
            except Exception:
                return self._terminated(state, "provider_unavailable")

            budget_guard = self._reservation_guard(state, input_tokens)
            if budget_guard:
                return self._terminated(state, budget_guard)

            turn, retries, failure = await self._create_turn(
                conversation,
                tools,
                state,
                context,
            )
            if failure:
                return self._terminated(state, failure)
            assert turn is not None
            state.turns += 1
            state.usage = _add_usage(state.usage, turn.usage)
            state.trace.append(
                {
                    "schema_version": "m6b-agent-trace-v1",
                    "turn": state.turns,
                    "model": MODEL_ID,
                    "stop_reason": turn.stop_reason or "missing",
                    "input_tokens": turn.usage.input_tokens,
                    "output_tokens": turn.usage.output_tokens,
                    "latency_ms": round(max(0.0, turn.latency_ms), 3),
                    "retries": retries,
                }
            )
            if state.usage.input_tokens > self._limits.max_input_tokens:
                return self._terminated(state, "input_token_budget")
            if state.usage.output_tokens > self._limits.max_output_tokens:
                return self._terminated(state, "output_token_budget")
            if self._estimated_cost(state.usage) > self._limits.max_cost_usd:
                return self._terminated(state, "cost_budget")

            if len(turn.tool_calls) > 1:
                return self._terminated(state, "multiple_tool_calls")
            if turn.stop_reason == "tool_use":
                if len(turn.tool_calls) != 1:
                    return self._terminated(state, "unexpected_stop_reason")
                if state.calls >= self._limits.max_tool_calls:
                    return self._terminated(state, "max_tool_calls")
                reason = await self._execute_tool(
                    conversation,
                    turn.tool_calls[0],
                    context,
                    state,
                )
                if reason:
                    return self._terminated(state, reason)
                continue
            if turn.tool_calls:
                return self._terminated(state, "unexpected_stop_reason")
            if turn.stop_reason == "end_turn":
                if not turn.text:
                    return self._terminated(state, "unexpected_stop_reason")
                if len(turn.text.encode("utf-8")) > self._limits.max_answer_bytes:
                    return self._terminated(state, "answer_budget")
                return self._completed(state, turn.text)
            return self._terminated(state, _stop_reason(turn.stop_reason))

        return self._terminated(state, "max_turns")

    async def _create_turn(
        self,
        conversation: Any,
        tools: Sequence[Mapping[str, Any]],
        state: _RunState,
        context: ToolContext,
    ) -> tuple[Any | None, int, str | None]:
        retries = 0
        while True:
            guard = self._guard(state, context)
            if guard:
                return None, retries, guard
            timeout = self._operation_timeout(state, self._limits.model_timeout_seconds)
            if timeout <= 0:
                return None, retries, "deadline_exceeded"
            try:
                turn = await asyncio.wait_for(
                    self._client.create_turn(
                        conversation,
                        tools,
                        max_tokens=self._limits.max_turn_output_tokens,
                        timeout=timeout,
                    ),
                    timeout=timeout,
                )
                return turn, retries, None
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                error = ProviderError(ProviderErrorCode.TIMEOUT, retryable=True)
            except ProviderError as exc:
                error = exc
            except Exception:
                return None, retries, "provider_unavailable"
            if not error.retryable or retries >= self._limits.max_retries:
                return None, retries, _provider_reason(error.code)
            delay = self._retry_delay(error)
            if delay >= self._remaining(state):
                return None, retries, "deadline_exceeded"
            retries += 1
            await self._sleep(delay)
            guard = self._guard(state, context)
            if guard:
                return None, retries, guard

    async def _execute_tool(
        self,
        conversation: Any,
        call: Any,
        context: ToolContext,
        state: _RunState,
    ) -> str | None:
        guard = self._guard(state, context)
        if guard:
            return guard
        fingerprint = _tool_fingerprint(call.name, call.arguments)
        if fingerprint in state.fingerprints:
            return "duplicate_tool_call"
        state.fingerprints.add(fingerprint)

        allowance = self._operation_timeout(state, self._limits.tool_timeout_seconds)
        if allowance <= 0:
            return "deadline_exceeded"
        try:
            result = await self._tool_work_limiter.execute(
                self._registry.execute,
                call.name,
                context,
                call.arguments,
                timeout=allowance,
            )
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            return "tool_timeout"
        except Exception:
            return "tool_failed"
        if self._remaining(state) <= 0:
            return "deadline_exceeded"

        state.calls += 1
        reason = _tool_error_reason(result)
        payload = _tool_payload(result)
        try:
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError, OverflowError):
            return "tool_failed"
        result_bytes = len(encoded.encode("utf-8"))
        state.trace.append(
            {
                "schema_version": "m6b-agent-trace-v1",
                "turn": state.turns,
                "tool": call.name if call.name in self._registry_names() else "unknown",
                "parameter_hash": fingerprint,
                "result_status": "error" if result.error else "ok",
                "error_code": result.error.code if result.error else None,
                "original_result_bytes": result_bytes,
                "returned_result_bytes": result_bytes,
            }
        )
        if result_bytes > self._limits.max_tool_result_bytes:
            return "tool_result_budget"
        if state.tool_result_bytes + result_bytes > self._limits.max_total_tool_result_bytes:
            return "tool_result_budget"
        if reason:
            return reason

        state.tool_result_bytes += result_bytes
        for source in result.sources:
            if source not in state.sources:
                state.sources.append(source)
        self._client.append_tool_result(
            conversation,
            ToolExecutionResult(call_id=call.call_id, content=encoded),
        )
        return None

    def _reservation_guard(self, state: _RunState, input_tokens: int) -> str | None:
        if input_tokens < 0:
            return "input_token_budget"
        if state.usage.input_tokens + input_tokens > self._limits.max_input_tokens:
            return "input_token_budget"
        if (
            state.usage.output_tokens + self._limits.max_turn_output_tokens
            > self._limits.max_output_tokens
        ):
            return "output_token_budget"
        reserved = ModelUsage(
            input_tokens=state.usage.input_tokens + input_tokens,
            output_tokens=state.usage.output_tokens
            + self._limits.max_turn_output_tokens,
        )
        if self._estimated_cost(reserved) > self._limits.max_cost_usd:
            return "cost_budget"
        return None

    def _retry_delay(self, error: ProviderError) -> float:
        if error.retry_after is not None:
            return min(error.retry_after, self._limits.retry_after_cap_seconds)
        return self._jitter(
            self._limits.retry_min_seconds,
            self._limits.retry_max_seconds,
        )

    def _operation_timeout(self, state: _RunState, limit: float) -> float:
        return max(0.0, min(limit, self._remaining(state)))

    def _remaining(self, state: _RunState) -> float:
        return self._limits.deadline_seconds - (self._monotonic() - state.started)

    def _guard(self, state: _RunState, context: ToolContext) -> str | None:
        if self._is_cancelled(context):
            return "cancelled"
        if self._remaining(state) <= 0:
            return "deadline_exceeded"
        return None

    def _is_cancelled(self, context: ToolContext) -> bool:
        return context.cancelled or self._cancelled()

    def _registry_names(self) -> frozenset[str]:
        return frozenset(item["name"] for item in self._registry.schemas())

    def _estimated_cost(self, usage: ModelUsage) -> float:
        return (
            usage.input_tokens * _INPUT_USD_PER_MILLION
            + usage.output_tokens * _OUTPUT_USD_PER_MILLION
        ) / 1_000_000

    def _completed(self, state: _RunState, answer: str) -> PreviewResult:
        return self._result(state, "completed", "completed", answer)

    def _terminated(self, state: _RunState, reason: str) -> PreviewResult:
        return self._result(state, "terminated", reason, None)

    def _result(
        self,
        state: _RunState,
        status: Literal["completed", "terminated"],
        reason: str,
        answer: str | None,
    ) -> PreviewResult:
        usage = PreviewUsage(
            input_tokens=state.usage.input_tokens,
            output_tokens=state.usage.output_tokens,
            cache_creation_input_tokens=state.usage.cache_creation_input_tokens,
            cache_read_input_tokens=state.usage.cache_read_input_tokens,
            estimated_cost_usd=round(self._estimated_cost(state.usage), 8),
        )
        return PreviewResult(
            status=status,
            termination_reason=reason,
            answer=answer,
            sources=tuple(state.sources),
            agent_trace=tuple(state.trace),
            usage=usage,
            model_turn_count=state.turns,
            tool_call_count=state.calls,
        )


def _validate_limits(limits: PreviewLimits) -> None:
    """Reject non-finite, non-positive, or relaxed hard limits."""
    defaults = PreviewLimits()
    for name in (
        "deadline_seconds",
        "model_timeout_seconds",
        "token_count_timeout_seconds",
        "tool_timeout_seconds",
        "max_cost_usd",
        "retry_min_seconds",
        "retry_max_seconds",
        "retry_after_cap_seconds",
    ):
        value = getattr(limits, name)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
        if value > getattr(defaults, name):
            raise ValueError(f"{name} cannot exceed the hard limit")
    for name in (
        "max_model_turns",
        "max_tool_calls",
        "max_input_tokens",
        "max_output_tokens",
        "max_turn_output_tokens",
        "max_prompt_bytes",
        "max_tool_result_bytes",
        "max_total_tool_result_bytes",
        "max_answer_bytes",
    ):
        value = getattr(limits, name)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
        if value > getattr(defaults, name):
            raise ValueError(f"{name} cannot exceed the hard limit")
    if isinstance(limits.max_retries, bool) or not isinstance(limits.max_retries, int):
        raise ValueError("max_retries must be an integer")
    if limits.max_retries < 0 or limits.max_retries > defaults.max_retries:
        raise ValueError("max_retries cannot exceed the hard limit")
    if limits.retry_min_seconds < defaults.retry_min_seconds:
        raise ValueError("retry_min_seconds cannot be below the frozen minimum")
    if limits.retry_max_seconds < limits.retry_min_seconds:
        raise ValueError("retry_max_seconds cannot be below retry_min_seconds")
    if limits.max_turn_output_tokens > limits.max_output_tokens:
        raise ValueError("turn output limit cannot exceed total output limit")
    if limits.max_tool_result_bytes > limits.max_total_tool_result_bytes:
        raise ValueError("individual tool result cannot exceed the total result limit")


def _add_usage(left: ModelUsage, right: ModelUsage) -> ModelUsage:
    return ModelUsage(
        input_tokens=left.input_tokens + right.input_tokens,
        output_tokens=left.output_tokens + right.output_tokens,
        cache_creation_input_tokens=(
            left.cache_creation_input_tokens + right.cache_creation_input_tokens
        ),
        cache_read_input_tokens=(
            left.cache_read_input_tokens + right.cache_read_input_tokens
        ),
    )


def _tool_fingerprint(name: str, arguments: Mapping[str, Any]) -> str:
    normalized = json.dumps(
        {"name": name, "arguments": dict(arguments)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _tool_payload(result: ToolResult) -> dict[str, Any]:
    if result.error:
        return {
            "error": {
                "code": result.error.code,
                "message": result.error.message,
                "retryable": result.error.retryable,
            }
        }
    return {"data": result.data}


def _tool_error_reason(result: ToolResult) -> str | None:
    if result.error is None:
        return None
    return {
        "TOOL_UNKNOWN": "unknown_tool",
        "TOOL_NOT_AUTHORIZED": "unauthorized_tool",
        "TOOL_ARGUMENTS_INVALID": "invalid_tool_arguments",
    }.get(result.error.code, "tool_failed")


def _provider_reason(code: ProviderErrorCode) -> str:
    return {
        ProviderErrorCode.AUTH: "provider_auth_failed",
        ProviderErrorCode.REJECTED: "provider_rejected",
        ProviderErrorCode.TIMEOUT: "provider_timeout",
        ProviderErrorCode.CONNECTION: "provider_unavailable",
        ProviderErrorCode.RATE_LIMIT: "provider_unavailable",
        ProviderErrorCode.UNAVAILABLE: "provider_unavailable",
        ProviderErrorCode.UNKNOWN: "provider_unavailable",
    }[code]


def _stop_reason(stop_reason: str | None) -> str:
    if stop_reason == "refusal":
        return "provider_refusal"
    if stop_reason == "max_tokens":
        return "output_token_budget"
    return "unexpected_stop_reason"


__all__ = [
    "PreviewAgent",
    "PreviewLimits",
    "PreviewResult",
    "PreviewUsage",
    "ToolWorkLimiter",
]
