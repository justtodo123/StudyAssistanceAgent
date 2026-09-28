from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, NoReturn

from app.m11_execution_authority import ExecutionAuthorityError, validate_execution_authority

SOURCE_ID = "rfc-editor-index"
ASSETS = ("rfc1034", "rfc9110", "rfc9293")
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
AUTHORITY_ID = "m11-rfc-legal-policy-review-3-20260928"
CENSUS_ID = "m11-p0-rfc-legal-policy-census-20260928"
CONTENT_QUALITY_RESULT_ID = "m11-p0-rfc-content-quality-review-result-20260928"
CATEGORIES = ("license", "robots_terms", "notice_ipr")


class RfcLegalPolicyReviewError(ValueError):
    """The owner-authorized RFC legal-policy result is invalid."""


def _fail(code: str) -> NoReturn:
    raise RfcLegalPolicyReviewError(code)


def _timestamp(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RfcLegalPolicyReviewError("RFC_LEGAL_REVIEW_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        _fail("RFC_LEGAL_REVIEW_TIMESTAMP_INVALID")
    return parsed


def validate_rfc_legal_policy_authority(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        authority = validate_execution_authority(payload, operation="human_review", expected_scope_digest=SCOPE_DIGEST, allowed_source_ids={SOURCE_ID: ASSETS}, now=_timestamp("2026-09-28T15:01:00Z"))
    except ExecutionAuthorityError as exc:
        raise RfcLegalPolicyReviewError(exc.code) from exc
    if authority.authority_id != AUTHORITY_ID or authority.source_ids != (SOURCE_ID,) or tuple(sorted(authority.assets_for(SOURCE_ID))) != tuple(sorted(ASSETS)):
        _fail("RFC_LEGAL_REVIEW_AUTHORITY_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))


def validate_rfc_legal_policy_result(payload: Mapping[str, Any], *, authority: Mapping[str, Any], census: Mapping[str, Any], content_quality_result: Mapping[str, Any]) -> dict[str, Any]:
    validate_rfc_legal_policy_authority(authority)
    required = {"schema", "result_id", "authority_id", "scope_digest", "census_reference", "content_quality_reference", "signed_by", "signed_at", "decision_reference", "asset_count", "verified_cell_count", "not_applicable_cell_count", "pending_cell_count", "failed_cell_count", "closure_effect", "result", "records", "successor_slice_written", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included"}
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("RFC_LEGAL_REVIEW_RESULT_FIELDS_INVALID")
    if payload["schema"] != "sa.m11.p0.rfc-legal-policy-review-result.v1" or payload["result_id"] != "m11-p0-rfc-legal-policy-review-result-20260928" or payload["authority_id"] != AUTHORITY_ID or payload["scope_digest"] != SCOPE_DIGEST:
        _fail("RFC_LEGAL_REVIEW_RESULT_IDENTITY_INVALID")
    if payload["census_reference"] != CENSUS_ID or census.get("census_id") != CENSUS_ID or payload["content_quality_reference"] != CONTENT_QUALITY_RESULT_ID or content_quality_result.get("result_id") != CONTENT_QUALITY_RESULT_ID:
        _fail("RFC_LEGAL_REVIEW_RESULT_LINK_INVALID")
    if _timestamp(payload["signed_at"]) < _timestamp(authority["issued_at"]):
        _fail("RFC_LEGAL_REVIEW_TIMESTAMP_ORDER_INVALID")
    if payload["asset_count"] != 3 or payload["verified_cell_count"] != 21 or payload["not_applicable_cell_count"] != 3 or payload["pending_cell_count"] != 0 or payload["failed_cell_count"] != 0 or payload["closure_effect"] != "COMPLETE" or payload["result"] != "EVIDENCE_COMPLETE_REVIEW_PENDING":
        _fail("RFC_LEGAL_REVIEW_COUNTS_INVALID")
    if payload["successor_slice_written"] is not False:
        _fail("RFC_LEGAL_REVIEW_SUCCESSOR_POLICY_INVALID")
    if any(payload[field] is not False for field in ("formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")):
        _fail("RFC_LEGAL_REVIEW_ESCALATION_FORBIDDEN")
    records = payload["records"]
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or len(records) != 3:
        _fail("RFC_LEGAL_REVIEW_RECORD_SCOPE_INVALID")
    seen = set()
    for record in records:
        if not isinstance(record, Mapping) or record.get("asset_id") not in ASSETS or record["asset_id"] in seen or set(record) != {"asset_id", *CATEGORIES}:
            _fail("RFC_LEGAL_REVIEW_RECORD_SCOPE_INVALID")
        seen.add(record["asset_id"])
        for category in CATEGORIES:
            decision = record[category]
            if not isinstance(decision, Mapping) or set(decision) != {"status", "refs", "rationale"} or decision["status"] != "VERIFIED" or not isinstance(decision["refs"], list) or not decision["refs"] or not isinstance(decision["rationale"], str) or not decision["rationale"].strip():
                _fail("RFC_LEGAL_REVIEW_DECISION_INVALID")
    if seen != set(ASSETS):
        _fail("RFC_LEGAL_REVIEW_RECORD_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))
