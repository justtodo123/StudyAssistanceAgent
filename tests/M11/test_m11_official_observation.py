from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.m11_official_observation import (
    OfficialObservationError,
    load_official_source_observation,
    validate_official_observation_bundle,
    validate_official_source_observation,
)

pytestmark = pytest.mark.m11

OBSERVATION = Path("data/manifests/m11-p0-official-source-observations-26-v1.json")
DIGEST = Path("data/manifests/m11-p0-digest-evidence-v1.json")
RECEIPTS = Path("data/manifests/m11-p0-acquisition-26-receipts-v1.json")
CLOSURE = Path("data/manifests/m11-p0-evidence-closure-26-v1.json")
PRIOR = Path("data/manifests/m11-p0-human-review-closure-defer-26-v1.json")
SUCCESSOR = Path("data/manifests/m11-p0-human-review-official-observation-defer-26-v1.json")


def _load(repo_root: Path, path: Path) -> dict:
    return json.loads((repo_root / path).read_text(encoding="utf-8"))


def _bundle(repo_root: Path):
    observation = _load(repo_root, OBSERVATION)
    digest = _load(repo_root, DIGEST)
    receipts = _load(repo_root, RECEIPTS)
    closure = _load(repo_root, CLOSURE)
    prior = _load(repo_root, PRIOR)
    successor = _load(repo_root, SUCCESSOR)
    authority = _load(repo_root, Path(observation["authority_record"]))
    prior_wrapper = _load(repo_root, Path(observation["prior_review_record"]))
    expected = [(item["source_id"], item["asset_id"]) for item in digest["assets"]]
    return observation, digest, receipts, closure, prior, successor, authority, prior_wrapper, expected


def test_official_observation_bundle_is_valid_and_non_closing(repo_root):
    observation, digest, receipts, closure, prior, successor, authority, prior_wrapper, expected = _bundle(repo_root)
    result = validate_official_observation_bundle(
        observation,
        digest_assets=digest["assets"],
        receipts=receipts["receipts"],
        closure_matrix=closure,
        closure_reviews=prior["records"],
        successor_reviews=successor["records"],
        expected_assets=expected,
        authority=authority,
        successor_wrapper=successor,
        prior_review_wrapper=prior_wrapper,
        robots=digest["robots"],
    )
    assert result["asset_count"] == 26
    assert result["result"] == "REVIEW_REQUIRED"
    assert len(result["source_observations"]) == 9
    assert any(item["kind"] == "SCHEMA_METADATA_CONFLICT" and item["status"] == "UNRESOLVED" for item in result["source_observations"])
    assert any(item["kind"] == "SOURCE_POLICY_LIMITATION" and item["status"] == "UNRESOLVED" for item in result["source_observations"])
    assert all(item["closure_state"] == "PENDING_UNCHANGED" for item in result["asset_links"])
    assert all(item["review_outcome"] == "DEFER" for item in result["asset_links"])


def test_observation_manifest_is_immutable_and_privacy_safe(repo_root):
    payload = _load(repo_root, OBSERVATION)
    original = copy.deepcopy(payload)
    returned = validate_official_source_observation(payload)
    returned["asset_links"][0]["closure_state"] = "VERIFIED"
    assert payload == original
    loaded = load_official_source_observation(repo_root / OBSERVATION)
    assert loaded == original
    bad = copy.deepcopy(payload)
    bad["source_observations"][0]["facts"][0]["value"] = {"host_path": "forbidden"}
    with pytest.raises(OfficialObservationError, match="OBSERVATION_PRIVACY_FIELD"):
        validate_official_source_observation(bad)


def test_observation_requires_source_local_finding_applicability(repo_root):
    observation, digest, receipts, closure, prior, successor, authority, prior_wrapper, expected = _bundle(repo_root)
    bad = copy.deepcopy(observation)
    link = bad["asset_links"][0]
    finding = next(item for item in bad["source_observations"] if item["finding_id"] == link["observation_refs"][0])
    finding["source_id"] = "iana-registries"
    with pytest.raises(OfficialObservationError, match="OBSERVATION_APPLICABILITY_INVALID"):
        validate_official_observation_bundle(
            bad,
            digest_assets=digest["assets"],
            receipts=receipts["receipts"],
            closure_matrix=closure,
            closure_reviews=prior["records"],
            successor_reviews=successor["records"],
            expected_assets=expected,
            authority=authority,
            successor_wrapper=successor,
            prior_review_wrapper=prior_wrapper,
            robots=digest["robots"],
        )


def test_observation_rejects_scope_mutation_and_successor_mismatch(repo_root):
    observation, digest, receipts, closure, prior, successor, authority, prior_wrapper, expected = _bundle(repo_root)
    bad = copy.deepcopy(observation)
    bad["asset_links"].pop()
    with pytest.raises(OfficialObservationError, match="OBSERVATION_LINK_COUNT_INVALID"):
        validate_official_source_observation(bad)
    bad_successor = copy.deepcopy(successor)
    bad_successor["records"][0]["decision"] = "ACCEPT_FOR_PROMOTION_REVIEW"
    with pytest.raises(OfficialObservationError, match="OBSERVATION_SUCCESSOR_NOT_DEFERRED"):
        validate_official_observation_bundle(
            observation,
            digest_assets=digest["assets"],
            receipts=receipts["receipts"],
            closure_matrix=closure,
            closure_reviews=prior["records"],
            successor_reviews=bad_successor["records"],
            expected_assets=expected,
            authority=authority,
            successor_wrapper=successor,
            prior_review_wrapper=prior_wrapper,
            robots=digest["robots"],
        )
