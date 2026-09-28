from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_mit_ocw_candidate_materialization import (
    MitOcwCandidateMaterializationError,
    validate_mit_ocw_candidate_materialization,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/manifests/m11-p0-mit-ocw-candidate-materialization-v1.json"


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_materialization_checkpoint_is_valid_and_non_promoting():
    payload = validate_mit_ocw_candidate_materialization(load())
    assert payload["input_asset_count"] == 20
    assert payload["candidate_asset_count"] == 18
    assert payload["rejected_asset_count"] == 2
    assert payload["validated_candidate_artifact_count"] == 18
    assert payload["candidate_chunk_count"] == 93
    assert payload["approved_document_count"] == 0
    assert payload["approved_chunk_count"] == 0
    assert payload["counts_toward_3k"] is False
    assert payload["formal_gate0_executed"] is False
    assert payload["publication_authorized"] is False


def test_materialization_partition_and_reasons_are_frozen():
    payload = load()
    rejected = {item["asset_id"]: item["reason"] for item in payload["rejections"]}
    assert rejected == {
        "digital_answers": "SOURCE_PARSE_FAILED",
        "information_worksheet": "INVALID_CANDIDATE_INPUT",
    }
    assert len({item["asset_id"] for item in payload["assets"]}) == 18
    validate_mit_ocw_candidate_materialization(payload)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda p: p.__setitem__("candidate_chunk_count", 3000),
        lambda p: p.__setitem__("counts_toward_3k", True),
        lambda p: p.__setitem__("publication_authorized", True),
        lambda p: p.__setitem__("approved_chunk_count", 93),
        lambda p: p["assets"][0].__setitem__("status", "APPROVED"),
        lambda p: p["assets"][0].__setitem__("candidate_artifact", "C:/private.json"),
        lambda p: p["rejections"][0].__setitem__("reason", "NONE"),
    ),
)
def test_materialization_mutations_fail_closed(mutation):
    payload = copy.deepcopy(load())
    mutation(payload)
    with pytest.raises(MitOcwCandidateMaterializationError):
        validate_mit_ocw_candidate_materialization(payload)


def test_validation_returns_detached_copy():
    payload = load()
    validated = validate_mit_ocw_candidate_materialization(payload)
    validated["assets"][0]["asset_id"] = "changed"
    assert payload["assets"][0]["asset_id"] != "changed"
