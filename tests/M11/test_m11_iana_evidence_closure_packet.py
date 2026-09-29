from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_iana_evidence_closure_packet import (
    IanaEvidenceClosurePacketError,
    _receipt_digest,
    exact_three_packet_digest,
    validate_iana_evidence_closure_packet,
)

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "data/manifests/m11-p0-iana-evidence-closure-packet-v1.json"
DIGEST_EVIDENCE = ROOT / "data/manifests/m11-p0-digest-evidence-v1.json"
RECEIPT_BATCH = ROOT / "data/manifests/m11-p0-acquisition-26-receipts-v1.json"


def load() -> dict:
    return json.loads(PACKET.read_text(encoding="utf-8"))


def dependencies() -> tuple[dict, dict]:
    return (
        json.loads(DIGEST_EVIDENCE.read_text(encoding="utf-8")),
        json.loads(RECEIPT_BATCH.read_text(encoding="utf-8")),
    )


def validate(payload: dict) -> dict:
    digest_evidence, receipt_batch = dependencies()
    return validate_iana_evidence_closure_packet(
        payload, digest_evidence=digest_evidence, receipt_batch=receipt_batch
    )


def test_packet_is_exact_three_non_executing_and_all_pending():
    payload = validate(load())
    assert [item["asset_id"] for item in payload["batch_records"]] == [
        "service-names-port-numbers-csv",
        "service-names-port-numbers-xml",
        "service-names-port-numbers-txt",
    ]
    assert payload["authority_issued"] is False
    assert payload["metadata_only"] is True
    assert payload["current_heads"] == {
        "rfc": "3 ACCEPT", "iana": "3 DEFER", "mit_ocw": "20 DEFER"
    }
    assert all(
        status == "PENDING"
        for statuses in payload["proposed_statuses"].values()
        for status in statuses.values()
    )
    assert sum(len(statuses) for statuses in payload["proposed_statuses"].values()) == 24


def test_packet_digest_and_manifest_linkage_are_exact():
    payload = load()
    assert exact_three_packet_digest(payload["batch_records"]) == payload["batch_digest"]
    assert exact_three_packet_digest(list(reversed(payload["batch_records"]))) == payload["batch_digest"]
    assert payload["source_manifest"] == "data/manifests/m11-p0-digest-evidence-v1.json"
    assert payload["receipt_manifest"] == "data/manifests/m11-p0-acquisition-26-receipts-v1.json"


@pytest.mark.parametrize(
    "mutation",
    (
        lambda p: p.__setitem__("authority_issued", True),
        lambda p: p.__setitem__("lifecycle_mutation", True),
        lambda p: p.__setitem__("publication_authorized", True),
        lambda p: p["current_heads"].__setitem__("iana", "3 ACCEPT"),
        lambda p: p["proposed_statuses"]["service-names-port-numbers-xml"].__setitem__(
            "schema", "NOT_APPLICABLE"
        ),
        lambda p: p["batch_records"].pop(),
        lambda p: p["batch_records"][0].__setitem__("receipt_digest", "0" * 64),
        lambda p: p.__setitem__("owner_verdict", "ACCEPT"),
    ),
)
def test_packet_mutations_fail_closed(mutation):
    payload = copy.deepcopy(load())
    mutation(payload)
    with pytest.raises(IanaEvidenceClosurePacketError):
        validate(payload)


def test_packet_has_no_bodies_host_paths_or_review_authority():
    serialized = json.dumps(load(), sort_keys=True)
    assert "D:/" not in serialized and "D:\\" not in serialized
    assert '"body"' not in serialized and '"content"' not in serialized
    assert "reviewer_id" not in serialized and "signed_at" not in serialized
    assert "successor" not in serialized and "promotion" not in serialized


def test_validation_returns_detached_copy_and_input_file_is_unchanged():
    before = PACKET.read_bytes()
    payload = load()
    validated = validate(payload)
    validated["proposed_statuses"]["service-names-port-numbers-csv"]["schema"] = "changed"
    assert payload["proposed_statuses"]["service-names-port-numbers-csv"]["schema"] == "PENDING"
    assert PACKET.read_bytes() == before


@pytest.mark.parametrize("field", ("candidate_digest", "receipt_digest", "revision"))
def test_packet_rejects_recomputed_batch_digest_with_mutated_link(field):
    payload = copy.deepcopy(load())
    payload["batch_records"][0][field] = "f" * 64
    payload["batch_digest"] = exact_three_packet_digest(payload["batch_records"])
    with pytest.raises(IanaEvidenceClosurePacketError):
        validate(payload)


def test_packet_rejects_receipt_dependency_reseal():
    payload = load()
    digest_evidence, receipt_batch = dependencies()
    receipt = next(
        item for item in receipt_batch["receipts"]
        if item["asset_id"] == "service-names-port-numbers-csv"
    )
    receipt["captured_at"] = "2026-09-26T14:00:01+00:00"
    payload["batch_records"][0]["receipt_digest"] = _receipt_digest(receipt)
    payload["batch_digest"] = exact_three_packet_digest(payload["batch_records"])
    with pytest.raises(IanaEvidenceClosurePacketError):
        validate_iana_evidence_closure_packet(
            payload, digest_evidence=digest_evidence, receipt_batch=receipt_batch
        )


@pytest.mark.parametrize("dependency", ("digest", "receipt"))
def test_packet_rejects_mutated_dependency_payloads(dependency):
    payload = load()
    digest_evidence, receipt_batch = dependencies()
    if dependency == "digest":
        next(
            item for item in digest_evidence["assets"]
            if item["asset_id"] == "service-names-port-numbers-csv"
        )["sha256"] = "f" * 64
    else:
        next(
            item for item in receipt_batch["receipts"]
            if item["asset_id"] == "service-names-port-numbers-csv"
        )["revision"] = "f" * 64
    with pytest.raises(IanaEvidenceClosurePacketError):
        validate_iana_evidence_closure_packet(
            payload, digest_evidence=digest_evidence, receipt_batch=receipt_batch
        )
