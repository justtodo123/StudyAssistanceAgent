"""知识库索引：扫描 knowledge/ 的 Markdown，切分为可检索切片（Chunk），提取 frontmatter。

对应参考项目 DocumentService / DocumentChunkRepository 的职责，但以纯文件 + JSON 缓存实现，
零数据库依赖，符合个人项目「轻量、可版本化」的定位。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .markdown_parser import _FRONTMATTER_RE, parse_frontmatter, split_headings
from .models import RetrievalChunk

_INDEX_CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"

# Kept as private compatibility aliases for existing callers while parsing lives
# in a neutral module shared by the legacy index and M6a source adapter.
_parse_frontmatter = parse_frontmatter
_split_headings = split_headings


@dataclass(frozen=True, slots=True)
class IndexSnapshot:
    """Legacy retrieval view bound to one materialized source generation."""

    generation: str
    chunks: tuple[RetrievalChunk, ...]


def materialize_index(root: Path | None = None) -> IndexSnapshot:
    """Build a validated legacy snapshot while retaining its portable generation."""
    from .retrieval_index import DefaultPackRetrievalIndex
    from .sources.markdown_pack import MarkdownPackSource

    source_snapshot = MarkdownPackSource(root).materialize()
    index = DefaultPackRetrievalIndex.from_source_snapshot(source_snapshot)
    return IndexSnapshot(index.generation, index.chunks)


def build_index(root: Path | None = None) -> list[RetrievalChunk]:
    """Materialize the default Markdown source as legacy retrieval chunks."""
    return list(materialize_index(root).chunks)


def build_index_cached(root: Path | None = None) -> list[RetrievalChunk]:
    """Return a cached legacy view only when it matches the full source generation.

    The public return type remains a list of ``RetrievalChunk`` values. Cache
    validity is driven by the materialized portable source snapshot rather than
    host timestamps, so moved roots and non-latest file edits cannot publish a
    stale mixed-ID corpus.
    """
    return list(build_index_snapshot_cached(root).chunks)


def build_index_snapshot_cached(root: Path | None = None) -> IndexSnapshot:
    """Return a legacy index snapshot cached by portable source generation."""
    from . import config
    from .observability import metrics

    root = root or config.KNOWLEDGE_ROOT
    snapshot = materialize_index(root)
    cache_dir = _INDEX_CACHE_DIR
    cache_path = cache_dir / "knowledge_index.json"
    meta_path = cache_dir / "knowledge_index.meta.json"
    cache_dir.mkdir(exist_ok=True)

    if cache_path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("generation") == snapshot.generation:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                chunks = tuple(RetrievalChunk(**chunk) for chunk in data)
                if meta.get("count") == len(chunks):
                    metrics.record_index_cache(hit=True, index_size=len(chunks))
                    return IndexSnapshot(snapshot.generation, chunks)
        except Exception:
            pass  # 缓存损坏则重建

    metrics.record_index_cache(hit=False, index_size=len(snapshot.chunks))
    cache_path.write_text(
        json.dumps([chunk.model_dump() for chunk in snapshot.chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    meta_path.write_text(
        json.dumps(
            {
                "generation": snapshot.generation,
                "count": len(snapshot.chunks),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return snapshot
