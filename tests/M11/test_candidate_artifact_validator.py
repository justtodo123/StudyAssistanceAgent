from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from app.m11_candidate_artifact_validator import (
    CandidateArtifactValidationError,
    load_and_validate_candidate_artifact,
    validate_candidate_artifact,
)
from app.m11_candidate_pipeline import _normalize_candidate

pytestmark = pytest.mark.m11


def _valid_artifact(m11_data_tree, tmp_path: Path) -> tuple[dict, Path]:
    raw = m11_data_tree["raw"] / "rfc9110.txt"
    raw_bytes = b"Network Working Group\n\nHTTP Semantics\n\nA candidate document.\n"
    raw.write_bytes(raw_bytes)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    result = _normalize_candidate(
        source_label="rfc-editor-index",
        asset_id="rfc9110",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        canonical_url="https://www.rfc-editor.org/rfc/rfc9110.txt",
        revision=digest,
    )
    assert result.status == "CANDIDATE", result.reason
    artifact = m11_data_tree["candidates"] / result.candidate_path
    return json.loads(artifact.read_text(encoding="utf-8")), artifact


def _assert_code(payload, code: str) -> None:
    with pytest.raises(CandidateArtifactValidationError) as exc_info:
        validate_candidate_artifact(payload)
    assert str(exc_info.value) == code


def test_valid_bound_candidate_artifact_passes(m11_data_tree, tmp_path):
    payload, artifact = _valid_artifact(m11_data_tree, tmp_path)
    validate_candidate_artifact(payload, artifact_name=artifact.name)
    assert load_and_validate_candidate_artifact(artifact)["approved"] is False


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda p: p.pop("schema"), "CANDIDATE_ARTIFACT_FIELDS_INVALID"),
        (lambda p: p.update(extra=True), "CANDIDATE_ARTIFACT_FIELDS_INVALID"),
        (lambda p: p.update(source_label="../source"), "CANDIDATE_ARTIFACT_SOURCE_LABEL_INVALID"),
        (lambda p: p.update(asset_id="/absolute"), "CANDIDATE_ARTIFACT_ASSET_ID_INVALID"),
        (lambda p: p.update(source_id="user-invalid"), "CANDIDATE_ARTIFACT_SOURCE_ID_MISMATCH"),
        (lambda p: p.update(canonical_url="http://example.org"), "CANDIDATE_ARTIFACT_PROVENANCE_INVALID"),
        (lambda p: p.update(revision=""), "CANDIDATE_ARTIFACT_PROVENANCE_INVALID"),
        (lambda p: p.update(source_blob_sha1="G" * 40), "CANDIDATE_ARTIFACT_PROVENANCE_INVALID"),
        (lambda p: p.update(content_digest="0" * 63), "CANDIDATE_ARTIFACT_DIGEST_INVALID"),
        (lambda p: p.update(license_status="approved"), "CANDIDATE_ARTIFACT_LICENSE_INVALID"),
        (lambda p: p.update(ingest_status="approved"), "CANDIDATE_ARTIFACT_LIFECYCLE_INVALID"),
        (lambda p: p.update(source_type="web_reviewed"), "CANDIDATE_ARTIFACT_SOURCE_TYPE_INVALID"),
        (lambda p: p.update(approved=True), "CANDIDATE_ARTIFACT_LIFECYCLE_INVALID"),
        (lambda p: p.update(published=True), "CANDIDATE_ARTIFACT_LIFECYCLE_INVALID"),
        (lambda p: p["document"].pop("format"), "CANDIDATE_ARTIFACT_DOCUMENT_FIELDS_INVALID"),
        (lambda p: p["document"].update(document_id="0" * 32), "CANDIDATE_ARTIFACT_DOCUMENT_ID_MISMATCH"),
        (lambda p: p["document"].update(content_fingerprint="0" * 64), "CANDIDATE_ARTIFACT_DIGEST_MISMATCH"),
        (lambda p: p["document"].update(chunk_count=0), "CANDIDATE_ARTIFACT_CHUNK_COUNT_INVALID"),
        (lambda p: p["chunks"][0].update(chunk_schema="wrong"), "CANDIDATE_ARTIFACT_CHUNK_SCHEMA_INVALID"),
        (lambda p: p["chunks"][0].update(chunk_id="0" * 32), "CANDIDATE_ARTIFACT_CHUNK_ID_MISMATCH"),
        (lambda p: p["chunks"][0].update(content_digest="x" * 64), "CANDIDATE_ARTIFACT_DIGEST_INVALID"),
        (lambda p: p["chunks"][0].update(ordinal=-1), "CANDIDATE_ARTIFACT_ORDINAL_INVALID"),
        (lambda p: p["chunks"][0].update(ordinal=True), "CANDIDATE_ARTIFACT_ORDINAL_INVALID"),
        (lambda p: p["chunks"][0].update(content="secret"), "CANDIDATE_ARTIFACT_PRIVACY_FIELD"),
        (lambda p: p["chunks"][0].update(raw_path="C:/secret"), "CANDIDATE_ARTIFACT_PRIVACY_FIELD"),
    ],
)

def test_artifact_mutations_fail_closed(m11_data_tree, tmp_path, mutation, code):
    payload, _ = _valid_artifact(m11_data_tree, tmp_path)
    mutated = copy.deepcopy(payload)
    mutation(mutated)
    _assert_code(mutated, code)


def test_artifact_rejects_document_and_chunk_link_drift(m11_data_tree, tmp_path):
    payload, _ = _valid_artifact(m11_data_tree, tmp_path)
    mutated = copy.deepcopy(payload)
    mutated["document"]["source_id"] = "user-other"
    _assert_code(mutated, "CANDIDATE_ARTIFACT_DOCUMENT_LINK_INVALID")

    mutated = copy.deepcopy(payload)
    mutated["chunks"][0]["logical_uri"] = "other"
    _assert_code(mutated, "CANDIDATE_ARTIFACT_CHUNK_LINK_INVALID")


def test_artifact_rejects_duplicate_chunk_identity_and_count_drift(m11_data_tree, tmp_path):
    payload, _ = _valid_artifact(m11_data_tree, tmp_path)
    if len(payload["chunks"]) < 2:
        pytest.skip("fixture produced one chunk")
    mutated = copy.deepcopy(payload)
    mutated["chunks"][1]["chunk_key"] = mutated["chunks"][0]["chunk_key"]
    _assert_code(mutated, "CANDIDATE_ARTIFACT_CHUNK_DUPLICATE")

    mutated = copy.deepcopy(payload)
    mutated["document"]["chunk_count"] += 1
    _assert_code(mutated, "CANDIDATE_ARTIFACT_CHUNK_COUNT_INVALID")


def test_artifact_name_is_bound_without_path_leakage(m11_data_tree, tmp_path):
    payload, artifact = _valid_artifact(m11_data_tree, tmp_path)
    with pytest.raises(CandidateArtifactValidationError) as exc_info:
        validate_candidate_artifact(payload, artifact_name="C:/outside.json")
    assert str(exc_info.value) == "CANDIDATE_ARTIFACT_NAME_INVALID"
    assert "outside" not in str(exc_info.value)
    validate_candidate_artifact(payload, artifact_name=artifact.name)


@pytest.mark.parametrize("raw", [b"", b"not-json"])
def test_loader_fails_closed_for_invalid_json(tmp_path, raw):
    path = tmp_path / "artifact.json"
    path.write_bytes(raw)
    with pytest.raises(CandidateArtifactValidationError) as exc_info:
        load_and_validate_candidate_artifact(path)
    assert str(exc_info.value) == "CANDIDATE_ARTIFACT_UNREADABLE"


def test_loader_rejects_non_object_and_missing_file(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(CandidateArtifactValidationError, match="CANDIDATE_ARTIFACT_ROOT_INVALID"):
        load_and_validate_candidate_artifact(path)
    with pytest.raises(CandidateArtifactValidationError, match="CANDIDATE_ARTIFACT_UNREADABLE"):
        load_and_validate_candidate_artifact(tmp_path / "missing.json")
