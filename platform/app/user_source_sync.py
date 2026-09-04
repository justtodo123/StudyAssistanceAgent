"""Source-local M7 sync worker for FULL and restricted INCREMENTAL runs.

This module is intentionally disconnected from FastAPI, Search, QA, preview,
and published retrieval indexes.  It only coordinates Source Registry control
plane records with source-local snapshot artifacts.
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
from dataclasses import replace
from enum import StrEnum
from pathlib import Path
from typing import Callable

from .normalized_document import CHUNK_SCHEMA_VERSION
from .parser_matrix import ParserMatrixError
from .source_manifest import ManifestAcceptance, SourceManifestError, build_manifest, canonical_json
from .source_registry import (
    SYNC_RUN_CANCELLED,
    SYNC_RUN_FAILED,
    SYNC_RUN_INTERRUPTED_INPUT_CHANGED,
    SYNC_RUN_RUNNING,
    SYNC_RUN_SUCCESS,
    SourceActorType,
    SourceLifecycleException,
    SourceLifecycleService,
    SourceLifecycleState,
    SourceRecord,
    SourceRevisionDraft,
    SyncRun,
    validate_uuid7,
)
from .user_source_snapshot import (
    MAX_DOCUMENTS_PER_SOURCE,
    MAX_RAW_BYTES_PER_FILE,
    PARSER_SCHEMA_VERSION,
    FullSnapshot,
    FullSnapshotError,
    UserSourceSnapshotPublisher,
)

SYNC_SCHEMA_VERSION = "sa.source.sync.v1"
SYNC_RETRY_DELAYS = (1.0, 2.0)
_STAGE_ENUMERATE = "ENUMERATE"
_STAGE_PARSE = "PARSE"
_STAGE_ASSEMBLE = "ASSEMBLE"
_STAGE_VALIDATE = "VALIDATE"
_STAGE_PUBLISH = "PUBLISH"


class SourceSyncErrorCode(StrEnum):
    SOURCE_SYNC_BUSY = "SOURCE_SYNC_BUSY"
    SOURCE_SYNC_REQUEST_CONFLICT = "SOURCE_SYNC_REQUEST_CONFLICT"
    SOURCE_SYNC_PRECONDITION_FAILED = "SOURCE_SYNC_PRECONDITION_FAILED"
    SOURCE_SYNC_VALIDATION_FAILED = "SOURCE_SYNC_VALIDATION_FAILED"
    SOURCE_SYNC_RETRY_EXHAUSTED = "SOURCE_SYNC_RETRY_EXHAUSTED"
    SOURCE_SYNC_CANCELLED = "SOURCE_SYNC_CANCELLED"
    SOURCE_SYNC_INTERRUPTED = "SOURCE_SYNC_INTERRUPTED"
    SOURCE_VERSION_CONFLICT = "SOURCE_VERSION_CONFLICT"


class SourceSyncError(RuntimeError):
    """Stable, content-free sync failure."""

    def __init__(self, code: SourceSyncErrorCode, message: str = "Source sync failed.") -> None:
        self.code = code
        super().__init__(message)


def _translate(exc: SourceLifecycleException) -> SourceSyncError:
    try:
        return SourceSyncError(SourceSyncErrorCode(exc.code.value))
    except ValueError:
        return SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_VALIDATION_FAILED)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return False
    if isinstance(exc, sqlite3.OperationalError):
        detail = str(exc).lower()
        return "busy" in detail or "locked" in detail
    return isinstance(exc, OSError)


class UserSourceSyncService:
    """Admit and execute one source-local sync run at a time."""

    _process_lock = threading.Lock()
    _process_active: tuple[str, str] | None = None

    def __init__(
        self,
        cache_root: str | Path,
        lifecycle: SourceLifecycleService,
        *,
        publisher: UserSourceSnapshotPublisher | None = None,
        sleeper: Callable[[float], None] | None = None,
        retry_delays: tuple[float, float] = SYNC_RETRY_DELAYS,
    ) -> None:
        self._lifecycle = lifecycle
        self._publisher = publisher or UserSourceSnapshotPublisher(cache_root, lifecycle)
        self._sleeper = sleeper or (lambda _delay: None)
        self._retry_delays = retry_delays
        self.stage_faults: dict[str, list[BaseException]] = {}
        self.before_stage: dict[str, Callable[[], None]] = {}
        self._publishing = False

    @classmethod
    def reset_process_gate(cls) -> None:
        with cls._process_lock:
            cls._process_active = None

    def request_sync(
        self,
        *,
        principal_id: str,
        source_id: str,
        request_id: str,
        expected_version: int,
        source_root: str | Path,
        correlation_id: str,
        strategy: str = "FULL",
        actor_type: SourceActorType = SourceActorType.SERVICE,
    ) -> SyncRun:
        try:
            validate_uuid7(request_id, field_name="request_id")
        except ValueError as exc:
            raise SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_VALIDATION_FAILED) from exc
        acquired = False
        with self._process_lock:
            if self._process_active not in {None, (source_id, request_id)}:
                raise SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_BUSY)
            try:
                run = self._lifecycle.begin_sync_run(
                    principal_id=principal_id,
                    source_id=source_id,
                    request_id=request_id,
                    expected_version=expected_version,
                    strategy=strategy,
                    actor_type=actor_type,
                    correlation_id=correlation_id,
                    parser_schema_version=PARSER_SCHEMA_VERSION,
                    chunk_schema_version=CHUNK_SCHEMA_VERSION,
                )
            except SourceLifecycleException as exc:
                raise _translate(exc) from exc
            if run.status != SYNC_RUN_RUNNING:
                return run
            self._process_active = (source_id, request_id)
            acquired = True
        try:
            return self._execute(
                principal_id=principal_id,
                source_id=source_id,
                request_id=request_id,
                source_root=source_root,
                correlation_id=correlation_id,
                actor_type=actor_type,
                run=run,
            )
        finally:
            if acquired:
                with self._process_lock:
                    if self._process_active == (source_id, request_id):
                        self._process_active = None

    def request_cancel(
        self,
        *,
        principal_id: str,
        source_id: str,
        request_id: str,
        expected_version: int,
    ) -> SyncRun:
        try:
            return self._lifecycle.request_cancel(
                principal_id=principal_id,
                source_id=source_id,
                request_id=request_id,
                expected_version=expected_version,
            )
        except SourceLifecycleException as exc:
            raise _translate(exc) from exc

    def _execute(
        self,
        *,
        principal_id: str,
        source_id: str,
        request_id: str,
        source_root: str | Path,
        correlation_id: str,
        actor_type: SourceActorType,
        run: SyncRun,
    ) -> SyncRun:
        self._publishing = False
        record = self._lifecycle.get_source(principal_id=principal_id, source_id=source_id)
        try:
            last_good = self._load_last_good(run)
            input_digest, snapshot = self._run_build_stages(
                principal_id=principal_id,
                source_id=source_id,
                request_id=request_id,
                source_root=source_root,
                run=run,
                last_good=last_good,
            )
            self._checkpoint(
                principal_id,
                source_id,
                request_id,
                _STAGE_VALIDATE,
                input_digest,
                snapshot,
            )
            self._raise_if_cancelled(principal_id, source_id, request_id)
            self._publishing = True
            record, run = self._publish(
                principal_id=principal_id,
                source_id=source_id,
                request_id=request_id,
                correlation_id=correlation_id,
                actor_type=actor_type,
                snapshot=snapshot,
                run=self._lifecycle.get_sync_run(
                    principal_id=principal_id, source_id=source_id, request_id=request_id
                ),
            )
            current = self._publisher.published_path(source_id)
            if current is None or current.name != f"gen-{snapshot.generation}":
                self._publisher._activate_generation(snapshot)
            return run
        except SourceSyncError as exc:
            self._fail(
                principal_id=principal_id,
                source_id=source_id,
                request_id=request_id,
                correlation_id=correlation_id,
                actor_type=actor_type,
                code=exc.code,
                status=(
                    SYNC_RUN_CANCELLED
                    if exc.code is SourceSyncErrorCode.SOURCE_SYNC_CANCELLED
                    else SYNC_RUN_INTERRUPTED_INPUT_CHANGED
                    if exc.code is SourceSyncErrorCode.SOURCE_SYNC_INTERRUPTED
                    else SYNC_RUN_FAILED
                ),
            )
            raise
        except FullSnapshotError as exc:
            error = SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_VALIDATION_FAILED)
            self._fail(
                principal_id=principal_id,
                source_id=source_id,
                request_id=request_id,
                correlation_id=correlation_id,
                actor_type=actor_type,
                code=error.code,
                status=SYNC_RUN_FAILED,
            )
            raise error from exc
        except (SourceManifestError, ParserMatrixError) as exc:
            error = SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_VALIDATION_FAILED)
            self._fail(
                principal_id=principal_id,
                source_id=source_id,
                request_id=request_id,
                correlation_id=correlation_id,
                actor_type=actor_type,
                code=error.code,
                status=SYNC_RUN_FAILED,
            )
            raise error from exc
        except SourceLifecycleException as exc:
            error = _translate(exc)
            self._fail(
                principal_id=principal_id,
                source_id=source_id,
                request_id=request_id,
                correlation_id=correlation_id,
                actor_type=actor_type,
                code=error.code,
                status=SYNC_RUN_FAILED,
            )
            raise error from exc

    def _load_last_good(self, run: SyncRun) -> FullSnapshot | None:
        if run.requested_strategy != "INCREMENTAL" or run.input_revision_no is None:
            if run.checkpoint_stage in {_STAGE_ASSEMBLE, _STAGE_VALIDATE} and run.candidate_generation:
                return self._publisher.load_snapshot(run.source_id, run.candidate_generation)
            return self._publisher.load_snapshot(run.source_id)
        snapshot = self._publisher.load_snapshot(run.source_id)
        if snapshot is None:
            raise SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_PRECONDITION_FAILED)
        return snapshot

    def _run_build_stages(
        self,
        *,
        principal_id: str,
        source_id: str,
        request_id: str,
        source_root: str | Path,
        run: SyncRun,
        last_good: FullSnapshot | None,
    ) -> tuple[str, FullSnapshot]:
        source = self._lifecycle.get_source(principal_id=principal_id, source_id=source_id)
        self._hook(_STAGE_ENUMERATE)
        self._raise_if_cancelled(principal_id, source_id, request_id)
        inventory = self._retry(
            _STAGE_ENUMERATE,
            lambda: self._enumerate(source_root, source_id),
        )
        input_digest = hashlib.sha256(
            canonical_json(
                {
                    "schema_name": SYNC_SCHEMA_VERSION,
                    "source_id": source_id,
                    "strategy": run.requested_strategy,
                    "parser_schema_version": PARSER_SCHEMA_VERSION,
                    "chunk_schema_version": CHUNK_SCHEMA_VERSION,
                    "published_generation": source.published_generation,
                    "entries": inventory,
                }
            )
        ).hexdigest()
        if run.input_digest and run.input_digest != input_digest:
            self._mark_interrupted(principal_id, source_id, request_id)
            raise SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_INTERRUPTED)

        snapshot = None
        if (
            run.checkpoint_stage in {_STAGE_ASSEMBLE, _STAGE_VALIDATE}
            and run.candidate_generation
            and run.input_digest == input_digest
        ):
            snapshot = self._publisher.load_snapshot(source_id, run.candidate_generation)

        if snapshot is None:
            self._hook(_STAGE_PARSE)
            self._raise_if_cancelled(principal_id, source_id, request_id)
            reuse = last_good if run.requested_strategy == "INCREMENTAL" else None
            snapshot = self._retry(
                _STAGE_PARSE,
                lambda: self._publisher._build_candidate(source_root, source_id, reuse),
            )
            self._hook(_STAGE_ASSEMBLE)
            self._raise_if_cancelled(principal_id, source_id, request_id)
            existing = self._publisher.published_path(source_id, snapshot.generation)
            if existing is None:
                self._publisher._materialize_candidate(snapshot)
            self._checkpoint(
                principal_id,
                source_id,
                request_id,
                _STAGE_ASSEMBLE,
                input_digest,
                snapshot,
            )

        self._hook(_STAGE_VALIDATE)
        self._raise_if_cancelled(principal_id, source_id, request_id)
        self._validate(snapshot, source_id)
        return input_digest, snapshot

    def _enumerate(self, source_root: str | Path, source_id: str) -> list[dict[str, str]]:
        manifest = build_manifest(
            source_root,
            source_id,
            max_file_bytes=MAX_RAW_BYTES_PER_FILE,
            max_documents=MAX_DOCUMENTS_PER_SOURCE,
        )
        return [
            {
                "logical_uri": entry.logical_uri,
                "content_fingerprint": entry.content_fingerprint,
            }
            for entry in manifest.entries
            if entry.acceptance is ManifestAcceptance.ACCEPTED
        ]

    def _validate(self, snapshot: FullSnapshot, source_id: str) -> None:
        if snapshot.source_id != source_id:
            raise SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_VALIDATION_FAILED)
        ids = [document.document_id for document in snapshot.documents]
        uris = [document.logical_uri for document in snapshot.documents]
        if len(ids) != len(set(ids)) or len(uris) != len(set(uris)):
            raise SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_VALIDATION_FAILED)
        payload = snapshot.canonical_bytes()
        if b"source_root" in payload or b":\\\\" in payload or b"/home/" in payload:
            raise SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_VALIDATION_FAILED)

    def _publish(
        self,
        *,
        principal_id: str,
        source_id: str,
        request_id: str,
        correlation_id: str,
        actor_type: SourceActorType,
        snapshot: FullSnapshot,
        run: SyncRun,
    ) -> tuple[SourceRecord, SyncRun]:
        self._hook(_STAGE_PUBLISH)
        record = self._lifecycle.get_source(principal_id=principal_id, source_id=source_id)
        revision = None
        if snapshot.generation != record.published_generation:
            revision = SourceRevisionDraft(
                build_result="SUCCESS",
                source_fingerprint=snapshot.source_fingerprint,
                manifest_digest=snapshot.manifest_digest,
                parser_schema_version=PARSER_SCHEMA_VERSION,
                chunk_schema_version=CHUNK_SCHEMA_VERSION,
                generation=snapshot.generation,
                document_count=snapshot.document_count,
                chunk_count=snapshot.chunk_count,
                raw_bytes=snapshot.raw_bytes,
            )
        finished = replace(
            run,
            status=SYNC_RUN_SUCCESS,
            result_code=SYNC_RUN_SUCCESS,
            candidate_generation=snapshot.generation,
            document_count=snapshot.document_count,
            chunk_count=snapshot.chunk_count,
            raw_bytes=snapshot.raw_bytes,
            checkpoint_stage=_STAGE_PUBLISH,
        )
        try:
            return self._lifecycle.complete_sync_run(
                principal_id=principal_id,
                source_id=source_id,
                expected_version=record.record_version,
                actor_type=actor_type,
                correlation_id=correlation_id,
                run=finished,
                target_state=SourceLifecycleState.READY,
                revision=revision,
            )
        except SourceLifecycleException as exc:
            raise _translate(exc) from exc

    def _checkpoint(
        self,
        principal_id: str,
        source_id: str,
        request_id: str,
        stage: str,
        input_digest: str,
        snapshot: FullSnapshot | None,
    ) -> SyncRun:
        run = self._lifecycle.get_sync_run(
            principal_id=principal_id, source_id=source_id, request_id=request_id
        )
        record = self._lifecycle.get_source(principal_id=principal_id, source_id=source_id)
        updated = replace(
            run,
            checkpoint_stage=stage,
            input_digest=input_digest,
            candidate_generation=None if snapshot is None else snapshot.generation,
            checkpoint_digest=self._checkpoint_digest(stage, input_digest, snapshot, record),
            document_count=0 if snapshot is None else snapshot.document_count,
            chunk_count=0 if snapshot is None else snapshot.chunk_count,
            raw_bytes=0 if snapshot is None else snapshot.raw_bytes,
        )
        try:
            return self._lifecycle.update_sync_run(
                principal_id=principal_id, source_id=source_id, run=updated
            )
        except SourceLifecycleException as exc:
            raise _translate(exc) from exc

    def _checkpoint_digest(
        self,
        stage: str,
        input_digest: str,
        snapshot: FullSnapshot | None,
        record: SourceRecord,
    ) -> str:
        return hashlib.sha256(
            canonical_json(
                {
                    "stage": stage,
                    "input_digest": input_digest,
                    "candidate_generation": None if snapshot is None else snapshot.generation,
                    "record_version": record.record_version,
                }
            )
        ).hexdigest()

    def _retry(self, stage: str, operation: Callable):
        attempts = 0
        while True:
            try:
                self._inject(stage)
                return operation()
            except SourceSyncError:
                raise
            except Exception as exc:
                if not _is_retryable(exc) or attempts >= len(self._retry_delays):
                    if _is_retryable(exc) and attempts >= len(self._retry_delays):
                        raise SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_RETRY_EXHAUSTED) from exc
                    raise
                self._sleeper(self._retry_delays[attempts])
                attempts += 1

    def _inject(self, stage: str) -> None:
        pending = self.stage_faults.get(stage) or []
        if pending:
            raise pending.pop(0)

    def _hook(self, stage: str) -> None:
        hook = self.before_stage.get(stage)
        if hook is not None:
            hook()

    def _raise_if_cancelled(self, principal_id: str, source_id: str, request_id: str) -> None:
        if self._publishing:
            return
        run = self._lifecycle.get_sync_run(
            principal_id=principal_id, source_id=source_id, request_id=request_id
        )
        if run.cancel_requested:
            raise SourceSyncError(SourceSyncErrorCode.SOURCE_SYNC_CANCELLED)

    def _mark_interrupted(self, principal_id: str, source_id: str, request_id: str) -> None:
        run = self._lifecycle.get_sync_run(
            principal_id=principal_id, source_id=source_id, request_id=request_id
        )
        try:
            self._lifecycle.update_sync_run(
                principal_id=principal_id,
                source_id=source_id,
                run=replace(
                    run,
                    status=SYNC_RUN_INTERRUPTED_INPUT_CHANGED,
                    result_code=SourceSyncErrorCode.SOURCE_SYNC_INTERRUPTED.value,
                ),
            )
        except SourceLifecycleException:
            return

    def _fail(
        self,
        *,
        principal_id: str,
        source_id: str,
        request_id: str,
        correlation_id: str,
        actor_type: SourceActorType,
        code: SourceSyncErrorCode,
        status: str,
    ) -> None:
        try:
            record = self._lifecycle.get_source(principal_id=principal_id, source_id=source_id)
            run = self._lifecycle.get_sync_run(
                principal_id=principal_id, source_id=source_id, request_id=request_id
            )
            finished = replace(run, status=status, result_code=code.value)
            if record.state is SourceLifecycleState.SYNCING:
                self._lifecycle.complete_sync_run(
                    principal_id=principal_id,
                    source_id=source_id,
                    expected_version=record.record_version,
                    actor_type=actor_type,
                    correlation_id=correlation_id,
                    run=finished,
                    target_state=SourceLifecycleState.DEGRADED,
                )
            else:
                self._lifecycle.update_sync_run(
                    principal_id=principal_id, source_id=source_id, run=finished
                )
        except SourceLifecycleException:
            return


__all__ = [
    "SYNC_RETRY_DELAYS",
    "SYNC_SCHEMA_VERSION",
    "SourceSyncError",
    "SourceSyncErrorCode",
    "UserSourceSyncService",
]
