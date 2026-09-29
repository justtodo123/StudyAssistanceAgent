"""Metadata-only RFC exact-three content-quality sampling checkpoint."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
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
_RESULT_FIELDS = frozenset({
    "schema", "sampling_result_id", "sampling_checkpoint_id", "generated_at", "source_id", "asset_ids", "scope_digest",
    "technical_sampling_status", "sample_size", "mode", "assets", "content_quality_status",
    "approved_document_count", "approved_chunk_count", "counts_toward_3k", "formal_gate0_executed",
    "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion",
    "lifecycle_mutation", "host_paths_included", "bodies_included",
})
_CHECKPOINT_ASSET_FIELDS = frozenset({
    "asset_id", "document_id", "candidate_artifact", "candidate_artifact_sha256",
    "normalized_artifact", "normalized_artifact_sha256", "candidate_digest",
    "revision", "format", "chunk_schema", "unit_kind", "ordinal", "chunk_count",
    "validator_status", "content_quality_status",
})
_RESULT_ASSET_FIELDS = frozenset({
    "asset_id", "document_id", "candidate_artifact_sha256",
    "normalized_artifact_sha256", "candidate_digest", "revision",
    "technical_status", "text_non_empty", "line_count", "character_count",
    "non_empty_unit_count", "chunk_count", "content_quality_status",
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


def sample_rfc_content_quality_bodies(
    *,
    candidate_root: Path,
    normalized_root: Path,
) -> dict[str, Any]:
    """Inspect local normalized bodies and return metadata-only technical facts."""
    from app.m11_candidate_artifact_validator import load_and_validate_candidate_artifact

    sampled: list[dict[str, Any]] = []
    for asset_id in ASSETS:
        candidate_path = candidate_root / f"rfc-editor-index-{asset_id}.json"
        normalized_path = normalized_root / candidate_path.name
        candidate = load_and_validate_candidate_artifact(candidate_path)
        if not normalized_path.is_file():
            _fail("RFC_QUALITY_NORMALIZED_ARTIFACT_MISSING")
        normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
        required_normalized = {
            "schema_name", "schema_version", "source_id", "document_id", "logical_uri",
            "format", "parser_id", "parser_version", "content_fingerprint",
            "normalized_text_digest", "units",
        }
        if not isinstance(normalized, Mapping) or set(normalized) != required_normalized:
            _fail("RFC_QUALITY_NORMALIZED_FIELDS_INVALID")
        text_units = normalized["units"]
        if not isinstance(text_units, list) or len(text_units) != 1:
            _fail("RFC_QUALITY_UNIT_COUNT_INVALID")
        unit = text_units[0]
        text = unit.get("text") if isinstance(unit, Mapping) else None
        if not isinstance(text, str) or not text.strip():
            _fail("RFC_QUALITY_TEXT_EMPTY")
        document = candidate["document"]
        if (
            normalized["document_id"] != document["document_id"]
            or normalized["content_fingerprint"] != candidate["content_digest"]
            or candidate["content_digest"] != candidate["revision"]
            or normalized["format"] != "txt"
            or unit.get("unit_kind") != "document"
            or unit.get("ordinal") != 0
        ):
            _fail("RFC_QUALITY_IDENTITY_MISMATCH")
        sampled.append({
            "asset_id": asset_id,
            "document_id": document["document_id"],
            "candidate_artifact_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
            "normalized_artifact_sha256": hashlib.sha256(normalized_path.read_bytes()).hexdigest(),
            "candidate_digest": candidate["content_digest"],
            "revision": candidate["revision"],
            "technical_status": "VERIFIED",
            "text_non_empty": True,
            "line_count": len(text.splitlines()),
            "character_count": len(text),
            "non_empty_unit_count": sum(1 for line in text.splitlines() if line.strip()),
            "chunk_count": document["chunk_count"],
            "content_quality_status": "PENDING",
        })
    return {
        "technical_sampling_status": "VERIFIED",
        "sample_size": len(sampled),
        "mode": "census",
        "assets": sampled,
    }


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
        if not isinstance(item, Mapping) or set(item) != _CHECKPOINT_ASSET_FIELDS:
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


def validate_rfc_content_quality_sampling_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the local technical result without making a quality decision."""
    if not isinstance(payload, Mapping) or set(payload) != _RESULT_FIELDS:
        _fail("RFC_QUALITY_RESULT_FIELDS_INVALID")
    if payload["schema"] != "sa.m11.p0.rfc-content-quality-sampling-result.v1":
        _fail("RFC_QUALITY_RESULT_SCHEMA_INVALID")
    if payload["source_id"] != SOURCE_ID or payload["asset_ids"] != list(ASSETS) or payload["scope_digest"] != SCOPE_DIGEST:
        _fail("RFC_QUALITY_RESULT_SCOPE_INVALID")
    if payload["sampling_result_id"] != "m11-p0-rfc-content-quality-sampling-result-20260928" or payload["sampling_checkpoint_id"] != "m11-p0-rfc-content-quality-sampling-20260928":
        _fail("RFC_QUALITY_RESULT_LINK_INVALID")
    if payload["technical_sampling_status"] != "VERIFIED" or payload["sample_size"] != 3 or payload["mode"] != "census" or payload["content_quality_status"] != "PENDING":
        _fail("RFC_QUALITY_RESULT_STATUS_INVALID")
    if payload["approved_document_count"] != 0 or payload["approved_chunk_count"] != 0:
        _fail("RFC_QUALITY_RESULT_APPROVAL_FORBIDDEN")
    if any(payload[field] is not False for field in ("counts_toward_3k", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")):
        _fail("RFC_QUALITY_RESULT_ESCALATION_FORBIDDEN")
    assets = payload["assets"]
    if not isinstance(assets, Sequence) or isinstance(assets, (str, bytes)) or len(assets) != 3:
        _fail("RFC_QUALITY_RESULT_ASSETS_INVALID")
    seen: set[str] = set()
    digests: set[str] = set()
    for item in assets:
        if not isinstance(item, Mapping) or set(item) != _RESULT_ASSET_FIELDS:
            _fail("RFC_QUALITY_RESULT_ASSET_FIELDS_INVALID")
        if item["asset_id"] not in ASSETS or item["asset_id"] in seen or item["technical_status"] != "VERIFIED" or item["content_quality_status"] != "PENDING" or item["text_non_empty"] is not True or item["chunk_count"] != 1:
            _fail("RFC_QUALITY_RESULT_ASSET_STATUS_INVALID")
        seen.add(item["asset_id"])
        for field in ("candidate_artifact_sha256", "normalized_artifact_sha256", "candidate_digest", "revision"):
            _digest(item[field])
        if any(isinstance(item[field], bool) or not isinstance(item[field], int) or item[field] < 1 for field in ("line_count", "character_count", "non_empty_unit_count")):
            _fail("RFC_QUALITY_RESULT_METRICS_INVALID")
        digests.add(item["candidate_digest"])
    if seen != set(ASSETS) or len(digests) != 3:
        _fail("RFC_QUALITY_RESULT_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))
