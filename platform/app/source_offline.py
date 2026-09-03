"""Source-local M7 offline fail-closed validation and explicit FULL repair.

This module does not start Search/QA/preview, does not auto-repair on query, and
does not create study-session or review-log state.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .fts5_tokenizer import (
    Fts5TokenizerError,
    Fts5TokenizerErrorCode,
    require_jieba,
)
from .source_delete import UserSourceDeleteService
from .source_isolation import SourceIsolationError, SourceIsolationGate
from .source_registry import SourceActorType, SourceLifecycleService, SourceLifecycleState, SourceRecord
from .user_source_fts5 import (
    Fts5Hit,
    Fts5IndexError,
    Fts5IndexErrorCode,
    Fts5IndexMetadata,
    UserSourceFts5Index,
)
from .user_source_snapshot import FullSnapshotError, UserSourceSnapshotPublisher


OFFLINE_SCHEMA_VERSION = "sa.source.offline-fallback.v1"


class SourceOfflineErrorCode(StrEnum):
    DEPENDENCY_UNAVAILABLE = "SOURCE_OFFLINE_DEPENDENCY_UNAVAILABLE"
    INDEX_INVALID = "SOURCE_OFFLINE_INDEX_INVALID"
    SOURCE_UNAVAILABLE = "SOURCE_OFFLINE_SOURCE_UNAVAILABLE"
    REPAIR_REQUIRED = "SOURCE_OFFLINE_REPAIR_REQUIRED"


_ERROR_MESSAGES: Mapping[SourceOfflineErrorCode, str] = MappingProxyType(
    {
        SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE: "A required source dependency is unavailable.",
        SourceOfflineErrorCode.INDEX_INVALID: "The source index is invalid.",
        SourceOfflineErrorCode.SOURCE_UNAVAILABLE: "The user source is unavailable.",
        SourceOfflineErrorCode.REPAIR_REQUIRED: "The source index requires an explicit FULL repair.",
    }
)


class SourceOfflineError(RuntimeError):
    """Stable, content-free offline rejection with a local repair category."""

    def __init__(self, code: SourceOfflineErrorCode, *, source_id: str | None = None) -> None:
        self.code = code
        self.source_id = source_id
        self.repair_category = {
            SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE: "repair-local-dependency",
            SourceOfflineErrorCode.INDEX_INVALID: "rebuild-source-index-full",
            SourceOfflineErrorCode.SOURCE_UNAVAILABLE: "repair-source-input",
            SourceOfflineErrorCode.REPAIR_REQUIRED: "rebuild-source-index-full",
        }[code]
        super().__init__(_ERROR_MESSAGES[code])

    def public_dict(self) -> dict[str, str]:
        payload = {"error": self.code.value, "repair": self.repair_category}
        if self.source_id is not None:
            payload["source_id"] = self.source_id
        return payload


@dataclass(frozen=True, slots=True)
class ValidatedSourceIndex:
    source_id: str
    generation: str
    metadata: Fts5IndexMetadata


class UserSourceOfflineGuard:
    """Validate M7 user-source indexes without fallback or silent repair."""

    def __init__(
        self,
        cache_root: str | Path,
        lifecycle: SourceLifecycleService,
        *,
        snapshot_publisher: UserSourceSnapshotPublisher | None = None,
        fts5: UserSourceFts5Index | None = None,
        delete_service: UserSourceDeleteService | None = None,
        isolation: SourceIsolationGate | None = None,
    ) -> None:
        self._root = Path(cache_root)
        self._lifecycle = lifecycle
        self._snapshots = snapshot_publisher or UserSourceSnapshotPublisher(self._root, lifecycle)
        self._fts5 = fts5 or UserSourceFts5Index(self._root)
        self._delete = delete_service or UserSourceDeleteService(self._root, lifecycle)
        self._isolation = isolation or SourceIsolationGate(lifecycle, self._delete)

    def validate_for_query(self, *, principal_id: str, source_id: str) -> ValidatedSourceIndex:
        self._isolation.require_source(principal_id, source_id)
        try:
            require_jieba()
        except Fts5TokenizerError as exc:
            raise self._map_tokenizer(exc, source_id) from exc
        try:
            record = self._lifecycle.get_source(principal_id=principal_id, source_id=source_id)
        except Exception as exc:
            raise SourceOfflineError(SourceOfflineErrorCode.SOURCE_UNAVAILABLE, source_id=source_id) from exc
        if record.published_generation is None or record.state not in {
            SourceLifecycleState.READY,
            SourceLifecycleState.DEGRADED,
        }:
            raise SourceOfflineError(SourceOfflineErrorCode.SOURCE_UNAVAILABLE, source_id=source_id)
        try:
            snapshot = self._snapshots.load_snapshot(source_id, record.published_generation)
        except FullSnapshotError as exc:
            raise SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id) from exc
        if snapshot is None:
            raise SourceOfflineError(SourceOfflineErrorCode.REPAIR_REQUIRED, source_id=source_id)
        try:
            metadata = self._fts5.validate(source_id, record.published_generation, snapshot)
        except Fts5TokenizerError as exc:
            raise self._map_tokenizer(exc, source_id) from exc
        except Fts5IndexError as exc:
            raise self._map_index(exc, source_id) from exc
        return ValidatedSourceIndex(
            source_id=source_id,
            generation=record.published_generation,
            metadata=metadata,
        )

    def search(
        self,
        *,
        principal_id: str,
        source_id: str,
        query: str,
        top_k: int = 5,
    ) -> tuple[Fts5Hit, ...]:
        validated = self.validate_for_query(principal_id=principal_id, source_id=source_id)
        try:
            return self._fts5.search(validated.source_id, validated.generation, query, top_k=top_k)
        except Fts5TokenizerError as exc:
            raise self._map_tokenizer(exc, source_id) from exc
        except Fts5IndexError as exc:
            raise self._map_index(exc, source_id) from exc

    def repair_full(
        self,
        *,
        principal_id: str,
        source_id: str,
        source_root: str | Path,
        correlation_id: str,
        actor_type: SourceActorType = SourceActorType.USER,
    ) -> SourceRecord:
        self._isolation.require_source(principal_id, source_id)
        try:
            require_jieba()
        except Fts5TokenizerError as exc:
            raise self._map_tokenizer(exc, source_id) from exc
        try:
            record = self._snapshots.publish_full(
                principal_id=principal_id,
                source_id=source_id,
                source_root=source_root,
                correlation_id=correlation_id,
                actor_type=actor_type,
            )
        except FullSnapshotError as exc:
            raise SourceOfflineError(SourceOfflineErrorCode.SOURCE_UNAVAILABLE, source_id=source_id) from exc
        if record.published_generation is None:
            raise SourceOfflineError(SourceOfflineErrorCode.REPAIR_REQUIRED, source_id=source_id)
        try:
            snapshot = self._snapshots.load_snapshot(source_id, record.published_generation)
            if snapshot is None:
                raise SourceOfflineError(SourceOfflineErrorCode.REPAIR_REQUIRED, source_id=source_id)
            self._fts5.build(snapshot, activate=True)
            self._fts5.validate(source_id, record.published_generation, snapshot)
        except Fts5TokenizerError as exc:
            raise self._map_tokenizer(exc, source_id) from exc
        except Fts5IndexError as exc:
            raise self._map_index(exc, source_id) from exc
        except SourceOfflineError:
            raise
        except Exception as exc:
            raise SourceOfflineError(SourceOfflineErrorCode.REPAIR_REQUIRED, source_id=source_id) from exc
        return record

    @staticmethod
    def _map_tokenizer(exc: Fts5TokenizerError, source_id: str) -> Exception:
        if exc.code is Fts5TokenizerErrorCode.UNAVAILABLE:
            return SourceOfflineError(SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE, source_id=source_id)
        if exc.code is Fts5TokenizerErrorCode.INVALID_QUERY:
            return exc
        if exc.code in {Fts5TokenizerErrorCode.MISMATCH, Fts5TokenizerErrorCode.UNSUPPORTED}:
            return SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)
        return SourceOfflineError(SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE, source_id=source_id)

    @staticmethod
    def _map_index(exc: Fts5IndexError, source_id: str) -> SourceOfflineError:
        if exc.code is Fts5IndexErrorCode.REPAIR_REQUIRED:
            return SourceOfflineError(SourceOfflineErrorCode.REPAIR_REQUIRED, source_id=source_id)
        return SourceOfflineError(SourceOfflineErrorCode.INDEX_INVALID, source_id=source_id)


__all__ = [
    "OFFLINE_SCHEMA_VERSION",
    "SourceOfflineErrorCode",
    "SourceOfflineError",
    "ValidatedSourceIndex",
    "UserSourceOfflineGuard",
]
