"""Strict adapter for operator-configured static Markdown sources."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from ..markdown_parser import _FRONTMATTER_RE, parse_frontmatter, split_headings
from ..protocols import (
    ProtocolValidationError,
    SourceChunk,
    SourceDescriptor,
    SourceIdentity,
    validate_source_snapshot,
)
from ..source_config import SourceLimits, StaticSourceConfig
from ..source_policy import is_indexable_relative_path
from .markdown_pack import CHUNK_SCHEMA, MarkdownPackSnapshot


class SourceContentError(ValueError):
    """Safe whole-source content failure."""

    code = "SOURCE_CONTENT_INVALID"


class SourceLimitError(ValueError):
    """Safe resource-cap failure."""

    code = "SOURCE_LIMIT_EXCEEDED"


class StaticMarkdownSource:
    """Materialize one strict, startup-configured Markdown root."""

    def __init__(self, source: StaticSourceConfig, limits: SourceLimits) -> None:
        self._source = source
        self._limits = limits
        self._snapshot: MarkdownPackSnapshot | None = None
        self.file_count = 0
        self.byte_count = 0

    def describe(self) -> SourceDescriptor:
        return self.materialize().descriptor

    def iter_chunks(self) -> Iterable[SourceChunk]:
        return iter(self.materialize().chunks)

    def materialize(self) -> MarkdownPackSnapshot:
        if self._snapshot is not None:
            return self._snapshot
        try:
            chunks = tuple(self._build_chunks())
            if not chunks:
                raise SourceContentError(
                    f"source {self._source.source_id} contains no retrieval chunks"
                )
            if len(chunks) > self._limits.max_extra_chunks_per_source:
                raise SourceLimitError(
                    f"source {self._source.source_id} exceeds the chunk limit"
                )
            fingerprint = _fingerprint(chunks)
            revision = _digest(
                {
                    "source_id": self._source.source_id,
                    "source_type": self._source.source_type.value,
                    "chunk_schema": CHUNK_SCHEMA,
                    "policy": "strict-static-markdown-v1",
                    "fingerprint": fingerprint,
                }
            )
            descriptor = SourceDescriptor(
                source_id=self._source.source_id,
                source_type=self._source.source_type,
                revision=revision,
                fingerprint=fingerprint,
                generation=_digest(
                    {
                        "source_id": self._source.source_id,
                        "revision": revision,
                        "fingerprint": fingerprint,
                    }
                ),
            )
            snapshot = MarkdownPackSnapshot(descriptor=descriptor, chunks=chunks)
            validate_source_snapshot(_Materialized(snapshot))
        except SourceLimitError:
            raise
        except SourceContentError:
            raise
        except (OSError, UnicodeError, ProtocolValidationError, ValueError) as exc:
            raise SourceContentError(
                f"source {self._source.source_id} contains invalid content"
            ) from exc
        self._snapshot = snapshot
        return snapshot

    def _build_chunks(self) -> Iterable[SourceChunk]:
        seen_files = 0
        seen_bytes = 0
        for path in sorted(self._source.root.rglob("*.md")):
            resolved = path.resolve(strict=True)
            try:
                resolved.relative_to(self._source.root)
            except ValueError as exc:
                raise SourceContentError(
                    f"source {self._source.source_id} contains an unsafe link"
                ) from exc
            logical_uri = path.relative_to(self._source.root).as_posix()
            if not is_indexable_relative_path(logical_uri):
                continue
            size = resolved.stat().st_size
            seen_files += 1
            seen_bytes += size
            if size > self._limits.max_file_bytes:
                raise SourceLimitError(
                    f"source {self._source.source_id} exceeds the single-file limit"
                )
            if seen_files > self._limits.max_files_per_source:
                raise SourceLimitError(
                    f"source {self._source.source_id} exceeds the file limit"
                )
            if seen_bytes > self._limits.max_bytes_per_source:
                raise SourceLimitError(
                    f"source {self._source.source_id} exceeds the byte limit"
                )
            text = resolved.read_text(encoding="utf-8-sig")
            metadata = parse_frontmatter(text)
            if not _is_approved(metadata, self._source.source_type.value):
                raise SourceContentError(
                    f"source {self._source.source_id} contains invalid frontmatter"
                )
            body = _FRONTMATTER_RE.sub("", text)
            identity = SourceIdentity(self._source.source_id, logical_uri)
            for ordinal, (heading, content) in enumerate(split_headings(body)):
                if len(content) < 15:
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
        self.file_count = seen_files
        self.byte_count = seen_bytes


class _Materialized:
    def __init__(self, snapshot: MarkdownPackSnapshot) -> None:
        self._snapshot = snapshot

    def describe(self) -> SourceDescriptor:
        return self._snapshot.descriptor

    def iter_chunks(self) -> Iterable[SourceChunk]:
        return iter(self._snapshot.chunks)


def _is_approved(metadata: dict, expected_type: str) -> bool:
    return (
        metadata.get("source_type") == expected_type
        and metadata.get("ingest_status") == "approved"
        and isinstance(metadata.get("course"), str)
        and bool(metadata["course"].strip())
    )


def _safe_metadata(metadata: dict) -> dict[str, object]:
    tags = metadata.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise SourceContentError("source metadata is invalid")
    return {
        "course": str(metadata.get("course", "")),
        "tags": tuple(tags),
        "difficulty": str(metadata.get("difficulty", "")),
        "updated": str(metadata.get("updated", "")),
    }


def _chunk_key(ordinal: int, heading: str) -> str:
    heading_digest = hashlib.sha256(heading.encode("utf-8")).hexdigest()[:16]
    return f"h2:{ordinal}:{heading_digest}"


def _fingerprint(chunks: tuple[SourceChunk, ...]) -> str:
    return _digest(
        [
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
    )


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = ["SourceContentError", "SourceLimitError", "StaticMarkdownSource"]
