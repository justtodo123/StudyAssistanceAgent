"""Owner-authorized exact-three IANA evidence review contract."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, NoReturn

from .m11_execution_authority import ExecutionAuthorityError, validate_execution_authority
from .m11_iana_evidence_closure_packet import (
    ASSETS,
    CATEGORIES,
    SCOPE_DIGEST,
    validate_iana_evidence_closure_packet,
)
from .m11_iana_owner_disposition import validate_iana_owner_disposition

SCHEMA = "sa.m11.p0.iana-evidence-review.v1"
APPLICATION_ID = "m11-p0-iana-evidence-review-application-20260929"
AUTHORITY_ID = "m11-iana-evidence-review-3-20260929"
RESULT_ID = "m11-p0-iana-evidence-review-result-20260929"
PACKET_ID = "m11-p0-iana-evidence-closure-packet-20260929"
CENSUS_ID = "m11-p0-iana-evidence-census-20260929"
DISPOSITION_ID = "m11-p0-iana-owner-disposition-20260929"
AUTHORITY_RECORD = "data/manifests/m11-p0-iana-evidence-review-authority-v1.json"
PREDECESSOR_SLICE_ID = "rfc-iana-evidence-review-defer-6-20260927"
PREDECESSOR_SLICE_MANIFEST = "data/manifests/m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json"
PREDECESSOR_SLICE_SHA256 = "57b7f286cadb62613f7f0ec8ee32b32e67e4c96e264b2725f6ec13ff2b3774b1"
FORMAL_GATE0_RESULT_ID = "m11-p0-formal-gate0-26-result-20260928"
FORMAL_GATE0_RESULT_MANIFEST = "data/manifests/m11-p0-formal-gate0-26-result-v1.json"
FORMAL_GATE0_RESULT_SHA256 = "fb08c974171f9935823c8819141de873f9c29565058b7a7583839b3130c4ac41"

_HEX = re.compile(r"[0-9a-f]{64}\Z")
_DRIVE_PATH = re.compile(r"[A-Za-z]:\\\\")
_UNC_PATH = re.compile(r"\\\\\\\\")
_POSIX_HOST_PATH = re.compile(r"(?<![A-Za-z0-9.])/(?:home|users|private|root|tmp|var/tmp)/", re.IGNORECASE)
_FORBIDDEN_KEYS = frozenset({"credentials", "password", "token", "learning_state", "private_learning_state", "signature", "reviewer_comment"})


def _private(value: Any) -> bool:
    if isinstance(value, Mapping):
        return bool(set(value) & _FORBIDDEN_KEYS) or any(_private(item) for item in value.values())
    if isinstance(value, list):
        return any(_private(item) for item in value)
    return isinstance(value, str) and bool(_DRIVE_PATH.search(value) or _UNC_PATH.search(value) or _POSIX_HOST_PATH.search(value))

class IanaEvidenceReviewError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

def _fail(code: str) -> NoReturn:
    raise IanaEvidenceReviewError(code)

def _timestamp(value: Any, code: str = "IANA_REVIEW_TIMESTAMP_INVALID") -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise IanaEvidenceReviewError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(code)
    return parsed.astimezone(timezone.utc)

def _digest(value: Any) -> None:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail("IANA_REVIEW_DIGEST_INVALID")


def _sealed_digest(payload: Mapping[str, Any]) -> str:
    if not isinstance(payload, Mapping):
        _fail("IANA_REVIEW_HISTORY_PAYLOAD_INVALID")
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_history(
    *, predecessor_slice: Mapping[str, Any], formal_gate0_result: Mapping[str, Any]
) -> None:
    if _sealed_digest(predecessor_slice) != PREDECESSOR_SLICE_SHA256:
        _fail("IANA_REVIEW_PREDECESSOR_DIGEST_INVALID")
    if predecessor_slice.get("slice_id") != PREDECESSOR_SLICE_ID:
        _fail("IANA_REVIEW_PREDECESSOR_ID_INVALID")
    records = predecessor_slice.get("records")
    if not isinstance(records, list):
        _fail("IANA_REVIEW_PREDECESSOR_RECORDS_INVALID")
    expected_ids = {
        "service-names-port-numbers-csv": "m11-hr-20260927-evidence-review-service-names-port-numbers-csv",
        "service-names-port-numbers-xml": "m11-hr-20260927-evidence-review-service-names-port-numbers-xml",
        "service-names-port-numbers-txt": "m11-hr-20260927-evidence-review-service-names-port-numbers-txt",
    }
    actual_ids = {
        record.get("asset_id"): record.get("review_id")
        for record in records
        if isinstance(record, Mapping) and record.get("source_id") == "iana-registries"
    }
    if actual_ids != expected_ids:
        _fail("IANA_REVIEW_PREDECESSOR_RECORDS_INVALID")
    if _sealed_digest(formal_gate0_result) != FORMAL_GATE0_RESULT_SHA256:
        _fail("IANA_REVIEW_GATE0_DIGEST_INVALID")
    if formal_gate0_result.get("result_id") != FORMAL_GATE0_RESULT_ID or formal_gate0_result.get("status") != "BLOCKED":
        _fail("IANA_REVIEW_GATE0_HISTORY_INVALID")

def validate_iana_evidence_review_authority(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        authority = validate_execution_authority(
            payload, operation="human_review", expected_scope_digest=SCOPE_DIGEST,
            allowed_source_ids={"iana-registries": ASSETS},
            now=_timestamp("2026-09-29T01:00:00Z"),
        )
    except ExecutionAuthorityError as exc:
        raise IanaEvidenceReviewError(exc.code) from exc
    if authority.authority_id != AUTHORITY_ID or authority.source_ids != ("iana-registries",):
        _fail("IANA_REVIEW_AUTHORITY_IDENTITY_INVALID")
    if tuple(sorted(authority.assets_for("iana-registries"))) != tuple(sorted(ASSETS)):
        _fail("IANA_REVIEW_AUTHORITY_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))

def _validate_application(payload: Mapping[str, Any], packet: Mapping[str, Any], authority: Mapping[str, Any]) -> dict[str, Any]:
    required = {"schema", "application_id", "authority_id", "scope_digest", "packet_id", "packet_manifest", "census_id", "census_manifest", "disposition_id", "disposition_manifest", "source_id", "asset_ids", "asset_count", "batch_digest", "submitted_by", "submitted_at", "operation", "metadata_only", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included"}
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("IANA_REVIEW_APPLICATION_FIELDS_INVALID")
    if _private(payload):
        _fail("IANA_REVIEW_APPLICATION_PRIVACY_INVALID")
    if payload["schema"] != SCHEMA or payload["application_id"] != APPLICATION_ID or payload["authority_id"] != AUTHORITY_ID or payload["scope_digest"] != SCOPE_DIGEST:
        _fail("IANA_REVIEW_APPLICATION_IDENTITY_INVALID")
    if payload["packet_id"] != PACKET_ID or payload["packet_manifest"] != "data/manifests/m11-p0-iana-evidence-closure-packet-v1.json" or payload["census_id"] != CENSUS_ID or payload["census_manifest"] != "data/manifests/m11-p0-iana-evidence-census-v1.json" or payload["disposition_id"] != DISPOSITION_ID or payload["disposition_manifest"] != "data/manifests/m11-p0-iana-owner-disposition-v1.json":
        _fail("IANA_REVIEW_APPLICATION_PARENT_INVALID")
    if payload["source_id"] != "iana-registries" or payload["asset_ids"] != list(ASSETS) or payload["asset_count"] != 3 or payload["batch_digest"] != packet.get("batch_digest"):
        _fail("IANA_REVIEW_APPLICATION_SCOPE_INVALID")
    submitted_at = _timestamp(payload["submitted_at"])
    issued_at = _timestamp(authority["issued_at"])
    expires_at = _timestamp(authority["expires_at"])
    if payload["submitted_by"] != authority["issued_by"] or submitted_at < issued_at or submitted_at >= expires_at or payload["operation"] != "human_review" or payload["metadata_only"] is True:
        _fail("IANA_REVIEW_APPLICATION_AUTHORITY_INVALID")
    for field in ("network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included"):
        if payload[field] is not False:
            _fail("IANA_REVIEW_APPLICATION_ESCALATION_FORBIDDEN")
    return copy.deepcopy(dict(payload))

def validate_iana_evidence_review_result(result: Mapping[str, Any], *, application: Mapping[str, Any], authority: Mapping[str, Any], packet: Mapping[str, Any], census: Mapping[str, Any], disposition: Mapping[str, Any], digest_evidence: Mapping[str, Any], receipt_batch: Mapping[str, Any], predecessor_slice: Mapping[str, Any], formal_gate0_result: Mapping[str, Any]) -> dict[str, Any]:
    payload = result
    try:
        validated_packet = validate_iana_evidence_closure_packet(packet, digest_evidence=digest_evidence, receipt_batch=receipt_batch)
        validated_disposition = validate_iana_owner_disposition(disposition, packet=packet, census=census, digest_evidence=digest_evidence, receipt_batch=receipt_batch)
    except Exception as exc:
        raise IanaEvidenceReviewError("IANA_REVIEW_PARENT_INVALID") from exc
    validate_iana_evidence_review_authority(authority)
    _validate_history(
        predecessor_slice=predecessor_slice, formal_gate0_result=formal_gate0_result
    )
    validated_application = _validate_application(application, validated_packet, authority)
    required = {"schema", "result_id", "application_id", "authority_id", "scope_digest", "packet_id", "census_id", "disposition_id", "signed_by", "signed_at", "decision_reference", "source_id", "asset_ids", "asset_count", "evidence_cell_count", "pending_cell_count", "failed_cell_count", "result", "closure_effect", "successor_slice_written", "current_heads", "predecessor_slice_id", "predecessor_slice_manifest", "predecessor_slice_sha256", "predecessor_review_ids", "formal_gate0_result_id", "formal_gate0_result_manifest", "formal_gate0_result_sha256", "records", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included"}
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("IANA_REVIEW_RESULT_FIELDS_INVALID")
    if _private(payload):
        _fail("IANA_REVIEW_RESULT_PRIVACY_INVALID")
    if payload["schema"] != SCHEMA or payload["result_id"] != RESULT_ID or payload["application_id"] != APPLICATION_ID or payload["authority_id"] != AUTHORITY_ID or payload["scope_digest"] != SCOPE_DIGEST:
        _fail("IANA_REVIEW_RESULT_IDENTITY_INVALID")
    if payload["packet_id"] != PACKET_ID or payload["census_id"] != CENSUS_ID or payload["disposition_id"] != DISPOSITION_ID or payload["source_id"] != "iana-registries" or payload["asset_ids"] != list(ASSETS):
        _fail("IANA_REVIEW_RESULT_PARENT_INVALID")
    if payload["predecessor_slice_id"] != PREDECESSOR_SLICE_ID or payload["predecessor_slice_manifest"] != PREDECESSOR_SLICE_MANIFEST or payload["predecessor_slice_sha256"] != PREDECESSOR_SLICE_SHA256 or payload["formal_gate0_result_id"] != FORMAL_GATE0_RESULT_ID or payload["formal_gate0_result_manifest"] != FORMAL_GATE0_RESULT_MANIFEST or payload["formal_gate0_result_sha256"] != FORMAL_GATE0_RESULT_SHA256:
        _fail("IANA_REVIEW_RESULT_HISTORY_LINK_INVALID")
    expected_predecessor_ids = {
        "service-names-port-numbers-csv": "m11-hr-20260927-evidence-review-service-names-port-numbers-csv",
        "service-names-port-numbers-xml": "m11-hr-20260927-evidence-review-service-names-port-numbers-xml",
        "service-names-port-numbers-txt": "m11-hr-20260927-evidence-review-service-names-port-numbers-txt",
    }
    if payload["predecessor_review_ids"] != expected_predecessor_ids:
        _fail("IANA_REVIEW_RESULT_HISTORY_LINK_INVALID")
    signed_at = _timestamp(payload["signed_at"])
    issued_at = _timestamp(authority["issued_at"])
    expires_at = _timestamp(authority["expires_at"])
    if payload["signed_by"] != authority["issued_by"] or signed_at < issued_at or signed_at >= expires_at:
        _fail("IANA_REVIEW_RESULT_SIGNER_INVALID")
    if payload["asset_count"] != 3 or payload["evidence_cell_count"] != 24 or payload["pending_cell_count"] != 24 or payload["failed_cell_count"] != 0 or payload["result"] != "REVIEW_REQUIRED" or payload["closure_effect"] != "NONE" or payload["successor_slice_written"] is not False:
        _fail("IANA_REVIEW_RESULT_STATE_INVALID")
    if payload["current_heads"] != {"rfc": "3 ACCEPT", "iana": "3 DEFER", "mit_ocw": "20 DEFER"}:
        _fail("IANA_REVIEW_RESULT_HEADS_INVALID")
    for field in ("formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included"):
        if payload[field] is not False:
            _fail("IANA_REVIEW_RESULT_ESCALATION_FORBIDDEN")
    if payload["decision_reference"] != "User choice: all 24 IANA evidence cells remain PENDING; XML remains UNRESOLVED; TXT remains FAIL_CLOSED":
        _fail("IANA_REVIEW_RESULT_DECISION_INVALID")
    records = payload["records"]
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or len(records) != 3:
        _fail("IANA_REVIEW_RESULT_RECORD_SCOPE_INVALID")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping) or set(record) != {"source_id", "asset_id", "candidate_digest", "receipt_digest", "revision", "evidence"} or record["source_id"] != "iana-registries" or record["asset_id"] not in ASSETS or record["asset_id"] in seen:
            _fail("IANA_REVIEW_RESULT_RECORD_INVALID")
        seen.add(record["asset_id"])
        for key in ("candidate_digest", "receipt_digest", "revision"):
            _digest(record[key])
        evidence = record["evidence"]
        if not isinstance(evidence, Mapping) or set(evidence) != set(CATEGORIES):
            _fail("IANA_REVIEW_RESULT_EVIDENCE_INVALID")
        for category in CATEGORIES:
            cell = evidence[category]
            if not isinstance(cell, Mapping) or set(cell) != {"status", "refs", "comment"} or cell["status"] != "PENDING" or not isinstance(cell["refs"], list) or not cell["refs"] or not isinstance(cell["comment"], str) or not cell["comment"].strip() or _private(cell["refs"]) or _private(cell["comment"]):
                _fail("IANA_REVIEW_RESULT_EVIDENCE_INVALID")
    if seen != set(ASSETS):
        _fail("IANA_REVIEW_RESULT_RECORD_SCOPE_INVALID")
    expected = {item["asset_id"]: item for item in validated_packet["batch_records"]}
    for record in records:
        if any(record[key] != expected[record["asset_id"]][key] for key in ("candidate_digest", "receipt_digest", "revision")):
            _fail("IANA_REVIEW_RESULT_DEPENDENCY_LINK_INVALID")
    if validated_disposition["current_heads"] != payload["current_heads"]:
        _fail("IANA_REVIEW_RESULT_DISPOSITION_LINK_INVALID")
    if validated_application["batch_digest"] != validated_packet["batch_digest"]:
        _fail("IANA_REVIEW_RESULT_APPLICATION_LINK_INVALID")
    return copy.deepcopy(dict(payload))
