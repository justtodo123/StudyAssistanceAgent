from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_rfc_legal_policy_review import (
    RfcLegalPolicyReviewError,
    validate_rfc_legal_policy_result,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "data/manifests"


def load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))


def args() -> tuple[dict, dict, dict, dict]:
    return (
        load("m11-p0-rfc-legal-policy-review-result-v1.json"),
        load("m11-p0-rfc-legal-policy-review-authority-v1.json"),
        load("m11-p0-rfc-legal-policy-census-v1.json"),
        load("m11-p0-rfc-content-quality-review-result-v1.json"),
    )


def test_legal_policy_result_completes_all_evidence_without_successor():
    result, authority, census, quality = args()
    validated = validate_rfc_legal_policy_result(result, authority=authority, census=census, content_quality_result=quality)
    assert validated["verified_cell_count"] == 21
    assert validated["not_applicable_cell_count"] == 3
    assert validated["pending_cell_count"] == 0
    assert validated["closure_effect"] == "COMPLETE"
    assert validated["successor_slice_written"] is False


@pytest.mark.parametrize(
    "mutation",
    (
        lambda r, a, c, q: r.__setitem__("publication_authorized", True),
        lambda r, a, c, q: r.__setitem__("successor_slice_written", True),
        lambda r, a, c, q: r["records"][0]["license"].__setitem__("status", "PENDING"),
        lambda r, a, c, q: r.__setitem__("pending_cell_count", 1),
        lambda r, a, c, q: a.__setitem__("operation", "gate0"),
        lambda r, a, c, q: c.__setitem__("census_id", "unrelated"),
    ),
)
def test_legal_policy_mutations_fail_closed(mutation):
    result, authority, census, quality = args()
    mutation(result, authority, census, quality)
    with pytest.raises(RfcLegalPolicyReviewError):
        validate_rfc_legal_policy_result(result, authority=authority, census=census, content_quality_result=quality)


def test_validation_returns_detached_copy():
    result, authority, census, quality = args()
    validated = validate_rfc_legal_policy_result(result, authority=authority, census=census, content_quality_result=quality)
    validated["records"][0]["license"]["status"] = "changed"
    assert result["records"][0]["license"]["status"] == "VERIFIED"
