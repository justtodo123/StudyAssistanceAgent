from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_rfc_schema_review import (
    RfcSchemaReviewError,
    validate_rfc_schema_review_authority,
    validate_rfc_schema_review_result,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "data/manifests"


def load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))


def args() -> tuple[dict, dict]:
    return (
        load("m11-p0-rfc-schema-review-result-v1.json"),
        load("m11-p0-rfc-schema-review-authority-v1.json"),
    )


def test_schema_only_decision_is_valid_and_partial():
    result, authority = args()
    validate_rfc_schema_review_authority(authority)
    validated = validate_rfc_schema_review_result(result, authority=authority)
    assert validated["closed_cell_count"] == 3
    assert validated["pending_cell_count"] == 21
    assert validated["closure_effect"] == "PARTIAL"
    assert validated["successor_slice_written"] is False
    assert {record["schema"]["status"] for record in validated["records"]} == {"NOT_APPLICABLE"}


@pytest.mark.parametrize(
    "mutation",
    (
        lambda result, authority: result.__setitem__("publication_authorized", True),
        lambda result, authority: result.__setitem__("successor_slice_written", True),
        lambda result, authority: result["records"][0]["schema"].__setitem__("status", "VERIFIED"),
        lambda result, authority: result.__setitem__("pending_cell_count", 0),
        lambda result, authority: authority["asset_ids"]["rfc-editor-index"].append("rfc9999"),
        lambda result, authority: authority.__setitem__("operation", "gate0"),
    ),
)
def test_schema_review_mutations_fail_closed(mutation):
    result, authority = args()
    mutation(result, authority)
    with pytest.raises(RfcSchemaReviewError):
        validate_rfc_schema_review_result(result, authority=authority)


def test_validation_returns_detached_copy():
    result, authority = args()
    validated = validate_rfc_schema_review_result(result, authority=authority)
    validated["records"][0]["schema"]["status"] = "changed"
    assert result["records"][0]["schema"]["status"] == "NOT_APPLICABLE"
