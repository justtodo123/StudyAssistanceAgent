from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.m11_rfc_iana_evidence_review import (
    PARENT_SCOPE_DIGEST,
    RfcIanaEvidenceReviewError,
    exact_six_batch_digest,
    validate_evidence_review_application,
    validate_rfc_iana_evidence_review_bundle,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "data/manifests"


def load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))


def bundle_args() -> dict:
    digest = load("m11-p0-digest-evidence-v1.json")
    return {
        "application": load("m11-p0-rfc-iana-evidence-review-application-v1.json"),
        "authority": load("m11-p0-rfc-iana-evidence-review-authority-v1.json"),
        "result": load("m11-p0-rfc-iana-evidence-review-result-v1.json"),
        "digest_assets": digest["assets"],
        "digest_robots": digest["robots"],
        "receipts": load("m11-p0-acquisition-26-receipts-v1.json")["receipts"],
        "closure_matrix": load("m11-p0-evidence-closure-26-v1.json"),
        "acquisition_review_wrapper": load("m11-p0-human-review-acq-defer-26-v1.json"),
        "closure_review_wrapper": load("m11-p0-human-review-closure-defer-26-v1.json"),
        "official_observation": load("m11-p0-official-source-observations-26-v1.json"),
        "official_authority": load("m11-p0-human-review-26-authority-v1.json"),
        "official_review_wrapper": load("m11-p0-human-review-official-observation-defer-26-v1.json"),
        "successor_wrapper": load("m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json"),
    }


def test_exact_six_bundle_is_valid_and_non_closing():
    validated = validate_rfc_iana_evidence_review_bundle(**bundle_args())
    assert validated["asset_count"] == 6
    assert validated["result"] == "REVIEW_REQUIRED"
    assert validated["closure_effect"] == "NONE"
    assert all(
        item["evidence"][category]["status"] == "PENDING"
        for item in validated["records"]
        for category in item["evidence"]
    )


def test_batch_digest_is_order_independent_and_scope_bound():
    application = load("m11-p0-rfc-iana-evidence-review-application-v1.json")
    records = application["batch_records"]
    assert exact_six_batch_digest(records) == application["batch_digest"]
    assert exact_six_batch_digest(list(reversed(records))) == application["batch_digest"]
    changed = copy.deepcopy(records)
    changed[0]["revision"] = "f" * 64
    assert exact_six_batch_digest(changed) != application["batch_digest"]


def test_broad_historical_authority_is_rejected():
    args = bundle_args()
    args["authority"] = load("m11-p0-human-review-26-authority-v1.json")
    with pytest.raises(RfcIanaEvidenceReviewError, match="RFC_IANA_AUTHORITY_NOT_EXACT_SIX"):
        validate_rfc_iana_evidence_review_bundle(**args)


def test_application_validation_returns_deep_copy_and_rejects_host_path():
    application = load("m11-p0-rfc-iana-evidence-review-application-v1.json")
    detached = validate_evidence_review_application(application)
    detached["batch_records"][0]["asset_id"] = "changed"
    assert application["batch_records"][0]["asset_id"] != "changed"
    application["batch_records"][0]["asset_id"] = r"C:\secret"
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_evidence_review_application(application)
    assert application["parent_scope_digest"] == PARENT_SCOPE_DIGEST


def test_application_rejects_malformed_naive_and_embedded_host_paths():
    application = load("m11-p0-rfc-iana-evidence-review-application-v1.json")
    for timestamp in ("not-a-timestamp", "2026-09-27T00:00:00"):
        mutated = copy.deepcopy(application)
        mutated["submitted_at"] = timestamp
        with pytest.raises(RfcIanaEvidenceReviewError):
            validate_evidence_review_application(mutated)

    for host_path in (
        r"file=C:\Users\owner\secret.txt",
        r"\\server\share\secret.txt",
        "/home/owner/secret.txt",
    ):
        mutated = copy.deepcopy(application)
        mutated["batch_records"][0]["asset_id"] = host_path
        with pytest.raises(RfcIanaEvidenceReviewError):
            validate_evidence_review_application(mutated)


def test_authority_lifetime_is_bound_to_application_and_review_times():
    args = bundle_args()
    before_issue = copy.deepcopy(args)
    before_issue["application"]["submitted_at"] = "2026-09-26T23:59:59Z"
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**before_issue)

    after_expiry = copy.deepcopy(args)
    after_expiry["successor_wrapper"]["signed_at"] = "2026-10-11T00:00:00Z"
    for record in after_expiry["successor_wrapper"]["records"]:
        record["signed_at"] = "2026-10-11T00:00:00Z"
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**after_expiry)


def test_duplicate_successor_target_is_rejected_before_indexing():
    args = bundle_args()
    duplicate = copy.deepcopy(args["successor_wrapper"]["records"][0])
    duplicate["review_id"] = "m11-hr-20260927-evidence-review-duplicate-csv"
    args["successor_wrapper"]["records"].append(duplicate)
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**args)


def test_successor_authority_record_timestamp_and_txt_assertion_are_bound():
    args = bundle_args()
    args["successor_wrapper"]["authority_record"] = "data/manifests/unrelated-authority.json"
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**args)

    args = bundle_args()
    args["successor_wrapper"]["records"][0]["signed_at"] = "2026-09-27T00:00:01Z"
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**args)

    args = bundle_args()
    txt = next(
        item
        for item in args["successor_wrapper"]["records"]
        if item["asset_id"] == "service-names-port-numbers-txt"
    )
    txt["comment"] = "TXT is no longer fail-closed; malformed input is accepted."
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**args)


def test_malformed_predecessor_and_dependency_errors_are_normalized():
    args = bundle_args()
    args["closure_review_wrapper"] = []
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**args)

    args = bundle_args()
    args["receipts"][0]["status"] = "INVALID"
    with pytest.raises(RfcIanaEvidenceReviewError) as exc_info:
        validate_rfc_iana_evidence_review_bundle(**args)
    assert exc_info.value.code == "RFC_IANA_DEPENDENCY_INVALID"


def test_result_and_successor_mutations_fail_closed():
    args = bundle_args()

    result_args = copy.deepcopy(args)
    result_args["result"]["records"][0]["evidence"]["license"]["status"] = "VERIFIED"
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**result_args)

    successor_args = copy.deepcopy(args)
    successor_args["successor_wrapper"]["records"][0]["decision"] = "ACCEPT_FOR_PROMOTION_REVIEW"
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**successor_args)


def test_identity_scope_and_escalation_mutations_fail_closed():
    args = bundle_args()

    identity_args = copy.deepcopy(args)
    identity_args["result"]["records"][0]["receipt_digest"] = "f" * 64
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**identity_args)

    scope_args = copy.deepcopy(args)
    scope_args["result"]["parent_scope_digest"] = "f" * 64
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**scope_args)

    escalation_args = copy.deepcopy(args)
    escalation_args["successor_wrapper"]["publication_authorized"] = True
    with pytest.raises(RfcIanaEvidenceReviewError):
        validate_rfc_iana_evidence_review_bundle(**escalation_args)


def test_exact_six_chain_excludes_mit_and_opendsa_and_keeps_gate0_blocked():
    args = bundle_args()
    application = args["application"]
    result = args["result"]
    successor = args["successor_wrapper"]

    assert application["source_ids"] == ["iana-registries", "rfc-editor-index"]
    assert result["source_ids"] == application["source_ids"]
    assert {record["source_id"] for record in successor["records"]} == set(application["source_ids"])
    assert all("mit" not in record["asset_id"].lower() for record in successor["records"])
    assert all("opendsa" not in record["asset_id"].lower() for record in successor["records"])

    validated = validate_rfc_iana_evidence_review_bundle(**args)
    validated["records"][0]["evidence"]["license"]["status"] = "VERIFIED"
    assert args["result"]["records"][0]["evidence"]["license"]["status"] == "PENDING"
