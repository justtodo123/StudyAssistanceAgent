"""Fail-closed authority contracts for executable M11 operations.

This module validates operation-specific, metadata-only authority records.  It
never grants authority from a historical manifest or from a metadata-only
checklist; callers must provide an explicit record bound to the frozen P0
scope digest.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

AUTHORITY_SCHEMA = "sa.m11.execution-authority.v1"
FROZEN_P0_SOURCE_IDS = frozenset({
    "knowledge-pack",
    "project-authored-evals",
    "mit-ocw-6-004-2017",
    "opendsa-main",
    "rfc-editor-index",
    "iana-registries",
})
EXCLUDED_SOURCE_IDS = frozenset({
    "network-candidates",
    "stackexchange-dump",
    "linux-kernel-docs",
    "m8-backend-assets",
    "m12-cloud-assets",
})
_ALLOWED_OPERATIONS = frozenset({
    "acquisition", "gate0", "human_review", "promotion", "formal_3k",
})
_FORBIDDEN_KEYS = frozenset({
    "body", "content", "raw_path", "normalized_path", "candidate_path",
    "approved_path", "credentials", "password", "token", "learning_state",
    "private_learning_state", "signature", "reviewer_comment",
})
_AUTHORITY_FIELDS = frozenset({
    "schema", "operation", "authority_id", "issued_by", "issued_at",
    "expires_at", "scope_digest", "source_ids", "asset_ids",
    "metadata_only", "publication_authorized", "status",
})
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*\Z")
_HEX_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class ExecutionAuthorityError(ValueError):
    """A supplied M11 authority record is not valid for the requested action."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class M11Operation(StrEnum):
    ACQUISITION = "acquisition"
    GATE0 = "gate0"
    HUMAN_REVIEW = "human_review"
    PROMOTION = "promotion"
    FORMAL_3K = "formal_3k"


@dataclass(frozen=True, slots=True)
class ExecutionAuthority:
    operation: str
    authority_id: str
    issued_by: str
    issued_at: str
    expires_at: str
    scope_digest: str
    source_ids: tuple[str, ...]
    asset_ids: tuple[tuple[str, tuple[str, ...]], ...]
    publication_authorized: bool = False

    def assets_for(self, source_id: str) -> frozenset[str]:
        for source, assets in self.asset_ids:
            if source == source_id:
                return frozenset(assets)
        return frozenset()


def scope_digest(payloads: Mapping[str, Any] | Sequence[Any]) -> str:
    """Return the canonical digest used to bind authority to frozen metadata."""
    if isinstance(payloads, Mapping):
        value: Any = dict(sorted(payloads.items()))
    else:
        value = list(payloads)
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ExecutionAuthorityError("AUTHORITY_SCOPE_INVALID") from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _fail(code: str) -> None:
    raise ExecutionAuthorityError(code)


def _string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        _fail(code)
    return value


def _safe_id(value: Any, code: str) -> str:
    value = _string(value, code)
    if not _SAFE_ID.fullmatch(value) or "\\" in value or any(ord(c) < 32 for c in value):
        _fail(code)
    return value


def _timestamp(value: Any, code: str) -> datetime:
    value = _string(value, code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExecutionAuthorityError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(code)
    return parsed.astimezone(timezone.utc)


def _validate_asset_ids(value: Any, source_ids: frozenset[str]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if not isinstance(value, Mapping) or set(value) != set(source_ids):
        _fail("AUTHORITY_ASSET_SCOPE_INVALID")
    result: list[tuple[str, tuple[str, ...]]] = []
    for source_id in sorted(source_ids):
        raw_assets = value[source_id]
        if not isinstance(raw_assets, list) or not raw_assets:
            _fail("AUTHORITY_ASSET_SCOPE_INVALID")
        assets = tuple(_safe_id(item, "AUTHORITY_ASSET_ID_INVALID") for item in raw_assets)
        if len(set(assets)) != len(assets):
            _fail("AUTHORITY_ASSET_SCOPE_INVALID")
        result.append((source_id, assets))
    return tuple(result)


def validate_execution_authority(
    payload: Mapping[str, Any],
    *,
    operation: str | M11Operation,
    expected_scope_digest: str,
    allowed_source_ids: Iterable[str] = FROZEN_P0_SOURCE_IDS,
    now: datetime | None = None,
) -> ExecutionAuthority:
    """Validate one explicit authority record without changing lifecycle state."""
    if not isinstance(payload, Mapping):
        _fail("AUTHORITY_ROOT_INVALID")
    if set(payload) != _AUTHORITY_FIELDS:
        _fail("AUTHORITY_FIELDS_INVALID")
    if set(payload) & _FORBIDDEN_KEYS:
        _fail("AUTHORITY_PRIVACY_FIELD")
    if payload["schema"] != AUTHORITY_SCHEMA:
        _fail("AUTHORITY_SCHEMA_INVALID")

    requested_operation = str(operation)
    if requested_operation not in _ALLOWED_OPERATIONS:
        _fail("AUTHORITY_OPERATION_INVALID")
    if payload["operation"] != requested_operation:
        _fail("AUTHORITY_OPERATION_MISMATCH")
    if payload["status"] != "AUTHORIZED" or payload["metadata_only"] is not False:
        _fail("AUTHORITY_NOT_EXECUTABLE")
    if payload["publication_authorized"] is not False:
        _fail("AUTHORITY_PUBLICATION_FORBIDDEN")

    authority_id = _safe_id(payload["authority_id"], "AUTHORITY_ID_INVALID")
    issued_by = _safe_id(payload["issued_by"], "AUTHORITY_ISSUER_INVALID")
    issued_at = _timestamp(payload["issued_at"], "AUTHORITY_TIMESTAMP_INVALID")
    expires_at = _timestamp(payload["expires_at"], "AUTHORITY_TIMESTAMP_INVALID")
    if expires_at <= issued_at:
        _fail("AUTHORITY_EXPIRY_INVALID")
    if now is not None:
        current = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
        if current < issued_at or current >= expires_at:
            _fail("AUTHORITY_EXPIRED")

    digest = _string(payload["scope_digest"], "AUTHORITY_SCOPE_INVALID")
    if not _HEX_DIGEST.fullmatch(digest) or digest != expected_scope_digest:
        _fail("AUTHORITY_SCOPE_MISMATCH")

    allowed = frozenset(allowed_source_ids)
    if not allowed or not allowed <= FROZEN_P0_SOURCE_IDS:
        _fail("AUTHORITY_SCOPE_INVALID")
    raw_sources = payload["source_ids"]
    if not isinstance(raw_sources, list) or not raw_sources:
        _fail("AUTHORITY_SOURCE_SCOPE_INVALID")
    source_ids = tuple(_safe_id(item, "AUTHORITY_SOURCE_ID_INVALID") for item in raw_sources)
    if len(set(source_ids)) != len(source_ids) or not set(source_ids) <= allowed:
        _fail("AUTHORITY_SOURCE_SCOPE_INVALID")
    assets = _validate_asset_ids(payload["asset_ids"], frozenset(source_ids))
    return ExecutionAuthority(
        operation=requested_operation,
        authority_id=authority_id,
        issued_by=issued_by,
        issued_at=issued_at.isoformat(),
        expires_at=expires_at.isoformat(),
        scope_digest=digest,
        source_ids=source_ids,
        asset_ids=assets,
    )


def assert_batch_authorized(
    authority: ExecutionAuthority,
    batch: Mapping[str, Iterable[str]],
) -> None:
    """Reject any source or asset not explicitly included in the authority."""
    if set(batch) - set(authority.source_ids):
        _fail("AUTHORITY_BATCH_OUT_OF_SCOPE")
    for source_id, raw_assets in batch.items():
        requested = tuple(raw_assets)
        if any(not isinstance(asset, str) or asset not in authority.assets_for(source_id)
               for asset in requested):
            _fail("AUTHORITY_BATCH_OUT_OF_SCOPE")


def load_execution_authority(path: Any, **kwargs: Any) -> ExecutionAuthority:
    """Load one local JSON authority record; no path is included in errors."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionAuthorityError("AUTHORITY_UNREADABLE") from exc
    return validate_execution_authority(payload, **kwargs)
