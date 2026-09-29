from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_rfc_content_quality_review import (
    RfcContentQualityReviewError,
    validate_rfc_content_quality_result,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "data/manifests"


def load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))


def args() -> tuple[dict, dict, dict, dict, dict]:
    return (
        load("m11-p0-rfc-content-quality-review-result-v1.json"),
        load("m11-p0-rfc-content-quality-review-authority-v1.json"),
        load("m11-p0-rfc-content-quality-sampling-result-v1.json"),
        load("m11-p0-rfc-technical-evidence-review-result-v1.json"),
        load("m11-p0-rfc-schema-review-result-v1.json"),
    )


def test_content_quality_owner_result_is_valid_and_partial():
    result, authority, sampling, technical, schema = args()
    validated = validate_rfc_content_quality_result(result, authority=authority, sampling_result=sampling, technical_result=technical, schema_result=schema)
    assert validated["verified_cell_count"] == 12
    assert validated["not_applicable_cell_count"] == 3
    assert validated["pending_cell_count"] == 9
    assert validated["successor_slice_written"] is False
    assert {item["content_quality"]["status"] for item in validated["records"]} == {"VERIFIED"}


@pytest.mark.parametrize(
    "mutation",
    (
        lambda r, a, s, t, sc: r.__setitem__("publication_authorized", True),
        lambda r, a, s, t, sc: r.__setitem__("successor_slice_written", True),
        lambda r, a, s, t, sc: r["records"][0]["content_quality"].__setitem__("status", "PENDING"),
        lambda r, a, s, t, sc: r.__setitem__("pending_cell_count", 0),
        lambda r, a, s, t, sc: a.__setitem__("operation", "gate0"),
        lambda r, a, s, t, sc: s.__setitem__("technical_sampling_status", "FAILED"),
    ),
)
def test_content_quality_mutations_fail_closed(mutation):
    result, authority, sampling, technical, schema = args()
    mutation(result, authority, sampling, technical, schema)
    with pytest.raises(RfcContentQualityReviewError):
        validate_rfc_content_quality_result(result, authority=authority, sampling_result=sampling, technical_result=technical, schema_result=schema)


def test_validation_returns_detached_copy():
    result, authority, sampling, technical, schema = args()
    validated = validate_rfc_content_quality_result(result, authority=authority, sampling_result=sampling, technical_result=technical, schema_result=schema)
    validated["records"][0]["content_quality"]["status"] = "changed"
    assert result["records"][0]["content_quality"]["status"] == "VERIFIED"
