"""Non-executing RFC exact-three closure review packet."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

SCHEMA = "sa.m11.p0.rfc-evidence-closure-packet.v1"
SOURCE_ID = "rfc-editor-index"
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
ASSETS = ("rfc1034", "rfc9110", "rfc9293")
CATEGORIES = ("license", "revision", "robots_terms", "notice_ipr", "schema", "provenance", "parser", "content_quality")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class RfcEvidenceClosurePacketError(ValueError):
    """The non-executing RFC closure packet is malformed or escalates scope."""


def _fail(code: str) -> NoReturn:
    raise RfcEvidenceClosurePacketError(code)


def _digest(value: Any) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail("RFC_PACKET_DIGEST_INVALID")
    return value


def exact_three_packet_digest(records: Sequence[Mapping[str, Any]]) -> str:
    canonical = []
    for item in sorted(records, key=lambda value: value["asset_id"]):
        if set(item) != {"source_id", "asset_id", "candidate_digest", "receipt_digest", "revision", "document_id", "chunk_count"}:
            _fail("RFC_PACKET_RECORD_FIELDS_INVALID")
        if item["source_id"] != SOURCE_ID or item["asset_id"] not in ASSETS:
            _fail("RFC_PACKET_SCOPE_INVALID")
        canonical.append(dict(item))
    if len(canonical) != 3 or {item["asset_id"] for item in canonical} != set(ASSETS):
        _fail("RFC_PACKET_SCOPE_INVALID")
    raw = json.dumps({"domain": "sa.m11.p0.rfc-evidence-closure.batch.v1", "parent_scope_digest": SCOPE_DIGEST, "records": canonical}, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def validate_rfc_evidence_closure_packet(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a review packet without issuing authority or changing evidence."""
    required = {"schema", "packet_id", "scope_digest", "operation", "metadata_only", "authority_issued", "application_id", "candidate_materialization", "batch_records", "batch_digest", "proposed_statuses", "current_status", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included"}
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("RFC_PACKET_FIELDS_INVALID")
    if payload["schema"] != SCHEMA or payload["scope_digest"] != SCOPE_DIGEST or payload["operation"] != "human_review":
        _fail("RFC_PACKET_IDENTITY_INVALID")
    if payload["metadata_only"] is not True or payload["authority_issued"] is not False:
        _fail("RFC_PACKET_AUTHORITY_ESCALATION")
    if payload["candidate_materialization"] != "data/manifests/m11-p0-rfc-candidate-materialization-v1.json":
        _fail("RFC_PACKET_MATERIALIZATION_LINK_INVALID")
    if payload["current_status"] != "REVIEW_REQUIRED" or payload["formal_gate0_executed"] is not False:
        _fail("RFC_PACKET_CURRENT_STATE_INVALID")
    if any(payload[field] is not False for field in ("candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")):
        _fail("RFC_PACKET_ESCALATION_FORBIDDEN")
    records = payload["batch_records"]
    if not isinstance(records, list):
        _fail("RFC_PACKET_RECORDS_INVALID")
    for item in records:
        for field in ("candidate_digest", "receipt_digest", "revision"):
            _digest(item[field])
        if not isinstance(item["document_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", item["document_id"]):
            _fail("RFC_PACKET_CANDIDATE_IDENTITY_INVALID")
        if isinstance(item["chunk_count"], bool) or not isinstance(item["chunk_count"], int) or item["chunk_count"] < 1:
            _fail("RFC_PACKET_CANDIDATE_IDENTITY_INVALID")
    if exact_three_packet_digest(records) != payload["batch_digest"]:
        _fail("RFC_PACKET_BATCH_DIGEST_INVALID")
    statuses = payload["proposed_statuses"]
    if set(statuses) != set(ASSETS):
        _fail("RFC_PACKET_STATUS_SCOPE_INVALID")
    for asset in ASSETS:
        if set(statuses[asset]) != set(CATEGORIES) or any(statuses[asset][category] != "PENDING" for category in CATEGORIES):
            _fail("RFC_PACKET_STATUS_MUST_REMAIN_PENDING")
    return copy.deepcopy(dict(payload))
