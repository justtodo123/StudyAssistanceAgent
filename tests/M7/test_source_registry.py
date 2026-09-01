from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, fields
from datetime import datetime, timezone
from enum import Enum

import pytest

from app.source_registry import (
    AuditEvent,
    LifecycleError,
    SourceActorType,
    SourceLifecycleErrorCode,
    SourceLifecycleException,
    SourceLifecycleService,
    SourceLifecycleState,
    SourceRecord,
    SourceRevision,
    SourceRevisionDraft,
    SqliteSourceRegistry,
    SyncRun,
    generate_uuid7,
    validate_user_source_id,
)

pytestmark = pytest.mark.m7

PRINCIPAL = "principal-owner"
OTHER_PRINCIPAL = "principal-other"
SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
SECOND_SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ac"
CORRELATION_ID = "corr-m7-test"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def _service(tmp_path, *, source_id: str = SOURCE_ID):
    repository = SqliteSourceRegistry(tmp_path / "registry.sqlite3")
    service = SourceLifecycleService(
        repository,
        source_id_factory=lambda: source_id,
    )
    return repository, service


def _register(service: SourceLifecycleService, *, source_id: str | None = None):
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


def _canonical_json(record) -> str:
    def normalize(value):
        if isinstance(value, datetime):
            return value.isoformat().replace("+00:00", "Z")
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        return value

    return json.dumps(
        normalize(asdict(record)),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def test_uuid7_generator_and_user_source_validation():
    value = generate_uuid7(timestamp_ms=1_700_000_000_000)
    assert value == value.lower()
    assert value[14] == "7"
    assert validate_user_source_id(f"user-{value}") == f"user-{value}"

    for invalid in (
        "user-notes",
        SOURCE_ID.upper(),
        "knowledge-pack",
        "user-01890f52-47e7-6abc-8def-0123456789ab",
    ):
        with pytest.raises(ValueError):
            validate_user_source_id(invalid)


def test_all_lifecycle_records_have_schema_version_time_and_immutable_identity():
    record_types = (SourceRecord, SourceRevision, SyncRun, LifecycleError, AuditEvent)
    for record_type in record_types:
        names = {field.name for field in fields(record_type)}
        assert "schema_version" in names
        assert any(name.endswith("_at") for name in names)

    now = datetime.now(timezone.utc)
    record = SourceRecord(
        source_id=SOURCE_ID,
        owner_principal_id=PRINCIPAL,
        state=SourceLifecycleState.REGISTERED,
        record_version=1,
        created_at=now,
        updated_at=now,
    )
    with pytest.raises((AttributeError, TypeError)):
        record.source_id = SECOND_SOURCE_ID


def test_lifecycle_repository_protocol_is_distinct_and_structural(tmp_path):
    from app.source_registry import SourceLifecycleRepository, SourceLifecycleTransaction

    repository = SqliteSourceRegistry(tmp_path / "registry.sqlite3")
    assert isinstance(repository, SourceLifecycleRepository)
    with repository.transaction() as transaction:
        assert isinstance(transaction, SourceLifecycleTransaction)
    assert not hasattr(repository, "save")


def test_register_is_atomic_and_audited(tmp_path):
    repository, service = _service(tmp_path)
    record = _register(service)

    assert record.state is SourceLifecycleState.REGISTERED
    assert record.record_version == 1
    events = repository.list_audit_events(record.source_id)
    assert len(events) == 1
    assert events[0].before_state is None
    assert events[0].after_state is SourceLifecycleState.REGISTERED


def test_duplicate_id_and_initial_expected_version_are_stable_errors(tmp_path):
    _, service = _service(tmp_path)
    _register(service)

    with pytest.raises(SourceLifecycleException) as duplicate:
        _register(service, source_id=SOURCE_ID)
    assert duplicate.value.code is SourceLifecycleErrorCode.SOURCE_ID_CONFLICT

    with pytest.raises(SourceLifecycleException) as mismatch:
        service.register_source(
            owner_principal_id=PRINCIPAL,
            expected_version=1,
            actor_type=SourceActorType.USER,
            correlation_id=CORRELATION_ID,
            source_id=SECOND_SOURCE_ID,
        )
    assert mismatch.value.code is SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT


LEGAL_EDGES = {
    SourceLifecycleState.REGISTERED: {
        SourceLifecycleState.SYNCING,
        SourceLifecycleState.DISABLED,
        SourceLifecycleState.DELETE_PENDING,
    },
    SourceLifecycleState.SYNCING: {
        SourceLifecycleState.READY,
        SourceLifecycleState.DEGRADED,
        SourceLifecycleState.DISABLED,
        SourceLifecycleState.DELETE_PENDING,
    },
    SourceLifecycleState.READY: {
        SourceLifecycleState.SYNCING,
        SourceLifecycleState.DISABLED,
        SourceLifecycleState.DELETE_PENDING,
    },
    SourceLifecycleState.DEGRADED: {
        SourceLifecycleState.SYNCING,
        SourceLifecycleState.DISABLED,
        SourceLifecycleState.DELETE_PENDING,
    },
    SourceLifecycleState.DISABLED: {
        SourceLifecycleState.SYNCING,
        SourceLifecycleState.DELETE_PENDING,
    },
    SourceLifecycleState.DELETE_PENDING: {SourceLifecycleState.DELETED},
    SourceLifecycleState.DELETED: set(),
}


def _reach_state(service: SourceLifecycleService, state: SourceLifecycleState):
    record = _register(service)
    if state is SourceLifecycleState.REGISTERED:
        return record
    if state is SourceLifecycleState.SYNCING:
        return _transition(service, record, state)
    if state is SourceLifecycleState.READY:
        record = _transition(service, record, SourceLifecycleState.SYNCING)
        return _transition(service, record, state, revision=_revision())
    if state is SourceLifecycleState.DEGRADED:
        record = _transition(service, record, SourceLifecycleState.SYNCING)
        return _transition(service, record, state)
    if state is SourceLifecycleState.DISABLED:
        return _transition(service, record, state)
    record = _transition(service, record, SourceLifecycleState.DELETE_PENDING)
    if state is SourceLifecycleState.DELETE_PENDING:
        return record
    return _transition(service, record, SourceLifecycleState.DELETED)


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (start, target)
        for start, targets in LEGAL_EDGES.items()
        for target in targets
    ],
)
def test_all_sixteen_legal_transition_edges(tmp_path, start, target):
    _, service = _service(tmp_path)
    record = _reach_state(service, start)
    revision = _revision() if target is SourceLifecycleState.READY else None
    updated = _transition(service, record, target, revision=revision)
    assert updated.state is target
    assert updated.record_version == record.record_version + 1


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (start, target)
        for start in SourceLifecycleState
        for target in SourceLifecycleState
        if target not in LEGAL_EDGES[start]
    ],
)
def test_all_other_transition_edges_are_rejected(tmp_path, start, target):
    _, service = _service(tmp_path)
    record = _reach_state(service, start)
    revision = _revision() if target is SourceLifecycleState.READY else None
    with pytest.raises(SourceLifecycleException) as exc:
        _transition(service, record, target, revision=revision)
    assert exc.value.code is SourceLifecycleErrorCode.SOURCE_INVALID_TRANSITION


def test_ready_atomically_publishes_immutable_revision(tmp_path):
    repository, service = _service(tmp_path)
    record = _transition(service, _register(service), SourceLifecycleState.SYNCING)
    ready = _transition(service, record, SourceLifecycleState.READY, revision=_revision())

    assert ready.published_revision_no == 1
    assert ready.published_generation == "generation-1"
    revisions = repository.list_revisions(ready.source_id)
    assert len(revisions) == 1
    assert revisions[0].build_result == "SUCCESS"

    syncing = _transition(service, ready, SourceLifecycleState.SYNCING)
    degraded = _transition(service, syncing, SourceLifecycleState.DEGRADED)
    assert degraded.published_revision_no == 1
    assert degraded.published_generation == "generation-1"
    assert repository.list_revisions(ready.source_id) == revisions


def test_ready_requires_revision_and_other_transitions_reject_one(tmp_path):
    _, service = _service(tmp_path)
    syncing = _transition(service, _register(service), SourceLifecycleState.SYNCING)
    with pytest.raises(SourceLifecycleException) as missing:
        _transition(service, syncing, SourceLifecycleState.READY)
    assert missing.value.code is SourceLifecycleErrorCode.SOURCE_INVALID_TRANSITION

    with pytest.raises(SourceLifecycleException) as unexpected:
        _transition(service, syncing, SourceLifecycleState.DEGRADED, revision=_revision())
    assert unexpected.value.code is SourceLifecycleErrorCode.SOURCE_INVALID_TRANSITION


def test_failed_or_unknown_build_result_cannot_publish_ready(tmp_path):
    repository, service = _service(tmp_path)
    syncing = _transition(service, _register(service), SourceLifecycleState.SYNCING)
    failed = SourceRevisionDraft(
        build_result="FAILED",
        source_fingerprint=DIGEST_A,
        manifest_digest=DIGEST_B,
        parser_schema_version="parser-v1",
        chunk_schema_version="chunk-v1",
        generation="failed-generation",
        document_count=2,
        chunk_count=5,
        raw_bytes=128,
    )

    with pytest.raises(SourceLifecycleException) as exc:
        _transition(service, syncing, SourceLifecycleState.READY, revision=failed)
    assert exc.value.code is SourceLifecycleErrorCode.SOURCE_INVALID_TRANSITION
    assert repository.get_source(SOURCE_ID) == syncing
    assert repository.list_revisions(SOURCE_ID) == ()

    with pytest.raises(ValueError, match="build_result is unsupported"):
        SourceRevisionDraft(
            build_result="UNKNOWN",
            source_fingerprint=DIGEST_A,
            manifest_digest=DIGEST_B,
            parser_schema_version="parser-v1",
            chunk_schema_version="chunk-v1",
            generation="unknown-generation",
            document_count=0,
            chunk_count=0,
            raw_bytes=0,
        )


def test_expected_version_conflict_preserves_entity_and_audit(tmp_path):
    repository, service = _service(tmp_path)
    record = _register(service)
    updated = _transition(service, record, SourceLifecycleState.DISABLED)

    with pytest.raises(SourceLifecycleException) as exc:
        service.transition_source(
            principal_id=PRINCIPAL,
            source_id=record.source_id,
            expected_version=record.record_version,
            target_state=SourceLifecycleState.DELETE_PENDING,
            actor_type=SourceActorType.USER,
            correlation_id=CORRELATION_ID,
        )
    assert exc.value.code is SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT
    assert repository.get_source(record.source_id) == updated
    assert len(repository.list_audit_events(record.source_id)) == 2


def test_one_hundred_independent_registry_pairs_enforce_sqlite_cas(tmp_path):
    successes = 0
    conflicts = 0
    lock_errors: list[BaseException] = []

    for pair in range(100):
        path = tmp_path / f"cas-{pair}.sqlite3"
        source_id = f"user-01890f52-47e7-7abc-8def-{pair:012x}"
        seed_repository = SqliteSourceRegistry(path)
        seed_service = SourceLifecycleService(
            seed_repository,
            source_id_factory=lambda source_id=source_id: source_id,
        )
        record = _transition(
            seed_service,
            _register(seed_service),
            SourceLifecycleState.SYNCING,
        )
        services = tuple(
            SourceLifecycleService(SqliteSourceRegistry(path))
            for _ in range(2)
        )

        def write(index: int) -> str:
            try:
                services[index].transition_source(
                    principal_id=PRINCIPAL,
                    source_id=source_id,
                    expected_version=record.record_version,
                    target_state=SourceLifecycleState.DISABLED,
                    actor_type=SourceActorType.SERVICE,
                    correlation_id=f"cas-{pair}-{index}",
                )
            except SourceLifecycleException as exc:
                return exc.code.value
            except BaseException as exc:  # pragma: no cover - diagnostic guard
                lock_errors.append(exc)
                return type(exc).__name__
            return "SUCCESS"

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = tuple(executor.map(write, range(2)))

        assert sorted(outcomes) == [
            SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT.value,
            "SUCCESS",
        ]
        final_repository = SqliteSourceRegistry(path)
        final = final_repository.get_source(source_id)
        assert final is not None
        assert final.record_version == record.record_version + 1
        assert len(final_repository.list_audit_events(source_id)) == 3
        assert final_repository.list_revisions(source_id) == ()
        successes += outcomes.count("SUCCESS")
        conflicts += outcomes.count(
            SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT.value
        )

    assert successes == 100
    assert conflicts == 100
    assert lock_errors == []


def test_owner_isolation_uses_non_disclosing_not_found(tmp_path):
    _, service = _service(tmp_path)
    record = _register(service)

    for principal, source_id in (
        (OTHER_PRINCIPAL, record.source_id),
        (PRINCIPAL, SECOND_SOURCE_ID),
    ):
        with pytest.raises(SourceLifecycleException) as exc:
            service.get_source(principal_id=principal, source_id=source_id)
        assert exc.value.code is SourceLifecycleErrorCode.SOURCE_NOT_FOUND
        assert str(exc.value) == "The Source was not found."

    assert service.list_sources(principal_id=OTHER_PRINCIPAL) == ()


def test_delete_pending_and_deleted_are_hidden_but_audit_remains_internal(tmp_path):
    repository, service = _service(tmp_path)
    record = _register(service)
    pending = _transition(service, record, SourceLifecycleState.DELETE_PENDING)

    with pytest.raises(SourceLifecycleException) as pending_read:
        service.get_source(principal_id=PRINCIPAL, source_id=record.source_id)
    assert pending_read.value.code is SourceLifecycleErrorCode.SOURCE_NOT_FOUND

    deleted = _transition(service, pending, SourceLifecycleState.DELETED)
    assert repository.get_source(record.source_id) == deleted
    assert service.list_sources(principal_id=PRINCIPAL) == ()
    with pytest.raises(SourceLifecycleException) as audit_read:
        service.list_audit_events(principal_id=PRINCIPAL, source_id=record.source_id)
    assert audit_read.value.code is SourceLifecycleErrorCode.SOURCE_NOT_FOUND
    assert len(repository.list_audit_events(record.source_id)) == 3


def test_restart_round_trip_preserves_source_revision_and_audit(tmp_path):
    path = tmp_path / "registry.sqlite3"
    repository = SqliteSourceRegistry(path)
    service = SourceLifecycleService(repository, source_id_factory=lambda: SOURCE_ID)
    syncing = _transition(service, _register(service), SourceLifecycleState.SYNCING)
    ready = _transition(service, syncing, SourceLifecycleState.READY, revision=_revision())

    reopened = SqliteSourceRegistry(path)
    assert reopened.schema_version() == 1
    assert reopened.get_source(SOURCE_ID) == ready
    assert len(reopened.list_revisions(SOURCE_ID)) == 1
    assert len(reopened.list_audit_events(SOURCE_ID)) == 3


def test_sync_run_and_lifecycle_error_persistence_survives_restart(tmp_path):
    path = tmp_path / "registry.sqlite3"
    repository = SqliteSourceRegistry(path)
    _, service = repository, SourceLifecycleService(
        repository, source_id_factory=lambda: SOURCE_ID
    )
    _register(service)
    now = datetime.now(timezone.utc)
    run = SyncRun(
        run_id=generate_uuid7(timestamp_ms=1_700_000_000_001),
        request_id=generate_uuid7(timestamp_ms=1_700_000_000_002),
        source_id=SOURCE_ID,
        requested_strategy="FULL",
        status="FAILED",
        started_at=now,
        updated_at=now,
        finished_at=now,
        result_code="BUILD_FAILED",
    )
    error = LifecycleError(
        error_id=generate_uuid7(timestamp_ms=1_700_000_000_003),
        source_id=SOURCE_ID,
        entity_id=run.run_id,
        stage="BUILD",
        error_code="BUILD_FAILED",
        first_seen_at=now,
        last_seen_at=now,
        count=1,
    )
    with repository.transaction() as transaction:
        transaction.insert_sync_run(run)
        transaction.insert_lifecycle_error(error)

    reopened = SqliteSourceRegistry(path)
    assert reopened.list_sync_runs(SOURCE_ID) == (run,)
    assert reopened.list_lifecycle_errors(SOURCE_ID) == (error,)


def test_twenty_golden_records_per_lifecycle_type_round_trip(tmp_path):
    path = tmp_path / "golden.sqlite3"
    repository = SqliteSourceRegistry(path)
    expected_sources: list[SourceRecord] = []
    expected_revisions: dict[str, SourceRevision] = {}
    expected_runs: dict[str, SyncRun] = {}
    expected_errors: dict[str, LifecycleError] = {}

    for index in range(20):
        source_id = f"user-01890f52-47e7-7abc-8def-{index:012x}"
        service = SourceLifecycleService(
            repository,
            source_id_factory=lambda source_id=source_id: source_id,
        )
        principal = f"principal-{index}"
        registered = service.register_source(
            owner_principal_id=principal,
            expected_version=0,
            actor_type=SourceActorType.USER,
            correlation_id=f"golden-register-{index}",
        )
        syncing = service.transition_source(
            principal_id=principal,
            source_id=source_id,
            expected_version=registered.record_version,
            target_state=SourceLifecycleState.SYNCING,
            actor_type=SourceActorType.SERVICE,
            correlation_id=f"golden-sync-{index}",
        )
        ready = service.transition_source(
            principal_id=principal,
            source_id=source_id,
            expected_version=syncing.record_version,
            target_state=SourceLifecycleState.READY,
            actor_type=SourceActorType.SERVICE,
            correlation_id=f"golden-ready-{index}",
            revision=SourceRevisionDraft(
                build_result="SUCCESS",
                source_fingerprint=f"{index + 1:064x}",
                manifest_digest=f"{index + 101:064x}",
                parser_schema_version="parser-v1",
                chunk_schema_version="chunk-v1",
                generation=f"generation-{index}",
                document_count=index,
                chunk_count=index * 2,
                raw_bytes=index * 10,
            ),
        )
        now = datetime(2026, 9, 1, 0, index, tzinfo=timezone.utc)
        run = SyncRun(
            run_id=generate_uuid7(timestamp_ms=1_700_000_100_000 + index * 3),
            request_id=generate_uuid7(timestamp_ms=1_700_000_100_001 + index * 3),
            source_id=source_id,
            requested_strategy="FULL",
            status="SUCCESS",
            started_at=now,
            updated_at=now,
            finished_at=now,
            input_revision_no=1,
            candidate_generation=f"generation-{index}",
            result_code="SUCCESS",
            document_count=index,
            chunk_count=index * 2,
            raw_bytes=index * 10,
        )
        error = LifecycleError(
            error_id=generate_uuid7(timestamp_ms=1_700_000_100_002 + index * 3),
            source_id=source_id,
            entity_id=run.run_id,
            stage="BUILD",
            error_code="RETRYABLE_BUILD_ERROR",
            first_seen_at=now,
            last_seen_at=now,
            count=index + 1,
        )
        with repository.transaction() as transaction:
            transaction.insert_sync_run(run)
            transaction.insert_lifecycle_error(error)

        expected_sources.append(ready)
        expected_revisions[source_id] = repository.list_revisions(source_id)[0]
        expected_runs[source_id] = run
        expected_errors[source_id] = error

    reopened = SqliteSourceRegistry(path)
    actual_sources = tuple(
        source
        for index in range(20)
        for source in reopened.list_sources(f"principal-{index}")
    )
    assert actual_sources == tuple(expected_sources)
    assert len(actual_sources) == 20

    canonical_records: list[str] = []
    for source in actual_sources:
        revisions = reopened.list_revisions(source.source_id)
        runs = reopened.list_sync_runs(source.source_id)
        errors = reopened.list_lifecycle_errors(source.source_id)
        audits = reopened.list_audit_events(source.source_id)
        assert revisions == (expected_revisions[source.source_id],)
        assert runs == (expected_runs[source.source_id],)
        assert errors == (expected_errors[source.source_id],)
        assert len(audits) == 3
        canonical_records.extend(
            _canonical_json(record)
            for record in (source, revisions[0], runs[0], errors[0], audits[-1])
        )

    assert len(canonical_records) == 100
    assert all(
        json.dumps(
            json.loads(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        == payload
        for payload in canonical_records
    )


def test_revision_and_audit_tables_are_database_immutable(tmp_path):
    repository, service = _service(tmp_path)
    syncing = _transition(service, _register(service), SourceLifecycleState.SYNCING)
    _transition(service, syncing, SourceLifecycleState.READY, revision=_revision())

    with sqlite3.connect(repository.db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE source_revisions SET build_result = 'FAILED' WHERE source_id = ?",
                (SOURCE_ID,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM audit_events WHERE source_id = ?", (SOURCE_ID,)
            )


def test_named_fault_checkpoints_roll_back_without_partial_commits(tmp_path):
    attempts = 0
    for checkpoint in ("after_entity_write", "before_audit_write", "before_commit"):
        for repetition in range(20):
            path = tmp_path / f"{checkpoint}-{repetition}.sqlite3"
            repository = SqliteSourceRegistry(path)
            service = SourceLifecycleService(
                repository,
                source_id_factory=lambda: SOURCE_ID,
            )
            record = _register(service)

            def inject(active: str, *, expected: str = checkpoint) -> None:
                if active == expected:
                    raise RuntimeError("injected lifecycle transaction failure")

            repository._fault_injector = inject
            with pytest.raises(
                RuntimeError,
                match="injected lifecycle transaction failure",
            ):
                _transition(service, record, SourceLifecycleState.DISABLED)
            repository._fault_injector = None

            reopened = SqliteSourceRegistry(path)
            assert reopened.get_source(SOURCE_ID) == record
            assert len(reopened.list_audit_events(SOURCE_ID)) == 1
            assert reopened.list_revisions(SOURCE_ID) == ()
            attempts += 1

    assert attempts == 60


def test_future_or_partial_schema_fails_closed(tmp_path):
    future = tmp_path / "future.sqlite3"
    repository = SqliteSourceRegistry(future)
    assert repository.schema_version() == 1
    with sqlite3.connect(future) as connection:
        connection.execute("UPDATE source_registry_meta SET schema_version = 2")

    with pytest.raises(SourceLifecycleException) as exc:
        SqliteSourceRegistry(future)
    assert exc.value.code is SourceLifecycleErrorCode.SOURCE_SCHEMA_UNSUPPORTED

    partial = tmp_path / "partial.sqlite3"
    with sqlite3.connect(partial) as connection:
        connection.execute("CREATE TABLE unrelated(value TEXT)")
    with pytest.raises(SourceLifecycleException) as partial_exc:
        SqliteSourceRegistry(partial)
    assert partial_exc.value.code is SourceLifecycleErrorCode.SOURCE_SCHEMA_UNSUPPORTED


def test_named_but_malformed_schema_fails_closed(tmp_path):
    mutations = {
        "missing-column": (
            "ALTER TABLE sync_runs DROP COLUMN result_code",
            None,
        ),
        "altered-constraint": (
            "PRAGMA writable_schema = ON",
            (
                "UPDATE sqlite_master SET sql = replace(sql, "
                "'CHECK(record_version >= 1)', 'CHECK(record_version >= 0)') "
                "WHERE type = 'table' AND name = 'source_records'"
            ),
        ),
        "missing-index": (
            "DROP INDEX source_records_owner_idx",
            None,
        ),
        "missing-trigger": (
            "DROP TRIGGER audit_events_no_delete",
            None,
        ),
        "invalid-meta-singleton": (
            "PRAGMA ignore_check_constraints = ON",
            (
                "INSERT INTO source_registry_meta(singleton, schema_family, "
                "schema_version, created_at, updated_at) "
                "SELECT 2, schema_family, schema_version, created_at, updated_at "
                "FROM source_registry_meta WHERE singleton = 1"
            ),
        ),
    }

    for name, statements in mutations.items():
        malformed = tmp_path / f"{name}.sqlite3"
        SqliteSourceRegistry(malformed)
        with sqlite3.connect(malformed) as connection:
            for statement in statements:
                if statement is not None:
                    connection.execute(statement)

        with pytest.raises(SourceLifecycleException) as exc:
            SqliteSourceRegistry(malformed)
        assert (
            exc.value.code
            is SourceLifecycleErrorCode.SOURCE_SCHEMA_UNSUPPORTED
        )


def test_foreign_key_corruption_fails_closed(tmp_path):
    malformed = tmp_path / "foreign-key-corruption.sqlite3"
    SqliteSourceRegistry(malformed)
    with sqlite3.connect(malformed) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            INSERT INTO lifecycle_errors(
                error_id, schema_version, source_id, entity_id, stage,
                error_code, first_seen_at, last_seen_at, count
            ) VALUES (?, 1, ?, 'entity', 'BUILD', 'FAILED', ?, ?, 1)
            """,
            (
                generate_uuid7(timestamp_ms=1_700_000_200_000),
                SOURCE_ID,
                "2026-09-01T00:00:00Z",
                "2026-09-01T00:00:00Z",
            ),
        )

    with pytest.raises(SourceLifecycleException) as exc:
        SqliteSourceRegistry(malformed)
    assert exc.value.code is SourceLifecycleErrorCode.SOURCE_SCHEMA_UNSUPPORTED


def test_audit_failure_rolls_back_entity_update(tmp_path, monkeypatch):
    repository, service = _service(tmp_path)
    record = _register(service)

    def fail_audit(_self, _event):
        raise RuntimeError("injected audit failure")

    from app import source_registry as module

    monkeypatch.setattr(module.SourceRegistryTransaction, "insert_audit", fail_audit)
    with pytest.raises(RuntimeError, match="injected audit failure"):
        _transition(service, record, SourceLifecycleState.DISABLED)

    assert repository.get_source(record.source_id) == record
    assert len(repository.list_audit_events(record.source_id)) == 1


def test_revision_failure_rolls_back_ready_transition(tmp_path):
    repository, service = _service(tmp_path)
    syncing = _transition(service, _register(service), SourceLifecycleState.SYNCING)
    duplicate = _revision("generation-1")
    ready = _transition(service, syncing, SourceLifecycleState.READY, revision=duplicate)
    syncing_again = _transition(service, ready, SourceLifecycleState.SYNCING)

    with pytest.raises(sqlite3.IntegrityError):
        _transition(service, syncing_again, SourceLifecycleState.READY, revision=duplicate)

    assert repository.get_source(SOURCE_ID) == syncing_again
    assert len(repository.list_revisions(SOURCE_ID)) == 1


def test_registry_records_exclude_bodies_credentials_and_host_paths(tmp_path):
    repository, service = _service(tmp_path)
    record = _register(service)
    _transition(service, record, SourceLifecycleState.DISABLED)

    with sqlite3.connect(repository.db_path) as connection:
        payload = "\n".join(
            str(value)
            for table in ("source_records", "source_revisions", "audit_events")
            for row in connection.execute(f"SELECT * FROM {table}")
            for value in row
            if value is not None
        )
    assert "super-secret" not in payload
    assert "document body" not in payload
    assert "C:\\Users\\" not in payload
    assert "/home/" not in payload
    assert PRINCIPAL in payload


def test_privacy_canaries_do_not_persist_or_escape_stable_errors(tmp_path):
    canaries = (
        "PRIVATE_DOCUMENT_BODY_8f31",
        "SECRET_TOKEN_8f31",
        r"C:\\Users\\private\\course.pdf",
        "/home/private/course.pdf",
        r"\\server\\private\\course.pdf",
    )

    for index, canary in enumerate(canaries):
        path = tmp_path / f"privacy-{index}.sqlite3"
        repository = SqliteSourceRegistry(path)
        service = SourceLifecycleService(
            repository,
            source_id_factory=lambda: SOURCE_ID,
        )
        record = _register(service)

        with pytest.raises(SourceLifecycleException) as rejected:
            service.transition_source(
                principal_id=PRINCIPAL,
                source_id=record.source_id,
                expected_version=record.record_version,
                target_state=SourceLifecycleState.DISABLED,
                actor_type=SourceActorType.SERVICE,
                correlation_id=f"invalid/{canary}",
            )
        assert (
            rejected.value.code
            is SourceLifecycleErrorCode.SOURCE_NOT_FOUND
        )
        assert canary not in str(rejected.value)
        assert canary not in rejected.value.message

        repository._fault_injector = lambda _: (_ for _ in ()).throw(
            RuntimeError("internal lifecycle failure")
        )
        with pytest.raises(RuntimeError) as internal:
            _transition(service, record, SourceLifecycleState.DISABLED)
        repository._fault_injector = None
        assert canary not in str(internal.value)

        with sqlite3.connect(path) as connection:
            payload = "\n".join(
                str(value)
                for table in (
                    "source_records",
                    "source_revisions",
                    "sync_runs",
                    "lifecycle_errors",
                    "audit_events",
                )
                for row in connection.execute(f"SELECT * FROM {table}")
                for value in row
                if value is not None
            )
        assert canary not in payload

        with sqlite3.connect(path) as connection:
            connection.execute(
                "UPDATE source_registry_meta SET schema_version = 2"
            )
        with pytest.raises(SourceLifecycleException) as schema:
            SqliteSourceRegistry(path)
        assert (
            schema.value.code
            is SourceLifecycleErrorCode.SOURCE_SCHEMA_UNSUPPORTED
        )
        assert canary not in str(schema.value)


def test_m7_rejects_reserved_and_noncanonical_source_ids(tmp_path):
    repository, service = _service(tmp_path)
    for source_id in (
        "knowledge-pack",
        "crawler-candidates",
        "user-notes",
        "user-01890f52-47e7-7abc-8def-0123456789AB",
        "user-01890f52-47e7-7abc-cdef-0123456789ab",
        "user-01890f52-47e7-6abc-8def-0123456789ab",
        "user-01890f52-47e7-7abc-8def-0123456789ab/../secret",
    ):
        with pytest.raises(SourceLifecycleException) as exc:
            _register(service, source_id=source_id)
        assert exc.value.code is SourceLifecycleErrorCode.SOURCE_ISOLATION_INVALID_REQUEST

    assert repository.list_sources(PRINCIPAL) == ()


def test_missing_principal_fails_with_auth_required(tmp_path):
    _, service = _service(tmp_path)
    record = _register(service)

    with pytest.raises(SourceLifecycleException) as exc:
        service.get_source(principal_id="", source_id=record.source_id)
    assert exc.value.code is SourceLifecycleErrorCode.SOURCE_AUTH_REQUIRED


def test_registration_enforces_ten_non_deleted_sources_per_principal(tmp_path):
    repository = SqliteSourceRegistry(tmp_path / "registry.sqlite3")
    ids = [
        f"user-{generate_uuid7(timestamp_ms=1_700_000_000_000 + offset)}"
        for offset in range(11)
    ]
    service = SourceLifecycleService(repository)
    for source_id in ids[:10]:
        _register(service, source_id=source_id)

    with pytest.raises(SourceLifecycleException) as exc:
        _register(service, source_id=ids[10])
    assert exc.value.code is SourceLifecycleErrorCode.SOURCE_COUNT_LIMIT_EXCEEDED

    deleted = service.transition_source(
        principal_id=PRINCIPAL,
        source_id=ids[0],
        expected_version=1,
        target_state=SourceLifecycleState.DELETE_PENDING,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION_ID,
    )
    service.transition_source(
        principal_id=PRINCIPAL,
        source_id=ids[0],
        expected_version=deleted.record_version,
        target_state=SourceLifecycleState.DELETED,
        actor_type=SourceActorType.SERVICE,
        correlation_id=CORRELATION_ID,
    )
    assert _register(service, source_id=ids[10]).record_version == 1


def test_unsupported_m7_schema_does_not_break_legacy_read_only_runtime(
    tmp_path,
    test_client,
):
    malformed = tmp_path / "unsupported-m7.sqlite3"
    with sqlite3.connect(malformed) as connection:
        connection.execute(
            "CREATE TABLE source_registry_meta(schema_family TEXT, schema_version INTEGER)"
        )
        connection.execute(
            "INSERT INTO source_registry_meta VALUES (?, ?)",
            ("sa.source.lifecycle.future", 999),
        )

    with pytest.raises(SourceLifecycleException) as exc:
        SqliteSourceRegistry(malformed)
    assert exc.value.code is SourceLifecycleErrorCode.SOURCE_SCHEMA_UNSUPPORTED

    health = test_client.get("/health")
    search = test_client.post(
        "/api/v1/search",
        json={"question": "进程调度", "top_k": 1},
    )
    assert health.status_code == 200
    assert health.json()["status"] == "UP"
    assert search.status_code == 200
    assert search.json()["results"]
