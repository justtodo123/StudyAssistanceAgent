"""Source-local M7 offline fail-closed validation and explicit FULL repair.

This module does not start Search/QA/preview, does not auto-repair on query, and
does not create study-session or review-log state.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from . import config
from .fts5_tokenizer import (
    Fts5TokenizerError,
    Fts5TokenizerErrorCode,
    fts5_match_query,
    require_jieba,
)
from .source_delete import UserSourceDeleteService
from .source_operation_lock import operation_lock
from .source_isolation import (
    IsolationSnapshot,
    SourceIsolationError,
    SourceIsolationErrorCode,
    SourceIsolationGate,
    is_user_source_id,
)
from .source_registry import SourceActorType, SourceLifecycleService, SourceLifecycleState, SourceRecord
from .user_source_fts5 import (
    Fts5Hit,
    Fts5IndexError,
    Fts5IndexErrorCode,
    Fts5IndexMetadata,
    VECTOR_STATUS_ATTACHED,
    UserSourceFts5Index,
    identity_set_digest,
)
from .user_source_snapshot import FullSnapshot, FullSnapshotError, UserSourceSnapshotPublisher
from .user_source_vector import (
    UserSourceVectorIndex,
    VectorIndexError,
    VectorIndexErrorCode,
    VectorIndexMetadata,
    VectorHit,
)


OFFLINE_SCHEMA_VERSION = "sa.source.offline-fallback.v1"


class SourceOfflineErrorCode(StrEnum):
    DEPENDENCY_UNAVAILABLE = "SOURCE_OFFLINE_DEPENDENCY_UNAVAILABLE"
    INDEX_INVALID = "SOURCE_OFFLINE_INDEX_INVALID"
    SOURCE_UNAVAILABLE = "SOURCE_OFFLINE_SOURCE_UNAVAILABLE"
    REPAIR_REQUIRED = "SOURCE_OFFLINE_REPAIR_REQUIRED"


_ERROR_MESSAGES: Mapping[SourceOfflineErrorCode, str] = MappingProxyType(
    {
        SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE: "A required source dependency is unavailable.",
        SourceOfflineErrorCode.INDEX_INVALID: "The source index is invalid.",
        SourceOfflineErrorCode.SOURCE_UNAVAILABLE: "The user source is unavailable.",
        SourceOfflineErrorCode.REPAIR_REQUIRED: "The source index requires an explicit FULL repair.",
    }
)


class SourceOfflineError(RuntimeError):
    """Stable, content-free offline rejection with a local repair category."""

    def __init__(self, code: SourceOfflineErrorCode, *, source_id: str | None = None) -> None:
        self.code = code
        self.source_id = source_id
        self.repair_category = {
            SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE: "repair-local-dependency",
            SourceOfflineErrorCode.INDEX_INVALID: "rebuild-source-index-full",
            SourceOfflineErrorCode.SOURCE_UNAVAILABLE: "repair-source-input",
            SourceOfflineErrorCode.REPAIR_REQUIRED: "rebuild-source-index-full",
        }[code]
        super().__init__(_ERROR_MESSAGES[code])

    def public_dict(self) -> dict[str, str]:
        payload = {"error": self.code.value, "repair": self.repair_category}
        if self.source_id is not None:
            payload["source_id"] = self.source_id
        return payload


@dataclass(frozen=True, slots=True)
class ValidatedSourceIndex:
    source_id: str
    generation: str
    metadata: Fts5IndexMetadata
    vector_metadata: VectorIndexMetadata | None
    snapshot: FullSnapshot


class UserSourceOfflineGuard:
    """Validate M7 user-source indexes without fallback or silent repair."""

    def __init__(
        self,
        cache_root: str | Path,
        lifecycle: SourceLifecycleService,
        *,
        snapshot_publisher: UserSourceSnapshotPublisher | None = None,
        fts5: UserSourceFts5Index | None = None,
        vector: UserSourceVectorIndex | None = None,
        vector_embedder: object | None = None,
        delete_service: UserSourceDeleteService | None = None,
        isolation: SourceIsolationGate | None = None,
    ) -> None:
        self._root = Path(cache_root)
        self._operation_lock = operation_lock(self._root)
        self._lifecycle = lifecycle
        self._snapshots = snapshot_publisher or UserSourceSnapshotPublisher(self._root, lifecycle)
        self._fts5 = fts5 or UserSourceFts5Index(self._root)
        self._vector = vector or UserSourceVectorIndex(self._root, embedder=vector_embedder)
        self._delete = delete_service or UserSourceDeleteService(
            self._root,
            lifecycle,
            publisher=self._snapshots,
        )
        self._delete.attach_index_runtimes(self._fts5, self._vector)
        self._isolation = isolation or SourceIsolationGate(lifecycle, self._delete)

    def validate_for_query(
        self,
        *,
        principal_id: str,
        source_id: str,
        isolation_snapshot: IsolationSnapshot | None = None,
        use_vector: bool = True,
    ) -> ValidatedSourceIndex:
        if isolation_snapshot is None:
            self._isolation.require_source(principal_id, source_id)
        else:
            if isolation_snapshot.principal_id != principal_id:
                raise SourceIsolationError(
                    SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                    "Source isolation is unavailable.",
                )
            if not is_user_source_id(source_id) or source_id not in isolation_snapshot.authorized_source_ids:
                raise SourceIsolationError(SourceIsolationErrorCode.SOURCE_NOT_FOUND, "The Source was not found.")
            if self._delete.is_blocked(source_id):
                raise SourceIsolationError(SourceIsolationErrorCode.SOURCE_NOT_FOUND, "The Source was not found.")
        try:
            require_jieba()
        except Fts5TokenizerError as exc:
            raise self._map_tokenizer(exc, source_id) from exc
        if not use_vector:
            vector_metadata = None
        else:
            try:
                self._vector.require_runtime()
            except VectorIndexError as exc:
                raise self._map_vector(exc, source_id) from exc
            vector_metadata = None
        try:
            record = self._lifecycle.get_source(principal_id=principal_id, source_id=source_id)
        except Exception as exc:
            raise SourceOfflineError(SourceOfflineErrorCode.SOURCE_UNAVAILABLE, source_id=source_id) from exc
        if record.published_generation is None or record.state not in {
            SourceLifecycleState.READY,
            SourceLifecycleState.DEGRADED,
        }:
            raise SourceOfflineError(SourceOfflineErrorCode.SOURCE_UNAVAILABLE, source_id=source_id)
        try:
            snapshot = self._snapshots.load_snapshot(source_id, record.published_generation)
        except FullSnapshotError as exc:
            raise SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id) from exc
        if snapshot is None:
            raise SourceOfflineError(SourceOfflineErrorCode.REPAIR_REQUIRED, source_id=source_id)
        try:
            metadata = self._fts5.validate(source_id, record.published_generation, snapshot)
            if use_vector:
                if metadata.vector_status != VECTOR_STATUS_ATTACHED:
                    raise SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)
                vector_metadata = self._vector.validate(
                    source_id,
                    record.published_generation,
                    snapshot,
                    revision_no=record.published_revision_no,
                )
        except Fts5TokenizerError as exc:
            raise self._map_tokenizer(exc, source_id) from exc
        except Fts5IndexError as exc:
            raise self._map_index(exc, source_id) from exc
        except VectorIndexError as exc:
            raise self._map_vector(exc, source_id) from exc
        snapshot_chunk_ids = {chunk.chunk_id for document in snapshot.documents for chunk in document.chunks()}
        if use_vector:
            assert vector_metadata is not None
            if (
                vector_metadata.identity_set_digest != metadata.identity_set_digest
                or metadata.vector_identity_set_digest != metadata.identity_set_digest
                or vector_metadata.source_id != metadata.source_id
                or vector_metadata.generation != metadata.generation
                or vector_metadata.snapshot_fingerprint != metadata.snapshot_fingerprint
                or len(snapshot_chunk_ids) != metadata.chunk_count
                or len(snapshot_chunk_ids) != vector_metadata.chunk_count
            ):
                raise SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)
        elif len(snapshot_chunk_ids) != metadata.chunk_count:
            raise SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)
        return ValidatedSourceIndex(
            source_id=source_id,
            generation=record.published_generation,
            metadata=metadata,
            vector_metadata=vector_metadata,
            snapshot=snapshot,
        )

    def encode_query(self, query: str, *, source_id: str = "") -> list[float]:
        try:
            return self._vector.encode_query(query)
        except VectorIndexError as exc:
            raise self._map_vector(exc, source_id) from exc

    def search(
        self,
        *,
        principal_id: str,
        source_id: str,
        query: str,
        top_k: int = 5,
        isolation_snapshot: IsolationSnapshot | None = None,
        query_vector: list[float] | None = None,
        use_vector: bool = True,
        validated_index: ValidatedSourceIndex | None = None,
    ) -> tuple[Fts5Hit, ...]:
        validated = validated_index or self.validate_for_query(
            principal_id=principal_id,
            source_id=source_id,
            isolation_snapshot=isolation_snapshot,
            use_vector=use_vector,
        )
        if validated.source_id != source_id:
            raise SourceIsolationError(
                SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                "Source isolation is unavailable.",
            )
        try:
            match = fts5_match_query(query)
            fts_hits = self._fts5.search(
                validated.source_id,
                validated.generation,
                query,
                top_k=top_k,
                match=match,
            )
            if use_vector:
                vector_hits = self._vector.search(
                    validated.source_id,
                    validated.generation,
                    query,
                    top_k=top_k,
                    query_vector=query_vector,
                )
                results = _rrf_hits(fts_hits, vector_hits, top_k)
            else:
                results = fts_hits[: max(int(top_k), 0)]
            with self._operation_lock:
                current = self.validate_for_query(
                    principal_id=principal_id,
                    source_id=source_id,
                    isolation_snapshot=None,
                    use_vector=use_vector,
                )
                if (
                    current.generation != validated.generation
                    or current.metadata.snapshot_fingerprint
                        != validated.metadata.snapshot_fingerprint
                    or current.metadata.identity_set_digest != validated.metadata.identity_set_digest
                    or (
                        use_vector
                        and current.vector_metadata != validated.vector_metadata
                    )
                ):
                    raise SourceIsolationError(
                        SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                        "Source isolation is unavailable.",
                    )
                return tuple(results)
        except Fts5TokenizerError as exc:
            raise self._map_tokenizer(exc, source_id) from exc
        except Fts5IndexError as exc:
            raise self._map_index(exc, source_id) from exc
        except VectorIndexError as exc:
            raise self._map_vector(exc, source_id) from exc

    def repair_full(
        self,
        *,
        principal_id: str,
        source_id: str,
        source_root: str | Path,
        correlation_id: str,
        actor_type: SourceActorType = SourceActorType.USER,
    ) -> SourceRecord:
        self._isolation.require_source(principal_id, source_id)
        try:
            require_jieba()
        except Fts5TokenizerError as exc:
            raise self._map_tokenizer(exc, source_id) from exc
        try:
            self._vector.require_runtime()
        except VectorIndexError as exc:
            raise self._map_vector(exc, source_id) from exc
        try:
            return self._snapshots.publish_full(
                principal_id=principal_id,
                source_id=source_id,
                source_root=source_root,
                correlation_id=correlation_id,
                actor_type=actor_type,
                prepare_revision=self._prepare_revision_indexes,
                activate_revision=self._activate_revision_indexes,
            )
        except FullSnapshotError as exc:
            raise SourceOfflineError(SourceOfflineErrorCode.SOURCE_UNAVAILABLE, source_id=source_id) from exc
        except Fts5TokenizerError as exc:
            raise self._map_tokenizer(exc, source_id) from exc
        except Fts5IndexError as exc:
            raise self._map_index(exc, source_id) from exc
        except VectorIndexError as exc:
            raise self._map_vector(exc, source_id) from exc
        except SourceOfflineError:
            raise
        except Exception as exc:
            raise SourceOfflineError(SourceOfflineErrorCode.REPAIR_REQUIRED, source_id=source_id) from exc

    def prepare_revision_indexes(self, snapshot: FullSnapshot, revision_no: int) -> None:
        """Materialize and validate mandatory indexes before authority commits."""
        self._prepare_revision_indexes(snapshot, revision_no)

    def activate_revision_indexes(self, snapshot: FullSnapshot, revision_no: int) -> None:
        """Advance mandatory index convenience pointers after authority commits."""
        self._activate_revision_indexes(snapshot, revision_no)

    def _prepare_revision_indexes(self, snapshot: FullSnapshot, revision_no: int) -> None:
        digest = identity_set_digest(snapshot)
        self._fts5.build(
            snapshot,
            activate=False,
            vector_status=VECTOR_STATUS_ATTACHED,
            vector_identity_set_digest=digest,
            repair_invalid=True,
        )
        self._vector.build(
            snapshot,
            revision_no=revision_no,
            activate=False,
            repair_invalid=True,
        )
        self._fts5.validate(snapshot.source_id, snapshot.generation, snapshot)
        self._vector.validate(
            snapshot.source_id,
            snapshot.generation,
            snapshot,
            revision_no=revision_no,
        )

    def _activate_revision_indexes(self, snapshot: FullSnapshot, revision_no: int) -> None:
        self._fts5.validate(snapshot.source_id, snapshot.generation, snapshot)
        self._vector.validate(
            snapshot.source_id,
            snapshot.generation,
            snapshot,
            revision_no=revision_no,
        )
        self._fts5.activate(snapshot.source_id, snapshot.generation)
        self._vector.activate(snapshot.source_id, snapshot.generation)

    @staticmethod
    def _map_tokenizer(exc: Fts5TokenizerError, source_id: str) -> Exception:
        if exc.code is Fts5TokenizerErrorCode.UNAVAILABLE:
            return SourceOfflineError(SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE, source_id=source_id)
        if exc.code is Fts5TokenizerErrorCode.INVALID_QUERY:
            return exc
        if exc.code in {Fts5TokenizerErrorCode.MISMATCH, Fts5TokenizerErrorCode.UNSUPPORTED}:
            return SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)
        return SourceOfflineError(SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE, source_id=source_id)

    @staticmethod
    def _map_index(exc: Fts5IndexError, source_id: str) -> SourceOfflineError:
        if exc.code is Fts5IndexErrorCode.REPAIR_REQUIRED:
            return SourceOfflineError(SourceOfflineErrorCode.REPAIR_REQUIRED, source_id=source_id)
        return SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)

    @staticmethod
    def _map_vector(exc: VectorIndexError, source_id: str) -> SourceOfflineError:
        if exc.code is VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE:
            return SourceOfflineError(SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE, source_id=source_id)
        if exc.code is VectorIndexErrorCode.REPAIR_REQUIRED:
            return SourceOfflineError(SourceOfflineErrorCode.REPAIR_REQUIRED, source_id=source_id)
        return SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)


def _rrf_hits(fts_hits: tuple[Fts5Hit, ...], vector_hits: tuple[VectorHit, ...], top_k: int) -> tuple[Fts5Hit, ...]:
    scores: dict[str, float] = {}
    by_id: dict[str, Fts5Hit] = {}
    for rank, hit in enumerate(fts_hits):
        by_id.setdefault(hit.chunk_id, hit)
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (config.RRF_K + rank + 1)
    for rank, hit in enumerate(vector_hits):
        by_id.setdefault(
            hit.chunk_id,
            Fts5Hit(
                source_id=hit.source_id,
                document_id=hit.document_id,
                chunk_id=hit.chunk_id,
                generation=hit.generation,
                rank=hit.rank,
            ),
        )
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (config.RRF_K + rank + 1)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[: max(int(top_k), 0)]
    fused: list[Fts5Hit] = []
    for rank, (chunk_id, _score) in enumerate(ranked, start=1):
        hit = by_id[chunk_id]
        fused.append(
            Fts5Hit(
                source_id=hit.source_id,
                document_id=hit.document_id,
                chunk_id=hit.chunk_id,
                generation=hit.generation,
                rank=rank,
            )
        )
    return tuple(fused)


__all__ = [
    "OFFLINE_SCHEMA_VERSION",
    "SourceOfflineErrorCode",
    "SourceOfflineError",
    "ValidatedSourceIndex",
    "UserSourceOfflineGuard",
]
