"""Pluggable vector stores used by the retrieval service.

M3a keeps the original in-memory implementation as a rollback/debug backend and
adds a persistent SQLite backend. Both implementations share the same upsert,
search, dimension-validation, and migration contract.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import struct
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Protocol, Sequence, runtime_checkable

from .models import RetrievalChunk

try:  # Optional dependency used only for text -> vector encoding.
    from sentence_transformers import SentenceTransformer

    _ST_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency is absent in CI.
    SentenceTransformer = Any  # type: ignore[assignment,misc]
    _ST_AVAILABLE = False

Vector = list[float]
_SCHEMA_VERSION = "m3a-1"


@runtime_checkable
class VectorStore(Protocol):
    """Common contract shared by all vector-store implementations."""

    def add(self, chunks: list[RetrievalChunk], vectors: list[Vector] | None = None) -> None:
        ...

    def replace_all(self, chunks: list[RetrievalChunk], vectors: list[Vector] | None = None) -> None:
        ...

    def search(
        self,
        query: str | Sequence[float] | None = None,
        top_k: int = 5,
        threshold: float = 0.0,
        *,
        query_vector: Sequence[float] | None = None,
    ) -> list[RetrievalChunk]:
        ...

    def count(self) -> int:
        ...

    def ids(self) -> set[str]:
        ...

    def is_synced(self, chunks: list[RetrievalChunk]) -> bool:
        ...

    def is_available(self) -> bool:
        ...


def _normalise_vectors(vectors: Any) -> list[Vector]:
    return [[float(value) for value in vector] for vector in vectors]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError(
            f"vector dimension mismatch: query={len(a)}, stored={len(b)}"
        )
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1e-9
    norm_b = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (norm_a * norm_b)


def _resolve_query(
    query: str | Sequence[float] | None,
    query_vector: Sequence[float] | None,
) -> str | Sequence[float]:
    """Accept both the legacy positional query and query_vector keyword."""
    if query_vector is not None:
        if query is not None:
            raise TypeError("query and query_vector are mutually exclusive")
        query = query_vector
    if query is None:
        raise TypeError("search() requires query or query_vector")
    return query


def _chunk_fingerprint(chunk: RetrievalChunk) -> str:
    """Hash indexed content and metadata, excluding the transient score field."""
    payload = chunk.model_dump(exclude={"score"})
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass
class _VectorItem:
    chunk: RetrievalChunk
    vector: Vector


class _EmbeddingMixin:
    """Shared encoding and vector validation helpers."""

    @staticmethod
    def encoder_available() -> bool:
        return _ST_AVAILABLE

    def _ensure_model(self) -> None:
        if self._model is None:
            if not _ST_AVAILABLE:
                raise RuntimeError("sentence-transformers is not installed")
            self._model = SentenceTransformer(self.model_name, cache_folder=self.cache_dir)

    def _encode(self, texts: list[str]) -> list[Vector]:
        embedder = getattr(self, "_embedder", None)
        if embedder is None:
            self._ensure_model()
            embedder = self._model
        encoded = embedder.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return _normalise_vectors(encoded)

    def _vectors_for(
        self,
        chunks: list[RetrievalChunk],
        vectors: list[Vector] | None,
    ) -> list[Vector]:
        values = vectors if vectors is not None else self._encode([chunk.content for chunk in chunks])
        values = _normalise_vectors(values)
        if len(values) != len(chunks):
            raise ValueError("vectors length must match chunks length")
        dimensions = {len(vector) for vector in values}
        if not values or not dimensions or 0 in dimensions:
            raise ValueError("vectors must not be empty")
        if len(dimensions) > 1:
            raise ValueError("all vectors must have the same dimension")
        return values

    def _query_vector(self, query: str | Sequence[float]) -> Vector:
        if isinstance(query, str):
            return self._encode([query])[0]
        values = _normalise_vectors([query])
        if not values or not values[0]:
            raise ValueError("query vector must not be empty")
        return values[0]


class LocalVectorStore(_EmbeddingMixin):
    """Original in-memory vector store kept as a simple fallback."""

    def __init__(
        self,
        model_name: str | None = None,
        cache_dir: str | os.PathLike[str] | None = None,
        embedder: Any | None = None,
    ) -> None:
        self.model_name = model_name or "BAAI/bge-small-zh-v1.5"
        self.cache_dir = str(cache_dir) if cache_dir is not None else None
        self._embedder = embedder
        self._model: Any | None = None
        self._items: list[_VectorItem] = []

    @staticmethod
    def available() -> bool:
        return _ST_AVAILABLE

    def is_available(self) -> bool:
        return self._embedder is not None or _ST_AVAILABLE

    def _validate_dimension(self, values: list[Vector]) -> None:
        if self._items and len(values[0]) != len(self._items[0].vector):
            raise ValueError(
                f"vector dimension mismatch: expected={len(self._items[0].vector)}, "
                f"actual={len(values[0])}"
            )

    def add(self, chunks: list[RetrievalChunk], vectors: list[Vector] | None = None) -> None:
        if not chunks:
            return
        values = self._vectors_for(chunks, vectors)
        self._validate_dimension(values)
        by_id = {item.chunk.id: item for item in self._items}
        order = [item.chunk.id for item in self._items]
        for chunk, vector in zip(chunks, values):
            if chunk.id not in by_id:
                order.append(chunk.id)
            by_id[chunk.id] = _VectorItem(chunk, vector)
        self._items = [by_id[chunk_id] for chunk_id in order]

    def replace_all(self, chunks: list[RetrievalChunk], vectors: list[Vector] | None = None) -> None:
        values = self._vectors_for(chunks, vectors) if chunks else []
        self._items = []
        if chunks:
            self._validate_dimension(values)
            self._items = [_VectorItem(chunk, vector) for chunk, vector in zip(chunks, values)]

    def search(
        self,
        query: str | Sequence[float] | None = None,
        top_k: int = 5,
        threshold: float = 0.0,
        *,
        query_vector: Sequence[float] | None = None,
    ) -> list[RetrievalChunk]:
        if top_k <= 0 or not self._items:
            return []
        resolved = _resolve_query(query, query_vector)
        query_vec = self._query_vector(resolved)
        self._validate_query_dimension(query_vec)
        scored = [
            (item, _cosine(query_vec, item.vector))
            for item in self._items
            if _cosine(query_vec, item.vector) >= threshold
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        results: list[RetrievalChunk] = []
        for item, score in scored[:top_k]:
            chunk = item.chunk.model_copy(deep=True)
            chunk.score = round(score, 4)
            results.append(chunk)
        return results

    def _validate_query_dimension(self, query_vector: Sequence[float]) -> None:
        if self._items and len(query_vector) != len(self._items[0].vector):
            raise ValueError(
                f"query vector dimension mismatch: expected={len(self._items[0].vector)}, "
                f"actual={len(query_vector)}"
            )

    def count(self) -> int:
        return len(self._items)

    def ids(self) -> set[str]:
        return {item.chunk.id for item in self._items}

    def is_synced(self, chunks: list[RetrievalChunk]) -> bool:
        if self.count() != len(chunks) or self.ids() != {chunk.id for chunk in chunks}:
            return False
        current = {item.chunk.id: _chunk_fingerprint(item.chunk) for item in self._items}
        return current == {chunk.id: _chunk_fingerprint(chunk) for chunk in chunks}

    def export_items(self) -> list[tuple[RetrievalChunk, Vector]]:
        return [(item.chunk.model_copy(deep=True), list(item.vector)) for item in self._items]


class SqliteVectorStore(_EmbeddingMixin):
    """Persistent SQLite vector store with content and model metadata."""

    def __init__(
        self,
        model_name: str | None = None,
        db_path: str | os.PathLike[str] | None = None,
        cache_dir: str | os.PathLike[str] | None = None,
        embedder: Any | None = None,
    ) -> None:
        self.model_name = model_name or "BAAI/bge-small-zh-v1.5"
        self.cache_dir = str(cache_dir) if cache_dir is not None else None
        self.db_path = Path(db_path) if db_path is not None else self._default_path()
        self._embedder = embedder
        self._model: Any | None = None
        self._memory_connection: sqlite3.Connection | None = (
            sqlite3.connect(":memory:") if str(self.db_path) == ":memory:" else None
        )
        self._initialise()

    @staticmethod
    def _default_path() -> Path:
        from . import config

        return config.VECTOR_STORE_PATH

    @staticmethod
    def available() -> bool:
        # SQLite is part of the Python standard library; encoding is separate.
        return True

    def is_available(self) -> bool:
        return True

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._memory_connection
        owned = connection is None
        if owned:
            connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            if owned:
                connection.close()

    def _initialise(self) -> None:
        if self._memory_connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS vectors (
                    chunk_id TEXT PRIMARY KEY,
                    chunk_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL DEFAULT '',
                    dimension INTEGER NOT NULL,
                    vector BLOB NOT NULL
                )
                """
            )
            # Upgrade databases created by the first M3a draft.
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(vectors)")}
            if "fingerprint" not in columns:
                connection.execute("ALTER TABLE vectors ADD COLUMN fingerprint TEXT NOT NULL DEFAULT ''")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_vectors_dimension ON vectors(dimension)")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS vector_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO vector_metadata(key, value) VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (_SCHEMA_VERSION,),
            )

    @staticmethod
    def _pack(vector: Sequence[float]) -> bytes:
        return struct.pack(f"<{len(vector)}f", *vector)

    @staticmethod
    def _unpack(blob: bytes, dimension: int) -> Vector:
        return list(struct.unpack(f"<{dimension}f", blob))

    def _validate_dimension(self, values: list[Vector], connection: sqlite3.Connection) -> None:
        if not values:
            return
        existing = {row[0] for row in connection.execute("SELECT DISTINCT dimension FROM vectors")}
        if existing and (len(existing) != 1 or next(iter(existing)) != len(values[0])):
            expected = next(iter(existing)) if len(existing) == 1 else sorted(existing)
            raise ValueError(f"vector dimension mismatch: expected={expected}, actual={len(values[0])}")

    def add(self, chunks: list[RetrievalChunk], vectors: list[Vector] | None = None) -> None:
        if not chunks:
            return
        values = self._vectors_for(chunks, vectors)
        with self._connection() as connection:
            self._validate_dimension(values, connection)
            connection.executemany(
                """
                INSERT INTO vectors(chunk_id, chunk_json, fingerprint, dimension, vector)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    chunk_json=excluded.chunk_json,
                    fingerprint=excluded.fingerprint,
                    dimension=excluded.dimension,
                    vector=excluded.vector
                """,
                [
                    (
                        chunk.id,
                        json.dumps(chunk.model_dump(), ensure_ascii=False),
                        _chunk_fingerprint(chunk),
                        len(vector),
                        self._pack(vector),
                    )
                    for chunk, vector in zip(chunks, values)
                ],
            )
            connection.execute("INSERT OR REPLACE INTO vector_metadata(key, value) VALUES ('model_name', ?)", (self.model_name,))

    def replace_all(self, chunks: list[RetrievalChunk], vectors: list[Vector] | None = None) -> None:
        values = self._vectors_for(chunks, vectors) if chunks else []
        with self._connection() as connection:
            connection.execute("DELETE FROM vectors")
            if chunks:
                self._validate_dimension(values, connection)
                connection.executemany(
                    """
                    INSERT INTO vectors(chunk_id, chunk_json, fingerprint, dimension, vector)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            chunk.id,
                            json.dumps(chunk.model_dump(), ensure_ascii=False),
                            _chunk_fingerprint(chunk),
                            len(vector),
                            self._pack(vector),
                        )
                        for chunk, vector in zip(chunks, values)
                    ],
                )
            connection.execute("INSERT OR REPLACE INTO vector_metadata(key, value) VALUES ('model_name', ?)", (self.model_name,))

    def search(
        self,
        query: str | Sequence[float] | None = None,
        top_k: int = 5,
        threshold: float = 0.0,
        *,
        query_vector: Sequence[float] | None = None,
    ) -> list[RetrievalChunk]:
        if top_k <= 0:
            return []
        resolved = _resolve_query(query, query_vector)
        query_vec = self._query_vector(resolved)
        scored: list[tuple[sqlite3.Row, float]] = []
        with self._connection() as connection:
            dimensions = {row[0] for row in connection.execute("SELECT DISTINCT dimension FROM vectors")}
            if not dimensions:
                return []
            if len(dimensions) != 1 or len(query_vec) != next(iter(dimensions)):
                expected = next(iter(dimensions)) if len(dimensions) == 1 else sorted(dimensions)
                raise ValueError(f"query vector dimension mismatch: expected={expected}, actual={len(query_vec)}")
            rows = connection.execute("SELECT chunk_json, dimension, vector FROM vectors")
            for row in rows:
                score = _cosine(query_vec, self._unpack(row["vector"], row["dimension"]))
                if score >= threshold:
                    scored.append((row, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        results: list[RetrievalChunk] = []
        for row, score in scored[:top_k]:
            chunk = RetrievalChunk(**json.loads(row["chunk_json"]))
            chunk.score = round(score, 4)
            results.append(chunk)
        return results

    def count(self) -> int:
        with self._connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM vectors").fetchone()[0])

    def ids(self) -> set[str]:
        with self._connection() as connection:
            return {row[0] for row in connection.execute("SELECT chunk_id FROM vectors")}

    def is_synced(self, chunks: list[RetrievalChunk]) -> bool:
        with self._connection() as connection:
            metadata = connection.execute("SELECT value FROM vector_metadata WHERE key='model_name'").fetchone()
            if not metadata or metadata[0] != self.model_name:
                return False
            rows = connection.execute("SELECT chunk_id, fingerprint FROM vectors")
            stored = {row[0]: row[1] for row in rows}
        expected = {chunk.id: _chunk_fingerprint(chunk) for chunk in chunks}
        return stored == expected

    def export_items(self) -> list[tuple[RetrievalChunk, Vector]]:
        items: list[tuple[RetrievalChunk, Vector]] = []
        with self._connection() as connection:
            rows = connection.execute("SELECT chunk_json, dimension, vector FROM vectors")
            for row in rows:
                items.append((RetrievalChunk(**json.loads(row["chunk_json"])), self._unpack(row["vector"], row["dimension"])))
        return items

    def close(self) -> None:
        if self._memory_connection is not None:
            self._memory_connection.close()
            self._memory_connection = None


def migrate_store(source: Any, target: VectorStore) -> int:
    """Copy encoded items between stores without re-encoding text."""
    if not hasattr(source, "export_items"):
        raise TypeError("source must provide export_items()")
    items = source.export_items()
    target.replace_all([chunk for chunk, _ in items], [vector for _, vector in items])
    return len(items)
