"""M6b tests for the bounded read-only preview loop."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest

from app.llm_client import (
    ModelTurn,
    ModelUsage,
    ProviderError,
    ProviderErrorCode,
    ToolCall,
    ToolExecutionResult,
)
from app.preview_agent import PreviewAgent, PreviewLimits, ToolWorkLimiter
from app.protocols import SourceIdentity, ToolContext, ToolError, ToolResult, ToolSpec
from app.tool_registry import ToolRegistry


pytestmark = pytest.mark.m6b


@dataclass
class _Conversation:
    prompt: str
    results: list[ToolExecutionResult]


class _Client:
    def __init__(
        self,
        turns: Sequence[ModelTurn | BaseException],
        *,
        token_counts: Sequence[int | BaseException] = (100,),
    ) -> None:
        self.turns = list(turns)
        self.token_counts = list(token_counts)
        self.create_calls = 0
        self.count_calls = 0
        self.conversation: _Conversation | None = None

    def new_conversation(self, prompt: str) -> _Conversation:
        self.conversation = _Conversation(prompt, [])
        return self.conversation

    async def count_tokens(
        self,
        conversation: Any,
        tools: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> int:
        del conversation, tools, timeout
        index = min(self.count_calls, len(self.token_counts) - 1)
        self.count_calls += 1
        result = self.token_counts[index]
        if isinstance(result, BaseException):
            raise result
        return result

    async def create_turn(
        self,
        conversation: Any,
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        timeout: float,
    ) -> ModelTurn:
        del conversation, tools, max_tokens, timeout
        index = self.create_calls
        self.create_calls += 1
        result = self.turns[index]
        if isinstance(result, BaseException):
            raise result
        return result

    def append_tool_result(
        self,
        conversation: _Conversation,
        result: ToolExecutionResult,
    ) -> None:
        conversation.results.append(result)

    async def close(self) -> None:
        return None


class _Tool:
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

    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        context: ToolContext,
        arguments: Mapping[str, Any],
    ) -> ToolResult:
        self.calls += 1
        return ToolResult(
            data={"answer": f"result:{arguments['question']}"},
            correlation_id=context.correlation_id,
        )


class _ContextTool(_Tool):
    def __init__(self, result: ToolResult | None = None) -> None:
        super().__init__()
        self.result = result
        self.contexts: list[ToolContext] = []

    def execute(
        self,
        context: ToolContext,
        arguments: Mapping[str, Any],
    ) -> ToolResult:
        self.contexts.append(context)
        if self.result is not None:
            self.calls += 1
            return ToolResult(
                data=self.result.data,
                sources=self.result.sources,
                error=self.result.error,
                side_effect=self.result.side_effect,
                correlation_id=context.correlation_id,
            )
        return super().execute(context, arguments)


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
        with self._lock:
            self.started += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if not self.release.wait(timeout=5):
                raise AssertionError("blocking tool was not released")
            return ToolResult(
                data={"answer": f"result:{arguments['question']}"},
                correlation_id=context.correlation_id,
            )
        finally:
            with self._lock:
                self.active -= 1

    def counts(self) -> tuple[int, int, int]:
        with self._lock:
            return self.started, self.active, self.max_active


def _registry(tool: _Tool | None = None) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(tool or _Tool(), lambda result: result.data)
    return registry


def _context(*, cancelled: bool = False) -> ToolContext:
    return ToolContext(
        learner_id="learner",
        source_scope="DEFAULT_PLUS_EXTRAS",
        correlation_id="request-1",
        permissions=frozenset({"read"}),
        cancelled=cancelled,
    )


def _turn(
    *,
    text: str = "",
    calls: tuple[ToolCall, ...] = (),
    stop: str | None = "end_turn",
    input_tokens: int = 100,
    output_tokens: int = 20,
) -> ModelTurn:
    return ModelTurn(
        text=text,
        tool_calls=calls,
        stop_reason=stop,
        usage=ModelUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        latency_ms=2.0,
    )


async def _wait_until(
    predicate: Callable[[], bool],
    *,
    timeout: float = 1.0,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError("condition did not become true")
        await asyncio.sleep(0.005)


def test_final_only_turn_completes_with_sanitized_usage() -> None:
    client = _Client([_turn(text="final answer")])

    result = asyncio.run(PreviewAgent(client, _registry()).run("prompt", _context()))

    assert result.status == "completed"
    assert result.termination_reason == "completed"
    assert result.answer == "final answer"
    assert result.model_turn_count == 1
    assert result.tool_call_count == 0
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 20
    assert result.agent_trace[0]["model"] == "claude-opus-5"
    assert "prompt" not in repr(result.agent_trace)


def test_native_tool_result_is_appended_once_before_continuation() -> None:
    call = ToolCall("call-1", "retrieve", {"question": "process"})
    tool = _Tool()
    client = _Client(
        [
            _turn(calls=(call,), stop="tool_use"),
            _turn(text="done"),
        ],
        token_counts=(100, 150),
    )

    result = asyncio.run(PreviewAgent(client, _registry(tool)).run("prompt", _context()))

    assert result.status == "completed"
    assert result.answer == "done"
    assert result.model_turn_count == 2
    assert result.tool_call_count == 1
    assert tool.calls == 1
    assert client.conversation is not None
    assert len(client.conversation.results) == 1
    assert client.conversation.results[0].call_id == "call-1"
    assert client.conversation.results[0].content == '{"data":{"answer":"result:process"}}'
    assert "process" not in repr(result.agent_trace)


def test_duplicate_tool_call_terminates_without_replay() -> None:
    first = ToolCall("call-1", "retrieve", {"question": "process"})
    duplicate = ToolCall("call-2", "retrieve", {"question": "process"})
    tool = _Tool()
    client = _Client(
        [
            _turn(calls=(first,), stop="tool_use"),
            _turn(calls=(duplicate,), stop="tool_use"),
        ],
        token_counts=(100, 150),
    )

    result = asyncio.run(PreviewAgent(client, _registry(tool)).run("prompt", _context()))

    assert result.status == "terminated"
    assert result.termination_reason == "duplicate_tool_call"
    assert tool.calls == 1
    assert result.tool_call_count == 1
    assert client.conversation is not None
    assert len(client.conversation.results) == 1


def test_multiple_tool_calls_execute_none() -> None:
    calls = (
        ToolCall("call-1", "retrieve", {"question": "one"}),
        ToolCall("call-2", "retrieve", {"question": "two"}),
    )
    tool = _Tool()
    client = _Client([_turn(calls=calls, stop="tool_use")])

    result = asyncio.run(PreviewAgent(client, _registry(tool)).run("prompt", _context()))

    assert result.termination_reason == "multiple_tool_calls"
    assert result.tool_call_count == 0
    assert tool.calls == 0


def test_one_retry_uses_capped_retry_after_and_does_not_add_turn() -> None:
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    client = _Client(
        [
            ProviderError(
                ProviderErrorCode.RATE_LIMIT,
                retryable=True,
                status_code=429,
                retry_after=9.0,
            ),
            _turn(text="done"),
        ]
    )
    agent = PreviewAgent(client, _registry(), sleep=sleep)

    result = asyncio.run(agent.run("prompt", _context()))

    assert result.status == "completed"
    assert result.model_turn_count == 1
    assert client.create_calls == 2
    assert sleeps == [2.0]
    assert result.agent_trace[0]["retries"] == 1


def test_non_retryable_provider_error_has_stable_reason() -> None:
    client = _Client(
        [ProviderError(ProviderErrorCode.AUTH, retryable=False)]
    )

    result = asyncio.run(PreviewAgent(client, _registry()).run("prompt", _context()))

    assert result.status == "terminated"
    assert result.termination_reason == "provider_auth_failed"
    assert result.agent_trace == ()


def test_budget_guards_fail_closed_before_generation() -> None:
    client = _Client([_turn(text="must not run")], token_counts=(12_001,))

    result = asyncio.run(PreviewAgent(client, _registry()).run("prompt", _context()))

    assert result.termination_reason == "input_token_budget"
    assert client.create_calls == 0


def test_answer_and_prompt_byte_budgets_are_utf8_based() -> None:
    limits = PreviewLimits(max_prompt_bytes=3, max_answer_bytes=3)
    prompt_result = asyncio.run(
        PreviewAgent(_Client([_turn(text="x")]), _registry(), limits=limits).run(
            "中文", _context()
        )
    )
    answer_result = asyncio.run(
        PreviewAgent(_Client([_turn(text="中文")]), _registry(), limits=limits).run(
            "ok", _context()
        )
    )

    assert prompt_result.termination_reason == "prompt_budget"
    assert answer_result.termination_reason == "answer_budget"


def test_cancelled_context_starts_no_provider_or_tool_work() -> None:
    client = _Client([_turn(text="must not run")])

    result = asyncio.run(
        PreviewAgent(client, _registry()).run("prompt", _context(cancelled=True))
    )

    assert result.termination_reason == "cancelled"
    assert client.count_calls == 0
    assert client.create_calls == 0


@pytest.mark.parametrize(
    ("stop", "reason"),
    [
        ("refusal", "provider_refusal"),
        ("max_tokens", "output_token_budget"),
        ("pause_turn", "unexpected_stop_reason"),
        ("stop_sequence", "unexpected_stop_reason"),
        (None, "unexpected_stop_reason"),
    ],
)
def test_non_final_stop_reasons_never_complete(
    stop: str | None,
    reason: str,
) -> None:
    client = _Client([_turn(text="not final", stop=stop)])

    result = asyncio.run(PreviewAgent(client, _registry()).run("prompt", _context()))

    assert result.status == "terminated"
    assert result.termination_reason == reason
    assert result.answer is None


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        (ProviderErrorCode.AUTH, "provider_auth_failed"),
        (ProviderErrorCode.REJECTED, "provider_rejected"),
        (ProviderErrorCode.TIMEOUT, "provider_timeout"),
        (ProviderErrorCode.CONNECTION, "provider_unavailable"),
        (ProviderErrorCode.RATE_LIMIT, "provider_unavailable"),
        (ProviderErrorCode.UNAVAILABLE, "provider_unavailable"),
        (ProviderErrorCode.UNKNOWN, "provider_unavailable"),
    ],
)
def test_token_count_provider_failures_keep_stable_categories(
    code: ProviderErrorCode,
    reason: str,
) -> None:
    client = _Client(
        [_turn(text="must not run")],
        token_counts=(ProviderError(code, retryable=False),),
    )

    result = asyncio.run(PreviewAgent(client, _registry()).run("prompt", _context()))

    assert result.termination_reason == reason
    assert client.create_calls == 0


def test_max_turns_terminates_after_bounded_tool_continuations() -> None:
    calls = tuple(
        ToolCall(f"call-{index}", "retrieve", {"question": str(index)})
        for index in range(1, 5)
    )
    client = _Client(
        [_turn(calls=(call,), stop="tool_use") for call in calls],
        token_counts=(100, 100, 100, 100),
    )
    limits = PreviewLimits(max_tool_calls=3)

    result = asyncio.run(
        PreviewAgent(client, _registry(), limits=limits).run("prompt", _context())
    )

    assert result.termination_reason == "max_tool_calls"
    assert result.model_turn_count == 4
    assert result.tool_call_count == 3


def test_max_turns_reason_is_stable_when_tool_budget_is_not_tighter() -> None:
    calls = tuple(
        ToolCall(f"call-{index}", "retrieve", {"question": str(index)})
        for index in range(1, 5)
    )
    client = _Client(
        [_turn(calls=(call,), stop="tool_use") for call in calls],
        token_counts=(100, 100, 100, 100),
    )
    limits = PreviewLimits(max_model_turns=3, max_tool_calls=3)

    result = asyncio.run(
        PreviewAgent(client, _registry(), limits=limits).run("prompt", _context())
    )

    assert result.termination_reason == "max_turns"
    assert result.model_turn_count == 3
    assert result.tool_call_count == 3


def test_cumulative_tool_result_budget_fails_closed_before_replay() -> None:
    first = ToolCall("call-1", "retrieve", {"question": "one"})
    second = ToolCall("call-2", "retrieve", {"question": "two"})
    client = _Client(
        [
            _turn(calls=(first,), stop="tool_use"),
            _turn(calls=(second,), stop="tool_use"),
        ],
        token_counts=(100, 100),
    )
    limits = PreviewLimits(
        max_tool_result_bytes=40,
        max_total_tool_result_bytes=50,
    )

    result = asyncio.run(
        PreviewAgent(client, _registry(), limits=limits).run("prompt", _context())
    )

    assert result.termination_reason == "tool_result_budget"
    assert result.tool_call_count == 2
    assert client.conversation is not None
    assert len(client.conversation.results) == 1
    tool_trace = [item for item in result.agent_trace if "tool" in item]
    assert tool_trace[-1]["original_result_bytes"] == tool_trace[-1]["returned_result_bytes"]


def test_reported_output_and_cost_overages_terminate_after_one_turn() -> None:
    output_result = asyncio.run(
        PreviewAgent(
            _Client([_turn(text="done", output_tokens=1_025)]),
            _registry(),
            limits=PreviewLimits(max_output_tokens=1_024),
        ).run("prompt", _context())
    )
    cost_result = asyncio.run(
        PreviewAgent(
            _Client([_turn(text="done", input_tokens=100, output_tokens=1_024)]),
            _registry(),
            limits=PreviewLimits(max_cost_usd=0.0782),
        ).run("prompt", _context())
    )

    assert output_result.termination_reason == "output_token_budget"
    assert cost_result.termination_reason == "cost_budget"


def test_retry_exhaustion_has_one_retry_and_stable_reason() -> None:
    error = ProviderError(ProviderErrorCode.CONNECTION, retryable=True)
    client = _Client([error, error])

    result = asyncio.run(
        PreviewAgent(client, _registry(), sleep=lambda delay: asyncio.sleep(0)).run(
            "prompt", _context()
        )
    )

    assert result.termination_reason == "provider_unavailable"
    assert client.create_calls == 2
    assert result.model_turn_count == 0


def test_retry_jitter_uses_frozen_bounds() -> None:
    bounds: list[tuple[float, float]] = []
    sleeps: list[float] = []

    def jitter(low: float, high: float) -> float:
        bounds.append((low, high))
        return high

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    client = _Client(
        [
            ProviderError(ProviderErrorCode.CONNECTION, retryable=True),
            _turn(text="done"),
        ]
    )

    result = asyncio.run(
        PreviewAgent(client, _registry(), jitter=jitter, sleep=sleep).run(
            "prompt", _context()
        )
    )

    assert result.status == "completed"
    assert bounds == [(0.2, 0.5)]
    assert sleeps == [0.5]


def test_cancellation_after_retry_sleep_starts_no_second_request() -> None:
    cancelled = False

    async def sleep(delay: float) -> None:
        nonlocal cancelled
        del delay
        cancelled = True

    client = _Client(
        [
            ProviderError(ProviderErrorCode.CONNECTION, retryable=True),
            _turn(text="must not run"),
        ]
    )
    agent = PreviewAgent(
        client,
        _registry(),
        sleep=sleep,
        cancelled=lambda: cancelled,
    )

    result = asyncio.run(agent.run("prompt", _context()))

    assert result.termination_reason == "cancelled"
    assert client.create_calls == 1


@pytest.mark.parametrize(
    ("call", "reason"),
    [
        (ToolCall("call-1", "missing", {}), "unknown_tool"),
        (ToolCall("call-1", "retrieve", {}), "invalid_tool_arguments"),
    ],
)
def test_tool_boundary_errors_have_stable_reasons(
    call: ToolCall,
    reason: str,
) -> None:
    client = _Client([_turn(calls=(call,), stop="tool_use")])

    result = asyncio.run(PreviewAgent(client, _registry()).run("prompt", _context()))

    assert result.termination_reason == reason
    assert result.tool_call_count == 1
    assert client.conversation is not None
    assert client.conversation.results == []


class _SlowTool(_Tool):
    def execute(
        self,
        context: ToolContext,
        arguments: Mapping[str, Any],
    ) -> ToolResult:
        self.calls += 1
        time.sleep(0.25)
        return super().execute(context, arguments)


class _ExplodingTool(_Tool):
    def execute(
        self,
        context: ToolContext,
        arguments: Mapping[str, Any],
    ) -> ToolResult:
        self.calls += 1
        raise RuntimeError("tool-secret-canary")


def test_blocking_tool_respects_real_deadline_without_continuation() -> None:
    tool = _SlowTool()
    client = _Client(
        [
            _turn(
                calls=(ToolCall("call-1", "retrieve", {"question": "slow"}),),
                stop="tool_use",
            ),
            _turn(text="should-not-run"),
        ]
    )

    result = asyncio.run(
        PreviewAgent(
            client,
            _registry(tool),
            limits=PreviewLimits(tool_timeout_seconds=0.05),
        ).run("prompt", _context())
    )

    assert result.status == "terminated"
    assert result.termination_reason == "tool_timeout"
    assert result.tool_call_count == 0
    assert result.answer is None
    assert client.create_calls == 1
    assert client.conversation is not None
    assert client.conversation.results == []


def test_tool_work_capacity_survives_request_timeout_and_recovers() -> None:
    async def scenario() -> None:
        tool = _BlockingTool()
        limiter = ToolWorkLimiter()
        call = ToolCall("call-1", "retrieve", {"question": "blocked"})
        clients = [
            _Client([_turn(calls=(call,), stop="tool_use"), _turn(text="late")])
            for _ in range(3)
        ]
        agents = [
            PreviewAgent(
                client,
                _registry(tool),
                limits=PreviewLimits(tool_timeout_seconds=0.05),
                tool_work_limiter=limiter,
            )
            for client in clients
        ]

        first = asyncio.create_task(agents[0].run("prompt-1", _context()))
        second = asyncio.create_task(agents[1].run("prompt-2", _context()))
        await _wait_until(lambda: tool.counts()[0] == 2)
        third = asyncio.create_task(agents[2].run("prompt-3", _context()))

        results = await asyncio.gather(first, second, third)
        assert [result.termination_reason for result in results] == [
            "tool_timeout",
            "tool_timeout",
            "tool_timeout",
        ]
        assert tool.counts() == (2, 2, 2)
        assert all(client.create_calls == 1 for client in clients)
        assert all(client.conversation is not None for client in clients)
        assert all(client.conversation.results == [] for client in clients if client.conversation)

        tool.release.set()
        await _wait_until(lambda: tool.counts()[1] == 0)

        recovery_client = _Client(
            [_turn(calls=(call,), stop="tool_use"), _turn(text="recovered")]
        )
        recovered = await PreviewAgent(
            recovery_client,
            _registry(tool),
            limits=PreviewLimits(tool_timeout_seconds=0.25),
            tool_work_limiter=limiter,
        ).run("prompt-4", _context())

        assert recovered.status == "completed"
        assert recovered.answer == "recovered"
        assert recovered.tool_call_count == 1
        assert tool.counts() == (3, 0, 2)

    asyncio.run(scenario())


def test_cancelled_request_holds_tool_permit_until_worker_finishes() -> None:
    async def scenario() -> None:
        tool = _BlockingTool()
        limiter = ToolWorkLimiter()
        call = ToolCall("call-1", "retrieve", {"question": "blocked"})
        client = _Client([_turn(calls=(call,), stop="tool_use"), _turn(text="late")])
        task = asyncio.create_task(
            PreviewAgent(
                client,
                _registry(tool),
                limits=PreviewLimits(tool_timeout_seconds=1.0),
                tool_work_limiter=limiter,
            ).run("prompt", _context())
        )
        await _wait_until(lambda: tool.counts()[0] == 1)

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert tool.counts() == (1, 1, 1)
        assert client.create_calls == 1
        assert client.conversation is not None
        assert client.conversation.results == []

        tool.release.set()
        await _wait_until(lambda: tool.counts()[1] == 0)
        assert client.create_calls == 1
        assert client.conversation.results == []

    asyncio.run(scenario())


def test_sensitive_tool_exception_is_sanitized_without_continuation() -> None:
    canary = "tool-secret-canary"
    tool = _ExplodingTool()
    client = _Client(
        [
            _turn(
                calls=(ToolCall("call-1", "retrieve", {"question": "question-canary"}),),
                stop="tool_use",
            ),
            _turn(text="should-not-run"),
        ]
    )

    result = asyncio.run(PreviewAgent(client, _registry(tool)).run("prompt", _context()))

    assert result.status == "terminated"
    assert result.termination_reason == "tool_failed"
    assert result.tool_call_count == 1
    assert tool.calls == 1
    assert client.create_calls == 1
    assert client.conversation is not None
    assert client.conversation.results == []
    assert canary not in repr(result)
    assert canary not in repr(result.agent_trace)
    assert "question-canary" not in repr(result.agent_trace)


def test_context_without_read_permission_rejects_tool_execution() -> None:
    call = ToolCall("call-1", "retrieve", {"question": "private-query-canary"})
    tool = _ContextTool()
    client = _Client([_turn(calls=(call,), stop="tool_use")])
    context = ToolContext(
        learner_id="learner",
        source_scope="DEFAULT_PLUS_EXTRAS",
        correlation_id="request-1",
        permissions=frozenset(),
    )

    result = asyncio.run(PreviewAgent(client, _registry(tool)).run("prompt", context))

    assert result.termination_reason == "unauthorized_tool"
    assert result.tool_call_count == 1
    assert tool.calls == 0
    assert tool.contexts == []
    assert "private-query-canary" not in repr(result.agent_trace)


def test_generic_tool_failure_is_sanitized() -> None:
    canary = "tool-error-body-canary"
    call = ToolCall("call-1", "retrieve", {"question": "question-canary"})
    tool = _ContextTool(
        ToolResult(error=ToolError("TOOL_INTERNAL", canary, retryable=False))
    )
    client = _Client([_turn(calls=(call,), stop="tool_use")])

    result = asyncio.run(PreviewAgent(client, _registry(tool)).run("prompt", _context()))

    assert result.termination_reason == "tool_failed"
    assert result.tool_call_count == 1
    assert tool.calls == 1
    assert client.conversation is not None
    assert client.conversation.results == []
    assert canary not in repr(result)
    assert "question-canary" not in repr(result.agent_trace)
    assert result.agent_trace[-1]["error_code"] == "TOOL_INTERNAL"


@pytest.mark.parametrize("data", [{"bad": object()}, {"bad": float("nan")}])
def test_non_json_tool_results_fail_closed(data: dict[str, Any]) -> None:
    call = ToolCall("call-1", "retrieve", {"question": "question"})
    tool = _ContextTool(ToolResult(data=data))
    client = _Client([_turn(calls=(call,), stop="tool_use")])

    result = asyncio.run(PreviewAgent(client, _registry(tool)).run("prompt", _context()))

    assert result.termination_reason == "tool_failed"
    assert result.tool_call_count == 1
    assert client.conversation is not None
    assert client.conversation.results == []


def test_sources_are_collected_exactly_once_in_first_seen_order() -> None:
    first = SourceIdentity("source-1", "knowledge/os/process.md")
    second = SourceIdentity("source-2", "knowledge/ds/tree.md")
    calls = (
        ToolCall("call-1", "retrieve", {"question": "one"}),
        ToolCall("call-2", "retrieve", {"question": "two"}),
    )
    tool = _ContextTool(ToolResult(data={"answer": "safe"}, sources=(first, second, first)))
    client = _Client(
        [
            _turn(calls=(calls[0],), stop="tool_use"),
            _turn(calls=(calls[1],), stop="tool_use"),
            _turn(text="final-answer-canary"),
        ],
        token_counts=(100, 100, 100),
    )

    result = asyncio.run(PreviewAgent(client, _registry(tool)).run("prompt", _context()))

    assert result.status == "completed"
    assert result.sources == (first, second)
    assert result.tool_call_count == 2
    assert tool.calls == 2
    assert "final-answer-canary" not in repr(result.agent_trace)
    assert "safe" not in repr(result.agent_trace)


def test_builtin_token_count_timeout_has_stable_reason() -> None:
    client = _Client([_turn(text="must not run")], token_counts=(TimeoutError(),))

    result = asyncio.run(PreviewAgent(client, _registry()).run("prompt", _context()))

    assert result.termination_reason == "provider_timeout"
    assert client.count_calls == 1
    assert client.create_calls == 0


def test_deadline_expiring_during_retry_sleep_starts_no_second_request() -> None:
    now = 0.0

    def monotonic() -> float:
        return now

    async def sleep(delay: float) -> None:
        nonlocal now
        assert delay == 0.2
        now = 0.31

    client = _Client(
        [
            ProviderError(ProviderErrorCode.CONNECTION, retryable=True),
            _turn(text="must not run"),
        ]
    )
    agent = PreviewAgent(
        client,
        _registry(),
        limits=PreviewLimits(deadline_seconds=0.3),
        monotonic=monotonic,
        jitter=lambda low, high: low,
        sleep=sleep,
    )

    result = asyncio.run(agent.run("prompt", _context()))

    assert result.termination_reason == "deadline_exceeded"
    assert client.create_calls == 1
    assert result.model_turn_count == 0


@pytest.mark.parametrize(
    "limits",
    [
        PreviewLimits(deadline_seconds=float("inf")),
        PreviewLimits(model_timeout_seconds=21.0),
        PreviewLimits(max_model_turns=5),
        PreviewLimits(max_retries=2),
        PreviewLimits(retry_min_seconds=0.1),
        PreviewLimits(retry_min_seconds=0.5, retry_max_seconds=0.4),
        PreviewLimits(max_output_tokens=512, max_turn_output_tokens=1_024),
        PreviewLimits(max_tool_result_bytes=100, max_total_tool_result_bytes=50),
    ],
)
def test_relaxed_or_incoherent_limits_are_rejected(limits: PreviewLimits) -> None:
    with pytest.raises(ValueError):
        PreviewAgent(_Client([_turn(text="unused")]), _registry(), limits=limits)
