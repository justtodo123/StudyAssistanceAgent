"""M9 授权 Source 只读摘要投影测试。

覆盖四类主张：
- 「可用」规则（`is_usable_for_retrieval`）在 7 种生命周期状态 × 有无 published generation 上正确；
- 摘要只含可用源：未发布 / 未就绪 / 禁用 / 待删 / 已删都**不进入**目录摘要；
- 只读与有界：一次 bulk 读、零领域写入、不触 revision / sync run 面；
- 与确定性 Planner 的接缝：未传 principal 时响应逐字节不变，plan_id 不因摘要而 churn。

本文件自带 registry 夹具：`tests/M7` 没有可 import 的 conftest（各模块各自复制），故此处照
`tests/M7/test_source_registry.py` 的形状内联 `_service` / `_register` / `_transition` / `_ready`，
**不修改 M7 测试目录**。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import pytest

from app.goal_planner import GoalPlannerService
from app.models import GoalPlanRequest
from app.source_registry import (
    MAX_SOURCES_PER_PRINCIPAL,
    SourceActorType,
    SourceLifecycleService,
    SourceLifecycleState,
    SourceRecord,
    SourceRegistryTransaction,
    SourceRevisionDraft,
    SqliteSourceRegistry,
)
from app.source_summary_projection import (
    SOURCE_SUMMARY_SCHEMA_VERSION,
    LazySourceSummaryProjection,
    SourceSummaryProjection,
    is_usable_for_retrieval,
)

pytestmark = pytest.mark.m9

PRINCIPAL = "principal-owner"
OTHER_PRINCIPAL = "principal-other"
SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
SECOND_SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ac"
CORRELATION_ID = "corr-m9-summary"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
_ENTRY_FIELDS = {"source_id", "state", "published_generation", "updated_at"}


# ── 工具 ──────────────────────────────────────────────────────────────────────


_FIXED_NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _service(tmp_path: Path, ids: list[str] | None = None):
    """返回 (repository, service)；`ids` 给定时按序用作 source_id 工厂。

    注入固定时钟：`updated_at` 取自 `_utc_now()`，不钉住它就无法断言「两个 registry 的摘要相同」，
    只能比较结构——那会把「值本身可复现」这一条悄悄降级成「键集合可复现」。
    """
    repository = SqliteSourceRegistry(tmp_path / "registry.sqlite3")
    iterator = iter(ids or [])
    service = SourceLifecycleService(
        repository,
        clock=lambda: _FIXED_NOW,
        source_id_factory=lambda: next(iterator, SOURCE_ID),
    )
    return repository, service


def _register(service: SourceLifecycleService, source_id: str | None = None):
    return service.register_source(
        owner_principal_id=PRINCIPAL,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION_ID,
        source_id=source_id,
    )


def _transition(
    service: SourceLifecycleService,
    record: SourceRecord,
    target: SourceLifecycleState,
    *,
    revision: SourceRevisionDraft | None = None,
):
    return service.transition_source(
        principal_id=PRINCIPAL,
        source_id=record.source_id,
        expected_version=record.record_version,
        target_state=target,
        actor_type=SourceActorType.SERVICE,
        correlation_id=CORRELATION_ID,
        revision=revision,
    )


def _revision(generation: str = "generation-1") -> SourceRevisionDraft:
    return SourceRevisionDraft(
        build_result="SUCCESS",
        source_fingerprint=DIGEST_A,
        manifest_digest=DIGEST_B,
        parser_schema_version="parser-v1",
        chunk_schema_version="chunk-v1",
        generation=generation,
        document_count=2,
        chunk_count=5,
        raw_bytes=128,
    )


def _to_ready(service: SourceLifecycleService, source_id: str | None = None) -> SourceRecord:
    """REGISTERED → SYNCING → READY（带 revision，因此有 published generation）。"""
    record = _register(service, source_id)
    record = _transition(service, record, SourceLifecycleState.SYNCING)
    return _transition(service, record, SourceLifecycleState.READY, revision=_revision())


def _record(
    state: SourceLifecycleState,
    *,
    published: bool,
    source_id: str = SOURCE_ID,
    principal: str = PRINCIPAL,
) -> SourceRecord:
    """直接构造记录：规则矩阵需要覆盖生命周期**无法**到达的组合（见 A 节）。"""
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    return SourceRecord(
        source_id=source_id,
        owner_principal_id=principal,
        state=state,
        record_version=1,
        created_at=now,
        updated_at=now,
        published_revision_no=1 if published else None,
        published_generation="generation-1" if published else None,
    )


def _request(**kwargs: Any) -> GoalPlanRequest:
    defaults: dict[str, Any] = {"goal": "两周内掌握进程调度与死锁", "course": "os"}
    defaults.update(kwargs)
    return GoalPlanRequest(**defaults)


# ── A. 「可用」规则矩阵 ───────────────────────────────────────────────────────


@pytest.mark.parametrize("state", list(SourceLifecycleState))
@pytest.mark.parametrize("published", [True, False])
def test_usable_rule_matrix(state: SourceLifecycleState, published: bool) -> None:
    """7 态 × 有无 generation = 14 例，钉住 `source_offline.py` 内联的同一判断。"""
    expected = published and state in {
        SourceLifecycleState.READY,
        SourceLifecycleState.DEGRADED,
    }

    assert is_usable_for_retrieval(_record(state, published=published)) is expected


def test_degraded_without_generation_is_excluded() -> None:
    """`DEGRADED + 无 generation` 是**唯一**能由生命周期自然到达的 DEGRADED 形态。

    `transition_source` 只在 `target_state is READY` 时接受 revision，所以 SYNCING → DEGRADED
    永远不带 generation；带 generation 的 DEGRADED 只经 `begin_sync_run` 的过期租约回收产生。
    本用例因此是「DEGRADED 不等于可用」的主要证据面。
    """
    assert is_usable_for_retrieval(_record(SourceLifecycleState.DEGRADED, published=False)) is False


def test_ready_without_generation_is_excluded() -> None:
    assert is_usable_for_retrieval(_record(SourceLifecycleState.READY, published=False)) is False


def test_schema_version_is_declared() -> None:
    assert SOURCE_SUMMARY_SCHEMA_VERSION == "m9-source-summary-v1"


# ── B. 投影过滤集成（真 registry） ────────────────────────────────────────────


def test_summaries_contain_only_usable_sources(tmp_path: Path) -> None:
    """READY 进入摘要；REGISTERED（未发布）与 DISABLED（禁用）不进入。"""
    _, service = _service(tmp_path)
    ready = _to_ready(service, SOURCE_ID)
    _register(service, SECOND_SOURCE_ID)
    disabled = _to_ready(service, "user-01890f52-47e7-7abc-8def-0123456789ad")
    disabled = _transition(service, disabled, SourceLifecycleState.DISABLED)

    summaries = SourceSummaryProjection(service).summaries(PRINCIPAL)

    assert set(summaries) == {ready.source_id}
    assert summaries[ready.source_id]["state"] == "READY"
    assert summaries[ready.source_id]["published_generation"] == "generation-1"
    assert disabled.source_id not in summaries
    assert SECOND_SOURCE_ID not in summaries


def test_summaries_entry_is_json_safe_and_exactly_these_fields(tmp_path: Path) -> None:
    """`save_plan` 走 json.dumps：放 datetime 会在步骤 4 持久化时 TypeError。"""
    _, service = _service(tmp_path)
    ready = _to_ready(service, SOURCE_ID)

    entry = SourceSummaryProjection(service).summaries(PRINCIPAL)[ready.source_id]

    assert set(entry) == _ENTRY_FIELDS
    assert isinstance(entry["updated_at"], str)
    assert json.loads(json.dumps(entry)) == entry


def test_summaries_are_scoped_to_the_principal(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)

    assert SourceSummaryProjection(service).summaries(OTHER_PRINCIPAL) == {}


def test_disabling_a_ready_source_removes_it(tmp_path: Path) -> None:
    """生命周期变化立刻反映在投影里（刻意不缓存）。"""
    _, service = _service(tmp_path)
    ready = _to_ready(service, SOURCE_ID)
    projection = SourceSummaryProjection(service)
    assert set(projection.summaries(PRINCIPAL)) == {ready.source_id}

    _transition(service, ready, SourceLifecycleState.DISABLED)

    assert projection.summaries(PRINCIPAL) == {}


# ── C. 隐藏态：钉的是 M7 的 WHERE 子句 ────────────────────────────────────────


def _hide(service: SourceLifecycleService, source_id: str, state: str) -> None:
    """用直接 SQL 种入隐藏态。

    `list_sources` 的 WHERE（`source_registry.py` 的 `state NOT IN (DELETE_PENDING, DELETED)`）
    使这两个状态**永远不可能**经服务层返回——用服务层种用例是**空转**的，所以这里绕过它。
    """
    connection = sqlite3.connect(str(service._repository.db_path))
    try:
        connection.execute(
            "UPDATE source_records SET state = ? WHERE source_id = ?", (state, source_id)
        )
        connection.commit()
    finally:
        connection.close()


def test_delete_pending_and_deleted_never_enter_the_summary(tmp_path: Path) -> None:
    """本用例钉的是 M7 既有 WHERE 子句的构造性保证，**不是**本增量新增的证据。"""
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)
    _to_ready(service, SECOND_SOURCE_ID)
    _hide(service, SECOND_SOURCE_ID, "DELETE_PENDING")

    listed = {r.source_id for r in service.list_sources(principal_id=PRINCIPAL)}
    summaries = SourceSummaryProjection(service).summaries(PRINCIPAL)

    assert SECOND_SOURCE_ID not in listed
    assert SECOND_SOURCE_ID not in summaries
    assert set(summaries) == {SOURCE_ID}


def test_summary_does_not_use_the_non_deleted_counter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`count_non_deleted_sources` 的 WHERE 是 `state != DELETED`，**包含** DELETE_PENDING。

    把它当作「可用源计数」的捷径会把待删源算进去，因此这里让它一旦被调用就失败。
    """
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)

    def _explode(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("summary must not use the non-deleted counter")

    monkeypatch.setattr(SourceRegistryTransaction, "count_non_deleted_sources", _explode)

    assert set(SourceSummaryProjection(service).summaries(PRINCIPAL)) == {SOURCE_ID}


# ── D. 恰好一次 bulk 读 ───────────────────────────────────────────────────────


class _CountingReader:
    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.calls = 0

    def list_sources(self, *, principal_id: str):
        self.calls += 1
        return self._inner.list_sources(principal_id=principal_id)


def test_summaries_read_the_registry_exactly_once(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    for index in range(3):
        _to_ready(service, f"user-01890f52-47e7-7abc-8def-01234567{index:04x}")
    reader = _CountingReader(service)

    summaries = SourceSummaryProjection(reader).summaries(PRINCIPAL)

    assert len(summaries) == 3
    assert reader.calls == 1


# ── E. 只读守卫 ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _DbState:
    dump: str
    digest: str
    counts: dict[str, int]
    data_version: int


def _db_state(observer: sqlite3.Connection) -> _DbState:
    dump = "\n".join(observer.iterdump())
    counts = {
        table: int(observer.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in ("source_records", "source_revisions", "sync_runs", "audit_events")
    }
    return _DbState(
        dump=dump,
        digest=hashlib.sha256(dump.encode("utf-8")).hexdigest(),
        counts=counts,
        data_version=int(observer.execute("PRAGMA data_version").fetchone()[0]),
    )


def _install_write_traps(monkeypatch: pytest.MonkeyPatch, repository: SqliteSourceRegistry):
    """把写入口换成 fail，并审计每条读连接的 total_changes 增量。"""
    observer = sqlite3.connect(str(repository.db_path))
    observer.execute("PRAGMA query_only=ON")
    deltas: list[int] = []
    original_read = SqliteSourceRegistry._read_connection

    @contextmanager
    def audited_read(self) -> Iterator[sqlite3.Connection]:
        with original_read(self) as connection:
            started = connection.total_changes
            yield connection
            deltas.append(connection.total_changes - started)

    monkeypatch.setattr(SqliteSourceRegistry, "_read_connection", audited_read)
    monkeypatch.setattr(
        SqliteSourceRegistry,
        "transaction",
        lambda *a, **k: pytest.fail("projection attempted a registry write transaction"),
    )
    for name, message in (
        ("register_source", "projection attempted a registration"),
        ("transition_source", "projection attempted a lifecycle transition"),
        ("begin_sync_run", "projection attempted a sync run"),
        ("complete_sync_run", "projection attempted a sync completion"),
        ("update_sync_run", "projection attempted a sync run update"),
    ):
        monkeypatch.setattr(
            SourceLifecycleService, name, lambda *a, _m=message, **k: pytest.fail(_m)
        )
    return observer, deltas


def test_summary_preserves_the_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """领域级只读。

    **边界（不得夸大）**：这不是文件系统级只读。`SqliteSourceRegistry._configure` 对每条连接都执行
    `PRAGMA journal_mode=WAL`，`_initialize_or_validate` 会 `mkdir` 且可能建表。本用例断言的是
    「无领域写入」——表内容、表计数与 `data_version` 不变，且每条连接 `total_changes` 增量为 0。
    """
    repository, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)
    _register(service, SECOND_SOURCE_ID)
    observer, deltas = _install_write_traps(monkeypatch, repository)
    before = _db_state(observer)

    summaries = SourceSummaryProjection(service).summaries(PRINCIPAL)

    after = _db_state(observer)
    observer.close()

    assert set(summaries) == {SOURCE_ID}
    assert before == after
    assert all(delta == 0 for delta in deltas)


def test_lazy_wiring_does_not_create_the_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """懒守卫必须在构造之前：`SqliteSourceRegistry.__init__` 会建库，跳过守卫就是写副作用。"""
    missing = tmp_path / "cache" / "source_registry.sqlite3"
    monkeypatch.setattr(
        SqliteSourceRegistry,
        "__init__",
        lambda *a, **k: pytest.fail("lazy guard must not construct the registry"),
    )
    projection = LazySourceSummaryProjection(missing)

    assert projection.summaries(PRINCIPAL) == {}
    assert projection.summaries(PRINCIPAL) == {}
    assert not missing.parent.exists()


def test_lazy_wiring_opens_once_the_registry_exists(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)
    projection = LazySourceSummaryProjection(repository.db_path)

    assert set(projection.summaries(PRINCIPAL)) == {SOURCE_ID}
    assert projection.summaries(OTHER_PRINCIPAL) == {}


# ── F. principal 守卫 ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("principal", [None, ""])
def test_falsy_principal_returns_empty_without_reading(
    tmp_path: Path, principal: str | None
) -> None:
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)
    reader = _CountingReader(service)

    assert SourceSummaryProjection(reader).summaries(principal) == {}
    assert reader.calls == 0


def test_malformed_principal_degrades_to_empty(tmp_path: Path) -> None:
    """控制面拒绝畸形 principal 时降级为空表，而不是把计划生成打挂（fail-soft）。"""
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)

    assert SourceSummaryProjection(service).summaries("###") == {}


def test_reader_failure_degrades_to_empty(tmp_path: Path) -> None:
    class _Broken:
        def list_sources(self, *, principal_id: str):
            raise RuntimeError("control plane unavailable")

    assert SourceSummaryProjection(_Broken()).summaries(PRINCIPAL) == {}


# ── G. 确定性 ─────────────────────────────────────────────────────────────────


def test_summaries_are_deterministic(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)
    projection = SourceSummaryProjection(service)

    assert projection.summaries(PRINCIPAL) == projection.summaries(PRINCIPAL)


def test_summaries_are_independent_of_insertion_order(tmp_path: Path) -> None:
    first_dir = tmp_path / "a"
    second_dir = tmp_path / "b"
    first_dir.mkdir()
    second_dir.mkdir()
    ids = [f"user-01890f52-47e7-7abc-8def-01234567{index:04x}" for index in range(3)]
    for directory, order in ((first_dir, ids), (second_dir, list(reversed(ids)))):
        _, service = _service(directory)
        for source_id in order:
            _to_ready(service, source_id)

    _, first_service = _service(first_dir)
    _, second_service = _service(second_dir)

    assert (
        SourceSummaryProjection(first_service).summaries(PRINCIPAL)
        == SourceSummaryProjection(second_service).summaries(PRINCIPAL)
    )


# ── H. 有界输入 ───────────────────────────────────────────────────────────────


def test_summary_is_bounded_by_the_per_principal_limit(tmp_path: Path) -> None:
    """条目数受 `MAX_SOURCES_PER_PRINCIPAL` 约束，且仍只读一次——不按源逐个回查。"""
    ids = [
        f"user-01890f52-47e7-7abc-8def-01234567{index:04x}"
        for index in range(MAX_SOURCES_PER_PRINCIPAL)
    ]
    _, service = _service(tmp_path)
    for source_id in ids:
        _to_ready(service, source_id)
    reader = _CountingReader(service)

    summaries = SourceSummaryProjection(reader).summaries(PRINCIPAL)

    assert len(summaries) == MAX_SOURCES_PER_PRINCIPAL
    assert reader.calls == 1


def test_summary_never_touches_revision_or_sync_run_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """输入有界：不读 revision、不读 sync run，因此不随 chunk 总量增长。"""
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)
    for name in ("list_revisions", "list_sync_runs", "list_audit_events", "list_lifecycle_errors"):
        monkeypatch.setattr(
            SqliteSourceRegistry,
            name,
            lambda *a, _n=name, **k: pytest.fail(f"summary must not read {_n}"),
        )

    assert set(SourceSummaryProjection(service).summaries(PRINCIPAL)) == {SOURCE_ID}


# ── I. 与确定性 Planner 的接缝 ────────────────────────────────────────────────


def test_planner_without_principal_is_byte_identical(tmp_path: Path) -> None:
    """未传 principal：`summary` 与不注入投影时逐字节相同，`plan_id` 也不变。"""
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)
    projection = SourceSummaryProjection(service)

    with_projection = GoalPlannerService(source_summary=projection).generate(_request())
    without = GoalPlannerService().generate(_request())

    assert "sources" not in with_projection.summary
    assert with_projection.summary == without.summary
    assert with_projection.plan_id == without.plan_id


def test_planner_reports_the_usable_count_when_a_principal_is_present(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)
    _register(service, SECOND_SOURCE_ID)  # 未发布 → 不计入
    planner = GoalPlannerService(source_summary=SourceSummaryProjection(service))

    plan = planner.generate(_request(), principal_id=PRINCIPAL)

    assert plan.summary["sources"] == {"usable": 1}


def test_planner_reports_zero_rather_than_omitting_the_key(tmp_path: Path) -> None:
    """键的出现取决于输入（有 principal + 注入了投影），不取决于结果是否有可用源。"""
    _, service = _service(tmp_path)
    _register(service, SOURCE_ID)
    planner = GoalPlannerService(source_summary=SourceSummaryProjection(service))

    plan = planner.generate(_request(), principal_id=PRINCIPAL)

    assert plan.summary["sources"] == {"usable": 0}


def test_principal_does_not_change_tasks_or_days(tmp_path: Path) -> None:
    """摘要不进入任务载荷与分日：**目录内容**变化不 churn 正在采纳中的计划内容。

    本用例原为 `test_principal_does_not_change_plan_identity_or_tasks`，同时断言
    `anonymous.plan_id == scoped.plan_id`。步骤 4b 证伪了该断言：`plan_lifecycle` 的
    `event_id` 是 `(plan_id, task_id, event)` 的哈希、不含 principal 成分，两个 principal 生成
    同一 Goal 会撞同一 `plan_id`，后者的进度事件被 `INSERT OR IGNORE` 静默去重、污染前者状态。
    故身份断言**有意**反转，见 `test_plan_identity.py`；此处保留内容侧不变量。
    """
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)
    planner = GoalPlannerService(source_summary=SourceSummaryProjection(service))

    anonymous = planner.generate(_request())
    scoped = planner.generate(_request(), principal_id=PRINCIPAL)

    assert anonymous.revisions[0].days == scoped.revisions[0].days
    assert {k: v for k, v in scoped.summary.items() if k != "sources"} == anonymous.summary


def test_planner_without_projection_has_no_sources_key() -> None:
    """依赖缺省是守卫，不是错误：与 `_mastery` 同形。"""
    plan = GoalPlannerService().generate(_request(), principal_id=PRINCIPAL)

    assert "sources" not in plan.summary


def test_planner_reads_the_summary_exactly_once(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    _to_ready(service, SOURCE_ID)
    reader = _CountingReader(service)
    planner = GoalPlannerService(source_summary=SourceSummaryProjection(reader))

    planner.generate(_request(), principal_id=PRINCIPAL)

    assert reader.calls == 1


# ── J. 模块守卫 ───────────────────────────────────────────────────────────────


def test_module_is_bounded_by_source() -> None:
    """源码级护栏：不 import 检索/生成链路，也不出现正文相关符号。"""
    import app.source_summary_projection as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("knowledge_index", "llm_client", "split_headings", "content"):
        assert forbidden not in source, f"source summary 不应出现 {forbidden!r}"
    # 整数计数捷径的陷阱：`count_non_deleted_sources` 会把 DELETE_PENDING 算进去
    assert "count_non_deleted_sources" not in source
