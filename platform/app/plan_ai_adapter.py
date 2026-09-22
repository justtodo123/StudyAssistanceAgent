"""M9 可选外部 AI 计划路径（`m9.external-ai`，默认关闭）。

实现 `M9-EXTERNAL-AI` 决策：显式 opt-in、默认关闭；最小披露；硬超时与 token/成本预算（只允许收紧）；
失败即回退确定性路径，**不产生半成品计划**。

## 最小披露是**结构性**的，不是承诺

送出去的载荷由 `PlanAIRequest` 与 `PlanAITaskSummary` 两个冻结 dataclass 定义。`PlanAITaskSummary`
**没有 `file` 字段**——任务以 `task_id` 标识，而 `task_id` 是 `sha256(file)[:16]`（见
`goal_planner._task_id`），是不透明摘要、不含路径信息。因此「不送文件路径」不是靠渲染时过滤实现的，
而是**类型上就没有那个字段可以送**。mastery 只送**聚合计数**，不送 per-file 值；`principal_id`
根本不在载荷里。

## 与 M6b 的关系

直接复用 `llm_client` 的 `LLMClient` 协议与 `AnthropicLLMClient`，不新建 provider 抽象；预算校验沿用
`preview_agent` 的「每值 ≤ 冻结默认」约定与同一组定价常量，避免两处定价各自漂移。

## output token 预算是**两个**字段，不是一个

`max_output_tokens` 是**累积**预算（整个计划路径的产出总量），只送给 provider——本地没有 tokenizer，
无从核验一次调用真正产出了多少 token，故它在本地没有执行点。`max_turn_output_tokens` 是**单轮**
预算，它才是传给 `create_turn` 的 `max_tokens`，而 `llm_client.create_turn` 硬拒大于
`MAX_TURN_OUTPUT_TOKENS` 的值，所以这道闸门**在本地、在发出任何 HTTP 请求之前**。

两者语义不同，故不可合并成一个值。**曾合并过**：累积值被直接当单轮值传下去，于是默认配置下每次
调用都在本地抛 `ValueError`，被 `propose` 的回退路径收敛成 `provider_unavailable`——整条外部 AI
路径静默失效，且既有测试全绿（它们经 `proposer=` 注入，绕过这个调用点）。回归用例因此必须驱动
`build_anthropic_proposer` 这条真实桥，见 `tests/M9/test_plan_ai_adapter.py` 的「单轮 output 预算」节。

## 同步/异步边界

Planner 的 `generate()` 是同步的，而 `LLMClient` 是异步的。本模块把这条边界收在**一个**地方：
注入接缝 `proposer` 是**同步可调用对象**，测试注入纯同步 stub（完全不碰 asyncio），生产路径由
`build_anthropic_proposer` 提供一个线程 + 独立事件循环的桥。超时后该线程**被放弃而非取消**——
它是 daemon 线程，不会阻塞进程退出，但也不会被强杀；这是本桥的已知限制，故 `deadline_seconds`
只是外层兜底，真正的单次调用上限由传给 `create_turn` 的 `model_timeout_seconds` 保证。
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields, replace
from typing import Any

from .llm_client import (
    MAX_TURN_OUTPUT_TOKENS,
    AnthropicLLMClient,
    LLMClient,
    ProviderError,
)

PLAN_AI_SCHEMA_VERSION = "m9-plan-ai-adapter-v1"

# 授权范围标识，随载荷送给 provider 以便其区分调用来源。必须与
# `docs/standards/stage-admission-gates.json` 里 M9 的 `approval_scope.scope_id` 一致——
# `tests/M9/test_plan_ai_adapter.py` 有一条用例直接比对登记表，防止两处静默漂移。
AUTHORIZED_SCOPE_ID = "m9-plan-lifecycle-v1"

# 与 `preview_agent` 同一组定价常量：两处各自定义会在调价时静默漂移，故在此引用同一来源。
_INPUT_USD_PER_MILLION = 15.0
_OUTPUT_USD_PER_MILLION = 75.0

# 审计里出现的原因码是稳定枚举，便于断言与聚合；不得把 provider 原文塞进来。
REASON_ADOPTED = "adopted"
REASON_DISABLED = "disabled"
REASON_PROMPT_BUDGET = "prompt_budget"
REASON_DEADLINE = "deadline_exceeded"
REASON_PROVIDER_TIMEOUT = "provider_timeout"
REASON_PROVIDER_UNAVAILABLE = "provider_unavailable"
REASON_PROVIDER_REJECTED = "provider_rejected"
REASON_ANSWER_BUDGET = "answer_budget"
REASON_UNPARSABLE = "unparsable_response"
REASON_NOT_A_PERMUTATION = "not_a_permutation"
REASON_COST_BUDGET = "cost_budget"


@dataclass(frozen=True, slots=True)
class PlanAILimits:
    """外部 AI 路径的资源预算；调用方只能**收紧**，放宽即拒绝。"""

    deadline_seconds: float = 30.0
    model_timeout_seconds: float = 20.0
    max_input_tokens: int = 8_000
    # 累积预算，**只在 provider 侧**执行：本地没有 tokenizer，无从核验一次调用真正产出了多少 token。
    max_output_tokens: int = 2_048
    # 单轮预算，**在本地执行**：这是传给 `create_turn` 的 `max_tokens`，而 `llm_client` 硬拒
    # 大于 `MAX_TURN_OUTPUT_TOKENS` 的值。两者语义不同，故必须是两个字段——把累积值直接当单轮值
    # 传下去（旧行为）会让每次调用在**发出任何 HTTP 请求之前**抛 ValueError，被回退路径收敛成
    # `provider_unavailable`，从而让整条外部 AI 路径静默失效。同形约定见 `preview_agent.PreviewLimits`。
    max_turn_output_tokens: int = MAX_TURN_OUTPUT_TOKENS
    max_cost_usd: float = 0.10
    # 字节预算而非 token 预算：本地没有 tokenizer，估算 token 会引入一个我们自己造的近似值。
    max_prompt_bytes: int = 16 * 1024
    max_answer_bytes: int = 16 * 1024
    max_retries: int = 1


@dataclass(frozen=True, slots=True)
class PlanAITaskSummary:
    """送往 provider 的单条任务摘要。

    **没有 `file` 字段**——这是最小披露的结构性保证（见模块 docstring）。新增字段前必须重新过一遍
    `M9-EXTERNAL-AI` 的最小披露清单。
    """

    task_id: str
    topic: str
    difficulty: str
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanAIRequest:
    """送往 provider 的**完整**载荷；本类型之外不送任何东西。"""

    goal: str
    course: str | None
    hours_per_day: float
    required_topics: tuple[str, ...]
    excluded_topics: tuple[str, ...]
    scope_id: str
    mastery_counts: Mapping[str, int]
    tasks: tuple[PlanAITaskSummary, ...]


@dataclass(frozen=True, slots=True)
class PlanAIAudit:
    """脱敏审计记录：只留规模与结果，不留 prompt 正文、不留 provider 原文。"""

    reason: str
    prompt_bytes: int = 0
    answer_bytes: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class PlanAIOutcome:
    """`order` 为 `None` 即**回退**确定性顺序；`reason` 说明为何。"""

    order: tuple[str, ...] | None
    audit: PlanAIAudit


def _validate_limits(limits: PlanAILimits) -> None:
    """拒绝非有限、非正或**放宽**的预算；与 `preview_agent._validate_limits` 同形。"""
    defaults = PlanAILimits()
    for name in ("deadline_seconds", "model_timeout_seconds", "max_cost_usd"):
        value = getattr(limits, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a finite positive number")
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
        if value > getattr(defaults, name):
            raise ValueError(f"{name} cannot exceed the hard limit")
    for name in (
        "max_input_tokens",
        "max_output_tokens",
        "max_turn_output_tokens",
        "max_prompt_bytes",
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
    if limits.max_output_tokens > limits.max_input_tokens:
        raise ValueError("output budget cannot exceed input budget")
    if limits.max_turn_output_tokens > limits.max_output_tokens:
        raise ValueError("turn output limit cannot exceed total output limit")


def limits_from_env() -> PlanAILimits:
    """按 `preview_agent` 的约定从环境变量构造预算（每项只允许收紧）。"""
    from . import config

    return config.plan_ai_limits()


def render_prompt(request: PlanAIRequest) -> str:
    """把载荷渲染成 prompt。**唯一**的渲染入口，故最小披露只有这一处需要审。"""
    payload = {
        "schema_version": PLAN_AI_SCHEMA_VERSION,
        "goal": request.goal,
        "course": request.course,
        "hours_per_day": request.hours_per_day,
        "required_topics": list(request.required_topics),
        "excluded_topics": list(request.excluded_topics),
        "scope_id": request.scope_id,
        "mastery_counts": dict(request.mastery_counts),
        "tasks": [
            {
                "task_id": task.task_id,
                "topic": task.topic,
                "difficulty": task.difficulty,
                "tags": list(task.tags),
            }
            for task in request.tasks
        ],
    }
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return (
        "You are ordering an existing study plan's tasks.\n"
        "Return ONLY a JSON object of the form {\"order\": [<task_id>, ...]}.\n"
        "`order` must be a permutation of exactly the task_id values given below: no additions,\n"
        "no omissions, no duplicates. Tasks named in required_topics must come first.\n"
        "Prerequisite constraints are not yours to decide; an invalid order is discarded.\n\n"
        f"{body}"
    )


_ORDER_KEY = "order"


def parse_order(answer: str, expected: Sequence[str]) -> tuple[str, ...] | None:
    """严格解析 provider 回复；任何不合规都返回 `None`（回退），不抛异常给调用方。

    必须是**恰好** `expected` 的一个置换：多、少、重复、非字符串、非 JSON 一律拒绝。
    """
    if not isinstance(answer, str):
        return None
    stripped = answer.strip()
    if stripped.startswith("```"):
        # 容忍 ```json ... ``` 围栏：这是格式噪声，不是语义偏差。
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    order = parsed.get(_ORDER_KEY)
    if not isinstance(order, list):
        return None
    if not all(isinstance(item, str) for item in order):
        return None
    # 置换校验：集合相等且长度相等 ⇒ 无重复、无增删。分别判长度是必要的，
    # 否则 ["a","a","b"] 与 ["a","b"] 会因集合相等而混过。
    if len(order) != len(expected) or set(order) != set(expected):
        return None
    return tuple(order)


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * _INPUT_USD_PER_MILLION
        + output_tokens * _OUTPUT_USD_PER_MILLION
    ) / 1_000_000


def _provider_reason(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return REASON_PROVIDER_TIMEOUT
    if isinstance(exc, ProviderError):
        if exc.code.value == "timeout":
            return REASON_PROVIDER_TIMEOUT
        if exc.code.value == "rejected":
            return REASON_PROVIDER_REJECTED
        return REASON_PROVIDER_UNAVAILABLE
    return REASON_PROVIDER_UNAVAILABLE


# 注入接缝：同步可调用对象。测试注入纯同步 stub，生产路径见 `build_anthropic_proposer`。
Proposer = Callable[[PlanAIRequest, PlanAILimits], PlanAIOutcome]


class PlanAIAdapter:
    """在**同一有界条目集**内为计划提出排序的外部 AI 路径。

    本类只负责「提出」；**采纳与否由 Planner 的确定性校验器决定**（见 `goal_planner._ai_order`）。
    任一步失败都返回 `order=None`，调用方据此逐字回退。
    """

    def __init__(
        self,
        *,
        proposer: Proposer | None = None,
        limits: PlanAILimits | None = None,
        enabled: bool = False,
    ) -> None:
        self._limits = limits if limits is not None else PlanAILimits()
        _validate_limits(self._limits)
        self._proposer = proposer
        # 默认关闭：未显式 enabled 且未注入 proposer 时，propose() 恒定回退。
        self._enabled = bool(enabled) and proposer is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def limits(self) -> PlanAILimits:
        return self._limits

    def propose_for(
        self,
        *,
        goal: str,
        course: str | None,
        hours_per_day: float,
        required_topics: Sequence[str],
        excluded_topics: Sequence[str],
        mastery_counts: Mapping[str, int],
        tasks: Sequence[Any],
    ) -> PlanAIOutcome:
        """从计划上下文构造载荷并提出排序。

        `tasks` 按**鸭子类型**取 `task_id` / `topic` / `difficulty` / `tags` 四个属性——本方法刻意不
        接收 `GoalPlanTask` 类型，好让 Planner 不必 import 本模块（Planner 有源码级护栏禁止出现
        provider 相关标识符）。`scope_id` 由本模块自持：它是**本路径授权范围**的属性，不是调用方
        每次要传的参数。任何 `file` 字段都不会被读取，故也不会被送出去。
        """
        summaries = tuple(
            PlanAITaskSummary(
                task_id=task.task_id,
                topic=task.topic,
                difficulty=task.difficulty,
                tags=tuple(task.tags),
            )
            for task in tasks
        )
        return self.propose(
            PlanAIRequest(
                goal=goal,
                course=course,
                hours_per_day=hours_per_day,
                required_topics=tuple(required_topics),
                excluded_topics=tuple(excluded_topics),
                scope_id=AUTHORIZED_SCOPE_ID,
                mastery_counts=dict(mastery_counts),
                tasks=summaries,
            )
        )

    def propose(self, request: PlanAIRequest) -> PlanAIOutcome:
        """提出一个排序；**不抛异常**——所有失败都收敛为 `order=None` + 稳定原因码。"""
        if not self._enabled:
            return PlanAIOutcome(None, PlanAIAudit(reason=REASON_DISABLED))
        if not request.tasks:
            return PlanAIOutcome(None, PlanAIAudit(reason=REASON_UNPARSABLE))
        prompt = render_prompt(request)
        prompt_bytes = len(prompt.encode("utf-8"))
        if prompt_bytes > self._limits.max_prompt_bytes:
            return PlanAIOutcome(
                None,
                PlanAIAudit(reason=REASON_PROMPT_BUDGET, prompt_bytes=prompt_bytes),
            )
        assert self._proposer is not None  # enabled 已蕴含非 None
        started = time.monotonic()
        try:
            outcome = self._proposer(request, self._limits)
        except BaseException:  # noqa: BLE001 - provider 的失败模式不归调用方处理
            return PlanAIOutcome(
                None,
                PlanAIAudit(
                    reason=REASON_PROVIDER_UNAVAILABLE,
                    prompt_bytes=prompt_bytes,
                    latency_ms=(time.monotonic() - started) * 1000.0,
                ),
            )
        elapsed = (time.monotonic() - started) * 1000.0
        audit = PlanAIAudit(
            reason=outcome.audit.reason,
            prompt_bytes=prompt_bytes,
            answer_bytes=outcome.audit.answer_bytes,
            input_tokens=outcome.audit.input_tokens,
            output_tokens=outcome.audit.output_tokens,
            estimated_cost_usd=outcome.audit.estimated_cost_usd,
            latency_ms=elapsed,
        )
        if outcome.audit.estimated_cost_usd > self._limits.max_cost_usd:
            # 成本超预算：即便回复可用也不采纳——预算是硬上限，不是告警阈值。
            return PlanAIOutcome(None, replace(audit, reason=REASON_COST_BUDGET))
        if outcome.order is None:
            return PlanAIOutcome(None, audit)
        return PlanAIOutcome(outcome.order, audit)


def build_anthropic_proposer(
    *,
    token: str,
    model: str | None = None,
    client_factory: Callable[[str], LLMClient] = AnthropicLLMClient,
) -> Proposer:
    """构造生产 proposer：把异步 `LLMClient` 桥成同步可调用对象。

    `client_factory` 是注入接缝，使测试可以完全离线地驱动这条路径（与 `PreviewService` 同形）。
    """

    def propose(request: PlanAIRequest, limits: PlanAILimits) -> PlanAIOutcome:
        prompt = render_prompt(request)
        expected = tuple(task.task_id for task in request.tasks)

        def call() -> PlanAIOutcome:
            return asyncio.run(_propose_async(prompt, expected, limits, token, model, client_factory))

        return _run_blocking(call, deadline_seconds=limits.deadline_seconds)

    return propose


async def _propose_async(
    prompt: str,
    expected: tuple[str, ...],
    limits: PlanAILimits,
    token: str,
    model: str | None,
    client_factory: Callable[[str], LLMClient],
) -> PlanAIOutcome:
    client = client_factory(token)
    try:
        conversation = client.new_conversation(prompt)
        turn = await client.create_turn(
            conversation,
            (),
            max_tokens=limits.max_turn_output_tokens,
            timeout=limits.model_timeout_seconds,
        )
    finally:
        try:
            await client.close()
        except Exception:  # noqa: BLE001 - 关闭失败不改变本次结论
            pass
    answer_bytes = len(turn.text.encode("utf-8"))
    usage = turn.usage
    audit = PlanAIAudit(
        reason=REASON_ADOPTED,
        answer_bytes=answer_bytes,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        estimated_cost_usd=_estimate_cost(usage.input_tokens, usage.output_tokens),
        latency_ms=turn.latency_ms,
    )
    if answer_bytes > limits.max_answer_bytes:
        return PlanAIOutcome(None, replace(audit, reason=REASON_ANSWER_BUDGET))
    order = parse_order(turn.text, expected)
    if order is None:
        return PlanAIOutcome(None, replace(audit, reason=REASON_NOT_A_PERMUTATION))
    return PlanAIOutcome(order, audit)


def _run_blocking(call: Callable[[], PlanAIOutcome], *, deadline_seconds: float) -> PlanAIOutcome:
    """在独立线程里跑 `asyncio.run`，最多等 `deadline_seconds`。

    超时后线程**被放弃而非取消**（daemon，不阻塞进程退出，但也不会被强杀）。真正的单次调用上限是
    传给 `create_turn` 的 `model_timeout_seconds`；本函数只是外层兜底，防止桥本身挂住调用方。
    """
    box: dict[str, Any] = {}

    def runner() -> None:
        try:
            box["value"] = call()
        except BaseException as exc:  # noqa: BLE001 - 归一到原因码，绝不外泄
            box["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(deadline_seconds)
    if thread.is_alive():
        return PlanAIOutcome(None, PlanAIAudit(reason=REASON_DEADLINE))
    if "error" in box:
        return PlanAIOutcome(None, PlanAIAudit(reason=_provider_reason(box["error"])))
    value = box.get("value")
    if not isinstance(value, PlanAIOutcome):
        return PlanAIOutcome(None, PlanAIAudit(reason=REASON_PROVIDER_UNAVAILABLE))
    return value


def limit_env_names() -> tuple[str, ...]:
    """暴露可收紧的预算环境变量名，供配置层与测试共用同一份清单。"""
    return tuple(f"SA_PLAN_AI_{field.name.upper()}" for field in fields(PlanAILimits))
