"""Metadata-only contract for the local MIT OCW candidate materialization checkpoint."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

SCHEMA = "sa.m11.p0.mit-ocw-candidate-materialization.v1"
SOURCE_ID = "mit-ocw-6-004-2017"
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
EXPECTED_CANDIDATES = frozenset({
    "beta_answers", "beta_worksheet", "caches_answers", "caches_worksheet",
    "cmos_answers", "cmos_worksheet", "combinational_answers",
    "combinational_worksheet", "compilation_answers", "compilation_worksheet",
    "digital_worksheet", "fsm_answers", "fsm_worksheet", "information_answers",
    "interrupts_answers", "interrupts_worksheet", "isa_answers", "isa_worksheet",
})
EXPECTED_REJECTIONS = {
    "digital_answers": "SOURCE_PARSE_FAILED",
    "information_worksheet": "INVALID_CANDIDATE_INPUT",
}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_FIELDS = frozenset({
    "schema", "materialization_id", "generated_at", "source_id", "scope_digest",
    "input_asset_count", "candidate_asset_count", "rejected_asset_count",
    "validated_candidate_artifact_count", "candidate_chunk_count", "assets",
    "rejections", "approved_document_count", "approved_chunk_count",
    "counts_toward_3k", "formal_gate0_executed",
    "candidate_promotion_authorized", "publication_authorized", "network_used",
    "source_expansion", "lifecycle_mutation", "host_paths_included",
    "bodies_included",
})
_ASSET_FIELDS = frozenset({
    "asset_id", "candidate_artifact", "candidate_artifact_sha256",
    "normalized_artifact", "normalized_artifact_sha256", "document_id",
    "chunk_count", "content_fingerprint", "candidate_digest", "status",
})
_REJECTION_FIELDS = frozenset({
    "asset_id", "rejected_artifact", "rejected_artifact_sha256", "reason", "status",
})
_FALSE_FLAGS = (
    "counts_toward_3k", "formal_gate0_executed", "candidate_promotion_authorized",
    "publication_authorized", "network_used", "source_expansion",
    "lifecycle_mutation", "host_paths_included", "bodies_included",
)


class MitOcwCandidateMaterializationError(ValueError):
    """The candidate materialization checkpoint is malformed or escalates scope."""


def _fail(code: str) -> NoReturn:
    raise MitOcwCandidateMaterializationError(code)


def _digest(value: Any, code: str) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail(code)
    return value


def _artifact_name(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.endswith(".json") or "/" in value or "\\" in value:
        _fail(code)
    return value


def validate_mit_ocw_candidate_materialization(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate counts, identities and non-promotion boundaries without reading bodies."""
    if not isinstance(payload, Mapping) or set(payload) != _FIELDS:
        _fail("MIT_MATERIALIZATION_FIELDS_INVALID")
    if payload["schema"] != SCHEMA or payload["source_id"] != SOURCE_ID:
        _fail("MIT_MATERIALIZATION_IDENTITY_INVALID")
    if payload["scope_digest"] != SCOPE_DIGEST:
        _fail("MIT_MATERIALIZATION_SCOPE_INVALID")
    if not isinstance(payload["materialization_id"], str) or not _ID.fullmatch(payload["materialization_id"]):
        _fail("MIT_MATERIALIZATION_ID_INVALID")
    if payload["generated_at"] != "2026-09-28":
        _fail("MIT_MATERIALIZATION_DATE_INVALID")
    if any(payload[field] is not False for field in _FALSE_FLAGS):
        _fail("MIT_MATERIALIZATION_ESCALATION_FORBIDDEN")
    if payload["approved_document_count"] != 0 or payload["approved_chunk_count"] != 0:
        _fail("MIT_MATERIALIZATION_APPROVAL_FORBIDDEN")

    assets = payload["assets"]
    rejections = payload["rejections"]
    if not isinstance(assets, Sequence) or isinstance(assets, (str, bytes)):
        _fail("MIT_MATERIALIZATION_ASSETS_INVALID")
    if not isinstance(rejections, Sequence) or isinstance(rejections, (str, bytes)):
        _fail("MIT_MATERIALIZATION_REJECTIONS_INVALID")

    asset_ids: set[str] = set()
    chunk_count = 0
    for item in assets:
        if not isinstance(item, Mapping) or set(item) != _ASSET_FIELDS:
            _fail("MIT_MATERIALIZATION_ASSET_FIELDS_INVALID")
        asset_id = item["asset_id"]
        if asset_id in asset_ids or asset_id not in EXPECTED_CANDIDATES:
            _fail("MIT_MATERIALIZATION_ASSET_SCOPE_INVALID")
        asset_ids.add(asset_id)
        if item["status"] != "CANDIDATE_VALIDATED":
            _fail("MIT_MATERIALIZATION_ASSET_STATUS_INVALID")
        _artifact_name(item["candidate_artifact"], "MIT_MATERIALIZATION_ARTIFACT_INVALID")
        _artifact_name(item["normalized_artifact"], "MIT_MATERIALIZATION_ARTIFACT_INVALID")
        for field in (
            "candidate_artifact_sha256", "normalized_artifact_sha256",
            "content_fingerprint", "candidate_digest",
        ):
            _digest(item[field], "MIT_MATERIALIZATION_DIGEST_INVALID")
        if not isinstance(item["document_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", item["document_id"]):
            _fail("MIT_MATERIALIZATION_DOCUMENT_ID_INVALID")
        if isinstance(item["chunk_count"], bool) or not isinstance(item["chunk_count"], int) or item["chunk_count"] < 1:
            _fail("MIT_MATERIALIZATION_CHUNK_COUNT_INVALID")
        chunk_count += item["chunk_count"]

    rejection_by_asset: dict[str, str] = {}
    for item in rejections:
        if not isinstance(item, Mapping) or set(item) != _REJECTION_FIELDS:
            _fail("MIT_MATERIALIZATION_REJECTION_FIELDS_INVALID")
        asset_id = item["asset_id"]
        if asset_id in rejection_by_asset or asset_id not in EXPECTED_REJECTIONS:
            _fail("MIT_MATERIALIZATION_REJECTION_SCOPE_INVALID")
        rejection_by_asset[asset_id] = item["reason"]
        if item["status"] != "REJECTED":
            _fail("MIT_MATERIALIZATION_REJECTION_STATUS_INVALID")
        _artifact_name(item["rejected_artifact"], "MIT_MATERIALIZATION_ARTIFACT_INVALID")
        _digest(item["rejected_artifact_sha256"], "MIT_MATERIALIZATION_DIGEST_INVALID")

    if asset_ids != EXPECTED_CANDIDATES or rejection_by_asset != EXPECTED_REJECTIONS:
        _fail("MIT_MATERIALIZATION_PARTITION_INVALID")
    if (
        payload["input_asset_count"] != 20
        or payload["candidate_asset_count"] != len(assets)
        or payload["validated_candidate_artifact_count"] != len(assets)
        or payload["rejected_asset_count"] != len(rejections)
        or payload["candidate_chunk_count"] != chunk_count
    ):
        _fail("MIT_MATERIALIZATION_COUNTS_INVALID")
    return copy.deepcopy(dict(payload))
