from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.m11_mit_ocw_pipeline_diagnosis import (
    MitOcwPipelineDiagnosisError,
    validate_mit_ocw_pipeline_diagnosis,
)

pytestmark = pytest.mark.m11
ROOT = Path(__file__).resolve().parents[2]
FILES = {
    "diagnosis": ROOT / "data/manifests/m11-p0-mit-ocw-pipeline-diagnosis-v1.json",
    "materialization": ROOT / "data/manifests/m11-p0-mit-ocw-candidate-materialization-v1.json",
    "digest_evidence": ROOT / "data/manifests/m11-p0-digest-evidence-v1.json",
    "receipt_batch": ROOT / "data/manifests/m11-p0-acquisition-26-receipts-v1.json",
}


def load(name: str):
    return json.loads(FILES[name].read_text(encoding="utf-8"))


def validate(payload=None, **dependencies):
    deps = {name: load(name) for name in ("materialization", "digest_evidence", "receipt_batch")}
    deps.update(dependencies)
    return validate_mit_ocw_pipeline_diagnosis(
        load("diagnosis") if payload is None else payload,
        materialization=deps["materialization"],
        digest_evidence=deps["digest_evidence"],
        receipt_batch=deps["receipt_batch"],
    )


def test_exact_two_diagnoses_remain_unresolved():
    result = validate()
    assert [item["asset_id"] for item in result["diagnoses"]] == [
        "digital_answers", "information_worksheet"
    ]
    assert [item["pipeline_reason"] for item in result["diagnoses"]] == [
        "SOURCE_PARSE_FAILED", "INVALID_CANDIDATE_INPUT"
    ]
    assert all(item["diagnosis_status"] == "UNRESOLVED" for item in result["diagnoses"])
    assert all(item["exact_root_cause_proved"] is False for item in result["diagnoses"])


def test_probe_results_are_observations_not_causes():
    result = validate()
    for item in result["diagnoses"]:
        assert [observation["result_code"] for observation in item["probe_observations"]] == [
            "FORMAT_UNSUPPORTED", "FORMAT_MISMATCH"
        ]
        assert all(
            observation["classification"] == "BOUNDED_OBSERVATION_NOT_ROOT_CAUSE"
            for observation in item["probe_observations"]
        )


def test_diagnosis_is_metadata_only_and_nonexecuting():
    result = validate()
    assert result["metadata_only"] is True
    for field in (
        "authority_issued", "human_review_reject_mapped", "evidence_failed_mapped",
        "successor_created", "formal_gate0_executed", "production_artifact_repaired",
        "parser_contract_changed", "network_used", "lifecycle_mutation",
        "host_paths_included", "bodies_included",
    ):
        assert result[field] is False


@pytest.mark.parametrize("dependency", ["materialization", "digest_evidence", "receipt_batch"])
def test_resealed_mutated_dependency_still_fails(dependency):
    deps = {name: load(name) for name in ("materialization", "digest_evidence", "receipt_batch")}
    if dependency == "materialization":
        deps[dependency]["rejections"][0]["reason"] = "SOURCE_PARSER_UNAVAILABLE"
    elif dependency == "digest_evidence":
        match = next(item for item in deps[dependency]["assets"] if item["asset_id"] == "digital_answers")
        match["bytes"] += 1
    else:
        match = next(item for item in deps[dependency]["receipts"] if item["asset_id"] == "information_worksheet")
        match["revision"] = "f" * 64
    payload = load("diagnosis")
    with pytest.raises(MitOcwPipelineDiagnosisError):
        validate(payload, **deps)


@pytest.mark.parametrize("mutation", [
    lambda p: p["diagnoses"][0].__setitem__("diagnosis_status", "RESOLVED"),
    lambda p: p["diagnoses"][0].__setitem__("exact_root_cause_proved", True),
    lambda p: p["diagnoses"][0]["probe_observations"][0].__setitem__("classification", "ROOT_CAUSE"),
    lambda p: p.__setitem__("human_review_reject_mapped", True),
    lambda p: p.__setitem__("evidence_failed_mapped", True),
    lambda p: p.__setitem__("successor_created", True),
    lambda p: p.__setitem__("formal_gate0_executed", True),
    lambda p: p.__setitem__("authority_issued", True),
    lambda p: p.__setitem__("owner_verdict", "REJECT"),
])
def test_manifest_mutations_fail_closed(mutation):
    payload = copy.deepcopy(load("diagnosis"))
    mutation(payload)
    with pytest.raises(MitOcwPipelineDiagnosisError):
        validate(payload)


def test_detached_copy_lf_and_privacy():
    before = FILES["diagnosis"].read_bytes()
    result = validate()
    result["diagnoses"][0]["diagnosis_status"] = "changed"
    assert load("diagnosis")["diagnoses"][0]["diagnosis_status"] == "UNRESOLVED"
    assert FILES["diagnosis"].read_bytes() == before
    assert b"\r" not in before
    text = before.decode("utf-8")
    assert "D:/" not in text and "D:\\" not in text and '"body"' not in text
