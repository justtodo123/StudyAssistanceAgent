"""Metadata-only RFC exact-three content-quality sampling checkpoint."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

SCHEMA = "sa.m11.p0.rfc-content-quality-sampling.v1"
SOURCE_ID = "rfc-editor-index"
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
ASSETS = ("rfc1034", "rfc9110", "rfc9293")
MATERIALIZATION_ID = "m11-p0-rfc-candidate-materialization-20260928"
SCHEMA_RESULT_ID = "m11-p0-rfc-schema-review-result-20260928"
TECHNICAL_RESULT_ID = "m11-p0-rfc-technical-evidence-review-result-20260928"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_FIELDS = frozenset({
    "schema", "sampling_id", "generated_at", "source_id", "asset_ids", "scope_digest",
    "materialization_id", "schema_decision_reference", "technical_decision_reference",
    "input_asset_count", "candidate_asset_count", "validated_candidate_artifact_count",
    "rejected_asset_count", "candidate_chunk_count", "distinct_content_digest_count",
    "parser_environment", "sampling_unit", "sampling_plan", "assets",
    "content_quality_status", "approved_document_count", "approved_chunk_count",
    "counts_toward_3k", "formal_gate0_executed", "candidate_approval_granted",
    "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation",
    "host_paths_included", "bodies_included",
})
_ASSET_FIELDS = frozenset({
    "asset_id", "document_id", "candidate_artifact", "candidate_artifact_sha256",
    "normalized_artifact", "normalized_artifact_sha256", "candidate_digest",
    "revision", "format", "chunk_schema", "unit_kind", "ordinal", "chunk_count",
    "validator_status", "content_quality_status",
})


class RfcContentQualitySamplingError(ValueError):
    """The metadata-only RFC content-quality sampling checkpoint is invalid."""


def _fail(code: str) -> NoReturn:
    raise RfcContentQualitySamplingError(code)


def _digest(value: Any) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail("RFC_QUALITY_DIGEST_INVALID")
    return value


def _artifact_name(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith(".json") or "/" in value or "\\" in value:
        _fail("RFC_QUALITY_ARTIFACT_INVALID")
    return value


def validate_rfc_content_quality_sampling(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate reproducible structural facts without deciding content quality."""
    if not isinstance(payload, Mapping) or set(payload) != _FIELDS:
        _fail("RFC_QUALITY_FIELDS_INVALID")
    if payload["schema"] != SCHEMA or payload["source_id"] != SOURCE_ID or payload["scope_digest"] != SCOPE_DIGEST:
        _fail("RFC_QUALITY_IDENTITY_INVALID")
    if payload["asset_ids"] != list(ASSETS) or payload["generated_at"] != "2026-09-28":
        _fail("RFC_QUALITY_SCOPE_INVALID")
    if payload["materialization_id"] != MATERIALIZATION_ID or payload["schema_decision_reference"] != SCHEMA_RESULT_ID or payload["technical_decision_reference"] != TECHNICAL_RESULT_ID:
        _fail("RFC_QUALITY_LINK_INVALID")
    if payload["parser_environment"] != {"python": "3.11.9", "parser_contract": "cpython-textio==3.11.9", "format": "txt"}:
        _fail("RFC_QUALITY_PARSER_ENV_INVALID")
    if payload["sampling_unit"] != "candidate_chunk" or payload["sampling_plan"] != {"sample_size": 3, "stratification": "rfc-editor-index-exact-three", "mode": "census", "body_persisted": False}:
        _fail("RFC_QUALITY_SAMPLING_PLAN_INVALID")
    if payload["content_quality_status"] != "PENDING" or payload["rejected_asset_count"] != 0 or payload["distinct_content_digest_count"] != 3:
        _fail("RFC_QUALITY_STATUS_INVALID")
    if any(payload[field] is not False for field in ("counts_toward_3k", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")):
        _fail("RFC_QUALITY_ESCALATION_FORBIDDEN")
    if payload["approved_document_count"] != 0 or payload["approved_chunk_count"] != 0:
        _fail("RFC_QUALITY_APPROVAL_FORBIDDEN")
    assets = payload["assets"]
    if not isinstance(assets, Sequence) or isinstance(assets, (str, bytes)) or len(assets) != 3:
        _fail("RFC_QUALITY_ASSETS_INVALID")
    seen: set[str] = set()
    digests: set[str] = set()
    chunks = 0
    for item in assets:
        if not isinstance(item, Mapping) or set(item) != _ASSET_FIELDS:
            _fail("RFC_QUALITY_ASSET_FIELDS_INVALID")
        asset = item["asset_id"]
        if asset not in ASSETS or asset in seen:
            _fail("RFC_QUALITY_ASSET_SCOPE_INVALID")
        seen.add(asset)
        _artifact_name(item["candidate_artifact"])
        _artifact_name(item["normalized_artifact"])
        for field in ("candidate_artifact_sha256", "normalized_artifact_sha256", "candidate_digest", "revision"):
            _digest(item[field])
        if item["document_id"] == "" or not isinstance(item["document_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", item["document_id"]):
            _fail("RFC_QUALITY_DOCUMENT_ID_INVALID")
        if item["format"] != "txt" or item["chunk_schema"] != "sa.chunk.normalized-unit.v1" or item["unit_kind"] != "document" or item["ordinal"] != 0 or item["chunk_count"] != 1 or item["validator_status"] != "CANDIDATE_VALIDATED" or item["content_quality_status"] != "PENDING":
            _fail("RFC_QUALITY_STRUCTURE_INVALID")
        digests.add(item["candidate_digest"])
        chunks += item["chunk_count"]
    if seen != set(ASSETS) or chunks != 3 or payload["candidate_chunk_count"] != 3 or payload["distinct_content_digest_count"] != len(digests):
        _fail("RFC_QUALITY_COUNTS_INVALID")
    if payload["input_asset_count"] != 3 or payload["candidate_asset_count"] != 3 or payload["validated_candidate_artifact_count"] != 3:
        _fail("RFC_QUALITY_COUNTS_INVALID")
    return copy.deepcopy(dict(payload))
