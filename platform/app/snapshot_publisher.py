"""Atomic publication and last-good service for combined retrieval snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from threading import RLock
from typing import Callable
from uuid import uuid4

from .combined_snapshot import CombinedRetrievalSnapshot, build_configured_snapshot
from .models import RetrievalChunk
from .retrieval import RetrievalScope


class SnapshotPublicationError(RuntimeError):
    """Safe failure while validating or switching a staged generation."""

    code = "SNAPSHOT_SWITCH_FAILED"


class SnapshotReductionError(SnapshotPublicationError):
    """Require revision-bound confirmation for a large default-pack reduction."""

    code = "SNAPSHOT_REDUCTION_CONFIRMATION_REQUIRED"


class CombinedSnapshotPublisher:
    """Publish complete snapshots atomically and keep serving one last-good view."""

    def __init__(
        self,
        cache_root: Path,
        *,
        builder: Callable[[], CombinedRetrievalSnapshot] = build_configured_snapshot,
        expected_default_revision: str | None = None,
    ) -> None:
        self._root = cache_root
        self._builder = builder
        self._expected_default_revision = expected_default_revision
        self._current: CombinedRetrievalSnapshot | None = self._load_last_good()
        self._lock = RLock()
        self._publish_lock = RLock()

    @property
    def current(self) -> CombinedRetrievalSnapshot | None:
        with self._lock:
            return self._current

    def publish(self) -> CombinedRetrievalSnapshot:
        """Build and atomically switch a complete candidate, retaining last-good on error."""
        with self._publish_lock:
            with self._lock:
                previous = self._current
            staging: Path | None = None
            try:
                candidate = self._builder()
                self._validate_reduction(previous, candidate)
                self._root.mkdir(parents=True, exist_ok=True)
                staging = self._root / f".staging-{uuid4().hex}"
                staging.mkdir()
                generation_dir = self._root / f"gen-{candidate.generation}"
                self._write_generation(staging, candidate)
                if generation_dir.exists():
                    persisted = self._load_generation(generation_dir.name)
                    if persisted != candidate:
                        raise SnapshotPublicationError(
                            "existing snapshot generation is invalid"
                        )
                    shutil.rmtree(staging)
                    staging = None
                else:
                    os.replace(staging, generation_dir)
                    staging = None
                    self._fsync_directory(self._root)
                self._switch_pointer("PREVIOUS", self._pointer_value("CURRENT"))
                self._switch_pointer("CURRENT", generation_dir.name)
                with self._lock:
                    self._current = candidate
                self._cleanup(candidate, generation_dir.name)
                return candidate
            except SnapshotReductionError:
                if staging is not None:
                    shutil.rmtree(staging, ignore_errors=True)
                raise
            except Exception as exc:
                if staging is not None:
                    shutil.rmtree(staging, ignore_errors=True)
                if previous is not None:
                    return previous
                if isinstance(exc, SnapshotPublicationError):
                    raise
                raise SnapshotPublicationError("snapshot publication failed") from exc

    def view(self, scope: RetrievalScope) -> tuple[str, list[RetrievalChunk]]:
        with self._lock:
            snapshot = self._current
        if snapshot is None:
            snapshot = self.publish()
        return snapshot.view(scope)

    def _load_last_good(self) -> CombinedRetrievalSnapshot | None:
        """Load CURRENT, or PREVIOUS when CURRENT is missing or invalid."""
        for pointer in ("CURRENT", "PREVIOUS"):
            generation_name = self._pointer_value(pointer)
            if generation_name is None:
                continue
            try:
                return self._load_generation(generation_name)
            except SnapshotPublicationError:
                continue
        return None

    def _load_generation(self, generation_name: str) -> CombinedRetrievalSnapshot:
        if not _valid_generation_name(generation_name):
            raise SnapshotPublicationError("snapshot pointer is invalid")
        generation_path = self._root / generation_name
        manifest_path = generation_path / "manifest.json"
        chunks_path = generation_path / "chunks.json"
        try:
            manifest_raw = manifest_path.read_bytes()
            chunks_raw = chunks_path.read_bytes()
            manifest = json.loads(manifest_raw)
            chunk_values = json.loads(chunks_raw)
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise SnapshotPublicationError("persisted snapshot is invalid") from exc
        if not isinstance(manifest, dict) or set(manifest) != {
            "schema",
            "generation",
            "default_generation",
            "default_revision",
            "default_count",
            "combined_count",
            "source_ids",
            "source_generations",
            "chunks_sha256",
        }:
            raise SnapshotPublicationError("persisted snapshot manifest is invalid")
        if manifest.get("schema") != "sa.combined-retrieval-manifest.v1":
            raise SnapshotPublicationError("persisted snapshot manifest is invalid")
        if not isinstance(chunk_values, list):
            raise SnapshotPublicationError("persisted snapshot chunks are invalid")
        checksum = hashlib.sha256(chunks_raw).hexdigest()
        if manifest.get("chunks_sha256") != checksum:
            raise SnapshotPublicationError("persisted snapshot checksum is invalid")
        try:
            chunks = tuple(RetrievalChunk.model_validate(value) for value in chunk_values)
            default_count = manifest["default_count"]
            combined_count = manifest["combined_count"]
            source_ids = tuple(manifest["source_ids"])
            source_generations = tuple(
                (item[0], item[1]) for item in manifest["source_generations"]
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise SnapshotPublicationError("persisted snapshot manifest is invalid") from exc
        if (
            not isinstance(default_count, int)
            or isinstance(default_count, bool)
            or default_count <= 0
            or not isinstance(combined_count, int)
            or isinstance(combined_count, bool)
            or combined_count != len(chunks)
            or default_count > combined_count
            or not source_ids
            or any(not isinstance(value, str) or not value for value in source_ids)
            or len(source_generations) != len(source_ids)
            or any(
                not isinstance(source_id, str)
                or not source_id
                or not isinstance(generation, str)
                or not generation
                for source_id, generation in source_generations
            )
        ):
            raise SnapshotPublicationError("persisted snapshot manifest is invalid")
        generation = manifest.get("generation")
        default_generation = manifest.get("default_generation")
        default_revision = manifest.get("default_revision")
        if (
            not isinstance(generation, str)
            or not generation
            or generation_name != f"gen-{generation}"
            or not isinstance(default_generation, str)
            or not default_generation
            or not isinstance(default_revision, str)
            or not default_revision
            or source_ids != tuple(source_id for source_id, _ in source_generations)
            or source_generations[0][1] != default_generation
            or generation
            != _combined_generation(source_generations, default_count, combined_count)
        ):
            raise SnapshotPublicationError("persisted snapshot manifest is invalid")
        try:
            return CombinedRetrievalSnapshot(
                generation=generation,
                default_generation=default_generation,
                default_revision=default_revision,
                default_chunks=chunks[:default_count],
                combined_chunks=chunks,
                source_ids=source_ids,
                source_generations=source_generations,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            raise SnapshotPublicationError("persisted snapshot is invalid") from exc

    def _validate_reduction(
        self,
        previous: CombinedRetrievalSnapshot | None,
        candidate: CombinedRetrievalSnapshot,
    ) -> None:
        if previous is None or not previous.default_chunks:
            return
        if len(candidate.default_chunks) * 2 >= len(previous.default_chunks):
            return
        if self._expected_default_revision == candidate.default_revision:
            return
        raise SnapshotReductionError(
            "default source reduction confirmation is required: "
            f"revision={candidate.default_revision}; "
            f"previous={len(previous.default_chunks)}; "
            f"candidate={len(candidate.default_chunks)}"
        )

    def _write_generation(
        self,
        staging: Path,
        snapshot: CombinedRetrievalSnapshot,
    ) -> None:
        chunks_path = staging / "chunks.json"
        manifest_path = staging / "manifest.json"
        chunks_payload = json.dumps(
            [chunk.model_dump() for chunk in snapshot.combined_chunks],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        checksum = hashlib.sha256(chunks_payload).hexdigest()
        manifest = {
            "schema": "sa.combined-retrieval-manifest.v1",
            "generation": snapshot.generation,
            "default_generation": snapshot.default_generation,
            "default_revision": snapshot.default_revision,
            "default_count": len(snapshot.default_chunks),
            "combined_count": len(snapshot.combined_chunks),
            "source_ids": list(snapshot.source_ids),
            "source_generations": [list(item) for item in snapshot.source_generations],
            "chunks_sha256": checksum,
        }
        self._write_fsynced(chunks_path, chunks_payload)
        self._write_fsynced(
            manifest_path,
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
        )
        if hashlib.sha256(chunks_path.read_bytes()).hexdigest() != checksum:
            raise SnapshotPublicationError("snapshot checksum validation failed")
        self._fsync_directory(staging)

    def _switch_pointer(self, name: str, value: str | None) -> None:
        target = self._root / name
        if not value:
            target.unlink(missing_ok=True)
            return
        temporary = self._root / f".{name}.{uuid4().hex}.tmp"
        self._write_fsynced(temporary, value.encode("ascii"))
        os.replace(temporary, target)
        self._fsync_directory(self._root)

    def _pointer_value(self, name: str) -> str | None:
        path = self._root / name
        if not path.is_file():
            return None
        try:
            value = path.read_text(encoding="ascii").strip()
        except (OSError, UnicodeError):
            return None
        return value if _valid_generation_name(value) else None

    def _cleanup(
        self,
        snapshot: CombinedRetrievalSnapshot,
        current_name: str,
    ) -> None:
        previous_name = self._pointer_value("PREVIOUS")
        previous_path = self._root / previous_name if previous_name else None
        if previous_path is not None and previous_path.is_dir():
            try:
                manifest = json.loads(
                    (previous_path / "manifest.json").read_text(encoding="utf-8")
                )
                removed = set(manifest.get("source_ids", ())) - set(snapshot.source_ids)
            except (OSError, ValueError, TypeError):
                removed = set()
            if removed:
                shutil.rmtree(previous_path, ignore_errors=True)
                (self._root / "PREVIOUS").unlink(missing_ok=True)
                previous_name = None
        retained = {current_name, previous_name}
        for path in self._root.iterdir():
            if path.is_dir() and (
                path.name.startswith(".staging-")
                or (path.name.startswith("gen-") and path.name not in retained)
            ):
                shutil.rmtree(path, ignore_errors=True)

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



def _valid_generation_name(value: str) -> bool:
    prefix = "gen-"
    digest = value.removeprefix(prefix)
    return value.startswith(prefix) and len(digest) == 64 and all(
        character in "0123456789abcdef" for character in digest
    )


def _combined_generation(
    source_generations: tuple[tuple[str, str], ...],
    default_count: int,
    combined_count: int,
) -> str:
    payload = json.dumps(
        {
            "schema": "sa.combined-retrieval-snapshot.v1",
            "sources": source_generations,
            "default_count": default_count,
            "combined_count": combined_count,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

__all__ = [
    "CombinedSnapshotPublisher",
    "SnapshotPublicationError",
    "SnapshotReductionError",
]
