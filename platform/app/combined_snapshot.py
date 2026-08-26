"""Immutable combined retrieval snapshots for startup-configured sources."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import config
from .models import RetrievalChunk
from .protocols import ProtocolValidationError, SourceChunk
from .retrieval import RetrievalScope
from .retrieval_index import DefaultPackRetrievalIndex
from .source_config import (
    SourceConfigError,
    SourceLimits,
    StaticSourceConfig,
    parse_extra_sources,
    parse_extra_sources_strict,
    parse_source_limits,
)
from .sources.markdown_pack import DEFAULT_SOURCE_ID, MarkdownPackSource
from .sources.static_markdown import (
    SourceContentError,
    SourceLimitError,
    StaticMarkdownSource,
)


class CombinedSnapshotError(RuntimeError):
    """Safe complete-candidate failure."""

    code = "SNAPSHOT_BUILD_FAILED"


@dataclass(frozen=True, slots=True)
class CombinedRetrievalSnapshot:
    """One immutable generation exposing two explicit source views."""

    generation: str
    default_generation: str
    default_revision: str
    default_chunks: tuple[RetrievalChunk, ...]
    combined_chunks: tuple[RetrievalChunk, ...]
    source_ids: tuple[str, ...]
    source_generations: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.generation or not self.default_generation or not self.default_revision:
            raise CombinedSnapshotError("snapshot metadata is invalid")
        if not self.default_chunks:
            raise CombinedSnapshotError("default source contains no retrieval chunks")
        if self.source_ids != tuple(source_id for source_id, _ in self.source_generations):
            raise CombinedSnapshotError("snapshot source metadata is invalid")
        default_ids = {chunk.id for chunk in self.default_chunks}
        combined_ids = [chunk.id for chunk in self.combined_chunks]
        if not default_ids.issubset(combined_ids) or len(combined_ids) != len(set(combined_ids)):
            raise CombinedSnapshotError("snapshot chunk identities are invalid")
        for chunk in self.default_chunks:
            if not chunk.file.startswith("knowledge/"):
                raise CombinedSnapshotError("default provenance is invalid")
        for chunk in self.combined_chunks[len(self.default_chunks) :]:
            if not chunk.file.startswith("extra://"):
                raise CombinedSnapshotError("extra provenance is invalid")

    def view(self, scope: RetrievalScope) -> tuple[str, list[RetrievalChunk]]:
        if scope is RetrievalScope.DEFAULT_ONLY:
            generation = self.default_generation
            chunks = self.default_chunks
        else:
            generation = self.generation
            chunks = self.combined_chunks
        return generation, [chunk.model_copy(deep=True) for chunk in chunks]


class CombinedSnapshotBuilder:
    """Build a complete default-plus-extras candidate without publishing it."""

    def __init__(
        self,
        default_root: Path,
        extras: tuple[StaticSourceConfig, ...],
        limits: SourceLimits,
        *,
        strict: bool,
    ) -> None:
        self._default_root = default_root
        self._extras = extras
        self._limits = limits
        self._strict = strict

    def build(self) -> CombinedRetrievalSnapshot:
        try:
            default_source = MarkdownPackSource(self._default_root).materialize()
            default_files, default_bytes = _measure_default_source(
                self._default_root,
                self._limits,
            )
        except (OSError, UnicodeError, ProtocolValidationError, ValueError) as exc:
            raise SourceContentError("source knowledge-pack contains invalid content") from exc
        _check_source_limits(
            DEFAULT_SOURCE_ID,
            default_files,
            default_bytes,
            len(default_source.chunks),
            self._limits,
        )

        default_index = DefaultPackRetrievalIndex.from_source_snapshot(default_source)
        default_chunks = default_index.chunks
        combined_chunks = list(default_chunks)
        source_generations = [
            (default_source.descriptor.source_id, default_source.descriptor.generation)
        ]
        total_files = default_files
        total_bytes = default_bytes
        total_chunks = len(default_source.chunks)

        for source_config in self._extras:
            source = StaticMarkdownSource(source_config, self._limits)
            try:
                source_snapshot = source.materialize()
                candidate_files = total_files + source.file_count
                candidate_bytes = total_bytes + source.byte_count
                candidate_chunks = total_chunks + len(source_snapshot.chunks)
                _check_aggregate_limits(
                    candidate_files,
                    candidate_bytes,
                    candidate_chunks,
                    self._limits,
                )
            except (SourceContentError, SourceLimitError, OSError, UnicodeError):
                if self._strict:
                    raise
                continue
            total_files = candidate_files
            total_bytes = candidate_bytes
            total_chunks = candidate_chunks
            combined_chunks.extend(
                _extra_retrieval_chunk(chunk) for chunk in source_snapshot.chunks
            )
            source_generations.append(
                (source_snapshot.descriptor.source_id, source_snapshot.descriptor.generation)
            )

        _check_aggregate_limits(total_files, total_bytes, total_chunks, self._limits)
        source_ids = tuple(source_id for source_id, _ in source_generations)
        generation = _digest(
            {
                "schema": "sa.combined-retrieval-snapshot.v1",
                "sources": source_generations,
                "default_count": len(default_chunks),
                "combined_count": len(combined_chunks),
            }
        )
        return CombinedRetrievalSnapshot(
            generation=generation,
            default_generation=default_source.descriptor.generation,
            default_revision=default_source.descriptor.revision,
            default_chunks=default_chunks,
            combined_chunks=tuple(combined_chunks),
            source_ids=source_ids,
            source_generations=tuple(source_generations),
        )


def build_configured_snapshot() -> CombinedRetrievalSnapshot:
    """Parse startup configuration and build one complete immutable candidate."""
    limits = parse_source_limits()
    extras = parse_extra_sources(
        default_root=config.KNOWLEDGE_ROOT,
        repository_root=config.REPO_ROOT,
        crawler_cache_root=_crawler_cache_root(),
    )
    builder = CombinedSnapshotBuilder(
        config.KNOWLEDGE_ROOT,
        extras,
        limits,
        strict=parse_extra_sources_strict(),
    )
    try:
        return builder.build()
    except (SourceConfigError, SourceContentError, SourceLimitError):
        raise
    except (OSError, UnicodeError, ProtocolValidationError, ValueError) as exc:
        raise CombinedSnapshotError("snapshot candidate is invalid") from exc


def _measure_default_source(
    root: Path,
    limits: SourceLimits,
) -> tuple[int, int]:
    from .source_policy import is_indexable_relative_path

    resolved_root = root.resolve(strict=True)
    files = 0
    size = 0
    for path in sorted(resolved_root.rglob("*.md")):
        resolved = path.resolve(strict=True)
        try:
            logical_uri = resolved.relative_to(resolved_root).as_posix()
        except ValueError as exc:
            raise SourceContentError("source knowledge-pack contains an unsafe link") from exc
        if not is_indexable_relative_path(logical_uri):
            continue
        file_size = resolved.stat().st_size
        if file_size > limits.max_file_bytes:
            raise SourceLimitError("source knowledge-pack exceeds the single-file limit")
        files += 1
        size += file_size
    return files, size


def _check_source_limits(
    source_id: str,
    files: int,
    size: int,
    chunks: int,
    limits: SourceLimits,
) -> None:
    if (
        files > limits.max_files_per_source
        or size > limits.max_bytes_per_source
        or chunks > limits.max_chunks_per_source
    ):
        raise SourceLimitError(f"source {source_id} exceeds configured limits")


def _check_aggregate_limits(
    files: int,
    size: int,
    chunks: int,
    limits: SourceLimits,
) -> None:
    if (
        files > limits.max_files_total
        or size > limits.max_bytes_total
        or chunks > limits.max_chunks_total
    ):
        raise SourceLimitError("combined sources exceed configured limits")


def _extra_retrieval_chunk(chunk: SourceChunk) -> RetrievalChunk:
    metadata = chunk.metadata
    return RetrievalChunk(
        id=chunk.chunk_id,
        file=f"extra://{chunk.identity.source_id}/{chunk.identity.logical_uri}",
        title=chunk.title,
        course=str(metadata.get("course", "")),
        tags=[str(tag) for tag in metadata.get("tags", ())],
        difficulty=str(metadata.get("difficulty", "")),
        updated=str(metadata.get("updated", "")),
        content=chunk.content,
    )


def _crawler_cache_root() -> Path | None:
    raw = os.getenv("SA_CRAWLER_CANDIDATE_CACHE", "")
    return Path(raw) if raw else None


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "CombinedRetrievalSnapshot",
    "CombinedSnapshotBuilder",
    "CombinedSnapshotError",
    "build_configured_snapshot",
]
