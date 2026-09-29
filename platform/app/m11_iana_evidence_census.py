"""IANA legal, robots, schema, and XML-conflict census validation."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn

from .m11_iana_evidence_closure_packet import (
    IanaEvidenceClosurePacketError,
    _validated_dependencies,
)

SOURCE_ID = "iana-registries"
ASSETS = (
    "service-names-port-numbers-csv",
    "service-names-port-numbers-xml",
    "service-names-port-numbers-txt",
)
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
ROBOTS_DIGEST = "e5c4b84484ee4216e9373be99380320c25dd94805f99f0a805846f087636553f"
ROBOTS_POLICY = "allow-all"
RAW_DIGESTS = {
    "service-names-port-numbers-csv": "34328ed0940d889207de6da29bf0e6e1438d604483c8e1ffb03dceab8f7ec26f",
    "service-names-port-numbers-xml": "30a69353af6e017ffd9e141d079f90a7b7117f113f122d2d89ee20ffb587da19",
    "service-names-port-numbers-txt": "6aa4def90086ae3dd71ee8f72e2bddb57857828718d3155b42c107138a3c1d29",
}
CSV_HEADERS = [
    "Service Name", "Port Number", "Transport Protocol", "Description", "Assignee", "Contact",
    "Registration Date", "Modification Date", "Reference", "Service Code",
    "Unauthorized Use Reported", "Assignment Notes",
]
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class IanaEvidenceCensusError(ValueError):
    """The IANA evidence census is malformed, inconsistent, or scope-escalating."""


def _fail(code: str) -> NoReturn:
    raise IanaEvidenceCensusError(code)


def census_iana_evidence(
    *,
    raw_root: Path,
    digest_evidence: Mapping[str, Any],
    receipt_batch: Mapping[str, Any],
) -> dict[str, Any]:
    """Read exact-three local inputs and return dependency-bound census facts."""
    try:
        expected_links = _validated_dependencies(digest_evidence, receipt_batch)
    except IanaEvidenceClosurePacketError as exc:
        raise IanaEvidenceCensusError("IANA_CENSUS_DEPENDENCY_INVALID") from exc
    blobs: dict[str, bytes] = {}
    for asset in ASSETS:
        path = raw_root / f"{asset}.raw"
        if not path.is_file():
            _fail("IANA_CENSUS_RAW_MISSING")
        blobs[asset] = path.read_bytes()
        if hashlib.sha256(blobs[asset]).hexdigest() != expected_links[asset]["candidate_digest"]:
            _fail("IANA_CENSUS_RAW_DIGEST_MISMATCH")

    csv_rows = list(csv.reader(io.StringIO(blobs[ASSETS[0]].decode("utf-8-sig", errors="strict"))))
    if not csv_rows or csv_rows[0] != CSV_HEADERS:
        _fail("IANA_CENSUS_CSV_SCHEMA_INVALID")
    try:
        root = ET.fromstring(blobs[ASSETS[1]])
    except ET.ParseError as exc:
        raise IanaEvidenceCensusError("IANA_CENSUS_XML_SCHEMA_INVALID") from exc
    namespace = "{http://www.iana.org/assignments}"
    if root.tag != f"{namespace}registry" or root.attrib.get("id") != "service-names-port-numbers":
        _fail("IANA_CENSUS_XML_SCHEMA_INVALID")
    updated = root.findtext(f"{namespace}updated")
    record_count = sum(1 for element in root.iter() if element.tag == f"{namespace}record")
    if updated != "2026-09-11" or record_count != 14535 or len(csv_rows) - 1 != 14535:
        _fail("IANA_CENSUS_SCHEMA_FACTS_INVALID")

    records = []
    for asset in ASSETS:
        records.append({
            "asset_id": asset,
            "raw_sha256": expected_links[asset]["candidate_digest"],
            "receipt_digest": expected_links[asset]["receipt_digest"],
            "cc0_observation": "CC0-1.0-direct-protocol-registry-data",
            "cc0_scope_excludes_linked_rfc_and_page_content": True,
            "robots_digest": ROBOTS_DIGEST,
            "robots_policy": ROBOTS_POLICY,
            "schema_applicable": True,
            "schema_observation": {
                ASSETS[0]: "csv-header-12-columns-record-count-14535",
                ASSETS[1]: "xml-registry-root-record-count-14535",
                ASSETS[2]: "historical-txt-fail-closed",
            }[asset],
            "license_status": "PENDING", "revision_status": "PENDING",
            "robots_terms_status": "PENDING", "notice_ipr_status": "PENDING",
            "schema_status": "PENDING", "provenance_status": "PENDING",
            "parser_status": "PENDING", "content_quality_status": "PENDING",
        })
    return {"technical_census_status": "VERIFIED", "sample_size": 3, "mode": "census", "records": records}


def validate_iana_evidence_census(
    payload: Mapping[str, Any],
    *,
    digest_evidence: Mapping[str, Any],
    receipt_batch: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        expected_links = _validated_dependencies(digest_evidence, receipt_batch)
    except IanaEvidenceClosurePacketError as exc:
        raise IanaEvidenceCensusError("IANA_CENSUS_DEPENDENCY_INVALID") from exc
    required = {
        "schema", "census_id", "generated_at", "source_id", "asset_ids", "scope_digest",
        "technical_census_status", "sample_size", "mode", "records", "xml_conflict",
        "authority_issued", "network_used", "formal_gate0_executed", "candidate_approval_granted",
        "publication_authorized", "source_expansion", "lifecycle_mutation", "host_paths_included",
        "bodies_included",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("IANA_CENSUS_FIELDS_INVALID")
    if payload["schema"] != "sa.m11.p0.iana-evidence-census.v1" or payload["source_id"] != SOURCE_ID or payload["asset_ids"] != list(ASSETS) or payload["scope_digest"] != SCOPE_DIGEST:
        _fail("IANA_CENSUS_IDENTITY_INVALID")
    if payload["technical_census_status"] != "VERIFIED" or payload["sample_size"] != 3 or payload["mode"] != "census":
        _fail("IANA_CENSUS_STATUS_INVALID")
    flags = ("authority_issued", "network_used", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")
    if any(payload[field] is not False for field in flags):
        _fail("IANA_CENSUS_ESCALATION_FORBIDDEN")
    conflict = payload["xml_conflict"]
    if conflict != {"asset_id": ASSETS[1], "status": "UNRESOLVED", "live_updated_date": "2024-12-20", "frozen_manifest_updated_date": "2026-09-11", "closure_effect": "NONE"}:
        _fail("IANA_CENSUS_XML_CONFLICT_INVALID")
    records = payload["records"]
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or len(records) != 3:
        _fail("IANA_CENSUS_RECORDS_INVALID")
    seen = set()
    expected_observations = {
        ASSETS[0]: "csv-header-12-columns-record-count-14535",
        ASSETS[1]: "xml-registry-root-record-count-14535",
        ASSETS[2]: "historical-txt-fail-closed",
    }
    for record in records:
        if not isinstance(record, Mapping) or set(record) != {
            "asset_id", "raw_sha256", "receipt_digest", "cc0_observation",
            "cc0_scope_excludes_linked_rfc_and_page_content", "robots_digest", "robots_policy",
            "schema_applicable", "schema_observation", "license_status", "revision_status",
            "robots_terms_status", "notice_ipr_status", "schema_status", "provenance_status",
            "parser_status", "content_quality_status",
        }:
            _fail("IANA_CENSUS_RECORD_FIELDS_INVALID")
        asset = record["asset_id"]
        if asset not in ASSETS or asset in seen:
            _fail("IANA_CENSUS_RECORD_SCOPE_INVALID")
        seen.add(asset)
        if record["raw_sha256"] != expected_links[asset]["candidate_digest"] or record["receipt_digest"] != expected_links[asset]["receipt_digest"]:
            _fail("IANA_CENSUS_DEPENDENCY_LINK_INVALID")
        if record["cc0_observation"] != "CC0-1.0-direct-protocol-registry-data" or record["cc0_scope_excludes_linked_rfc_and_page_content"] is not True:
            _fail("IANA_CENSUS_LICENSE_FACTS_INVALID")
        if record["robots_digest"] != ROBOTS_DIGEST or record["robots_policy"] != ROBOTS_POLICY:
            _fail("IANA_CENSUS_ROBOTS_FACTS_INVALID")
        if record["schema_applicable"] is not True or record["schema_observation"] != expected_observations[asset]:
            _fail("IANA_CENSUS_SCHEMA_FACTS_INVALID")
        status_fields = [field for field in record if field.endswith("_status")]
        if len(status_fields) != 8 or any(record[field] != "PENDING" for field in status_fields):
            _fail("IANA_CENSUS_CELLS_MUST_REMAIN_PENDING")
    if seen != set(ASSETS):
        _fail("IANA_CENSUS_RECORD_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))
