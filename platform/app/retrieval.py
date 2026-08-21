"""多路召回 + RRF 融合（模型源自参考项目 MultiRecallService）。

路 1：稠密向量（BGE 本地，可选）
路 2：BM25 关键词（候选池内）
融合：Reciprocal Rank Fusion，k=60
"""

from __future__ import annotations

import time
from collections import OrderedDict

from . import config
from .bm25 import Bm25Search
from .models import RetrievalChunk
from .observability import log_operation, metrics
from .vector_store import LocalVectorStore, SqliteVectorStore, VectorStore

RRF_K = config.RRF_K


class _VectorHolder:
    """惰性单例：避免未装依赖/首次加载阻塞无向量需求的请求。"""

    _store: VectorStore | None = None
    _loaded = False

    @classmethod
    def get(cls) -> VectorStore | None:
        if not config.VECTOR_ENABLED or not cls._available():
            return None
        if not cls._loaded:
            if config.VECTOR_STORE == "linear":
                cls._store = LocalVectorStore(config.EMBEDDING_MODEL)
            else:
                cls._store = SqliteVectorStore(
                    config.EMBEDDING_MODEL,
                    db_path=config.VECTOR_STORE_PATH,
                )
            cls._loaded = True
        return cls._store

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

    def __init__(self) -> None:
        self._chunks: list[RetrievalChunk] | None = None
        self._result_cache: OrderedDict[
            tuple[str, int, float, str | None], tuple[list[RetrievalChunk], str]
        ] = OrderedDict()
        self._cache_capacity = 128

    @staticmethod
    def _copy_results(results: list[RetrievalChunk]) -> list[RetrievalChunk]:
        return [chunk.model_copy(deep=True) for chunk in results]

    def recall(
        self,
        question: str,
        top_k: int = 5,
        threshold: float | None = None,
        course: str | None = None,
    ) -> tuple[list[RetrievalChunk], str]:
        """Return fused results and the active retrieval mode."""
        started = time.perf_counter()
        if threshold is None:
            threshold = config.VECTOR_THRESHOLD
        cache_key = (question, top_k, threshold, course)
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

        self._chunks = self._chunks or self._load()

        # BM25_POOL=0 means search the complete corpus.
        pool = self._chunks if config.BM25_POOL <= 0 else self._chunks[: config.BM25_POOL]
        routes: list[list[RetrievalChunk]] = []

        vector_store = _VectorHolder.get()
        if vector_store is not None:
            try:
                if not vector_store.is_synced(self._chunks):
                    vector_store.replace_all(self._chunks)
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

    def _load(self) -> list[RetrievalChunk]:
        from .knowledge_index import build_index_cached

        return build_index_cached()

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
        for cid, score in scores.items():
            f = by_id[cid].file
            if f not in best_by_file or score > best_by_file[f][1]:
                best_by_file[f] = (cid, score)

        ranked = sorted(best_by_file.values(), key=lambda x: x[1], reverse=True)[:top_k]
        out = [by_id[cid].model_copy(deep=True) for cid, _ in ranked]
        for chunk in out:
            chunk.score = round(scores[chunk.id], 4)
        return out
