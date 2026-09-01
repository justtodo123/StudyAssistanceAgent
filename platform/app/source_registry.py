"""M7-1 Source Registry lifecycle control plane.

The registry is intentionally separate from learning-state and retrieval storage.
Only ``SourceLifecycleService`` issues lifecycle writes; the SQLite repository
provides the transaction-scoped persistence primitives used by that service.
"""

from __future__ import annotations

import re
import secrets
import sqlite3
import threading
import time
import uuid
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Callable, Iterator, Protocol, runtime_checkable

LIFECYCLE_SCHEMA_FAMILY = "sa.source.lifecycle.v1"
LIFECYCLE_SCHEMA_VERSION = 1
ISOLATION_POLICY_VERSION = "sa.source.isolation.v1"
MAX_SOURCES_PER_PRINCIPAL = 10
SUCCESSFUL_BUILD_RESULT = "SUCCESS"
_BUILD_RESULTS = frozenset({SUCCESSFUL_BUILD_RESULT, "FAILED"})

_USER_SOURCE_RE = re.compile(
    r"^user-[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_SAFE_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,127}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:([\\/]|$)")


class SourceLifecycleState(StrEnum):
    REGISTERED = "REGISTERED"
    SYNCING = "SYNCING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    DISABLED = "DISABLED"
    DELETE_PENDING = "DELETE_PENDING"
    DELETED = "DELETED"


class SourceActorType(StrEnum):
    USER = "USER"
    SERVICE = "SERVICE"
    ADMIN = "ADMIN"


class SourceLifecycleErrorCode(StrEnum):
    SOURCE_AUTH_REQUIRED = "SOURCE_AUTH_REQUIRED"
    SOURCE_COUNT_LIMIT_EXCEEDED = "SOURCE_COUNT_LIMIT_EXCEEDED"
    SOURCE_ID_CONFLICT = "SOURCE_ID_CONFLICT"
    SOURCE_INVALID_TRANSITION = "SOURCE_INVALID_TRANSITION"
    SOURCE_ISOLATION_INVALID_REQUEST = "SOURCE_ISOLATION_INVALID_REQUEST"
    SOURCE_ISOLATION_UNAVAILABLE = "SOURCE_ISOLATION_UNAVAILABLE"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    SOURCE_SCHEMA_UNSUPPORTED = "SOURCE_SCHEMA_UNSUPPORTED"
    SOURCE_VERSION_CONFLICT = "SOURCE_VERSION_CONFLICT"


class SourceLifecycleException(RuntimeError):
    """Stable, content-free lifecycle failure."""

    def __init__(self, code: SourceLifecycleErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SourceSchemaUnsupportedError(SourceLifecycleException):
    def __init__(self) -> None:
        super().__init__(
            SourceLifecycleErrorCode.SOURCE_SCHEMA_UNSUPPORTED,
            "The Source Registry schema is unsupported.",
        )


_ALLOWED_TRANSITIONS: dict[SourceLifecycleState, frozenset[SourceLifecycleState]] = {
    SourceLifecycleState.REGISTERED: frozenset(
        {
            SourceLifecycleState.SYNCING,
            SourceLifecycleState.DISABLED,
            SourceLifecycleState.DELETE_PENDING,
        }
    ),
    SourceLifecycleState.SYNCING: frozenset(
        {
            SourceLifecycleState.READY,
            SourceLifecycleState.DEGRADED,
            SourceLifecycleState.DISABLED,
            SourceLifecycleState.DELETE_PENDING,
        }
    ),
    SourceLifecycleState.READY: frozenset(
        {
            SourceLifecycleState.SYNCING,
            SourceLifecycleState.DISABLED,
            SourceLifecycleState.DELETE_PENDING,
        }
    ),
    SourceLifecycleState.DEGRADED: frozenset(
        {
            SourceLifecycleState.SYNCING,
            SourceLifecycleState.DISABLED,
            SourceLifecycleState.DELETE_PENDING,
        }
    ),
    SourceLifecycleState.DISABLED: frozenset(
        {
            SourceLifecycleState.SYNCING,
            SourceLifecycleState.DELETE_PENDING,
        }
    ),
    SourceLifecycleState.DELETE_PENDING: frozenset({SourceLifecycleState.DELETED}),
    SourceLifecycleState.DELETED: frozenset(),
}


def generate_uuid7(*, timestamp_ms: int | None = None) -> str:
    """Generate a canonical lowercase UUIDv7 without a third-party dependency."""
    milliseconds = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    if not 0 <= milliseconds < 1 << 48:
        raise ValueError("timestamp_ms is outside the UUIDv7 range")
    random_a = secrets.randbits(12)
    random_b = secrets.randbits(62)
    value = (
        (milliseconds << 80)
        | (0x7 << 76)
        | (random_a << 64)
        | (0b10 << 62)
        | random_b
    )
    return str(uuid.UUID(int=value))


def generate_user_source_id() -> str:
    return f"user-{generate_uuid7()}"


def validate_uuid7(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or value != value.lower():
        raise ValueError(f"{field_name} must be a canonical lowercase UUIDv7")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{field_name} must be a canonical lowercase UUIDv7") from exc
    if str(parsed) != value or parsed.version != 7 or parsed.variant != uuid.RFC_4122:
        raise ValueError(f"{field_name} must be a canonical lowercase UUIDv7")
    return value


def validate_user_source_id(value: str) -> str:
    if not isinstance(value, str) or _USER_SOURCE_RE.fullmatch(value) is None:
        raise ValueError("source_id must use the canonical user UUIDv7 namespace")
    validate_uuid7(value[5:], field_name="source_id")
    return value


def _validate_opaque_id(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or _SAFE_OPAQUE_ID_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a canonical opaque identifier")
    if value.startswith(("/", "\\", "//")) or _WINDOWS_DRIVE_RE.match(value):
        raise ValueError(f"{field_name} must not be a host path")
    return value


def _validate_digest(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_utc(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
    return value


def _timestamp(value: datetime) -> str:
    return _validate_utc(value, field_name="timestamp").isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SourceSchemaUnsupportedError() from exc
    try:
        return _validate_utc(parsed, field_name="timestamp")
    except ValueError as exc:
        raise SourceSchemaUnsupportedError() from exc


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    owner_principal_id: str
    state: SourceLifecycleState
    record_version: int
    created_at: datetime
    updated_at: datetime
    published_revision_no: int | None = None
    published_generation: str | None = None
    source_type: str = "user_registered"
    schema_version: int = LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        validate_user_source_id(self.source_id)
        _validate_opaque_id(self.owner_principal_id, field_name="owner_principal_id")
        if self.schema_version != LIFECYCLE_SCHEMA_VERSION:
            raise ValueError("unsupported SourceRecord schema_version")
        if self.source_type != "user_registered":
            raise ValueError("M7 v1 SourceRecord source_type must be user_registered")
        if not isinstance(self.state, SourceLifecycleState):
            raise ValueError("state must be a SourceLifecycleState")
        if not isinstance(self.record_version, int) or self.record_version < 1:
            raise ValueError("record_version must be a positive integer")
        _validate_utc(self.created_at, field_name="created_at")
        _validate_utc(self.updated_at, field_name="updated_at")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if (self.published_revision_no is None) != (self.published_generation is None):
            raise ValueError("published revision and generation must be set together")
        if self.published_revision_no is not None and self.published_revision_no < 1:
            raise ValueError("published_revision_no must be positive")
        if self.published_generation is not None:
            _validate_opaque_id(self.published_generation, field_name="published_generation")


@dataclass(frozen=True, slots=True)
class SourceRevision:
    source_id: str
    revision_no: int
    build_result: str
    source_fingerprint: str
    manifest_digest: str
    parser_schema_version: str
    chunk_schema_version: str
    generation: str
    document_count: int
    chunk_count: int
    raw_bytes: int
    created_at: datetime
    schema_version: int = LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        validate_user_source_id(self.source_id)
        if (
            self.schema_version != LIFECYCLE_SCHEMA_VERSION
            or not isinstance(self.revision_no, int)
            or isinstance(self.revision_no, bool)
            or self.revision_no < 1
        ):
            raise ValueError("invalid SourceRevision version")
        if self.build_result not in _BUILD_RESULTS:
            raise ValueError("build_result is unsupported")
        _validate_digest(self.source_fingerprint, field_name="source_fingerprint")
        _validate_digest(self.manifest_digest, field_name="manifest_digest")
        for name in ("parser_schema_version", "chunk_schema_version", "generation"):
            _validate_opaque_id(getattr(self, name), field_name=name)
        for name in ("document_count", "chunk_count", "raw_bytes"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        _validate_utc(self.created_at, field_name="created_at")


@dataclass(frozen=True, slots=True)
class SourceRevisionDraft:
    build_result: str
    source_fingerprint: str
    manifest_digest: str
    parser_schema_version: str
    chunk_schema_version: str
    generation: str
    document_count: int
    chunk_count: int
    raw_bytes: int

    def __post_init__(self) -> None:
        if self.build_result not in _BUILD_RESULTS:
            raise ValueError("build_result is unsupported")
        _validate_digest(self.source_fingerprint, field_name="source_fingerprint")
        _validate_digest(self.manifest_digest, field_name="manifest_digest")
        for name in ("parser_schema_version", "chunk_schema_version", "generation"):
            _validate_opaque_id(getattr(self, name), field_name=name)
        for name in ("document_count", "chunk_count", "raw_bytes"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class SyncRun:
    run_id: str
    request_id: str
    source_id: str
    requested_strategy: str
    status: str
    started_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    input_revision_no: int | None = None
    candidate_generation: str | None = None
    result_code: str | None = None
    document_count: int = 0
    chunk_count: int = 0
    raw_bytes: int = 0
    schema_version: int = LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        validate_uuid7(self.run_id, field_name="run_id")
        validate_uuid7(self.request_id, field_name="request_id")
        validate_user_source_id(self.source_id)
        if self.schema_version != LIFECYCLE_SCHEMA_VERSION:
            raise ValueError("unsupported SyncRun schema_version")
        if self.requested_strategy not in {"FULL", "INCREMENTAL"}:
            raise ValueError("requested_strategy is unsupported")
        _validate_opaque_id(self.status, field_name="status")
        _validate_utc(self.started_at, field_name="started_at")
        _validate_utc(self.updated_at, field_name="updated_at")
        if self.finished_at is not None:
            _validate_utc(self.finished_at, field_name="finished_at")
        if self.input_revision_no is not None and (
            not isinstance(self.input_revision_no, int)
            or isinstance(self.input_revision_no, bool)
            or self.input_revision_no < 1
        ):
            raise ValueError("input_revision_no must be positive")
        if self.candidate_generation is not None:
            _validate_opaque_id(self.candidate_generation, field_name="candidate_generation")
        if self.result_code is not None:
            _validate_opaque_id(self.result_code, field_name="result_code")
        for name in ("document_count", "chunk_count", "raw_bytes"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True, slots=True)
class LifecycleError:
    error_id: str
    source_id: str
    entity_id: str
    stage: str
    error_code: str
    first_seen_at: datetime
    last_seen_at: datetime
    count: int
    schema_version: int = LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        validate_uuid7(self.error_id, field_name="error_id")
        validate_user_source_id(self.source_id)
        for name in ("entity_id", "stage", "error_code"):
            _validate_opaque_id(getattr(self, name), field_name=name)
        if (
            self.schema_version != LIFECYCLE_SCHEMA_VERSION
            or not isinstance(self.count, int)
            or isinstance(self.count, bool)
            or self.count < 1
        ):
            raise ValueError("invalid LifecycleError version or count")
        _validate_utc(self.first_seen_at, field_name="first_seen_at")
        _validate_utc(self.last_seen_at, field_name="last_seen_at")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    source_id: str
    actor_type: SourceActorType
    action: str
    before_state: SourceLifecycleState | None
    after_state: SourceLifecycleState
    entity_id: str
    correlation_id: str
    result: str
    created_at: datetime
    schema_version: int = LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        validate_uuid7(self.event_id, field_name="event_id")
        validate_user_source_id(self.source_id)
        if not isinstance(self.actor_type, SourceActorType):
            raise ValueError("actor_type must be a SourceActorType")
        for name in ("action", "entity_id", "correlation_id", "result"):
            _validate_opaque_id(getattr(self, name), field_name=name)
        if self.before_state is not None and not isinstance(
            self.before_state, SourceLifecycleState
        ):
            raise ValueError("before_state must be a SourceLifecycleState")
        if not isinstance(self.after_state, SourceLifecycleState):
            raise ValueError("after_state must be a SourceLifecycleState")
        if self.schema_version != LIFECYCLE_SCHEMA_VERSION:
            raise ValueError("unsupported AuditEvent schema_version")
        _validate_utc(self.created_at, field_name="created_at")


_SCHEMA = """
CREATE TABLE source_registry_meta (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    schema_family TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE source_records (
    source_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    owner_principal_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    state TEXT NOT NULL,
    record_version INTEGER NOT NULL CHECK(record_version >= 1),
    published_revision_no INTEGER,
    published_generation TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK((published_revision_no IS NULL) = (published_generation IS NULL))
);
CREATE INDEX source_records_owner_idx ON source_records(owner_principal_id, state);

CREATE TABLE source_revisions (
    source_id TEXT NOT NULL REFERENCES source_records(source_id),
    revision_no INTEGER NOT NULL CHECK(revision_no >= 1),
    schema_version INTEGER NOT NULL,
    build_result TEXT NOT NULL,
    source_fingerprint TEXT NOT NULL,
    manifest_digest TEXT NOT NULL,
    parser_schema_version TEXT NOT NULL,
    chunk_schema_version TEXT NOT NULL,
    generation TEXT NOT NULL,
    document_count INTEGER NOT NULL CHECK(document_count >= 0),
    chunk_count INTEGER NOT NULL CHECK(chunk_count >= 0),
    raw_bytes INTEGER NOT NULL CHECK(raw_bytes >= 0),
    created_at TEXT NOT NULL,
    PRIMARY KEY(source_id, revision_no),
    UNIQUE(source_id, generation)
);

CREATE TABLE sync_runs (
    run_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    request_id TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES source_records(source_id),
    requested_strategy TEXT NOT NULL,
    status TEXT NOT NULL,
    input_revision_no INTEGER,
    candidate_generation TEXT,
    result_code TEXT,
    document_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    raw_bytes INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT,
    UNIQUE(source_id, request_id)
);

CREATE TABLE lifecycle_errors (
    error_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    source_id TEXT NOT NULL REFERENCES source_records(source_id),
    entity_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    error_code TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    count INTEGER NOT NULL CHECK(count >= 1)
);

CREATE TABLE audit_events (
    event_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    source_id TEXT NOT NULL REFERENCES source_records(source_id),
    actor_type TEXT NOT NULL,
    action TEXT NOT NULL,
    before_state TEXT,
    after_state TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    result TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX audit_events_source_idx ON audit_events(source_id, created_at, event_id);

CREATE TRIGGER source_revisions_no_update
BEFORE UPDATE ON source_revisions
BEGIN
    SELECT RAISE(ABORT, 'source revisions are immutable');
END;
CREATE TRIGGER source_revisions_no_delete
BEFORE DELETE ON source_revisions
BEGIN
    SELECT RAISE(ABORT, 'source revisions are immutable');
END;
CREATE TRIGGER audit_events_no_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are append-only');
END;
CREATE TRIGGER audit_events_no_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are append-only');
END;
"""


def _normalized_schema_manifest(connection: sqlite3.Connection) -> dict[tuple[str, str], str]:
    rows = connection.execute(
        """
        SELECT type, name, sql FROM sqlite_master
        WHERE type IN ('table', 'index', 'trigger') AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    return {
        (str(row[0]), str(row[1])): " ".join(str(row[2]).split())
        for row in rows
        if row[2] is not None
    }


def _expected_schema_manifest() -> dict[tuple[str, str], str]:
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(_SCHEMA)
        return _normalized_schema_manifest(connection)
    finally:
        connection.close()


@runtime_checkable
class SourceLifecycleTransaction(Protocol):
    """Atomic persistence primitives required by the lifecycle service."""

    def get_source(self, source_id: str) -> SourceRecord | None: ...

    def count_non_deleted_sources(self, owner_principal_id: str) -> int: ...

    def next_revision_no(self, source_id: str) -> int: ...

    def insert_source(self, record: SourceRecord) -> None: ...

    def update_source(self, record: SourceRecord, *, expected_version: int) -> bool: ...

    def insert_revision(self, revision: SourceRevision) -> None: ...

    def insert_sync_run(self, run: SyncRun) -> None: ...

    def insert_lifecycle_error(self, error: LifecycleError) -> None: ...

    def insert_audit(self, event: AuditEvent) -> None: ...

    def _inject_fault(self, checkpoint: str) -> None: ...


@runtime_checkable
class SourceLifecycleRepository(Protocol):
    """M7 lifecycle boundary, distinct from M6a published descriptors."""

    def transaction(self) -> AbstractContextManager[SourceLifecycleTransaction]: ...

    def get_source(self, source_id: str) -> SourceRecord | None: ...

    def list_sources(self, owner_principal_id: str) -> tuple[SourceRecord, ...]: ...

    def list_revisions(self, source_id: str) -> tuple[SourceRevision, ...]: ...

    def list_sync_runs(self, source_id: str) -> tuple[SyncRun, ...]: ...

    def list_lifecycle_errors(self, source_id: str) -> tuple[LifecycleError, ...]: ...

    def list_audit_events(self, source_id: str) -> tuple[AuditEvent, ...]: ...


class SourceRegistryTransaction:
    """Write primitives scoped to one repository transaction."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        self._connection = connection
        self._fault_injector = fault_injector

    def _inject_fault(self, checkpoint: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(checkpoint)

    def get_source(self, source_id: str) -> SourceRecord | None:
        row = self._connection.execute(
            "SELECT * FROM source_records WHERE source_id = ?", (source_id,)
        ).fetchone()
        return _source_from_row(row) if row is not None else None

    def count_non_deleted_sources(self, owner_principal_id: str) -> int:
        row = self._connection.execute(
            """
            SELECT COUNT(*) FROM source_records
            WHERE owner_principal_id = ? AND state != ?
            """,
            (owner_principal_id, SourceLifecycleState.DELETED.value),
        ).fetchone()
        return int(row[0])

    def next_revision_no(self, source_id: str) -> int:
        row = self._connection.execute(
            "SELECT COALESCE(MAX(revision_no), 0) + 1 FROM source_revisions WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        return int(row[0])

    def insert_source(self, record: SourceRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO source_records(
                source_id, schema_version, owner_principal_id, source_type, state,
                record_version, published_revision_no, published_generation,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.source_id,
                record.schema_version,
                record.owner_principal_id,
                record.source_type,
                record.state.value,
                record.record_version,
                record.published_revision_no,
                record.published_generation,
                _timestamp(record.created_at),
                _timestamp(record.updated_at),
            ),
        )

    def update_source(self, record: SourceRecord, *, expected_version: int) -> bool:
        cursor = self._connection.execute(
            """
            UPDATE source_records SET
                state = ?, record_version = ?, published_revision_no = ?,
                published_generation = ?, updated_at = ?
            WHERE source_id = ? AND record_version = ?
            """,
            (
                record.state.value,
                record.record_version,
                record.published_revision_no,
                record.published_generation,
                _timestamp(record.updated_at),
                record.source_id,
                expected_version,
            ),
        )
        return cursor.rowcount == 1

    def insert_revision(self, revision: SourceRevision) -> None:
        self._connection.execute(
            """
            INSERT INTO source_revisions(
                source_id, revision_no, schema_version, build_result,
                source_fingerprint, manifest_digest, parser_schema_version,
                chunk_schema_version, generation, document_count, chunk_count,
                raw_bytes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                revision.source_id,
                revision.revision_no,
                revision.schema_version,
                revision.build_result,
                revision.source_fingerprint,
                revision.manifest_digest,
                revision.parser_schema_version,
                revision.chunk_schema_version,
                revision.generation,
                revision.document_count,
                revision.chunk_count,
                revision.raw_bytes,
                _timestamp(revision.created_at),
            ),
        )

    def insert_sync_run(self, run: SyncRun) -> None:
        self._connection.execute(
            """
            INSERT INTO sync_runs(
                run_id, schema_version, request_id, source_id, requested_strategy,
                status, input_revision_no, candidate_generation, result_code,
                document_count, chunk_count, raw_bytes, started_at, updated_at,
                finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                run.schema_version,
                run.request_id,
                run.source_id,
                run.requested_strategy,
                run.status,
                run.input_revision_no,
                run.candidate_generation,
                run.result_code,
                run.document_count,
                run.chunk_count,
                run.raw_bytes,
                _timestamp(run.started_at),
                _timestamp(run.updated_at),
                None if run.finished_at is None else _timestamp(run.finished_at),
            ),
        )

    def insert_lifecycle_error(self, error: LifecycleError) -> None:
        self._connection.execute(
            """
            INSERT INTO lifecycle_errors(
                error_id, schema_version, source_id, entity_id, stage, error_code,
                first_seen_at, last_seen_at, count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                error.error_id,
                error.schema_version,
                error.source_id,
                error.entity_id,
                error.stage,
                error.error_code,
                _timestamp(error.first_seen_at),
                _timestamp(error.last_seen_at),
                error.count,
            ),
        )

    def insert_audit(self, event: AuditEvent) -> None:
        self._connection.execute(
            """
            INSERT INTO audit_events(
                event_id, schema_version, source_id, actor_type, action,
                before_state, after_state, entity_id, correlation_id, result, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.schema_version,
                event.source_id,
                event.actor_type.value,
                event.action,
                None if event.before_state is None else event.before_state.value,
                event.after_state.value,
                event.entity_id,
                event.correlation_id,
                event.result,
                _timestamp(event.created_at),
            ),
        )


class SqliteSourceRegistry:
    """SQLite persistence boundary for M7 lifecycle records."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path) if str(db_path) != ":memory:" else Path(":memory:")
        self._lock = threading.Lock()
        self._fault_injector: Callable[[str], None] | None = None
        self._memory: sqlite3.Connection | None = None
        if str(db_path) == ":memory:":
            self._memory = sqlite3.connect(":memory:", check_same_thread=False)
            self._configure(self._memory)
        self._initialize_or_validate()

    @contextmanager
    def transaction(self) -> Iterator[SourceRegistryTransaction]:
        with self._lock:
            connection, owned = self._open_connection()
            try:
                connection.execute("BEGIN IMMEDIATE")
                transaction = SourceRegistryTransaction(connection, self._fault_injector)
                yield transaction
                transaction._inject_fault("before_commit")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                if owned:
                    connection.close()

    def get_source(self, source_id: str) -> SourceRecord | None:
        validate_user_source_id(source_id)
        with self._read_connection() as connection:
            row = connection.execute(
                "SELECT * FROM source_records WHERE source_id = ?", (source_id,)
            ).fetchone()
        return _source_from_row(row) if row is not None else None

    def list_sources(self, owner_principal_id: str) -> tuple[SourceRecord, ...]:
        _validate_opaque_id(owner_principal_id, field_name="owner_principal_id")
        with self._read_connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM source_records
                WHERE owner_principal_id = ? AND state NOT IN (?, ?)
                ORDER BY created_at, source_id
                """,
                (
                    owner_principal_id,
                    SourceLifecycleState.DELETE_PENDING.value,
                    SourceLifecycleState.DELETED.value,
                ),
            ).fetchall()
        return tuple(_source_from_row(row) for row in rows)

    def list_revisions(self, source_id: str) -> tuple[SourceRevision, ...]:
        validate_user_source_id(source_id)
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM source_revisions WHERE source_id = ? ORDER BY revision_no",
                (source_id,),
            ).fetchall()
        return tuple(_revision_from_row(row) for row in rows)

    def list_sync_runs(self, source_id: str) -> tuple[SyncRun, ...]:
        validate_user_source_id(source_id)
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM sync_runs WHERE source_id = ? ORDER BY started_at, run_id",
                (source_id,),
            ).fetchall()
        return tuple(_sync_run_from_row(row) for row in rows)

    def list_lifecycle_errors(self, source_id: str) -> tuple[LifecycleError, ...]:
        validate_user_source_id(source_id)
        with self._read_connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM lifecycle_errors
                WHERE source_id = ? ORDER BY first_seen_at, error_id
                """,
                (source_id,),
            ).fetchall()
        return tuple(_lifecycle_error_from_row(row) for row in rows)

    def list_audit_events(self, source_id: str) -> tuple[AuditEvent, ...]:
        validate_user_source_id(source_id)
        with self._read_connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM audit_events
                WHERE source_id = ? ORDER BY created_at, event_id
                """,
                (source_id,),
            ).fetchall()
        return tuple(_audit_from_row(row) for row in rows)

    def schema_version(self) -> int:
        with self._read_connection() as connection:
            row = connection.execute(
                "SELECT schema_family, schema_version FROM source_registry_meta WHERE singleton = 1"
            ).fetchone()
        if row is None or row[0] != LIFECYCLE_SCHEMA_FAMILY:
            raise SourceSchemaUnsupportedError()
        return int(row[1])

    def _initialize_or_validate(self) -> None:
        if self._memory is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection, owned = self._open_connection()
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if not tables:
                now = _timestamp(_utc_now())
                connection.execute("BEGIN IMMEDIATE")
                connection.executescript(_SCHEMA)
                connection.execute(
                    """
                    INSERT INTO source_registry_meta(
                        singleton, schema_family, schema_version, created_at, updated_at
                    ) VALUES (1, ?, ?, ?, ?)
                    """,
                    (LIFECYCLE_SCHEMA_FAMILY, LIFECYCLE_SCHEMA_VERSION, now, now),
                )
                connection.commit()
                return
            if "source_registry_meta" not in tables:
                raise SourceSchemaUnsupportedError()
            row = connection.execute(
                "SELECT schema_family, schema_version FROM source_registry_meta WHERE singleton = 1"
            ).fetchone()
            if (
                row is None
                or row[0] != LIFECYCLE_SCHEMA_FAMILY
                or row[1] != LIFECYCLE_SCHEMA_VERSION
            ):
                raise SourceSchemaUnsupportedError()
            meta_count = connection.execute(
                "SELECT COUNT(*) FROM source_registry_meta"
            ).fetchone()[0]
            if meta_count != 1:
                raise SourceSchemaUnsupportedError()
            if _normalized_schema_manifest(connection) != _expected_schema_manifest():
                raise SourceSchemaUnsupportedError()
            foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_keys:
                raise SourceSchemaUnsupportedError()
        except sqlite3.Error as exc:
            raise SourceSchemaUnsupportedError() from exc
        finally:
            if owned:
                connection.close()

    @contextmanager
    def _read_connection(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            connection, owned = self._open_connection()
            try:
                yield connection
            except sqlite3.Error as exc:
                raise SourceSchemaUnsupportedError() from exc
            finally:
                if owned:
                    connection.close()

    def _open_connection(self) -> tuple[sqlite3.Connection, bool]:
        if self._memory is not None:
            return self._memory, False
        connection = sqlite3.connect(
            str(self.db_path), timeout=30, check_same_thread=False
        )
        self._configure(connection)
        return connection, True

    @staticmethod
    def _configure(connection: sqlite3.Connection) -> None:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")


class SourceLifecycleService:
    """Sole authority for Source Registry lifecycle mutations."""

    def __init__(
        self,
        repository: SourceLifecycleRepository,
        *,
        clock: Callable[[], datetime] = _utc_now,
        id_factory: Callable[[], str] = generate_uuid7,
        source_id_factory: Callable[[], str] = generate_user_source_id,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._id_factory = id_factory
        self._source_id_factory = source_id_factory

    def register_source(
        self,
        *,
        owner_principal_id: str,
        expected_version: int,
        actor_type: SourceActorType,
        correlation_id: str,
        source_id: str | None = None,
    ) -> SourceRecord:
        try:
            owner = _validate_opaque_id(
                owner_principal_id, field_name="owner_principal_id"
            )
            correlation = _validate_opaque_id(
                correlation_id, field_name="correlation_id"
            )
        except ValueError as exc:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_ISOLATION_INVALID_REQUEST,
                "The Source registration request is invalid.",
            ) from exc
        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version != 0:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT,
                "The Source version does not match.",
            )
        candidate_id = source_id or self._source_id_factory()
        try:
            validate_user_source_id(candidate_id)
        except ValueError as exc:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_ISOLATION_INVALID_REQUEST,
                "The Source registration request is invalid.",
            ) from exc
        if not isinstance(actor_type, SourceActorType):
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_ISOLATION_INVALID_REQUEST,
                "The Source registration request is invalid.",
            )
        now = _validate_utc(self._clock(), field_name="clock")
        record = SourceRecord(
            source_id=candidate_id,
            owner_principal_id=owner,
            state=SourceLifecycleState.REGISTERED,
            record_version=1,
            created_at=now,
            updated_at=now,
        )
        audit = self._audit_event(
            source_id=candidate_id,
            actor_type=actor_type,
            action="SOURCE_REGISTERED",
            before_state=None,
            after_state=record.state,
            correlation_id=correlation,
            created_at=now,
        )
        with self._repository.transaction() as transaction:
            if transaction.get_source(candidate_id) is not None:
                raise SourceLifecycleException(
                    SourceLifecycleErrorCode.SOURCE_ID_CONFLICT,
                    "The Source identifier is already registered.",
                )
            if transaction.count_non_deleted_sources(owner) >= MAX_SOURCES_PER_PRINCIPAL:
                raise SourceLifecycleException(
                    SourceLifecycleErrorCode.SOURCE_COUNT_LIMIT_EXCEEDED,
                    "The Source count limit has been reached.",
                )
            transaction.insert_source(record)
            transaction._inject_fault("after_entity_write")
            transaction._inject_fault("before_audit_write")
            transaction.insert_audit(audit)
        return record

    def get_source(self, *, principal_id: str, source_id: str) -> SourceRecord:
        if not principal_id:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_AUTH_REQUIRED,
                "Source authentication is required.",
            )
        try:
            principal = _validate_opaque_id(principal_id, field_name="principal_id")
            validate_user_source_id(source_id)
        except ValueError as exc:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_NOT_FOUND,
                "The Source was not found.",
            ) from exc
        record = self._repository.get_source(source_id)
        if (
            record is None
            or record.owner_principal_id != principal
            or record.state
            in {SourceLifecycleState.DELETE_PENDING, SourceLifecycleState.DELETED}
        ):
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_NOT_FOUND,
                "The Source was not found.",
            )
        return record

    def transition_source(
        self,
        *,
        principal_id: str,
        source_id: str,
        expected_version: int,
        target_state: SourceLifecycleState,
        actor_type: SourceActorType,
        correlation_id: str,
        revision: SourceRevisionDraft | None = None,
    ) -> SourceRecord:
        if not principal_id:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_AUTH_REQUIRED,
                "Source authentication is required.",
            )
        try:
            principal = _validate_opaque_id(principal_id, field_name="principal_id")
            validate_user_source_id(source_id)
            correlation = _validate_opaque_id(
                correlation_id, field_name="correlation_id"
            )
        except ValueError as exc:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_NOT_FOUND,
                "The Source was not found.",
            ) from exc
        if (
            not isinstance(expected_version, int)
            or isinstance(expected_version, bool)
            or expected_version < 1
        ):
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT,
                "The Source version does not match.",
            )
        if not isinstance(target_state, SourceLifecycleState):
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_INVALID_TRANSITION,
                "The Source lifecycle transition is invalid.",
            )
        if (
            not isinstance(actor_type, SourceActorType)
            or (target_state is SourceLifecycleState.READY) != (revision is not None)
            or (
                revision is not None
                and revision.build_result != SUCCESSFUL_BUILD_RESULT
            )
        ):
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_INVALID_TRANSITION,
                "The Source lifecycle transition is invalid.",
            )
        now = _validate_utc(self._clock(), field_name="clock")
        with self._repository.transaction() as transaction:
            current = transaction.get_source(source_id)
            if current is None or current.owner_principal_id != principal:
                raise SourceLifecycleException(
                    SourceLifecycleErrorCode.SOURCE_NOT_FOUND,
                    "The Source was not found.",
                )
            if current.record_version != expected_version:
                raise SourceLifecycleException(
                    SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT,
                    "The Source version does not match.",
                )
            if target_state not in _ALLOWED_TRANSITIONS[current.state]:
                raise SourceLifecycleException(
                    SourceLifecycleErrorCode.SOURCE_INVALID_TRANSITION,
                    "The Source lifecycle transition is invalid.",
                )

            revision_record: SourceRevision | None = None
            published_revision_no = current.published_revision_no
            published_generation = current.published_generation
            if revision is not None:
                revision_no = transaction.next_revision_no(source_id)
                revision_record = SourceRevision(
                    source_id=source_id,
                    revision_no=revision_no,
                    build_result=revision.build_result,
                    source_fingerprint=revision.source_fingerprint,
                    manifest_digest=revision.manifest_digest,
                    parser_schema_version=revision.parser_schema_version,
                    chunk_schema_version=revision.chunk_schema_version,
                    generation=revision.generation,
                    document_count=revision.document_count,
                    chunk_count=revision.chunk_count,
                    raw_bytes=revision.raw_bytes,
                    created_at=now,
                )
                published_revision_no = revision_no
                published_generation = revision.generation

            updated = SourceRecord(
                source_id=current.source_id,
                owner_principal_id=current.owner_principal_id,
                state=target_state,
                record_version=current.record_version + 1,
                created_at=current.created_at,
                updated_at=now,
                published_revision_no=published_revision_no,
                published_generation=published_generation,
            )
            if revision_record is not None:
                transaction.insert_revision(revision_record)
            if not transaction.update_source(updated, expected_version=expected_version):
                raise SourceLifecycleException(
                    SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT,
                    "The Source version does not match.",
                )
            transaction._inject_fault("after_entity_write")
            transaction._inject_fault("before_audit_write")
            transaction.insert_audit(
                self._audit_event(
                    source_id=source_id,
                    actor_type=actor_type,
                    action=f"SOURCE_{target_state.value}",
                    before_state=current.state,
                    after_state=target_state,
                    correlation_id=correlation,
                    created_at=now,
                )
            )
        return updated

    def list_audit_events(
        self, *, principal_id: str, source_id: str
    ) -> tuple[AuditEvent, ...]:
        if not principal_id:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_AUTH_REQUIRED,
                "Source authentication is required.",
            )
        try:
            principal = _validate_opaque_id(principal_id, field_name="principal_id")
            validate_user_source_id(source_id)
        except ValueError as exc:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_NOT_FOUND,
                "The Source was not found.",
            ) from exc
        record = self._repository.get_source(source_id)
        if (
            record is None
            or record.owner_principal_id != principal
            or record.state
            in {SourceLifecycleState.DELETE_PENDING, SourceLifecycleState.DELETED}
        ):
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_NOT_FOUND,
                "The Source was not found.",
            )
        return self._repository.list_audit_events(source_id)

    def list_sources(self, *, principal_id: str) -> tuple[SourceRecord, ...]:
        if not principal_id:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_AUTH_REQUIRED,
                "Source authentication is required.",
            )
        try:
            principal = _validate_opaque_id(principal_id, field_name="principal_id")
        except ValueError as exc:
            raise SourceLifecycleException(
                SourceLifecycleErrorCode.SOURCE_NOT_FOUND,
                "The Source was not found.",
            ) from exc
        return self._repository.list_sources(principal)

    def create_source(self, **kwargs: object) -> SourceRecord:
        """Compatibility spelling for the registration command."""
        return self.register_source(**kwargs)  # type: ignore[arg-type]

    def transition(self, **kwargs: object) -> SourceRecord:
        """Compatibility spelling for the lifecycle transition command."""
        return self.transition_source(**kwargs)  # type: ignore[arg-type]

    def _audit_event(
        self,
        *,
        source_id: str,
        actor_type: SourceActorType,
        action: str,
        before_state: SourceLifecycleState | None,
        after_state: SourceLifecycleState,
        correlation_id: str,
        created_at: datetime,
    ) -> AuditEvent:
        return AuditEvent(
            event_id=self._id_factory(),
            source_id=source_id,
            actor_type=actor_type,
            action=action,
            before_state=before_state,
            after_state=after_state,
            entity_id=source_id,
            correlation_id=correlation_id,
            result="SUCCESS",
            created_at=created_at,
        )


__all__ = [
    "AuditEvent",
    "LifecycleError",
    "LIFECYCLE_SCHEMA_FAMILY",
    "LIFECYCLE_SCHEMA_VERSION",
    "SUCCESSFUL_BUILD_RESULT",
    "SourceActorType",
    "SourceLifecycleErrorCode",
    "SourceLifecycleException",
    "SourceLifecycleRepository",
    "SourceLifecycleService",
    "SourceLifecycleState",
    "SourceLifecycleTransaction",
    "SourceRecord",
    "SourceRevision",
    "SourceRevisionDraft",
    "SourceSchemaUnsupportedError",
    "SqliteSourceRegistry",
    "SyncRun",
    "generate_user_source_id",
    "generate_uuid7",
    "validate_user_source_id",
    "validate_uuid7",
]


def _source_from_row(row: sqlite3.Row) -> SourceRecord:
    try:
        return SourceRecord(
            source_id=row["source_id"],
            owner_principal_id=row["owner_principal_id"],
            source_type=row["source_type"],
            state=SourceLifecycleState(row["state"]),
            record_version=row["record_version"],
            published_revision_no=row["published_revision_no"],
            published_generation=row["published_generation"],
            created_at=_parse_timestamp(row["created_at"]),
            updated_at=_parse_timestamp(row["updated_at"]),
            schema_version=row["schema_version"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceSchemaUnsupportedError() from exc


def _revision_from_row(row: sqlite3.Row) -> SourceRevision:
    try:
        return SourceRevision(
            source_id=row["source_id"],
            revision_no=row["revision_no"],
            build_result=row["build_result"],
            source_fingerprint=row["source_fingerprint"],
            manifest_digest=row["manifest_digest"],
            parser_schema_version=row["parser_schema_version"],
            chunk_schema_version=row["chunk_schema_version"],
            generation=row["generation"],
            document_count=row["document_count"],
            chunk_count=row["chunk_count"],
            raw_bytes=row["raw_bytes"],
            created_at=_parse_timestamp(row["created_at"]),
            schema_version=row["schema_version"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceSchemaUnsupportedError() from exc


def _audit_from_row(row: sqlite3.Row) -> AuditEvent:
    try:
        before = row["before_state"]
        return AuditEvent(
            event_id=row["event_id"],
            source_id=row["source_id"],
            actor_type=SourceActorType(row["actor_type"]),
            action=row["action"],
            before_state=None if before is None else SourceLifecycleState(before),
            after_state=SourceLifecycleState(row["after_state"]),
            entity_id=row["entity_id"],
            correlation_id=row["correlation_id"],
            result=row["result"],
            created_at=_parse_timestamp(row["created_at"]),
            schema_version=row["schema_version"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceSchemaUnsupportedError() from exc


def _sync_run_from_row(row: sqlite3.Row) -> SyncRun:
    try:
        finished_at = row["finished_at"]
        return SyncRun(
            run_id=row["run_id"],
            request_id=row["request_id"],
            source_id=row["source_id"],
            requested_strategy=row["requested_strategy"],
            status=row["status"],
            input_revision_no=row["input_revision_no"],
            candidate_generation=row["candidate_generation"],
            result_code=row["result_code"],
            document_count=row["document_count"],
            chunk_count=row["chunk_count"],
            raw_bytes=row["raw_bytes"],
            started_at=_parse_timestamp(row["started_at"]),
            updated_at=_parse_timestamp(row["updated_at"]),
            finished_at=None if finished_at is None else _parse_timestamp(finished_at),
            schema_version=row["schema_version"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceSchemaUnsupportedError() from exc


def _lifecycle_error_from_row(row: sqlite3.Row) -> LifecycleError:
    try:
        return LifecycleError(
            error_id=row["error_id"],
            source_id=row["source_id"],
            entity_id=row["entity_id"],
            stage=row["stage"],
            error_code=row["error_code"],
            first_seen_at=_parse_timestamp(row["first_seen_at"]),
            last_seen_at=_parse_timestamp(row["last_seen_at"]),
            count=row["count"],
            schema_version=row["schema_version"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceSchemaUnsupportedError() from exc
