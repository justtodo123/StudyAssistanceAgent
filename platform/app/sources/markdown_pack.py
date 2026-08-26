"""Adapter for the repository's trusted default Markdown knowledge pack."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .. import config
from ..markdown_parser import _FRONTMATTER_RE, parse_frontmatter, split_headings
from ..protocols import (
    ProtocolValidationError,
    SourceChunk,
    SourceDescriptor,
    SourceIdentity,
    SourceType,
    validate_source_snapshot,
)
from ..source_policy import is_indexable_frontmatter, is_indexable_relative_path

DEFAULT_SOURCE_ID = "knowledge-pack"
CHUNK_SCHEMA = "sa.chunk.markdown-h2.v1"


@dataclass(frozen=True, slots=True)
class MarkdownPackSnapshot:
    """Complete materialized view of the default Markdown source."""

    descriptor: SourceDescriptor
    chunks: tuple[SourceChunk, ...]

    def __post_init__(self) -> None:
        if any(chunk.identity.source_id != self.descriptor.source_id for chunk in self.chunks):
            raise ProtocolValidationError("snapshot chunk namespace must match descriptor")


class MarkdownPackSource:
    """Expose the trusted default Markdown tree through the M6a Source contract."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = (root or config.KNOWLEDGE_ROOT).resolve()
        self._snapshot: MarkdownPackSnapshot | None = None

    def describe(self) -> SourceDescriptor:
        return self.materialize().descriptor

    def iter_chunks(self) -> Iterable[SourceChunk]:
        return iter(self.materialize().chunks)

    def materialize(self) -> MarkdownPackSnapshot:
        if self._snapshot is None:
            chunks = tuple(self._build_chunks())
            fingerprint = _fingerprint_chunks(chunks)
            revision = _revision_for(self._root, fingerprint)
            descriptor = SourceDescriptor(
                source_id=DEFAULT_SOURCE_ID,
                source_type=SourceType.HUMAN_MARKDOWN,
                revision=revision,
                fingerprint=fingerprint,
                generation=_generation_for(revision, fingerprint),
            )
            snapshot = MarkdownPackSnapshot(descriptor=descriptor, chunks=chunks)
            validate_source_snapshot(_MaterializedSource(snapshot))
            self._snapshot = snapshot
        return self._snapshot

    def _build_chunks(self) -> Iterable[SourceChunk]:
        if not self._root.exists():
            return

        for path in sorted(self._root.rglob("*.md")):
            logical_uri = path.relative_to(self._root).as_posix()
            if not is_indexable_relative_path(logical_uri):
                continue
            text = path.read_text(encoding="utf-8-sig")
            metadata = parse_frontmatter(text)
            if not is_indexable_frontmatter(metadata):
                continue
            body = _FRONTMATTER_RE.sub("", text)
            identity = SourceIdentity(DEFAULT_SOURCE_ID, logical_uri)
            headings = split_headings(body)
            for ordinal, (heading, content) in enumerate(headings):
                if len(content) < config.CHUNK_MIN_CHARS:
                    continue
                title = heading or str(metadata.get("title", "") or path.stem)
                yield SourceChunk(
                    identity=identity,
                    chunk_key=_chunk_key(ordinal, heading),
                    content=content,
                    title=title,
                    metadata=_safe_metadata(metadata),
                    chunk_schema=CHUNK_SCHEMA,
                )


@dataclass(frozen=True, slots=True)
class _MaterializedSource:
    snapshot: MarkdownPackSnapshot

    def describe(self) -> SourceDescriptor:
        return self.snapshot.descriptor

    def iter_chunks(self) -> Iterable[SourceChunk]:
        return iter(self.snapshot.chunks)


def _chunk_key(ordinal: int, heading: str) -> str:
    normalized_heading = " ".join(heading.split()).casefold()
    return f"h2-{ordinal}:{normalized_heading or 'document'}"


def _safe_metadata(metadata: dict) -> dict[str, object]:
    return {
        "course": str(metadata.get("course", "")),
        "tags": tuple(str(tag) for tag in metadata.get("tags", [])),
        "difficulty": str(metadata.get("difficulty", "")),
        "updated": str(metadata.get("updated", "")),
    }


def _fingerprint_chunks(chunks: tuple[SourceChunk, ...]) -> str:
    payload = [
        {
            "document_id": chunk.identity.document_id,
            "chunk_id": chunk.chunk_id,
            "chunk_key": chunk.chunk_key,
            "content": chunk.content,
            "title": chunk.title,
            "metadata": dict(chunk.metadata),
            "chunk_schema": chunk.chunk_schema,
        }
        for chunk in chunks
    ]
    return _digest(payload)


def _revision_for(root: Path, fingerprint: str) -> str:
    payload = {
        "source_id": DEFAULT_SOURCE_ID,
        "source_type": SourceType.HUMAN_MARKDOWN.value,
        "chunk_schema": CHUNK_SCHEMA,
        "policy": "default-markdown-pack-v1",
        "root_exists": root.exists(),
        "fingerprint": fingerprint,
    }
    return _digest(payload)


def _generation_for(revision: str, fingerprint: str) -> str:
    return _digest({"source_id": DEFAULT_SOURCE_ID, "revision": revision, "fingerprint": fingerprint})


def _digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
