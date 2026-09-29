from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from app.m11_iana_evidence_census import ASSETS as CENSUS_ASSETS
from app.m11_iana_evidence_census import validate_iana_evidence_census
from app.m11_iana_evidence_closure_packet import validate_iana_evidence_closure_packet

SCHEMA = "sa.m11.p0.iana-owner-disposition.v1"
SOURCE_ID = "iana-registries"
ASSETS = tuple(CENSUS_ASSETS)
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
PACKET_ID = "m11-p0-iana-evidence-closure-packet-20260929"
CENSUS_ID = "m11-p0-iana-evidence-census-20260929"
PACKET_MANIFEST = "data/manifests/m11-p0-iana-evidence-closure-packet-v1.json"
CENSUS_MANIFEST = "data/manifests/m11-p0-iana-evidence-census-v1.json"
CATEGORIES = (
    "license",
    "revision",
    "robots_terms",
    "notice_ipr",
    "schema",
    "provenance",
    "parser",
    "content_quality",
)


class IanaOwnerDispositionError(ValueError):
    pass


def _fail(code: str) -> None:
    raise IanaOwnerDispositionError(code)


def validate_iana_owner_disposition(
    payload: Mapping[str, Any],
    *,
    packet: Mapping[str, Any],
    census: Mapping[str, Any],
    digest_evidence: Mapping[str, Any],
    receipt_batch: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        validated_packet = validate_iana_evidence_closure_packet(
            packet, digest_evidence=digest_evidence, receipt_batch=receipt_batch
        )
        validated_census = validate_iana_evidence_census(
            census, digest_evidence=digest_evidence, receipt_batch=receipt_batch
        )
    except Exception as exc:
        raise IanaOwnerDispositionError("IANA_DISPOSITION_PARENT_INVALID") from exc

    required = {
        "schema", "disposition_id", "source_id", "scope_digest", "packet_manifest", "packet_id",
        "census_manifest", "census_id", "operation", "metadata_only", "owner_decision", "records",
        "current_heads", "current_status", "closure_effect", "escalation",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("IANA_DISPOSITION_FIELDS_INVALID")
    if (
        payload["schema"] != SCHEMA
        or payload["source_id"] != SOURCE_ID
        or payload["scope_digest"] != SCOPE_DIGEST
        or payload["packet_manifest"] != PACKET_MANIFEST
        or payload["packet_id"] != PACKET_ID
        or payload["census_manifest"] != CENSUS_MANIFEST
        or payload["census_id"] != CENSUS_ID
        or payload["operation"] != "owner_disposition"
        or payload["metadata_only"] is not True
    ):
        _fail("IANA_DISPOSITION_IDENTITY_INVALID")
    if validated_packet["packet_id"] != PACKET_ID or validated_census["census_id"] != CENSUS_ID:
        _fail("IANA_DISPOSITION_PARENT_ID_INVALID")
    if validated_packet["scope_digest"] != SCOPE_DIGEST or validated_census["scope_digest"] != SCOPE_DIGEST:
        _fail("IANA_DISPOSITION_PARENT_SCOPE_INVALID")

    owner = payload["owner_decision"]
    if not isinstance(owner, Mapping) or set(owner) != {"identity", "decision_date", "decision_reference", "references"}:
        _fail("IANA_DISPOSITION_OWNER_FIELDS_INVALID")
    if (
        owner["identity"] != "justtodo123"
        or owner["decision_date"] != "2026-09-29"
        or owner["decision_reference"]
        != "User choice: XML remains UNRESOLVED; TXT remains FAIL_CLOSED; all three schema cells remain applicable and PENDING"
    ):
        _fail("IANA_DISPOSITION_OWNER_IDENTITY_INVALID")
    if owner["references"] != [PACKET_MANIFEST, CENSUS_MANIFEST]:
        _fail("IANA_DISPOSITION_OWNER_REFERENCES_INVALID")

    if payload["current_heads"] != {"rfc": "3 ACCEPT", "iana": "3 DEFER", "mit_ocw": "20 DEFER"}:
        _fail("IANA_DISPOSITION_HEADS_INVALID")
    if payload["current_status"] != "REVIEW_REQUIRED" or payload["closure_effect"] != "NONE":
        _fail("IANA_DISPOSITION_CURRENT_STATE_INVALID")

    records = payload["records"]
    if not isinstance(records, list) or len(records) != 3:
        _fail("IANA_DISPOSITION_RECORDS_INVALID")
    expected = {
        "service-names-port-numbers-csv": ("PENDING", "PENDING", None),
        "service-names-port-numbers-xml": ("PENDING", "PENDING", "UNRESOLVED"),
        "service-names-port-numbers-txt": ("PENDING", "FAIL_CLOSED", None),
    }
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping) or set(record) != {
            "source_id", "asset_id", "schema_applicable", "schema_status", "parser_status", "xml_conflict_status"
        }:
            _fail("IANA_DISPOSITION_RECORD_FIELDS_INVALID")
        asset = record["asset_id"]
        if record["source_id"] != SOURCE_ID or asset not in ASSETS or asset in seen:
            _fail("IANA_DISPOSITION_RECORD_SCOPE_INVALID")
        seen.add(asset)
        schema_status, parser_status, conflict_status = expected[asset]
        if (
            record["schema_applicable"] is not True
            or record["schema_status"] != schema_status
            or record["parser_status"] != parser_status
            or record["xml_conflict_status"] != conflict_status
        ):
            _fail("IANA_DISPOSITION_STATUS_INVALID")
    if seen != set(ASSETS):
        _fail("IANA_DISPOSITION_RECORD_SCOPE_INVALID")

    escalation = payload["escalation"]
    escalation_fields = {
        "authority_issued", "execution_authorized", "evidence_closed", "successor_created",
        "candidate_approval_granted", "publication_authorized", "formal_gate0_executed", "network_used",
        "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included",
    }
    if not isinstance(escalation, Mapping) or set(escalation) != escalation_fields:
        _fail("IANA_DISPOSITION_ESCALATION_FIELDS_INVALID")
    if any(escalation[field] is not False for field in escalation_fields):
        _fail("IANA_DISPOSITION_ESCALATION_FORBIDDEN")
    return copy.deepcopy(dict(payload))
