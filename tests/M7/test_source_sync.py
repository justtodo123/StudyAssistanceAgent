from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.parser_matrix import ParsedDocument, ParsedUnit
from app.source_offline import UserSourceOfflineGuard
from app.source_registry import (
    SYNC_RUN_CANCELLED,
    SYNC_RUN_RUNNING,
    SYNC_RUN_SUCCESS,
    SourceActorType,
    SourceLifecycleService,
    SourceLifecycleState,
    SqliteSourceRegistry,
    generate_uuid7,
)
from app.user_source_snapshot import (
    FullSnapshotError,
    FullSnapshotErrorCode,
)
from app.user_source_sync import (
    SYNC_RETRY_DELAYS,
    SourceSyncError,
    SourceSyncErrorCode,
    UserSourceSyncService,
)
from app.user_source_vector import HashVectorEmbedder

pytestmark = pytest.mark.m7

SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
PRINCIPAL = "principal-owner"
CORRELATION = "corr-m7-sync"


@pytest.fixture(autouse=True)
def _reset_process_gate() -> None:
    UserSourceSyncService.reset_process_gate()
    yield
    UserSourceSyncService.reset_process_gate()


@pytest.fixture(autouse=True)
def _synthetic_markdown_parser(monkeypatch: pytest.MonkeyPatch):
    def fake_parse(path, fmt, max_bytes=None):  # type: ignore[no-untyped-def]
        text = Path(path).read_text(encoding="utf-8")
        return ParsedDocument(
            format=fmt or "md",
            parser_id="markdown-it-py",
            parser_version="4.0.0",
            units=(ParsedUnit("document", 0, text),),
        )

    monkeypatch.setattr("app.user_source_snapshot.parse_file", fake_parse)
    return fake_parse


def _write_docs(root: Path, texts: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (root / name).write_text(text, encoding="utf-8")


def _service(tmp_path: Path) -> tuple[SourceLifecycleService, UserSourceSyncService, Path]:
    registry = SqliteSourceRegistry(tmp_path / "registry.sqlite3")
    lifecycle = SourceLifecycleService(registry, source_id_factory=lambda: SOURCE_ID)
    lifecycle.register_source(
        owner_principal_id=PRINCIPAL,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION,
        source_id=SOURCE_ID,
    )
    source_root = tmp_path / "source"
    cache_root = tmp_path / "cache"
    offline = UserSourceOfflineGuard(
        cache_root,
        lifecycle,
        vector_embedder=HashVectorEmbedder(),
    )
    sync = UserSourceSyncService(
        cache_root,
        lifecycle,
        publisher=offline._snapshots,
        offline=offline,
        sleeper=lambda _delay: None,
    )
    return lifecycle, sync, source_root


def _sync(
    service: UserSourceSyncService,
    source_root: Path,
    *,
    request_id: str | None = None,
    expected_version: int,
    strategy: str = "FULL",
) -> object:
    return service.request_sync(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        request_id=request_id or generate_uuid7(),
        expected_version=expected_version,
        source_root=source_root,
        correlation_id=CORRELATION,
        strategy=strategy,
    )


def test_request_sync_preserves_ready_after_current_activation_failure(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "发布后指针修复"})
    original_activate = service._publisher._activate_generation
    request_id = generate_uuid7()

    def fail_activation(snapshot) -> None:  # type: ignore[no-untyped-def]
        raise OSError("CURRENT is temporarily unavailable")

    service._publisher._activate_generation = fail_activation  # type: ignore[method-assign]
    try:
        completed = _sync(
            service,
            source_root,
            request_id=request_id,
            expected_version=1,
        )
    finally:
        service._publisher._activate_generation = original_activate  # type: ignore[method-assign]

    record = lifecycle.get_source(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
    )
    persisted = lifecycle.get_sync_run(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        request_id=request_id,
    )
    assert completed == persisted
    assert persisted.status == SYNC_RUN_SUCCESS
    assert persisted.result_code == SYNC_RUN_SUCCESS
    assert record.state is SourceLifecycleState.READY
    assert record.published_generation == persisted.candidate_generation
    assert service._publisher.published_path(SOURCE_ID) is None
    assert service._offline._fts5.published_path(SOURCE_ID) is None
    assert service._offline._vector.published_path(SOURCE_ID) is None

    repaired = _sync(
        service,
        source_root,
        request_id=request_id,
        expected_version=record.record_version,
    )
    current = service._publisher.published_path(SOURCE_ID)
    assert repaired == persisted
    assert current is not None
    assert current.name == f"gen-{persisted.candidate_generation}"
    assert service._offline._fts5.published_path(SOURCE_ID) is not None
    assert service._offline._vector.published_path(SOURCE_ID) is not None
    snapshot = service._publisher.load_snapshot(SOURCE_ID)
    assert snapshot is not None
    service._offline._vector.validate(
        SOURCE_ID,
        snapshot.generation,
        snapshot,
        revision_no=record.published_revision_no,
    )
    assert len(lifecycle._repository.list_revisions(SOURCE_ID)) == 1


def test_first_full_sync_publishes_ready_revision(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "操作系统调度", "b.md": "进程与线程"})
    run = _sync(service, source_root, expected_version=1)

    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert run.status == SYNC_RUN_SUCCESS
    assert record.state is SourceLifecycleState.READY
    assert record.published_generation == run.candidate_generation
    assert record.published_revision_no == 1
    assert len(lifecycle.list_sync_runs(principal_id=PRINCIPAL, source_id=SOURCE_ID)) == 1
    snapshot = service._publisher.load_snapshot(SOURCE_ID)
    assert snapshot is not None
    assert snapshot.document_count == 2
    assert b"source_root" not in snapshot.canonical_bytes()
    assert service._offline._fts5.published_path(SOURCE_ID) is not None
    assert service._offline._vector.published_path(SOURCE_ID) is not None
    service._offline._fts5.validate(SOURCE_ID, snapshot.generation, snapshot)
    metadata = service._offline._vector.validate(
        SOURCE_ID,
        snapshot.generation,
        snapshot,
        revision_no=record.published_revision_no,
    )
    assert metadata.revision_no == record.published_revision_no


def test_repeat_request_id_does_not_create_run_or_revision(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "稳定内容"})
    request_id = generate_uuid7()
    first = _sync(service, source_root, request_id=request_id, expected_version=1)
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    second = _sync(
        service,
        source_root,
        request_id=request_id,
        expected_version=record.record_version,
    )
    assert first.run_id == second.run_id
    assert len(lifecycle.list_sync_runs(principal_id=PRINCIPAL, source_id=SOURCE_ID)) == 1
    assert len(lifecycle._repository.list_revisions(SOURCE_ID)) == 1


def test_request_conflict_when_same_id_changes_strategy(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "稳定内容"})
    request_id = generate_uuid7()
    _sync(service, source_root, request_id=request_id, expected_version=1)
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    with pytest.raises(SourceSyncError) as error:
        _sync(
            service,
            source_root,
            request_id=request_id,
            expected_version=record.record_version,
            strategy="INCREMENTAL",
        )
    assert error.value.code is SourceSyncErrorCode.SOURCE_SYNC_REQUEST_CONFLICT


def test_incremental_noop_keeps_generation(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "调度算法", "b.md": "死锁"})
    full = _sync(service, source_root, expected_version=1)
    ready = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    incremental = _sync(
        service,
        source_root,
        expected_version=ready.record_version,
        strategy="INCREMENTAL",
    )
    after = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert incremental.status == SYNC_RUN_SUCCESS
    assert after.published_generation == full.candidate_generation
    assert len(lifecycle._repository.list_revisions(SOURCE_ID)) == 1


def test_incremental_uses_registry_generation_when_current_is_missing(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "权威版本"})
    first = _sync(service, source_root, expected_version=1)
    ready = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    current = service._publisher._root / SOURCE_ID / "CURRENT"
    current.unlink()

    (source_root / "b.md").write_text("新增内容", encoding="utf-8")
    incremental = _sync(
        service,
        source_root,
        expected_version=ready.record_version,
        strategy="INCREMENTAL",
    )

    published = service._publisher.load_snapshot(
        SOURCE_ID,
        incremental.candidate_generation,
    )
    assert first.candidate_generation == ready.published_generation
    assert published is not None
    assert {document.logical_uri for document in published.documents} == {
        "a.md",
        "b.md",
    }


def test_incremental_added_modified_removed_matches_full_rebuild(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(
        source_root,
        {f"doc-{index:02d}.md": f"主题{index} 内容" for index in range(10)},
    )
    _sync(service, source_root, expected_version=1)
    (source_root / "doc-00.md").write_text("主题0 已修改", encoding="utf-8")
    (source_root / "doc-01.md").unlink()
    (source_root / "doc-10.md").write_text("新增主题", encoding="utf-8")
    ready = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    incremental = _sync(
        service,
        source_root,
        expected_version=ready.record_version,
        strategy="INCREMENTAL",
    )
    clone_root = tmp_path / "clone"
    _write_docs(
        clone_root,
        {
            path.name: path.read_text(encoding="utf-8")
            for path in source_root.glob("*.md")
        },
    )
    rebuilt = service._publisher._build_candidate(clone_root, SOURCE_ID)
    published = service._publisher.load_snapshot(SOURCE_ID)
    assert published is not None
    assert incremental.candidate_generation == rebuilt.generation
    assert {doc.document_id for doc in published.documents} == {
        doc.document_id for doc in rebuilt.documents
    }
    assert "doc-01.md" not in {doc.logical_uri for doc in published.documents}
    assert "doc-10.md" in {doc.logical_uri for doc in published.documents}


def test_incremental_reuses_unchanged_documents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"keep.md": "保留", "change.md": "旧值"})
    _sync(service, source_root, expected_version=1)
    (source_root / "change.md").write_text("新值", encoding="utf-8")
    calls: list[str] = []
    real = __import__("app.user_source_snapshot", fromlist=["parse_file"]).parse_file

    def counting(path, fmt, max_bytes=None):  # type: ignore[no-untyped-def]
        calls.append(Path(path).name)
        return real(path, fmt, max_bytes=max_bytes)

    monkeypatch.setattr("app.user_source_snapshot.parse_file", counting)
    ready = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    _sync(service, source_root, expected_version=ready.record_version, strategy="INCREMENTAL")
    assert calls == ["change.md"]


def test_incremental_without_ready_fails_precondition(tmp_path: Path) -> None:
    _, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "内容"})
    with pytest.raises(SourceSyncError) as error:
        _sync(service, source_root, expected_version=1, strategy="INCREMENTAL")
    assert error.value.code is SourceSyncErrorCode.SOURCE_SYNC_PRECONDITION_FAILED


def test_unknown_strategy_is_rejected(tmp_path: Path) -> None:
    _, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "内容"})
    with pytest.raises(SourceSyncError) as error:
        _sync(service, source_root, expected_version=1, strategy="PARTIAL")
    assert error.value.code is SourceSyncErrorCode.SOURCE_SYNC_VALIDATION_FAILED


def test_one_hundred_dual_requests_have_single_active_run(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "并发内容"})
    _sync(service, source_root, expected_version=1)
    busy = 0
    success = 0
    for _ in range(100):
        record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
        first_id = generate_uuid7()
        second_id = generate_uuid7()

        def invoke(request_id: str, version: int = record.record_version):
            return _sync(service, source_root, request_id=request_id, expected_version=version)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(invoke, first_id), pool.submit(invoke, second_id)]
            results = []
            for future in futures:
                try:
                    results.append(future.result())
                except SourceSyncError as exc:
                    results.append(exc)
        statuses = [
            item.status if not isinstance(item, SourceSyncError) else item.code
            for item in results
        ]
        assert statuses.count(SYNC_RUN_SUCCESS) == 1
        assert statuses.count(SourceSyncErrorCode.SOURCE_SYNC_BUSY) == 1
        success += 1
        busy += 1
    assert success == 100
    assert busy == 100


def test_retry_recovers_after_two_failures_and_exhausts_on_three(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "重试内容"})
    delays: list[float] = []
    service._sleeper = delays.append
    service.stage_faults[_STAGE := "ENUMERATE"] = [OSError("busy"), OSError("busy")]
    run = _sync(service, source_root, expected_version=1)
    assert run.status == SYNC_RUN_SUCCESS
    assert delays == list(SYNC_RETRY_DELAYS)

    ready = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    delays.clear()
    service.stage_faults["ENUMERATE"] = [OSError("busy"), OSError("busy"), OSError("busy")]
    with pytest.raises(SourceSyncError) as error:
        _sync(service, source_root, expected_version=ready.record_version)
    assert error.value.code is SourceSyncErrorCode.SOURCE_SYNC_RETRY_EXHAUSTED
    assert delays == list(SYNC_RETRY_DELAYS)


def test_materialization_oserror_exhaustion_finishes_run(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "物化失败必须终态化"})
    request_id = generate_uuid7()
    delays: list[float] = []
    calls = {"count": 0}
    original = service._publisher._materialize_candidate
    service._sleeper = delays.append

    def fail_materialization(snapshot) -> None:  # type: ignore[no-untyped-def]
        calls["count"] += 1
        raise OSError("staging rename is temporarily unavailable")

    service._publisher._materialize_candidate = fail_materialization  # type: ignore[method-assign]
    try:
        with pytest.raises(SourceSyncError) as error:
            _sync(
                service,
                source_root,
                request_id=request_id,
                expected_version=1,
            )
    finally:
        service._publisher._materialize_candidate = original  # type: ignore[method-assign]

    assert error.value.code is SourceSyncErrorCode.SOURCE_SYNC_RETRY_EXHAUSTED
    assert calls["count"] == len(SYNC_RETRY_DELAYS) + 1
    assert delays == list(SYNC_RETRY_DELAYS)
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    run = lifecycle.get_sync_run(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        request_id=request_id,
    )
    assert record.state is SourceLifecycleState.DEGRADED
    assert run.status != SYNC_RUN_RUNNING
    assert run.status != SYNC_RUN_SUCCESS
    assert run.result_code == SourceSyncErrorCode.SOURCE_SYNC_RETRY_EXHAUSTED.value
    assert lifecycle._repository.list_revisions(SOURCE_ID) == ()
    assert service._publisher.published_path(SOURCE_ID) is None


def test_materialization_oserror_retries_then_succeeds(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "物化重试成功"})
    delays: list[float] = []
    calls = {"count": 0}
    original = service._publisher._materialize_candidate
    service._sleeper = delays.append

    def fail_once(snapshot) -> None:  # type: ignore[no-untyped-def]
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("staging rename is temporarily unavailable")
        original(snapshot)

    service._publisher._materialize_candidate = fail_once  # type: ignore[method-assign]
    try:
        run = _sync(service, source_root, expected_version=1)
    finally:
        service._publisher._materialize_candidate = original  # type: ignore[method-assign]

    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert calls["count"] == 2
    assert delays == [SYNC_RETRY_DELAYS[0]]
    assert run.status == SYNC_RUN_SUCCESS
    assert record.state is SourceLifecycleState.READY
    assert record.published_generation == run.candidate_generation


def test_non_retryable_materialization_oserror_finishes_run(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "物化权限失败必须终态化"})
    request_id = generate_uuid7()
    calls = {"count": 0}
    original = service._publisher._materialize_candidate

    def deny_materialization(snapshot) -> None:  # type: ignore[no-untyped-def]
        calls["count"] += 1
        raise PermissionError("staging directory denied")

    service._publisher._materialize_candidate = deny_materialization  # type: ignore[method-assign]
    try:
        with pytest.raises(PermissionError):
            _sync(
                service,
                source_root,
                request_id=request_id,
                expected_version=1,
            )
    finally:
        service._publisher._materialize_candidate = original  # type: ignore[method-assign]

    assert calls["count"] == 1
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    run = lifecycle.get_sync_run(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        request_id=request_id,
    )
    assert record.state is SourceLifecycleState.DEGRADED
    assert run.status != SYNC_RUN_RUNNING
    assert run.status != SYNC_RUN_SUCCESS
    assert run.result_code == SourceSyncErrorCode.SOURCE_SYNC_VALIDATION_FAILED.value
    assert lifecycle._repository.list_revisions(SOURCE_ID) == ()


def test_non_retryable_error_runs_once(tmp_path: Path) -> None:
    _, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "权限"})
    calls = {"count": 0}
    original = service._enumerate

    def once(source_root, source_id):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        raise PermissionError("denied")

    service._enumerate = once  # type: ignore[method-assign]
    with pytest.raises(PermissionError):
        _sync(service, source_root, expected_version=1)
    assert calls["count"] == 1
    service._enumerate = original  # type: ignore[method-assign]


def test_cancel_before_publish_keeps_last_good(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "首版"})
    first = _sync(service, source_root, expected_version=1)
    (source_root / "a.md").write_text("次版", encoding="utf-8")
    ready = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)

    def cancel() -> None:
        current = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
        service.request_cancel(
            principal_id=PRINCIPAL,
            source_id=SOURCE_ID,
            request_id=active_request,
            expected_version=current.record_version,
        )

    active_request = generate_uuid7()
    service.before_stage["VALIDATE"] = cancel
    with pytest.raises(SourceSyncError) as error:
        _sync(
            service,
            source_root,
            request_id=active_request,
            expected_version=ready.record_version,
        )
    assert error.value.code is SourceSyncErrorCode.SOURCE_SYNC_CANCELLED
    degraded = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert degraded.state is SourceLifecycleState.DEGRADED
    assert degraded.published_generation == first.candidate_generation
    runs = lifecycle.list_sync_runs(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert runs[-1].status == SYNC_RUN_CANCELLED


def test_cancel_after_publish_started_does_not_fake_cancel(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "发布中"})
    request_id = generate_uuid7()

    def cancel() -> None:
        current = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
        service.request_cancel(
            principal_id=PRINCIPAL,
            source_id=SOURCE_ID,
            request_id=request_id,
            expected_version=current.record_version,
        )

    service.before_stage["PUBLISH"] = cancel
    run = _sync(service, source_root, request_id=request_id, expected_version=1)
    assert run.status == SYNC_RUN_SUCCESS
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert record.state is SourceLifecycleState.READY


def test_resume_from_assemble_checkpoint(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "可恢复"})
    request_id = generate_uuid7()

    def crash() -> None:
        raise RuntimeError("injected process interrupt")

    service.before_stage["VALIDATE"] = crash
    with pytest.raises(RuntimeError):
        _sync(service, source_root, request_id=request_id, expected_version=1)
    run = lifecycle.get_sync_run(
        principal_id=PRINCIPAL, source_id=SOURCE_ID, request_id=request_id
    )
    assert run.status == SYNC_RUN_RUNNING
    assert run.checkpoint_stage == "ASSEMBLE"
    service.before_stage.clear()
    resumed = _sync(service, source_root, request_id=request_id, expected_version=1)
    assert resumed.status == SYNC_RUN_SUCCESS
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert record.state is SourceLifecycleState.READY


def test_changed_input_on_resume_is_interrupted(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "原输入"})
    request_id = generate_uuid7()
    service.before_stage["VALIDATE"] = lambda: (_ for _ in ()).throw(RuntimeError("crash"))
    with pytest.raises(RuntimeError):
        _sync(service, source_root, request_id=request_id, expected_version=1)
    (source_root / "a.md").write_text("输入已变", encoding="utf-8")
    service.before_stage.clear()
    with pytest.raises(SourceSyncError) as error:
        _sync(service, source_root, request_id=request_id, expected_version=1)
    assert error.value.code is SourceSyncErrorCode.SOURCE_SYNC_INTERRUPTED
    run = lifecycle.get_sync_run(
        principal_id=PRINCIPAL, source_id=SOURCE_ID, request_id=request_id
    )
    assert run.status == "INTERRUPTED_INPUT_CHANGED"


def test_privacy_canaries_are_absent_from_control_plane(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    canaries = (
        "PRIVATE_DOCUMENT_BODY_8f31",
        "SECRET_TOKEN_8f31",
        r"C:\Users\private\course.pdf",
        "/home/private/course.pdf",
    )
    _write_docs(source_root, {"a.md": "公开摘要"})
    _sync(service, source_root, expected_version=1)
    db_path = tmp_path / "registry.sqlite3"
    with sqlite3.connect(db_path) as connection:
        payload = "\n".join(
            str(value)
            for table in ("source_records", "source_revisions", "sync_runs", "audit_events")
            for row in connection.execute(f"SELECT * FROM {table}")
            for value in row
            if value is not None
        )
    snapshot = service._publisher.load_snapshot(SOURCE_ID)
    assert snapshot is not None
    blob = payload + snapshot.canonical_bytes().decode("utf-8")
    for canary in canaries:
        assert canary not in blob


def test_sync_module_does_not_import_app_main() -> None:
    import ast
    import app.user_source_sync as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert "app.main" not in imported
    assert "fastapi" not in imported


def test_sync_publication_serializes_delete_admission(
    tmp_path: Path,
) -> None:
    import threading

    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "first generation"})
    entered = threading.Event()
    release = threading.Event()
    service.before_stage["PUBLISH"] = lambda: (entered.set(), release.wait(5))
    request_id = generate_uuid7()
    errors: list[BaseException] = []
    from app.source_delete import UserSourceDeleteService
    delete = UserSourceDeleteService(tmp_path / "cache", lifecycle)
    delete_request_id = generate_uuid7()

    def run_sync() -> None:
        try:
            _sync(service, source_root, request_id=request_id, expected_version=1)
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=run_sync)
    worker.start()
    assert entered.wait(5)
    before = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert before.state is SourceLifecycleState.SYNCING

    delete_started = threading.Event()
    delete_done = threading.Event()
    delete_errors: list[BaseException] = []

    def run_delete() -> None:
        try:
            delete_started.set()
            delete.request_delete(
                principal_id=PRINCIPAL,
                source_id=SOURCE_ID,
                request_id=delete_request_id,
                expected_version=before.record_version + 1,
                actor_type=SourceActorType.USER,
                reason="user-requested",
                correlation_id=CORRELATION,
            )
        except BaseException as exc:
            delete_errors.append(exc)
        finally:
            delete_done.set()

    deleter = threading.Thread(target=run_delete)
    deleter.start()
    assert delete_started.wait(5)
    assert not service._operation_lock.acquire(blocking=False)
    assert delete.get_intent(SOURCE_ID, delete_request_id) is None
    assert not delete_done.is_set()
    release.set()
    worker.join(5)
    deleter.join(5)
    assert not worker.is_alive()
    assert not deleter.is_alive()
    assert not errors
    assert not delete_errors
    final = lifecycle._repository.get_source(SOURCE_ID)
    assert final is not None
    assert final.state is SourceLifecycleState.DELETE_PENDING


def test_delete_pending_rejects_admitted_sync_publication(
    tmp_path: Path,
) -> None:
    import threading

    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "candidate generation"})
    admitted = threading.Event()
    release = threading.Event()
    service.before_stage["OPERATION_LOCK"] = lambda: (
        admitted.set(),
        release.wait(5),
    )
    request_id = generate_uuid7()
    sync_errors: list[BaseException] = []

    def run_sync() -> None:
        try:
            _sync(
                service,
                source_root,
                request_id=request_id,
                expected_version=1,
            )
        except BaseException as exc:
            sync_errors.append(exc)

    worker = threading.Thread(target=run_sync)
    worker.start()
    assert admitted.wait(5)
    syncing = lifecycle._repository.get_source(SOURCE_ID)
    assert syncing is not None
    assert syncing.state is SourceLifecycleState.SYNCING

    from app.source_delete import UserSourceDeleteService

    delete = UserSourceDeleteService(tmp_path / "cache", lifecycle)
    intent = delete.request_delete(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        request_id=generate_uuid7(),
        expected_version=syncing.record_version,
        actor_type=SourceActorType.USER,
        reason="user-requested",
        correlation_id=CORRELATION,
    )
    assert intent.barrier_published
    assert intent.surfaces_unreadable

    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert len(sync_errors) == 1
    assert isinstance(sync_errors[0], SourceSyncError)
    assert sync_errors[0].code is SourceSyncErrorCode.SOURCE_SYNC_VALIDATION_FAILED

    final = lifecycle._repository.get_source(SOURCE_ID)
    assert final is not None
    assert final.state is SourceLifecycleState.DELETE_PENDING
    assert final.published_generation is None
    assert final.published_revision_no is None
    assert lifecycle._repository.list_revisions(SOURCE_ID) == ()
    run = lifecycle._repository.get_sync_run(SOURCE_ID, request_id)
    assert run is not None
    assert run.status != SYNC_RUN_RUNNING
    assert run.status != SYNC_RUN_SUCCESS
    assert service._publisher.published_path(SOURCE_ID) is None
    assert service._offline._fts5.published_path(SOURCE_ID) is None
    assert service._offline._vector.published_path(SOURCE_ID) is None
