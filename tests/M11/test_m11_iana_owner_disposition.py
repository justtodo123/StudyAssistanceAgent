from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.m11_iana_owner_disposition import (
    IanaOwnerDispositionError,
    validate_iana_owner_disposition,
)

ROOT = Path(__file__).resolve().parents[2]
DISPOSITION = ROOT / "data/manifests/m11-p0-iana-owner-disposition-v1.json"
PACKET = ROOT / "data/manifests/m11-p0-iana-evidence-closure-packet-v1.json"
CENSUS = ROOT / "data/manifests/m11-p0-iana-evidence-census-v1.json"
DIGEST_EVIDENCE = ROOT / "data/manifests/m11-p0-digest-evidence-v1.json"
RECEIPT_BATCH = ROOT / "data/manifests/m11-p0-acquisition-26-receipts-v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dependencies() -> dict:
    return {
        "packet": load(PACKET),
        "census": load(CENSUS),
        "digest_evidence": load(DIGEST_EVIDENCE),
        "receipt_batch": load(RECEIPT_BATCH),
    }


def validate(payload: dict) -> dict:
    return validate_iana_owner_disposition(payload, **dependencies())


def test_owner_disposition_is_exact_and_metadata_only():
    result = validate(load(DISPOSITION))
    assert result["owner_decision"]["identity"] == "justtodo123"
    assert result["current_heads"] == {"rfc": "3 ACCEPT", "iana": "3 DEFER", "mit_ocw": "20 DEFER"}
    assert [item["schema_status"] for item in result["records"]] == ["PENDING"] * 3
    assert result["records"][1]["xml_conflict_status"] == "UNRESOLVED"
    assert result["records"][2]["parser_status"] == "FAIL_CLOSED"
    assert all(value is False for value in result["escalation"].values())


@pytest.mark.parametrize(
    "mutation",
    (
        lambda p: p["records"][1].__setitem__("xml_conflict_status", "RESOLVED"),
        lambda p: p["records"][2].__setitem__("parser_status", "VERIFIED"),
        lambda p: p["records"][0].__setitem__("schema_applicable", False),
        lambda p: p["records"][0].__setitem__("schema_status", "NOT_APPLICABLE"),
        lambda p: p["escalation"].__setitem__("authority_issued", True),
        lambda p: p["escalation"].__setitem__("execution_authorized", True),
        lambda p: p["owner_decision"].__setitem__("identity", "other-owner"),
        lambda p: p["owner_decision"]["references"].append("other.json"),
        lambda p: p.__setitem__("current_heads", {"rfc": "3 ACCEPT", "iana": "3 ACCEPT", "mit_ocw": "20 DEFER"}),
        lambda p: p["escalation"].__setitem__("successor_created", True),
    ),
)
def test_mutations_fail_closed(mutation):
    payload = copy.deepcopy(load(DISPOSITION))
    mutation(payload)
    with pytest.raises(IanaOwnerDispositionError):
        validate(payload)


def test_validation_returns_detached_copy_and_does_not_mutate_inputs():
    payload = load(DISPOSITION)
    original = copy.deepcopy(payload)
    result = validate(payload)
    assert payload == original
    result["records"][0]["schema_status"] = "VERIFIED"
    assert payload == original
