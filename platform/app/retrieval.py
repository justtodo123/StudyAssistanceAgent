"""多路召回 + RRF 融合（模型源自参考项目 MultiRecallService）。

路 1：稠密向量（BGE 本地，可选）
路 2：BM25 关键词（候选池内）
融合：Reciprocal Rank Fusion，k=60
"""

from __future__ import annotations

from . import config
from .bm25 import Bm25Search
from .models import RetrievalChunk
from .vector_store import LocalVectorStore

RRF_K = 60


class _VectorHolder:
    """惰性单例：避免未装依赖/首次加载阻塞无向量需求的请求。"""

    _store: LocalVectorStore | None = None
    _loaded = False

    @classmethod
    def get(cls) -> LocalVectorStore | None:
        if not config.VECTOR_ENABLED or not LocalVectorStore.available():
            return None
        if not cls._loaded:
            cls._store = LocalVectorStore(config.EMBEDDING_MODEL)
            cls._loaded = True
        return cls._store


class MultiRecallService:
    """多路召回统一入口。向量不可用或失败时优雅回退到纯关键词路。"""

    def __init__(self) -> None:
        self._chunks: list[RetrievalChunk] | None = None

    def recall(self, question: str, top_k: int = 5, threshold: float = 0.0) -> tuple[list[RetrievalChunk], str]:
        """返回 (融合结果, 生效模式)。mode 用于日志/响应标注：hybrid / keyword-only。"""
        self._chunks = self._chunks or self._load()

        pool = self._chunks[: config.BM25_POOL] or self._chunks
        routes: list[list[RetrievalChunk]] = []

        # 路 1：向量（可选）
        vector_store = _VectorHolder.get()
        if vector_store is not None:
            try:
                if not getattr(vector_store, "_items", None):
                    vector_store.add(self._chunks)
                routes.append(vector_store.search(question, top_k=20, threshold=threshold))
            except Exception:
                routes.append([])  # 向量路失败不阻断

        # 路 2：BM25
        try:
            bm25 = Bm25Search(pool)
            routes.append(bm25.search(question, top_k=20))
        except Exception:
            routes.append([])

        if not any(routes):
            return [], "keyword-only"

        mode = "hybrid" if len(routes) > 1 and all(routes) else "keyword-only"
        fused = self._rrf_fuse(routes, top_k)
        return fused, mode

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
        ranked_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
        out = [by_id[i].model_copy(deep=True) for i in ranked_ids]
        for chunk in out:
            chunk.score = round(scores[chunk.id], 4)
        return out
