"""Generation-bound source-local SQLite vector index for M7 user sources.

FTS5 and vector are built from the same normalized published generation.
This module does not mutate default-pack SqliteVectorStore/LocalVectorStore
fallback behavior, Quiz, Review Plan, study-sessions, or M6b preview.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import sqlite3
import struct
import threading
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from importlib import metadata
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Protocol, Sequence
from uuid import uuid4

try:
    import numpy as np
except Exception:  # pragma: no cover - optional acceleration
    np = None

from . import config
from .normalized_document import CHUNK_SCHEMA_VERSION
from .source_manifest import canonical_json
from .user_source_fts5 import identity_set, identity_set_digest
from .user_source_snapshot import FullSnapshot


VECTOR_SCHEMA_VERSION = "sa.source.vector.v1"
VECTOR_STATUS_ATTACHED = "attached"
VECTOR_INDEX_TYPE = "linear_cosine"
HASH_EMBEDDING_MODEL = "sa.source.vector.hash.v1"
HASH_EMBEDDING_VERSION = "hash-charngram-v1"
BGE_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"


class VectorIndexErrorCode(StrEnum):
    BUILD_FAILED = "SOURCE_OFFLINE_INDEX_INVALID"
    PUBLICATION_FAILED = "SOURCE_OFFLINE_INDEX_INVALID"
    INDEX_INVALID = "SOURCE_OFFLINE_INDEX_INVALID"
    REPAIR_REQUIRED = "SOURCE_OFFLINE_REPAIR_REQUIRED"
    DEPENDENCY_UNAVAILABLE = "SOURCE_OFFLINE_DEPENDENCY_UNAVAILABLE"


_ERROR_MESSAGES: Mapping[VectorIndexErrorCode, str] = MappingProxyType(
    {
        VectorIndexErrorCode.BUILD_FAILED: "The source index is invalid.",
        VectorIndexErrorCode.PUBLICATION_FAILED: "The source index is invalid.",
        VectorIndexErrorCode.INDEX_INVALID: "The source index is invalid.",
        VectorIndexErrorCode.REPAIR_REQUIRED: "The source index requires an explicit FULL repair.",
        VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE: "A required source dependency is unavailable.",
    }
)


class VectorIndexError(RuntimeError):
    """Stable, content-free vector index failure."""

    def __init__(self, code: VectorIndexErrorCode) -> None:
        self.code = code
        self.repair_category = {
            VectorIndexErrorCode.BUILD_FAILED: "rebuild-source-index-full",
            VectorIndexErrorCode.PUBLICATION_FAILED: "rebuild-source-index-full",
            VectorIndexErrorCode.INDEX_INVALID: "rebuild-source-index-full",
            VectorIndexErrorCode.REPAIR_REQUIRED: "rebuild-source-index-full",
            VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE: "repair-local-dependency",
        }[code]
        super().__init__(_ERROR_MESSAGES[code])


@dataclass(frozen=True, slots=True)
class VectorHit:
    source_id: str
    document_id: str
    chunk_id: str
    generation: str
    rank: int
    score: float


class VectorEmbedder(Protocol):
    model_name: str
    version: str
    dimension: int
    normalize: bool

    def require_runtime(self) -> None:
        ...

    def encode(self, texts: list[str]) -> list[list[float]]:
        ...

    def metadata(self) -> dict[str, str]:
        ...


def sentence_transformers_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        return False
    return True


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector)) or 1e-9
    return [value / norm for value in vector]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
    return sum(a * b for a, b in zip(left, right))


class HashVectorEmbedder:
    """Deterministic character-ngram embedder for M7 contract tests."""

    def __init__(self, *, dimension: int | None = None) -> None:
        self.model_name = HASH_EMBEDDING_MODEL
        self.version = HASH_EMBEDDING_VERSION
        self.dimension = int(dimension or config.EMBEDDING_EXPECTED_DIM)
        self.normalize = True
        if self.dimension <= 0:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)

    def require_runtime(self) -> None:
        return None

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [_l2_normalize(self._embed(text)) for text in texts]

    def metadata(self) -> dict[str, str]:
        return {
            "vector_schema": VECTOR_SCHEMA_VERSION,
            "embedding_model": self.model_name,
            "embedding_version": self.version,
            "embedding_dim": str(self.dimension),
            "embedding_normalize": "true",
            "chunk_schema_version": CHUNK_SCHEMA_VERSION,
            "vector_index_type": VECTOR_INDEX_TYPE,
        }

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        normalized = unicodedata.normalize("NFC", text).casefold()
        if not normalized:
            vector[0] = 1.0
            return vector
        for index, char in enumerate(normalized):
            self._accumulate(vector, char.encode("utf-8"))
            if index + 1 < len(normalized):
                self._accumulate(vector, (char + normalized[index + 1]).encode("utf-8"))
        return vector

    def _accumulate(self, vector: list[float], payload: bytes) -> None:
        digest = hashlib.sha256(payload).digest()
        bucket = int.from_bytes(digest[:4], "little") % self.dimension
        vector[bucket] += 1.0


class SentenceTransformerEmbedder:
    """Frozen BGE embedder for production M7 user-source vectors."""

    def __init__(self) -> None:
        self.model_name = config.EMBEDDING_MODEL
        self.dimension = int(config.EMBEDDING_EXPECTED_DIM)
        self.normalize = bool(config.EMBEDDING_NORMALIZE)
        self._model = None
        self.version = self._package_version()

    @staticmethod
    def _package_version() -> str:
        try:
            installed = metadata.version("sentence-transformers")
        except metadata.PackageNotFoundError:
            return "sentence-transformers-missing"
        return f"sentence-transformers-{installed}"

    def require_runtime(self) -> None:
        if not sentence_transformers_available() or self.model_name != BGE_EMBEDDING_MODEL:
            raise VectorIndexError(VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE)
        if self.dimension != int(config.EMBEDDING_EXPECTED_DIM) or self.dimension <= 0:
            raise VectorIndexError(VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE)
        try:
            metadata.version("sentence-transformers")
        except metadata.PackageNotFoundError as exc:
            raise VectorIndexError(VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE) from exc

    def _ensure_model(self):
        self.require_runtime()
        if self._model is not None:
            return self._model
        try:
            import torch
            from sentence_transformers import SentenceTransformer

            torch.set_grad_enabled(False)
            threads = max(1, min(4, int(torch.get_num_threads() or 1)))
            torch.set_num_threads(threads)
            model = SentenceTransformer(self.model_name, local_files_only=True)
            model.eval()
            self._torch = torch
            self._model = model
        except Exception as exc:
            raise VectorIndexError(VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE) from exc
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_model()
        with self._torch.inference_mode():
            encoded = model.encode(
                texts,
                batch_size=32,
                convert_to_numpy=True,
                normalize_embeddings=self.normalize,
                show_progress_bar=False,
            )
        values = encoded.tolist()
        if any(len(vector) != self.dimension for vector in values):
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
        return values

    def metadata(self) -> dict[str, str]:
        return {
            "vector_schema": VECTOR_SCHEMA_VERSION,
            "embedding_model": self.model_name,
            "embedding_version": self.version,
            "embedding_dim": str(self.dimension),
            "embedding_normalize": "true" if self.normalize else "false",
            "chunk_schema_version": CHUNK_SCHEMA_VERSION,
            "vector_index_type": VECTOR_INDEX_TYPE,
        }


@dataclass(frozen=True, slots=True)
class VectorIndexMetadata:
    source_id: str
    generation: str
    revision_no: int
    chunk_count: int
    identity_set_digest: str
    content_digest: str
    build_input_digest: str
    snapshot_fingerprint: str
    embedding_model: str
    embedding_version: str
    embedding_dim: int
    embedding_normalize: bool
    chunk_schema_version: str
    vector_index_type: str
    vector_status: str = VECTOR_STATUS_ATTACHED
    schema_name: str = VECTOR_SCHEMA_VERSION
    offline_schema: str = "sa.source.offline-fallback.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_name": self.schema_name,
            "offline_schema": self.offline_schema,
            "source_id": self.source_id,
            "generation": self.generation,
            "revision_no": self.revision_no,
            "chunk_count": self.chunk_count,
            "identity_set_digest": self.identity_set_digest,
            "content_digest": self.content_digest,
            "build_input_digest": self.build_input_digest,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "embedding_model": self.embedding_model,
            "embedding_version": self.embedding_version,
            "embedding_dim": self.embedding_dim,
            "embedding_normalize": self.embedding_normalize,
            "chunk_schema_version": self.chunk_schema_version,
            "vector_index_type": self.vector_index_type,
            "vector_status": self.vector_status,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: object) -> "VectorIndexMetadata":
        if not isinstance(payload, dict) or payload.get("schema_name") != VECTOR_SCHEMA_VERSION:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
        try:
            metadata = cls(
                source_id=str(payload.get("source_id")),
                generation=str(payload.get("generation")),
                revision_no=int(payload.get("revision_no", -1)),
                chunk_count=int(payload.get("chunk_count", -1)),
                identity_set_digest=str(payload.get("identity_set_digest")),
                content_digest=str(payload.get("content_digest")),
                build_input_digest=str(payload.get("build_input_digest")),
                snapshot_fingerprint=str(payload.get("snapshot_fingerprint")),
                embedding_model=str(payload.get("embedding_model")),
                embedding_version=str(payload.get("embedding_version")),
                embedding_dim=int(payload.get("embedding_dim", -1)),
                embedding_normalize=bool(payload.get("embedding_normalize")),
                chunk_schema_version=str(payload.get("chunk_schema_version")),
                vector_index_type=str(payload.get("vector_index_type")),
                vector_status=str(payload.get("vector_status", "")),
                schema_name=str(payload.get("schema_name")),
                offline_schema=str(payload.get("offline_schema", "")),
            )
        except (TypeError, ValueError) as exc:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID) from exc
        if metadata.canonical_bytes() != canonical_json(payload):
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
        if (
            metadata.revision_no < 1
            or metadata.chunk_count < 0
            or metadata.embedding_dim <= 0
            or metadata.vector_status != VECTOR_STATUS_ATTACHED
            or metadata.chunk_schema_version != CHUNK_SCHEMA_VERSION
            or metadata.vector_index_type != VECTOR_INDEX_TYPE
        ):
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
        return metadata


@dataclass(slots=True)
class _VectorRuntime:
    source_id: str
    generation: str
    metadata: VectorIndexMetadata
    metadata_digest: str
    sqlite_path: Path
    sqlite_size: int
    sqlite_mtime_ns: int
    identity_pairs: tuple[tuple[str, str], ...]
    matrix: object


def _file_fingerprint(path: Path) -> tuple[int, int]:
    stat = path.stat()
    mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))
    return int(stat.st_size), int(mtime_ns)


def _read_vector_identity(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    rows = connection.execute(
        "SELECT chunk_id, document_id FROM vectors ORDER BY chunk_id, document_id"
    ).fetchall()
    return tuple((str(row["chunk_id"]), str(row["document_id"])) for row in rows)


def _hits_from_matrix(runtime: _VectorRuntime, query_vector: Sequence[float], *, top_k: int) -> tuple[VectorHit, ...]:
    limit = max(int(top_k), 0)
    if not runtime.identity_pairs or limit == 0:
        return ()
    if np is not None and not isinstance(runtime.matrix, list):
        query = np.asarray(query_vector, dtype=np.float32)
        if query.shape[0] != runtime.metadata.embedding_dim:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
        scores = runtime.matrix @ query
        count = min(limit, int(scores.shape[0]))
        if count == int(scores.shape[0]):
            order = np.argsort(-scores, kind="stable")
        else:
            part = np.argpartition(-scores, count - 1)[:count]
            order = part[np.argsort(-scores[part], kind="stable")]
        hits = []
        for rank, index in enumerate((int(item) for item in order.tolist()), start=1):
            chunk_id, document_id = runtime.identity_pairs[index]
            hits.append(
                VectorHit(
                    source_id=runtime.source_id,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    generation=runtime.generation,
                    rank=rank,
                    score=round(float(scores[index]), 4),
                )
            )
        return tuple(hits)
    scored: list[tuple[str, str, float]] = []
    for (chunk_id, document_id), vector in zip(runtime.identity_pairs, runtime.matrix):
        scored.append((chunk_id, document_id, _cosine(query_vector, vector)))
    scored.sort(key=lambda item: item[2], reverse=True)
    hits = []
    for rank, (chunk_id, document_id, score) in enumerate(scored[:limit], start=1):
        hits.append(
            VectorHit(
                source_id=runtime.source_id,
                document_id=document_id,
                chunk_id=chunk_id,
                generation=runtime.generation,
                rank=rank,
                score=round(score, 4),
            )
        )
    return tuple(hits)


class UserSourceVectorIndex:
    """Build and read one generation-bound vector index per user source."""

    def __init__(
        self,
        cache_root: str | Path,
        *,
        embedder: VectorEmbedder | None = None,
    ) -> None:
        self._root = Path(cache_root) / "user-source-vector" / "v1"
        self._embedder = embedder or SentenceTransformerEmbedder()
        self._lock = threading.RLock()
        self._runtimes: dict[tuple[str, str], "_VectorRuntime"] = {}

    @property
    def embedder(self) -> VectorEmbedder:
        return self._embedder

    def require_runtime(self) -> None:
        try:
            self._embedder.require_runtime()
        except VectorIndexError:
            raise
        except Exception as exc:
            raise VectorIndexError(VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE) from exc

    def published_path(self, source_id: str, generation: str | None = None) -> Path | None:
        root = self._root / source_id
        if generation is None:
            generation_name = self._pointer_value(root / "CURRENT")
            if generation_name is None:
                return None
            path = root / generation_name
        else:
            path = root / f"gen-{generation}"
        return path if path.is_dir() else None

    def load_metadata(self, source_id: str, generation: str | None = None) -> VectorIndexMetadata | None:
        path = self.published_path(source_id, generation)
        if path is None:
            return None
        return self._load_metadata(path)

    def chunk_ids(self, source_id: str, generation: str) -> set[str]:
        runtime = self._ensure_runtime(source_id, generation)
        return {chunk_id for chunk_id, _document_id in runtime.identity_pairs}

    def build(
        self,
        snapshot: FullSnapshot,
        *,
        revision_no: int,
        activate: bool = True,
    ) -> VectorIndexMetadata:
        with self._lock:
            self._drop_runtimes(snapshot.source_id)
            metadata = self._materialize(snapshot, revision_no=revision_no)
            if activate:
                self._activate(snapshot.source_id, snapshot.generation)
            return metadata

    def encode_query(self, query: str) -> list[float]:
        try:
            encoded = self._embedder.encode([query])
        except VectorIndexError:
            raise
        except Exception as exc:
            raise VectorIndexError(VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE) from exc
        if not encoded:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
        return encoded[0]

    def search(
        self,
        source_id: str,
        generation: str,
        query: str,
        *,
        top_k: int = 5,
        query_vector: list[float] | None = None,
    ) -> tuple[VectorHit, ...]:
        runtime = self._runtimes.get((source_id, generation)) or self._ensure_runtime(source_id, generation)
        if top_k <= 0:
            return ()
        vector = query_vector if query_vector is not None else self.encode_query(query)
        if len(vector) != runtime.metadata.embedding_dim:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
        return _hits_from_matrix(
            runtime,
            vector,
            top_k=top_k,
        )

    def validate(
        self,
        source_id: str,
        generation: str,
        snapshot: FullSnapshot | None = None,
        *,
        revision_no: int | None = None,
    ) -> VectorIndexMetadata:
        return self._ensure_runtime(
            source_id,
            generation,
            snapshot,
            revision_no=revision_no,
        ).metadata

    def _drop_runtimes(self, source_id: str | None = None) -> None:
        if source_id is None:
            self._runtimes.clear()
            return
        for key in [item for item in self._runtimes if item[0] == source_id]:
            del self._runtimes[key]

    def _ensure_runtime(
        self,
        source_id: str,
        generation: str,
        snapshot: FullSnapshot | None = None,
        *,
        revision_no: int | None = None,
    ) -> "_VectorRuntime":
        self.require_runtime()
        with self._lock:
            path = self.published_path(source_id, generation)
            if path is None:
                raise VectorIndexError(VectorIndexErrorCode.REPAIR_REQUIRED)
            metadata = self._load_metadata(path)
            expected = self._embedder.metadata()
            if (
                metadata.source_id != source_id
                or metadata.generation != generation
                or metadata.embedding_model != expected["embedding_model"]
                or metadata.embedding_version != expected["embedding_version"]
                or str(metadata.embedding_dim) != expected["embedding_dim"]
                or metadata.chunk_schema_version != expected["chunk_schema_version"]
                or metadata.vector_index_type != expected["vector_index_type"]
                or metadata.vector_status != VECTOR_STATUS_ATTACHED
            ):
                raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
            if revision_no is not None and metadata.revision_no != revision_no:
                raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
            if snapshot is not None and (
                snapshot.source_id != source_id
                or snapshot.generation != generation
                or snapshot.source_fingerprint != metadata.snapshot_fingerprint
                or identity_set_digest(snapshot) != metadata.identity_set_digest
                or snapshot.chunk_count != metadata.chunk_count
            ):
                raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
            sqlite_path = path / "index.sqlite3"
            try:
                sqlite_size, sqlite_mtime_ns = _file_fingerprint(sqlite_path)
                metadata_digest = (path / "SHA256").read_text(encoding="ascii").strip()
            except OSError as exc:
                raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID) from exc
            key = (source_id, generation)
            cached = self._runtimes.get(key)
            if (
                cached is not None
                and cached.metadata_digest == metadata_digest
                and cached.sqlite_size == sqlite_size
                and cached.sqlite_mtime_ns == sqlite_mtime_ns
                and cached.matrix is not None
            ):
                cached.metadata = metadata
                return cached
            connection: sqlite3.Connection | None = None
            try:
                connection = sqlite3.connect(str(sqlite_path))
                connection.row_factory = sqlite3.Row
                identity_pairs = _read_vector_identity(connection)
                identity = sorted([[document_id, chunk_id] for chunk_id, document_id in identity_pairs])
                digest = hashlib.sha256(canonical_json(identity)).hexdigest()
                if digest != metadata.identity_set_digest or len(identity_pairs) != metadata.chunk_count:
                    raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
                if snapshot is not None and identity_set(snapshot) != identity:
                    raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
                if (
                    cached is not None
                    and cached.metadata_digest == metadata_digest
                    and cached.sqlite_size == sqlite_size
                    and cached.sqlite_mtime_ns == sqlite_mtime_ns
                    and cached.metadata.identity_set_digest == digest
                    and cached.matrix is not None
                    and cached.identity_pairs == identity_pairs
                ):
                    cached.metadata = metadata
                    return cached
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                if integrity is None or str(integrity[0]) != "ok":
                    raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
                loaded_pairs, matrix = self._load_matrix(connection, metadata, source_id, generation)
                if loaded_pairs != identity_pairs:
                    raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
                runtime = _VectorRuntime(
                    source_id=source_id,
                    generation=generation,
                    metadata=metadata,
                    metadata_digest=metadata_digest,
                    sqlite_path=sqlite_path,
                    sqlite_size=sqlite_size,
                    sqlite_mtime_ns=sqlite_mtime_ns,
                    identity_pairs=identity_pairs,
                    matrix=matrix,
                )
                self._runtimes[key] = runtime
                return runtime
            except VectorIndexError:
                self._runtimes.pop(key, None)
                raise
            except sqlite3.Error as exc:
                self._runtimes.pop(key, None)
                raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID) from exc
            finally:
                if connection is not None:
                    connection.close()

    def _load_matrix(
        self,
        connection: sqlite3.Connection,
        metadata: VectorIndexMetadata,
        source_id: str,
        generation: str,
    ) -> tuple[tuple[tuple[str, str], ...], object]:
        try:
            rows = connection.execute(
                """
                SELECT chunk_id, document_id, source_id, generation, revision_no, dimension, vector
                FROM vectors
                ORDER BY chunk_id, document_id
                """
            ).fetchall()
        except sqlite3.Error as exc:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID) from exc
        pairs: list[tuple[str, str]] = []
        blobs: list[bytes] = []
        expected_bytes = metadata.embedding_dim * 4
        for row in rows:
            if (
                str(row["source_id"]) != source_id
                or str(row["generation"]) != generation
                or int(row["revision_no"]) != metadata.revision_no
                or int(row["dimension"]) != metadata.embedding_dim
            ):
                raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
            blob = bytes(row["vector"])
            if len(blob) != expected_bytes:
                raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
            pairs.append((str(row["chunk_id"]), str(row["document_id"])))
            blobs.append(blob)
        if np is not None:
            if blobs:
                matrix = np.frombuffer(b"".join(blobs), dtype=np.float32).reshape(
                    len(blobs),
                    metadata.embedding_dim,
                )
                if not matrix.flags.writeable:
                    matrix = np.array(matrix, copy=True)
            else:
                matrix = np.empty((0, metadata.embedding_dim), dtype=np.float32)
        else:
            matrix = [self._unpack(blob, metadata.embedding_dim) for blob in blobs]
        return tuple(pairs), matrix

    def _materialize(self, snapshot: FullSnapshot, *, revision_no: int) -> VectorIndexMetadata:
        if not isinstance(revision_no, int) or isinstance(revision_no, bool) or revision_no < 1:
            raise VectorIndexError(VectorIndexErrorCode.BUILD_FAILED)
        root = self._root / snapshot.source_id
        root.mkdir(parents=True, exist_ok=True)
        staging = root / f".staging-{uuid4().hex}"
        generation = root / f"gen-{snapshot.generation}"
        try:
            staging.mkdir()
            metadata = self._write_index(staging, snapshot, revision_no=revision_no)
            payload = metadata.canonical_bytes()
            self._write_fsynced(staging / "metadata.json", payload)
            self._write_fsynced(
                staging / "SHA256",
                hashlib.sha256(payload).hexdigest().encode("ascii") + b"\n",
            )
            self._fsync_directory(staging)
            if generation.exists():
                if not self._is_valid_generation(generation, metadata):
                    raise VectorIndexError(VectorIndexErrorCode.PUBLICATION_FAILED)
                self._discard_staging(staging)
            else:
                os.replace(staging, generation)
                self._fsync_directory(root)
            return metadata
        except VectorIndexError:
            self._discard_staging(staging)
            raise
        except Exception:
            self._discard_staging(staging)
            raise

    def _activate(self, source_id: str, generation: str) -> None:
        self._drop_runtimes(source_id)
        root = self._root / source_id
        generation_name = f"gen-{generation}"
        path = root / generation_name
        if not path.is_dir():
            raise VectorIndexError(VectorIndexErrorCode.PUBLICATION_FAILED)
        previous = self._pointer_value(root / "CURRENT")
        if previous is not None and previous != generation_name:
            self._switch_pointer(root / "PREVIOUS", previous)
        self._switch_pointer(root / "CURRENT", generation_name)

    def _write_index(
        self,
        staging: Path,
        snapshot: FullSnapshot,
        *,
        revision_no: int,
    ) -> VectorIndexMetadata:
        self.require_runtime()
        versions = self._embedder.metadata()
        rows: list[tuple[str, str, str]] = []
        for document in snapshot.documents:
            for chunk in document.chunks():
                rows.append((chunk.chunk_id, chunk.document_id, chunk.content))
        try:
            vectors = self._embedder.encode([content for _chunk_id, _document_id, content in rows]) if rows else []
        except VectorIndexError:
            raise
        except Exception as exc:
            raise VectorIndexError(VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE) from exc
        if len(vectors) != len(rows):
            raise VectorIndexError(VectorIndexErrorCode.BUILD_FAILED)
        if any(len(vector) != self._embedder.dimension for vector in vectors):
            raise VectorIndexError(VectorIndexErrorCode.BUILD_FAILED)
        sqlite_path = staging / "index.sqlite3"
        connection = sqlite3.connect(sqlite_path)
        try:
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute(
                """
                CREATE TABLE vectors (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    generation TEXT NOT NULL,
                    revision_no INTEGER NOT NULL,
                    dimension INTEGER NOT NULL,
                    vector BLOB NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX idx_vectors_identity ON vectors(source_id, generation, chunk_id)"
            )
            connection.execute("CREATE INDEX idx_vectors_document ON vectors(document_id)")
            connection.executemany(
                """
                INSERT INTO vectors(
                    chunk_id, document_id, source_id, generation, revision_no, dimension, vector
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk_id,
                        document_id,
                        snapshot.source_id,
                        snapshot.generation,
                        revision_no,
                        len(vector),
                        self._pack(vector),
                    )
                    for (chunk_id, document_id, _content), vector in zip(rows, vectors)
                ],
            )
            connection.commit()
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or str(integrity[0]) != "ok":
                raise VectorIndexError(VectorIndexErrorCode.BUILD_FAILED)
        except VectorIndexError:
            raise
        except sqlite3.Error as exc:
            raise VectorIndexError(VectorIndexErrorCode.BUILD_FAILED) from exc
        finally:
            connection.close()
        identity_digest = identity_set_digest(snapshot)
        stored_identity = sorted([[document_id, chunk_id] for chunk_id, document_id, _content in rows])
        if hashlib.sha256(canonical_json(stored_identity)).hexdigest() != identity_digest:
            raise VectorIndexError(VectorIndexErrorCode.BUILD_FAILED)
        if stored_identity != identity_set(snapshot):
            raise VectorIndexError(VectorIndexErrorCode.BUILD_FAILED)
        content_digest = hashlib.sha256(
            canonical_json(
                [
                    {"chunk_id": chunk_id, "document_id": document_id, "content": content}
                    for chunk_id, document_id, content in rows
                ]
            )
        ).hexdigest()
        build_input = canonical_json(
            {
                "embedder": versions,
                "source_id": snapshot.source_id,
                "generation": snapshot.generation,
                "revision_no": revision_no,
                "snapshot_fingerprint": snapshot.source_fingerprint,
                "identity_set_digest": identity_digest,
                "chunk_schema_version": CHUNK_SCHEMA_VERSION,
            }
        )
        return VectorIndexMetadata(
            source_id=snapshot.source_id,
            generation=snapshot.generation,
            revision_no=revision_no,
            chunk_count=len(rows),
            identity_set_digest=identity_digest,
            content_digest=content_digest,
            build_input_digest=hashlib.sha256(build_input).hexdigest(),
            snapshot_fingerprint=snapshot.source_fingerprint,
            embedding_model=versions["embedding_model"],
            embedding_version=versions["embedding_version"],
            embedding_dim=int(versions["embedding_dim"]),
            embedding_normalize=versions["embedding_normalize"] == "true",
            chunk_schema_version=versions["chunk_schema_version"],
            vector_index_type=versions["vector_index_type"],
        )

    def _load_metadata(self, path: Path) -> VectorIndexMetadata:
        try:
            payload = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
            digest = (path / "SHA256").read_text(encoding="ascii").strip()
        except (OSError, json.JSONDecodeError, UnicodeError) as exc:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID) from exc
        metadata = VectorIndexMetadata.from_dict(payload)
        if hashlib.sha256(metadata.canonical_bytes()).hexdigest() != digest:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
        return metadata

    def _is_valid_generation(self, path: Path, expected: VectorIndexMetadata) -> bool:
        try:
            metadata = self._load_metadata(path)
            self._read_rows(path / "index.sqlite3")
        except (VectorIndexError, OSError):
            return False
        return metadata.canonical_bytes() == expected.canonical_bytes()

    def _read_rows(self, sqlite_path: Path) -> list[tuple[str, str]]:
        try:
            connection = sqlite3.connect(str(sqlite_path))
        except sqlite3.Error as exc:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID) from exc
        try:
            connection.row_factory = sqlite3.Row
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or str(integrity[0]) != "ok":
                raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID)
            rows = connection.execute(
                "SELECT chunk_id, document_id FROM vectors ORDER BY chunk_id, document_id"
            ).fetchall()
        except sqlite3.Error as exc:
            raise VectorIndexError(VectorIndexErrorCode.INDEX_INVALID) from exc
        finally:
            connection.close()
        return [(str(row["chunk_id"]), str(row["document_id"])) for row in rows]

    def _switch_pointer(self, path: Path, value: str) -> None:
        temporary = path.with_name(f".{path.name}-{uuid4().hex}")
        self._write_fsynced(temporary, f"{value}\n".encode("ascii"))
        os.replace(temporary, path)
        self._fsync_directory(path.parent)

    @staticmethod
    def _pointer_value(path: Path) -> str | None:
        try:
            value = path.read_text(encoding="ascii").strip()
        except OSError:
            return None
        return value if value.startswith("gen-m7-") else None

    @staticmethod
    def _discard_staging(staging: Path) -> None:
        if staging.is_dir() and staging.name.startswith(".staging-"):
            shutil.rmtree(staging, ignore_errors=True)

    @staticmethod
    def _write_fsynced(path: Path, payload: bytes) -> None:
        with path.open("wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        if os.name == "nt":
            return
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _pack(vector: Sequence[float]) -> bytes:
        return struct.pack(f"<{len(vector)}f", *vector)

    @staticmethod
    def _unpack(blob: bytes, dimension: int) -> list[float]:
        return list(struct.unpack(f"<{dimension}f", blob))


__all__ = [
    "VECTOR_SCHEMA_VERSION",
    "VECTOR_STATUS_ATTACHED",
    "VECTOR_INDEX_TYPE",
    "HASH_EMBEDDING_MODEL",
    "HASH_EMBEDDING_VERSION",
    "BGE_EMBEDDING_MODEL",
    "VectorIndexErrorCode",
    "VectorIndexError",
    "VectorHit",
    "VectorIndexMetadata",
    "HashVectorEmbedder",
    "SentenceTransformerEmbedder",
    "sentence_transformers_available",
    "UserSourceVectorIndex",
]
