from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, NoReturn

from app.m11_execution_authority import ExecutionAuthorityError, validate_execution_authority
from app.m11_review import ReviewError, gate0_status, project_current_review_heads, review_digest, validate_review_history

SOURCE_ID = "rfc-editor-index"
ASSETS = ("rfc1034", "rfc9110", "rfc9293")
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
AUTHORITY_ID = "m11-rfc-exact-three-accept-3-20260928"
RESULT_ID = "m11-p0-rfc-exact-three-accept-result-20260928"
LEGAL_RESULT_ID = "m11-p0-rfc-legal-policy-review-result-20260928"
SLICE_ID = "rfc-exact-three-accept-3-20260928"
EXPECTED = {
    "rfc1034": ("2186f345e64dbac70a29a5c56026947e", "b4b9e68fe2343e503bbb280a7ffb626f", "d6b10a71441df879cc2817d23f2dad120c8a5f87e74eba1e4ed4b743a76a891a", "6a7a22c4d5e4ac738715e5d004664d3c5c0ab3afeecf007973297b9243df9fe5"),
    "rfc9110": ("c4a82e00b607cd3ce2b44888f0f1583d", "d07e193fcb66290468aea31c9df37cd3", "21c1cdce6ab0e5509b04d84a28000836c7a087cf786efe6f04877ebfff47232a", "6d0e2f64f1c9622eef27d497a2d042d28964a642c5aa28b5ed7541d4d97e7e2d"),
    "rfc9293": ("e8131883983093c7b086358b4cfa5fb6", "71f8faad1d3562092b15435a75ab3db7", "6d9ac8be4b0286f8c3d337addf442b2eb6a9b14e1366594ea7fbc273f93dc2d9", "355b80fc571e74fab0757a408a5edb989aa86fd3cde87cfeb7391a8a72c4f819"),
}


class RfcExactThreeSuccessorError(ValueError):
    """The RFC exact-three ACCEPT successor is invalid."""


def _fail(code: str) -> NoReturn:
    raise RfcExactThreeSuccessorError(code)


def _timestamp(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RfcExactThreeSuccessorError("RFC_SUCCESSOR_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        _fail("RFC_SUCCESSOR_TIMESTAMP_INVALID")
    return parsed


def validate_rfc_exact_three_successor(*, authority: Mapping[str, Any], result: Mapping[str, Any], legal_result: Mapping[str, Any], successor_wrapper: Mapping[str, Any], official_reviews: Sequence[Mapping[str, Any]], exact_six_reviews: Sequence[Mapping[str, Any]], mit_reviews: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    try:
        auth = validate_execution_authority(authority, operation="human_review", expected_scope_digest=SCOPE_DIGEST, allowed_source_ids={SOURCE_ID: ASSETS}, now=_timestamp("2026-09-28T16:01:00Z"))
        if auth.authority_id != AUTHORITY_ID:
            _fail("RFC_SUCCESSOR_AUTHORITY_INVALID")
        if legal_result.get("result_id") != LEGAL_RESULT_ID or legal_result.get("closure_effect") != "COMPLETE" or legal_result.get("pending_cell_count") != 0:
            _fail("RFC_SUCCESSOR_EVIDENCE_INCOMPLETE")
        if result.get("result_id") != RESULT_ID or result.get("authority_id") != AUTHORITY_ID or result.get("legal_policy_result_id") != LEGAL_RESULT_ID or result.get("successor_slice_written") is not True or result.get("decision") != "ACCEPT_FOR_PROMOTION_REVIEW":
            _fail("RFC_SUCCESSOR_RESULT_INVALID")
        if any(result.get(field) is not False for field in ("formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")):
            _fail("RFC_SUCCESSOR_RESULT_ESCALATION")
        if successor_wrapper.get("schema") != "sa.m11.p0.human-review-slice.v1" or successor_wrapper.get("slice_id") != SLICE_ID or successor_wrapper.get("authority_id") != AUTHORITY_ID or successor_wrapper.get("source_ids") != [SOURCE_ID] or successor_wrapper.get("asset_count") != 3 or successor_wrapper.get("decision") != "ACCEPT_FOR_PROMOTION_REVIEW":
            _fail("RFC_SUCCESSOR_WRAPPER_INVALID")
        if any(successor_wrapper.get(field) is not False for field in ("formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")):
            _fail("RFC_SUCCESSOR_WRAPPER_ESCALATION")
        records = successor_wrapper.get("records")
        if not isinstance(records, list):
            _fail("RFC_SUCCESSOR_RECORDS_INVALID")
        validated = validate_review_history(records)
        if len(validated) != 3 or {(item.source_id, item.asset_id) for item in validated} != {(SOURCE_ID, asset) for asset in ASSETS}:
            _fail("RFC_SUCCESSOR_SCOPE_INVALID")
        expected_refs = {"m11-p0-digest-evidence-v1", "m11-p0-acquisition-26-receipts-v1", "m11-p0-rfc-candidate-materialization-20260928", "m11-p0-rfc-schema-review-result-20260928", "m11-p0-rfc-technical-evidence-review-result-20260928", "m11-p0-rfc-content-quality-review-result-20260928", "m11-p0-rfc-legal-policy-census-20260928", LEGAL_RESULT_ID}
        for item in validated:
            document_id, chunk_id, candidate_digest, receipt_digest = EXPECTED[item.asset_id]
            if item.decision != "ACCEPT_FOR_PROMOTION_REVIEW" or item.document_id != document_id or item.chunk_ids != (chunk_id,) or item.candidate_digest != candidate_digest or item.receipt_digest != receipt_digest or item.supersedes != f"m11-hr-20260927-evidence-review-{item.asset_id}" or set(item.evidence_refs) != expected_refs:
                _fail("RFC_SUCCESSOR_IDENTITY_INVALID")
            if item.sampling_plan != {"sample_size": 3, "stratification": "rfc-editor-index-exact-three", "batch": SLICE_ID, "slice": "rfc-exact-three-accept-3"}:
                _fail("RFC_SUCCESSOR_SAMPLING_INVALID")
            payload = item.as_dict(); payload.pop("attestation_digest")
            if item.attestation_digest != review_digest(payload):
                _fail("RFC_SUCCESSOR_ATTESTATION_INVALID")
        validate_review_history([*exact_six_reviews, *records])
        current = project_current_review_heads([*official_reviews, *exact_six_reviews, *mit_reviews, *records])
        if len(current) != 26:
            _fail("RFC_SUCCESSOR_CURRENT_HEAD_COUNT_INVALID")
        current_by_key = {(item.source_id, item.asset_id): item for item in current}
        if any(current_by_key[(SOURCE_ID, asset)].decision != "ACCEPT_FOR_PROMOTION_REVIEW" for asset in ASSETS):
            _fail("RFC_SUCCESSOR_CURRENT_HEAD_INVALID")
        if any(item.decision != "DEFER" for key, item in current_by_key.items() if key[0] != SOURCE_ID):
            _fail("RFC_SUCCESSOR_OTHER_HEADS_CHANGED")
        status = gate0_status(required_assets=[(SOURCE_ID, asset) for asset in ASSETS], reviews=records, acquisition_receipts=(), authority_present=False, scope_digest=SCOPE_DIGEST)
        if status["reviewed_asset_count"] != 3 or status["status"] != "BLOCKED" or status["candidate_promotion_authorized"] or status["publication_authorized"]:
            _fail("RFC_SUCCESSOR_GATE0_PROJECTION_INVALID")
        return copy.deepcopy(dict(result))
    except RfcExactThreeSuccessorError:
        raise
    except (ExecutionAuthorityError, ReviewError, KeyError, TypeError) as exc:
        raise RfcExactThreeSuccessorError("RFC_SUCCESSOR_DEPENDENCY_INVALID") from exc
