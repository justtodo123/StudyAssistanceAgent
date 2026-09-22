"""M9 可选外部 AI 计划路径测试（`m9.external-ai`）。

覆盖四件事：**最小披露是结构性的**（送出去的载荷里根本没有路径/正文/principal 字段可送）、
**预算只允许收紧**、**任何失败都逐字回退且不产生半成品计划**、以及**确定性校验器真的在裁决**
（AI 提出的非法顺序会被拒，不是照单全收）。

AI 路径全程用注入的同步 stub 驱动，**离线可复现**；真实 provider 不在本套件内。
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.goal_planner import GoalPlannerService
from app.learning_store import SqliteLearningStore
from app.llm_client import MAX_TURN_OUTPUT_TOKENS, ModelTurn, ModelUsage
from app.models import GoalPlanConstraints, GoalPlanRequest
from app.plan_ai_adapter import (
    AUTHORIZED_SCOPE_ID,
    PLAN_AI_SCHEMA_VERSION,
    REASON_ADOPTED,
    REASON_COST_BUDGET,
    REASON_DISABLED,
    REASON_NOT_A_PERMUTATION,
    REASON_PROMPT_BUDGET,
    REASON_PROVIDER_UNAVAILABLE,
    PlanAIAdapter,
    PlanAIAudit,
    PlanAILimits,
    PlanAIOutcome,
    PlanAIRequest,
    PlanAITaskSummary,
    build_anthropic_proposer,
    limit_env_names,
    parse_order,
    render_prompt,
)
from app.topic_graph_projection import TopicGraphProjection


pytestmark = pytest.mark.m9


def _request(**kwargs) -> GoalPlanRequest:
    defaults = {"goal": "两周内掌握进程调度与死锁", "course": "os"}
    defaults.update(kwargs)
    return GoalPlanRequest(**defaults)


def _tasks(plan) -> list:
    return [task for day in plan.revisions[0].days for task in day.tasks]


def _stable(plan) -> dict:
    """计划的逐字段快照，剔除 `generated_at`。

    两次 `generate()` 必然得到不同的时间戳，直接比 `model_dump()` 会比出一处与本次改动无关的差异，
    掩盖真正想断言的「顺序/身份/摘要是否变了」。
    """
    dumped = plan.model_dump()
    for revision in dumped["revisions"]:
        revision.pop("generated_at", None)
    return dumped


def _stub(order, *, audit=None, error=None):
    """构造一个同步 stub proposer；`error` 非空时抛出，用于测失败回退。"""

    def propose(request, limits):
        if error is not None:
            raise error
        return PlanAIOutcome(
            None if order is None else tuple(order),
            audit or PlanAIAudit(reason=REASON_ADOPTED),
        )

    return propose


def _adapter(order, **kwargs):
    return PlanAIAdapter(proposer=_stub(order, **kwargs), enabled=True)


def _planner(adapter) -> GoalPlannerService:
    return GoalPlannerService(review_history={}, plan_ai=adapter)


# ── 最小披露 ────────────────────────────────────────────────────────────────


def test_task_summary_has_no_path_or_identity_field():
    """最小披露的**结构性**保证：摘要类型上没有可送路径/主体的字段。

    这比「渲染时过滤掉」强：新增字段必须显式过一遍白名单，而不是默默漏出去。
    """
    names = {field.name for field in fields(PlanAITaskSummary)}
    assert names == {"task_id", "topic", "difficulty", "tags"}


def test_request_has_no_path_principal_or_body_field():
    names = {field.name for field in fields(PlanAIRequest)}
    assert names == {
        "goal",
        "course",
        "hours_per_day",
        "required_topics",
        "excluded_topics",
        "scope_id",
        "mastery_counts",
        "tasks",
    }


def test_prompt_carries_only_the_whitelisted_keys(goal_planner_service):
    plan = goal_planner_service.generate(_request())
    tasks = _tasks(plan)
    request = PlanAIRequest(
        goal="两周内掌握进程调度与死锁",
        course="os",
        hours_per_day=2.0,
        required_topics=("进程调度",),
        excluded_topics=("死锁",),
        scope_id=AUTHORIZED_SCOPE_ID,
        mastery_counts={"no_evidence": 3, "attempted": 1, "mastered": 0},
        tasks=tuple(
            PlanAITaskSummary(
                task_id=t.task_id, topic=t.topic, difficulty=t.difficulty, tags=tuple(t.tags)
            )
            for t in tasks
        ),
    )
    payload = json.loads(render_prompt(request).split("\n\n")[-1])

    assert set(payload) == {
        "schema_version",
        "goal",
        "course",
        "hours_per_day",
        "required_topics",
        "excluded_topics",
        "scope_id",
        "mastery_counts",
        "tasks",
    }
    assert payload["schema_version"] == PLAN_AI_SCHEMA_VERSION
    assert payload["scope_id"] == AUTHORIZED_SCOPE_ID
    for item in payload["tasks"]:
        assert set(item) == {"task_id", "topic", "difficulty", "tags"}


def test_prompt_never_leaks_paths_principal_or_chunk_bodies():
    """真语料 + 真 principal 下，prompt 里不得出现文件路径、用户源或 chunk 正文。"""
    planner = GoalPlannerService(review_history={})
    plan = planner.generate(_request(course="os"))
    tasks = _tasks(plan)
    assert tasks, "expected the os corpus to yield tasks"

    request = PlanAIRequest(
        goal="两周内掌握进程调度与死锁",
        course="os",
        hours_per_day=2.0,
        required_topics=(),
        excluded_topics=(),
        scope_id=AUTHORIZED_SCOPE_ID,
        mastery_counts={"no_evidence": len(tasks), "attempted": 0, "mastered": 0},
        tasks=tuple(
            PlanAITaskSummary(
                task_id=t.task_id, topic=t.topic, difficulty=t.difficulty, tags=tuple(t.tags)
            )
            for t in tasks
        ),
    )
    prompt = render_prompt(request)

    # 任务以不透明 task_id 标识；其 file 路径一个都不许出现。
    for task in tasks:
        assert task.file not in prompt, f"prompt leaked the file path {task.file!r}"
    assert "knowledge/" not in prompt
    assert "knowledge\\" not in prompt
    assert "user://" not in prompt
    assert "principal" not in prompt.lower()
    assert "C:\\" not in prompt
    # 正文标记：chunk 切分产生的标题锚点不该出现在载荷里。
    assert "##" not in prompt


def test_authorized_scope_id_matches_the_registry(repo_root: Path):
    """载荷里送的 scope 标识必须与登记表的 `scope_id` 一致，否则两处会静默漂移。"""
    registry = json.loads(
        (repo_root / "docs" / "standards" / "stage-admission-gates.json").read_text(
            encoding="utf-8"
        )
    )
    m9 = next(stage for stage in registry["stages"] if stage["stage"] == "M9")
    assert m9["approval_scope"]["scope_id"] == AUTHORIZED_SCOPE_ID
    assert "m9.external-ai" in m9["approval_scope"]["included"]


def test_mastery_is_sent_as_aggregate_counts_not_per_file_values(goal_planner_service):
    plan = goal_planner_service.generate(_request())
    tasks = _tasks(plan)
    adapter = _adapter([t.task_id for t in tasks])
    seen: list[PlanAIRequest] = []
    adapter._proposer = lambda request, limits: (
        seen.append(request) or PlanAIOutcome(None, PlanAIAudit(reason=REASON_ADOPTED))
    )
    _planner(adapter).generate(_request())

    assert seen, "the adapter was never asked to propose"
    counts = seen[0].mastery_counts
    assert set(counts) == {"no_evidence", "attempted", "mastered"}
    assert all(isinstance(value, int) for value in counts.values())


# ── 预算只允许收紧 ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name, relaxed",
    (
        ("deadline_seconds", 999.0),
        ("model_timeout_seconds", 999.0),
        ("max_input_tokens", 10**9),
        ("max_output_tokens", 10**9),
        ("max_turn_output_tokens", 10**9),
        ("max_cost_usd", 99.0),
        ("max_prompt_bytes", 10**9),
        ("max_answer_bytes", 10**9),
        ("max_retries", 9),
    ),
)
def test_limits_cannot_be_relaxed(name, relaxed):
    with pytest.raises(ValueError):
        PlanAIAdapter(limits=replace(PlanAILimits(), **{name: relaxed}))


@pytest.mark.parametrize("name", ("deadline_seconds", "model_timeout_seconds", "max_cost_usd"))
def test_limits_reject_non_positive_floats(name):
    for bad in (0.0, -1.0, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            PlanAIAdapter(limits=replace(PlanAILimits(), **{name: bad}))


@pytest.mark.parametrize(
    "name",
    (
        "max_input_tokens",
        "max_output_tokens",
        "max_turn_output_tokens",
        "max_prompt_bytes",
        "max_answer_bytes",
    ),
)
def test_limits_reject_non_positive_ints(name):
    for bad in (0, -1):
        with pytest.raises(ValueError):
            PlanAIAdapter(limits=replace(PlanAILimits(), **{name: bad}))


def test_tightened_limits_are_accepted():
    limits = PlanAILimits(
        deadline_seconds=5.0, max_prompt_bytes=512, max_answer_bytes=256, max_cost_usd=0.01
    )
    assert PlanAIAdapter(limits=limits).limits.max_prompt_bytes == 512


# ── 单轮 output 预算：累积值与单轮值是**两个**字段 ──────────────────────────
#
# 已证实缺陷的回归：`max_output_tokens`（累积，2048）曾被**直接**当作 `create_turn` 的
# `max_tokens` 传下去，而 `llm_client.create_turn` 硬拒大于 `MAX_TURN_OUTPUT_TOKENS`（1024）的值。
# 于是**默认配置下**每次调用都在发出任何 HTTP 请求之前抛 ValueError，被回退路径收敛成
# `provider_unavailable`——整条外部 AI 路径静默失效，而**本文件修复前收集的 50 项全绿**：其中凡是
# 构造 adapter 的都经 `proposer=` 注入同步 stub（其余只碰 dataclass / 载荷 / 解析 / 预算校验等接缝，
# 根本不构造 adapter），故没有一项触到那个调用点。**但盲区不止于此**：修复前**默认运行**的真实桥
# 驱动者 `test_plan_ai_benchmark.py` **穿过**了那个调用点却仍全绿，因为它的 `_StubClient.create_turn`
# 把 `max_tokens` 丢掉（`del … max_tokens …`），超限的 2048 照样通过。（`test_plan_ai_provider_smoke.py`
# 同样走真实桥，但它默认 skip、本次未运行。）真教训是**桥接 stub 必须复刻客户端的硬拒**，
# 不只是「`proposer=` 注入会绕过调用点」。故本节的断言必须驱动**真实桥**
# （`build_anthropic_proposer`），且下面的 `_RecordingClient` 刻意复刻了那道硬拒。


class _RecordingClient:
    """离线假 provider：记录 `create_turn` 收到的 `max_tokens`，并复刻真实客户端的硬拒。"""

    def __init__(self, *, order: Sequence[str], seen: list[int]) -> None:
        self._order = list(order)
        self._seen = seen

    def new_conversation(self, prompt: str) -> object:
        del prompt
        return object()

    async def create_turn(
        self, conversation: object, tools: Sequence[object], *, max_tokens: int, timeout: float
    ) -> ModelTurn:
        del conversation, tools, timeout
        if not 1 <= max_tokens <= MAX_TURN_OUTPUT_TOKENS:
            # 与 `AnthropicLLMClient.create_turn` 同形。这正是被回退路径吞掉的那一步：
            # 真实客户端在此抛 ValueError，调用方只看得到 provider_unavailable。
            raise ValueError("max_tokens exceeds the M6b hard limit")
        self._seen.append(max_tokens)
        return ModelTurn(
            text=json.dumps({"order": self._order}),
            tool_calls=(),
            stop_reason="end_turn",
            usage=ModelUsage(input_tokens=10, output_tokens=10),
            latency_ms=1.0,
        )

    async def close(self) -> None:
        return None


def _single_task_request() -> PlanAIRequest:
    return PlanAIRequest(
        goal="两周内掌握进程调度与死锁",
        course="os",
        hours_per_day=2.0,
        required_topics=(),
        excluded_topics=(),
        scope_id=AUTHORIZED_SCOPE_ID,
        mastery_counts={},
        tasks=(PlanAITaskSummary(task_id="t1", topic="调度", difficulty="基础", tags=()),),
    )


def test_default_limits_actually_reach_the_provider():
    """默认预算必须能走到 provider：旧行为在此抛 ValueError 并静默回退成 provider_unavailable。"""
    seen: list[int] = []
    adapter = PlanAIAdapter(
        proposer=build_anthropic_proposer(
            token="offline-token-not-a-credential",
            client_factory=lambda key: _RecordingClient(order=("t1",), seen=seen),
        ),
        enabled=True,
    )

    outcome = adapter.propose(_single_task_request())

    assert outcome.audit.reason == REASON_ADOPTED
    assert outcome.audit.reason != REASON_PROVIDER_UNAVAILABLE
    assert outcome.order == ("t1",)


def test_default_per_turn_budget_is_what_reaches_the_client():
    """传给 `create_turn` 的是**单轮**预算，且默认值就在客户端硬上限上——不是累积值。"""
    seen: list[int] = []
    adapter = PlanAIAdapter(
        proposer=build_anthropic_proposer(
            token="offline-token-not-a-credential",
            client_factory=lambda key: _RecordingClient(order=("t1",), seen=seen),
        ),
        enabled=True,
    )

    adapter.propose(_single_task_request())

    assert seen == [MAX_TURN_OUTPUT_TOKENS]
    assert PlanAILimits().max_output_tokens > MAX_TURN_OUTPUT_TOKENS  # 累积值本就更大


def test_default_per_turn_budget_sits_within_both_ceilings():
    limits = PlanAILimits()

    assert limits.max_turn_output_tokens <= MAX_TURN_OUTPUT_TOKENS
    assert limits.max_turn_output_tokens <= limits.max_output_tokens


def test_per_turn_budget_cannot_exceed_the_cumulative_budget():
    """单轮 > 累积是自相矛盾的预算，必须在构造时拒绝。"""
    with pytest.raises(ValueError):
        PlanAIAdapter(limits=replace(PlanAILimits(), max_output_tokens=512))


def test_per_turn_budget_env_var_is_wired_and_tightens_only(monkeypatch: pytest.MonkeyPatch):
    """配置层必须真的读这个变量，且只能收紧；否则新字段会静默不可配置。"""
    from app import config

    monkeypatch.setenv("SA_PLAN_AI_MAX_TURN_OUTPUT_TOKENS", "512")
    assert config.plan_ai_limits().max_turn_output_tokens == 512

    monkeypatch.setenv("SA_PLAN_AI_MAX_TURN_OUTPUT_TOKENS", str(MAX_TURN_OUTPUT_TOKENS + 1))
    with pytest.raises(ValueError):
        config.plan_ai_limits()


def test_advertised_budget_env_names_are_exactly_the_honoured_ones() -> None:
    """`limit_env_names()` 宣传的清单必须与配置层**兑现**的清单逐个相同。

    它曾按 `PlanAILimits` 的字段名推导，于是宣传了一个没人兑现的 `SA_PLAN_AI_MAX_RETRIES`
    （`max_retries` 有字段但刻意不可由环境变量覆盖）。操作者照它设值会**静默无效**——配置层不报错，
    预算也不收紧。这条用例把两份清单钉在一起，防止再次漂移。
    """
    from app import config

    honoured = {env_name for env_name, _ in config._PLAN_AI_LIMIT_ENV.values()}

    assert set(limit_env_names()) == honoured
    # 反向：`max_retries` 有字段但不可配置，故不得出现在宣传清单里。
    assert "SA_PLAN_AI_MAX_RETRIES" not in limit_env_names()
    # 宣传清单非空，否则「相等」会因两边都空而平凡成立。
    assert len(honoured) == len(PlanAILimits.__dataclass_fields__) - 1


# ── 回退：每一类失败都收敛为 order=None ─────────────────────────────────────


def test_disabled_adapter_always_falls_back():
    adapter = PlanAIAdapter(proposer=_stub(["x"]), enabled=False)
    assert adapter.enabled is False
    outcome = adapter.propose_for(
        goal="g",
        course="os",
        hours_per_day=2.0,
        required_topics=(),
        excluded_topics=(),
        mastery_counts={},
        tasks=[],
    )
    assert outcome.order is None
    assert outcome.audit.reason == REASON_DISABLED


def test_adapter_without_proposer_is_disabled():
    """默认构造即关闭：没有 proposer 就没有路径可走。"""
    assert PlanAIAdapter().enabled is False
    assert PlanAIAdapter(proposer=None, enabled=True).enabled is False


@pytest.mark.parametrize(
    "answer",
    (
        '{"order": ["a", "b", "c", "d"]}',      # 多一个
        '{"order": ["a", "b"]}',                # 少一个
        '{"order": ["a", "a", "b"]}',           # 重复（集合相等但长度不等）
        '{"order": ["a", "b", 1]}',             # 非字符串
        '{"order": "abc"}',                     # 非列表
        '{"items": ["a", "b", "c"]}',           # 键不对
        '{"order": ["a", "b", "x"]}',           # 替换了一个
        "not json at all",
        "[1, 2, 3]",
        "",
    ),
)
def test_parse_order_rejects_everything_that_is_not_a_permutation(answer):
    assert parse_order(answer, ["a", "b", "c"]) is None


def test_parse_order_accepts_a_permutation():
    assert parse_order('{"order": ["b", "a", "c"]}', ["a", "b", "c"]) == ("b", "a", "c")


def test_parse_order_accepts_a_fenced_permutation():
    assert parse_order('```json\n{"order": ["b", "a"]}\n```', ["a", "b"]) == ("b", "a")


def test_prompt_budget_rejects_before_calling_the_provider(goal_planner_service):
    calls: list[int] = []
    adapter = PlanAIAdapter(
        proposer=lambda request, limits: calls.append(1),
        limits=PlanAILimits(max_prompt_bytes=16),
        enabled=True,
    )
    outcome = adapter.propose_for(
        goal="两周内掌握进程调度与死锁",
        course="os",
        hours_per_day=2.0,
        required_topics=(),
        excluded_topics=(),
        mastery_counts={},
        tasks=_tasks(goal_planner_service.generate(_request())),
    )
    assert outcome.order is None
    assert outcome.audit.reason == REASON_PROMPT_BUDGET
    assert calls == [], "the provider must not be called once the prompt exceeds its budget"


def test_cost_budget_rejects_even_a_valid_order(goal_planner_service):
    """成本是硬上限，不是告警阈值：超了就不采纳，即便顺序合法。"""
    tasks = _tasks(goal_planner_service.generate(_request()))
    adapter = PlanAIAdapter(
        proposer=_stub(
            [t.task_id for t in tasks],
            audit=PlanAIAudit(reason=REASON_ADOPTED, estimated_cost_usd=5.0),
        ),
        limits=PlanAILimits(max_cost_usd=0.10),
        enabled=True,
    )
    outcome = adapter.propose_for(
        goal="g",
        course="os",
        hours_per_day=2.0,
        required_topics=(),
        excluded_topics=(),
        mastery_counts={},
        tasks=tasks,
    )
    assert outcome.order is None
    assert outcome.audit.reason == REASON_COST_BUDGET


def test_proposer_exception_falls_back_without_propagating(goal_planner_service):
    adapter = _adapter(None, error=RuntimeError("provider exploded"))
    tasks = _tasks(goal_planner_service.generate(_request()))
    outcome = adapter.propose_for(
        goal="g",
        course="os",
        hours_per_day=2.0,
        required_topics=(),
        excluded_topics=(),
        mastery_counts={},
        tasks=tasks,
    )
    assert outcome.order is None


def test_audit_never_carries_prompt_or_provider_text():
    """脱敏审计：只留规模与原因码，不留 prompt 正文、不留 provider 原文。"""
    names = {field.name for field in fields(PlanAIAudit)}
    assert names == {
        "reason",
        "prompt_bytes",
        "answer_bytes",
        "input_tokens",
        "output_tokens",
        "estimated_cost_usd",
        "latency_ms",
    }
    assert not any("text" in name or "body" in name for name in names)


# ── Planner 集成 ────────────────────────────────────────────────────────────


def test_planner_without_adapter_is_unchanged(goal_planner_service):
    """未注入 adapter：输出与接入前逐字节相同。"""
    plan = goal_planner_service.generate(_request())
    assert _stable(_planner(None).generate(_request())) == _stable(plan)


def test_disabled_adapter_is_byte_identical_to_no_adapter(goal_planner_service):
    """默认关闭是**恒等操作**，不是「跑了但结果一样」。"""
    baseline = goal_planner_service.generate(_request())
    disabled = _planner(PlanAIAdapter(proposer=_stub(["x"]), enabled=False)).generate(_request())
    assert _stable(disabled) == _stable(baseline)
    assert disabled.plan_id == baseline.plan_id


def test_disabled_adapter_never_calls_the_proposer(goal_planner_service):
    calls: list[int] = []
    adapter = PlanAIAdapter(proposer=lambda request, limits: calls.append(1), enabled=False)
    _planner(adapter).generate(_request())
    assert calls == []


def test_adopted_order_changes_the_plan(goal_planner_service):
    """AI 路径产出的是一份**自己的**计划：顺序变 ⇒ 身份变（顺序在派生摘要里）。"""
    baseline = goal_planner_service.generate(_request())
    reversed_ids = [t.task_id for t in reversed(_tasks(baseline))]
    assert reversed_ids != [t.task_id for t in _tasks(baseline)]

    ai_plan = _planner(_adapter(reversed_ids)).generate(_request())

    assert [t.task_id for t in _tasks(ai_plan)] == reversed_ids
    assert ai_plan.plan_id != baseline.plan_id
    assert ai_plan.summary["total_tasks"] == baseline.summary["total_tasks"]


def test_non_permutation_from_the_adapter_is_rejected(goal_planner_service):
    """adapter 是可注入接缝，故置换校验必须在 Planner 侧**再做一遍**。"""
    baseline = goal_planner_service.generate(_request())
    ids = [t.task_id for t in _tasks(baseline)]

    for bad in (ids[:-1], ids + ["deadbeef"], [ids[0]] * len(ids)):
        plan = _planner(_adapter(bad)).generate(_request())
        assert _stable(plan) == _stable(baseline), f"accepted a non-permutation: {bad}"


def _graph_planner(adapter) -> GoalPlannerService:
    return GoalPlannerService(
        review_history={}, topic_graph=TopicGraphProjection(), plan_ai=adapter
    )


def test_prerequisite_gate_rejects_an_illegal_order(goal_planner_service):
    """先修合法性是**闸门**：违反即整体回退到确定性顺序，不是就地修好。

    非空转的证明在同一个用例里：**同一个 adapter、同一个提案**，注入先修图时被拒，
    不注入图（无边可违反）时被采纳。两者唯一的差别就是那道闸门。
    """
    baseline = _graph_planner(None).generate(_request(course="os"))
    ids = [t.task_id for t in _tasks(baseline)]

    # deadlock 的先修是 synchronization；把它提到最前必然违反那条边。
    deadlock = next(t for t in _tasks(baseline) if t.file.endswith("deadlock.md"))
    violating = [deadlock.task_id] + [i for i in ids if i != deadlock.task_id]
    assert violating != ids

    with_gate = _graph_planner(_adapter(violating)).generate(_request(course="os"))
    assert [t.task_id for t in _tasks(with_gate)] == ids, "an illegal order was adopted"
    assert with_gate.summary["prerequisites"]["violations"] == 0
    assert with_gate.plan_id == baseline.plan_id

    # 同提案、同 adapter，只是没有图可违反 —— 必须被采纳，否则说明「拒绝」另有原因。
    without_gate = _planner(_adapter(violating)).generate(_request(course="os"))
    assert [t.task_id for t in _tasks(without_gate)] == violating


def test_ai_path_keeps_prerequisite_violations_at_zero(goal_planner_service):
    """`M9-EVALUATION` 的判据在 AI 路径上同样成立。"""
    planner = GoalPlannerService(
        review_history={},
        topic_graph=TopicGraphProjection(),
        plan_ai=_adapter(None),
    )
    plan = planner.generate(_request(course="os"))
    assert plan.summary["prerequisites"]["violations"] == 0


def _prereq_closure(graph: dict, present: set[str], seed: str) -> set[str]:
    """必选主题的**传递**先修闭包，限制在任务集内（与 `_pin_required` 同义）。"""
    closure = {seed}
    stack = [seed]
    while stack:
        for prereq in graph.get(stack.pop(), ()):
            if prereq in present and prereq not in closure:
                closure.add(prereq)
                stack.append(prereq)
    return closure


def test_required_topics_stay_pinned_even_when_ai_moves_them(goal_planner_service):
    """必选主题置顶由确定性侧**重新施加**：AI 把它挪走也挪不动。

    断言的是 `_pin_required` 真正给出的不变量——**必选主题的传递闭包块是前缀**。断言
    「必选主题排在第 0 位」是错的：闭包内还要再跑一次拓扑排序，必选主题未必在首位
    （os 课 `required=['死锁']` 时首位是它的传递先修「操作系统概述」）。
    """
    req = _request(course="os", constraints=GoalPlanConstraints(required_topics=["死锁"]))
    tasks = _tasks(_graph_planner(None).generate(req))
    ids = [t.task_id for t in tasks]

    seed = next(t for t in tasks if t.file.endswith("deadlock.md"))
    # 必选主题必须真的匹配上了任务集，否则 `_pin_required` 原样返回、本用例会空转。
    assert seed.topic.lower() == "死锁"

    closure = _prereq_closure(TopicGraphProjection().graph(), {t.file for t in tasks}, seed.file)
    assert len(closure) > 1, "死锁 没有先修，闭包退化为单点，测不到「块」"
    inside = {t.task_id for t in tasks if t.file in closure}
    outside = {t.task_id for t in tasks if t.file not in closure}

    # 把当前首个任务（属于闭包）挪到末尾：不重新施加置顶的话，闭包就不再是前缀。
    moved = ids[1:] + ids[:1]
    assert moved[0] in inside and moved[-1] in inside

    ai_ids = [t.task_id for t in _tasks(_graph_planner(_adapter(moved)).generate(req))]

    assert ai_ids != moved, "the AI order was adopted verbatim; the pin was not re-applied"
    assert max(ai_ids.index(i) for i in inside) < min(ai_ids.index(i) for i in outside)


def test_fallback_returns_the_original_list_object(goal_planner_service):
    """回退是**逐字**的：返回入参本身，而不是「重排成一样」的新列表。"""
    plan = goal_planner_service.generate(_request())
    tasks = _tasks(plan)
    planner = _planner(_adapter(None))
    assert planner._ai_order(tasks, _request(), {}) is tasks


def test_ai_path_does_not_write_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """失败回退不得落库：沿用真只读守卫（写入口全 fail + 连接级审计 + 库快照比对）。"""
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    store.save({"session_id": "seed", "course": "os", "status": "active"})

    observer = sqlite3.connect(str(store.db_path))
    observer.execute("PRAGMA query_only=ON")
    before = "\n".join(observer.iterdump())
    deltas: list[int] = []
    original_connect = store._connect

    @contextmanager
    def audited_connect():
        with original_connect() as connection:
            started = connection.total_changes
            yield connection
            deltas.append(connection.total_changes - started)

    monkeypatch.setattr(store, "_connect", audited_connect)
    for name in ("save", "save_review", "save_plan", "save_progress_event"):
        monkeypatch.setattr(
            SqliteLearningStore, name, lambda *a, **k: pytest.fail("the AI path wrote state")
        )

    # 一个会失败的回退路径，和一个会成功采纳的路径，两条都不许写。
    for adapter in (_adapter(None, error=RuntimeError("boom")), _adapter(None)):
        GoalPlannerService(review_history={}, plan_ai=adapter).generate(_request(course="os"))

    after = "\n".join(observer.iterdump())
    observer.close()
    assert hashlib.sha256(before.encode()).digest() == hashlib.sha256(after.encode()).digest()
    assert all(delta == 0 for delta in deltas)


def test_adapter_module_is_bounded_by_source():
    """adapter 模块只经 `llm_client` 的协议说话，不自己造 provider 抽象、不读知识库。"""
    import app.plan_ai_adapter as adapter_module

    source = Path(adapter_module.__file__).read_text(encoding="utf-8")
    assert "knowledge" not in source
    assert "split_headings" not in source
    assert "requests" not in source
    assert re.search(r"^from \.llm_client import", source, re.MULTILINE)
