"""Compatibility adapter between M6a source snapshots and legacy retrieval chunks."""

from __future__ import annotations

from dataclasses import dataclass

from .models import RetrievalChunk
from .protocols import ProtocolValidationError, RetrievalIndex, RetrievalSnapshot, SourceChunk
from .sources.markdown_pack import MarkdownPackSnapshot


@dataclass(slots=True)
class DefaultPackRetrievalIndex:
    """Adapt one complete default-pack snapshot for legacy retrieval consumers."""

    _snapshot: RetrievalSnapshot
    _chunks: tuple[RetrievalChunk, ...]

    @classmethod
    def from_source_snapshot(cls, snapshot: MarkdownPackSnapshot) -> "DefaultPackRetrievalIndex":
        retrieval_snapshot = RetrievalSnapshot(
            generation=snapshot.descriptor.generation,
            chunks=snapshot.chunks,
        )
        return cls.from_retrieval_snapshot(retrieval_snapshot)

    @classmethod
    def from_retrieval_snapshot(cls, snapshot: RetrievalSnapshot) -> "DefaultPackRetrievalIndex":
        chunks = tuple(_to_retrieval_chunk(chunk) for chunk in snapshot.chunks)
        return cls(snapshot, chunks)

    @property
    def generation(self) -> str:
        return self._snapshot.generation

    @property
    def chunks(self) -> tuple[RetrievalChunk, ...]:
        return self._chunks

    def search(self, query: str, top_k: int = 5) -> list[SourceChunk]:
        normalized_query = query.casefold()
        return [
            chunk
            for chunk in self._snapshot.chunks
            if normalized_query in chunk.content.casefold()
        ][:top_k]

    def replace_all(self, snapshot: RetrievalSnapshot) -> None:
        """Atomically publish a complete logical retrieval snapshot."""
        self._snapshot = snapshot
        self._chunks = tuple(_to_retrieval_chunk(chunk) for chunk in snapshot.chunks)


def _to_retrieval_chunk(chunk: SourceChunk) -> RetrievalChunk:
    metadata = chunk.metadata
    course = str(metadata.get("course", ""))
    tags = [str(tag) for tag in metadata.get("tags", ())]
    return RetrievalChunk(
        id=chunk.chunk_id,
        file=f"knowledge/{chunk.identity.logical_uri}",
        title=chunk.title,
        course=course,
        tags=tags,
        difficulty=str(metadata.get("difficulty", "")),
        updated=str(metadata.get("updated", "")),
        content=chunk.content,
    )
