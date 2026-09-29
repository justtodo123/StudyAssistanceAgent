from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_rfc_technical_evidence_review import (
    RfcTechnicalEvidenceReviewError,
    validate_rfc_technical_result,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "data/manifests"


def load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))


def args() -> tuple[dict, dict, dict]:
    return (
        load("m11-p0-rfc-technical-evidence-review-result-v1.json"),
        load("m11-p0-rfc-technical-evidence-review-authority-v1.json"),
        load("m11-p0-rfc-schema-review-result-v1.json"),
    )


def test_cumulative_rfc_evidence_is_partial_and_non_promoting():
    result, authority, schema_result = args()
    validated = validate_rfc_technical_result(result, authority=authority, schema_result=schema_result)
    assert validated["verified_cell_count"] == 9
    assert validated["not_applicable_cell_count"] == 3
    assert validated["pending_cell_count"] == 12
    assert validated["closed_cell_count"] == 12
    assert validated["successor_slice_written"] is False
    assert {item[category]["status"] for item in validated["records"] for category in ("revision", "provenance", "parser")} == {"VERIFIED"}


@pytest.mark.parametrize(
    "mutation",
    (
        lambda r, a, s: r.__setitem__("publication_authorized", True),
        lambda r, a, s: r.__setitem__("successor_slice_written", True),
        lambda r, a, s: r["records"][0]["parser"].__setitem__("status", "PENDING"),
        lambda r, a, s: r.__setitem__("pending_cell_count", 0),
        lambda r, a, s: a.__setitem__("operation", "gate0"),
        lambda r, a, s: s.__setitem__("result_id", "unrelated"),
    ),
)
def test_technical_evidence_mutations_fail_closed(mutation):
    result, authority, schema_result = args()
    mutation(result, authority, schema_result)
    with pytest.raises(RfcTechnicalEvidenceReviewError):
        validate_rfc_technical_result(result, authority=authority, schema_result=schema_result)


def test_validation_returns_detached_copy():
    result, authority, schema_result = args()
    validated = validate_rfc_technical_result(result, authority=authority, schema_result=schema_result)
    validated["records"][0]["parser"]["status"] = "changed"
    assert result["records"][0]["parser"]["status"] == "VERIFIED"
