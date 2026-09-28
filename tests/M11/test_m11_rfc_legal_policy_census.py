from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_rfc_legal_policy_census import (
    RfcLegalPolicyCensusError,
    validate_rfc_legal_policy_census,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/manifests/m11-p0-rfc-legal-policy-census-v1.json"


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_legal_census_is_valid_and_non_closing():
    payload = validate_rfc_legal_policy_census(load())
    by_asset = {item["asset_id"]: item for item in payload["records"]}
    assert by_asset["rfc1034"]["notice_family"] == "pre-trust-unlimited-distribution"
    assert by_asset["rfc9110"]["notice_family"] == "modern-ietf-trust-bcp78"
    assert by_asset["rfc9293"]["notice_family"] == "modern-ietf-trust-bcp78"
    assert all(item["license_status"] == "PENDING" for item in payload["records"])
    assert payload["authority_issued"] is False
    serialized = json.dumps(payload, sort_keys=True)
    assert "Copyright (c)" not in serialized
    assert "Distribution of this memo" not in serialized


@pytest.mark.parametrize(
    "mutation",
    (
        lambda p: p.__setitem__("authority_issued", True),
        lambda p: p.__setitem__("network_used", True),
        lambda p: p["records"][0].__setitem__("license_status", "VERIFIED"),
        lambda p: p["records"][0].__setitem__("notice_family", "modern-ietf-trust-bcp78"),
        lambda p: p["records"][1].__setitem__("copyright_year", 2021),
        lambda p: p["records"].pop(),
    ),
)
def test_legal_census_mutations_fail_closed(mutation):
    payload = copy.deepcopy(load())
    mutation(payload)
    with pytest.raises(RfcLegalPolicyCensusError):
        validate_rfc_legal_policy_census(payload)


def test_validation_returns_detached_copy():
    payload = load()
    validated = validate_rfc_legal_policy_census(payload)
    validated["records"][0]["notice_family"] = "changed"
    assert payload["records"][0]["notice_family"] != "changed"
