"""M9 外部 AI 路径的**真实 provider** 读数（显式 opt-in、**非门禁**）。

## 为什么单独一个文件

`test_plan_ai_benchmark.py` 用确定性 stub 冻结的是**预算被强制执行**这一事实，不是性能：那里的
`latency_ms` 是桥接开销，`estimated_cost_usd` 由脚本化 usage 算出。真实 provider 的延迟 / 成本 /
失败模式**只能**在这里读，且必须由人显式启动。

## 承重的是 skip 门控，不是 marker

本文件在 `tests/M9/` 内，而 CI 的阶段测试步骤**不排除** `online` 标记（只排除 `slow` /
`m6b_benchmark` / `m9_benchmark`）。故「默认不跑」完全由 `M9_PROVIDER_SMOKE` 未设时的
`pytest.skip` 承担；把它去掉会让 CI 试图用真凭据打真网络。
同理，本文件**绝不**触碰 workflow：`tests/regression/test_ci_contract.py` 明文禁止
`ANTHROPIC_API_KEY` / `SA_PLAN_AI_TOKEN` / `SA_PLAN_AI_ENABLED` 出现在其中。

## 这不是什么

对齐 `M6B-P95` 的真实 Anthropic smoke 条款：**该小样本不是稳定 SLA，不阻塞默认离线 CI，也不得
冒充离线 benchmark**。它同样**不是** M9 的退出证据——任何门禁、退出条件与登记表都不得依赖本文件。
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform as runtime_platform
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from app import config
from app.goal_planner import GoalPlannerService
from app.llm_client import MODEL_ID
from app.plan_ai_adapter import (
    REASON_ADOPTED,
    REASON_ANSWER_BUDGET,
    REASON_COST_BUDGET,
    REASON_DEADLINE,
    REASON_NOT_A_PERMUTATION,
    REASON_PROMPT_BUDGET,
    REASON_PROVIDER_REJECTED,
    REASON_PROVIDER_TIMEOUT,
    REASON_PROVIDER_UNAVAILABLE,
    REASON_UNPARSABLE,
    PlanAIAdapter,
    PlanAILimits,
    build_anthropic_proposer,
)
from app.topic_graph_projection import TopicGraphProjection
from tests.M9.test_plan_ai_benchmark import _WORKLOAD, _request, _tasks, _workload_digest
from tools.run_m7_benchmark import PRINCIPAL, percentile

pytestmark = [pytest.mark.m9, pytest.mark.online]

_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_SMOKE_HOURS_PER_DAY = 2.0
# 每轮跑一遍全部 workload：5 × 2 = 10 个固定 case（对齐 `M6B-P95` 的「至少 10 个」）。
_ROUNDS = (1, 2)
# 默认花费上限。`PlanAILimits.max_cost_usd` 是 $0.10/次，10 次最坏 $1.00。
_DEFAULT_SPEND_CAP_USD = 1.0
# 单次调用的最坏成本上界（默认 token 预算 × 冻结价目表），用于给「事后累加」的闸门留出余量。
_SINGLE_CALL_WORST_CASE_USD = 0.30
# provider 凭据的最小长度；与 `config` 对 `SA_PLAN_AI_TOKEN` 的校验同口径。
_MIN_TOKEN_BYTES = 32
_KNOWN_REASONS = frozenset(
    {
        REASON_ADOPTED,
        REASON_ANSWER_BUDGET,
        REASON_COST_BUDGET,
        REASON_DEADLINE,
        REASON_NOT_A_PERMUTATION,
        REASON_PROMPT_BUDGET,
        REASON_PROVIDER_REJECTED,
        REASON_PROVIDER_TIMEOUT,
        REASON_PROVIDER_UNAVAILABLE,
        REASON_UNPARSABLE,
    }
)

_CASES = tuple(
    {"workload": spec["name"], "round": round_index}
    for spec in _WORKLOAD
    for round_index in _ROUNDS
)
_SPECS_BY_NAME = {spec["name"]: spec for spec in _WORKLOAD}


def _smoke_enabled() -> bool:
    return os.getenv("M9_PROVIDER_SMOKE", "").strip().lower() in {"1", "true", "yes"}


def _run_id() -> str:
    value = os.getenv("M9_PROVIDER_SMOKE_RUN_ID")
    if value is None:
        return "local-unrecorded"
    if _RUN_ID_PATTERN.fullmatch(value) is None:
        raise AssertionError("M9 provider smoke run ID is invalid")
    return value


def _spend_cap() -> float:
    raw = os.getenv("M9_PROVIDER_SMOKE_MAX_USD")
    if raw is None:
        return _DEFAULT_SPEND_CAP_USD
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        raise AssertionError("M9_PROVIDER_SMOKE_MAX_USD must be a finite positive number")
    return value


def _write_report(report: Mapping[str, Any], run_id: str) -> None:
    """独占创建报告：已存在即 `FileExistsError`，避免覆盖上一轮读数。"""
    report_path = os.getenv("M9_PROVIDER_SMOKE_REPORT")
    if report_path is None:
        return
    if os.getenv("M9_PROVIDER_SMOKE_RUN_ID") is None:
        raise AssertionError("recorded provider smoke evidence requires an explicit run ID")
    destination = Path(report_path)
    if run_id not in destination.name:
        raise AssertionError("provider smoke report name must contain its run ID")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def _tasks_for(spec: Mapping[str, Any]) -> list:
    """真实知识库上的冻结任务集；不注入 AI，故取到的是确定性基线。"""
    planner = GoalPlannerService(topic_graph=TopicGraphProjection())
    return _tasks(planner.generate(_request(spec), PRINCIPAL))


def test_provider_smoke_run_id_rejects_unsafe_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("M9_PROVIDER_SMOKE_RUN_ID", "unsafe/path")

    with pytest.raises(AssertionError, match="run ID is invalid"):
        _run_id()


def test_provider_smoke_report_is_exclusive_and_identity_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "exclusive-create-test"
    destination = tmp_path / f"m9-plan-ai-provider-smoke-{run_id}.json"
    monkeypatch.setenv("M9_PROVIDER_SMOKE_RUN_ID", run_id)
    monkeypatch.setenv("M9_PROVIDER_SMOKE_REPORT", str(destination))
    report = {"run_id": run_id, "gating": False}

    _write_report(report, _run_id())

    assert json.loads(destination.read_text(encoding="utf-8")) == report
    with pytest.raises(FileExistsError):
        _write_report(report, run_id)


def test_real_provider_reading_is_opt_in_and_sanitized() -> None:
    """真实 provider 读数：固定 case 集、脱敏字段、事后花费闸门。

    默认 **skip**——它要真凭据、真网络、真花费。启动方式见本文件末的注释。
    """
    if not _smoke_enabled():
        pytest.skip("real provider smoke is opt-in via M9_PROVIDER_SMOKE=1")
    token = config.PLAN_AI_TOKEN
    if len(token.encode("utf-8")) < _MIN_TOKEN_BYTES:
        pytest.skip("no provider credential present (SA_PLAN_AI_TOKEN / ANTHROPIC_API_KEY)")

    limits = PlanAILimits()
    # 走**生产** proposer：默认 `client_factory=AnthropicLLMClient`，真发请求。
    adapter = PlanAIAdapter(
        proposer=build_anthropic_proposer(token=token),
        limits=limits,
        enabled=True,
    )
    cap = _spend_cap()
    tasks_by_workload = {spec["name"]: _tasks_for(spec) for spec in _WORKLOAD}
    assert all(tasks_by_workload.values()), "a frozen workload yielded no tasks"

    rows: list[dict[str, Any]] = []
    spent = 0.0
    aborted_early = False
    for case in _CASES:
        spec = _SPECS_BY_NAME[case["workload"]]
        outcome = adapter.propose_for(
            goal=spec["goal"],
            course=spec["course"],
            hours_per_day=_SMOKE_HOURS_PER_DAY,
            required_topics=spec["required"],
            excluded_topics=spec["excluded"],
            mastery_counts={},
            tasks=tasks_by_workload[case["workload"]],
        )
        audit = outcome.audit
        spent += audit.estimated_cost_usd
        # **只**记脱敏字段：没有 prompt 正文、没有 provider 原文、没有路径、没有异常文本。
        rows.append(
            {
                "workload": case["workload"],
                "round": case["round"],
                "reason": audit.reason,
                "order_proposed": outcome.order is not None,
                "prompt_bytes": audit.prompt_bytes,
                "answer_bytes": audit.answer_bytes,
                "input_tokens": audit.input_tokens,
                "output_tokens": audit.output_tokens,
                "estimated_cost_usd": audit.estimated_cost_usd,
                "latency_ms": audit.latency_ms,
            }
        )
        if spent >= cap:
            aborted_early = True
            break

    latencies = [row["latency_ms"] for row in rows]
    p95 = percentile(latencies, 0.95)
    run_id = _run_id()
    report = {
        "schema_version": "m9-plan-ai-provider-smoke-v1",
        "run_id": run_id,
        "gating": False,
        "scope": "m9.external-ai real provider reading; manual opt-in, non-gating",
        "evaluation_scope": (
            "the M9 external AI path only (m9.external-ai), on the same frozen workload as the "
            "offline benchmark. This is a small manual sample, not a project-wide evaluation."
        ),
        "model": MODEL_ID,
        "workload_digest": _workload_digest(),
        "limits": {
            "deadline_seconds": limits.deadline_seconds,
            "model_timeout_seconds": limits.model_timeout_seconds,
            "max_input_tokens": limits.max_input_tokens,
            "max_output_tokens": limits.max_output_tokens,
            "max_cost_usd": limits.max_cost_usd,
            "max_prompt_bytes": limits.max_prompt_bytes,
            "max_answer_bytes": limits.max_answer_bytes,
        },
        "case_count": len(rows),
        "cases": rows,
        "environment": {
            "os": runtime_platform.platform(),
            "python": runtime_platform.python_version(),
            "provider": "anthropic-messages (real network)",
        },
        "spend": {
            "cap_usd": cap,
            "estimated_usd": spent,
            "aborted_early": aborted_early,
            "note": (
                "the cap is checked after each call, so the worst case is cap + one call; "
                "estimated_usd comes from provider-reported usage, not from a billing API"
            ),
        },
        "latency_ms": {
            "label": "real provider end-to-end; small sample, NOT a stable SLA",
            "samples": len(latencies),
            "p50": percentile(latencies, 0.50),
            "p95": p95,
            "max": max(latencies) if latencies else 0.0,
            "within_hard_deadline": p95 < limits.deadline_seconds * 1000.0,
        },
        "usage": {
            "input_tokens_total": sum(row["input_tokens"] for row in rows),
            "output_tokens_total": sum(row["output_tokens"] for row in rows),
            "adopted": sum(1 for row in rows if row["reason"] == REASON_ADOPTED),
        },
        "not_evidence_for": [
            "a stable SLA: this is a small manual sample, not a benchmark",
            "the offline CI gate: this run never blocks or substitutes for it",
            "10K/100K capacity (M8 BLOCKED / M11 proposed)",
            "the M9 exit conditions: no gate, exit condition or registry may depend on this run",
        ],
    }
    report["report_digest"] = hashlib.sha256(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    # 报告先落盘：即便下面的断言判红，读数也已经被保留下来。
    _write_report(report, run_id)

    assert rows, "the opt-in smoke attempted no case"
    assert all(row["reason"] in _KNOWN_REASONS for row in rows), rows
    # **承重断言：必须真的读到了 provider。** 本烟测的全部价值就在于此，而
    # `provider_unavailable` **也在** `_KNOWN_REASONS` 里——若一次都没触达（token 失效、网络不通、
    # 模型名写错），下面每条断言都照样通过，报告看起来像一次成功读数，实际什么都没测到，owner 却
    # 以为拿到了真实读数。故显式要求「至少有一次调用真正回来了」，并以 provider **自报**的 usage
    # 为证据（本地无从伪造）：触达过 ⇒ input_tokens 必大于 0。
    reached = [row for row in rows if row["reason"] != REASON_PROVIDER_UNAVAILABLE]
    assert reached, (
        "no case reached the provider: every call returned provider_unavailable, "
        "so this run is not a provider reading"
    )
    assert report["usage"]["input_tokens_total"] > 0, (
        "provider-reported usage is all zero: no call actually returned"
    )
    assert spent <= cap + _SINGLE_CALL_WORST_CASE_USD, report["spend"]
    assert p95 < limits.deadline_seconds * 1000.0, "provider p95 exceeded the hard deadline"
    assert len(report["report_digest"]) == 64


# 运行方式（需要 owner 自己的凭据，且会花真钱）：
#   SA_PLAN_AI_TOKEN=... M9_PROVIDER_SMOKE=1 \
#   M9_PROVIDER_SMOKE_RUN_ID=<id> M9_PROVIDER_SMOKE_REPORT=/path/m9-plan-ai-provider-smoke-<id>.json \
#   ./platform/.venv/Scripts/python -m pytest tests/M9/test_plan_ai_provider_smoke.py -q -m online
# 花费上限默认 $1.00，可用 M9_PROVIDER_SMOKE_MAX_USD 覆盖。
