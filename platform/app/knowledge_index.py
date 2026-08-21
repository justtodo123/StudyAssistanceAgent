"""知识库索引：扫描 knowledge/ 的 Markdown，切分为可检索切片（Chunk），提取 frontmatter。

对应参考项目 DocumentService / DocumentChunkRepository 的职责，但以纯文件 + JSON 缓存实现，
零数据库依赖，符合个人项目「轻量、可版本化」的定位。
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .models import RetrievalChunk

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_YAML_FIELD_RE = re.compile(r"^(\w[\w-]*)\s*:\s*(.*)$")


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """解析 Markdown 开头 YAML frontmatter，容错失败（不完整则返回空）。"""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    data: dict[str, Any] = {}
    for line in m.group(1).splitlines():
        fm = _YAML_FIELD_RE.match(line.strip())
        if not fm:
            continue
        key, val = fm.group(1), fm.group(2).strip().strip('"').strip("'")
        if key == "tags":
            # 兼容两种写法：[] / [a, b] / a,b
            val = [t.strip().strip('"') for t in val.strip("[]").split(",") if t.strip()]
        else:
            val = val.strip()
        data[key] = val
    return data


def _split_headings(text: str) -> list[tuple[str, str]]:
    """按 ## 标题切分为小节，返回 [(title, body)]，至少保留一个整块。"""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current:
                sections.append((current_title, current))
            current_title = line[3:].strip()
            current = []
        else:
            current.append(line)
    if current or not sections:
        sections.append((current_title, current))
    return [(t, "\n".join(b).strip()) for t, b in sections if "\n".join(b).strip()]


def _chunk_id(file: Path, title: str) -> str:
    raw = f"{file.relative_to(file.anchor)}#{title}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def build_index(root: Path | None = None) -> list[RetrievalChunk]:
    """扫描知识库目录，返回全部检索切片。root 默认取配置中的 KNOWLEDGE_ROOT。"""
    from . import config
    from .source_policy import is_indexable_frontmatter, is_indexable_relative_path

    root = root or config.KNOWLEDGE_ROOT
    chunks: list[RetrievalChunk] = []
    if not root.exists():
        return chunks

    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root).as_posix()
        if not is_indexable_relative_path(rel):
            continue
        text = md.read_text(encoding="utf-8")
        meta = _parse_frontmatter(text)
        if not is_indexable_frontmatter(meta):
            continue
        body = _FRONTMATTER_RE.sub("", text)
        for title, content in _split_headings(body):
            if len(content) < 15:  # 过短片段（可能是占位）跳过，减少噪音
                continue
            chunks.append(
                RetrievalChunk(
                    id=_chunk_id(md, title),
                    file=f"knowledge/{rel}",
                    title=title or (meta.get("title", "") or md.stem),
                    course=meta.get("course", ""),
                    tags=meta.get("tags", []),
                    difficulty=meta.get("difficulty", ""),
                    updated=meta.get("updated", ""),
                    content=content,
                )
            )
    return chunks


def _latest_mtime(root: Path) -> float:
    """知识库内最晚修改时间，作为缓存失效依据。"""
    if not root.exists():
        return 0.0
    return max((p.stat().st_mtime for p in root.rglob("*.md")), default=0.0)


def build_index_cached(root: Path | None = None) -> list[RetrievalChunk]:
    """带 JSON 缓存的索引构建：md 时间戳未变则读缓存，避免重复扫描。
    缓存写入数据目录 .cache/（已在 .gitignore 忽略）。"""
    from . import config
    from .observability import metrics

    root = root or config.KNOWLEDGE_ROOT
    cache_dir = Path(__file__).resolve().parents[1] / ".cache"
    cache_path = cache_dir / "knowledge_index.json"
    meta_path = cache_dir / "knowledge_index.meta.json"
    cache_dir.mkdir(exist_ok=True)

    if cache_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("latest_mtime", -1) == _latest_mtime(root):
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                chunks = [RetrievalChunk(**c) for c in data]
                metrics.record_index_cache(hit=True, index_size=len(chunks))
                return chunks
        except Exception:
            pass  # 缓存损坏则重建

    chunks = build_index(root)
    metrics.record_index_cache(hit=False, index_size=len(chunks))
    cache_path.write_text(
        json.dumps([c.model_dump() for c in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    meta_path.write_text(
        json.dumps({"latest_mtime": _latest_mtime(root), "count": len(chunks)}),
        encoding="utf-8",
    )
    return chunks
