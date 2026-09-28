from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_rfc_content_quality_sampling import (
    RfcContentQualitySamplingError,
    validate_rfc_content_quality_sampling,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/manifests/m11-p0-rfc-content-quality-sampling-v1.json"


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_sampling_checkpoint_is_valid_and_non_closing():
    payload = validate_rfc_content_quality_sampling(load())
    assert payload["candidate_chunk_count"] == 3
    assert payload["sampling_plan"]["mode"] == "census"
    assert payload["content_quality_status"] == "PENDING"
    assert {item["content_quality_status"] for item in payload["assets"]} == {"PENDING"}
    assert payload["approved_chunk_count"] == 0
    assert payload["counts_toward_3k"] is False


@pytest.mark.parametrize(
    "mutation",
    (
        lambda p: p.__setitem__("content_quality_status", "VERIFIED"),
        lambda p: p["assets"][0].__setitem__("content_quality_status", "VERIFIED"),
        lambda p: p.__setitem__("counts_toward_3k", True),
        lambda p: p.__setitem__("publication_authorized", True),
        lambda p: p["sampling_plan"].__setitem__("body_persisted", True),
        lambda p: p["assets"][0].__setitem__("unit_kind", "section"),
        lambda p: p["assets"][0].__setitem__("candidate_artifact", "C:/private.json"),
        lambda p: p["assets"].pop(),
    ),
)
def test_sampling_mutations_fail_closed(mutation):
    payload = copy.deepcopy(load())
    mutation(payload)
    with pytest.raises(RfcContentQualitySamplingError):
        validate_rfc_content_quality_sampling(payload)


def test_validation_returns_detached_copy():
    payload = load()
    validated = validate_rfc_content_quality_sampling(payload)
    validated["assets"][0]["content_quality_status"] = "changed"
    assert payload["assets"][0]["content_quality_status"] == "PENDING"
