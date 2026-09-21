"""M9 受限检索接缝（grounding）测试。

覆盖四类主张：
- **预算**：`top_k` / `max_evidence_bytes` / `max_user_sources` / `timeout_seconds` 各自生效，
  且只能收紧、不能放宽；
- **stale/deleted 拒绝**：`user://` chunk 的来源不在可用集合内即被丢弃，覆盖未发布 / 未就绪 /
  禁用 / 待删 / 已删五种生命周期形态（真 registry + 真投影，非 mock 状态字符串）；
- **fail-closed**：未注入投影、无 principal、控制面抛异常三种「不确定」都收敛到「丢弃用户源」，
  而不是放行；
- **只读与有界**：零领域写入、registry 库字节不变；证据规模由预算决定，不随语料总量增长。

**本文件测什么、不测什么**：M7 已在自己的套件里证明**内层**检索路径拒绝 stale/deleted 源
（`tests/M7/test_user_source_search.py`、`test_source_isolation.py`、`test_source_lifecycle_e2e.py`）。
本文件不重复那层证据，测的是**Planner 接缝上的第二道交叉校验**——它独立于内层路径，用真实生命周期
状态驱动，使 `M9-EVALUATION` 的 `STALE_DELETED_SOURCE_ENTRY_ZERO` 在计划侧可测。

本文件自带 registry 夹具：`tests/M7` 没有可 import 的 conftest，故照
`tests/M9/test_source_summary_projection.py` 的形状内联，**不修改其他阶段测试**。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.models import RetrievalChunk
from app.plan_grounding import (
    GROUNDING_BUDGET_CEILING,
    GROUNDING_SCHEMA_VERSION,
    GroundingBudget,
    GroundingBudgetError,
    PlanGroundingService,
)
from app.source_registry import (
    SourceActorType,
    SourceLifecycleService,
    SourceLifecycleState,
    SourceRecord,
    SourceRevisionDraft,
    SqliteSourceRegistry,
)
from app.source_summary_projection import SourceSummaryProjection
from app.user_source_search import USER_PROVENANCE_SCHEME

pytestmark = pytest.mark.m9

PRINCIPAL = "principal-owner"
SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
OTHER_SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ac"
CORRELATION_ID = "corr-m9-grounding"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
_FIXED_NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)


# ── 夹具 ──────────────────────────────────────────────────────────────────────


def _service(tmp_path: Path) -> tuple[SqliteSourceRegistry, SourceLifecycleService]:
    repository = SqliteSourceRegistry(tmp_path / "registry.sqlite3")
    service = SourceLifecycleService(
        repository,
        clock=lambda: _FIXED_NOW,
        source_id_factory=lambda: SOURCE_ID,
    )
    return repository, service


def _transition(
    service: SourceLifecycleService,
    record: SourceRecord,
    target: SourceLifecycleState,
    *,
    revision: SourceRevisionDraft | None = None,
) -> SourceRecord:
    return service.transition_source(
        principal_id=PRINCIPAL,
        source_id=record.source_id,
        expected_version=record.record_version,
        target_state=target,
        actor_type=SourceActorType.SERVICE,
        correlation_id=CORRELATION_ID,
        revision=revision,
    )


def _revision() -> SourceRevisionDraft:
    return SourceRevisionDraft(
        build_result="SUCCESS",
        source_fingerprint=DIGEST_A,
        manifest_digest=DIGEST_B,
        parser_schema_version="parser-v1",
        chunk_schema_version="chunk-v1",
        generation="generation-1",
        document_count=2,
        chunk_count=5,
        raw_bytes=128,
    )


def _to_ready(service: SourceLifecycleService, source_id: str | None = None) -> SourceRecord:
    """REGISTERED → SYNCING → READY（带 revision，因此有 published generation）。"""
    record = service.register_source(
        owner_principal_id=PRINCIPAL,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION_ID,
        source_id=source_id,
    )
    record = _transition(service, record, SourceLifecycleState.SYNCING)
    return _transition(service, record, SourceLifecycleState.READY, revision=_revision())


def _chunk(file: str, content: str = "正文", chunk_id: str | None = None) -> RetrievalChunk:
    return RetrievalChunk(id=chunk_id or f"{file}#1", file=file, content=content)


def _user_chunk(source_id: str = SOURCE_ID, content: str = "用户源正文") -> RetrievalChunk:
    return _chunk(f"{USER_PROVENANCE_SCHEME}://{source_id}/notes/a.md", content=content)


def _pack_chunk(name: str = "knowledge/os/process.md", content: str = "默认包正文") -> RetrievalChunk:
    return _chunk(name, content=content)


class _RecallStub:
    """记录调用参数并返回预置 chunk 的可调用对象。"""

    def __init__(self, chunks: list[RetrievalChunk] | None = None) -> None:
        self.chunks = list(chunks or [])
        self.calls: list[dict[str, Any]] = []

    def __call__(self, question: str, **kwargs: Any) -> tuple[list[RetrievalChunk], str]:
        self.calls.append({"question": question, **kwargs})
        return list(self.chunks), "keyword-only"


def _grounding(
    *,
    chunks: list[RetrievalChunk] | None = None,
    summary: SourceSummaryProjection | None = None,
) -> tuple[PlanGroundingService, _RecallStub]:
    recall = _RecallStub(chunks)
    return PlanGroundingService(recall, source_summary=summary), recall


class _AllUsableReader:
    """把所有给定 id 都报成 READY + 已发布的 reader。

    用于把预算用例与生命周期解耦：那里测的是裁剪顺序，不是可用性规则（后者由 C/D 节用真
    registry 覆盖）。
    """

    def __init__(self, source_ids: set[str]) -> None:
        self._ids = source_ids

    def list_sources(self, *, principal_id: str) -> tuple[SourceRecord, ...]:
        return tuple(
            SourceRecord(
                source_id=source_id,
                owner_principal_id=principal_id,
                state=SourceLifecycleState.READY,
                record_version=1,
                created_at=_FIXED_NOW,
                updated_at=_FIXED_NOW,
                published_revision_no=1,
                published_generation="generation-1",
            )
            for source_id in sorted(self._ids)
        )


def _summary(service: SourceLifecycleService) -> SourceSummaryProjection:
    return SourceSummaryProjection(service)


# ── A. schema 与预算校验 ──────────────────────────────────────────────────────


def test_schema_version_is_declared() -> None:
    assert GROUNDING_SCHEMA_VERSION == "m9-plan-grounding-v1"


def test_ceiling_is_the_documented_default() -> None:
    assert GROUNDING_BUDGET_CEILING == GroundingBudget(
        top_k=5, max_evidence_bytes=16_384, max_user_sources=4, timeout_seconds=2.0
    )


@pytest.mark.parametrize(
    "budget",
    [
        GroundingBudget(top_k=6),
        GroundingBudget(max_evidence_bytes=16_385),
        GroundingBudget(max_user_sources=5),
        GroundingBudget(timeout_seconds=2.1),
    ],
)
def test_widening_any_budget_dimension_is_rejected(budget: GroundingBudget) -> None:
    """四个维度**逐一**验证：任一维度放宽都必须被拒绝，不能只守住一个。"""
    service, recall = _grounding()

    with pytest.raises(GroundingBudgetError):
        service.ground("q", budget=budget)
    assert recall.calls == [], "被拒的预算不得触达检索路径"


@pytest.mark.parametrize(
    "budget",
    [
        GroundingBudget(top_k=-1),
        GroundingBudget(max_evidence_bytes=-1),
        GroundingBudget(max_user_sources=-1),
        GroundingBudget(timeout_seconds=0),
    ],
)
def test_illegal_budget_values_are_rejected(budget: GroundingBudget) -> None:
    service, _ = _grounding()

    with pytest.raises(GroundingBudgetError):
        service.ground("q", budget=budget)


def test_exactly_the_ceiling_is_allowed() -> None:
    """边界是「≤ 上限」，不是「< 上限」——用默认预算的调用方必须能通过。"""
    service, recall = _grounding(chunks=[_pack_chunk()])

    evidence = service.ground("q", budget=GROUNDING_BUDGET_CEILING)

    assert len(evidence.chunks) == 1
    assert len(recall.calls) == 1


def test_tightening_is_allowed() -> None:
    service, recall = _grounding(chunks=[_pack_chunk()])

    service.ground("q", budget=GroundingBudget(top_k=1, max_evidence_bytes=16))

    assert recall.calls[0]["top_k"] == 1


# ── B. 预算生效 ───────────────────────────────────────────────────────────────


def test_zero_top_k_short_circuits_without_recall() -> None:
    service, recall = _grounding(chunks=[_pack_chunk()])

    evidence = service.ground("q", budget=GroundingBudget(top_k=0))

    assert evidence.chunks == ()
    assert recall.calls == []


def test_top_k_is_forwarded_to_the_retrieval_path() -> None:
    """`top_k` 靠**传参**生效，不是召回后再截断——否则检索路径已经做完了超预算的工作。"""
    service, recall = _grounding(chunks=[_pack_chunk()])

    service.ground("q", budget=GroundingBudget(top_k=2))

    assert recall.calls[0]["top_k"] == 2


def test_max_evidence_bytes_bounds_the_evidence() -> None:
    chunks = [_chunk(f"knowledge/os/p{i}.md", content="x" * 10) for i in range(5)]
    service, _ = _grounding(chunks=chunks)

    evidence = service.ground("q", budget=GroundingBudget(top_k=5, max_evidence_bytes=25))

    assert len(evidence.chunks) == 2, "25 字节预算只能装下两个 10 字节 chunk"
    assert "max_evidence_bytes" in evidence.truncated


def test_max_user_sources_bounds_distinct_user_sources() -> None:
    chunks = [
        _user_chunk(SOURCE_ID, "a"),
        _user_chunk(OTHER_SOURCE_ID, "b"),
    ]
    summary = SourceSummaryProjection(_AllUsableReader({SOURCE_ID, OTHER_SOURCE_ID}))
    grounding, _ = _grounding(chunks=chunks, summary=summary)

    evidence = grounding.ground(
        "q", principal_id=PRINCIPAL, budget=GroundingBudget(max_user_sources=1)
    )

    assert len(evidence.user_source_ids) == 1
    assert "max_user_sources" in evidence.truncated
    assert len(evidence.chunks) == 1


def test_timeout_returns_empty_evidence_and_is_recorded() -> None:
    """事后截止检查：超时即**不返回任何证据**，并如实标注为 `timeout`。"""
    service, _ = _grounding(chunks=[_pack_chunk()])
    # 用一个必然超时的极小预算，避开对真实墙钟的依赖。
    evidence = service.ground("q", budget=GroundingBudget(timeout_seconds=1e-9))

    assert evidence.chunks == ()
    assert evidence.truncated == ("timeout",)


# ── C. stale/deleted 拒绝（真 registry + 真投影） ─────────────────────────────


@pytest.mark.parametrize(
    "target",
    [
        SourceLifecycleState.DISABLED,
        SourceLifecycleState.DELETE_PENDING,
    ],
)
def test_disabled_and_delete_pending_sources_are_dropped(
    tmp_path: Path, target: SourceLifecycleState
) -> None:
    """READY → DISABLED / DELETE_PENDING 后，该源的用户 chunk 必须一个都不剩。"""
    _, lifecycle = _service(tmp_path)
    record = _to_ready(lifecycle)
    grounding, _ = _grounding(chunks=[_user_chunk()], summary=_summary(lifecycle))

    before = grounding.ground("q", principal_id=PRINCIPAL)
    assert len(before.chunks) == 1, "READY 且已发布时应当保留"

    _transition(lifecycle, record, target)

    after = grounding.ground("q", principal_id=PRINCIPAL)
    assert after.chunks == ()
    assert after.dropped_unusable_sources == 1


def test_hard_deleted_source_is_dropped(tmp_path: Path) -> None:
    """DELETE_PENDING → DELETED（终态）后仍然一个都不剩。"""
    _, lifecycle = _service(tmp_path)
    record = _to_ready(lifecycle)
    record = _transition(lifecycle, record, SourceLifecycleState.DELETE_PENDING)
    _transition(lifecycle, record, SourceLifecycleState.DELETED)
    grounding, _ = _grounding(chunks=[_user_chunk()], summary=_summary(lifecycle))

    evidence = grounding.ground("q", principal_id=PRINCIPAL)

    assert evidence.chunks == ()
    assert evidence.dropped_unusable_sources == 1


def test_unpublished_source_is_dropped(tmp_path: Path) -> None:
    """REGISTERED（已注册但从未发布）不在可用集合内，即使它确实「存在」。"""
    _, lifecycle = _service(tmp_path)
    lifecycle.register_source(
        owner_principal_id=PRINCIPAL,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION_ID,
        source_id=SOURCE_ID,
    )
    grounding, _ = _grounding(chunks=[_user_chunk()], summary=_summary(lifecycle))

    evidence = grounding.ground("q", principal_id=PRINCIPAL)

    assert evidence.chunks == ()
    assert evidence.dropped_unusable_sources == 1


def test_syncing_source_is_dropped(tmp_path: Path) -> None:
    """SYNCING 是「已授权但不可用」——它必须被丢弃，这正是 `usable` ≠ `authorized` 的要害。"""
    _, lifecycle = _service(tmp_path)
    record = lifecycle.register_source(
        owner_principal_id=PRINCIPAL,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION_ID,
        source_id=SOURCE_ID,
    )
    _transition(lifecycle, record, SourceLifecycleState.SYNCING)
    grounding, _ = _grounding(chunks=[_user_chunk()], summary=_summary(lifecycle))

    assert grounding.ground("q", principal_id=PRINCIPAL).chunks == ()


def test_other_principals_sources_are_not_usable(tmp_path: Path) -> None:
    """可用集合按 principal 作用域取；别人的源不能成为本 principal 的证据。"""
    _, lifecycle = _service(tmp_path)
    _to_ready(lifecycle)
    grounding, _ = _grounding(chunks=[_user_chunk()], summary=_summary(lifecycle))

    evidence = grounding.ground("q", principal_id="principal-someone-else")

    assert evidence.chunks == ()
    assert evidence.dropped_unusable_sources == 1


# ── D. fail-closed ────────────────────────────────────────────────────────────


def test_without_principal_all_user_chunks_are_dropped() -> None:
    """无 principal → 可用集合为空 → 用户源全部丢弃；默认包不受影响。"""
    summary = SourceSummaryProjection(_AllUsableReader({SOURCE_ID}))
    grounding, _ = _grounding(
        chunks=[_pack_chunk(), _user_chunk()], summary=summary
    )

    evidence = grounding.ground("q")

    assert [c.file for c in evidence.chunks] == ["knowledge/os/process.md"]


def test_without_projection_all_user_chunks_are_dropped() -> None:
    """未注入投影 = 无法校验 = **丢弃**，不是放行。"""
    grounding, _ = _grounding(chunks=[_pack_chunk(), _user_chunk()])

    evidence = grounding.ground("q", principal_id=PRINCIPAL)

    assert [c.file for c in evidence.chunks] == ["knowledge/os/process.md"]
    assert evidence.cross_checked is False
    assert evidence.dropped_unusable_sources == 1


def test_projection_failure_drops_user_chunks_instead_of_raising() -> None:
    """控制面不可用时计划生成不该崩——但也不能放行用户源。"""

    class _Boom:
        def summaries(self, principal_id: str | None = None) -> dict[str, dict[str, Any]]:
            raise RuntimeError("control plane down")

    grounding = PlanGroundingService(
        _RecallStub([_pack_chunk(), _user_chunk()]), source_summary=_Boom()
    )

    evidence = grounding.ground("q", principal_id=PRINCIPAL)

    assert [c.file for c in evidence.chunks] == ["knowledge/os/process.md"]
    assert evidence.cross_checked is True


def test_malformed_user_provenance_is_dropped() -> None:
    """畸形 `user://` 的 source_id 必然不在可用集合里，因此被丢弃而非当作默认包放行。"""
    summary = SourceSummaryProjection(_AllUsableReader({SOURCE_ID}))
    malformed = _chunk(f"{USER_PROVENANCE_SCHEME}://not-a-valid-id/x.md")
    grounding, _ = _grounding(chunks=[malformed], summary=summary)

    evidence = grounding.ground("q", principal_id=PRINCIPAL)

    assert evidence.chunks == ()
    assert evidence.dropped_unusable_sources == 1


def test_default_pack_chunks_are_never_source_gated() -> None:
    """默认知识包不是生命周期门控对象：未注入投影时也必须原样保留。"""
    grounding, _ = _grounding(chunks=[_pack_chunk("knowledge/ds/tree.md")])

    evidence = grounding.ground("q")

    assert [c.file for c in evidence.chunks] == ["knowledge/ds/tree.md"]
    assert evidence.dropped_unusable_sources == 0


# ── E. 只读与有界 ─────────────────────────────────────────────────────────────


def test_grounding_does_not_modify_the_registry(tmp_path: Path) -> None:
    """真只读：跑完 grounding 后 registry 库的字节不变。"""
    registry_path = tmp_path / "registry.sqlite3"
    _, lifecycle = _service(tmp_path)
    _to_ready(lifecycle)
    grounding, _ = _grounding(chunks=[_user_chunk()], summary=_summary(lifecycle))

    before = registry_path.read_bytes()
    grounding.ground("q", principal_id=PRINCIPAL)
    after = registry_path.read_bytes()

    assert before == after


def test_service_exposes_no_write_surface() -> None:
    """结构性只读：类上不存在写入口。"""
    public = [name for name in dir(PlanGroundingService) if not name.startswith("_")]

    assert public == ["ground"]


def test_evidence_is_bounded_by_budget_not_by_corpus_size() -> None:
    """输入有界：语料从 10 条涨到 500 条，证据规模由预算封顶、不随之增长。"""
    summary = SourceSummaryProjection(_AllUsableReader({SOURCE_ID}))
    budget = GroundingBudget(top_k=3, max_evidence_bytes=64)

    def _evidence_size(count: int) -> int:
        chunks = [_chunk(f"knowledge/os/p{i}.md", content="x" * 10) for i in range(count)]
        grounding, _ = _grounding(chunks=chunks, summary=summary)
        return len(grounding.ground("q", principal_id=PRINCIPAL, budget=budget).chunks)

    assert _evidence_size(10) == _evidence_size(500) == 3


def test_recall_receives_the_extras_scope_and_the_principal() -> None:
    """接缝必须把 principal 透传到检索路径——否则用户源叠加根本不会触发。"""
    service, recall = _grounding(chunks=[_pack_chunk()])

    service.ground("q", course="os", principal_id=PRINCIPAL)

    call = recall.calls[0]
    assert call["principal_id"] == PRINCIPAL
    assert call["course"] == "os"
    assert call["scope"].value == "DEFAULT_PLUS_EXTRAS"
