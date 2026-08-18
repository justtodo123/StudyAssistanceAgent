"""多路召回 + RRF 融合（模型源自参考项目 MultiRecallService）。

路 1：稠密向量（BGE 本地，可选）
路 2：BM25 关键词（候选池内）
融合：Reciprocal Rank Fusion，k=60
"""

from __future__ import annotations

from . import config
from .bm25 import Bm25Search
from .models import RetrievalChunk
from .vector_store import LocalVectorStore, SqliteVectorStore, VectorStore

RRF_K = 60


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

    def recall(self, question: str, top_k: int = 5, threshold: float = 0.0,
               course: str | None = None) -> tuple[list[RetrievalChunk], str]:
        """返回 (融合结果, 生效模式)。mode 用于日志/响应标注：hybrid / keyword-only。"""
        self._chunks = self._chunks or self._load()

        # BM25_POOL=0 表示全库检索；>0 时仅检索前 N 片（参考项目大语料场景的优化开关）
        pool = self._chunks if config.BM25_POOL <= 0 else self._chunks[: config.BM25_POOL]
        routes: list[list[RetrievalChunk]] = []

        # 路 1：向量（可选）
        vector_store = _VectorHolder.get()
        if vector_store is not None:
            try:
                if not vector_store.is_synced(self._chunks):
                    vector_store.replace_all(self._chunks)
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

        # 课程过滤：在融合后过滤，避免向量单例缓存导致过滤失效
        if course:
            fused = [r for r in fused if r.course == course]

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
