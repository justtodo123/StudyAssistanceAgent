from __future__ import annotations

import copy
import hashlib

import pytest

from app.m11_review import (
    REVIEW_SCHEMA,
    ReviewError,
    gate0_status,
    review_digest,
    validate_review_history,
    validate_review_record,
)

pytestmark = pytest.mark.m11

SCOPE = "a" * 64


def _review(decision="ACCEPT_FOR_PROMOTION_REVIEW"):
    payload = {
        "schema": REVIEW_SCHEMA, "review_id": "review-1", "scope_digest": SCOPE,
        "source_id": "rfc-editor-index", "asset_id": "rfc9110", "document_id": "doc-1",
        "chunk_ids": ["chunk-1"], "candidate_digest": "b" * 64,
        "receipt_digest": "c" * 64, "reviewer_id": "owner", "reviewer_role": "domain-reviewer",
        "sampling_plan": {"sample_size": 1, "stratification": "source"},
        "signed_at": "2026-09-25T12:00:00Z", "attestation_digest": "d" * 64,
        "decision": decision, "evidence_refs": ["receipt-1"], "supersedes": None, "comment": "",
    }
    return payload


def test_review_record_is_metadata_only_and_validates():
    record = validate_review_record(_review())
    assert record.decision == "ACCEPT_FOR_PROMOTION_REVIEW"
    assert review_digest(record.as_dict()) == review_digest(record.as_dict())


@pytest.mark.parametrize("mutation, code", [
    (lambda p: p.pop("reviewer_id"), "REVIEW_FIELDS_INVALID"),
    (lambda p: p.update(content="secret"), "REVIEW_FIELDS_INVALID"),
    (lambda p: p.update(candidate_digest="x" * 64), "REVIEW_CANDIDATE_DIGEST_INVALID"),
    (lambda p: p.update(decision="APPROVED"), "REVIEW_DECISION_INVALID"),
    (lambda p: p.update(sampling_plan={}), "REVIEW_SAMPLING_PLAN_INVALID"),
    (lambda p: p.update(comment="x" * 501), "REVIEW_COMMENT_INVALID"),
])
def test_review_rejects_mutations(mutation, code):
    payload = copy.deepcopy(_review())
    mutation(payload)
    with pytest.raises(ReviewError) as exc_info:
        validate_review_record(payload)
    assert str(exc_info.value) == code


def test_conflicting_reviews_require_explicit_supersession():
    first = _review()
    second = copy.deepcopy(first)
    second.update(review_id="review-2", decision="REJECT")
    with pytest.raises(ReviewError, match="REVIEW_CONFLICT_UNRESOLVED"):
        validate_review_history([first, second])
    second["supersedes"] = "review-1"
    assert len(validate_review_history([first, second])) == 2


def test_gate0_is_blocked_when_owner_inputs_are_missing():
    result = gate0_status(
        required_assets=[("rfc-editor-index", "rfc9110")], reviews=[],
        acquisition_receipts=[], authority_present=False, scope_digest=SCOPE,
    )
    assert result["status"] == "BLOCKED"
    assert result["candidate_promotion_authorized"] is False
    assert result["publication_authorized"] is False
    assert result["missing_asset_count"] == 1
    assert len(result["missing_asset_keys"][0]) == 16


def test_gate0_does_not_expose_asset_identifiers_in_missing_keys():
    result = gate0_status(
        required_assets=[("rfc-editor-index", "private-name")], reviews=[],
        acquisition_receipts=[], authority_present=False, scope_digest=SCOPE,
    )
    assert "private-name" not in str(result)
