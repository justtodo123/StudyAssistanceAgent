"""Source-local M7 retrieval isolation gate.

This module does not register routes or mutate Search/QA/preview.  It only
computes an owner-only authorization snapshot and filters candidate hits
before they would be allowed to reach BM25, vector, RRF, result cache, or
provenance assembly.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Iterable, Mapping

from .source_delete import UserSourceDeleteService
from .source_registry import (
    ISOLATION_POLICY_VERSION,
    SourceLifecycleService,
    SourceLifecycleState,
)

_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,127}$")
_USER_SOURCE_RE = re.compile(
    r"^user-[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_HIDDEN_STATES = frozenset({SourceLifecycleState.DELETE_PENDING, SourceLifecycleState.DELETED})
_BLOCKED_ORIGINS = frozenset({"ai_draft", "web_candidate"})


class SourceIsolationErrorCode(StrEnum):
    SOURCE_AUTH_REQUIRED = "SOURCE_AUTH_REQUIRED"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    SOURCE_ISOLATION_INVALID_REQUEST = "SOURCE_ISOLATION_INVALID_REQUEST"
    SOURCE_ISOLATION_UNAVAILABLE = "SOURCE_ISOLATION_UNAVAILABLE"


class SourceIsolationError(RuntimeError):
    """Stable, content-free isolation failure."""

    def __init__(self, code: SourceIsolationErrorCode, message: str = "Source isolation failed.") -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    source_id: str | None
    document_id: str | None = None
    chunk_id: str | None = None
    logical_uri: str | None = None
    generation: str | None = None
    origin_kind: str | None = None
    cache_key: str | None = None


@dataclass(frozen=True, slots=True)
class IsolationSnapshot:
    principal_id: str
    authorized_source_ids: frozenset[str]
    published_generations: dict[str, str]
    auth_digest: str
    policy_version: str = ISOLATION_POLICY_VERSION


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def is_user_source_id(source_id: str) -> bool:
    return isinstance(source_id, str) and _USER_SOURCE_RE.fullmatch(source_id) is not None


def _tombstones_block(
    tombstones: tuple,
    *,
    logical_uri: str | None,
    document_id: str | None,
    generation: str | None,
) -> bool:
    for tombstone in tombstones:
        if tombstone.logical_uri == "*":
            return True
        if logical_uri is not None and tombstone.logical_uri == logical_uri:
            return True
        if document_id is not None and tombstone.document_id == document_id:
            return True
        if generation is not None and tombstone.generation_upper_bound == generation:
            return True
    return False


class SourceIsolationGate:
    """Forced pre-query filter for M7 user sources."""

    def __init__(
        self,
        lifecycle: SourceLifecycleService,
        delete_service: UserSourceDeleteService,
        *,
        snapshot_observer: Callable[[IsolationSnapshot], None] | None = None,
    ) -> None:
        self._lifecycle = lifecycle
        self._delete = delete_service
        self.snapshot_observer = snapshot_observer
        self.mid_request_mutations: list[Callable[[], None]] = []

    def capture_snapshot(self, principal_id: str) -> IsolationSnapshot:
        if not principal_id:
            raise SourceIsolationError(SourceIsolationErrorCode.SOURCE_AUTH_REQUIRED, "Source authentication is required.")
        if _OPAQUE_ID_RE.fullmatch(principal_id) is None:
            raise SourceIsolationError(SourceIsolationErrorCode.SOURCE_NOT_FOUND, "The Source was not found.")
        try:
            records = self._lifecycle.list_sources(principal_id=principal_id)
        except Exception as exc:
            raise SourceIsolationError(
                SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                "Source isolation is unavailable.",
            ) from exc
        authorized: list[str] = []
        generations: dict[str, str] = {}
        for record in records:
            if record.state in _HIDDEN_STATES:
                continue
            authorized.append(record.source_id)
            if record.published_generation is not None:
                generations[record.source_id] = record.published_generation
        digest = hashlib.sha256(
            _canonical_json(
                {
                    "principal_id": principal_id,
                    "policy_version": ISOLATION_POLICY_VERSION,
                    "source_ids": sorted(authorized),
                    "generations": generations,
                }
            ).encode("utf-8")
        ).hexdigest()
        snapshot = IsolationSnapshot(
            principal_id=principal_id,
            authorized_source_ids=frozenset(authorized),
            published_generations=generations,
            auth_digest=digest,
        )
        if self.snapshot_observer is not None:
            self.snapshot_observer(snapshot)
        return snapshot

    def require_source(self, principal_id: str, source_id: str) -> None:
        snapshot = self.capture_snapshot(principal_id)
        if not is_user_source_id(source_id) or source_id not in snapshot.authorized_source_ids:
            raise SourceIsolationError(SourceIsolationErrorCode.SOURCE_NOT_FOUND, "The Source was not found.")
        if self._delete.is_blocked(source_id):
            raise SourceIsolationError(SourceIsolationErrorCode.SOURCE_NOT_FOUND, "The Source was not found.")

    def filter_hits(
        self,
        principal_id: str,
        hits: Iterable[RetrievalHit],
        *,
        snapshot: IsolationSnapshot | None = None,
    ) -> tuple[RetrievalHit, ...]:
        resolved = snapshot if snapshot is not None else self._stable_snapshot(principal_id)
        allowed: list[RetrievalHit] = []
        hidden: dict[str, bool] = {}
        tombstones: dict[str, tuple] = {}
        for hit in hits:
            if hit.source_id is None:
                raise SourceIsolationError(
                    SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                    "Source isolation is unavailable.",
                )
            if not is_user_source_id(hit.source_id):
                allowed.append(hit)
                continue
            if hit.cache_key is not None and resolved.auth_digest not in hit.cache_key:
                raise SourceIsolationError(
                    SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                    "Source isolation is unavailable.",
                )
            if hit.source_id not in resolved.authorized_source_ids:
                continue
            if hit.source_id not in hidden:
                hidden[hit.source_id] = self._delete.is_blocked(hit.source_id)
                tombstones[hit.source_id] = self._delete.list_tombstones(hit.source_id)
            if hidden[hit.source_id]:
                continue
            if _tombstones_block(
                tombstones[hit.source_id],
                logical_uri=hit.logical_uri,
                document_id=hit.document_id,
                generation=hit.generation,
            ):
                continue
            published = resolved.published_generations.get(hit.source_id)
            if hit.generation is not None and published is not None and hit.generation != published:
                continue
            if hit.origin_kind in _BLOCKED_ORIGINS:
                continue
            if hit.document_id is not None:
                status = self._delete.surfaces.provenance_status(hit.source_id, hit.document_id)
                if status in {"TOMBSTONED", "STALE_DERIVATION"}:
                    continue
            allowed.append(hit)
        return tuple(allowed)

    def _fire_mutation(self) -> None:
        if self.mid_request_mutations:
            self.mid_request_mutations.pop(0)()

    def _stable_snapshot(self, principal_id: str) -> IsolationSnapshot:
        first = self.capture_snapshot(principal_id)
        self._fire_mutation()
        second = self.capture_snapshot(principal_id)
        if second == first:
            return first
        self._fire_mutation()
        third = self.capture_snapshot(principal_id)
        if third != second:
            raise SourceIsolationError(
                SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE,
                "Source isolation is unavailable.",
            )
        return third
