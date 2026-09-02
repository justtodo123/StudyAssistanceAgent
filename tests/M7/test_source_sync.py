from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.parser_matrix import ParsedDocument, ParsedUnit
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
from app.user_source_sync import (
    SYNC_RETRY_DELAYS,
    SourceSyncError,
    SourceSyncErrorCode,
    UserSourceSyncService,
)

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
    sync = UserSourceSyncService(
        tmp_path / "cache",
        lifecycle,
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


def test_first_full_sync_publishes_ready_revision(tmp_path: Path) -> None:
    lifecycle, service, source_root = _service(tmp_path)
    _write_docs(source_root, {"a.md": "操作系统调度", "b.md": "进程与线程"})
    run = _sync(service, source_root, expected_version=1)

    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert run.status == SYNC_RUN_SUCCESS
    assert record.state is SourceLifecycleState.READY
    assert record.published_generation == run.candidate_generation
    assert len(lifecycle.list_sync_runs(principal_id=PRINCIPAL, source_id=SOURCE_ID)) == 1
    snapshot = service._publisher.load_snapshot(SOURCE_ID)
    assert snapshot is not None
    assert snapshot.document_count == 2
    assert b"source_root" not in snapshot.canonical_bytes()


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
