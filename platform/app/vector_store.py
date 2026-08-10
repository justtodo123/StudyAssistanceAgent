"""向量存储抽象 + 本地实现（可选）。

对齐参考项目 VectorStoreService 接口，但做「可选依赖 + 优雅降级」：
- 未安装 sentence-transformers 时 VECTOR_AVAILABLE=False，上层自动回退纯关键词检索。
- 向量相似度采用余弦，索引用朴素线性扫描；个人知识库规模（几百片）足够，无需 Milvus。
"""

from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Optional

from .models import RetrievalChunk

try:  # 可选依赖
    from sentence_transformers import SentenceTransformer

    _ST_AVAILABLE = True
except Exception:  # pragma: no cover - 依赖未装时的降级路径
    _ST_AVAILABLE = False


@dataclass
class _VectorItem:
    chunk: RetrievalChunk
    vec: list[float]


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


class LocalVectorStore:
    """本地向量库：embedding 模型 + 余弦最近邻。首次加载模型较慢，故做单例。"""

    def __init__(self, model_name: str, cache_dir: Optional[str] = None):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model: Optional[SentenceTransformer] = None
        self._items: list[_VectorItem] = []

    # -- 可选依赖状态，供上层判断是否启用向量路 --
    @staticmethod
    def available() -> bool:
        return _ST_AVAILABLE

    def _ensure_model(self) -> None:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, cache_folder=self.cache_dir)

    def add(self, chunks: list[RetrievalChunk]) -> None:
        if not chunks:
            return
        self._ensure_model()
        texts = [c.content for c in chunks]
        vecs = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        self._items = [
            _VectorItem(chunk=c, vec=vec) for c, vec in zip(chunks, vecs)
        ]

    def search(self, query: str, top_k: int = 5, threshold: float = 0.0) -> list[RetrievalChunk]:
        if not self._items:
            return []
        self._ensure_model()
        q_vec = self._model.encode([query], normalize_embeddings=True)[0]
        scored = [
            (i, _cosine(q_vec, item.vec)) for i, item in enumerate(self._items)
        ]
        scored.sort(key=lambda t: t[1], reverse=True)
        out: list[RetrievalChunk] = []
        for idx, score in scored[:top_k]:
            if score < threshold:
                continue
            item = self._items[idx]
            chunk = item.chunk.model_copy(deep=True)
            chunk.score = round(score, 4)
            out.append(chunk)
        return out
