from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, NoReturn

from app.m11_execution_authority import ExecutionAuthorityError, validate_execution_authority

SOURCE_ID = "rfc-editor-index"
ASSETS = ("rfc1034", "rfc9110", "rfc9293")
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
AUTHORITY_ID = "m11-rfc-technical-evidence-review-3-20260928"
SCHEMA_RESULT_ID = "m11-p0-rfc-schema-review-result-20260928"
SCHEMA_DECISION_REFERENCE = "m11-p0-rfc-schema-review-result-v1"
CATEGORIES = ("license", "revision", "robots_terms", "notice_ipr", "schema", "provenance", "parser", "content_quality")
VERIFIED_CATEGORIES = ("revision", "provenance", "parser")


class RfcTechnicalEvidenceReviewError(ValueError):
    """The RFC technical evidence review is invalid."""


def _fail(code: str) -> NoReturn:
    raise RfcTechnicalEvidenceReviewError(code)


def _timestamp(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RfcTechnicalEvidenceReviewError("RFC_TECHNICAL_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        _fail("RFC_TECHNICAL_TIMESTAMP_INVALID")
    return parsed


def validate_rfc_technical_authority(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        authority = validate_execution_authority(payload, operation="human_review", expected_scope_digest=SCOPE_DIGEST, allowed_source_ids={SOURCE_ID: ASSETS}, now=_timestamp("2026-09-28T13:01:00Z"))
    except ExecutionAuthorityError as exc:
        raise RfcTechnicalEvidenceReviewError(exc.code) from exc
    if authority.authority_id != AUTHORITY_ID or authority.source_ids != (SOURCE_ID,) or tuple(sorted(authority.assets_for(SOURCE_ID))) != tuple(sorted(ASSETS)):
        _fail("RFC_TECHNICAL_AUTHORITY_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))


def validate_rfc_technical_result(payload: Mapping[str, Any], *, authority: Mapping[str, Any], schema_result: Mapping[str, Any]) -> dict[str, Any]:
    validate_rfc_technical_authority(authority)
    required = {"schema", "result_id", "packet_id", "authority_id", "scope_digest", "signed_by", "signed_at", "decision_reference", "asset_count", "closed_cell_count", "verified_cell_count", "not_applicable_cell_count", "pending_cell_count", "failed_cell_count", "closure_effect", "result", "records", "schema_decision_reference", "successor_slice_written", "all_other_categories_remain_pending", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included"}
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("RFC_TECHNICAL_RESULT_FIELDS_INVALID")
    if payload["schema"] != "sa.m11.p0.rfc-technical-evidence-review-result.v1" or payload["result_id"] != "m11-p0-rfc-technical-evidence-review-result-20260928" or payload["authority_id"] != AUTHORITY_ID or payload["scope_digest"] != SCOPE_DIGEST:
        _fail("RFC_TECHNICAL_RESULT_IDENTITY_INVALID")
    if _timestamp(payload["signed_at"]) < _timestamp(authority["issued_at"]):
        _fail("RFC_TECHNICAL_RESULT_TIMESTAMP_ORDER_INVALID")
    if payload["schema_decision_reference"] != SCHEMA_DECISION_REFERENCE or schema_result.get("result_id") != SCHEMA_RESULT_ID:
        _fail("RFC_TECHNICAL_SCHEMA_RESULT_LINK_INVALID")
    if payload["asset_count"] != 3 or payload["closed_cell_count"] != 12 or payload["verified_cell_count"] != 9 or payload["not_applicable_cell_count"] != 3 or payload["pending_cell_count"] != 12 or payload["failed_cell_count"] != 0 or payload["closure_effect"] != "PARTIAL" or payload["result"] != "REVIEW_REQUIRED":
        _fail("RFC_TECHNICAL_RESULT_COUNTS_INVALID")
    if payload["successor_slice_written"] is not False or payload["all_other_categories_remain_pending"] is not True:
        _fail("RFC_TECHNICAL_SUCCESSOR_POLICY_INVALID")
    if any(payload[field] is not False for field in ("formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")):
        _fail("RFC_TECHNICAL_ESCALATION_FORBIDDEN")
    records = payload["records"]
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or len(records) != 3:
        _fail("RFC_TECHNICAL_RECORD_SCOPE_INVALID")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping) or record.get("asset_id") not in ASSETS or record["asset_id"] in seen:
            _fail("RFC_TECHNICAL_RECORD_SCOPE_INVALID")
        seen.add(record["asset_id"])
        if set(record) != {"asset_id", *VERIFIED_CATEGORIES}:
            _fail("RFC_TECHNICAL_RECORD_FIELDS_INVALID")
        for category in VERIFIED_CATEGORIES:
            item = record[category]
            if not isinstance(item, Mapping) or set(item) != {"status", "refs", "rationale"} or item["status"] != "VERIFIED" or not isinstance(item["refs"], list) or not item["refs"] or not isinstance(item["rationale"], str) or not item["rationale"].strip():
                _fail("RFC_TECHNICAL_DECISION_INVALID")
    if seen != set(ASSETS):
        _fail("RFC_TECHNICAL_RECORD_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))
