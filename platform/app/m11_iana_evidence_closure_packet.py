"""Non-executing IANA exact-three owner decision-input packet."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

from .m11_acquisition import AcquisitionError, validate_receipt

SCHEMA = "sa.m11.p0.iana-evidence-closure-packet.v1"
SOURCE_ID = "iana-registries"
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
DIGEST_EVIDENCE_DIGEST = "a6503d2629414759ea6bce97190a991a5a4797e2ab9fcb2325849be7c1d23425"
RECEIPT_BATCH_DIGEST = "0a7d9184d30546b9bc5713bc564f43b2b9712515abfc8547de2911a3fa6c7431"
ASSETS = (
    "service-names-port-numbers-csv",
    "service-names-port-numbers-xml",
    "service-names-port-numbers-txt",
)
CATEGORIES = (
    "license", "revision", "robots_terms", "notice_ipr", "schema", "provenance",
    "parser", "content_quality",
)
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class IanaEvidenceClosurePacketError(ValueError):
    """The IANA decision-input packet is malformed or escalates scope."""


def _fail(code: str) -> NoReturn:
    raise IanaEvidenceClosurePacketError(code)


def _digest(value: Any) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail("IANA_PACKET_DIGEST_INVALID")
    return value


def _receipt_digest(receipt: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(receipt), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _payload_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validated_dependencies(
    digest_evidence: Mapping[str, Any], receipt_batch: Mapping[str, Any]
) -> dict[str, dict[str, str]]:
    if _payload_digest(digest_evidence) != DIGEST_EVIDENCE_DIGEST:
        _fail("IANA_PACKET_DIGEST_DEPENDENCY_INVALID")
    if (
        not isinstance(digest_evidence, Mapping)
        or digest_evidence.get("schema") != "sa.m11.p0-digest-evidence.v1"
        or digest_evidence.get("status") != "DIGESTS_CAPTURED_CANDIDATE_PIPELINE_AUTHORIZED"
        or digest_evidence.get("asset_count") != 26
        or not isinstance(digest_evidence.get("assets"), list)
    ):
        _fail("IANA_PACKET_DIGEST_DEPENDENCY_INVALID")
    digest_by_asset: dict[str, Mapping[str, Any]] = {}
    for item in digest_evidence["assets"]:
        if not isinstance(item, Mapping):
            _fail("IANA_PACKET_DIGEST_DEPENDENCY_INVALID")
        if item.get("source_id") == SOURCE_ID and item.get("asset_id") in ASSETS:
            asset = item["asset_id"]
            if asset in digest_by_asset or not _HEX.fullmatch(str(item.get("sha256", ""))):
                _fail("IANA_PACKET_DIGEST_DEPENDENCY_INVALID")
            digest_by_asset[asset] = item
    if set(digest_by_asset) != set(ASSETS):
        _fail("IANA_PACKET_DIGEST_DEPENDENCY_INVALID")

    if _payload_digest(receipt_batch) != RECEIPT_BATCH_DIGEST:
        _fail("IANA_PACKET_RECEIPT_DEPENDENCY_INVALID")
    if (
        not isinstance(receipt_batch, Mapping)
        or receipt_batch.get("schema") != "sa.m11.p0.acquisition-receipt-batch.v1"
        or receipt_batch.get("scope_digest") != SCOPE_DIGEST
        or receipt_batch.get("asset_count") != 26
        or receipt_batch.get("decision") != "ACQUIRED"
        or not isinstance(receipt_batch.get("receipts"), list)
    ):
        _fail("IANA_PACKET_RECEIPT_DEPENDENCY_INVALID")
    receipt_by_asset: dict[str, Mapping[str, Any]] = {}
    for item in receipt_batch["receipts"]:
        try:
            validated = validate_receipt(item)
        except (AcquisitionError, TypeError, ValueError) as exc:
            raise IanaEvidenceClosurePacketError(
                "IANA_PACKET_RECEIPT_DEPENDENCY_INVALID"
            ) from exc
        if validated.source_id == SOURCE_ID and validated.asset_id in ASSETS:
            if validated.asset_id in receipt_by_asset or validated.status != "ACQUIRED":
                _fail("IANA_PACKET_RECEIPT_DEPENDENCY_INVALID")
            receipt_by_asset[validated.asset_id] = item
    if set(receipt_by_asset) != set(ASSETS):
        _fail("IANA_PACKET_RECEIPT_DEPENDENCY_INVALID")

    linked: dict[str, dict[str, str]] = {}
    for asset in ASSETS:
        digest_item = digest_by_asset[asset]
        receipt = receipt_by_asset[asset]
        candidate_digest = str(digest_item["sha256"])
        if (
            receipt.get("sha256") != candidate_digest
            or receipt.get("revision") != candidate_digest
            or receipt.get("canonical_url") != digest_item.get("url")
            or receipt.get("bytes") != digest_item.get("bytes")
        ):
            _fail("IANA_PACKET_DEPENDENCY_LINK_INVALID")
        linked[asset] = {
            "candidate_digest": candidate_digest,
            "receipt_digest": _receipt_digest(receipt),
            "revision": str(receipt["revision"]),
        }
    return linked


def exact_three_packet_digest(records: Sequence[Mapping[str, Any]]) -> str:
    canonical = []
    for item in sorted(records, key=lambda value: value["asset_id"]):
        if set(item) != {
            "source_id", "asset_id", "candidate_digest", "receipt_digest", "revision",
        }:
            _fail("IANA_PACKET_RECORD_FIELDS_INVALID")
        if item["source_id"] != SOURCE_ID or item["asset_id"] not in ASSETS:
            _fail("IANA_PACKET_SCOPE_INVALID")
        canonical.append(dict(item))
    if len(canonical) != 3 or {item["asset_id"] for item in canonical} != set(ASSETS):
        _fail("IANA_PACKET_SCOPE_INVALID")
    encoded = json.dumps(
        {"domain": "sa.m11.p0.iana-evidence-closure.batch.v2", "parent_scope_digest": SCOPE_DIGEST,
         "records": canonical}, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_iana_evidence_closure_packet(
    payload: Mapping[str, Any],
    *,
    digest_evidence: Mapping[str, Any],
    receipt_batch: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate owner inputs against tracked digest and acquisition dependencies."""
    required = {
        "schema", "packet_id", "scope_digest", "operation", "metadata_only", "authority_issued",
        "application_id", "source_manifest", "receipt_manifest", "batch_records", "batch_digest",
        "proposed_statuses", "current_heads", "current_status", "formal_gate0_executed",
        "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion",
        "lifecycle_mutation", "host_paths_included", "bodies_included",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("IANA_PACKET_FIELDS_INVALID")
    if payload["schema"] != SCHEMA or payload["scope_digest"] != SCOPE_DIGEST or payload["operation"] != "owner_decision_inputs":
        _fail("IANA_PACKET_IDENTITY_INVALID")
    if payload["metadata_only"] is not True or payload["authority_issued"] is not False:
        _fail("IANA_PACKET_AUTHORITY_ESCALATION")
    if payload["source_manifest"] != "data/manifests/m11-p0-digest-evidence-v1.json" or payload["receipt_manifest"] != "data/manifests/m11-p0-acquisition-26-receipts-v1.json":
        _fail("IANA_PACKET_LINK_INVALID")
    expected_links = _validated_dependencies(digest_evidence, receipt_batch)
    if payload["current_status"] != "REVIEW_REQUIRED" or payload["formal_gate0_executed"] is not False:
        _fail("IANA_PACKET_CURRENT_STATE_INVALID")
    if payload["current_heads"] != {"rfc": "3 ACCEPT", "iana": "3 DEFER", "mit_ocw": "20 DEFER"}:
        _fail("IANA_PACKET_HEADS_INVALID")
    flags = ("candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")
    if any(payload[field] is not False for field in flags):
        _fail("IANA_PACKET_ESCALATION_FORBIDDEN")
    records = payload["batch_records"]
    if not isinstance(records, list) or len(records) != 3:
        _fail("IANA_PACKET_RECORDS_INVALID")
    for item in records:
        if not isinstance(item, Mapping):
            _fail("IANA_PACKET_RECORDS_INVALID")
        if set(item) != {"source_id", "asset_id", "candidate_digest", "receipt_digest", "revision"}:
            _fail("IANA_PACKET_RECORD_FIELDS_INVALID")
        asset = item.get("asset_id")
        if item.get("source_id") != SOURCE_ID or asset not in expected_links:
            _fail("IANA_PACKET_SCOPE_INVALID")
        for field in ("candidate_digest", "receipt_digest", "revision"):
            _digest(item[field])
        if any(item[field] != expected_links[asset][field] for field in expected_links[asset]):
            _fail("IANA_PACKET_DEPENDENCY_LINK_INVALID")
    if exact_three_packet_digest(records) != payload["batch_digest"]:
        _fail("IANA_PACKET_BATCH_DIGEST_INVALID")
    statuses = payload["proposed_statuses"]
    if not isinstance(statuses, Mapping) or set(statuses) != set(ASSETS):
        _fail("IANA_PACKET_STATUS_SCOPE_INVALID")
    for asset in ASSETS:
        if set(statuses[asset]) != set(CATEGORIES) or any(statuses[asset][category] != "PENDING" for category in CATEGORIES):
            _fail("IANA_PACKET_STATUS_MUST_REMAIN_PENDING")
    return copy.deepcopy(dict(payload))
