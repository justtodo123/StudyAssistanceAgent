"""Metadata-only contract for RFC exact-three candidate materialization."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

SCHEMA = "sa.m11.p0.rfc-candidate-materialization.v1"
SOURCE_ID = "rfc-editor-index"
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
EXPECTED_ASSETS = frozenset({"rfc1034", "rfc9110", "rfc9293"})
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_FIELDS = frozenset({
    "schema", "materialization_id", "generated_at", "source_id", "asset_ids",
    "scope_digest", "input_asset_count", "candidate_asset_count",
    "validated_candidate_artifact_count", "candidate_chunk_count", "assets",
    "rejections", "approved_document_count", "approved_chunk_count",
    "counts_toward_3k", "formal_gate0_executed", "candidate_approval_granted",
    "publication_authorized", "network_used", "source_expansion",
    "lifecycle_mutation", "host_paths_included", "bodies_included",
})
_ASSET_FIELDS = frozenset({
    "asset_id", "candidate_artifact", "candidate_artifact_sha256",
    "normalized_artifact", "normalized_artifact_sha256", "document_id",
    "chunk_count", "content_fingerprint", "candidate_digest", "revision",
    "source_blob_sha1", "status",
})


class RfcCandidateMaterializationError(ValueError):
    """The RFC candidate materialization checkpoint is invalid."""


def _fail(code: str) -> NoReturn:
    raise RfcCandidateMaterializationError(code)


def _digest(value: Any, code: str) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail(code)
    return value


def _artifact_name(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith(".json") or "/" in value or "\\" in value:
        _fail("RFC_MATERIALIZATION_ARTIFACT_INVALID")
    return value


def validate_rfc_candidate_materialization(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate RFC candidate identities and non-promotion boundaries."""
    if not isinstance(payload, Mapping) or set(payload) != _FIELDS:
        _fail("RFC_MATERIALIZATION_FIELDS_INVALID")
    if payload["schema"] != SCHEMA or payload["source_id"] != SOURCE_ID:
        _fail("RFC_MATERIALIZATION_IDENTITY_INVALID")
    if payload["scope_digest"] != SCOPE_DIGEST:
        _fail("RFC_MATERIALIZATION_SCOPE_INVALID")
    if payload["asset_ids"] != sorted(EXPECTED_ASSETS) or payload["generated_at"] != "2026-09-28":
        _fail("RFC_MATERIALIZATION_SCOPE_INVALID")
    if not isinstance(payload["materialization_id"], str) or not _ID.fullmatch(payload["materialization_id"]):
        _fail("RFC_MATERIALIZATION_ID_INVALID")
    if any(payload[field] is not False for field in (
        "counts_toward_3k", "formal_gate0_executed", "candidate_approval_granted",
        "publication_authorized", "network_used", "source_expansion",
        "lifecycle_mutation", "host_paths_included", "bodies_included",
    )):
        _fail("RFC_MATERIALIZATION_ESCALATION_FORBIDDEN")
    if payload["approved_document_count"] != 0 or payload["approved_chunk_count"] != 0:
        _fail("RFC_MATERIALIZATION_APPROVAL_FORBIDDEN")
    assets = payload["assets"]
    if not isinstance(assets, Sequence) or isinstance(assets, (str, bytes)):
        _fail("RFC_MATERIALIZATION_ASSETS_INVALID")
    if payload["rejections"] != []:
        _fail("RFC_MATERIALIZATION_REJECTIONS_INVALID")
    expected_digests = {
        "rfc1034": "d6b10a71441df879cc2817d23f2dad120c8a5f87e74eba1e4ed4b743a76a891a",
        "rfc9110": "21c1cdce6ab0e5509b04d84a28000836c7a087cf786efe6f04877ebfff47232a",
        "rfc9293": "6d9ac8be4b0286f8c3d337addf442b2eb6a9b14e1366594ea7fbc273f93dc2d9",
    }
    seen: set[str] = set()
    chunks = 0
    for item in assets:
        if not isinstance(item, Mapping) or set(item) != _ASSET_FIELDS:
            _fail("RFC_MATERIALIZATION_ASSET_FIELDS_INVALID")
        asset = item["asset_id"]
        if asset in seen or asset not in EXPECTED_ASSETS:
            _fail("RFC_MATERIALIZATION_ASSET_SCOPE_INVALID")
        seen.add(asset)
        if item["status"] != "CANDIDATE_VALIDATED" or item["source_blob_sha1"] is not None:
            _fail("RFC_MATERIALIZATION_ASSET_STATUS_INVALID")
        _artifact_name(item["candidate_artifact"])
        _artifact_name(item["normalized_artifact"])
        for field in ("candidate_artifact_sha256", "normalized_artifact_sha256", "content_fingerprint", "candidate_digest", "revision"):
            _digest(item[field], "RFC_MATERIALIZATION_DIGEST_INVALID")
        if item["candidate_digest"] != expected_digests[asset] or item["revision"] != expected_digests[asset]:
            _fail("RFC_MATERIALIZATION_IDENTITY_DIGEST_INVALID")
        if not isinstance(item["document_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", item["document_id"]):
            _fail("RFC_MATERIALIZATION_DOCUMENT_ID_INVALID")
        if isinstance(item["chunk_count"], bool) or not isinstance(item["chunk_count"], int) or item["chunk_count"] < 1:
            _fail("RFC_MATERIALIZATION_CHUNK_COUNT_INVALID")
        chunks += item["chunk_count"]
    if seen != EXPECTED_ASSETS or len(assets) != 3:
        _fail("RFC_MATERIALIZATION_PARTITION_INVALID")
    if (
        payload["input_asset_count"] != 3
        or payload["candidate_asset_count"] != 3
        or payload["validated_candidate_artifact_count"] != 3
        or payload["candidate_chunk_count"] != chunks
    ):
        _fail("RFC_MATERIALIZATION_COUNTS_INVALID")
    return copy.deepcopy(dict(payload))
