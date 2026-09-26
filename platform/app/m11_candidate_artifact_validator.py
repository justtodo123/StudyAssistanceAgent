"""Offline validation for serialized, metadata-only M11 candidate artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .m11_candidate_artifact_contract import (
    CANDIDATE_ARTIFACT_SCHEMA,
    candidate_source_id_for_label,
)
from .normalized_document import CHUNK_SCHEMA_VERSION
from .source_policy import IngestStatus, SourceType


_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_SHA1_RE = re.compile(r"[0-9a-f]{40}\Z")
_ROOT_FIELDS = {
    "schema", "source_label", "source_id", "asset_id", "canonical_url",
    "content_digest", "revision", "source_blob_sha1", "document", "chunks",
    "license_status", "ingest_status", "source_type", "approved", "published",
}
_DOCUMENT_FIELDS = {
    "source_id", "document_id", "logical_uri", "format", "content_fingerprint", "chunk_count",
}
_CHUNK_FIELDS = {
    "source_id", "document_id", "logical_uri", "chunk_key", "chunk_id",
    "chunk_schema", "content_digest", "title", "unit_kind", "ordinal",
}
_FORBIDDEN_KEYS = {
    "body", "content", "text", "raw_content", "normalized_content", "credential",
    "credentials", "password", "token", "learning_state", "private_learning_state",
    "raw_path", "normalized_path", "candidate_path", "rejected_path", "reviewer",
    "signature", "sign_off", "gold_document_id", "sample_content", "approval",
    "publication", "published_at",
}


class CandidateArtifactValidationError(ValueError):
    """Raised when a serialized M11 candidate artifact fails integrity validation."""


def _fail(code: str) -> None:
    raise CandidateArtifactValidationError(code)


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        return set(value) | {key for child in value.values() for key in _walk_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in _walk_keys(child)}
    return set()


def _require_object(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(code)
    return value


def _require_string(value: Any, code: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        _fail(code)
    return value


def _safe_identifier(value: Any, code: str, *, allow_path: bool) -> str:
    value = _require_string(value, code)
    if value != value.strip() or value in {".", ".."} or any(ord(char) < 32 for char in value):
        _fail(code)
    normalized = value.replace("\\", "/")
    parts = normalized.split("/")
    if not allow_path and len(parts) != 1:
        _fail(code)
    if normalized.startswith("/") or ":" in normalized:
        _fail(code)
    if any(part in {"", ".", ".."} for part in parts):
        _fail(code)
    return normalized


def _require_digest(value: Any, code: str, pattern: re.Pattern[str]) -> str:
    value = _require_string(value, code)
    if not pattern.fullmatch(value):
        _fail(code)
    return value


def _validate_artifact_name(name: str, source_label: str, asset_id: str) -> None:
    if not isinstance(name, str) or name != Path(name).name:
        _fail("CANDIDATE_ARTIFACT_NAME_INVALID")
    expected = f"{source_label}-{asset_id.replace('/', '__')}.json"
    if name != expected:
        _fail("CANDIDATE_ARTIFACT_NAME_INVALID")


def validate_candidate_artifact(
    payload: Mapping[str, Any], *, artifact_name: str | None = None
) -> None:
    """Fail closed unless *payload* is one valid candidate-only artifact."""
    root = _require_object(payload, "CANDIDATE_ARTIFACT_ROOT_INVALID")
    if set(root) != _ROOT_FIELDS:
        _fail("CANDIDATE_ARTIFACT_FIELDS_INVALID")
    if _walk_keys(root) & _FORBIDDEN_KEYS:
        _fail("CANDIDATE_ARTIFACT_PRIVACY_FIELD")

    if root["schema"] != CANDIDATE_ARTIFACT_SCHEMA:
        _fail("CANDIDATE_ARTIFACT_SCHEMA_INVALID")
    source_label = _safe_identifier(root["source_label"], "CANDIDATE_ARTIFACT_SOURCE_LABEL_INVALID", allow_path=False)
    asset_id = _safe_identifier(root["asset_id"], "CANDIDATE_ARTIFACT_ASSET_ID_INVALID", allow_path=True)
    if artifact_name is not None:
        _validate_artifact_name(artifact_name, source_label, asset_id)

    source_id = _require_string(root["source_id"], "CANDIDATE_ARTIFACT_SOURCE_ID_INVALID")
    if source_id != candidate_source_id_for_label(source_label):
        _fail("CANDIDATE_ARTIFACT_SOURCE_ID_MISMATCH")
    if root["canonical_url"] is None or not isinstance(root["canonical_url"], str) or not root["canonical_url"].startswith("https://"):
        _fail("CANDIDATE_ARTIFACT_PROVENANCE_INVALID")
    _require_string(root["revision"], "CANDIDATE_ARTIFACT_PROVENANCE_INVALID")
    blob_sha1 = root["source_blob_sha1"]
    if blob_sha1 is not None:
        _require_digest(blob_sha1, "CANDIDATE_ARTIFACT_PROVENANCE_INVALID", _SHA1_RE)
    _require_digest(root["content_digest"], "CANDIDATE_ARTIFACT_DIGEST_INVALID", _SHA256_RE)

    if root["license_status"] != "review_required":
        _fail("CANDIDATE_ARTIFACT_LICENSE_INVALID")
    if root["ingest_status"] != IngestStatus.CANDIDATE.value:
        _fail("CANDIDATE_ARTIFACT_LIFECYCLE_INVALID")
    if root["source_type"] != SourceType.USER_REGISTERED.value:
        _fail("CANDIDATE_ARTIFACT_SOURCE_TYPE_INVALID")
    if root["approved"] is not False or root["published"] is not False:
        _fail("CANDIDATE_ARTIFACT_LIFECYCLE_INVALID")

    document = _require_object(root["document"], "CANDIDATE_ARTIFACT_DOCUMENT_INVALID")
    if set(document) != _DOCUMENT_FIELDS:
        _fail("CANDIDATE_ARTIFACT_DOCUMENT_FIELDS_INVALID")
    if document["source_id"] != source_id or document["logical_uri"] != asset_id:
        _fail("CANDIDATE_ARTIFACT_DOCUMENT_LINK_INVALID")
    document_id = _require_string(document["document_id"], "CANDIDATE_ARTIFACT_DOCUMENT_ID_INVALID")
    expected_document_id = hashlib.sha256(f"{source_id}\0{asset_id}".encode("utf-8")).hexdigest()[:32]
    if document_id != expected_document_id:
        _fail("CANDIDATE_ARTIFACT_DOCUMENT_ID_MISMATCH")
    _require_string(document["format"], "CANDIDATE_ARTIFACT_DOCUMENT_INVALID")
    fingerprint = _require_digest(document["content_fingerprint"], "CANDIDATE_ARTIFACT_DIGEST_INVALID", _SHA256_RE)
    if fingerprint != root["content_digest"]:
        _fail("CANDIDATE_ARTIFACT_DIGEST_MISMATCH")

    chunks = root["chunks"]
    if not isinstance(chunks, list) or not chunks:
        _fail("CANDIDATE_ARTIFACT_CHUNKS_INVALID")
    if document["chunk_count"] != len(chunks) or isinstance(document["chunk_count"], bool) or not isinstance(document["chunk_count"], int):
        _fail("CANDIDATE_ARTIFACT_CHUNK_COUNT_INVALID")
    chunk_keys: set[str] = set()
    chunk_ids: set[str] = set()
    ordinals: set[int] = set()
    for chunk_value in chunks:
        chunk = _require_object(chunk_value, "CANDIDATE_ARTIFACT_CHUNK_INVALID")
        if set(chunk) != _CHUNK_FIELDS:
            _fail("CANDIDATE_ARTIFACT_CHUNK_FIELDS_INVALID")
        if chunk["source_id"] != source_id or chunk["document_id"] != document_id or chunk["logical_uri"] != asset_id:
            _fail("CANDIDATE_ARTIFACT_CHUNK_LINK_INVALID")
        chunk_key = _require_string(chunk["chunk_key"], "CANDIDATE_ARTIFACT_CHUNK_KEY_INVALID")
        chunk_schema = chunk["chunk_schema"]
        if chunk_schema != CHUNK_SCHEMA_VERSION:
            _fail("CANDIDATE_ARTIFACT_CHUNK_SCHEMA_INVALID")
        chunk_id = _require_string(chunk["chunk_id"], "CANDIDATE_ARTIFACT_CHUNK_ID_INVALID")
        expected_chunk_id = hashlib.sha256(
            f"{document_id}\0{chunk_key}\0{chunk_schema}".encode("utf-8")
        ).hexdigest()[:32]
        if chunk_id != expected_chunk_id:
            _fail("CANDIDATE_ARTIFACT_CHUNK_ID_MISMATCH")
        if chunk_key in chunk_keys or chunk_id in chunk_ids:
            _fail("CANDIDATE_ARTIFACT_CHUNK_DUPLICATE")
        chunk_keys.add(chunk_key)
        chunk_ids.add(chunk_id)
        _require_digest(chunk["content_digest"], "CANDIDATE_ARTIFACT_DIGEST_INVALID", _SHA256_RE)
        _require_string(chunk["title"], "CANDIDATE_ARTIFACT_CHUNK_INVALID", nonempty=False)
        _require_string(chunk["unit_kind"], "CANDIDATE_ARTIFACT_CHUNK_INVALID")
        ordinal = chunk["ordinal"]
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0 or ordinal in ordinals:
            _fail("CANDIDATE_ARTIFACT_ORDINAL_INVALID")
        ordinals.add(ordinal)


def load_and_validate_candidate_artifact(path: Path) -> Mapping[str, Any]:
    """Load and validate one local candidate artifact without modifying it."""
    try:
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail("CANDIDATE_ARTIFACT_UNREADABLE")
    if not isinstance(payload, Mapping):
        _fail("CANDIDATE_ARTIFACT_ROOT_INVALID")
    validate_candidate_artifact(payload, artifact_name=path.name)
    return payload
