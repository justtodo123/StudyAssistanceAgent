from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_iana_evidence_census import (
    IanaEvidenceCensusError,
    census_iana_evidence,
    validate_iana_evidence_census,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/manifests/m11-p0-iana-evidence-census-v1.json"
RAW_ROOT = ROOT / "data/raw/iana-registries"
DIGEST_EVIDENCE = ROOT / "data/manifests/m11-p0-digest-evidence-v1.json"
RECEIPT_BATCH = ROOT / "data/manifests/m11-p0-acquisition-26-receipts-v1.json"


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def dependencies() -> tuple[dict, dict]:
    return (
        json.loads(DIGEST_EVIDENCE.read_text(encoding="utf-8")),
        json.loads(RECEIPT_BATCH.read_text(encoding="utf-8")),
    )


def validate(payload: dict) -> dict:
    digest_evidence, receipt_batch = dependencies()
    return validate_iana_evidence_census(
        payload, digest_evidence=digest_evidence, receipt_batch=receipt_batch
    )


def test_census_is_valid_non_closing_and_schema_applicable():
    payload = validate(load())
    assert payload["xml_conflict"] == {
        "asset_id": "service-names-port-numbers-xml",
        "status": "UNRESOLVED",
        "live_updated_date": "2024-12-20",
        "frozen_manifest_updated_date": "2026-09-11",
        "closure_effect": "NONE",
    }
    assert all(item["schema_applicable"] is True for item in payload["records"])
    assert all(item["robots_policy"] == "allow-all" for item in payload["records"])
    assert all(item["cc0_observation"] == "CC0-1.0-direct-protocol-registry-data" for item in payload["records"])
    statuses = [value for item in payload["records"] for key, value in item.items() if key.endswith("_status")]
    assert statuses == ["PENDING"] * 24


def test_local_census_matches_tracked_metadata_without_mutating_raw_inputs():
    before = {path: path.read_bytes() for path in RAW_ROOT.glob("service-names-port-numbers-*.raw")}
    digest_evidence, receipt_batch = dependencies()
    observed = census_iana_evidence(
        raw_root=RAW_ROOT,
        digest_evidence=digest_evidence,
        receipt_batch=receipt_batch,
    )
    tracked = load()
    assert observed["records"] == tracked["records"]
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize(
    "mutation",
    (
        lambda p: p.__setitem__("authority_issued", True),
        lambda p: p.__setitem__("formal_gate0_executed", True),
        lambda p: p["xml_conflict"].__setitem__("status", "RESOLVED"),
        lambda p: p["xml_conflict"].__setitem__("live_updated_date", "2026-09-11"),
        lambda p: p["records"][0].__setitem__("robots_policy", "unknown"),
        lambda p: p["records"][1].__setitem__("schema_applicable", False),
        lambda p: p["records"][2].__setitem__("schema_status", "NOT_APPLICABLE"),
        lambda p: p["records"].pop(),
        lambda p: p["records"][0].__setitem__("raw_sha256", "0" * 64),
    ),
)
def test_census_mutations_fail_closed(mutation):
    payload = copy.deepcopy(load())
    mutation(payload)
    with pytest.raises(IanaEvidenceCensusError):
        validate(payload)


def test_census_is_metadata_only_private_and_detached():
    payload = load()
    serialized = json.dumps(payload, sort_keys=True)
    assert "D:/" not in serialized and "D:\\" not in serialized
    assert '"body"' not in serialized and '"content"' not in serialized
    validated = validate(payload)
    validated["records"][0]["schema_observation"] = "changed"
    assert payload["records"][0]["schema_observation"] != "changed"


@pytest.mark.parametrize("dependency", ("digest", "receipt"))
def test_census_rejects_mutated_dependency_payloads(dependency):
    payload = load()
    digest_evidence, receipt_batch = dependencies()
    if dependency == "digest":
        next(
            item for item in digest_evidence["assets"]
            if item["asset_id"] == "service-names-port-numbers-xml"
        )["sha256"] = "f" * 64
    else:
        next(
            item for item in receipt_batch["receipts"]
            if item["asset_id"] == "service-names-port-numbers-xml"
        )["sha256"] = "f" * 64
    with pytest.raises(IanaEvidenceCensusError):
        validate_iana_evidence_census(
            payload, digest_evidence=digest_evidence, receipt_batch=receipt_batch
        )
