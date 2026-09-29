from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.m11_mit_ocw_content_quality_review import MitOcwContentQualityReviewError, validate_mit_ocw_content_quality_result
from app.m11_mit_ocw_schema_review import MitOcwSchemaReviewError, validate_mit_ocw_schema_result
from app.m11_mit_ocw_technical_evidence_review import MitOcwTechnicalEvidenceReviewError, validate_mit_ocw_technical_result

pytestmark = pytest.mark.m11
ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "data/manifests"

def load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))

def dependencies() -> dict:
    return {key: load(name) for key, name in {
        "packet": "m11-p0-mit-ocw-owner-decision-input-packet-v1.json",
        "materialization": "m11-p0-mit-ocw-candidate-materialization-v1.json",
        "digest_evidence": "m11-p0-digest-evidence-v1.json",
        "receipt_batch": "m11-p0-acquisition-26-receipts-v1.json",
        "gate0_result": "m11-p0-formal-gate0-26-result-v1.json",
    }.items()}

def validate_all() -> tuple[dict, dict, dict]:
    deps = dependencies()
    schema = validate_mit_ocw_schema_result(load("m11-p0-mit-ocw-schema-review-result-v1.json"), authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), **deps)
    technical = validate_mit_ocw_technical_result(load("m11-p0-mit-ocw-technical-evidence-review-result-v1.json"), authority=load("m11-p0-mit-ocw-technical-evidence-review-authority-v1.json"), schema_result=schema, schema_authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), **deps)
    content = validate_mit_ocw_content_quality_result(load("m11-p0-mit-ocw-content-quality-review-result-v1.json"), authority=load("m11-p0-mit-ocw-content-quality-review-authority-v1.json"), schema_result=schema, schema_authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), technical_result=technical, technical_authority=load("m11-p0-mit-ocw-technical-evidence-review-authority-v1.json"), **deps)
    return schema, technical, content

def test_exact_eighteen_conservative_review_chain_is_valid():
    schema, technical, content = validate_all()
    for result, expected_pending in ((schema, 18), (technical, 54), (content, 18)):
        assert result["asset_count"] == 18
        assert (result["closed_cell_count"], result["pending_cell_count"], result["packet_pending_cell_count"], result["failed_cell_count"]) == (0, expected_pending, 144, 0)
        assert result["result"] == "REVIEW_REQUIRED"
        assert result["current_heads"] == {"rfc": "3 ACCEPT", "iana": "3 DEFER", "mit_ocw": "20 DEFER"}
        assert result["successor_slice_written"] is False
    assert {record["schema"]["status"] for record in schema["records"]} == {"PENDING"}
    assert {record["revision"]["status"] for record in technical["records"]} == {"PENDING"}
    assert {record["content_quality"]["status"] for record in content["records"]} == {"PENDING"}

def test_rejected_assets_cannot_enter_authority_or_results():
    deps = dependencies()
    authority = load("m11-p0-mit-ocw-schema-review-authority-v1.json")
    authority["asset_ids"]["mit-ocw-6-004-2017"].append("digital_answers")
    with pytest.raises(MitOcwSchemaReviewError):
        validate_mit_ocw_schema_result(load("m11-p0-mit-ocw-schema-review-result-v1.json"), authority=authority, **deps)
    result = load("m11-p0-mit-ocw-schema-review-result-v1.json")
    result["records"][0]["asset_id"] = "information_worksheet"
    with pytest.raises(MitOcwSchemaReviewError):
        validate_mit_ocw_schema_result(result, authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), **deps)

@pytest.mark.parametrize("mutation", [
    lambda result: result.__setitem__("formal_gate0_executed", True),
    lambda result: result.__setitem__("successor_slice_written", True),
    lambda result: result.__setitem__("publication_authorized", True),
    lambda result: result["records"][0]["schema"].__setitem__("status", "VERIFIED"),
    lambda result: result.__setitem__("pending_cell_count", 0),
])
def test_schema_mutations_fail_closed(mutation):
    deps = dependencies()
    result = load("m11-p0-mit-ocw-schema-review-result-v1.json")
    mutation(result)
    with pytest.raises(MitOcwSchemaReviewError):
        validate_mit_ocw_schema_result(result, authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), **deps)

def test_dependency_seals_and_predecessors_fail_closed():
    deps = dependencies()
    schema, technical, _ = validate_all()
    mutated = copy.deepcopy(deps)
    mutated["materialization"]["assets"][0]["candidate_digest"] = "0" * 64
    with pytest.raises(MitOcwSchemaReviewError):
        validate_mit_ocw_schema_result(load("m11-p0-mit-ocw-schema-review-result-v1.json"), authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), **mutated)
    forged_schema = copy.deepcopy(schema)
    forged_schema["records"][0]["schema"]["rationale"] = "forged same-id predecessor"
    with pytest.raises(MitOcwTechnicalEvidenceReviewError):
        validate_mit_ocw_technical_result(load("m11-p0-mit-ocw-technical-evidence-review-result-v1.json"), authority=load("m11-p0-mit-ocw-technical-evidence-review-authority-v1.json"), schema_result=forged_schema, schema_authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), **deps)
    forged_technical = copy.deepcopy(technical)
    forged_technical["records"][0]["parser"]["rationale"] = "forged same-id predecessor"
    with pytest.raises(MitOcwContentQualityReviewError):
        validate_mit_ocw_content_quality_result(load("m11-p0-mit-ocw-content-quality-review-result-v1.json"), authority=load("m11-p0-mit-ocw-content-quality-review-authority-v1.json"), schema_result=schema, schema_authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), technical_result=forged_technical, technical_authority=load("m11-p0-mit-ocw-technical-evidence-review-authority-v1.json"), **deps)
    technical["result_id"] = "wrong"
    with pytest.raises(MitOcwContentQualityReviewError):
        validate_mit_ocw_content_quality_result(load("m11-p0-mit-ocw-content-quality-review-result-v1.json"), authority=load("m11-p0-mit-ocw-content-quality-review-authority-v1.json"), schema_result=schema, schema_authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), technical_result=technical, technical_authority=load("m11-p0-mit-ocw-technical-evidence-review-authority-v1.json"), **deps)


def test_authority_and_result_timestamps_are_bounded_and_ordered():
    deps = dependencies()
    authority = load("m11-p0-mit-ocw-schema-review-authority-v1.json")
    result = load("m11-p0-mit-ocw-schema-review-result-v1.json")
    assert authority["issued_at"] == "2026-09-29T06:00:00Z"
    assert result["signed_at"] == "2026-09-29T06:20:00Z"
    assert authority["expires_at"] == "2026-10-13T06:00:00Z"
    expired_signature = copy.deepcopy(result)
    expired_signature["signed_at"] = authority["expires_at"]
    with pytest.raises(MitOcwSchemaReviewError):
        validate_mit_ocw_schema_result(expired_signature, authority=authority, **deps)
    expired_authority = copy.deepcopy(authority)
    expired_authority["expires_at"] = "2026-09-29T06:30:00Z"
    with pytest.raises(MitOcwSchemaReviewError):
        validate_mit_ocw_schema_result(result, authority=expired_authority, **deps)

def test_results_are_detached_and_inputs_unchanged():
    schema, technical, content = validate_all()
    schema["records"][0]["schema"]["status"] = "changed"
    technical["records"][0]["parser"]["status"] = "changed"
    content["records"][0]["content_quality"]["status"] = "changed"
    fresh_schema, fresh_technical, fresh_content = validate_all()
    assert fresh_schema["records"][0]["schema"]["status"] == "PENDING"
    assert fresh_technical["records"][0]["parser"]["status"] == "PENDING"
    assert fresh_content["records"][0]["content_quality"]["status"] == "PENDING"


def test_derived_counts_timestamp_order_and_predecessor_seals_fail_closed():
    deps = dependencies()
    schema, technical, content = validate_all()
    assert [result["signed_at"] for result in (schema, technical, content)] == [
        "2026-09-29T06:20:00Z", "2026-09-29T06:21:00Z", "2026-09-29T06:22:00Z"
    ]
    invalid_technical = load("m11-p0-mit-ocw-technical-evidence-review-result-v1.json")
    invalid_technical["pending_cell_count"] = 18
    with pytest.raises(MitOcwTechnicalEvidenceReviewError):
        validate_mit_ocw_technical_result(invalid_technical, authority=load("m11-p0-mit-ocw-technical-evidence-review-authority-v1.json"), schema_result=schema, schema_authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), **deps)
    invalid_content = load("m11-p0-mit-ocw-content-quality-review-result-v1.json")
    invalid_content["signed_at"] = technical["signed_at"]
    with pytest.raises(MitOcwContentQualityReviewError):
        validate_mit_ocw_content_quality_result(invalid_content, authority=load("m11-p0-mit-ocw-content-quality-review-authority-v1.json"), schema_result=schema, schema_authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), technical_result=technical, technical_authority=load("m11-p0-mit-ocw-technical-evidence-review-authority-v1.json"), **deps)
    invalid_seal = load("m11-p0-mit-ocw-technical-evidence-review-result-v1.json")
    invalid_seal["predecessor_content_seals"]["schema_result"] = "0" * 64
    with pytest.raises(MitOcwTechnicalEvidenceReviewError):
        validate_mit_ocw_technical_result(invalid_seal, authority=load("m11-p0-mit-ocw-technical-evidence-review-authority-v1.json"), schema_result=schema, schema_authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), **deps)
