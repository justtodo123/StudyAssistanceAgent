from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_rfc_evidence_closure_packet import (
    RfcEvidenceClosurePacketError,
    exact_three_packet_digest,
    validate_rfc_evidence_closure_packet,
)

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "data/manifests/m11-p0-rfc-evidence-closure-packet-draft-v1.json"


def load() -> dict:
    return json.loads(PACKET.read_text(encoding="utf-8"))


def test_packet_is_non_executing_and_all_pending():
    payload = validate_rfc_evidence_closure_packet(load())
    assert payload["authority_issued"] is False
    assert payload["metadata_only"] is True
    assert payload["current_status"] == "REVIEW_REQUIRED"
    assert all(
        status == "PENDING"
        for statuses in payload["proposed_statuses"].values()
        for status in statuses.values()
    )


def test_packet_digest_is_order_independent_and_identity_bound():
    payload = load()
    assert exact_three_packet_digest(payload["batch_records"]) == payload["batch_digest"]
    assert exact_three_packet_digest(list(reversed(payload["batch_records"]))) == payload["batch_digest"]
    changed = copy.deepcopy(payload["batch_records"])
    changed[0]["chunk_count"] += 1
    assert exact_three_packet_digest(changed) != payload["batch_digest"]


@pytest.mark.parametrize(
    "mutation",
    (
        lambda p: p.__setitem__("authority_issued", True),
        lambda p: p.__setitem__("publication_authorized", True),
        lambda p: p["proposed_statuses"]["rfc1034"].__setitem__("schema", "NOT_APPLICABLE"),
        lambda p: p["batch_records"].pop(),
        lambda p: p["batch_records"][0].__setitem__("document_id", None),
    ),
)
def test_packet_mutations_fail_closed(mutation):
    payload = copy.deepcopy(load())
    mutation(payload)
    with pytest.raises(RfcEvidenceClosurePacketError):
        validate_rfc_evidence_closure_packet(payload)


def test_validation_returns_detached_copy():
    payload = load()
    validated = validate_rfc_evidence_closure_packet(payload)
    validated["proposed_statuses"]["rfc1034"]["schema"] = "changed"
    assert payload["proposed_statuses"]["rfc1034"]["schema"] == "PENDING"
