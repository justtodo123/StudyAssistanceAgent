"""多路召回 + RRF 融合（模型源自参考项目 MultiRecallService）。

路 1：稠密向量（BGE 本地，可选）
路 2：BM25 关键词（候选池内）
融合：Reciprocal Rank Fusion，k=60
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from threading import RLock

from . import config
from .bm25 import Bm25Search
from .models import RetrievalChunk
from .observability import log_operation, metrics
from .vector_store import LocalVectorStore, SqliteVectorStore, VectorStore

RRF_K = config.RRF_K


class RetrievalScope(StrEnum):
    """Select the immutable source view used by one retrieval request."""

    DEFAULT_ONLY = "DEFAULT_ONLY"
    DEFAULT_PLUS_EXTRAS = "DEFAULT_PLUS_EXTRAS"


class _VectorHolder:
    """Lazy vector stores isolated by immutable retrieval scope and generation."""

    _stores: dict[tuple[str, str], VectorStore] = {}
    _lock = RLock()
    _max_generations = 2

    @classmethod
    def get(cls, scope: RetrievalScope, generation: str) -> VectorStore | None:
        if not config.VECTOR_ENABLED or not cls._available():
            return None
        key = (scope.value, generation)
        with cls._lock:
            store = cls._stores.get(key)
            if store is None:
                if config.VECTOR_STORE == "linear":
                    store = LocalVectorStore(config.EMBEDDING_MODEL)
                else:
                    store = SqliteVectorStore(
                        config.EMBEDDING_MODEL,
                        db_path=cls._sqlite_path(scope, generation),
                    )
                cls._stores[key] = store
                cls._evict(scope, keep=key)
            return store

    @classmethod
    def _evict(
        cls,
        scope: RetrievalScope,
        *,
        keep: tuple[str, str],
    ) -> None:
        candidates = [
            key
            for key in cls._stores
            if key[0] == scope.value and key != keep
        ]
        while len(candidates) >= cls._max_generations:
            key = candidates.pop(0)
            store = cls._stores.pop(key)
            close = getattr(store, "close", None)
            if callable(close):
                close()

    @classmethod
    def reset(cls) -> None:
        """Release process-local stores; persisted cache files remain untouched."""
        with cls._lock:
            stores = tuple(cls._stores.values())
            cls._stores.clear()
        for store in stores:
            close = getattr(store, "close", None)
            if callable(close):
                close()

    @staticmethod
    def _sqlite_path(scope: RetrievalScope, generation: str) -> Path:
        path = config.VECTOR_STORE_PATH
        suffix = path.suffix or ".sqlite3"
        return path.with_name(
            f"{path.stem}-{scope.value.lower()}-{generation}{suffix}"
        )

    @staticmethod
    def _available() -> bool:
        if config.VECTOR_STORE == "linear":
            return LocalVectorStore.available()
        if config.VECTOR_STORE == "sqlite":
            return SqliteVectorStore.available()
        raise ValueError(
            f"unsupported vector store: {config.VECTOR_STORE!r}; "
            "expected 'sqlite' or 'linear'"
        )


class MultiRecallService:
    """多路召回统一入口。向量不可用或失败时优雅回退到纯关键词路。"""

    def __init__(
        self,
        snapshot_provider: Callable[
            [RetrievalScope], tuple[str, list[RetrievalChunk]]
        ]
        | None = None,
        user_source_search: object | None = None,
    ) -> None:
        self._snapshot_provider = snapshot_provider
        self._user_source_search = user_source_search
        self._chunks_by_scope: dict[str, list[RetrievalChunk]] = {}
        self._generation_by_scope: dict[str, str] = {}
        self._result_cache: OrderedDict[
            tuple[str, str, str, int, float, str | None, str | None],
            tuple[list[RetrievalChunk], str],
        ] = OrderedDict()
        self._cache_capacity = 128
        self._lock = RLock()

    @staticmethod
    def _copy_results(results: list[RetrievalChunk]) -> list[RetrievalChunk]:
        return [chunk.model_copy(deep=True) for chunk in results]

    def recall(
        self,
        question: str,
        top_k: int = 5,
        threshold: float | None = None,
        course: str | None = None,
        scope: RetrievalScope = RetrievalScope.DEFAULT_ONLY,
        principal_id: str | None = None,
    ) -> tuple[list[RetrievalChunk], str]:
        """Return fused results from exactly one current source generation."""
        started = time.perf_counter()
        if threshold is None:
            threshold = config.VECTOR_THRESHOLD

        with self._lock:
            generation, chunks = self._load_snapshot(scope)
            scope_key = scope.value
            if self._generation_by_scope.get(scope_key) != generation:
                self._generation_by_scope[scope_key] = generation
                self._chunks_by_scope[scope_key] = chunks
                stale_keys = [key for key in self._result_cache if key[1] == scope_key]
                for key in stale_keys:
                    del self._result_cache[key]
            principal = (principal_id or '').strip() or None
            cache_key = (generation, scope_key, question, top_k, threshold, course, principal)
            cached = self._result_cache.get(cache_key)
            if cached is not None:
                results, mode = cached
                self._result_cache.move_to_end(cache_key)
                results = self._copy_results(results)
                duration_ms = (time.perf_counter() - started) * 1000
                metrics.record("search", duration_ms, len(results), cache_hit=True)
                log_operation(
                    "search",
                    duration_ms=duration_ms,
                    result_count=len(results),
                    course=course,
                    mode=mode,
                    cache_hit=True,
                )
                return results, mode

            # BM25_POOL=0 means search the complete corpus.
            pool = chunks if config.BM25_POOL <= 0 else chunks[: config.BM25_POOL]
            routes: list[list[RetrievalChunk]] = []

            vector_store = _VectorHolder.get(scope, generation)
            if vector_store is not None:
                try:
                    if not vector_store.is_synced(chunks):
                        vector_store.replace_all(chunks)
                    routes.append(vector_store.search(question, top_k=20, threshold=threshold))
                except Exception:
                    routes.append([])

            try:
                bm25 = Bm25Search(pool)
                routes.append(bm25.search(question, top_k=20))
            except Exception:
                routes.append([])

            if not any(routes):
                results, mode = [], "keyword-only"
                results = self._merge_user_sources(
                    results,
                    question=question,
                    top_k=top_k,
                    principal_id=principal,
                )
                if results:
                    mode = "fts5"
            else:
                mode = "hybrid" if len(routes) > 1 and all(routes) else "keyword-only"
                # Keep a wider candidate set before applying content-type and course
                # preferences. Otherwise interview notes or README navigation chunks can
                # occupy every top-k slot and hide the underlying course note.
                results = self._rrf_fuse(routes, max(top_k, 20))
                if course:
                    results = [result for result in results if result.course == course]
                else:
                    results = self._prioritize_content_type(question, results)
                results = self._merge_user_sources(
                    results,
                    question=question,
                    top_k=top_k,
                    principal_id=principal,
                )
                results = results[:top_k]

            stored = self._copy_results(results)
            self._result_cache[cache_key] = (stored, mode)
            self._result_cache.move_to_end(cache_key)
            while len(self._result_cache) > self._cache_capacity:
                self._result_cache.popitem(last=False)

            duration_ms = (time.perf_counter() - started) * 1000
            metrics.record("search", duration_ms, len(results), cache_hit=False)
            log_operation(
                "search",
                duration_ms=duration_ms,
                result_count=len(results),
                course=course,
                mode=mode,
                cache_hit=False,
            )
            return self._copy_results(results), mode


    def _merge_user_sources(
        self,
        results: list[RetrievalChunk],
        *,
        question: str,
        top_k: int,
        principal_id: str | None,
    ) -> list[RetrievalChunk]:
        """RRF-merge authorized user-source hits after isolation/FTS5."""
        if not principal_id or self._user_source_search is None:
            return results
        try:
            user_result = self._user_source_search.search(  # type: ignore[attr-defined]
                principal_id=principal_id,
                query=question,
                top_k=max(top_k, 20),
            )
        except Exception:
            return results
        user_chunks = list(getattr(user_result, "chunks", ()))
        if not user_chunks:
            return results
        from .user_source_search import ensure_user_provenance

        ensure_user_provenance(user_chunks)
        if not results:
            return user_chunks[: max(top_k, 20)]
        return self._rrf_fuse([results, user_chunks], max(top_k, 20))

    @staticmethod
    def _prioritize_content_type(
        question: str,
        results: list[RetrievalChunk],
    ) -> list[RetrievalChunk]:
        """Favor actual course notes for study queries and interview notes for interview queries.

        README chunks are useful navigation material but should not displace a note
        that directly answers the question. Interview-bank chunks remain preferred
        when the user explicitly asks an interview-oriented question.
        """
        normalized = question.lower()
        asks_for_interview = "面试" in question or "interview" in normalized

        interview: list[RetrievalChunk] = []
        course_notes: list[RetrievalChunk] = []
        navigation: list[RetrievalChunk] = []
        for chunk in results:
            if "/interview/" in chunk.file:
                interview.append(chunk)
            elif chunk.file.endswith("/README.md"):
                navigation.append(chunk)
            else:
                course_notes.append(chunk)

        if asks_for_interview:
            return interview + course_notes + navigation
        return course_notes + interview + navigation

    def _load_snapshot(
        self,
        scope: RetrievalScope = RetrievalScope.DEFAULT_ONLY,
    ) -> tuple[str, list[RetrievalChunk]]:
        if self._snapshot_provider is not None:
            return self._snapshot_provider(scope)

        from .knowledge_index import build_index_snapshot_cached

        snapshot = build_index_snapshot_cached()
        return snapshot.generation, list(snapshot.chunks)

    def _load(self) -> list[RetrievalChunk]:
        """Compatibility helper for callers that only require legacy chunks."""
        _generation, chunks = self._load_snapshot()
        return chunks

    @staticmethod
    def _rrf_fuse(lists: list[list[RetrievalChunk]], top_k: int) -> list[RetrievalChunk]:
        scores: dict[str, float] = {}
        by_id: dict[str, RetrievalChunk] = {}
        for route in lists:
            for rank, chunk in enumerate(route):
                key = chunk.id
                by_id.setdefault(key, chunk)
                scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)

        # 按文件去重：同一文件只保留得分最高的 chunk，避免同一笔记多个切片霸占结果
        best_by_file: dict[str, tuple[str, float]] = {}  # file → (chunk_id, score)
        for chunk_id, score in scores.items():
            file = by_id[chunk_id].file
            if file not in best_by_file or score > best_by_file[file][1]:
                best_by_file[file] = (chunk_id, score)

        ranked = sorted(best_by_file.values(), key=lambda value: value[1], reverse=True)[:top_k]
        output = [by_id[chunk_id].model_copy(deep=True) for chunk_id, _ in ranked]
        for chunk in output:
            chunk.score = round(scores[chunk.id], 4)
        return output
