"""Owner-filtered M7 user-source search path.

Isolation runs before FTS5 and vector. Results are generation-bound, provenance-checked,
and cached by auth digest. This module does not mutate default-pack BM25,
Quiz, Review Plan, study-sessions, or M6b preview retrieve.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Iterable, Mapping

from . import config
from .fts5_tokenizer import Fts5TokenizerError, fts5_match_query
from .models import RetrievalChunk
from .source_delete import UserSourceDeleteService
from .source_operation_lock import operation_lock
from .source_isolation import (
    IsolationSnapshot,
    RetrievalHit,
    SourceIsolationError,
    SourceIsolationErrorCode,
    SourceIsolationGate,
)
from .source_offline import (
    SourceOfflineError,
    SourceOfflineErrorCode,
    UserSourceOfflineGuard,
    ValidatedSourceIndex,
)
from .source_registry import SourceLifecycleService, SqliteSourceRegistry
from .user_source_fts5 import Fts5Hit, UserSourceFts5Index
from .user_source_vector import UserSourceVectorIndex
from .user_source_snapshot import UserSourceSnapshotPublisher


PROVENANCE_SCHEMA = "sa.source.provenance.v1"
RESULT_CACHE_SCHEMA = "sa.source.result-cache.v1"
USER_PROVENANCE_SCHEME = "user"


def _contains_host_path(value: str) -> bool:
    if "\\" in value or re.match(r"^[A-Za-z]:/", value):
        return True
    remainder = value[len(USER_PROVENANCE_SCHEME) + 3 :] if value.startswith(f"{USER_PROVENANCE_SCHEME}://") else value
    return remainder.startswith("/") or "/Users/" in remainder or "/home/" in remainder


_USER_SOURCE_RE = re.compile(
    r"^user-[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def public_uri(source_id: str, logical_uri: str) -> str:
    return f"{USER_PROVENANCE_SCHEME}://{source_id}/{logical_uri}"


def _canonical_json(payload: Mapping[str, object] | list[object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class UserSourceProvenance:
    source_id: str
    document_id: str
    chunk_id: str
    logical_uri: str
    generation: str
    origin_kind: str
    public_uri: str
    schema: str = PROVENANCE_SCHEMA

    def validate(self) -> None:
        expected = public_uri(self.source_id, self.logical_uri)
        if (
            self.schema != PROVENANCE_SCHEMA
            or self.public_uri != expected
            or not _USER_SOURCE_RE.fullmatch(self.source_id)
            or not self.logical_uri
            or ".." in self.logical_uri.split("/")
            or self.logical_uri.startswith("/")
            or _contains_host_path(self.public_uri)
            or "\\" in self.public_uri
        ):
            raise SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=self.source_id)


@dataclass(frozen=True, slots=True)
class UserSourceSearchResult:
    chunks: tuple[RetrievalChunk, ...]
    provenance: tuple[UserSourceProvenance, ...]
    mode: str
    auth_digest: str
    generation_digest: str
    cache_hit: bool = False
    publication_contracts: tuple[ValidatedSourceIndex, ...] = ()

    @classmethod
    def empty(cls, *, auth_digest: str = "", generation_digest: str = "") -> "UserSourceSearchResult":
        return cls(
            chunks=(),
            provenance=(),
            mode="fts5",
            auth_digest=auth_digest,
            generation_digest=generation_digest,
            cache_hit=False,
        )


class UserSourceSearchService:
    """Hybrid FTS5+vector search over authorized published user sources."""

    def __init__(
        self,
        cache_root: str | Path,
        lifecycle: SourceLifecycleService,
        *,
        snapshot_publisher: UserSourceSnapshotPublisher | None = None,
        offline: UserSourceOfflineGuard | None = None,
        delete_service: UserSourceDeleteService | None = None,
        isolation: SourceIsolationGate | None = None,
        vector_embedder: object | None = None,
        cache_capacity: int = 128,
    ) -> None:
        self._root = Path(cache_root)
        self._operation_lock = operation_lock(self._root)
        self._lifecycle = lifecycle
        self._snapshots = snapshot_publisher or UserSourceSnapshotPublisher(
            self._root,
            lifecycle,
        )
        if offline is None:
            fts5 = UserSourceFts5Index(self._root)
            vector = UserSourceVectorIndex(
                self._root,
                embedder=vector_embedder,
            )
            self._delete = delete_service or UserSourceDeleteService(
                self._root,
                lifecycle,
                publisher=self._snapshots,
            )
            self._delete.attach_index_runtimes(fts5, vector)
            self._isolation = isolation or SourceIsolationGate(
                lifecycle,
                self._delete,
            )
            self._offline = UserSourceOfflineGuard(
                self._root,
                lifecycle,
                snapshot_publisher=self._snapshots,
                fts5=fts5,
                vector=vector,
                delete_service=self._delete,
                isolation=self._isolation,
            )
        else:
            if delete_service is not None and delete_service is not offline._delete:
                raise ValueError(
                    "offline and delete_service must share one delete service"
                )
            if isolation is not None and isolation is not offline._isolation:
                raise ValueError(
                    "offline and isolation must share one isolation gate"
                )
            self._offline = offline
            self._delete = offline._delete
            self._isolation = offline._isolation
        self._cache: OrderedDict[
            tuple[str, str, str, int, str | None, bool],
            UserSourceSearchResult,
        ] = OrderedDict()
        self._cache_capacity = cache_capacity
        self._lock = RLock()
        self._delete.attach_runtime(self)

    def clear_source(self, source_id: str) -> None:
        """Forget cached result bodies for one source."""
        with self._lock:
            for key, result in tuple(self._cache.items()):
                if any(item.source_id == source_id for item in result.provenance):
                    self._cache.pop(key, None)

    def search(
        self,
        *,
        principal_id: str,
        query: str,
        top_k: int = 5,
        source_id: str | None = None,
        use_vector: bool = True,
    ) -> UserSourceSearchResult:
        snapshot = self._isolation.capture_snapshot(principal_id)
        if source_id is not None:
            self._isolation.require_source(principal_id, source_id)
            source_ids = (source_id,)
        else:
            source_ids = tuple(sorted(snapshot.authorized_source_ids))
        normalized_top_k = max(int(top_k), 0)
        generation_digest = _generation_digest(snapshot, source_ids)
        cache_key = (
            snapshot.auth_digest, generation_digest, query, normalized_top_k,
            source_id, bool(use_vector),
        )
        with self._lock:
            cached = self._cache.get(cache_key)
        if cached is not None:
            current = self._isolation.capture_stable_snapshot(principal_id)
            current_source_ids = ((source_id,) if source_id is not None else tuple(sorted(current.authorized_source_ids)))
            current_generation_digest = _generation_digest(current, current_source_ids)
            if (
                current.auth_digest == snapshot.auth_digest
                and current_generation_digest == generation_digest
                and (source_id is None or source_id in current.authorized_source_ids)
                and not any(self._delete.is_blocked(item) for item in current_source_ids)
            ):
                with self._operation_lock:
                    gated = self._isolation.capture_stable_snapshot(principal_id)
                    gated_source_ids = (
                        (source_id,)
                        if source_id is not None
                        else tuple(sorted(gated.authorized_source_ids))
                    )
                    if (
                        gated.auth_digest != snapshot.auth_digest
                        or _generation_digest(gated, gated_source_ids) != generation_digest
                        or (
                            source_id is not None
                            and source_id not in gated.authorized_source_ids
                        )
                        or any(self._delete.is_blocked(item) for item in gated_source_ids)
                    ):
                        raise SourceIsolationError(
                            SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                            "Source isolation is unavailable.",
                        )
                    expected_contracts = {
                        contract.source_id: contract
                        for contract in cached.publication_contracts
                    }
                    if set(expected_contracts) != {
                        item
                        for item in gated_source_ids
                        if gated.published_generations.get(item)
                    }:
                        raise SourceIsolationError(
                            SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                            "Source isolation is unavailable.",
                        )
                    for current_source, expected in expected_contracts.items():
                        current_contract = self._offline.validate_for_query(
                            principal_id=principal_id,
                            source_id=current_source,
                            isolation_snapshot=gated,
                            use_vector=use_vector,
                        )
                        if not _same_publication_contract(
                            current_contract,
                            expected,
                            use_vector=use_vector,
                        ):
                            raise SourceIsolationError(
                                SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                                "Source isolation is unavailable.",
                            )
                    with self._lock:
                        self._cache.move_to_end(cache_key)
                        cached = self._cache[cache_key]
                        return UserSourceSearchResult(
                            chunks=tuple(chunk.model_copy(deep=True) for chunk in cached.chunks),
                            provenance=cached.provenance,
                            mode=cached.mode,
                            auth_digest=cached.auth_digest,
                            generation_digest=cached.generation_digest,
                            cache_hit=True,
                            publication_contracts=cached.publication_contracts,
                        )
            if source_id is not None and source_id not in current.authorized_source_ids:
                raise SourceIsolationError(SourceIsolationErrorCode.SOURCE_NOT_FOUND, "The Source was not found.")
            snapshot = current
            source_ids = ((source_id,) if source_id is not None else tuple(sorted(snapshot.authorized_source_ids)))
            generation_digest = _generation_digest(snapshot, source_ids)
            cache_key = (snapshot.auth_digest, generation_digest, query, normalized_top_k, source_id, bool(use_vector))
        routes: list[list[RetrievalChunk]] = []
        provenance_by_chunk: dict[str, UserSourceProvenance] = {}
        published_ids = tuple(current for current in source_ids if snapshot.published_generations.get(current))
        if normalized_top_k == 0:
            return UserSourceSearchResult.empty(auth_digest=snapshot.auth_digest, generation_digest=generation_digest)
        if published_ids:
            fts5_match_query(query)
        validated_indexes = tuple(
            self._offline.validate_for_query(
                principal_id=principal_id,
                source_id=current_source,
                isolation_snapshot=snapshot,
                use_vector=use_vector,
            )
            for current_source in published_ids
        )
        validated_by_source = {
            item.source_id: item
            for item in validated_indexes
        }
        contracts = {
            (
                item.vector_metadata.schema_name,
                item.vector_metadata.offline_schema,
                item.vector_metadata.embedding_model,
                item.vector_metadata.embedding_version,
                item.vector_metadata.embedding_dim,
                item.vector_metadata.embedding_normalize,
                item.vector_metadata.chunk_schema_version,
                item.vector_metadata.vector_index_type,
            )
            for item in validated_indexes if item.vector_metadata is not None
        }
        if use_vector and len(contracts) > 1:
            raise SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)
        query_vector = (
            self._offline.encode_query(query, source_id=published_ids[0])
            if use_vector and published_ids else None
        )
        for current_source in source_ids:
            published = snapshot.published_generations.get(current_source)
            if not published:
                if source_id is not None:
                    raise SourceOfflineError(SourceOfflineErrorCode.SOURCE_UNAVAILABLE, source_id=current_source)
                continue
            hits = self._offline.search(
                principal_id=principal_id,
                source_id=current_source,
                query=query,
                top_k=max(normalized_top_k, 20),
                isolation_snapshot=snapshot,
                query_vector=query_vector,
                use_vector=use_vector,
                validated_index=validated_by_source[current_source],
            )
            filtered = self._isolation.filter_hits(
                principal_id,
                _hits_to_retrieval(hits, snapshot.auth_digest),
                snapshot=snapshot,
            )
            chunks, provenances = self._hydrate(current_source, published, filtered)
            if chunks:
                routes.append(chunks)
                for item in provenances:
                    provenance_by_chunk[item.chunk_id] = item
        fused = _rrf_fuse(routes, normalized_top_k, query=query)
        provenance = tuple(provenance_by_chunk[chunk.id] for chunk in fused)
        if len(provenance) != len(fused):
            raise SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)
        for item in provenance:
            item.validate()
        final_snapshot = self._isolation.capture_stable_snapshot(principal_id)
        final_source_ids = ((source_id,) if source_id is not None else tuple(sorted(final_snapshot.authorized_source_ids)))
        final_generation_digest = _generation_digest(final_snapshot, final_source_ids)
        if (
            final_snapshot.auth_digest != snapshot.auth_digest
            or final_generation_digest != generation_digest
            or (source_id is not None and source_id not in final_snapshot.authorized_source_ids)
            or any(self._delete.is_blocked(item) for item in final_source_ids)
        ):
            raise SourceIsolationError(SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE, "Source isolation is unavailable.")
        stored = UserSourceSearchResult(
            chunks=tuple(chunk.model_copy(deep=True) for chunk in fused),
            provenance=provenance,
            mode="hybrid" if use_vector else "keyword-only",
            auth_digest=snapshot.auth_digest,
            generation_digest=generation_digest,
            cache_hit=False,
            publication_contracts=tuple(validated_indexes),
        )
        with self._operation_lock:
            final_snapshot = self._isolation.capture_stable_snapshot(principal_id)
            final_source_ids = ((source_id,) if source_id is not None else tuple(sorted(final_snapshot.authorized_source_ids)))
            if (
                final_snapshot.auth_digest != snapshot.auth_digest
                or _generation_digest(final_snapshot, final_source_ids) != generation_digest
                or (source_id is not None and source_id not in final_snapshot.authorized_source_ids)
                or any(self._delete.is_blocked(item) for item in final_source_ids)
            ):
                raise SourceIsolationError(SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE, "Source isolation is unavailable.")
            expected_contracts = {
                contract.source_id: contract
                for contract in stored.publication_contracts
            }
            if set(expected_contracts) != {
                item
                for item in final_source_ids
                if final_snapshot.published_generations.get(item)
            }:
                raise SourceIsolationError(
                    SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                    "Source isolation is unavailable.",
                )
            for current_source, expected in expected_contracts.items():
                current_contract = self._offline.validate_for_query(
                    principal_id=principal_id,
                    source_id=current_source,
                    isolation_snapshot=final_snapshot,
                    use_vector=use_vector,
                )
                if not _same_publication_contract(
                    current_contract,
                    expected,
                    use_vector=use_vector,
                ):
                    raise SourceIsolationError(
                        SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                        "Source isolation is unavailable.",
                    )
            with self._lock:
                self._cache[cache_key] = stored
                self._cache.move_to_end(cache_key)
                while len(self._cache) > self._cache_capacity:
                    self._cache.popitem(last=False)
                return UserSourceSearchResult(
                    chunks=tuple(chunk.model_copy(deep=True) for chunk in stored.chunks),
                    provenance=stored.provenance,
                    mode=stored.mode,
                    auth_digest=stored.auth_digest,
                    generation_digest=stored.generation_digest,
                    cache_hit=False,
                    publication_contracts=stored.publication_contracts,
                )

    def _hydrate(
        self,
        source_id: str,
        generation: str,
        hits: Iterable[RetrievalHit],
    ) -> tuple[list[RetrievalChunk], tuple[UserSourceProvenance, ...]]:
        snapshot = self._snapshots.load_snapshot(source_id, generation)
        if snapshot is None:
            raise SourceOfflineError(SourceOfflineErrorCode.REPAIR_REQUIRED, source_id=source_id)
        by_chunk = {
            chunk.chunk_id: chunk
            for document in snapshot.documents
            for chunk in document.chunks()
        }
        chunks: list[RetrievalChunk] = []
        provenances: list[UserSourceProvenance] = []
        for rank, hit in enumerate(hits, start=1):
            if hit.chunk_id is None or hit.chunk_id not in by_chunk:
                raise SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)
            normalized = by_chunk[hit.chunk_id]
            uri = public_uri(source_id, normalized.logical_uri)
            provenance = UserSourceProvenance(
                source_id=source_id,
                document_id=normalized.document_id,
                chunk_id=normalized.chunk_id,
                logical_uri=normalized.logical_uri,
                generation=generation,
                origin_kind=hit.origin_kind or "original",
                public_uri=uri,
            )
            provenance.validate()
            chunks.append(
                RetrievalChunk(
                    id=normalized.chunk_id,
                    file=uri,
                    title=normalized.title,
                    content=normalized.content,
                    score=round(1.0 / (config.RRF_K + rank), 4),
                )
            )
            provenances.append(provenance)
        return chunks, tuple(provenances)


class LazyUserSourceSearch:
    """Open the user-source control plane only when a principal is present."""

    def __init__(self, registry_path: str | Path, cache_root: str | Path) -> None:
        self._registry_path = Path(registry_path)
        self._cache_root = Path(cache_root)
        self._inner: UserSourceSearchService | None = None
        self._lock = RLock()
        self._unavailable = False

    def search(
        self,
        *,
        principal_id: str,
        query: str,
        top_k: int = 5,
        source_id: str | None = None,
        use_vector: bool = True,
    ) -> UserSourceSearchResult:
        inner = self._get()
        if inner is None:
            return UserSourceSearchResult.empty()
        return inner.search(
            principal_id=principal_id,
            query=query,
            top_k=top_k,
            source_id=source_id,
            use_vector=use_vector,
        )

    def _get(self) -> UserSourceSearchService | None:
        with self._lock:
            if self._unavailable:
                return None
            if self._inner is not None:
                return self._inner
            if not self._registry_path.is_file():
                return None
            try:
                lifecycle = SourceLifecycleService(SqliteSourceRegistry(self._registry_path))
                self._inner = UserSourceSearchService(self._cache_root, lifecycle)
            except Exception:
                self._unavailable = True
                return None
            return self._inner


def ensure_user_provenance(chunks: Iterable[RetrievalChunk]) -> None:
    """Fail closed if a user-source hit cannot be bound to a public URI."""
    for chunk in chunks:
        if not chunk.file.startswith(f"{USER_PROVENANCE_SCHEME}://"):
            continue
        rest = chunk.file[len(USER_PROVENANCE_SCHEME) + 3 :]
        source_id, separator, logical_uri = rest.partition("/")
        if (
            separator != "/"
            or not _USER_SOURCE_RE.fullmatch(source_id)
            or not logical_uri
            or ".." in logical_uri.split("/")
            or _contains_host_path(chunk.file)
            or "\\" in chunk.file
            or not chunk.id
        ):
            raise SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id or None)


def _hits_to_retrieval(hits: Iterable[Fts5Hit], auth_digest: str) -> tuple[RetrievalHit, ...]:
    return tuple(
        RetrievalHit(
            source_id=hit.source_id,
            document_id=hit.document_id,
            chunk_id=hit.chunk_id,
            generation=hit.generation,
            origin_kind="original",
            cache_key=auth_digest,
        )
        for hit in hits
    )


def _generation_digest(snapshot: IsolationSnapshot, source_ids: tuple[str, ...]) -> str:
    payload = {
        "schema": RESULT_CACHE_SCHEMA,
        "generations": {
            source_id: snapshot.published_generations[source_id]
            for source_id in source_ids
            if source_id in snapshot.published_generations
        },
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _same_publication_contract(
    current: ValidatedSourceIndex,
    expected: ValidatedSourceIndex,
    *,
    use_vector: bool,
) -> bool:
    return (
        current.source_id == expected.source_id
        and current.generation == expected.generation
        and current.metadata.snapshot_fingerprint
        == expected.metadata.snapshot_fingerprint
        and current.metadata.identity_set_digest
        == expected.metadata.identity_set_digest
        and (
            not use_vector
            or current.vector_metadata == expected.vector_metadata
        )
    )


def _rrf_fuse(
    lists: list[list[RetrievalChunk]],
    top_k: int,
    *,
    query: str = "",
) -> list[RetrievalChunk]:
    scores: dict[str, float] = {}
    by_id: dict[str, RetrievalChunk] = {}
    needle = query.strip()
    for route in lists:
        for rank, chunk in enumerate(route):
            by_id.setdefault(chunk.id, chunk)
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (config.RRF_K + rank + 1)
    if needle:
        for chunk_id, chunk in by_id.items():
            content = (chunk.content or "").strip()
            title = (chunk.title or "").strip()
            if content == needle or title == needle:
                scores[chunk_id] += 1.0
            elif needle in content or needle in title:
                scores[chunk_id] += 0.25
    best_by_file: dict[str, tuple[str, float]] = {}
    for chunk_id, score in scores.items():
        file = by_id[chunk_id].file
        if file not in best_by_file or score > best_by_file[file][1]:
            best_by_file[file] = (chunk_id, score)
    ranked = sorted(best_by_file.values(), key=lambda value: value[1], reverse=True)[:top_k]
    output = [by_id[chunk_id].model_copy(deep=True) for chunk_id, _ in ranked]
    for chunk in output:
        chunk.score = round(scores[chunk.id], 4)
    return output


__all__ = [
    "PROVENANCE_SCHEMA",
    "RESULT_CACHE_SCHEMA",
    "USER_PROVENANCE_SCHEME",
    "public_uri",
    "UserSourceProvenance",
    "UserSourceSearchResult",
    "UserSourceSearchService",
    "LazyUserSourceSearch",
    "ensure_user_provenance",
    "SourceOfflineError",
    "SourceOfflineErrorCode",
    "SourceIsolationError",
    "Fts5TokenizerError",
]