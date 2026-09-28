from __future__ import annotations

import copy

import pytest

from app.m11_acquisition import FrozenAsset
from app.m11_gate0 import EVIDENCE_CATEGORIES, Gate0Error, run_gate0

pytestmark = pytest.mark.m11

SCOPE = "a" * 64
ASSET = ("rfc-editor-index", "rfc9110")


def _review():
    return {
        "schema": "sa.m11.human-review.v1", "review_id": "review-1", "scope_digest": SCOPE,
        "source_id": ASSET[0], "asset_id": ASSET[1], "document_id": "doc-1",
        "chunk_ids": ["chunk-1"], "candidate_digest": "b" * 64,
        "receipt_digest": "c" * 64, "reviewer_id": "owner", "reviewer_role": "domain-reviewer",
        "sampling_plan": {"sample_size": 1, "stratification": "source"},
        "signed_at": "2026-09-25T12:00:00Z", "attestation_digest": "d" * 64,
        "decision": "ACCEPT_FOR_PROMOTION_REVIEW", "evidence_refs": ["receipt-1"],
        "supersedes": None, "comment": "",
    }


def _authority():
    return {
        "schema": "sa.m11.execution-authority.v1", "operation": "gate0",
        "authority_id": "gate0-authority-1", "issued_by": "owner",
        "issued_at": "2026-09-25T00:00:00Z", "expires_at": "2026-09-26T00:00:00Z",
        "scope_digest": SCOPE, "source_ids": [ASSET[0]],
        "asset_ids": {ASSET[0]: [ASSET[1]]}, "metadata_only": False,
        "publication_authorized": False, "status": "AUTHORIZED",
    }


def _acquisition_authority():
    authority = _authority()
    authority["operation"] = "acquisition"
    authority["authority_id"] = "acquisition-authority-1"
    return authority


def _receipt():
    return {
        "schema": "sa.m11.acquisition-receipt.v1", "status": "ACQUIRED",
        "source_id": ASSET[0], "asset_id": ASSET[1],
        "canonical_url": "https://www.rfc-editor.org/rfc/rfc9110.txt",
        "revision": "rfc9110", "captured_at": "2026-09-25T12:00:00Z",
        "bytes": 1, "sha256": "e" * 64, "source_blob_sha1": None,
        "authority_id": "gate0-authority-1", "scope_digest": SCOPE,
        "refusal_code": None,
    }


def _evidence():
    return {ASSET: {category: "VERIFIED" for category in EVIDENCE_CATEGORIES}}


def _run(**overrides):
    values = {
        "required_assets": [ASSET], "evidence": _evidence(), "reviews": [_review()],
        "acquisition_receipts": [_receipt()], "candidate_validated": {ASSET: True},
        "authority": _authority(), "scope_digest": SCOPE,
        "lifecycle_counts": {"candidate": 1, "approved": 0, "published": 0},
        "owner_id": "owner", "signed_at": "2026-09-25T12:00:00Z",
    }
    values.update(overrides)
    return run_gate0(**values)


def test_formal_gate0_passes_only_with_independent_categories():
    result = _run()
    assert result["status"] == "PASS"
    assert result["candidate_promotion_authorized"] is False
    assert result["publication_authorized"] is False
    assert result["missing_asset_count"] == 0


def test_gate0_accepts_explicit_acquisition_authority_and_binds_provenance():
    receipt = _receipt()
    receipt["authority_id"] = "acquisition-authority-1"
    result = _run(
        acquisition_receipts=[receipt],
        acquisition_authority=_acquisition_authority(),
    )
    assert result["status"] == "PASS"
    assert result["authority_id"] == "gate0-authority-1"
    assert result["acquisition_authority_id"] == "acquisition-authority-1"


def test_gate0_rejects_explicit_acquisition_authority_with_wrong_operation():
    receipt = _receipt()
    receipt["authority_id"] = "acquisition-authority-1"
    authority = _acquisition_authority()
    authority["operation"] = "gate0"
    with pytest.raises(Gate0Error, match="GATE0_ACQUISITION_AUTHORITY_INVALID"):
        _run(acquisition_receipts=[receipt], acquisition_authority=authority)


def test_gate0_rejects_gate0_authority_before_acquisition_authority():
    receipt = _receipt()
    receipt["authority_id"] = "acquisition-authority-1"
    authority = _authority()
    authority["operation"] = "acquisition"
    with pytest.raises(Gate0Error, match="GATE0_AUTHORITY_INVALID"):
        _run(
            authority=authority,
            acquisition_receipts=[receipt],
            acquisition_authority=_acquisition_authority(),
        )


def test_gate0_rejects_receipt_outside_explicit_acquisition_authority_window():
    receipt = _receipt()
    receipt["authority_id"] = "acquisition-authority-1"
    receipt["captured_at"] = "2026-09-24T23:59:59Z"
    with pytest.raises(Gate0Error, match="GATE0_RECEIPT_AUTHORITY_WINDOW_INVALID"):
        _run(
            acquisition_receipts=[receipt],
            acquisition_authority=_acquisition_authority(),
        )


@pytest.mark.parametrize(
    ("captured_at", "error_code"),
    (
        ("not-a-timestamp", "GATE0_RECEIPT_CAPTURED_AT_INVALID"),
        ("2026-09-25T12:00:00", "GATE0_RECEIPT_CAPTURED_AT_INVALID"),
        ("2026-09-26T00:00:00Z", "GATE0_RECEIPT_AUTHORITY_WINDOW_INVALID"),
    ),
)
def test_gate0_rejects_malformed_or_expired_capture_timestamp(captured_at, error_code):
    receipt = _receipt()
    receipt["authority_id"] = "acquisition-authority-1"
    receipt["captured_at"] = captured_at
    with pytest.raises(Gate0Error, match=error_code):
        _run(
            acquisition_receipts=[receipt],
            acquisition_authority=_acquisition_authority(),
        )


def test_gate0_input_digest_binds_explicit_acquisition_authority():
    receipt = _receipt()
    receipt["authority_id"] = "acquisition-authority-1"
    authority = _acquisition_authority()
    first = _run(acquisition_receipts=[receipt], acquisition_authority=authority)
    changed = copy.deepcopy(authority)
    changed["issued_by"] = "other-owner"
    second = _run(acquisition_receipts=[receipt], acquisition_authority=changed)
    assert first["input_digest"] != second["input_digest"]


@pytest.mark.parametrize("field", ["reviews", "acquisition_receipts", "candidate_validated"])
def test_gate0_blocks_when_one_independent_input_is_missing(field):
    values = {"reviews": [], "acquisition_receipts": [], "candidate_validated": {}}
    result = _run(**{field: values[field]})
    assert result["status"] == "BLOCKED"
    assert result["missing_asset_count"] == 1


def test_gate0_fails_on_explicit_evidence_failure():
    evidence = _evidence()
    evidence[ASSET]["license"] = "FAILED"
    result = _run(evidence=evidence)
    assert result["status"] == "FAIL"
    assert result["failed_asset_keys"]


def test_gate0_blocks_pending_evidence_and_hides_asset_identifier():
    evidence = _evidence()
    evidence[ASSET]["robots_terms"] = "PENDING"
    result = _run(evidence=evidence)
    assert result["status"] == "BLOCKED"
    assert ASSET[1] not in str(result)


def test_gate0_rejects_privacy_fields():
    evidence = _evidence()
    evidence[ASSET]["content"] = "secret"
    with pytest.raises(Gate0Error, match="GATE0_PRIVACY_FIELD"):
        _run(evidence=evidence)


def test_gate0_does_not_mutate_inputs():
    evidence = _evidence()
    before = copy.deepcopy(evidence)
    _run(evidence=evidence)
    assert evidence == before


def test_gate0_rejects_evidence_for_asset_outside_required_scope():
    evidence = _evidence()
    evidence[("rfc-editor-index", "rfc9999")] = {
        category: "VERIFIED" for category in EVIDENCE_CATEGORIES
    }
    with pytest.raises(Gate0Error, match="GATE0_EVIDENCE_OUT_OF_SCOPE"):
        _run(evidence=evidence)


def test_gate0_rejects_candidate_validation_for_asset_outside_required_scope():
    candidate_validated = {ASSET: True, ("rfc-editor-index", "rfc9999"): True}
    with pytest.raises(Gate0Error, match="GATE0_CANDIDATE_OUT_OF_SCOPE"):
        _run(candidate_validated=candidate_validated)


def test_gate0_rejects_receipt_authority_mismatch_instead_of_ignoring_it():
    receipt = _receipt()
    receipt["authority_id"] = "other-authority"
    with pytest.raises(Gate0Error, match="GATE0_RECEIPT_AUTHORITY_MISMATCH"):
        _run(acquisition_receipts=[receipt])


def test_gate0_rejects_duplicate_receipt_identity():
    with pytest.raises(Gate0Error, match="GATE0_RECEIPT_DUPLICATE"):
        _run(acquisition_receipts=[_receipt(), _receipt()])




def test_gate0_uses_strict_frozen_asset_receipt_linkage():
    frozen_assets = {
        ASSET: FrozenAsset(
            ASSET[0],
            ASSET[1],
            "https://www.rfc-editor.org/rfc/rfc9110.txt",
            "rfc9110",
            "e" * 64,
            None,
        )
    }
    _run(frozen_assets=frozen_assets)
    drifted = dict(frozen_assets)
    drifted[ASSET] = FrozenAsset(
        ASSET[0], ASSET[1], frozen_assets[ASSET].canonical_url,
        "different-revision", "e" * 64, None,
    )
    with pytest.raises(Gate0Error, match="GATE0_RECEIPTS_INVALID"):
        _run(frozen_assets=drifted)

def test_gate0_input_digest_changes_when_evidence_changes():
    first = _run()
    evidence = _evidence()
    evidence[ASSET]["robots_terms"] = "PENDING"
    second = _run(evidence=evidence)
    assert first["input_digest"] != second["input_digest"]


def test_gate0_input_digest_changes_when_review_changes():
    first = _run()
    review = _review()
    review["comment"] = "updated review note"
    second = _run(reviews=[review])
    assert first["input_digest"] != second["input_digest"]
