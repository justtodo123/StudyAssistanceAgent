"""M9 冻结工作负载上的「确定性路径 vs 外部 AI 路径」比较（`m9.external-ai`，1K 语料）。

本文件是步骤 6 **窄口径**的证据面：在**同一冻结任务集**上把两条路径各跑一遍，断言它们受同一组
不变量约束（先修违反 == 0、stale/deleted Source 不进入、确定性可重放），并证明**输入有界**。

## 1K 语料是**只读复用** M7 的确定性生成器

`tools.run_m7_benchmark.build_corpus` / `publish_sources`（`sources=1, documents=100, units=10`
= 1000 chunks）把哈希种子生成的 markdown 物化到临时目录，**不落任何二进制、不持久化、不触碰
M8 数据面**。M7 已 `ADMITTED / COMPLETE` 且 `m7.1k-3k-benchmark-implementation` 本在其批准范围内，
故这是跨阶段**只读**耦合：本文件不修改 M7 的任何生产文件，只在测试进程内调用其生成器。

## 「输入有界」证的是什么（避免读成容量声明）

Planner 的任务集来自 `KNOWLEDGE_ROOT` 的 frontmatter，**不读 chunk 正文**；送往 provider 的载荷由
`PlanAIRequest` / `PlanAITaskSummary` 定义，两者都没有 chunk 或路径字段。于是：语料从 10 chunks
放大到 1000 chunks（可检索、可命中深端文档），**送往 AI 的 prompt 字节数与条目数逐字不变**。

这**不是**容量声明：M9 既不存储也不索引 1K chunks，1K 读数只证明**输入不随语料规模增长**。
10K/100K 容量验证属 M8（`BLOCKED`）/ M11（拟议）依赖，本文件不触碰。

## AI 路径在 CI 里用**确定性 stub**

真实 provider 不在本套件内（无网络、无凭据）。stub 提出的是**由先修图算出的合法相邻对换**，
故「AI 路径确实产出了一份不同的合法计划」不是空话；另有一路故意提出非法顺序，用来证明闸门在
1K 规模上同样生效。

## 预算矩阵证明的是**强制执行**，不是**性能**

本文件另有一张冻结的预算矩阵，逐项收紧一个预算并断言收敛到稳定原因码。它驱动的是**真实**的
`build_anthropic_proposer(client_factory=…)` 接缝——这一点是承重的：`_run_blocking` 的 deadline
守卫**只存在于那条路径上**，若像本文件其余用例那样用 `proposer=` 注入同步 stub 就会整个绕过它，
于是「deadline 被强制执行」是一句没有证据的话。

**但 stub 下没有任何性能读数**：`latency_ms` 是桥接开销（线程启动 + 一次 `asyncio.run`），
`estimated_cost_usd` 由脚本化的 usage 算出。两者都不是 provider 的测量值，故本文件只能冻结
**预算确实被强制执行**这一事实。真实 provider 的延迟 / 成本 / 失败模式见
`test_plan_ai_provider_smoke.py`（显式 opt-in、非门禁、本次未运行）。
"""

from __future__ import annotations

import hashlib
import json
import os
import platform as runtime_platform
import re
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from app import preview_agent
from app.goal_planner import GoalPlannerService, _prerequisite_report
from app.models import GoalPlanConstraints, GoalPlanRequest
from app.llm_client import ModelTurn, ModelUsage
from app.plan_ai_adapter import (
    REASON_ADOPTED,
    REASON_ANSWER_BUDGET,
    REASON_COST_BUDGET,
    REASON_DEADLINE,
    REASON_NOT_A_PERMUTATION,
    REASON_PROMPT_BUDGET,
    PlanAIAdapter,
    PlanAIAudit,
    PlanAILimits,
    PlanAIOutcome,
    _estimate_cost,
    build_anthropic_proposer,
    parse_order,
    render_prompt,
)
from app.source_registry import SourceLifecycleService, SqliteSourceRegistry
from app.source_summary_projection import SourceSummaryProjection
from app.topic_graph_projection import TopicGraphProjection
from app.user_source_search import UserSourceSearchService
from app.user_source_vector import HashVectorEmbedder
from tools.run_m7_benchmark import (
    PRINCIPAL,
    _install_unit_parser,
    build_corpus,
    percentile,
    publish_sources,
)


pytestmark = [pytest.mark.m9, pytest.mark.slow, pytest.mark.m9_benchmark]

_EVIDENCE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
# 冻结工作负载：覆盖不同课程与不同约束（§7 要求任务集覆盖课程/等级/约束的差异）。
_WORKLOAD = (
    {
        "name": "os-baseline",
        "goal": "两周内掌握操作系统核心概念",
        "course": "os",
        "required": [],
        "excluded": [],
    },
    {
        "name": "os-required-deadlock",
        "goal": "两周内掌握进程调度与死锁",
        "course": "os",
        "required": ["死锁"],
        "excluded": [],
    },
    {
        "name": "os-excluded-memory",
        "goal": "两周内掌握进程与并发",
        "course": "os",
        "required": [],
        "excluded": ["内存"],
    },
    {
        "name": "ds-baseline",
        "goal": "两周内掌握数据结构核心",
        "course": "ds",
        "required": [],
        "excluded": [],
    },
    {
        "name": "network-baseline",
        "goal": "两周内掌握网络分层",
        "course": "network",
        "required": [],
        "excluded": [],
    },
)
# 语料规模：(sources, documents, units)。`1k` 即 M7 的 `("1k-single", 1, 100, 10)` = 1000 chunks。
_SMALL_CORPUS = (1, 1, 10)
_LARGE_CORPUS = (1, 100, 10)

# ── 冻结预算矩阵 ────────────────────────────────────────────────────────────
# 每行收紧**恰好一项**预算，并断言收敛到**稳定原因码**。`provider_reached` 是承重字段：
# `prompt-budget` 必须在**调用 provider 之前**返回，否则「预算在入口就挡住」只是巧合。
_BUDGET_SCENARIOS = (
    {
        "name": "prompt-budget",
        "limits": {"max_prompt_bytes": 16},
        "stub": "legal",
        "expected_reason": REASON_PROMPT_BUDGET,
        "provider_reached": False,
    },
    {
        "name": "answer-budget",
        "limits": {"max_answer_bytes": 16},
        "stub": "oversized",
        "expected_reason": REASON_ANSWER_BUDGET,
        "provider_reached": True,
    },
    {
        "name": "cost-budget",
        "limits": {},
        "stub": "expensive",
        "expected_reason": REASON_COST_BUDGET,
        "provider_reached": True,
    },
    {
        "name": "deadline",
        "limits": {"deadline_seconds": 0.2},
        "stub": "blocking",
        "expected_reason": REASON_DEADLINE,
        "provider_reached": True,
    },
    {
        "name": "adopted",
        "limits": {},
        "stub": "legal",
        "expected_reason": REASON_ADOPTED,
        "provider_reached": True,
    },
    {
        "name": "not-a-permutation",
        "limits": {},
        "stub": "duplicate",
        "expected_reason": REASON_NOT_A_PERMUTATION,
        "provider_reached": True,
    },
)

_OFFLINE_TOKEN = "offline-provider-key"
_STUB_HOURS_PER_DAY = 2.0
# stub 自报的延迟；`propose()` 用**整次调用的墙钟**覆盖它，故这个常数不进入任何读数。
_STUB_REPORTED_LATENCY_MS = 0.25
# 超出 `answer-budget` 场景那 16 字节上限的答案长度。
_OVERSIZED_ANSWER_BYTES = 64
# `cost-budget` 场景的 usage：按冻结价目表算出 $0.30，高于默认 $0.10 上限。
_EXPENSIVE_USAGE = ModelUsage(input_tokens=10_000, output_tokens=2_000)
_CHEAP_USAGE = ModelUsage(input_tokens=64, output_tokens=16)
# `adopted` 场景的样本数，用来给 stub 延迟一个分布形状（**不是** SLA）。
_LATENCY_SAMPLES = 200
# 绑在冻结 `deadline_seconds`（30s）之下的松上限，只用来抓「数量级写错」。
_STUB_P95_BUDGET_MS = 1000.0
# 阻塞式 stub 的有界等待：即便测试自身失败，也不会让线程永久泄漏。
_GATE_TIMEOUT_SECONDS = 5.0
# 墙钟与 `time.monotonic` 是两个时钟，交叉校验时留少量余量。
_CLOCK_SLACK_MS = 25.0
# 冻结价目表（USD / 百万 token）。比的是**不漂移**，不是数字本身。
_FROZEN_INPUT_USD_PER_MILLION = 15.0
_FROZEN_OUTPUT_USD_PER_MILLION = 75.0
# `_estimate_cost` 的可复现表：(input_tokens, output_tokens, expected USD)。
_FROZEN_COST_TABLE = (
    (0, 0, 0.0),
    (1_000_000, 0, _FROZEN_INPUT_USD_PER_MILLION),
    (0, 1_000_000, _FROZEN_OUTPUT_USD_PER_MILLION),
    (10_000, 2_000, 0.30),
)
# 本地**真正执行**的预算；其余项不在本地执行，理由逐条写在报告里。
_ENFORCED_LOCALLY = (
    "max_prompt_bytes",
    "max_answer_bytes",
    "max_cost_usd",
    "deadline_seconds",
)
_NOT_ENFORCED_LOCALLY = (
    "max_input_tokens: no local tokenizer; byte budgets are used instead",
    "model_timeout_seconds: passed to the provider; provider-side only",
    "max_output_tokens: passed to the provider; provider-side only",
)


def _budget_scenario_digest() -> str:
    encoded = json.dumps(
        _BUDGET_SCENARIOS, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _workload_digest() -> str:
    encoded = json.dumps(_WORKLOAD, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _evidence_id() -> str:
    value = os.getenv("M9_BENCHMARK_EVIDENCE_ID")
    if value is None:
        return "local-unrecorded"
    if _EVIDENCE_ID_PATTERN.fullmatch(value) is None:
        raise AssertionError("M9 benchmark evidence ID is invalid")
    return value


def _write_report(report: Mapping[str, Any], evidence_id: str) -> None:
    """独占创建报告：已存在即 `FileExistsError`，避免覆盖上一轮证据。"""
    report_path = os.getenv("M9_BENCHMARK_REPORT")
    if report_path is None:
        return
    if os.getenv("M9_BENCHMARK_EVIDENCE_ID") is None:
        raise AssertionError("recorded M9 benchmark evidence requires an explicit ID")
    destination = Path(report_path)
    if evidence_id not in destination.name:
        raise AssertionError("M9 benchmark report name must contain its evidence ID")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def test_benchmark_evidence_id_rejects_unsafe_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("M9_BENCHMARK_EVIDENCE_ID", "unsafe/path")

    with pytest.raises(AssertionError, match="evidence ID is invalid"):
        _evidence_id()


def test_benchmark_report_is_exclusive_and_identity_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence_id = "exclusive-create-test"
    destination = tmp_path / f"m9-plan-ai-benchmark-{evidence_id}.json"
    monkeypatch.setenv("M9_BENCHMARK_EVIDENCE_ID", evidence_id)
    monkeypatch.setenv("M9_BENCHMARK_REPORT", str(destination))
    report = {"evidence_id": evidence_id, "schema_version": "test"}

    _write_report(report, _evidence_id())

    assert json.loads(destination.read_text(encoding="utf-8")) == report
    with pytest.raises(FileExistsError):
        _write_report(report, evidence_id)


# ── 语料 ────────────────────────────────────────────────────────────────────


class _Corpus:
    """一份物化并发布过的 M7 语料。"""

    def __init__(
        self,
        service: UserSourceSearchService,
        lifecycle: SourceLifecycleService,
        gold,
        root: Path,
    ):
        self.service = service
        self.lifecycle = lifecycle
        self.gold = gold
        self.root = root

    def hits(self, query: str) -> int:
        return len(self.service.search(principal_id=PRINCIPAL, query=query, top_k=5).chunks)

    @property
    def units(self) -> int:
        """语料的行数。

        M7 的 `_install_unit_parser` 把**每个非空行**映射为一个 unit，而每个 unit 就是一个 chunk
        （其 docstring 明说 "one visible unit per paragraph so 100 docs can yield 1,000 chunks"）。
        故行数即 chunk 数，且这是**量出来的**而不是从 `documents * units` 推出来的。
        """
        return sum(
            1
            for path in self.root.rglob("*.md")
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    @property
    def published(self) -> bool:
        """该源是否真的发布过（而不只是磁盘上有文件）。"""
        records = self.lifecycle.list_sources(principal_id=PRINCIPAL)
        return len(records) == 1 and records[0].published_generation is not None


def _materialize(root: Path, scale: tuple[int, int, int]) -> _Corpus:
    sources, documents, units = scale
    gold = build_corpus(root / "corpus", sources=sources, documents=documents, units=units)
    lifecycle = SourceLifecycleService(SqliteSourceRegistry(root / "registry.sqlite3"))
    service = UserSourceSearchService(
        root / "cache", lifecycle, vector_embedder=HashVectorEmbedder()
    )
    publish_sources(service, lifecycle, root / "corpus", sources=sources)
    return _Corpus(service, lifecycle, gold, root / "corpus")


@pytest.fixture
def unit_parser():
    """装上 M7 的确定性 unit parser，用完**恢复**。

    `_install_unit_parser` 是对 `app.user_source_snapshot` 模块函数的全局替换；泄漏到同进程的
    其他测试会静默改变它们解析出的 chunk 结构，故必须成对恢复，而不是依赖测试顺序。
    """
    import app.user_source_snapshot as snapshot_mod

    originals = (snapshot_mod.parse_file, snapshot_mod.normalize_document)
    _install_unit_parser()
    try:
        yield
    finally:
        snapshot_mod.parse_file, snapshot_mod.normalize_document = originals


# ── 冻结工作负载 ────────────────────────────────────────────────────────────


def _request(spec: Mapping[str, Any]) -> GoalPlanRequest:
    return GoalPlanRequest(
        goal=spec["goal"],
        course=spec["course"],
        constraints=GoalPlanConstraints(
            required_topics=list(spec["required"]), excluded_topics=list(spec["excluded"])
        ),
    )


def _tasks(plan) -> list:
    return [task for day in plan.revisions[0].days for task in day.tasks]


class _Capture:
    """记录送往 provider 的载荷，并把一个预设置换交回去。"""

    def __init__(self, order: list[str] | None) -> None:
        self.order = order
        self.requests: list[Any] = []

    def __call__(self, request, limits) -> PlanAIOutcome:
        self.requests.append(request)
        return PlanAIOutcome(
            None if self.order is None else tuple(self.order),
            PlanAIAudit(reason=REASON_ADOPTED),
        )


def _planner(corpus: _Corpus, capture: _Capture | None) -> GoalPlannerService:
    return GoalPlannerService(
        topic_graph=TopicGraphProjection(),
        source_summary=SourceSummaryProjection(corpus.lifecycle),
        plan_ai=None if capture is None else PlanAIAdapter(proposer=capture, enabled=True),
    )


def _adjacent_swap(tasks: list, graph: dict, *, want_violation: bool) -> list[str] | None:
    """找一对相邻任务，交换后**恰好**违反（`want_violation=True`）或不违反（`False`）先修。

    交换**相邻**元素只改变这两者之间的相对次序，故合法性只取决于它们之间有没有边——这让
    「构造一个合法/非法置换」不必搜索整个置换空间。

    参数按「想要什么结果」命名，不按「合法与否」命名：后者与 `violations` 的极性相反，写反了
    两条断言会**互换**着通过，看起来仍然全绿。

    合法候选从**尾部**往前找：`_pin_required` 返回 `置顶块 + 其余`，块内会被重新拓扑排序，故落在
    块内的合法对换会被静默归一化掉，看起来像「AI 的顺序没被采纳」。尾部候选几乎必然落在块外
    （块是严格前缀），从而真的能观察到采纳。
    """
    ids = [t.task_id for t in tasks]
    by_id = {t.task_id: t for t in tasks}
    order = range(len(tasks) - 1) if want_violation else reversed(range(len(tasks) - 1))
    for index in order:
        swapped = list(ids)
        swapped[index], swapped[index + 1] = swapped[index + 1], swapped[index]
        reordered = [by_id[task_id] for task_id in swapped]
        violates = bool(_prerequisite_report(reordered, graph)["violations"])
        if violates is want_violation:
            return swapped
    return None


# ── 冻结预算矩阵的驱动 ──────────────────────────────────────────────────────


def _stub_answer(behaviour: str, order: Sequence[str]) -> str:
    """按场景给出 provider 回复。`legal` / `expensive` / `blocking` 都是**合法置换**。"""
    if behaviour == "oversized":
        return "x" * _OVERSIZED_ANSWER_BYTES
    if behaviour == "duplicate":
        # 长度相同但集合不同 ⇒ 不是置换。
        return json.dumps({"order": [order[0], *order[1:-1], order[0]]})
    return json.dumps({"order": list(order)})


class _StubClient:
    """离线假 provider，只实现桥**真正调用**的三个方法。

    `count_tokens` / `append_tool_result` 不在 `_propose_async` 的调用序列里，故不实现——这是
    **故意**的：本类同时钉住「桥把哪几个方法当作承重面」。
    """

    def __init__(
        self,
        *,
        behaviour: str,
        order: Sequence[str],
        calls: list[int],
        gate: threading.Event | None,
    ) -> None:
        self._behaviour = behaviour
        self._order = list(order)
        self._calls = calls
        self._gate = gate

    def new_conversation(self, prompt: str) -> object:
        del prompt
        return object()

    async def create_turn(
        self,
        conversation: object,
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        timeout: float,
    ) -> ModelTurn:
        del conversation, tools, max_tokens, timeout
        self._calls.append(1)
        if self._gate is not None:
            # 同步阻塞事件循环线程：`_run_blocking` 的 join 会先超时并放弃本线程（daemon）。
            # 有界等待（而非无限）保证即便测试自身失败，线程也不会永久泄漏。
            self._gate.wait(_GATE_TIMEOUT_SECONDS)
        return ModelTurn(
            text=_stub_answer(self._behaviour, self._order),
            tool_calls=(),
            stop_reason="end_turn",
            usage=_EXPENSIVE_USAGE if self._behaviour == "expensive" else _CHEAP_USAGE,
            latency_ms=_STUB_REPORTED_LATENCY_MS,
        )

    async def close(self) -> None:
        return None


def _stub_adapter(
    scenario: Mapping[str, Any],
    *,
    order: Sequence[str],
    calls: list[int],
    gate: threading.Event | None,
) -> PlanAIAdapter:
    """构造**真实** `build_anthropic_proposer` 路径上的 adapter。

    刻意不用 `proposer=` 注入：那条接缝绕过 `_run_blocking`，于是 `deadline_seconds` 根本没有被
    执行的机会，断言它「被强制执行」会是假证据。
    """

    def client_factory(key: str) -> _StubClient:
        assert key == _OFFLINE_TOKEN, "the offline token must reach the client factory unchanged"
        return _StubClient(behaviour=scenario["stub"], order=order, calls=calls, gate=gate)

    return PlanAIAdapter(
        proposer=build_anthropic_proposer(token=_OFFLINE_TOKEN, client_factory=client_factory),
        limits=PlanAILimits(**scenario["limits"]),
        enabled=True,
    )


def _propose_with(adapter: PlanAIAdapter, spec: Mapping[str, Any], tasks: list) -> PlanAIOutcome:
    """走 adapter 自己的载荷构造（`propose_for`），而不是手工拼一个 `PlanAIRequest`。"""
    return adapter.propose_for(
        goal=spec["goal"],
        course=spec["course"],
        hours_per_day=_STUB_HOURS_PER_DAY,
        required_topics=spec["required"],
        excluded_topics=spec["excluded"],
        mastery_counts={},
        tasks=tasks,
    )


def _legal_order(tasks: list, graph: dict) -> list[str]:
    """一个合法置换；找不到可对换的相邻对时回落到恒等顺序（预算断言不依赖合法性）。"""
    return _adjacent_swap(tasks, graph, want_violation=False) or [t.task_id for t in tasks]


def _budget_rows(spec: Mapping[str, Any], tasks: list, graph: dict) -> list[dict[str, Any]]:
    """在冻结预算矩阵上逐场景驱动真实桥，返回逐行证据。"""
    legal = _legal_order(tasks, graph)
    rows: list[dict[str, Any]] = []
    for scenario in _BUDGET_SCENARIOS:
        calls: list[int] = []
        gate = threading.Event() if scenario["stub"] == "blocking" else None
        adapter = _stub_adapter(scenario, order=legal, calls=calls, gate=gate)
        try:
            outcome = _propose_with(adapter, spec, tasks)
        finally:
            # 放行被放弃的线程，避免 daemon 线程逐场景堆积。
            if gate is not None:
                gate.set()
        observed = outcome.audit.reason
        reason_matches = observed == scenario["expected_reason"]
        reached_matches = bool(calls) == scenario["provider_reached"]
        rows.append(
            {
                "scenario": scenario["name"],
                "limits": dict(scenario["limits"]),
                "stub": scenario["stub"],
                "expected_reason": scenario["expected_reason"],
                "observed_reason": observed,
                "expected_provider_reached": scenario["provider_reached"],
                "provider_reached": bool(calls),
                "provider_calls": len(calls),
                "order_returned": outcome.order is not None,
                "prompt_bytes": outcome.audit.prompt_bytes,
                "answer_bytes": outcome.audit.answer_bytes,
                "input_tokens": outcome.audit.input_tokens,
                "output_tokens": outcome.audit.output_tokens,
                "estimated_cost_usd": outcome.audit.estimated_cost_usd,
                "latency_ms": outcome.audit.latency_ms,
                "reason_matches": reason_matches,
                "provider_reached_matches": reached_matches,
                "enforced": reason_matches and reached_matches,
            }
        )
    return rows


def _latency_samples(spec: Mapping[str, Any], tasks: list, graph: dict) -> list[float]:
    """`adopted` 场景的 stub 延迟分布。

    取 `outcome.audit.latency_ms`——`propose()` 用**整次调用的墙钟**覆盖 provider 自报值，故这才是
    报告里那个字段的真身。早返回路径（prompt 预算）的该字段恒为 `0.0`，只有 `adopted` 能进分布。
    """
    legal = _legal_order(tasks, graph)
    calls: list[int] = []
    adapter = _stub_adapter({"limits": {}, "stub": "legal"}, order=legal, calls=calls, gate=None)
    samples: list[float] = []
    for _ in range(_LATENCY_SAMPLES):
        outcome = _propose_with(adapter, spec, tasks)
        assert outcome.audit.reason == REASON_ADOPTED, outcome.audit.reason
        samples.append(outcome.audit.latency_ms)
    assert len(calls) == _LATENCY_SAMPLES, "the stub was not reached once per sample"
    return samples


def test_frozen_workload_comparison_at_1k(
    tmp_path: Path,
    unit_parser: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SA_USE_VECTOR", "false")
    small = _materialize(tmp_path / "small", _SMALL_CORPUS)
    large = _materialize(tmp_path / "large", _LARGE_CORPUS)

    # 规模差异必须是真的：量出来的 chunk 数，不是从 `documents * units` 推出来的。
    assert (small.units, large.units) == (10, 1000), (small.units, large.units)
    # 而且真的发布过、真的可检索——否则「输入有界」是在两份没被索引的目录上证明的。
    assert small.published and large.published, "a corpus was not published"
    assert large.hits(large.gold[-1]["query"]) > 0, "the 1K corpus is not retrievable"

    graph = TopicGraphProjection().graph()
    rows: list[dict[str, Any]] = []
    bounded_ok = True

    # ── 冻结预算矩阵：驱动**真实**桥（`client_factory=`），不是 `proposer=` 注入 ──
    budget_spec = _WORKLOAD[0]
    budget_tasks = _tasks(_planner(large, None).generate(_request(budget_spec), PRINCIPAL))
    assert budget_tasks, "the frozen workload yielded no tasks"
    budget_rows = _budget_rows(budget_spec, budget_tasks, graph)
    latency_samples = _latency_samples(budget_spec, budget_tasks, graph)

    for spec in _WORKLOAD:
        req = _request(spec)
        baseline_planner = _planner(large, None)
        baseline = baseline_planner.generate(req, PRINCIPAL)
        tasks = _tasks(baseline)
        assert tasks, f"{spec['name']}: the frozen workload yielded no tasks"

        # 同一冻结任务集在两种语料规模下，送往 AI 的 prompt 字节数与条目数必须逐字相同。
        shapes = {}
        for scale_name, corpus in (("10", small), ("1000", large)):
            capture = _Capture(None)
            _planner(corpus, capture).generate(req, PRINCIPAL)
            assert len(capture.requests) == 1, f"{spec['name']}: the adapter was not consulted"
            request = capture.requests[0]
            shapes[scale_name] = (
                len(render_prompt(request).encode("utf-8")),
                len(request.tasks),
            )
        bounded_ok = bounded_ok and shapes["10"] == shapes["1000"]

        # 合法相邻对换：AI 路径产出一份**不同的**合法计划，而不是原样退回。
        legal = _adjacent_swap(tasks, graph, want_violation=False)
        illegal = _adjacent_swap(tasks, graph, want_violation=True)

        adopted = _planner(large, _Capture(legal)).generate(req, PRINCIPAL) if legal else None
        rejected = (
            _planner(large, _Capture(illegal)).generate(req, PRINCIPAL) if illegal else None
        )
        # 确定性可重放：同一 workload 跑两次得到逐字相同的 plan_id。
        replay = baseline_planner.generate(req, PRINCIPAL)

        for label, plan in (("deterministic", baseline), ("ai-legal", adopted), ("ai-illegal", rejected)):
            if plan is None:
                continue
            assert plan.summary["prerequisites"]["violations"] == 0, f"{spec['name']}/{label}"
        assert replay.plan_id == baseline.plan_id, f"{spec['name']}: replay is not deterministic"
        assert baseline.summary["sources"] == {"usable": 1}, f"{spec['name']}: source summary"

        rows.append(
            {
                "workload": spec["name"],
                "course": spec["course"],
                "required_topics": list(spec["required"]),
                "excluded_topics": list(spec["excluded"]),
                "tasks": len(tasks),
                "prompt_bytes_10_chunks": shapes["10"][0],
                "prompt_bytes_1000_chunks": shapes["1000"][0],
                "input_bounded": shapes["10"] == shapes["1000"],
                "legal_swap_available": legal is not None,
                # 逐字采纳：只在**没有必选主题**时成立——有必选主题时 `_pin_required` 会合法地
                # 覆盖 AI 的顺序（见下一行），那是置顶生效，不是采纳失败。
                "ai_legal_adopted_verbatim": adopted is not None
                and [t.task_id for t in _tasks(adopted)] == legal,
                # 真正要断言的：AI 路径确实产出了一份**自己的**计划，而不是原样退回。
                "ai_legal_differs": adopted is not None
                and [t.task_id for t in _tasks(adopted)] != [t.task_id for t in tasks],
                "illegal_swap_available": illegal is not None,
                "ai_illegal_fell_back": rejected is not None
                and [t.task_id for t in _tasks(rejected)] == [t.task_id for t in tasks],
                "prerequisite_violations": 0,
                "replay_identical": replay.plan_id == baseline.plan_id,
                "usable_sources": baseline.summary["sources"]["usable"],
            }
        )

    evidence_id = _evidence_id()
    report = {
        "schema_version": "m9-plan-ai-evaluation-v2",
        "evidence_id": evidence_id,
        "scope": "m9.external-ai narrow scope: 1K corpus, input-boundedness and budget enforcement",
        "evaluation_scope": (
            "the M9 external AI path only (m9.external-ai): input boundedness and budget "
            "enforcement under a deterministic stub. Not a project-wide evaluation, and not "
            "provider performance."
        ),
        "workload_digest": _workload_digest(),
        "budget_scenario_digest": _budget_scenario_digest(),
        "budget_scenarios": budget_rows,
        "budget_enforcement": {
            "enforced": sum(1 for row in budget_rows if row["enforced"]),
            "total": len(budget_rows),
            "rate": sum(1 for row in budget_rows if row["enforced"]) / len(budget_rows),
            "enforced_locally": list(_ENFORCED_LOCALLY),
            "not_enforced_locally": list(_NOT_ENFORCED_LOCALLY),
        },
        "stub_latency_ms": {
            "label": "deterministic-stub end-to-end; NOT provider latency",
            "samples": len(latency_samples),
            "p50": percentile(latency_samples, 0.50),
            "p95": percentile(latency_samples, 0.95),
            "max": max(latency_samples),
        },
        "corpus": {
            "small": {"sources": 1, "documents": _SMALL_CORPUS[1], "units": _SMALL_CORPUS[2]},
            "large": {"sources": 1, "documents": _LARGE_CORPUS[1], "units": _LARGE_CORPUS[2]},
            "measured_chunks_small": small.units,
            "measured_chunks_large": large.units,
            "generator": "tools.run_m7_benchmark.build_corpus",
        },
        "environment": {
            "os": runtime_platform.platform(),
            "python": runtime_platform.python_version(),
            "provider": "deterministic-stub (no network)",
        },
        "workloads": rows,
        "input_bounded": bounded_ok,
        "prerequisite_violations_total": sum(row["prerequisite_violations"] for row in rows),
        "deterministic_replay_consistency": all(row["replay_identical"] for row in rows),
        "not_evidence_for": [
            "10K/100K capacity (M8 BLOCKED / M11 proposed)",
            "real provider latency, cost or failure modes (see the opt-in provider smoke)",
            "a project-wide evaluation: this scope is the M9 external AI path only",
            "a stable SLA of any kind: the latency distribution above is stub-derived",
        ],
    }
    report["report_digest"] = hashlib.sha256(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _write_report(report, evidence_id)

    assert bounded_ok, "the AI prompt grew with the retrieval corpus"
    assert report["prerequisite_violations_total"] == 0
    assert report["deterministic_replay_consistency"] is True
    # 非空转护栏：AI 路径必须真的产出过**自己的**计划，先修闸门必须真的拒绝过非法置换。
    # 否则本文件只证明了「两条路径都没做事」——那是最容易全绿、也最没有信息量的结果。
    assert all(row["ai_legal_differs"] for row in rows if row["legal_swap_available"]), rows
    assert any(row["ai_legal_adopted_verbatim"] for row in rows), "no workload adopted a legal swap"
    assert any(row["illegal_swap_available"] for row in rows), "no illegal swap was constructible"
    assert all(row["ai_illegal_fell_back"] for row in rows if row["illegal_swap_available"])
    assert len(report["workload_digest"]) == 64
    assert len(report["report_digest"]) == 64

    # ── 预算矩阵：强制执行率必须是 1.0，且原因码逐场景精确 ──
    assert [row["observed_reason"] for row in budget_rows] == [
        row["expected_reason"] for row in budget_rows
    ], budget_rows
    assert all(row["provider_reached_matches"] for row in budget_rows), budget_rows
    assert report["budget_enforcement"]["rate"] == 1.0
    # 结构性证据：prompt 预算在**调用 provider 之前**返回，故 provider 一次都没被触达。
    prompt_row = next(row for row in budget_rows if row["scenario"] == "prompt-budget")
    assert prompt_row["provider_calls"] == 0
    # 硬上限性质：stub 提出的**是**一个合法置换，却仍被丢弃——预算是上限，不是告警阈值。
    legal_ids = _legal_order(budget_tasks, graph)
    cost_row = next(row for row in budget_rows if row["scenario"] == "cost-budget")
    assert cost_row["order_returned"] is False
    assert cost_row["estimated_cost_usd"] > PlanAILimits().max_cost_usd
    assert parse_order(_stub_answer("legal", legal_ids), tuple(legal_ids)) is not None
    # 价目表两处各自定义会静默漂移：比的是**相等**，单边改价即判红。
    assert preview_agent._INPUT_USD_PER_MILLION == _FROZEN_INPUT_USD_PER_MILLION
    assert preview_agent._OUTPUT_USD_PER_MILLION == _FROZEN_OUTPUT_USD_PER_MILLION
    for input_tokens, output_tokens, expected in _FROZEN_COST_TABLE:
        assert _estimate_cost(input_tokens, output_tokens) == pytest.approx(expected)
    # 交叉校验：审计里的延迟是**量出来的**（整次调用墙钟），不是 stub 自报的那个常数。
    probe = _stub_adapter({"limits": {}, "stub": "legal"}, order=legal_ids, calls=[], gate=None)
    wall_started = time.perf_counter()
    probed = _propose_with(probe, budget_spec, budget_tasks)
    wall_ms = (time.perf_counter() - wall_started) * 1000.0
    assert probed.audit.reason == REASON_ADOPTED
    assert probed.audit.latency_ms > 0.0
    assert probed.audit.latency_ms != _STUB_REPORTED_LATENCY_MS
    assert probed.audit.latency_ms <= wall_ms + _CLOCK_SLACK_MS
    # 分布形状：上限绑在冻结 `deadline_seconds` 之下，只抓「数量级写错」。
    assert percentile(latency_samples, 0.95) <= _STUB_P95_BUDGET_MS
    assert percentile(latency_samples, 0.95) < PlanAILimits().deadline_seconds * 1000.0
    assert len(report["budget_scenario_digest"]) == 64
