from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_mit_ocw_evidence_review import (
    EXACT_ASSETS,
    PARENT_SCOPE_DIGEST,
    SOURCE_ID,
    MitOcwEvidenceReviewError,
    exact_twenty_batch_digest,
    validate_mit_ocw_evidence_review_application,
    validate_mit_ocw_evidence_review_bundle,
    validate_mit_ocw_evidence_review_result,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "data/manifests"

def load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))


def bundle_args() -> dict:
    digest = load("m11-p0-digest-evidence-v1.json")
    return {
        "application": load("m11-p0-mit-ocw-evidence-review-application-v1.json"),
        "authority": load("m11-p0-mit-ocw-evidence-review-authority-v1.json"),
        "result": load("m11-p0-mit-ocw-evidence-review-result-v1.json"),
        "digest_assets": digest["assets"],
        "digest_robots": digest["robots"],
        "receipts": load("m11-p0-acquisition-26-receipts-v1.json")["receipts"],
        "closure_matrix": load("m11-p0-evidence-closure-26-v1.json"),
        "acquisition_review_wrapper": load("m11-p0-human-review-acq-defer-26-v1.json"),
        "closure_review_wrapper": load("m11-p0-human-review-closure-defer-26-v1.json"),
        "official_observation": load("m11-p0-official-source-observations-26-v1.json"),
        "official_authority": load("m11-p0-human-review-26-authority-v1.json"),
        "official_review_wrapper": load(
            "m11-p0-human-review-official-observation-defer-26-v1.json"
        ),
        "successor_wrapper": load("m11-p0-human-review-mit-ocw-evidence-defer-20-v1.json"),
        "rfc_iana_successor_wrapper": load(
            "m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json"
        ),
    }


def mutate_asset_id(args: dict, asset_id: str) -> None:
    args["application"]["batch_records"][0]["asset_id"] = asset_id
    args["application"]["batch_digest"] = exact_twenty_batch_digest(
        args["application"]["batch_records"]
    )


def test_exact_twenty_bundle_is_valid_and_non_closing():
    args = bundle_args()
    validated = validate_mit_ocw_evidence_review_bundle(**args)

    assert validated["asset_count"] == 20
    assert validated["result"] == "REVIEW_REQUIRED"
    assert validated["closure_effect"] == "NONE"
    assert sum(
        entry["status"] == "PENDING"
        for record in validated["records"]
        for entry in record["evidence"].values()
    ) == 160
    assert {record["determination"] for record in validated["records"]} == {"DEFER"}
    assert {record["third_party_rights"] for record in validated["records"]} == {
        "UNRESOLVED"
    }


def test_batch_digest_is_order_independent_and_identity_bound():
    application = load("m11-p0-mit-ocw-evidence-review-application-v1.json")
    records = application["batch_records"]

    assert exact_twenty_batch_digest(records) == application["batch_digest"]
    assert exact_twenty_batch_digest(list(reversed(records))) == application["batch_digest"]
    for field in ("candidate_digest", "receipt_digest", "revision"):
        changed = copy.deepcopy(records)
        changed[0][field] = "f" * 64
        assert exact_twenty_batch_digest(changed) != application["batch_digest"]


@pytest.mark.parametrize(
    "mutation",
    ("missing", "extra", "unknown", "duplicate"),
)
def test_application_rejects_non_exact_asset_scope(mutation: str):
    application = load("m11-p0-mit-ocw-evidence-review-application-v1.json")
    if mutation == "missing":
        application["batch_records"].pop()
    elif mutation == "extra":
        extra = copy.deepcopy(application["batch_records"][0])
        extra["asset_id"] = "extra_asset"
        application["batch_records"].append(extra)
    elif mutation == "unknown":
        application["batch_records"][0]["asset_id"] = "unknown_asset"
    else:
        application["batch_records"][1] = copy.deepcopy(application["batch_records"][0])
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_application(application)


def test_broad_historical_authority_and_wrong_authority_id_are_rejected():
    args = bundle_args()
    args["authority"] = load("m11-p0-human-review-26-authority-v1.json")
    with pytest.raises(
        MitOcwEvidenceReviewError,
        match="MIT_OCW_AUTHORITY_NOT_EXACT_TWENTY",
    ):
        validate_mit_ocw_evidence_review_bundle(**args)

    args = bundle_args()
    args["application"]["authority_id"] = "unrelated-authority"
    args["result"]["authority_id"] = "unrelated-authority"
    with pytest.raises(MitOcwEvidenceReviewError, match="MIT_OCW_APPLICATION_IDENTITY_INVALID"):
        validate_mit_ocw_evidence_review_bundle(**args)


def test_authority_lifetime_is_bound_to_application_and_successor_times():
    args = bundle_args()
    args["application"]["submitted_at"] = "2026-09-27T11:59:59Z"
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)

    args = bundle_args()
    args["successor_wrapper"]["signed_at"] = "2026-10-11T12:00:01Z"
    for record in args["successor_wrapper"]["records"]:
        record["signed_at"] = "2026-10-11T12:00:01Z"
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)


@pytest.mark.parametrize("field", ("candidate_digest", "receipt_digest", "revision"))
def test_result_identity_mutations_fail_closed(field: str):
    args = bundle_args()
    args["result"]["records"][0][field] = "f" * 64
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)


def test_historical_disposition_and_normalization_exceptions_are_bound():
    args = bundle_args()
    records = {record["asset_id"]: record for record in args["result"]["records"]}

    assert records["digital_answers"]["prior_disposition"] == "NORMALIZATION_REJECTED"
    assert (
        records["digital_answers"]["normalization_status"],
        records["digital_answers"]["normalization_reason"],
    ) == ("NORMALIZATION_REJECTED", "SOURCE_PARSE_FAILED")
    assert records["information_worksheet"]["prior_disposition"] == "NORMALIZATION_REJECTED"
    assert (
        records["information_worksheet"]["normalization_status"],
        records["information_worksheet"]["normalization_reason"],
    ) == ("NORMALIZATION_REJECTED", "INVALID_CANDIDATE_INPUT")

    args["result"]["records"][0]["prior_disposition"] = "NORMALIZATION_REJECTED"
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)

    args = bundle_args()
    record = next(
        item for item in args["result"]["records"] if item["asset_id"] == "digital_answers"
    )
    record["normalization_status"] = "CANDIDATE"
    record["normalization_reason"] = "NONE"
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)


def test_observations_remain_non_closing_and_limitations_are_exact():
    args = bundle_args()
    findings = {
        item["finding_id"]: item
        for item in args["official_observation"]["source_observations"]
    }
    for finding_id in (
        "mit-robots-digest-match",
        "mit-source-policy",
        "mit-third-party-limitation",
    ):
        assert findings[finding_id]["closure_effect"] == "NONE"
        assert findings[finding_id]["requires_follow_up"] is True

    args["result"]["records"][0]["observation_limitations"][0] = "substituted limitation"
    with pytest.raises(
        MitOcwEvidenceReviewError,
        match="MIT_OCW_RESULT_OBSERVATION_LIMITATION_INVALID",
    ):
        validate_mit_ocw_evidence_review_bundle(**args)

    args = bundle_args()
    args["result"]["records"][0]["third_party_rights"] = "RESOLVED"
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)


def test_evidence_status_and_human_decision_cannot_be_promoted_or_rejected():
    args = bundle_args()
    args["result"]["records"][0]["evidence"]["license"]["status"] = "VERIFIED"
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)

    for decision in ("ACCEPT_FOR_PROMOTION_REVIEW", "REJECT"):
        args = bundle_args()
        args["successor_wrapper"]["records"][0]["decision"] = decision
        with pytest.raises(MitOcwEvidenceReviewError):
            validate_mit_ocw_evidence_review_bundle(**args)


def test_successors_are_metadata_only_and_exactly_supersede_mit_heads():
    args = bundle_args()
    records = args["successor_wrapper"]["records"]
    assert len(records) == 20
    assert all(record["decision"] == "DEFER" for record in records)
    assert all(record["document_id"] is None and record["chunk_ids"] == [] for record in records)
    assert {
        record["supersedes"] for record in records
    } == {
        f"m11-hr-20260926-official-observation-{asset_id}"
        for asset_id in EXACT_ASSETS[SOURCE_ID]
    }

    args["successor_wrapper"]["records"][0]["supersedes"] = (
        "m11-hr-20260926-official-observation-rfc-9110"
    )
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)


def test_both_successor_slices_form_exactly_twenty_six_current_heads():
    args = bundle_args()
    official = args["official_review_wrapper"]["records"]
    rfc_successors = args["rfc_iana_successor_wrapper"]["records"]
    mit_successors = args["successor_wrapper"]["records"]
    superseded = {
        record["supersedes"] for record in [*rfc_successors, *mit_successors]
    }
    current = {
        record["review_id"]
        for record in [*official, *rfc_successors, *mit_successors]
        if record["review_id"] not in superseded
    }

    assert len([*official, *rfc_successors, *mit_successors]) == 52
    assert len(superseded) == 26
    assert len(current) == 26
    assert current == {
        record["review_id"] for record in [*rfc_successors, *mit_successors]
    }
    validate_mit_ocw_evidence_review_bundle(**args)


def test_gate0_projection_remains_blocked_with_zero_reviewed_assets(monkeypatch):
    args = bundle_args()
    observed: dict = {}

    def fake_gate0_status(**kwargs):
        observed.update(kwargs)
        return {"status": "BLOCKED", "reviewed_asset_count": 0}

    monkeypatch.setattr(
        "app.m11_mit_ocw_evidence_review.gate0_status",
        fake_gate0_status,
    )
    validate_mit_ocw_evidence_review_bundle(**args)

    assert set(observed["required_assets"]) == {
        (SOURCE_ID, asset_id) for asset_id in EXACT_ASSETS[SOURCE_ID]
    }
    assert observed["authority_present"] is True
    assert observed["scope_digest"] == PARENT_SCOPE_DIGEST

    monkeypatch.setattr(
        "app.m11_mit_ocw_evidence_review.gate0_status",
        lambda **kwargs: {"status": "PASS", "reviewed_asset_count": 20},
    )
    with pytest.raises(MitOcwEvidenceReviewError, match="MIT_OCW_GATE0_STATE_CHANGED"):
        validate_mit_ocw_evidence_review_bundle(**args)


def test_application_and_result_return_detached_copies():
    application = load("m11-p0-mit-ocw-evidence-review-application-v1.json")
    detached_application = validate_mit_ocw_evidence_review_application(application)
    detached_application["batch_records"][0]["asset_id"] = "changed"
    assert application["batch_records"][0]["asset_id"] != "changed"

    result = load("m11-p0-mit-ocw-evidence-review-result-v1.json")
    detached_result = validate_mit_ocw_evidence_review_result(result)
    detached_result["records"][0]["evidence"]["license"]["status"] = "VERIFIED"
    assert result["records"][0]["evidence"]["license"]["status"] == "PENDING"


def test_privacy_host_paths_escalation_and_bad_timestamps_fail_closed():
    application = load("m11-p0-mit-ocw-evidence-review-application-v1.json")
    for host_path in (
        r"file=C:\Users\owner\secret.txt",
        r"\\server\share\secret.txt",
        "/home/owner/secret.txt",
    ):
        mutated = copy.deepcopy(application)
        mutated["submitted_by"] = host_path
        with pytest.raises(MitOcwEvidenceReviewError):
            validate_mit_ocw_evidence_review_application(mutated)

    for timestamp in ("not-a-timestamp", "2026-09-27T12:00:00"):
        mutated = copy.deepcopy(application)
        mutated["submitted_at"] = timestamp
        with pytest.raises(MitOcwEvidenceReviewError):
            validate_mit_ocw_evidence_review_application(mutated)

    args = bundle_args()
    args["application"]["network_used"] = True
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)

    args = bundle_args()
    args["result"]["records"][0]["private_learning_state"] = "forbidden"
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)


def test_dependency_errors_are_normalized():
    args = bundle_args()
    args["receipts"][0]["status"] = "INVALID"
    with pytest.raises(MitOcwEvidenceReviewError) as exc_info:
        validate_mit_ocw_evidence_review_bundle(**args)
    assert exc_info.value.code == "MIT_OCW_DEPENDENCY_INVALID"


def test_scope_is_only_mit_exact_twenty_and_excludes_other_sources():
    args = bundle_args()
    assert args["application"]["source_ids"] == [SOURCE_ID]
    assert args["application"]["asset_ids"] == {
        SOURCE_ID: list(EXACT_ASSETS[SOURCE_ID])
    }
    assert {record["source_id"] for record in args["result"]["records"]} == {SOURCE_ID}
    assert {record["source_id"] for record in args["successor_wrapper"]["records"]} == {
        SOURCE_ID
    }
    assert all("rfc" not in record["asset_id"] for record in args["result"]["records"])
    assert all("iana" not in record["asset_id"] for record in args["result"]["records"])
    assert all("opendsa" not in record["asset_id"] for record in args["result"]["records"])

    validate_mit_ocw_evidence_review_bundle(**args)


def test_fixed_artifact_identities_and_predecessor_links_fail_closed():
    application = load("m11-p0-mit-ocw-evidence-review-application-v1.json")
    application["application_id"] = "m11-p0-mit-ocw-evidence-review-application-v2"
    with pytest.raises(MitOcwEvidenceReviewError, match="MIT_OCW_APPLICATION_IDENTITY_INVALID"):
        validate_mit_ocw_evidence_review_application(application)

    application = load("m11-p0-mit-ocw-evidence-review-application-v1.json")
    application["authority_id"] = "unrelated-authority"
    with pytest.raises(MitOcwEvidenceReviewError, match="MIT_OCW_APPLICATION_IDENTITY_INVALID"):
        validate_mit_ocw_evidence_review_application(application)

    result = load("m11-p0-mit-ocw-evidence-review-result-v1.json")
    result["result_id"] = "m11-p0-mit-ocw-evidence-review-result-v2"
    with pytest.raises(MitOcwEvidenceReviewError, match="MIT_OCW_RESULT_IDENTITY_INVALID"):
        validate_mit_ocw_evidence_review_result(result)

    args = bundle_args()
    args["closure_matrix"]["matrix_id"] = "m11-p0-evidence-closure-26-substitute"
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)


def test_predecessor_universe_and_historical_evidence_are_frozen():
    args = bundle_args()
    fake = copy.deepcopy(args["digest_assets"][0])
    fake["source_id"] = SOURCE_ID
    fake["asset_id"] = EXACT_ASSETS[SOURCE_ID][0]
    args["digest_assets"][0] = fake
    with pytest.raises(MitOcwEvidenceReviewError, match="MIT_OCW_PREDECESSOR_SCOPE_INVALID"):
        validate_mit_ocw_evidence_review_bundle(**args)

    args = bundle_args()
    closure_record = next(
        record
        for record in args["closure_matrix"]["records"]
        if record["source_id"] == SOURCE_ID
    )
    closure_record["evidence"]["license"]["refs"] = ["substituted-reference"]
    with pytest.raises(MitOcwEvidenceReviewError):
        validate_mit_ocw_evidence_review_bundle(**args)


def test_successor_requires_exact_provenance_causal_time_and_valid_attestation():
    args = bundle_args()
    args["successor_wrapper"]["records"][0]["evidence_refs"].pop()
    with pytest.raises(MitOcwEvidenceReviewError, match="MIT_OCW_SUCCESSOR_IDENTITY_INVALID"):
        validate_mit_ocw_evidence_review_bundle(**args)

    args = bundle_args()
    args["application"]["submitted_at"] = "2026-09-27T12:00:01Z"
    with pytest.raises(MitOcwEvidenceReviewError, match="MIT_OCW_SUCCESSOR_TIMESTAMP_ORDER_INVALID"):
        validate_mit_ocw_evidence_review_bundle(**args)

    args = bundle_args()
    args["successor_wrapper"]["records"][0]["attestation_digest"] = "f" * 64
    with pytest.raises(MitOcwEvidenceReviewError, match="MIT_OCW_SUCCESSOR_ATTESTATION_INVALID"):
        validate_mit_ocw_evidence_review_bundle(**args)


def test_malformed_nested_dependencies_are_normalized():
    args = bundle_args()
    args["closure_matrix"]["records"][0]["evidence"]["license"] = []
    with pytest.raises(MitOcwEvidenceReviewError) as exc_info:
        validate_mit_ocw_evidence_review_bundle(**args)
    assert exc_info.value.code == "MIT_OCW_DEPENDENCY_INVALID"
