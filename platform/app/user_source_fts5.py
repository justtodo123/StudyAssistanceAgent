"""Generation-bound source-local SQLite FTS5 index for M7 user sources.

This module does not register Search/QA/preview routes or mutate default-pack
BM25. Published artifacts stay under the local cache root.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import threading
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4

from .fts5_tokenizer import (
    FTS_SCHEMA_VERSION,
    Fts5TokenizerError,
    Fts5TokenizerErrorCode,
    fts5_match_query,
    token_stream,
    tokenizer_metadata,
    validate_tokenizer_metadata,
)
from .source_manifest import canonical_json
from .user_source_snapshot import FullSnapshot


INDEX_SCHEMA_VERSION = FTS_SCHEMA_VERSION
VECTOR_STATUS_NOT_ATTACHED = "not_attached"
VECTOR_STATUS_ATTACHED = "attached"
RESULT_CACHE_STATUS_NOT_ATTACHED = "not_attached"
_EMPTY_SET_DIGEST = hashlib.sha256(canonical_json([])).hexdigest()


class Fts5IndexErrorCode(StrEnum):
    BUILD_FAILED = "SOURCE_OFFLINE_INDEX_INVALID"
    PUBLICATION_FAILED = "SOURCE_OFFLINE_INDEX_INVALID"
    INDEX_INVALID = "SOURCE_OFFLINE_INDEX_INVALID"
    REPAIR_REQUIRED = "SOURCE_OFFLINE_REPAIR_REQUIRED"


_ERROR_MESSAGES: Mapping[Fts5IndexErrorCode, str] = MappingProxyType(
    {
        Fts5IndexErrorCode.BUILD_FAILED: "The source index is invalid.",
        Fts5IndexErrorCode.PUBLICATION_FAILED: "The source index is invalid.",
        Fts5IndexErrorCode.INDEX_INVALID: "The source index is invalid.",
        Fts5IndexErrorCode.REPAIR_REQUIRED: "The source index requires an explicit FULL repair.",
    }
)


class Fts5IndexError(RuntimeError):
    """Stable, content-free FTS5 index failure."""

    def __init__(self, code: Fts5IndexErrorCode) -> None:
        self.code = code
        self.repair_category = "rebuild-source-index-full"
        super().__init__(_ERROR_MESSAGES[code])


@dataclass(frozen=True, slots=True)
class Fts5Hit:
    source_id: str
    document_id: str
    chunk_id: str
    generation: str
    rank: int


@dataclass(frozen=True, slots=True)
class Fts5IndexMetadata:
    source_id: str
    generation: str
    chunk_count: int
    identity_set_digest: str
    token_stream_digest: str
    content_digest: str
    build_input_digest: str
    snapshot_fingerprint: str
    tokenizer_schema: str
    tokenizer_version: str
    normalization_version: str
    fts_schema_version: str
    jieba_version: str
    vector_status: str = VECTOR_STATUS_NOT_ATTACHED
    vector_identity_set_digest: str = _EMPTY_SET_DIGEST
    result_cache_status: str = RESULT_CACHE_STATUS_NOT_ATTACHED
    result_cache_digest: str = _EMPTY_SET_DIGEST
    schema_name: str = INDEX_SCHEMA_VERSION
    offline_schema: str = "sa.source.offline-fallback.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_name": self.schema_name,
            "offline_schema": self.offline_schema,
            "source_id": self.source_id,
            "generation": self.generation,
            "chunk_count": self.chunk_count,
            "identity_set_digest": self.identity_set_digest,
            "token_stream_digest": self.token_stream_digest,
            "content_digest": self.content_digest,
            "build_input_digest": self.build_input_digest,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "tokenizer_schema": self.tokenizer_schema,
            "tokenizer_version": self.tokenizer_version,
            "normalization_version": self.normalization_version,
            "fts_schema_version": self.fts_schema_version,
            "jieba_version": self.jieba_version,
            "vector_status": self.vector_status,
            "vector_identity_set_digest": self.vector_identity_set_digest,
            "result_cache_status": self.result_cache_status,
            "result_cache_digest": self.result_cache_digest,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: object) -> "Fts5IndexMetadata":
        if not isinstance(payload, dict) or payload.get("schema_name") != INDEX_SCHEMA_VERSION:
            raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
        try:
            metadata = cls(
                source_id=str(payload.get("source_id")),
                generation=str(payload.get("generation")),
                chunk_count=int(payload.get("chunk_count", -1)),
                identity_set_digest=str(payload.get("identity_set_digest")),
                token_stream_digest=str(payload.get("token_stream_digest")),
                content_digest=str(payload.get("content_digest")),
                build_input_digest=str(payload.get("build_input_digest")),
                snapshot_fingerprint=str(payload.get("snapshot_fingerprint")),
                tokenizer_schema=str(payload.get("tokenizer_schema")),
                tokenizer_version=str(payload.get("tokenizer_version")),
                normalization_version=str(payload.get("normalization_version")),
                fts_schema_version=str(payload.get("fts_schema_version")),
                jieba_version=str(payload.get("jieba_version")),
                vector_status=str(payload.get("vector_status", "")),
                vector_identity_set_digest=str(payload.get("vector_identity_set_digest", "")),
                result_cache_status=str(payload.get("result_cache_status", "")),
                result_cache_digest=str(payload.get("result_cache_digest", "")),
                schema_name=str(payload.get("schema_name")),
                offline_schema=str(payload.get("offline_schema", "")),
            )
        except (TypeError, ValueError) as exc:
            raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID) from exc
        if metadata.canonical_bytes() != canonical_json(payload):
            raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
        return metadata


def identity_set(snapshot: FullSnapshot) -> list[list[str]]:
    pairs = [
        [chunk.document_id, chunk.chunk_id]
        for document in snapshot.documents
        for chunk in document.chunks()
    ]
    pairs.sort()
    return pairs


def identity_set_digest(snapshot: FullSnapshot) -> str:
    return hashlib.sha256(canonical_json(identity_set(snapshot))).hexdigest()


@dataclass(slots=True)
class _Fts5Runtime:
    source_id: str
    generation: str
    metadata: Fts5IndexMetadata
    metadata_digest: str
    sqlite_path: Path
    sqlite_size: int
    sqlite_mtime_ns: int
    identity_pairs: tuple[tuple[str, str], ...]


def _file_fingerprint(path: Path) -> tuple[int, int]:
    stat = path.stat()
    mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))
    return int(stat.st_size), int(mtime_ns)


def _read_fts5_identity(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    rows = connection.execute(
        "SELECT chunk_id, document_id FROM chunks ORDER BY chunk_id, document_id"
    ).fetchall()
    return tuple((str(row["chunk_id"]), str(row["document_id"])) for row in rows)


class UserSourceFts5Index:
    """Build and read one generation-bound FTS5 index per user source."""

    def __init__(self, cache_root: str | Path) -> None:
        self._root = Path(cache_root) / "user-source-fts5" / "v1"
        self._lock = threading.RLock()
        self._runtimes: dict[tuple[str, str], "_Fts5Runtime"] = {}

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

    def load_metadata(self, source_id: str, generation: str | None = None) -> Fts5IndexMetadata | None:
        path = self.published_path(source_id, generation)
        if path is None:
            return None
        return self._load_metadata(path)

    def build(
        self,
        snapshot: FullSnapshot,
        *,
        activate: bool = True,
        vector_status: str = VECTOR_STATUS_NOT_ATTACHED,
        vector_identity_set_digest: str | None = None,
    ) -> Fts5IndexMetadata:
        with self._lock:
            self._drop_runtimes(snapshot.source_id)
            metadata = self._materialize(
                snapshot,
                vector_status=vector_status,
                vector_identity_set_digest=vector_identity_set_digest,
            )
            if activate:
                self._activate(snapshot.source_id, snapshot.generation)
            return metadata

    def search(self, source_id: str, generation: str, query: str, *, top_k: int = 5) -> tuple[Fts5Hit, ...]:
        runtime = self._runtimes.get((source_id, generation)) or self._ensure_runtime(source_id, generation)
        try:
            match = fts5_match_query(query)
        except Fts5TokenizerError:
            raise
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(runtime.sqlite_path))
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT chunk_id, document_id, bm25(chunks) AS score
                FROM chunks
                WHERE chunks MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (match, max(int(top_k), 0)),
            ).fetchall()
        except Fts5TokenizerError:
            raise
        except sqlite3.Error as exc:
            raise Fts5TokenizerError(Fts5TokenizerErrorCode.INVALID_QUERY) from exc
        finally:
            if connection is not None:
                connection.close()
        hits = []
        for rank, row in enumerate(rows, start=1):
            hits.append(
                Fts5Hit(
                    source_id=source_id,
                    document_id=str(row["document_id"]),
                    chunk_id=str(row["chunk_id"]),
                    generation=runtime.metadata.generation,
                    rank=rank,
                )
            )
        return tuple(hits)

    def validate(self, source_id: str, generation: str, snapshot: FullSnapshot | None = None) -> Fts5IndexMetadata:
        return self._ensure_runtime(source_id, generation, snapshot).metadata

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
    ) -> "_Fts5Runtime":
        with self._lock:
            path = self.published_path(source_id, generation)
            if path is None:
                raise Fts5IndexError(Fts5IndexErrorCode.REPAIR_REQUIRED)
            metadata = self._load_metadata(path)
            try:
                validate_tokenizer_metadata(metadata.to_dict())
            except Fts5TokenizerError:
                raise
            if metadata.source_id != source_id or metadata.generation != generation:
                raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
            if metadata.vector_status == VECTOR_STATUS_ATTACHED:
                if metadata.vector_identity_set_digest != metadata.identity_set_digest:
                    raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
            elif metadata.vector_status == VECTOR_STATUS_NOT_ATTACHED:
                if metadata.vector_identity_set_digest != _EMPTY_SET_DIGEST:
                    raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
            else:
                raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
            if metadata.result_cache_status != RESULT_CACHE_STATUS_NOT_ATTACHED:
                raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
            if metadata.result_cache_digest != _EMPTY_SET_DIGEST:
                raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
            if snapshot is not None and (
                snapshot.source_id != source_id
                or snapshot.generation != generation
                or snapshot.source_fingerprint != metadata.snapshot_fingerprint
                or identity_set_digest(snapshot) != metadata.identity_set_digest
                or snapshot.chunk_count != metadata.chunk_count
            ):
                raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
            sqlite_path = path / "index.sqlite3"
            try:
                sqlite_size, sqlite_mtime_ns = _file_fingerprint(sqlite_path)
                metadata_digest = (path / "SHA256").read_text(encoding="ascii").strip()
            except OSError as exc:
                raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID) from exc
            key = (source_id, generation)
            cached = self._runtimes.get(key)
            if (
                cached is not None
                and cached.metadata_digest == metadata_digest
                and cached.sqlite_size == sqlite_size
                and cached.sqlite_mtime_ns == sqlite_mtime_ns
            ):
                cached.metadata = metadata
                return cached
            connection: sqlite3.Connection | None = None
            try:
                connection = sqlite3.connect(str(sqlite_path))
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA temp_store=MEMORY")
                identity_pairs = _read_fts5_identity(connection)
                digest = hashlib.sha256(
                    canonical_json(sorted([[document_id, chunk_id] for chunk_id, document_id in identity_pairs]))
                ).hexdigest()
                if digest != metadata.identity_set_digest or len(identity_pairs) != metadata.chunk_count:
                    raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
                if (
                    cached is not None
                    and cached.metadata_digest == metadata_digest
                    and cached.sqlite_size == sqlite_size
                    and cached.sqlite_mtime_ns == sqlite_mtime_ns
                    and cached.identity_pairs == identity_pairs
                ):
                    cached.metadata = metadata
                    return cached
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                if integrity is None or str(integrity[0]) != "ok":
                    raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
                rows = connection.execute(
                    "SELECT chunk_id, document_id, content FROM chunks ORDER BY chunk_id, document_id"
                ).fetchall()
                parsed_rows = [(str(row["chunk_id"]), str(row["document_id"]), str(row["content"])) for row in rows]
                recomputed = self._digests_from_rows(source_id, generation, parsed_rows)
                if (
                    recomputed["identity_set_digest"] != metadata.identity_set_digest
                    or recomputed["token_stream_digest"] != metadata.token_stream_digest
                    or recomputed["content_digest"] != metadata.content_digest
                    or recomputed["chunk_count"] != metadata.chunk_count
                ):
                    raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
                runtime = _Fts5Runtime(
                    source_id=source_id,
                    generation=generation,
                    metadata=metadata,
                    metadata_digest=metadata_digest,
                    sqlite_path=sqlite_path,
                    sqlite_size=sqlite_size,
                    sqlite_mtime_ns=sqlite_mtime_ns,
                    identity_pairs=identity_pairs,
                )
                self._runtimes[key] = runtime
                return runtime
            except Fts5TokenizerError:
                self._runtimes.pop(key, None)
                raise
            except sqlite3.Error as exc:
                self._runtimes.pop(key, None)
                raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID) from exc
            finally:
                if connection is not None:
                    connection.close()

    def _materialize(
        self,
        snapshot: FullSnapshot,
        *,
        vector_status: str = VECTOR_STATUS_NOT_ATTACHED,
        vector_identity_set_digest: str | None = None,
    ) -> Fts5IndexMetadata:
        root = self._root / snapshot.source_id
        root.mkdir(parents=True, exist_ok=True)
        staging = root / f".staging-{uuid4().hex}"
        generation = root / f"gen-{snapshot.generation}"
        try:
            staging.mkdir()
            metadata = self._write_index(
                staging,
                snapshot,
                vector_status=vector_status,
                vector_identity_set_digest=vector_identity_set_digest,
            )
            payload = metadata.canonical_bytes()
            self._write_fsynced(staging / "metadata.json", payload)
            self._write_fsynced(
                staging / "SHA256",
                hashlib.sha256(payload).hexdigest().encode("ascii") + b"\n",
            )
            self._fsync_directory(staging)
            if generation.exists():
                if not self._is_valid_generation(generation, metadata):
                    raise Fts5IndexError(Fts5IndexErrorCode.PUBLICATION_FAILED)
                self._discard_staging(staging)
            else:
                os.replace(staging, generation)
                self._fsync_directory(root)
            return metadata
        except Fts5TokenizerError:
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
            raise Fts5IndexError(Fts5IndexErrorCode.PUBLICATION_FAILED)
        previous = self._pointer_value(root / "CURRENT")
        if previous is not None and previous != generation_name:
            self._switch_pointer(root / "PREVIOUS", previous)
        self._switch_pointer(root / "CURRENT", generation_name)

    def _write_index(
        self,
        staging: Path,
        snapshot: FullSnapshot,
        *,
        vector_status: str = VECTOR_STATUS_NOT_ATTACHED,
        vector_identity_set_digest: str | None = None,
    ) -> Fts5IndexMetadata:
        versions = tokenizer_metadata()
        rows: list[tuple[str, str, str]] = []
        for document in snapshot.documents:
            for chunk in document.chunks():
                rows.append((chunk.chunk_id, chunk.document_id, token_stream(chunk.content, purpose="document")))
        sqlite_path = staging / "index.sqlite3"
        connection = sqlite3.connect(sqlite_path)
        try:
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute(
                """
                CREATE VIRTUAL TABLE chunks USING fts5(
                    chunk_id UNINDEXED,
                    document_id UNINDEXED,
                    content,
                    tokenize = 'unicode61'
                )
                """
            )
            connection.executemany(
                "INSERT INTO chunks(chunk_id, document_id, content) VALUES (?, ?, ?)",
                rows,
            )
            connection.commit()
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or str(integrity[0]) != "ok":
                raise Fts5IndexError(Fts5IndexErrorCode.BUILD_FAILED)
        except Fts5TokenizerError:
            raise
        except sqlite3.Error as exc:
            raise Fts5IndexError(Fts5IndexErrorCode.BUILD_FAILED) from exc
        finally:
            connection.close()
        digests = self._digests_from_rows(snapshot.source_id, snapshot.generation, rows)
        identity_digest = identity_set_digest(snapshot)
        if digests["identity_set_digest"] != identity_digest:
            raise Fts5IndexError(Fts5IndexErrorCode.BUILD_FAILED)
        build_input = canonical_json(
            {
                "tokenizer": versions,
                "source_id": snapshot.source_id,
                "generation": snapshot.generation,
                "snapshot_fingerprint": snapshot.source_fingerprint,
                "identity_set_digest": identity_digest,
                "token_stream_digest": digests["token_stream_digest"],
            }
        )
        if vector_status == VECTOR_STATUS_ATTACHED:
            bound_digest = vector_identity_set_digest or identity_digest
            if bound_digest != identity_digest:
                raise Fts5IndexError(Fts5IndexErrorCode.BUILD_FAILED)
        elif vector_status == VECTOR_STATUS_NOT_ATTACHED:
            bound_digest = _EMPTY_SET_DIGEST
            if vector_identity_set_digest not in {None, _EMPTY_SET_DIGEST}:
                raise Fts5IndexError(Fts5IndexErrorCode.BUILD_FAILED)
        else:
            raise Fts5IndexError(Fts5IndexErrorCode.BUILD_FAILED)
        return Fts5IndexMetadata(
            source_id=snapshot.source_id,
            generation=snapshot.generation,
            chunk_count=digests["chunk_count"],
            identity_set_digest=identity_digest,
            token_stream_digest=digests["token_stream_digest"],
            content_digest=digests["content_digest"],
            build_input_digest=hashlib.sha256(build_input).hexdigest(),
            snapshot_fingerprint=snapshot.source_fingerprint,
            tokenizer_schema=versions["tokenizer_schema"],
            tokenizer_version=versions["tokenizer_version"],
            normalization_version=versions["normalization_version"],
            fts_schema_version=versions["fts_schema_version"],
            jieba_version=versions["jieba_version"],
            vector_status=vector_status,
            vector_identity_set_digest=bound_digest,
        )

    def _load_metadata(self, path: Path) -> Fts5IndexMetadata:
        try:
            payload = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
            digest = (path / "SHA256").read_text(encoding="ascii").strip()
        except (OSError, json.JSONDecodeError, UnicodeError) as exc:
            raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID) from exc
        metadata = Fts5IndexMetadata.from_dict(payload)
        if hashlib.sha256(metadata.canonical_bytes()).hexdigest() != digest:
            raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
        return metadata

    def _is_valid_generation(self, path: Path, expected: Fts5IndexMetadata) -> bool:
        try:
            metadata = self._load_metadata(path)
            self._read_rows(path / "index.sqlite3")
        except (Fts5IndexError, OSError):
            return False
        return metadata.canonical_bytes() == expected.canonical_bytes()

    def _read_rows(self, sqlite_path: Path) -> list[tuple[str, str, str]]:
        try:
            connection = sqlite3.connect(str(sqlite_path))
        except sqlite3.Error as exc:
            raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID) from exc
        try:
            connection.row_factory = sqlite3.Row
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or str(integrity[0]) != "ok":
                raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID)
            rows = connection.execute(
                "SELECT chunk_id, document_id, content FROM chunks ORDER BY chunk_id, document_id"
            ).fetchall()
        except sqlite3.Error as exc:
            raise Fts5IndexError(Fts5IndexErrorCode.INDEX_INVALID) from exc
        finally:
            connection.close()
        return [(str(row["chunk_id"]), str(row["document_id"]), str(row["content"])) for row in rows]

    @staticmethod
    def _digests_from_rows(
        source_id: str,
        generation: str,
        rows: list[tuple[str, str, str]],
    ) -> dict[str, object]:
        rows = sorted(rows, key=lambda item: (item[0], item[1]))
        identity = sorted([[document_id, chunk_id] for chunk_id, document_id, _content in rows])
        token_payload = canonical_json(
            [{"chunk_id": chunk_id, "document_id": document_id, "content": content} for chunk_id, document_id, content in rows]
        )
        return {
            "chunk_count": len(rows),
            "identity_set_digest": hashlib.sha256(canonical_json(identity)).hexdigest(),
            "token_stream_digest": hashlib.sha256(
                canonical_json([content for _chunk_id, _document_id, content in rows])
            ).hexdigest(),
            "content_digest": hashlib.sha256(token_payload).hexdigest(),
            "source_id": source_id,
            "generation": generation,
        }

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


__all__ = [
    "INDEX_SCHEMA_VERSION",
    "VECTOR_STATUS_NOT_ATTACHED",
    "VECTOR_STATUS_ATTACHED",
    "RESULT_CACHE_STATUS_NOT_ATTACHED",
    "Fts5IndexErrorCode",
    "Fts5IndexError",
    "Fts5Hit",
    "Fts5IndexMetadata",
    "identity_set",
    "identity_set_digest",
    "UserSourceFts5Index",
]
