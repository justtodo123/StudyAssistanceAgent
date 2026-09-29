from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, NoReturn

from app.m11_execution_authority import ExecutionAuthorityError, validate_execution_authority
from app.m11_mit_ocw_candidate_materialization import EXPECTED_CANDIDATES
from app.m11_mit_ocw_owner_decision_packet import validate_mit_ocw_owner_decision_packet

SOURCE_ID = "mit-ocw-6-004-2017"
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
PACKET_ID = "m11-p0-mit-ocw-owner-decision-input-packet-20260929"
CATEGORIES = ("license", "revision", "robots_terms", "notice_ipr", "schema", "provenance", "parser", "content_quality")
LEGAL_CATEGORIES = ("license", "robots_terms", "notice_ipr")


def payload_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def timestamp(value: Any, error: type[ValueError], code: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise error(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise error(code)
    return parsed.astimezone(timezone.utc)


def validate_authority(payload: Mapping[str, Any], *, authority_id: str, error: type[ValueError], prefix: str) -> dict[str, Any]:
    try:
        authority = validate_execution_authority(
            payload,
            operation="human_review",
            expected_scope_digest=SCOPE_DIGEST,
            allowed_source_ids={SOURCE_ID: sorted(EXPECTED_CANDIDATES)},
            now=datetime(2026, 9, 29, 6, 30, tzinfo=timezone.utc),
        )
    except (ExecutionAuthorityError, TypeError, ValueError) as exc:
        code = getattr(exc, "code", f"{prefix}_AUTHORITY_INVALID")
        raise error(code) from exc
    if authority.authority_id != authority_id or authority.source_ids != (SOURCE_ID,) or authority.assets_for(SOURCE_ID) != EXPECTED_CANDIDATES:
        raise error(f"{prefix}_AUTHORITY_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))


def validate_packet(*, packet: Mapping[str, Any], materialization: Mapping[str, Any], digest_evidence: Mapping[str, Any], receipt_batch: Mapping[str, Any], gate0_result: Mapping[str, Any], error: type[ValueError], prefix: str) -> dict[str, Any]:
    try:
        return validate_mit_ocw_owner_decision_packet(
            packet,
            materialization=materialization,
            digest_evidence=digest_evidence,
            receipt_batch=receipt_batch,
            gate0_result=gate0_result,
        )
    except (TypeError, ValueError) as exc:
        raise error(f"{prefix}_INPUT_PACKET_INVALID") from exc


def _safe_review_text(value: Any, error: type[ValueError], prefix: str) -> None:
    if not isinstance(value, str) or not value.strip() or "\\" in value or ":\\" in value:
        raise error(f"{prefix}_PRIVACY_INVALID")


def validate_result_common(payload: Mapping[str, Any], *, authority: Mapping[str, Any], authority_id: str, result_id: str, schema: str, predecessor_ids: Mapping[str, str], predecessor_payloads: Mapping[str, Mapping[str, Any]], records: Sequence[str], error: type[ValueError], prefix: str) -> dict[str, Any]:
    required = {
        "schema", "result_id", "packet_id", "authority_id", "scope_digest", "signed_by", "signed_at", "decision_reference",
        "asset_count", "closed_cell_count", "pending_cell_count", "packet_pending_cell_count", "failed_cell_count", "closure_effect", "result", "records",
        "predecessor_references", "predecessor_content_seals", "successor_slice_written", "remaining_pending_categories", "current_heads", "current_status", "formal_gate0_executed",
        "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation",
        "host_paths_included", "bodies_included",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise error(f"{prefix}_RESULT_FIELDS_INVALID")
    if (payload["schema"], payload["result_id"], payload["packet_id"], payload["authority_id"], payload["scope_digest"]) != (schema, result_id, PACKET_ID, authority_id, SCOPE_DIGEST):
        raise error(f"{prefix}_RESULT_IDENTITY_INVALID")
    validate_authority(authority, authority_id=authority_id, error=error, prefix=prefix)
    signed_at = timestamp(payload["signed_at"], error, f"{prefix}_TIMESTAMP_INVALID")
    issued_at = timestamp(authority["issued_at"], error, f"{prefix}_TIMESTAMP_INVALID")
    expires_at = timestamp(authority["expires_at"], error, f"{prefix}_TIMESTAMP_INVALID")
    if signed_at < issued_at or signed_at >= expires_at:
        raise error(f"{prefix}_TIMESTAMP_ORDER_INVALID")
    if payload["signed_by"] != authority["issued_by"]:
        raise error(f"{prefix}_SIGNER_INVALID")
    _safe_review_text(payload["decision_reference"], error, prefix)
    expected_local = len(EXPECTED_CANDIDATES) * len(records)
    expected_packet = len(EXPECTED_CANDIDATES) * len(CATEGORIES)
    if payload["asset_count"] != len(EXPECTED_CANDIDATES) or payload["closed_cell_count"] != 0 or payload["pending_cell_count"] != expected_local or payload["packet_pending_cell_count"] != expected_packet or payload["failed_cell_count"] != 0 or payload["closure_effect"] != "NONE" or payload["result"] != "REVIEW_REQUIRED":
        raise error(f"{prefix}_COUNTS_INVALID")
    if payload["predecessor_references"] != dict(predecessor_ids) or set(payload["predecessor_content_seals"]) != set(predecessor_ids):
        raise error(f"{prefix}_PREDECESSOR_INVALID")
    for key, predecessor in predecessor_payloads.items():
        if key not in predecessor_ids or not isinstance(predecessor, Mapping) or payload["predecessor_references"][key] != predecessor.get("result_id", predecessor.get("packet_id")) or payload["predecessor_content_seals"].get(key) != payload_digest(predecessor):
            raise error(f"{prefix}_PREDECESSOR_SEAL_INVALID")
    if payload["successor_slice_written"] is not False or payload["remaining_pending_categories"] != list(CATEGORIES):
        raise error(f"{prefix}_PREDECESSOR_INVALID")
    if payload["current_heads"] != {"rfc": "3 ACCEPT", "iana": "3 DEFER", "mit_ocw": "20 DEFER"} or payload["current_status"] != "REVIEW_REQUIRED":
        raise error(f"{prefix}_CURRENT_STATE_INVALID")
    flags = ("formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")
    if any(payload[field] is not False for field in flags):
        raise error(f"{prefix}_ESCALATION_FORBIDDEN")
    raw_records = payload["records"]
    if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)) or len(raw_records) != len(EXPECTED_CANDIDATES):
        raise error(f"{prefix}_RECORD_SCOPE_INVALID")
    seen: set[str] = set()
    for record in raw_records:
        if not isinstance(record, Mapping) or set(record) != {"asset_id", *records} or record["asset_id"] not in EXPECTED_CANDIDATES or record["asset_id"] in seen:
            raise error(f"{prefix}_RECORD_FIELDS_INVALID")
        seen.add(record["asset_id"])
        for category in records:
            item = record[category]
            if not isinstance(item, Mapping) or set(item) != {"status", "refs", "rationale"} or item["status"] != "PENDING" or not isinstance(item["refs"], list) or not item["refs"]:
                raise error(f"{prefix}_DECISION_INVALID")
            _safe_review_text(item["rationale"], error, prefix)
            if item["refs"] != [PACKET_ID] or item["rationale"] != "Tracked evidence is insufficient for a definitive category decision." or any(not isinstance(ref, str) or not ref.strip() or "\\" in ref for ref in item["refs"]):
                raise error(f"{prefix}_DECISION_INVALID")
    if seen != EXPECTED_CANDIDATES:
        raise error(f"{prefix}_RECORD_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))
