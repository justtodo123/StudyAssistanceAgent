from __future__ import annotations

import ast
import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.source_delete import (
    DELETE_SCHEMA_NUMERIC,
    DELETE_SCHEMA_VERSION,
    MIN_AUDIT_RETENTION_DAYS,
    SOURCE_WIDE_URI,
    SourceDeleteError,
    SourceDeleteErrorCode,
    UserSourceDeleteService,
)
from app.source_registry import (
    SourceActorType,
    SourceLifecycleErrorCode,
    SourceLifecycleException,
    SourceLifecycleService,
    SourceLifecycleState,
    SourceRevisionDraft,
    SqliteSourceRegistry,
    generate_uuid7,
)

pytestmark = pytest.mark.m7

SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
PRINCIPAL = "principal-owner"
OTHER = "principal-other"
CORRELATION = "corr-m7-delete"
REASON = "user-requested"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


class _Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class _GenerationPublisher:
    def __init__(self, *, current: str | None, snapshots: dict[str, object]) -> None:
        self.current = current
        self.snapshots = snapshots
        self.loads: list[tuple[str, str | None]] = []

    def load_snapshot(self, source_id: str, generation: str | None = None):
        self.loads.append((source_id, generation))
        resolved = generation or self.current
        return None if resolved is None else self.snapshots.get(resolved)


class _ClearRuntime:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def clear_source(self, source_id: str) -> None:
        if source_id in self.calls:
            raise AssertionError("runtime cleared more than once")
        self.calls.append(source_id)


def _document_id(uri: str, source_id: str = SOURCE_ID) -> str:
    return hashlib.sha256(f"{source_id}\0{uri}".encode("utf-8")).hexdigest()[:32]


def _revision() -> SourceRevisionDraft:
    return SourceRevisionDraft(
        build_result="SUCCESS",
        source_fingerprint=DIGEST_A,
        manifest_digest=DIGEST_B,
        parser_schema_version="parser-v1",
        chunk_schema_version="chunk-v1",
        generation="generation-1",
        document_count=1,
        chunk_count=1,
        raw_bytes=32,
    )


def _service(
    tmp_path: Path,
    *,
    source_id: str = SOURCE_ID,
    clock: _Clock | None = None,
    publisher=None,
):
    registry = SqliteSourceRegistry(tmp_path / "registry.sqlite3")
    lifecycle = SourceLifecycleService(registry, source_id_factory=lambda: source_id)
    record = lifecycle.register_source(
        owner_principal_id=PRINCIPAL,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION,
        source_id=source_id,
    )
    ready = lifecycle.transition_source(
        principal_id=PRINCIPAL,
        source_id=source_id,
        expected_version=record.record_version,
        target_state=SourceLifecycleState.SYNCING,
        actor_type=SourceActorType.SERVICE,
        correlation_id=CORRELATION,
    )
    ready = lifecycle.transition_source(
        principal_id=PRINCIPAL,
        source_id=source_id,
        expected_version=ready.record_version,
        target_state=SourceLifecycleState.READY,
        actor_type=SourceActorType.SERVICE,
        correlation_id=CORRELATION,
        revision=_revision(),
    )
    delete = UserSourceDeleteService(
        tmp_path / "cache",
        lifecycle,
        publisher=publisher,
        clock=clock or _utc,
    )
    delete.surfaces.seed(
        source_id,
        generation="generation-1",
        documents=(
            {
                "logical_uri": "lesson.md",
                "document_id": _document_id("lesson.md", source_id),
                "chunk_id": "chunk-1",
            },
        ),
        provenance=(
            {
                "document_id": _document_id("lesson.md", source_id),
                "logical_uri": "lesson.md",
                "origin_kind": "original",
                "derived_from_document_ids": [],
                "status": "ACTIVE",
            },
        ),
        result_cache={"cached": "VISIBLE_CACHE_HIT"},
    )
    return registry, lifecycle, delete, ready


def _utc() -> datetime:
    return datetime(2026, 9, 2, tzinfo=timezone.utc)


def _delete(service: UserSourceDeleteService, record, *, request_id: str | None = None, **kwargs):
    payload = {
        "principal_id": PRINCIPAL,
        "source_id": record.source_id,
        "request_id": request_id or generate_uuid7(),
        "expected_version": record.record_version,
        "actor_type": SourceActorType.USER,
        "reason": REASON,
        "correlation_id": CORRELATION,
    }
    payload.update(kwargs)
    return service.request_delete(**payload)


def test_delete_publishes_barrier_and_hides_surfaces(tmp_path: Path) -> None:
    registry, lifecycle, delete, record = _service(tmp_path)
    document_id = _document_id("lesson.md")
    assert delete.surfaces.lookup(SOURCE_ID, "bm25", document_id) == "lesson.md"

    intent = _delete(delete, record)

    hidden = registry.get_source(SOURCE_ID)
    assert hidden is not None
    assert hidden.state is SourceLifecycleState.DELETE_PENDING
    assert intent.barrier_published is True
    assert intent.surfaces_unreadable is True
    assert any(item.logical_uri == SOURCE_WIDE_URI for item in delete.list_tombstones(SOURCE_ID))
    assert delete.is_blocked(SOURCE_ID, logical_uri="lesson.md", document_id=document_id)
    assert delete.surfaces.readable(SOURCE_ID, "bm25") is False
    assert delete.surfaces.lookup(SOURCE_ID, "bm25", document_id) is None
    assert delete.surfaces.lookup(SOURCE_ID, "vector", document_id) is None
    assert delete.surfaces.lookup(SOURCE_ID, "result_cache", "cached") is None
    assert delete.surfaces.lookup(SOURCE_ID, "provenance", document_id) is None
    with pytest.raises(SourceLifecycleException) as exc:
        lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert exc.value.code is SourceLifecycleErrorCode.SOURCE_NOT_FOUND


def test_delete_uses_authoritative_generation_when_current_is_stale(tmp_path: Path) -> None:
    authoritative = SimpleNamespace(
        documents=(
            SimpleNamespace(
                logical_uri="authoritative.md",
                document_id=_document_id("authoritative.md"),
            ),
        ),
    )
    stale = SimpleNamespace(
        documents=(
            SimpleNamespace(
                logical_uri="stale.md",
                document_id=_document_id("stale.md"),
            ),
        ),
    )
    publisher = _GenerationPublisher(
        current="stale-generation",
        snapshots={"generation-1": authoritative, "stale-generation": stale},
    )
    _, _, delete, record = _service(tmp_path, publisher=publisher)

    intent = _delete(delete, record)

    tombstones = delete.list_tombstones(SOURCE_ID)
    assert publisher.loads == [(SOURCE_ID, intent.generation_upper_bound)]
    assert intent.generation_upper_bound == "generation-1"
    assert any(item.logical_uri == "authoritative.md" for item in tombstones)
    assert not any(item.logical_uri == "stale.md" for item in tombstones)
    assert all(item.generation_upper_bound == "generation-1" for item in tombstones)


def test_delete_uses_authoritative_generation_when_current_is_missing(tmp_path: Path) -> None:
    authoritative = SimpleNamespace(
        documents=(
            SimpleNamespace(
                logical_uri="authoritative.md",
                document_id=_document_id("authoritative.md"),
            ),
            SimpleNamespace(
                logical_uri="second.md",
                document_id=_document_id("second.md"),
            ),
        ),
    )
    publisher = _GenerationPublisher(
        current=None,
        snapshots={"generation-1": authoritative},
    )
    _, _, delete, record = _service(tmp_path, publisher=publisher)

    intent = _delete(delete, record)

    tombstones = delete.list_tombstones(SOURCE_ID)
    file_tombstones = {item.logical_uri: item.document_id for item in tombstones if item.document_id}
    assert publisher.loads == [(SOURCE_ID, intent.generation_upper_bound)]
    assert file_tombstones == {
        "authoritative.md": _document_id("authoritative.md"),
        "second.md": _document_id("second.md"),
    }
    assert all(item.generation_upper_bound == "generation-1" for item in tombstones)


def test_repeat_request_id_is_idempotent(tmp_path: Path) -> None:
    _, _, delete, record = _service(tmp_path)
    request_id = generate_uuid7()
    first = _delete(delete, record, request_id=request_id)
    second = _delete(delete, record, request_id=request_id)
    assert first == second
    with sqlite3.connect(tmp_path / "cache" / "source-delete" / "v1" / "delete.sqlite3") as connection:
        count = connection.execute("SELECT COUNT(*) FROM deletion_intents").fetchone()[0]
    assert count == 1


def test_same_request_id_with_different_reason_conflicts(tmp_path: Path) -> None:
    _, _, delete, record = _service(tmp_path)
    request_id = generate_uuid7()
    _delete(delete, record, request_id=request_id)
    with pytest.raises(SourceDeleteError) as exc:
        _delete(delete, record, request_id=request_id, reason="other-reason")
    assert exc.value.code is SourceDeleteErrorCode.SOURCE_DELETE_REQUEST_CONFLICT


def test_v1_schema_migration_preserves_intent_and_tombstones(tmp_path: Path) -> None:
    registry, lifecycle, delete, record = _service(tmp_path)
    intent = _delete(delete, record)
    assert delete.list_tombstones(SOURCE_ID)
    db_path = tmp_path / "cache" / "source-delete" / "v1" / "delete.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP TABLE hard_delete_operations")
        connection.execute("UPDATE delete_meta SET schema_version = 1 WHERE singleton = 1")
        connection.commit()

    reopened = UserSourceDeleteService(tmp_path / "cache", lifecycle, clock=_utc)
    assert reopened.get_intent(SOURCE_ID, intent.request_id) == intent
    assert reopened.list_tombstones(SOURCE_ID)
    with sqlite3.connect(db_path) as connection:
        assert connection.execute(
            "SELECT schema_version FROM delete_meta WHERE singleton = 1"
        ).fetchone()[0] == DELETE_SCHEMA_NUMERIC
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(hard_delete_operations)")
        }
    assert columns == {
        "source_id",
        "request_id",
        "object_counts",
        "store_digests",
        "started_at",
        "schema_version",
    }
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETE_PENDING


def test_v1_schema_migration_preserves_existing_receipt(tmp_path: Path) -> None:
    clock = _Clock(_utc())
    _, lifecycle, delete, record = _service(tmp_path, clock=clock)
    intent = _delete(delete, record)
    clock.now = _utc() + timedelta(days=MIN_AUDIT_RETENTION_DAYS)
    receipt = delete.sweep_hard_delete(SOURCE_ID, intent.request_id)
    assert receipt is not None
    db_path = tmp_path / "cache" / "source-delete" / "v1" / "delete.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP TABLE hard_delete_operations")
        connection.execute("UPDATE delete_meta SET schema_version = 1 WHERE singleton = 1")
        connection.commit()

    reopened = UserSourceDeleteService(tmp_path / "cache", lifecycle, clock=clock)
    assert reopened.get_intent(SOURCE_ID, intent.request_id) == intent
    assert reopened.get_receipt(SOURCE_ID, intent.request_id) == receipt


def test_v2_missing_operation_table_fails_closed(tmp_path: Path) -> None:
    _, lifecycle, delete, _ = _service(tmp_path)
    db_path = tmp_path / "cache" / "source-delete" / "v1" / "delete.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP TABLE hard_delete_operations")
        connection.commit()
    with pytest.raises(SourceDeleteError) as exc:
        UserSourceDeleteService(tmp_path / "cache", lifecycle)
    assert exc.value.code is SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED


def test_malformed_operation_table_shape_fails_closed(tmp_path: Path) -> None:
    _, lifecycle, delete, _ = _service(tmp_path)
    db_path = tmp_path / "cache" / "source-delete" / "v1" / "delete.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("ALTER TABLE hard_delete_operations DROP COLUMN store_digests")
        connection.commit()
    with pytest.raises(SourceDeleteError) as exc:
        UserSourceDeleteService(tmp_path / "cache", lifecycle)
    assert exc.value.code is SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED


def test_malformed_operation_manifest_fails_closed(tmp_path: Path) -> None:
    _, lifecycle, delete, record = _service(tmp_path)
    intent = _delete(delete, record)
    db_path = tmp_path / "cache" / "source-delete" / "v1" / "delete.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """INSERT INTO hard_delete_operations
               (source_id, request_id, object_counts, store_digests, started_at, schema_version)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                SOURCE_ID,
                intent.request_id,
                '{"surfaces":0}',
                "{}",
                _utc().isoformat().replace("+00:00", "Z"),
                1,
            ),
        )
        connection.commit()
    with pytest.raises(SourceDeleteError) as exc:
        delete._get_hard_delete_operation(SOURCE_ID, intent.request_id)
    assert exc.value.code is SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE


def test_unknown_fields_and_future_schema_are_rejected(tmp_path: Path) -> None:
    _, _, delete, record = _service(tmp_path)
    with pytest.raises(SourceDeleteError) as unknown:
        _delete(delete, record, extra_fields={"owner_principal_id": PRINCIPAL})
    assert unknown.value.code is SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST
    with pytest.raises(SourceDeleteError) as schema:
        _delete(delete, record, protocol_version="sa.source.delete.v2")
    assert schema.value.code is SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED


def test_unauthorized_and_already_deleted_are_stable(tmp_path: Path) -> None:
    registry, lifecycle, delete, record = _service(tmp_path)
    with pytest.raises(SourceDeleteError) as missing:
        _delete(delete, record, principal_id=OTHER)
    assert missing.value.code is SourceDeleteErrorCode.SOURCE_NOT_FOUND
    intent = _delete(delete, record)
    clock = _Clock(_utc() + timedelta(days=MIN_AUDIT_RETENTION_DAYS))
    delete._clock = clock
    receipt = delete.sweep_hard_delete(SOURCE_ID, intent.request_id)
    assert receipt is not None
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETED
    with pytest.raises(SourceDeleteError) as deleted:
        delete.request_delete(
            principal_id=PRINCIPAL,
            source_id=SOURCE_ID,
            request_id=generate_uuid7(),
            expected_version=registry.get_source(SOURCE_ID).record_version,
            actor_type=SourceActorType.USER,
            reason=REASON,
            correlation_id=CORRELATION,
        )
    assert deleted.value.code is SourceDeleteErrorCode.SOURCE_ALREADY_DELETED
    with pytest.raises(SourceLifecycleException):
        lifecycle.transition_source(
            principal_id=PRINCIPAL,
            source_id=SOURCE_ID,
            expected_version=registry.get_source(SOURCE_ID).record_version,
            target_state=SourceLifecycleState.READY,
            actor_type=SourceActorType.SERVICE,
            correlation_id=CORRELATION,
        )


def test_one_hundred_concurrent_deletes_have_one_success(tmp_path: Path) -> None:
    successes = 0
    conflicts = 0
    for pair in range(100):
        root = tmp_path / f"pair-{pair}"
        source_id = f"user-01890f52-47e7-7abc-8def-{pair:012x}"
        _, _, delete, record = _service(root, source_id=source_id)
        request_ids = (generate_uuid7(), generate_uuid7())

        def write(index: int) -> str:
            try:
                _delete(delete, record, request_id=request_ids[index])
            except SourceDeleteError as exc:
                return exc.code.value
            return "SUCCESS"

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = tuple(executor.map(write, range(2)))
        assert sorted(outcomes) == [
            SourceDeleteErrorCode.SOURCE_VERSION_CONFLICT.value,
            "SUCCESS",
        ]
        successes += outcomes.count("SUCCESS")
        conflicts += outcomes.count(SourceDeleteErrorCode.SOURCE_VERSION_CONFLICT.value)
    assert successes == 100
    assert conflicts == 100


def test_version_conflict_discards_unadmitted_intent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry, lifecycle, delete, record = _service(tmp_path)
    original_transition = lifecycle.transition_source
    advanced = False

    def transition_with_interleaving(**kwargs):
        nonlocal advanced
        if kwargs["target_state"] is SourceLifecycleState.DELETE_PENDING and not advanced:
            advanced = True
            current = registry.get_source(SOURCE_ID)
            original_transition(
                principal_id=PRINCIPAL,
                source_id=SOURCE_ID,
                expected_version=current.record_version,
                target_state=SourceLifecycleState.SYNCING,
                actor_type=SourceActorType.SERVICE,
                correlation_id=CORRELATION,
            )
        return original_transition(**kwargs)

    monkeypatch.setattr(lifecycle, "transition_source", transition_with_interleaving)
    stale_request = generate_uuid7()
    with pytest.raises(SourceDeleteError) as exc:
        _delete(delete, record, request_id=stale_request)
    assert exc.value.code is SourceDeleteErrorCode.SOURCE_VERSION_CONFLICT
    assert delete.get_intent(SOURCE_ID, stale_request) is None

    current = registry.get_source(SOURCE_ID)
    intent = _delete(delete, current)
    assert intent.barrier_published is True
    assert intent.surfaces_unreadable is True
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETE_PENDING


def test_retryable_barrier_failure_uses_one_bounded_budget(tmp_path: Path) -> None:
    delays: list[float] = []
    registry, lifecycle, _, record = _service(tmp_path)
    delete = UserSourceDeleteService(
        tmp_path / "cache",
        lifecycle,
        sleeper=delays.append,
    )
    delete.stage_faults["after_tombstone"] = [
        OSError("retryable") for _ in range(10)
    ]

    with pytest.raises(SourceDeleteError) as exc:
        _delete(delete, record)
    assert exc.value.code is SourceDeleteErrorCode.SOURCE_DELETE_FAILED
    assert delays == list(delete._retry_delays)
    assert len(delete.stage_faults["after_tombstone"]) == 7
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETE_PENDING


def test_barrier_retry_sleeps_after_releasing_operation_lock(
    tmp_path: Path,
) -> None:
    import threading

    sleep_entered = threading.Event()
    release_sleep = threading.Event()
    lock_acquired = threading.Event()
    registry, lifecycle, _, record = _service(tmp_path)

    def sleeper(_delay: float) -> None:
        sleep_entered.set()
        assert release_sleep.wait(5)

    delete = UserSourceDeleteService(
        tmp_path / "cache",
        lifecycle,
        sleeper=sleeper,
    )
    delete.stage_faults["after_tombstone"] = [OSError("retryable")]
    errors: list[BaseException] = []

    def run_delete() -> None:
        try:
            _delete(delete, record)
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=run_delete)
    worker.start()
    assert sleep_entered.wait(5)

    def acquire_same_cache_lock() -> None:
        with delete._operation_lock:
            lock_acquired.set()

    probe = threading.Thread(target=acquire_same_cache_lock)
    probe.start()
    assert lock_acquired.wait(5)
    release_sleep.set()
    worker.join(5)
    probe.join(5)
    assert not worker.is_alive()
    assert not probe.is_alive()
    assert not errors
    intent = delete.get_intent(SOURCE_ID, delete._intent_for_source(SOURCE_ID).request_id)
    assert intent is not None
    assert intent.barrier_published
    assert intent.surfaces_unreadable
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETE_PENDING


def test_concurrent_barrier_recovery_and_sweep_are_idempotent(
    tmp_path: Path,
) -> None:
    import threading

    clock = _Clock(_utc())
    registry, _, delete, record = _service(tmp_path, clock=clock)
    runtime = _ClearRuntime()
    delete.attach_runtime(runtime)
    request_id = generate_uuid7()
    delete.stage_faults["after_cas"] = [RuntimeError("injected")]

    with pytest.raises(SourceDeleteError) as exc:
        _delete(delete, record, request_id=request_id)
    assert exc.value.code is SourceDeleteErrorCode.SOURCE_DELETE_FAILED
    intent = delete.get_intent(SOURCE_ID, request_id)
    assert intent is not None
    assert not intent.barrier_published
    assert not intent.surfaces_unreadable
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETE_PENDING

    clock.now = intent.created_at + timedelta(days=MIN_AUDIT_RETENTION_DAYS)
    start = threading.Barrier(3)

    def sweep():  # type: ignore[no-untyped-def]
        start.wait()
        return delete.sweep_hard_delete(SOURCE_ID, request_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (executor.submit(sweep), executor.submit(sweep))
        start.wait()
        receipts = tuple(future.result(timeout=5) for future in futures)

    assert receipts[0] is not None
    assert receipts[1] == receipts[0]
    receipt = receipts[0]
    operation = delete._get_hard_delete_operation(SOURCE_ID, request_id)
    assert operation is not None
    assert receipt.object_counts == operation.object_counts
    assert receipt.store_digests == operation.store_digests
    assert receipt.started_at == operation.started_at
    assert runtime.calls == [SOURCE_ID]
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETED
    assert delete.list_tombstones(SOURCE_ID) == ()
    assert not delete.surfaces.path(SOURCE_ID).exists()
    assert delete.sweep_hard_delete(SOURCE_ID, request_id) == receipt

    db_path = tmp_path / "cache" / "source-delete" / "v1" / "delete.sqlite3"
    with sqlite3.connect(db_path) as connection:
        receipt_count = connection.execute(
            """SELECT COUNT(*) FROM hard_delete_receipts
               WHERE source_id = ? AND request_id = ?""",
            (SOURCE_ID, request_id),
        ).fetchone()[0]
        operation_count = connection.execute(
            """SELECT COUNT(*) FROM hard_delete_operations
               WHERE source_id = ? AND request_id = ?""",
            (SOURCE_ID, request_id),
        ).fetchone()[0]
    assert receipt_count == 1
    assert operation_count == 1


def test_physical_clear_invalidates_each_runtime_once_by_identity(tmp_path: Path) -> None:
    clock = _Clock(_utc())
    _, _, delete, record = _service(tmp_path, clock=clock)
    first = _ClearRuntime()
    second = _ClearRuntime()
    delete.attach_runtime(first)
    delete.attach_runtime(second)
    delete.attach_runtime(first)
    intent = _delete(delete, record)
    clock.now = _utc() + timedelta(days=MIN_AUDIT_RETENTION_DAYS)

    receipt = delete.sweep_hard_delete(SOURCE_ID, intent.request_id)

    assert receipt is not None
    assert first.calls == [SOURCE_ID]
    assert second.calls == [SOURCE_ID]


def test_attach_index_runtimes_retains_all_cache_owners_by_identity(tmp_path: Path) -> None:
    class EqualRuntime(_ClearRuntime):
        def __eq__(self, other: object) -> bool:
            return isinstance(other, EqualRuntime)

    _, _, delete, _ = _service(tmp_path)
    previous_fts5 = EqualRuntime()
    previous_vector = EqualRuntime()
    retained = EqualRuntime()
    replacement_fts5 = EqualRuntime()
    replacement_vector = EqualRuntime()
    delete.attach_index_runtimes(previous_fts5, previous_vector)
    delete.attach_runtime(retained)

    delete.attach_index_runtimes(replacement_fts5, replacement_vector)
    delete.attach_index_runtimes(replacement_fts5, replacement_vector)

    expected = (
        previous_fts5,
        previous_vector,
        retained,
        replacement_fts5,
        replacement_vector,
    )
    assert len(delete._runtimes) == len(expected)
    assert all(
        any(runtime is item for item in delete._runtimes)
        for runtime in expected
    )


def test_fault_after_physical_clear_replays_receipt_and_transition(tmp_path: Path) -> None:
    clock = _Clock(_utc())
    registry, _, delete, record = _service(tmp_path, clock=clock)
    intent = _delete(delete, record)
    clock.now = _utc() + timedelta(days=MIN_AUDIT_RETENTION_DAYS)
    operation = delete._prepare_hard_delete_operation(
        SOURCE_ID,
        intent.request_id,
        clock.now,
    )
    assert operation.object_counts["surfaces"] == 1
    delete.stage_faults["after_physical_clear"] = [RuntimeError("injected")]

    with pytest.raises(SourceDeleteError) as exc:
        delete.sweep_hard_delete(SOURCE_ID, intent.request_id)
    assert exc.value.code is SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE
    assert delete.surfaces.path(SOURCE_ID).exists() is False
    assert delete.list_tombstones(SOURCE_ID) == ()
    assert delete.get_receipt(SOURCE_ID, intent.request_id) is None
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETE_PENDING

    receipt = delete.sweep_hard_delete(SOURCE_ID, intent.request_id)
    assert receipt is not None
    assert receipt.object_counts == operation.object_counts
    assert receipt.store_digests == operation.store_digests
    assert delete.get_receipt(SOURCE_ID, intent.request_id) == receipt
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETED


def test_operation_manifest_survives_crash_before_physical_clear(tmp_path: Path) -> None:
    clock = _Clock(_utc())
    registry, _, delete, record = _service(tmp_path, clock=clock)
    intent = _delete(delete, record)
    clock.now = _utc() + timedelta(days=MIN_AUDIT_RETENTION_DAYS)
    delete.stage_faults["after_operation_prepared"] = [RuntimeError("injected")]

    with pytest.raises(SourceDeleteError) as exc:
        delete.sweep_hard_delete(SOURCE_ID, intent.request_id)
    assert exc.value.code is SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE
    operation = delete._get_hard_delete_operation(SOURCE_ID, intent.request_id)
    assert operation is not None
    assert operation.object_counts["surfaces"] == 1
    assert delete.surfaces.path(SOURCE_ID).exists() is True
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETE_PENDING

    receipt = delete.sweep_hard_delete(SOURCE_ID, intent.request_id)
    assert receipt is not None
    assert receipt.object_counts == operation.object_counts
    assert receipt.store_digests == operation.store_digests
    assert receipt.started_at == operation.started_at


@pytest.mark.parametrize("checkpoint", ["after_cas", "after_tombstone", "after_surfaces_unreadable"])
def test_faults_keep_source_unreadable_and_resume(tmp_path: Path, checkpoint: str) -> None:
    for index in range(20):
        root = tmp_path / checkpoint / f"run-{index}"
        source_id = f"user-01890f52-47e7-7abc-8def-{index:012x}"
        registry, _, delete, record = _service(root, source_id=source_id)
        request_id = generate_uuid7()
        delete.stage_faults[checkpoint] = [RuntimeError("injected")]
        with pytest.raises(SourceDeleteError) as exc:
            _delete(delete, record, request_id=request_id)
        assert exc.value.code is SourceDeleteErrorCode.SOURCE_DELETE_FAILED
        pending = registry.get_source(source_id)
        assert pending is not None
        assert pending.state is SourceLifecycleState.DELETE_PENDING
        resumed = _delete(delete, record, request_id=request_id)
        assert resumed.barrier_published is True
        assert resumed.surfaces_unreadable is True
        assert delete.surfaces.readable(source_id) is False


def test_hard_delete_fault_before_receipt_does_not_complete(tmp_path: Path) -> None:
    for index in range(20):
        root = tmp_path / f"receipt-{index}"
        source_id = f"user-01890f52-47e7-7abc-8def-{index:012x}"
        clock = _Clock(_utc())
        registry, _, delete, record = _service(root, source_id=source_id, clock=clock)
        intent = _delete(delete, record)
        clock.now = _utc() + timedelta(days=MIN_AUDIT_RETENTION_DAYS)
        delete.stage_faults["before_receipt"] = [RuntimeError("injected")]
        with pytest.raises(SourceDeleteError) as exc:
            delete.sweep_hard_delete(source_id, intent.request_id)
        assert exc.value.code in {
            SourceDeleteErrorCode.SOURCE_DELETE_FAILED,
            SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE,
        }
        assert registry.get_source(source_id).state is SourceLifecycleState.DELETE_PENDING
        assert delete.get_receipt(source_id, intent.request_id) is None
        receipt = delete.sweep_hard_delete(source_id, intent.request_id)
        assert receipt is not None
        assert registry.get_source(source_id).state is SourceLifecycleState.DELETED


def test_hard_delete_receipt_resumes_deleted_transition(tmp_path: Path) -> None:
    clock = _Clock(_utc())
    registry, _, delete, record = _service(tmp_path, clock=clock)
    intent = _delete(delete, record)
    clock.now = _utc() + timedelta(days=MIN_AUDIT_RETENTION_DAYS)
    delete.stage_faults["before_deleted_transition"] = [RuntimeError("injected")]

    with pytest.raises(SourceDeleteError) as exc:
        delete.sweep_hard_delete(SOURCE_ID, intent.request_id)
    assert exc.value.code is SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE
    receipt = delete.get_receipt(SOURCE_ID, intent.request_id)
    assert receipt is not None
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETE_PENDING
    assert delete.surfaces.readable(SOURCE_ID, "bm25") is False

    resumed = delete.sweep_hard_delete(SOURCE_ID, intent.request_id)
    assert resumed == receipt
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETED
    assert delete.sweep_hard_delete(SOURCE_ID, intent.request_id) == receipt


def test_retention_boundary_blocks_then_emits_receipt(tmp_path: Path) -> None:
    for index in range(20):
        root = tmp_path / f"retain-{index}"
        source_id = f"user-01890f52-47e7-7abc-8def-{index:012x}"
        clock = _Clock(_utc())
        registry, _, delete, record = _service(root, source_id=source_id, clock=clock)
        intent = _delete(delete, record)
        clock.now = intent.created_at + timedelta(days=MIN_AUDIT_RETENTION_DAYS) - timedelta(seconds=1)
        assert delete.sweep_hard_delete(source_id, intent.request_id) is None
        assert registry.get_source(source_id).state is SourceLifecycleState.DELETE_PENDING
        assert delete.list_tombstones(source_id)
        clock.now = intent.created_at + timedelta(days=MIN_AUDIT_RETENTION_DAYS)
        receipt = delete.sweep_hard_delete(source_id, intent.request_id)
        assert receipt is not None
        assert receipt.result_code == "HARD_DELETE_COMPLETED"
        assert set(receipt.object_counts) == {
            "snapshots",
            "normalized_documents",
            "fts5",
            "vector",
            "tombstones",
            "surfaces",
        }
        assert set(receipt.store_digests) == set(receipt.object_counts)
        assert delete.list_tombstones(source_id) == ()
        assert not delete.surfaces.path(source_id).exists()
        assert not (
            root
            / "cache"
            / "user-source-fts5"
            / "v1"
            / source_id
        ).exists()
        assert not (
            root
            / "cache"
            / "user-source-vector"
            / "v1"
            / source_id
        ).exists()
        assert registry.get_source(source_id).state is SourceLifecycleState.DELETED
        replay = delete.sweep_hard_delete(source_id, intent.request_id)
        assert replay == receipt


def test_origin_delete_marks_derived_provenance_stale(tmp_path: Path) -> None:
    other_id = "user-01890f52-47e7-7abc-8def-0123456789ac"
    _, _, delete, record = _service(tmp_path)
    origin_id = _document_id("lesson.md")
    derived_id = _document_id("notes.md", other_id)
    delete.surfaces.seed(
        other_id,
        generation="generation-9",
        documents=({"logical_uri": "notes.md", "document_id": derived_id, "chunk_id": "c2"},),
        provenance=(
            {
                "document_id": derived_id,
                "logical_uri": "notes.md",
                "origin_kind": "human_refined",
                "derived_from_document_ids": [origin_id],
                "status": "ACTIVE",
            },
        ),
    )
    _delete(delete, record)
    assert delete.surfaces.provenance_status(other_id, derived_id) == "STALE_DERIVATION"
    assert delete.surfaces.lookup(SOURCE_ID, "provenance", origin_id) is None


def test_privacy_canaries_are_absent_from_delete_records(tmp_path: Path) -> None:
    canaries = (
        "PRIVATE_DOCUMENT_BODY_8f31",
        "SECRET_TOKEN_8f31",
        r"C:\Users\private\course.pdf",
        "/home/private/course.pdf",
        r"\\server\share\course.pdf",
        "VISIBLE_CACHE_HIT",
    )
    clock = _Clock(_utc())
    registry, _, delete, record = _service(tmp_path, clock=clock)
    intent = _delete(delete, record)
    clock.now = _utc() + timedelta(days=MIN_AUDIT_RETENTION_DAYS)
    receipt = delete.sweep_hard_delete(SOURCE_ID, intent.request_id)
    assert receipt is not None
    db_path = tmp_path / "cache" / "source-delete" / "v1" / "delete.sqlite3"
    with sqlite3.connect(db_path) as connection:
        payload = "\n".join(
            str(value)
            for table in ("deletion_intents", "tombstones", "hard_delete_operations", "hard_delete_receipts")
            for row in connection.execute(f"SELECT * FROM {table}")
            for value in row
            if value is not None
        )
    blob = payload + str(intent.to_public_dict()) + str(receipt.to_public_dict())
    for canary in canaries:
        assert canary not in blob
    audit = delete.inspect_for_audit(actor_type=SourceActorType.ADMIN, source_id=SOURCE_ID)
    assert audit["source_id"] == SOURCE_ID
    with pytest.raises(SourceDeleteError) as hidden:
        delete.inspect_for_audit(actor_type=SourceActorType.USER, source_id=SOURCE_ID)
    assert hidden.value.code is SourceDeleteErrorCode.SOURCE_NOT_FOUND
    for canary in canaries:
        assert canary not in str(hidden.value)
        assert canary not in str(audit)
    assert registry.get_source(SOURCE_ID).state is SourceLifecycleState.DELETED


def test_delete_module_does_not_import_app_main() -> None:
    module = Path("platform/app/source_delete.py").read_text(encoding="utf-8")
    tree = ast.parse(module)
    imported = {
        alias.name
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else node.names)
    }
    assert "app.main" not in module
    assert "main" not in imported
