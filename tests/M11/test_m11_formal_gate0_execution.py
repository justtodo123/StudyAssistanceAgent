from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.m11_execution_authority import ExecutionAuthorityError, validate_execution_authority
from app.m11_gate0_result import FormalGate0ResultError, validate_formal_gate0_result
from tools import run_m11_formal_gate0 as formal_gate0

pytestmark = pytest.mark.m11

MANIFESTS = Path(__file__).resolve().parents[2] / "data/manifests"


def _result() -> dict:
    return json.loads((MANIFESTS / formal_gate0.RESULT_NAME).read_text(encoding="utf-8"))


def test_repository_formal_gate0_is_reproducibly_blocked():
    runner_result = formal_gate0.evaluate()
    result = validate_formal_gate0_result(_result(), expected_runner_result=runner_result, authority=formal_gate0._load("m11-p0-formal-gate0-26-authority-v1.json"))

    assert result["status"] == "BLOCKED"
    assert result["required_asset_count"] == 26
    assert result["receipt_asset_count"] == 26
    assert result["reviewed_asset_count"] == 3
    assert result["candidate_validated_count"] == 21
    assert result["missing_asset_count"] == 23
    assert result["authority_id"] == "m11-formal-gate0-26-20260928"
    assert result["acquisition_authority_id"] == "m11-acquisition-26-20260926"


def test_repository_current_heads_preserve_rfc_accept_and_other_deferral():
    heads = formal_gate0._reviews()
    decisions = {item["decision"] for item in heads}

    assert len(heads) == 26
    assert sum(item["decision"] == "ACCEPT_FOR_PROMOTION_REVIEW" for item in heads) == 3
    assert decisions == {"ACCEPT_FOR_PROMOTION_REVIEW", "DEFER"}


def test_repository_candidates_remain_distinct_from_approved_or_3k_counts():
    result = formal_gate0.evaluate()

    assert result["candidate_validated_count"] == 21
    assert result["lifecycle_counts_before"] == {
        "approved_chunks": 0,
        "approved_documents": 0,
        "candidate_chunks": 96,
        "candidate_documents": 21,
    }


def test_result_rejects_status_or_escalation_mutation():
    runner_result = formal_gate0.evaluate()
    mutated = _result()
    mutated["status"] = "PASS"
    with pytest.raises(FormalGate0ResultError, match="FORMAL_GATE0_RESULT_BINDING_INVALID"):
        validate_formal_gate0_result(mutated, expected_runner_result=runner_result, authority=formal_gate0._load("m11-p0-formal-gate0-26-authority-v1.json"))

    mutated = _result()
    mutated["publication_authorized"] = True
    with pytest.raises(FormalGate0ResultError, match="FORMAL_GATE0_RESULT_BINDING_INVALID"):
        validate_formal_gate0_result(mutated, expected_runner_result=runner_result, authority=formal_gate0._load("m11-p0-formal-gate0-26-authority-v1.json"))


@pytest.mark.parametrize("signed_at", ("2026-09-28T16:59:59Z", "2026-09-29T17:00:00Z"))
def test_result_rejects_gate0_authority_window_boundaries(signed_at):
    runner_result = formal_gate0.evaluate()
    mutated = _result()
    mutated["signed_at"] = signed_at
    with pytest.raises(FormalGate0ResultError, match="FORMAL_GATE0_RESULT_AUTHORITY_WINDOW_INVALID"):
        validate_formal_gate0_result(mutated, expected_runner_result=runner_result, authority=formal_gate0._load("m11-p0-formal-gate0-26-authority-v1.json"))


def test_result_accepts_gate0_issued_at_boundary():
    runner_result = formal_gate0.evaluate()
    mutated = _result()
    authority = formal_gate0._load("m11-p0-formal-gate0-26-authority-v1.json")
    mutated["signed_at"] = authority["issued_at"]
    assert validate_formal_gate0_result(mutated, expected_runner_result=runner_result, authority=authority)["signed_at"] == authority["issued_at"]


def test_result_rejects_body_or_host_path_leakage():
    runner_result = formal_gate0.evaluate()
    mutated = _result()
    mutated["bodies_included"] = True
    with pytest.raises(FormalGate0ResultError, match="FORMAL_GATE0_RESULT_ESCALATION_FORBIDDEN"):
        validate_formal_gate0_result(mutated, expected_runner_result=runner_result, authority=formal_gate0._load("m11-p0-formal-gate0-26-authority-v1.json"))

    mutated = _result()
    mutated["host_path"] = "C:/secret"
    with pytest.raises(FormalGate0ResultError, match="FORMAL_GATE0_RESULT_FIELDS_INVALID"):
        validate_formal_gate0_result(mutated, expected_runner_result=runner_result, authority=formal_gate0._load("m11-p0-formal-gate0-26-authority-v1.json"))


def test_gate0_authority_rejects_wrong_operation_or_scope():
    authority = json.loads(
        (MANIFESTS / "m11-p0-formal-gate0-26-authority-v1.json").read_text(encoding="utf-8")
    )
    changed = copy.deepcopy(authority)
    changed["operation"] = "acquisition"
    with pytest.raises(ExecutionAuthorityError):
        validate_execution_authority(
            changed, operation="gate0", expected_scope_digest=formal_gate0.SCOPE_DIGEST
        )

    changed = copy.deepcopy(authority)
    changed["scope_digest"] = "0" * 64
    with pytest.raises(ExecutionAuthorityError):
        validate_execution_authority(
            changed, operation="gate0", expected_scope_digest=formal_gate0.SCOPE_DIGEST
        )


def test_evaluation_rejects_invalid_rfc_evidence_authority(monkeypatch):
    original = formal_gate0._load

    def tampered(name: str) -> dict:
        payload = original(name)
        if name == "m11-p0-rfc-schema-review-authority-v1.json":
            payload["scope_digest"] = "0" * 64
        return payload

    monkeypatch.setattr(formal_gate0, "_load", tampered)
    with pytest.raises(Exception, match="AUTHORITY_SCOPE_MISMATCH"):
        formal_gate0.evaluate()


def test_evaluation_rejects_invalid_rfc_evidence_result(monkeypatch):
    original = formal_gate0._load

    def tampered(name: str) -> dict:
        payload = original(name)
        if name == "m11-p0-rfc-legal-policy-review-result-v1.json":
            payload["authority_id"] = "forged-authority"
        return payload

    monkeypatch.setattr(formal_gate0, "_load", tampered)
    with pytest.raises(Exception, match="RFC_LEGAL_REVIEW_RESULT_IDENTITY_INVALID"):
        formal_gate0.evaluate()


def test_evaluation_rejects_invalid_rfc_dependency_references(monkeypatch):
    original = formal_gate0._load

    def tampered(name: str) -> dict:
        payload = original(name)
        if name == "m11-p0-rfc-technical-evidence-review-result-v1.json":
            payload["schema_decision_reference"] = "forged-schema-result"
        elif name == "m11-p0-rfc-content-quality-review-result-v1.json":
            payload["technical_decision_reference"] = "forged-technical-result"
        return payload

    monkeypatch.setattr(formal_gate0, "_load", tampered)
    with pytest.raises(Exception, match="RFC_TECHNICAL_SCHEMA_RESULT_LINK_INVALID"):
        formal_gate0.evaluate()

    def quality_tampered(name: str) -> dict:
        payload = original(name)
        if name == "m11-p0-rfc-content-quality-review-result-v1.json":
            payload["technical_decision_reference"] = "forged-technical-result"
        return payload

    monkeypatch.setattr(formal_gate0, "_load", quality_tampered)
    with pytest.raises(Exception, match="RFC_QUALITY_REVIEW_RESULT_LINK_INVALID"):
        formal_gate0.evaluate()


def test_evaluation_rejects_forged_rfc_provenance(monkeypatch):
    original = formal_gate0._load

    def forged_reference(name: str) -> dict:
        payload = original(name)
        if name == "m11-p0-rfc-technical-evidence-review-result-v1.json":
            payload["records"][0]["revision"]["refs"] = ["forged-reference"]
        return payload

    monkeypatch.setattr(formal_gate0, "_load", forged_reference)
    with pytest.raises(ValueError, match="FORMAL_GATE0_RFC_REFERENCE_INVALID"):
        formal_gate0.evaluate()

    def forged_signer(name: str) -> dict:
        payload = original(name)
        if name == "m11-p0-rfc-legal-policy-review-result-v1.json":
            payload["signed_by"] = "forged-signer"
        return payload

    monkeypatch.setattr(formal_gate0, "_load", forged_signer)
    with pytest.raises(ValueError, match="FORMAL_GATE0_RFC_SIGNER_INVALID"):
        formal_gate0.evaluate()

    def forged_sampling_digest(name: str) -> dict:
        payload = original(name)
        if name == "m11-p0-rfc-content-quality-sampling-result-v1.json":
            payload["assets"][0]["candidate_artifact_sha256"] = "0" * 64
        return payload

    monkeypatch.setattr(formal_gate0, "_load", forged_sampling_digest)
    with pytest.raises(ValueError, match="FORMAL_GATE0_RFC_DIGEST_LINK_INVALID"):
        formal_gate0.evaluate()

    def forged_census_digest(name: str) -> dict:
        payload = original(name)
        if name == "m11-p0-rfc-legal-policy-census-v1.json":
            payload["records"][0]["raw_sha256"] = "0" * 64
        return payload

    monkeypatch.setattr(formal_gate0, "_load", forged_census_digest)
    with pytest.raises(ValueError, match="FORMAL_GATE0_RFC_DIGEST_LINK_INVALID"):
        formal_gate0.evaluate()


def test_evaluation_does_not_mutate_committed_result_or_inputs():
    before = _result()
    formal_gate0.evaluate()
    assert _result() == before
