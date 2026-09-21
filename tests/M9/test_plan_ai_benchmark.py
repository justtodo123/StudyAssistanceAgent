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
"""

from __future__ import annotations

import hashlib
import json
import os
import platform as runtime_platform
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from app.goal_planner import GoalPlannerService, _prerequisite_report
from app.models import GoalPlanConstraints, GoalPlanRequest
from app.plan_ai_adapter import (
    REASON_ADOPTED,
    PlanAIAdapter,
    PlanAIAudit,
    PlanAIOutcome,
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
        "schema_version": "m9-plan-ai-benchmark-v1",
        "evidence_id": evidence_id,
        "scope": "m9.external-ai narrow scope: 1K only, latency/cost remain deferred",
        "workload_digest": _workload_digest(),
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
            "real provider latency, cost or failure modes",
            "the M9-EVALUATION workload freeze (latency/cost remain deferred)",
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
