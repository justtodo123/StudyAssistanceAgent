from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.m11_evidence_closure import (
    EVIDENCE_CLOSURE_SCHEMA,
    EVIDENCE_STATUSES,
    EvidenceClosureError,
    load_evidence_closure,
    validate_closure_bundle,
    validate_evidence_closure,
)
from app.m11_review import gate0_status

pytestmark = pytest.mark.m11

MATRIX = Path("data/manifests/m11-p0-evidence-closure-26-v1.json")
DIGEST = Path("data/manifests/m11-p0-digest-evidence-v1.json")
RECEIPTS = Path("data/manifests/m11-p0-acquisition-26-receipts-v1.json")
PRIOR = Path("data/manifests/m11-p0-human-review-acq-defer-26-v1.json")
CLOSURE = Path("data/manifests/m11-p0-human-review-closure-defer-26-v1.json")


def _load(repo_root: Path, path: Path) -> dict:
    return json.loads((repo_root / path).read_text(encoding="utf-8"))


def _bundle(repo_root: Path):
    matrix = _load(repo_root, MATRIX)
    digest = _load(repo_root, DIGEST)
    receipts = _load(repo_root, RECEIPTS)
    prior = _load(repo_root, PRIOR)
    closure = _load(repo_root, CLOSURE)
    expected = [(x["source_id"], x["asset_id"]) for x in digest["assets"]]
    return matrix, digest, receipts, prior, closure, expected


def test_closure_matrix_is_exactly_26_and_all_eight_categories(repo_root):
    matrix = load_evidence_closure(repo_root / MATRIX)
    assert matrix["schema"] == EVIDENCE_CLOSURE_SCHEMA
    assert matrix["asset_count"] == 26
    assert len(matrix["records"]) == 26
    assert {x["source_id"] for x in matrix["records"]} == {
        "rfc-editor-index", "iana-registries", "mit-ocw-6-004-2017"
    }
    assert all(set(item["evidence"]) == {
        "license", "revision", "robots_terms", "notice_ipr", "schema", "provenance",
        "parser", "content_quality",
    } for item in matrix["records"])
    assert all(
        evidence["status"] in EVIDENCE_STATUSES
        for item in matrix["records"] for evidence in item["evidence"].values()
    )
    assert all(
        evidence["status"] == "PENDING"
        for item in matrix["records"] for evidence in item["evidence"].values()
    )


def test_closure_bundle_links_digest_receipts_and_reviews(repo_root):
    matrix, digest, receipts, prior, closure, expected = _bundle(repo_root)
    result = validate_closure_bundle(
        matrix, digest_assets=digest["assets"], receipts=receipts["receipts"],
        reviews=closure["records"], prior_reviews=prior["records"], expected_assets=expected,
    )
    assert result["result"] == "REVIEW_REQUIRED"
    assert {x["asset_id"] for x in result["records"]} >= {"digital_answers", "information_worksheet"}
    assert all(x["decision"] == "DEFER" for x in closure["records"])
    assert all(x["supersedes"] == old["review_id"] for x, old in zip(closure["records"], prior["records"]))
    assert all("m11-p0-evidence-closure-26-v1" in x["evidence_refs"] for x in closure["records"])


def test_closure_is_immutable_and_privacy_safe(repo_root):
    matrix = _load(repo_root, MATRIX)
    original = copy.deepcopy(matrix)
    returned = validate_evidence_closure(matrix)
    returned["records"][0]["evidence"]["license"]["status"] = "VERIFIED"
    assert matrix == original
    bad = copy.deepcopy(matrix)
    bad["records"][0]["host_path"] = "forbidden"
    with pytest.raises(EvidenceClosureError, match="CLOSURE_PRIVACY_FIELD"):
        validate_evidence_closure(bad)


def test_closure_rejects_scope_mutation_and_failed_evidence(repo_root):
    matrix = _load(repo_root, MATRIX)
    bad = copy.deepcopy(matrix)
    bad["records"].pop()
    with pytest.raises(EvidenceClosureError, match="CLOSURE_RECORD_COUNT_INVALID"):
        validate_evidence_closure(bad)
    bad = copy.deepcopy(matrix)
    bad["records"][0]["evidence"]["license"]["status"] = "FAILED"
    with pytest.raises(EvidenceClosureError, match="CLOSURE_FAILED_EVIDENCE"):
        validate_closure_bundle(
            bad, digest_assets=_load(repo_root, DIGEST)["assets"],
            receipts=_load(repo_root, RECEIPTS)["receipts"],
            reviews=_load(repo_root, CLOSURE)["records"],
            prior_reviews=_load(repo_root, PRIOR)["records"],
            expected_assets=[(x["source_id"], x["asset_id"]) for x in _load(repo_root, DIGEST)["assets"]],
        )


def test_closure_remains_blocked_in_legacy_gate_projection(repo_root):
    matrix, digest, receipts, _, closure, expected = _bundle(repo_root)
    status = gate0_status(
        required_assets=expected, reviews=closure["records"],
        acquisition_receipts=receipts["receipts"], authority_present=True,
        scope_digest=matrix["scope_digest"],
    )
    assert status["status"] == "BLOCKED"
    assert status["reviewed_asset_count"] == 0
    assert status["receipt_asset_count"] == 26
    assert status["candidate_promotion_authorized"] is False
    assert status["publication_authorized"] is False
