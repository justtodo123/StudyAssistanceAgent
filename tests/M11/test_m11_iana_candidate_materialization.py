from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_iana_candidate_materialization import (
    IanaCandidateMaterializationError,
    frozen_runtime_identity,
    validate_iana_candidate_materialization,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/manifests/m11-p0-iana-candidate-materialization-v1.json"

def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))

def test_iana_exact_three_checkpoint_is_strict_and_non_promoting():
    payload = validate_iana_candidate_materialization(load())
    assert payload["candidate_asset_count"] == payload["candidate_chunk_count"] == 3
    assert payload["rejections"] == []
    assert payload["approved_document_count"] == payload["approved_chunk_count"] == 0
    assert payload["current_heads"]["iana"] == "3 DEFER"
    assert payload["historical_gate0"]["result"] == "BLOCKED"

def test_iana_checkpoint_binds_document_chunk_and_artifact_identities():
    payload = load()
    assert len({item["document_id"] for item in payload["assets"]}) == 3
    assert len({item["chunk_id"] for item in payload["assets"]}) == 3
    assert all(item["raw_sha256"] == item["revision"] == item["content_fingerprint"] for item in payload["assets"])
    assert all(len(item["candidate_artifact_sha256"]) == 64 and len(item["normalized_artifact_sha256"]) == 64 for item in payload["assets"])

def test_iana_checkpoint_preserves_pending_review_facts():
    review = json.loads((ROOT / "data/manifests/m11-p0-iana-evidence-review-result-v1.json").read_text(encoding="utf-8"))
    assert review["pending_cell_count"] == 24
    assert review["current_heads"]["iana"] == "3 DEFER"
    assert review["successor_slice_written"] is False
    assert all(value["status"] == "PENDING" for record in review["records"] for value in record["evidence"].values())

def test_ambient_non_3119_runtime_fails_closed_without_outputs(tmp_path):
    before = list(tmp_path.iterdir())
    try:
        identity = frozen_runtime_identity()
    except IanaCandidateMaterializationError as exc:
        assert str(exc) == "IANA_MATERIALIZATION_RUNTIME_UNAVAILABLE"
    else:
        assert identity == {"implementation": "cpython", "python": "3.11.9", "parser_contract": "cpython-textio==3.11.9"}
    assert list(tmp_path.iterdir()) == before

@pytest.mark.parametrize("mutation", (
    lambda p: p["assets"].pop(),
    lambda p: p["assets"][0].__setitem__("chunk_id", "f" * 32),
    lambda p: p["parser_environment"].__setitem__("python", "3.13.3"),
    lambda p: p["parser_observations"].__setitem__("txt", "REPLAYED"),
    lambda p: p["historical_gate0"].__setitem__("result", "PASSED"),
    lambda p: p["current_heads"].__setitem__("iana", "3 ACCEPT"),
    lambda p: p.__setitem__("publication_authorized", True),
    lambda p: p.__setitem__("approved_chunk_count", 3),
))
def test_iana_checkpoint_mutations_fail_closed(mutation):
    payload = copy.deepcopy(load())
    mutation(payload)
    with pytest.raises(IanaCandidateMaterializationError):
        validate_iana_candidate_materialization(payload)
