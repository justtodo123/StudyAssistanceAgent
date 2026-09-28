from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_rfc_candidate_materialization import (
    RfcCandidateMaterializationError,
    validate_rfc_candidate_materialization,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/manifests/m11-p0-rfc-candidate-materialization-v1.json"


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_rfc_materialization_checkpoint_is_valid_and_non_promoting():
    payload = validate_rfc_candidate_materialization(load())
    assert payload["asset_ids"] == ["rfc1034", "rfc9110", "rfc9293"]
    assert payload["candidate_asset_count"] == 3
    assert payload["validated_candidate_artifact_count"] == 3
    assert payload["candidate_chunk_count"] == 3
    assert payload["approved_chunk_count"] == 0
    assert payload["counts_toward_3k"] is False


def test_rfc_materialization_uses_current_candidate_identity():
    payload = load()
    assert {item["candidate_digest"] for item in payload["assets"]} == {
        item["revision"] for item in payload["assets"]
    }
    assert len({item["candidate_digest"] for item in payload["assets"]}) == 3
    assert all(item["source_blob_sha1"] is None for item in payload["assets"])


@pytest.mark.parametrize(
    "mutation",
    (
        lambda p: p.__setitem__("candidate_chunk_count", 3000),
        lambda p: p.__setitem__("counts_toward_3k", True),
        lambda p: p.__setitem__("publication_authorized", True),
        lambda p: p["assets"][0].__setitem__("candidate_digest", "f" * 64),
        lambda p: p["assets"][0].__setitem__("candidate_artifact", "C:/private.json"),
        lambda p: p["assets"].pop(),
    ),
)
def test_rfc_materialization_mutations_fail_closed(mutation):
    payload = copy.deepcopy(load())
    mutation(payload)
    with pytest.raises(RfcCandidateMaterializationError):
        validate_rfc_candidate_materialization(payload)


def test_validation_returns_detached_copy():
    payload = load()
    validated = validate_rfc_candidate_materialization(payload)
    validated["assets"][0]["asset_id"] = "changed"
    assert payload["assets"][0]["asset_id"] != "changed"
