"""Source-local M7 FULL snapshot construction and atomic publication.

This module intentionally has no dependency on retrieval, Search, QA, preview, or
FastAPI.  Its published artifacts are control-plane-adjacent local files only.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from .normalized_document import (
    CHUNK_SCHEMA_VERSION,
    NormalizedDocument,
    NormalizedDocumentError,
    normalize_document,
)
from .parser_matrix import ParserMatrixError, parse_file
from .source_manifest import (
    ManifestAcceptance,
    SourceManifest,
    SourceManifestError,
    build_manifest,
    canonical_json,
)
from .source_registry import (
    SUCCESSFUL_BUILD_RESULT,
    SourceActorType,
    SourceLifecycleException,
    SourceLifecycleService,
    SourceLifecycleState,
    SourceRecord,
    SourceRevisionDraft,
)

PARSER_SCHEMA_VERSION = "sa.source.parser-matrix.v1"
SNAPSHOT_SCHEMA_VERSION = "sa.source.full-snapshot.v1"
MAX_DOCUMENTS_PER_SOURCE = 100
MAX_CHUNKS_PER_SOURCE = 1_000
MAX_RAW_BYTES_PER_SOURCE = 256 * 1024 * 1024
MAX_RAW_BYTES_PER_FILE = 32 * 1024 * 1024


class FullSnapshotErrorCode(StrEnum):
    SOURCE_NOT_READY = "SOURCE_FULL_SNAPSHOT_NOT_READY"
    SOURCE_LIMIT_EXCEEDED = "SOURCE_FULL_SNAPSHOT_LIMIT_EXCEEDED"
    BUILD_FAILED = "SOURCE_FULL_SNAPSHOT_BUILD_FAILED"
    PUBLICATION_FAILED = "SOURCE_FULL_SNAPSHOT_PUBLICATION_FAILED"


class FullSnapshotError(RuntimeError):
    """Stable, content-free source-local FULL snapshot failure."""

    def __init__(self, code: FullSnapshotErrorCode, message: str = "Source snapshot build failed.") -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class FullSnapshot:
    source_id: str
    generation: str
    manifest_digest: str
    source_fingerprint: str
    document_count: int
    chunk_count: int
    raw_bytes: int
    documents: tuple[NormalizedDocument, ...]

    def __post_init__(self) -> None:
        for digest in (self.manifest_digest, self.source_fingerprint):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise FullSnapshotError(FullSnapshotErrorCode.BUILD_FAILED)
        if not self.generation.startswith("m7-") or not all(
            char.isascii() and (char.isalnum() or char == "-") for char in self.generation
        ):
            raise FullSnapshotError(FullSnapshotErrorCode.BUILD_FAILED)
        if self.document_count != len(self.documents):
            raise FullSnapshotError(FullSnapshotErrorCode.BUILD_FAILED)
        chunks = tuple(chunk for document in self.documents for chunk in document.chunks())
        if self.chunk_count != len(chunks) or self.raw_bytes < 0:
            raise FullSnapshotError(FullSnapshotErrorCode.BUILD_FAILED)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_name": SNAPSHOT_SCHEMA_VERSION,
            "source_id": self.source_id,
            "generation": self.generation,
            "manifest_digest": self.manifest_digest,
            "source_fingerprint": self.source_fingerprint,
            "document_count": self.document_count,
            "chunk_count": self.chunk_count,
            "raw_bytes": self.raw_bytes,
            "documents": [document.to_dict() for document in self.documents],
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: object) -> "FullSnapshot":
        if not isinstance(payload, dict) or payload.get("schema_name") != SNAPSHOT_SCHEMA_VERSION:
            raise FullSnapshotError(FullSnapshotErrorCode.BUILD_FAILED)
        documents = tuple(
            NormalizedDocument.from_dict(item) for item in payload.get("documents") or ()
        )
        snapshot = cls(
            source_id=str(payload.get("source_id")),
            generation=str(payload.get("generation")),
            manifest_digest=str(payload.get("manifest_digest")),
            source_fingerprint=str(payload.get("source_fingerprint")),
            document_count=int(payload.get("document_count", -1)),
            chunk_count=int(payload.get("chunk_count", -1)),
            raw_bytes=int(payload.get("raw_bytes", -1)),
            documents=documents,
        )
        if snapshot.canonical_bytes() != canonical_json(payload):
            raise FullSnapshotError(FullSnapshotErrorCode.BUILD_FAILED)
        return snapshot


class UserSourceSnapshotPublisher:
    """Build and publish one registered source through the lifecycle service."""

    def __init__(self, cache_root: str | Path, lifecycle: SourceLifecycleService) -> None:
        self._root = Path(cache_root) / "user-source-snapshots" / "v1"
        self._lifecycle = lifecycle
        self._lock = threading.RLock()
        self._snapshot_cache: dict[tuple[str, str], tuple[str, FullSnapshot]] = {}

    def load_snapshot(self, source_id: str, generation: str | None = None) -> FullSnapshot | None:
        path = self.published_path(source_id, generation)
        if path is None:
            return None
        resolved = generation or path.name.removeprefix("gen-")
        try:
            digest = (path / "SHA256").read_text(encoding="ascii").strip()
        except OSError as exc:
            raise FullSnapshotError(FullSnapshotErrorCode.PUBLICATION_FAILED) from exc
        cache_key = (source_id, resolved)
        with self._lock:
            cached = self._snapshot_cache.get(cache_key)
            if cached is not None and cached[0] == digest:
                return cached[1]
        try:
            payload = json.loads((path / "snapshot.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FullSnapshotError(FullSnapshotErrorCode.PUBLICATION_FAILED) from exc
        snapshot = FullSnapshot.from_dict(payload)
        if hashlib.sha256(snapshot.canonical_bytes()).hexdigest() != digest:
            raise FullSnapshotError(FullSnapshotErrorCode.PUBLICATION_FAILED)
        with self._lock:
            self._snapshot_cache[cache_key] = (digest, snapshot)
        return snapshot

    def published_path(self, source_id: str, generation: str | None = None) -> Path | None:
        root = self._root / source_id
        if generation is None:
            generation_name = self._pointer_value(root / "CURRENT")
            if generation_name is None:
                return None
            path = root / generation_name
        else:
            path = root / f"gen-{generation}"
        return path if path.is_dir() else None

    def publish_full(
        self,
        *,
        principal_id: str,
        source_id: str,
        source_root: str | Path,
        correlation_id: str,
        actor_type: SourceActorType = SourceActorType.SERVICE,
    ) -> SourceRecord:
        """Build a complete candidate and publish its lifecycle revision.

        The registry revision is the publication authority.  A generation is first
        materialized without changing ``CURRENT``; only a committed READY revision
        may cause the convenience pointer to advance.  This prevents a failed CAS
        or registry transaction from exposing an uncommitted filesystem candidate.
        """
        with self._lock:
            record = self._lifecycle.get_source(principal_id=principal_id, source_id=source_id)
            if record.state not in {
                SourceLifecycleState.REGISTERED,
                SourceLifecycleState.READY,
                SourceLifecycleState.DEGRADED,
            }:
                raise FullSnapshotError(FullSnapshotErrorCode.SOURCE_NOT_READY)

            # A byte-for-byte repeat of the current immutable revision is a
            # successful idempotent FULL request, not another revision.  The
            # registry intentionally rejects duplicate (source, generation)
            # pairs, so preflight a READY source before entering SYNCING.
            candidate: FullSnapshot | None = None
            preflight_error: Exception | None = None
            if record.state is SourceLifecycleState.READY:
                try:
                    candidate = self._build_candidate(source_root, source_id)
                    if candidate.generation == record.published_generation:
                        self._materialize_candidate(candidate)
                        self._activate_generation(candidate)
                        return record
                except Exception as exc:
                    preflight_error = exc

            syncing = self._lifecycle.transition_source(
                principal_id=principal_id,
                source_id=source_id,
                expected_version=record.record_version,
                target_state=SourceLifecycleState.SYNCING,
                actor_type=actor_type,
                correlation_id=correlation_id,
            )
            try:
                if preflight_error is not None:
                    raise preflight_error
                candidate = candidate or self._build_candidate(source_root, source_id)
                self._materialize_candidate(candidate)
                ready = self._lifecycle.transition_source(
                    principal_id=principal_id,
                    source_id=source_id,
                    expected_version=syncing.record_version,
                    target_state=SourceLifecycleState.READY,
                    actor_type=actor_type,
                    correlation_id=correlation_id,
                    revision=SourceRevisionDraft(
                        build_result=SUCCESSFUL_BUILD_RESULT,
                        source_fingerprint=candidate.source_fingerprint,
                        manifest_digest=candidate.manifest_digest,
                        parser_schema_version=PARSER_SCHEMA_VERSION,
                        chunk_schema_version=CHUNK_SCHEMA_VERSION,
                        generation=candidate.generation,
                        document_count=candidate.document_count,
                        chunk_count=candidate.chunk_count,
                        raw_bytes=candidate.raw_bytes,
                    ),
                )
            except Exception as exc:
                self._degrade(
                    principal_id=principal_id,
                    source_id=source_id,
                    expected_version=syncing.record_version,
                    actor_type=actor_type,
                    correlation_id=correlation_id,
                )
                if isinstance(exc, FullSnapshotError):
                    raise
                if isinstance(exc, (SourceManifestError, ParserMatrixError, NormalizedDocumentError)):
                    raise FullSnapshotError(FullSnapshotErrorCode.BUILD_FAILED) from exc
                raise FullSnapshotError(
                    FullSnapshotErrorCode.PUBLICATION_FAILED,
                    "Source snapshot publication failed.",
                ) from exc

            # The registry revision remains authoritative, but a return from a
            # successful publication also guarantees that its local convenience
            # pointer was advanced.  A failure here is surfaced rather than
            # hidden; the immutable generation remains addressable by name.
            try:
                self._activate_generation(candidate)
            except (OSError, FullSnapshotError) as exc:
                raise FullSnapshotError(
                    FullSnapshotErrorCode.PUBLICATION_FAILED,
                    "Source snapshot publication failed.",
                ) from exc
            return ready

    def _degrade(
        self,
        *,
        principal_id: str,
        source_id: str,
        expected_version: int,
        actor_type: SourceActorType,
        correlation_id: str,
    ) -> None:
        try:
            self._lifecycle.transition_source(
                principal_id=principal_id,
                source_id=source_id,
                expected_version=expected_version,
                target_state=SourceLifecycleState.DEGRADED,
                actor_type=actor_type,
                correlation_id=correlation_id,
            )
        except SourceLifecycleException:
            pass

    def _build_candidate(
        self,
        source_root: str | Path,
        source_id: str,
        last_good: FullSnapshot | None = None,
    ) -> FullSnapshot:
        manifest = build_manifest(
            source_root,
            source_id,
            max_file_bytes=MAX_RAW_BYTES_PER_FILE,
            max_documents=MAX_DOCUMENTS_PER_SOURCE,
        )
        if manifest.accepted_bytes > MAX_RAW_BYTES_PER_SOURCE:
            raise FullSnapshotError(FullSnapshotErrorCode.SOURCE_LIMIT_EXCEEDED)
        previous = {
            document.logical_uri: document
            for document in (last_good.documents if last_good is not None else ())
        }
        documents: list[NormalizedDocument] = []
        for entry in manifest.entries:
            if entry.acceptance is not ManifestAcceptance.ACCEPTED:
                continue
            reused = previous.get(entry.logical_uri)
            if (
                reused is not None
                and reused.content_fingerprint == entry.content_fingerprint
            ):
                documents.append(reused)
                continue
            path = Path(source_root) / Path(entry.logical_uri)
            parsed = parse_file(path, entry.format, max_bytes=MAX_RAW_BYTES_PER_FILE)
            document = normalize_document(
                parsed,
                source_id=source_id,
                document_id=entry.document_id,
                logical_uri=entry.logical_uri,
                format=entry.format or "",
                content_fingerprint=entry.content_fingerprint,
                parser_id=parsed.parser_id,
                parser_version=parsed.parser_version,
            )
            documents.append(document)
        documents.sort(key=lambda document: (document.logical_uri.casefold(), document.logical_uri))
        chunks = tuple(chunk for document in documents for chunk in document.chunks())
        if len(documents) > MAX_DOCUMENTS_PER_SOURCE or len(chunks) > MAX_CHUNKS_PER_SOURCE:
            raise FullSnapshotError(FullSnapshotErrorCode.SOURCE_LIMIT_EXCEEDED)
        source_fingerprint = hashlib.sha256(
            canonical_json(
                {
                    "documents": [
                        {
                            "logical_uri": document.logical_uri,
                            "content_fingerprint": document.content_fingerprint,
                            "normalized_text_digest": document.normalized_text_digest,
                        }
                        for document in documents
                    ]
                }
            )
        ).hexdigest()
        generation = f"m7-{source_fingerprint[:24]}"
        return FullSnapshot(
            source_id=source_id,
            generation=generation,
            manifest_digest=manifest.manifest_digest,
            source_fingerprint=source_fingerprint,
            document_count=len(documents),
            chunk_count=len(chunks),
            raw_bytes=manifest.accepted_bytes,
            documents=tuple(documents),
        )

    def _publish_candidate(self, snapshot: FullSnapshot) -> None:
        """Compatibility wrapper that materializes and activates a candidate."""
        self._materialize_candidate(snapshot)
        self._activate_generation(snapshot)

    def _materialize_candidate(self, snapshot: FullSnapshot) -> None:
        """Durably write a generation without making it the current snapshot."""
        root = self._root / snapshot.source_id
        root.mkdir(parents=True, exist_ok=True)
        staging = root / f".staging-{uuid4().hex}"
        generation = root / f"gen-{snapshot.generation}"
        try:
            staging.mkdir()
            payload = snapshot.canonical_bytes()
            self._write_fsynced(staging / "snapshot.json", payload)
            self._write_fsynced(staging / "SHA256", hashlib.sha256(payload).hexdigest().encode("ascii") + b"\n")
            self._fsync_directory(staging)
            if generation.exists():
                if not self._is_valid_generation(generation, payload):
                    raise FullSnapshotError(FullSnapshotErrorCode.PUBLICATION_FAILED)
                self._discard_staging(staging)
            else:
                os.replace(staging, generation)
                self._fsync_directory(root)
        except Exception:
            self._discard_staging(staging)
            raise

    def _activate_generation(self, snapshot: FullSnapshot) -> None:
        """Advance non-authoritative convenience pointers after READY commits."""
        root = self._root / snapshot.source_id
        generation = root / f"gen-{snapshot.generation}"
        payload = snapshot.canonical_bytes()
        if not self._is_valid_generation(generation, payload):
            raise FullSnapshotError(FullSnapshotErrorCode.PUBLICATION_FAILED)
        previous = self._pointer_value(root / "CURRENT")
        if previous is not None and previous != generation.name:
            self._switch_pointer(root / "PREVIOUS", previous)
        self._switch_pointer(root / "CURRENT", generation.name)
        self._cleanup(root, generation.name)

    @staticmethod
    def _discard_staging(staging: Path) -> None:
        if staging.is_dir() and staging.name.startswith(".staging-"):
            shutil.rmtree(staging, ignore_errors=True)

    @staticmethod
    def _is_valid_generation(path: Path, expected: bytes) -> bool:
        try:
            payload = (path / "snapshot.json").read_bytes()
            digest = (path / "SHA256").read_text(encoding="ascii").strip()
        except OSError:
            return False
        return payload == expected and hashlib.sha256(payload).hexdigest() == digest

    def _switch_pointer(self, path: Path, value: str) -> None:
        temporary = path.with_name(f".{path.name}-{uuid4().hex}")
        self._write_fsynced(temporary, f"{value}\n".encode("ascii"))
        os.replace(temporary, path)
        self._fsync_directory(path.parent)

    @staticmethod
    def _pointer_value(path: Path) -> str | None:
        try:
            value = path.read_text(encoding="ascii").strip()
        except OSError:
            return None
        return value if value.startswith("gen-m7-") else None

    @staticmethod
    def _write_fsynced(path: Path, payload: bytes) -> None:
        with path.open("wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        if os.name == "nt":
            return
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _cleanup(root: Path, current: str) -> None:
        # Stale generation collection is intentionally deferred to a separately
        # authorized lifecycle cleanup path.  FULL publication itself must only
        # add/switch artifacts and leave a last-good candidate intact.
        del root, current


__all__ = [
    "PARSER_SCHEMA_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "MAX_DOCUMENTS_PER_SOURCE",
    "MAX_CHUNKS_PER_SOURCE",
    "MAX_RAW_BYTES_PER_SOURCE",
    "MAX_RAW_BYTES_PER_FILE",
    "FullSnapshotErrorCode",
    "FullSnapshotError",
    "FullSnapshot",
    "UserSourceSnapshotPublisher",
]
