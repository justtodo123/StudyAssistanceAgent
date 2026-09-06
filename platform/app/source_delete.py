"""Source-local M7 delete contract: tombstones, unreadability, and hard-delete.

This module is intentionally disconnected from FastAPI, Search, QA, preview,
and published retrieval indexes.  It coordinates Source Registry CAS transitions
with source-local tombstones and retrieval-surface unreadability.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Callable, Iterable, Iterator, Mapping, Protocol

from .source_operation_lock import operation_lock
from .source_registry import (
    SourceActorType,
    SourceLifecycleErrorCode,
    SourceLifecycleException,
    SourceLifecycleService,
    SourceLifecycleState,
    generate_uuid7,
    validate_user_source_id,
    validate_uuid7,
)
from .user_source_snapshot import UserSourceSnapshotPublisher

DELETE_SCHEMA_VERSION = "sa.source.delete.v1"
DELETE_SCHEMA_NUMERIC = 2
DELETE_OPERATION_SCHEMA_VERSION = 1
MIN_AUDIT_RETENTION_DAYS = 30
SOURCE_WIDE_URI = "*"
DELETE_RETRY_DELAYS = (1.0, 2.0)
_ALLOWED_FIELDS = frozenset({
    "principal_id",
    "source_id",
    "request_id",
    "expected_version",
    "actor_type",
    "reason",
    "protocol_version",
    "correlation_id",
})
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,127}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_HIDDEN_STATES = frozenset(
    {SourceLifecycleState.DELETE_PENDING, SourceLifecycleState.DELETED}
)

class SourceIndexRuntime(Protocol):
    """Source-scoped runtime cache that must be released before deletion."""

    def clear_source(self, source_id: str) -> None: ...


class SourceDeleteErrorCode(StrEnum):
    SOURCE_AUTH_REQUIRED = "SOURCE_AUTH_REQUIRED"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    SOURCE_DELETE_INVALID_REQUEST = "SOURCE_DELETE_INVALID_REQUEST"
    SOURCE_SCHEMA_UNSUPPORTED = "SOURCE_SCHEMA_UNSUPPORTED"
    SOURCE_ALREADY_DELETED = "SOURCE_ALREADY_DELETED"
    SOURCE_VERSION_CONFLICT = "SOURCE_VERSION_CONFLICT"
    SOURCE_DELETE_REQUEST_CONFLICT = "SOURCE_DELETE_REQUEST_CONFLICT"
    SOURCE_DELETE_FAILED = "SOURCE_DELETE_FAILED"
    SOURCE_HARD_DELETE_INCOMPLETE = "SOURCE_HARD_DELETE_INCOMPLETE"


class SourceDeleteError(RuntimeError):
    """Stable, content-free delete failure."""

    def __init__(self, code: SourceDeleteErrorCode, message: str = "Source delete failed.") -> None:
        self.code = code
        super().__init__(message)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST)
    return parsed.astimezone(timezone.utc)


def _validate_opaque(value: object) -> str:
    if not isinstance(value, str) or _OPAQUE_ID_RE.fullmatch(value) is None:
        raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST)
    return value


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(payload: Mapping[str, object] | str | bytes) -> str:
    if isinstance(payload, bytes):
        raw = payload
    elif isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = _canonical_json(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return False
    if isinstance(exc, sqlite3.OperationalError):
        detail = str(exc).lower()
        return "busy" in detail or "locked" in detail
    return isinstance(exc, OSError)


def _translate_lifecycle(exc: SourceLifecycleException) -> SourceDeleteError:
    mapping = {
        SourceLifecycleErrorCode.SOURCE_AUTH_REQUIRED: SourceDeleteErrorCode.SOURCE_AUTH_REQUIRED,
        SourceLifecycleErrorCode.SOURCE_NOT_FOUND: SourceDeleteErrorCode.SOURCE_NOT_FOUND,
        SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT: SourceDeleteErrorCode.SOURCE_VERSION_CONFLICT,
        SourceLifecycleErrorCode.SOURCE_SCHEMA_UNSUPPORTED: SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED,
        SourceLifecycleErrorCode.SOURCE_INVALID_TRANSITION: SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST,
    }
    return SourceDeleteError(mapping.get(exc.code, SourceDeleteErrorCode.SOURCE_DELETE_FAILED))


@dataclass(frozen=True, slots=True)
class DeletionIntent:
    source_id: str
    request_id: str
    owner_principal_id: str
    actor_type: SourceActorType
    reason_code: str
    expected_version: int
    generation_upper_bound: str | None
    correlation_id: str
    created_at: datetime
    protocol_version: str = DELETE_SCHEMA_VERSION
    schema_version: int = DELETE_SCHEMA_NUMERIC
    barrier_published: bool = False
    surfaces_unreadable: bool = False

    def to_public_dict(self) -> dict[str, object]:
        return {
            "schema_name": self.protocol_version,
            "source_id": self.source_id,
            "request_id": self.request_id,
            "actor_type": self.actor_type.value,
            "reason_code": self.reason_code,
            "expected_version": self.expected_version,
            "generation_upper_bound": self.generation_upper_bound,
            "created_at": _timestamp(self.created_at),
            "barrier_published": self.barrier_published,
            "surfaces_unreadable": self.surfaces_unreadable,
        }


@dataclass(frozen=True, slots=True)
class Tombstone:
    source_id: str
    logical_uri: str
    document_id: str | None
    generation_upper_bound: str | None
    request_id: str
    reason_code: str
    created_at: datetime
    schema_version: int = DELETE_SCHEMA_NUMERIC


@dataclass(frozen=True, slots=True)
class HardDeleteReceipt:
    receipt_id: str
    source_id: str
    request_id: str
    scope_digest: str
    object_counts: dict[str, int]
    store_digests: dict[str, str]
    started_at: datetime
    finished_at: datetime
    policy_version: str
    result_code: str
    schema_version: int = DELETE_SCHEMA_NUMERIC

    def to_public_dict(self) -> dict[str, object]:
        return {
            "receipt_id": self.receipt_id,
            "source_id": self.source_id,
            "request_id": self.request_id,
            "scope_digest": self.scope_digest,
            "object_counts": dict(self.object_counts),
            "store_digests": dict(self.store_digests),
            "started_at": _timestamp(self.started_at),
            "finished_at": _timestamp(self.finished_at),
            "policy_version": self.policy_version,
            "result_code": self.result_code,
        }


@dataclass(frozen=True, slots=True)
class _HardDeleteOperation:
    source_id: str
    request_id: str
    object_counts: dict[str, int]
    store_digests: dict[str, str]
    started_at: datetime
    schema_version: int = DELETE_OPERATION_SCHEMA_VERSION


class SourceLocalRetrievalSurfaces:
    """Source-local BM25/vector/result-cache/provenance handles for delete tests."""

    def __init__(self, cache_root: str | Path) -> None:
        self._root = Path(cache_root) / "retrieval-surfaces" / "v1"
        self._payload_cache: dict[str, tuple[int, dict[str, object] | None]] = {}

    def path(self, source_id: str) -> Path:
        return self._root / source_id

    def seed(
        self,
        source_id: str,
        *,
        generation: str,
        documents: Iterable[Mapping[str, str]],
        provenance: Iterable[Mapping[str, object]] = (),
        result_cache: Mapping[str, str] | None = None,
    ) -> None:
        root = self.path(source_id)
        root.mkdir(parents=True, exist_ok=True)
        docs = [dict(item) for item in documents]
        payload = {
            "source_id": source_id,
            "generation": generation,
            "readable": True,
            "documents": docs,
            "bm25": {item["document_id"]: item.get("logical_uri", "") for item in docs},
            "vector": {item["document_id"]: item.get("chunk_id", "") for item in docs},
            "result_cache": dict(result_cache or {}),
            "provenance": [dict(item) for item in provenance],
        }
        self._write(root / "surfaces.json", payload)

    def mark_unreadable(self, source_id: str) -> None:
        payload = self._load(source_id)
        if payload is None:
            self.path(source_id).mkdir(parents=True, exist_ok=True)
            payload = {
                "source_id": source_id,
                "generation": None,
                "readable": False,
                "documents": [],
                "bm25": {},
                "vector": {},
                "result_cache": {},
                "provenance": [],
            }
        payload["readable"] = False
        for record in payload.get("provenance", []):
            if isinstance(record, dict):
                record["status"] = "TOMBSTONED"
        self._write(self.path(source_id) / "surfaces.json", payload)

    def mark_stale_derivations(self, origin_document_ids: Iterable[str]) -> None:
        origins = set(origin_document_ids)
        if not origins or not self._root.exists():
            return
        for path in self._root.glob("*/surfaces.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            changed = False
            for record in payload.get("provenance", []):
                derived_from = record.get("derived_from_document_ids") or []
                if any(item in origins for item in derived_from):
                    record["status"] = "STALE_DERIVATION"
                    changed = True
            if changed:
                self._write(path, payload)

    def readable(self, source_id: str, surface: str | None = None) -> bool:
        del surface
        payload = self._load(source_id)
        return bool(payload and payload.get("readable") is True)

    def lookup(self, source_id: str, surface: str, identity: str) -> object | None:
        payload = self._load(source_id)
        if payload is None or payload.get("readable") is not True:
            return None
        if surface == "provenance":
            for record in payload.get("provenance", []):
                if record.get("document_id") == identity and record.get("status") not in {
                    "TOMBSTONED",
                    "STALE_DERIVATION",
                }:
                    return record
            return None
        bucket = payload.get(surface) or {}
        return bucket.get(identity)

    def provenance_status(self, source_id: str, document_id: str) -> str | None:
        payload = self._load(source_id)
        if payload is None:
            return None
        if payload.get("readable") is not True:
            return "TOMBSTONED"
        for record in payload.get("provenance", []):
            if record.get("document_id") == document_id:
                return str(record.get("status") or "ACTIVE")
        return None

    def physical_clear(self, source_id: str) -> None:
        self._payload_cache.pop(source_id, None)
        root = self.path(source_id)
        if root.exists():
            for child in root.iterdir():
                child.unlink()
            root.rmdir()

    def confirmation_digest(self, source_id: str) -> str:
        if not self.path(source_id).exists():
            return _digest({"source_id": source_id, "cleared": True})
        payload = self._load(source_id) or {}
        return _digest({"source_id": source_id, "readable": bool(payload.get("readable")), "exists": True})

    def _load(self, source_id: str) -> dict[str, object] | None:
        path = self.path(source_id) / "surfaces.json"
        if not path.is_file():
            self._payload_cache[source_id] = (-1, None)
            return None
        mtime_ns = getattr(path.stat(), "st_mtime_ns", int(path.stat().st_mtime * 1_000_000_000))
        cached = self._payload_cache.get(source_id)
        if cached is not None and cached[0] == mtime_ns:
            return cached[1]
        payload = json.loads(path.read_text(encoding="utf-8"))
        parsed = payload if isinstance(payload, dict) else None
        self._payload_cache[source_id] = (int(mtime_ns), parsed)
        return parsed

    def _write(self, path: Path, payload: Mapping[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_canonical_json(payload), encoding="utf-8")
        source_id = path.parent.name
        self._payload_cache.pop(source_id, None)


_DELETE_SCHEMA = """
CREATE TABLE delete_meta (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    schema_family TEXT NOT NULL,
    schema_version INTEGER NOT NULL
);
CREATE TABLE deletion_intents (
    source_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    protocol_version TEXT NOT NULL,
    owner_principal_id TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    expected_version INTEGER NOT NULL,
    generation_upper_bound TEXT,
    correlation_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    barrier_published INTEGER NOT NULL DEFAULT 0 CHECK(barrier_published IN (0, 1)),
    surfaces_unreadable INTEGER NOT NULL DEFAULT 0 CHECK(surfaces_unreadable IN (0, 1)),
    PRIMARY KEY(source_id, request_id)
);
CREATE UNIQUE INDEX deletion_intents_source_uidx ON deletion_intents(source_id);
CREATE TABLE tombstones (
    source_id TEXT NOT NULL,
    logical_uri TEXT NOT NULL,
    document_id TEXT,
    generation_upper_bound TEXT,
    request_id TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    created_at TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    PRIMARY KEY(source_id, logical_uri)
);
CREATE TABLE hard_delete_operations (
    source_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    object_counts TEXT NOT NULL,
    store_digests TEXT NOT NULL,
    started_at TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    PRIMARY KEY(source_id, request_id)
);
CREATE TABLE hard_delete_receipts (
    receipt_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    scope_digest TEXT NOT NULL,
    object_counts TEXT NOT NULL,
    store_digests TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    result_code TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    UNIQUE(source_id, request_id)
);
CREATE TRIGGER hard_delete_receipts_no_update
BEFORE UPDATE ON hard_delete_receipts
BEGIN
    SELECT RAISE(ABORT, 'hard-delete receipts are immutable');
END;
CREATE TRIGGER hard_delete_receipts_no_delete
BEFORE DELETE ON hard_delete_receipts
BEGIN
    SELECT RAISE(ABORT, 'hard-delete receipts are immutable');
END;
"""


class UserSourceDeleteService:
    """Admit a logical delete, publish tombstones, and later hard-delete."""

    def __init__(
        self,
        cache_root: str | Path,
        lifecycle: SourceLifecycleService,
        *,
        publisher: UserSourceSnapshotPublisher | None = None,
        fts5: SourceIndexRuntime | None = None,
        vector: SourceIndexRuntime | None = None,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] | None = None,
        retry_delays: tuple[float, float] = DELETE_RETRY_DELAYS,
        retention_days: int = MIN_AUDIT_RETENTION_DAYS,
    ) -> None:
        if retention_days < MIN_AUDIT_RETENTION_DAYS:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST)
        self._cache_root = Path(cache_root)
        self._operation_lock = operation_lock(self._cache_root)
        self._lifecycle = lifecycle
        self._publisher = publisher
        self._fts5 = fts5
        self._vector = vector
        self._runtimes: list[SourceIndexRuntime] = []
        for runtime in (publisher, fts5, vector):
            if runtime is not None:
                self._runtimes.append(runtime)
        self._clock = clock or _utc_now
        self._sleeper = sleeper or (lambda _delay: None)
        self._retry_delays = retry_delays
        self._retention = timedelta(days=retention_days)
        self._db_path = self._cache_root / "source-delete" / "v1" / "delete.sqlite3"
        self._lock = threading.RLock()
        self.surfaces = SourceLocalRetrievalSurfaces(self._cache_root)
        self.stage_faults: dict[str, list[BaseException]] = {}
        with self._operation_lock:
            self._initialize()

    def attach_index_runtimes(
        self,
        fts5: SourceIndexRuntime,
        vector: SourceIndexRuntime,
    ) -> None:
        """Use live retrieval indexes when clearing a source."""
        with self._lock:
            self._fts5 = fts5
            self._vector = vector
            for runtime in (fts5, vector):
                if all(existing is not runtime for existing in self._runtimes):
                    self._runtimes.append(runtime)

    def attach_runtime(self, runtime: SourceIndexRuntime) -> None:
        """Track a cache-owning runtime for hard-delete invalidation."""
        with self._lock:
            if all(existing is not runtime for existing in self._runtimes):
                self._runtimes.append(runtime)

    def request_delete(
        self,
        *,
        principal_id: str,
        source_id: str,
        request_id: str,
        expected_version: int,
        actor_type: SourceActorType,
        reason: str,
        correlation_id: str,
        protocol_version: str = DELETE_SCHEMA_VERSION,
        extra_fields: Mapping[str, object] | None = None,
    ) -> DeletionIntent:
        retry_after_admission = False
        with self._operation_lock:
            self._validate_request(
                principal_id=principal_id,
                source_id=source_id,
                request_id=request_id,
                expected_version=expected_version,
                actor_type=actor_type,
                reason=reason,
                correlation_id=correlation_id,
                protocol_version=protocol_version,
                extra_fields=extra_fields,
            )
            intent = self.get_intent(source_id, request_id)
            if intent is not None:
                self._assert_idempotent(
                    intent,
                    expected_version=expected_version,
                    actor_type=actor_type,
                    reason=reason,
                    protocol_version=protocol_version,
                )
            else:
                record = self._internal_source(source_id)
                if record is None or record.owner_principal_id != principal_id:
                    raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_NOT_FOUND)
                if record.state is SourceLifecycleState.DELETED:
                    raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_ALREADY_DELETED)
                other = self._intent_for_source(source_id)
                if other is not None:
                    raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_VERSION_CONFLICT)
                try:
                    intent = self._write_intent(
                        source_id=source_id,
                        request_id=request_id,
                        owner_principal_id=record.owner_principal_id,
                        actor_type=actor_type,
                        reason=reason,
                        expected_version=expected_version,
                        generation_upper_bound=record.published_generation,
                        correlation_id=correlation_id,
                    )
                except sqlite3.IntegrityError as exc:
                    other = self._intent_for_source(source_id)
                    if other is None or other.request_id != request_id:
                        raise SourceDeleteError(
                            SourceDeleteErrorCode.SOURCE_VERSION_CONFLICT
                        ) from exc
                    intent = other
            intent = self._ensure_pending_and_barrier(
                intent,
                principal_id=principal_id,
                actor_type=actor_type,
                correlation_id=correlation_id,
            )
            retry_after_admission = not (
                intent.barrier_published and intent.surfaces_unreadable
            )
        if retry_after_admission:
            if not self._retry_delays:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_FAILED)
            self._sleeper(self._retry_delays[0])
            return self._resume_barrier(intent, attempts=1)
        return intent

    def _ensure_pending_and_barrier(
        self,
        intent: DeletionIntent,
        *,
        principal_id: str,
        actor_type: SourceActorType,
        correlation_id: str,
    ) -> DeletionIntent:
        with self._operation_lock:
            record = self._internal_source(intent.source_id)
            if record is None or record.owner_principal_id != principal_id:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_NOT_FOUND)
            if record.state is SourceLifecycleState.DELETED:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_ALREADY_DELETED)
            if record.state is not SourceLifecycleState.DELETE_PENDING:
                try:
                    self._lifecycle.transition_source(
                        principal_id=principal_id,
                        source_id=intent.source_id,
                        expected_version=intent.expected_version,
                        target_state=SourceLifecycleState.DELETE_PENDING,
                        actor_type=actor_type,
                        correlation_id=correlation_id,
                    )
                except SourceLifecycleException as exc:
                    if exc.code is SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT:
                        current = self._internal_source(intent.source_id)
                        if current is None or current.state is not SourceLifecycleState.DELETE_PENDING:
                            self._discard_unadmitted_intent(intent)
                            raise SourceDeleteError(
                                SourceDeleteErrorCode.SOURCE_VERSION_CONFLICT
                            ) from exc
                    else:
                        raise _translate_lifecycle(exc) from exc
                try:
                    self._inject_fault("after_cas")
                except SourceDeleteError:
                    raise
                except Exception as exc:
                    raise SourceDeleteError(
                        SourceDeleteErrorCode.SOURCE_DELETE_FAILED
                    ) from exc
            current = self.get_intent(intent.source_id, intent.request_id)
            if current is None:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_FAILED)
            if current.barrier_published and current.surfaces_unreadable:
                return current
            try:
                return self._resume_barrier_once(
                    current.source_id,
                    current.request_id,
                )
            except SourceDeleteError:
                raise
            except Exception as exc:
                if not _is_retryable(exc):
                    raise SourceDeleteError(
                        SourceDeleteErrorCode.SOURCE_DELETE_FAILED
                    ) from exc
                return current

    def sweep_hard_delete(self, source_id: str, request_id: str) -> HardDeleteReceipt | None:
        while True:
            with self._operation_lock:
                intent = self.get_intent(source_id, request_id)
                if intent is None:
                    raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_NOT_FOUND)
                existing = self.get_receipt(source_id, request_id)
                if existing is not None:
                    return self._complete_deleted_transition(intent, existing)
                now = self._clock()
                if now.tzinfo is None:
                    raise SourceDeleteError(
                        SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST
                    )
                if now < intent.created_at + self._retention:
                    return None
                barrier_complete = (
                    intent.barrier_published and intent.surfaces_unreadable
                )
            if not barrier_complete:
                self._resume_barrier(intent)
                continue

            with self._operation_lock:
                intent = self.get_intent(source_id, request_id)
                if intent is None:
                    raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_NOT_FOUND)
                existing = self.get_receipt(source_id, request_id)
                if existing is not None:
                    return self._complete_deleted_transition(intent, existing)
                now = self._clock()
                if now.tzinfo is None:
                    raise SourceDeleteError(
                        SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST
                    )
                if now < intent.created_at + self._retention:
                    return None
                if not intent.barrier_published or not intent.surfaces_unreadable:
                    continue
                try:
                    operation = self._prepare_hard_delete_operation(
                        source_id,
                        request_id,
                        now,
                    )
                    self._inject_fault("after_operation_prepared")
                    self._physical_clear(operation)
                    self._inject_fault("after_physical_clear")
                    self._inject_fault("before_receipt")
                    receipt = HardDeleteReceipt(
                        receipt_id=generate_uuid7(),
                        source_id=source_id,
                        request_id=request_id,
                        scope_digest=_digest(
                            {
                                "source_id": source_id,
                                "request_id": request_id,
                                "counts": operation.object_counts,
                            }
                        ),
                        object_counts=operation.object_counts,
                        store_digests=operation.store_digests,
                        started_at=operation.started_at,
                        finished_at=self._clock(),
                        policy_version=DELETE_SCHEMA_VERSION,
                        result_code="HARD_DELETE_COMPLETED",
                    )
                    receipt = self._insert_receipt(receipt)
                    self._inject_fault("before_deleted_transition")
                    return self._complete_deleted_transition(intent, receipt)
                except SourceDeleteError:
                    raise
                except Exception as exc:
                    raise SourceDeleteError(
                        SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE
                    ) from exc

    def _complete_deleted_transition(
        self,
        intent: DeletionIntent,
        receipt: HardDeleteReceipt,
    ) -> HardDeleteReceipt:
        current = self._internal_source(intent.source_id)
        if current is None:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE)
        if current.state is SourceLifecycleState.DELETED:
            return receipt
        if current.state is not SourceLifecycleState.DELETE_PENDING:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE)
        try:
            self._lifecycle.transition_source(
                principal_id=intent.owner_principal_id,
                source_id=intent.source_id,
                expected_version=current.record_version,
                target_state=SourceLifecycleState.DELETED,
                actor_type=SourceActorType.SERVICE,
                correlation_id=intent.correlation_id,
            )
        except SourceLifecycleException as exc:
            if exc.code is SourceLifecycleErrorCode.SOURCE_VERSION_CONFLICT:
                refreshed = self._internal_source(intent.source_id)
                if refreshed is not None and refreshed.state is SourceLifecycleState.DELETED:
                    return receipt
            raise _translate_lifecycle(exc) from exc
        return receipt

    def get_intent(self, source_id: str, request_id: str) -> DeletionIntent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM deletion_intents WHERE source_id = ? AND request_id = ?",
                (source_id, request_id),
            ).fetchone()
        return _intent_from_row(row) if row is not None else None

    def list_tombstones(self, source_id: str) -> tuple[Tombstone, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tombstones WHERE source_id = ? ORDER BY logical_uri",
                (source_id,),
            ).fetchall()
        return tuple(_tombstone_from_row(row) for row in rows)

    def get_receipt(self, source_id: str, request_id: str) -> HardDeleteReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM hard_delete_receipts WHERE source_id = ? AND request_id = ?",
                (source_id, request_id),
            ).fetchone()
        return _receipt_from_row(row) if row is not None else None

    def is_blocked(
        self,
        source_id: str,
        *,
        logical_uri: str | None = None,
        document_id: str | None = None,
        generation: str | None = None,
    ) -> bool:
        record = self._internal_source(source_id)
        if record is not None and record.state in _HIDDEN_STATES:
            return True
        for tombstone in self.list_tombstones(source_id):
            if tombstone.logical_uri == SOURCE_WIDE_URI:
                return True
            if logical_uri is not None and tombstone.logical_uri == logical_uri:
                return True
            if document_id is not None and tombstone.document_id == document_id:
                return True
            if generation is not None and tombstone.generation_upper_bound == generation:
                return True
        return False

    def inspect_for_audit(self, *, actor_type: SourceActorType, source_id: str) -> dict[str, object]:
        if actor_type is not SourceActorType.ADMIN:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_NOT_FOUND)
        intent = self._intent_for_source(source_id)
        if intent is None:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_NOT_FOUND)
        receipt = self.get_receipt(source_id, intent.request_id)
        return {
            "source_id": source_id,
            "request_id": intent.request_id,
            "reason_code": intent.reason_code,
            "created_at": _timestamp(intent.created_at),
            "result_code": None if receipt is None else receipt.result_code,
            "receipt_id": None if receipt is None else receipt.receipt_id,
        }

    def _validate_request(
        self,
        *,
        principal_id: str,
        source_id: str,
        request_id: str,
        expected_version: int,
        actor_type: SourceActorType,
        reason: str,
        correlation_id: str,
        protocol_version: str,
        extra_fields: Mapping[str, object] | None,
    ) -> None:
        if extra_fields and set(extra_fields) - _ALLOWED_FIELDS:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST)
        if not principal_id:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_AUTH_REQUIRED)
        if protocol_version != DELETE_SCHEMA_VERSION:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED)
        if not isinstance(actor_type, SourceActorType):
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST)
        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 1:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_VERSION_CONFLICT)
        try:
            _validate_opaque(principal_id)
            validate_user_source_id(source_id)
            validate_uuid7(request_id, field_name="request_id")
            _validate_opaque(reason)
            _validate_opaque(correlation_id)
        except ValueError as exc:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST) from exc

    def _assert_idempotent(
        self,
        existing: DeletionIntent,
        *,
        expected_version: int,
        actor_type: SourceActorType,
        reason: str,
        protocol_version: str,
    ) -> None:
        if (
            existing.expected_version != expected_version
            or existing.actor_type is not actor_type
            or existing.reason_code != reason
            or existing.protocol_version != protocol_version
        ):
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_REQUEST_CONFLICT)

    def _discard_unadmitted_intent(self, intent: DeletionIntent) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM deletion_intents
                WHERE source_id = ? AND request_id = ?
                  AND expected_version = ?
                  AND barrier_published = 0 AND surfaces_unreadable = 0
                """,
                (intent.source_id, intent.request_id, intent.expected_version),
            )
            connection.commit()

    def _resume_barrier(
        self,
        intent: DeletionIntent,
        *,
        attempts: int = 0,
    ) -> DeletionIntent:
        while True:
            try:
                return self._resume_barrier_once(
                    intent.source_id,
                    intent.request_id,
                )
            except SourceDeleteError:
                raise
            except Exception as exc:
                if not _is_retryable(exc) or attempts >= len(self._retry_delays):
                    raise SourceDeleteError(
                        SourceDeleteErrorCode.SOURCE_DELETE_FAILED
                    ) from exc
                delay = self._retry_delays[attempts]
                attempts += 1
                self._sleeper(delay)

    def _resume_barrier_once(
        self,
        source_id: str,
        request_id: str,
    ) -> DeletionIntent:
        with self._operation_lock:
            current = self.get_intent(source_id, request_id)
            if current is None:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_FAILED)
            if not current.barrier_published:
                self._publish_tombstones(current)
                self._inject_fault("after_tombstone")
                self._mark_intent(
                    current.source_id,
                    current.request_id,
                    barrier_published=True,
                )
            current = self.get_intent(source_id, request_id)
            if current is None:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_FAILED)
            if not current.surfaces_unreadable:
                identities = [
                    item.document_id
                    for item in self.list_tombstones(current.source_id)
                    if item.document_id
                ]
                self.surfaces.mark_stale_derivations(identities)
                self.surfaces.mark_unreadable(current.source_id)
                self._inject_fault("after_surfaces_unreadable")
                self._mark_intent(
                    current.source_id,
                    current.request_id,
                    surfaces_unreadable=True,
                )
            updated = self.get_intent(source_id, request_id)
            if updated is None:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_FAILED)
            return updated

    def _publish_tombstones(self, intent: DeletionIntent) -> None:
        documents: list[tuple[str, str | None]] = [(SOURCE_WIDE_URI, None)]
        snapshot = (
            None
            if self._publisher is None or intent.generation_upper_bound is None
            else self._publisher.load_snapshot(intent.source_id, intent.generation_upper_bound)
        )
        if snapshot is not None:
            for document in snapshot.documents:
                documents.append((document.logical_uri, document.document_id))
        else:
            payload = self.surfaces._load(intent.source_id)
            if payload is not None:
                for item in payload.get("documents", []):
                    documents.append((str(item.get("logical_uri") or SOURCE_WIDE_URI), item.get("document_id")))
        created_at = _timestamp(intent.created_at)
        with self._connect() as connection:
            for logical_uri, document_id in documents:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO tombstones (
                        source_id, logical_uri, document_id, generation_upper_bound,
                        request_id, reason_code, created_at, schema_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        intent.source_id,
                        logical_uri,
                        document_id,
                        intent.generation_upper_bound,
                        intent.request_id,
                        intent.reason_code,
                        created_at,
                        DELETE_SCHEMA_NUMERIC,
                    ),
                )
            connection.commit()

    def _get_hard_delete_operation(
        self,
        source_id: str,
        request_id: str,
    ) -> _HardDeleteOperation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM hard_delete_operations WHERE source_id = ? AND request_id = ?",
                (source_id, request_id),
            ).fetchone()
        if row is None:
            return None
        try:
            counts = json.loads(row["object_counts"])
            digests = json.loads(row["store_digests"])
            if (
                not isinstance(counts, dict)
                or not isinstance(digests, dict)
                or set(counts) != {"snapshots", "normalized_documents", "fts5", "vector", "tombstones", "surfaces"}
                or set(digests) != set(counts)
                or any(not isinstance(value, int) or value < 0 for value in counts.values())
                or any(not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None for value in digests.values())
            ):
                raise ValueError
            schema_version = int(row["schema_version"])
            if schema_version != DELETE_OPERATION_SCHEMA_VERSION:
                raise ValueError
            return _HardDeleteOperation(
                source_id=source_id,
                request_id=request_id,
                object_counts=counts,
                store_digests=digests,
                started_at=_parse_timestamp(row["started_at"]),
                schema_version=schema_version,
            )
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE) from exc

    def _prepare_hard_delete_operation(
        self,
        source_id: str,
        request_id: str,
        started_at: datetime,
    ) -> _HardDeleteOperation:
        existing = self._get_hard_delete_operation(source_id, request_id)
        if existing is not None:
            return existing
        snapshot_root = self._cache_root / "user-source-snapshots" / "v1" / source_id
        normalized_root = self._cache_root / "normalized-documents" / "v1" / source_id
        fts5_root = self._cache_root / "user-source-fts5" / "v1" / source_id
        vector_root = self._cache_root / "user-source-vector" / "v1" / source_id
        counts = {
            "snapshots": 1 if snapshot_root.exists() else 0,
            "normalized_documents": 1 if normalized_root.exists() else 0,
            "fts5": 1 if fts5_root.exists() else 0,
            "vector": 1 if vector_root.exists() else 0,
            "tombstones": len(self.list_tombstones(source_id)),
            "surfaces": 1 if self.surfaces.path(source_id).exists() else 0,
        }
        digests = {
            store: _digest({"source_id": source_id, "store": store, "cleared": True})
            for store in ("snapshots", "normalized_documents", "fts5", "vector", "tombstones")
        }
        digests["surfaces"] = _digest({"source_id": source_id, "cleared": True})
        operation = _HardDeleteOperation(
            source_id=source_id,
            request_id=request_id,
            object_counts=counts,
            store_digests=digests,
            started_at=started_at,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO hard_delete_operations
                (source_id, request_id, object_counts, store_digests, started_at, schema_version)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    request_id,
                    _canonical_json(counts),
                    _canonical_json(digests),
                    _timestamp(started_at),
                    DELETE_OPERATION_SCHEMA_VERSION,
                ),
            )
            connection.commit()
        persisted = self._get_hard_delete_operation(source_id, request_id)
        if persisted is None:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE)
        return persisted

    def _physical_clear(self, operation: _HardDeleteOperation) -> None:
        source_id = operation.source_id
        snapshot_root = self._cache_root / "user-source-snapshots" / "v1" / source_id
        normalized_root = self._cache_root / "normalized-documents" / "v1" / source_id
        fts5_root = self._cache_root / "user-source-fts5" / "v1" / source_id
        vector_root = self._cache_root / "user-source-vector" / "v1" / source_id
        with self._operation_lock, self._lock:
            runtimes = tuple(self._runtimes)
            for runtime in runtimes:
                runtime.clear_source(source_id)
            self._rmtree(snapshot_root)
            self._rmtree(normalized_root)
            self._rmtree(fts5_root)
            self._rmtree(vector_root)
            self.surfaces.physical_clear(source_id)
            with self._connect() as connection:
                connection.execute("DELETE FROM tombstones WHERE source_id = ?", (source_id,))
                connection.commit()
        remaining = (
            self.surfaces.path(source_id),
            snapshot_root,
            normalized_root,
            fts5_root,
            vector_root,
        )
        if any(path.exists() for path in remaining) or self.list_tombstones(source_id):
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_HARD_DELETE_INCOMPLETE)

    def _write_intent(
        self,
        *,
        source_id: str,
        request_id: str,
        owner_principal_id: str,
        actor_type: SourceActorType,
        reason: str,
        expected_version: int,
        generation_upper_bound: str | None,
        correlation_id: str,
    ) -> DeletionIntent:
        now = self._clock()
        if now.tzinfo is None:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_INVALID_REQUEST)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO deletion_intents (
                    source_id, request_id, schema_version, protocol_version,
                    owner_principal_id, actor_type, reason_code, expected_version,
                    generation_upper_bound, correlation_id, created_at,
                    barrier_published, surfaces_unreadable
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                """,
                (
                    source_id,
                    request_id,
                    DELETE_SCHEMA_NUMERIC,
                    DELETE_SCHEMA_VERSION,
                    owner_principal_id,
                    actor_type.value,
                    reason,
                    expected_version,
                    generation_upper_bound,
                    correlation_id,
                    _timestamp(now),
                ),
            )
            connection.commit()
        intent = self.get_intent(source_id, request_id)
        if intent is None:
            raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_DELETE_FAILED)
        return intent

    def _mark_intent(
        self,
        source_id: str,
        request_id: str,
        *,
        barrier_published: bool | None = None,
        surfaces_unreadable: bool | None = None,
    ) -> None:
        assignments: list[str] = []
        values: list[object] = []
        if barrier_published is not None:
            assignments.append("barrier_published = ?")
            values.append(1 if barrier_published else 0)
        if surfaces_unreadable is not None:
            assignments.append("surfaces_unreadable = ?")
            values.append(1 if surfaces_unreadable else 0)
        if not assignments:
            return
        values.extend([source_id, request_id])
        with self._connect() as connection:
            connection.execute(
                f"UPDATE deletion_intents SET {', '.join(assignments)} WHERE source_id = ? AND request_id = ?",
                values,
            )
            connection.commit()

    def _insert_receipt(self, receipt: HardDeleteReceipt) -> HardDeleteReceipt:
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO hard_delete_receipts (
                        receipt_id, source_id, request_id, scope_digest, object_counts,
                        store_digests, started_at, finished_at, policy_version,
                        result_code, schema_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.receipt_id,
                        receipt.source_id,
                        receipt.request_id,
                        receipt.scope_digest,
                        _canonical_json(receipt.object_counts),
                        _canonical_json(receipt.store_digests),
                        _timestamp(receipt.started_at),
                        _timestamp(receipt.finished_at),
                        receipt.policy_version,
                        receipt.result_code,
                        receipt.schema_version,
                    ),
                )
                connection.commit()
                return receipt
            except sqlite3.IntegrityError:
                row = connection.execute(
                    "SELECT * FROM hard_delete_receipts WHERE source_id = ? AND request_id = ?",
                    (receipt.source_id, receipt.request_id),
                ).fetchone()
                if row is None:
                    raise
                existing = _receipt_from_row(row)
                if (
                    existing.scope_digest != receipt.scope_digest
                    or existing.object_counts != receipt.object_counts
                    or existing.store_digests != receipt.store_digests
                    or existing.started_at != receipt.started_at
                    or existing.policy_version != receipt.policy_version
                    or existing.result_code != receipt.result_code
                ):
                    raise
                return existing

    def _intent_for_source(self, source_id: str) -> DeletionIntent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM deletion_intents WHERE source_id = ? ORDER BY created_at LIMIT 1",
                (source_id,),
            ).fetchone()
        return _intent_from_row(row) if row is not None else None

    def _internal_source(self, source_id: str):
        return self._lifecycle._repository.get_source(source_id)

    def _initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            exists = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'delete_meta'"
            ).fetchone()
            if exists is None:
                connection.executescript(_DELETE_SCHEMA)
                connection.execute(
                    "INSERT INTO delete_meta(singleton, schema_family, schema_version) VALUES (1, ?, ?)",
                    (DELETE_SCHEMA_VERSION, DELETE_SCHEMA_NUMERIC),
                )
                connection.commit()
                return
            row = connection.execute(
                "SELECT schema_family, schema_version FROM delete_meta WHERE singleton = 1"
            ).fetchone()
            if row is None or row["schema_family"] != DELETE_SCHEMA_VERSION:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED)
            try:
                version = int(row["schema_version"])
            except (TypeError, ValueError) as exc:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED) from exc
            if version > DELETE_SCHEMA_NUMERIC or version < 1:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED)

            operation_columns = connection.execute(
                "PRAGMA table_info(hard_delete_operations)"
            ).fetchall()
            expected_operation_columns = {
                "source_id",
                "request_id",
                "object_counts",
                "store_digests",
                "started_at",
                "schema_version",
            }
            if operation_columns:
                actual_columns = {row["name"] for row in operation_columns}
                primary_key = {row["name"] for row in operation_columns if row["pk"]}
                if (
                    actual_columns != expected_operation_columns
                    or primary_key != {"source_id", "request_id"}
                ):
                    raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED)
            elif version == 1:
                connection.execute(
                    """
                    CREATE TABLE hard_delete_operations (
                        source_id TEXT NOT NULL,
                        request_id TEXT NOT NULL,
                        object_counts TEXT NOT NULL,
                        store_digests TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        schema_version INTEGER NOT NULL,
                        PRIMARY KEY(source_id, request_id)
                    )
                    """
                )
            else:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED)

            receipt_columns = connection.execute(
                "PRAGMA table_info(hard_delete_receipts)"
            ).fetchall()
            expected_receipt_columns = {
                "receipt_id",
                "source_id",
                "request_id",
                "scope_digest",
                "object_counts",
                "store_digests",
                "started_at",
                "finished_at",
                "policy_version",
                "result_code",
                "schema_version",
            }
            if not receipt_columns:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED)
            actual_receipt_columns = {row["name"] for row in receipt_columns}
            receipt_primary_key = {
                row["name"] for row in receipt_columns if row["pk"]
            }
            if (
                actual_receipt_columns != expected_receipt_columns
                or receipt_primary_key != {"receipt_id"}
            ):
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED)
            receipt_unique = [
                row
                for row in connection.execute(
                    "PRAGMA index_list('hard_delete_receipts')"
                ).fetchall()
                if row["unique"]
            ]
            has_scope_unique = False
            for index in receipt_unique:
                index_name = index["name"]
                indexed_columns = connection.execute(
                    f"PRAGMA index_info('{index_name}')"
                ).fetchall()
                if {item["name"] for item in indexed_columns} == {
                    "source_id",
                    "request_id",
                }:
                    has_scope_unique = True
                    break
            if not has_scope_unique:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED)
            trigger_names = {
                row["name"]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'trigger' AND tbl_name = 'hard_delete_receipts'
                    """
                ).fetchall()
            }
            if not {
                "hard_delete_receipts_no_update",
                "hard_delete_receipts_no_delete",
            }.issubset(trigger_names):
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED)

            if version == 1:
                connection.execute(
                    "UPDATE delete_meta SET schema_version = ? WHERE singleton = 1",
                    (DELETE_SCHEMA_NUMERIC,),
                )
                connection.commit()
            elif version != DELETE_SCHEMA_NUMERIC:
                raise SourceDeleteError(SourceDeleteErrorCode.SOURCE_SCHEMA_UNSUPPORTED)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            connection = sqlite3.connect(str(self._db_path), timeout=30, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=30000")
            try:
                yield connection
            finally:
                connection.close()

    def _inject_fault(self, checkpoint: str) -> None:
        faults = self.stage_faults.get(checkpoint) or []
        if faults:
            raise faults.pop(0)

    def _rmtree(self, path: Path) -> None:
        if not path.exists():
            return
        if path.is_file():
            path.unlink()
            return
        for child in path.iterdir():
            self._rmtree(child)
        path.rmdir()


def _intent_from_row(row: sqlite3.Row) -> DeletionIntent:
    return DeletionIntent(
        source_id=row["source_id"],
        request_id=row["request_id"],
        owner_principal_id=row["owner_principal_id"],
        actor_type=SourceActorType(row["actor_type"]),
        reason_code=row["reason_code"],
        expected_version=int(row["expected_version"]),
        generation_upper_bound=row["generation_upper_bound"],
        correlation_id=row["correlation_id"],
        created_at=_parse_timestamp(row["created_at"]),
        protocol_version=row["protocol_version"],
        schema_version=int(row["schema_version"]),
        barrier_published=bool(row["barrier_published"]),
        surfaces_unreadable=bool(row["surfaces_unreadable"]),
    )


def _tombstone_from_row(row: sqlite3.Row) -> Tombstone:
    return Tombstone(
        source_id=row["source_id"],
        logical_uri=row["logical_uri"],
        document_id=row["document_id"],
        generation_upper_bound=row["generation_upper_bound"],
        request_id=row["request_id"],
        reason_code=row["reason_code"],
        created_at=_parse_timestamp(row["created_at"]),
        schema_version=int(row["schema_version"]),
    )


def _receipt_from_row(row: sqlite3.Row) -> HardDeleteReceipt:
    return HardDeleteReceipt(
        receipt_id=row["receipt_id"],
        source_id=row["source_id"],
        request_id=row["request_id"],
        scope_digest=row["scope_digest"],
        object_counts=json.loads(row["object_counts"]),
        store_digests=json.loads(row["store_digests"]),
        started_at=_parse_timestamp(row["started_at"]),
        finished_at=_parse_timestamp(row["finished_at"]),
        policy_version=row["policy_version"],
        result_code=row["result_code"],
        schema_version=int(row["schema_version"]),
    )
