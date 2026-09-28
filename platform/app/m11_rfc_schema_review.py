"""Owner-authorized RFC exact-three schema-only evidence decision."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

from app.m11_execution_authority import ExecutionAuthorityError, validate_execution_authority

SOURCE_ID = "rfc-editor-index"
ASSETS = ("rfc1034", "rfc9110", "rfc9293")
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
AUTHORITY_ID = "m11-rfc-schema-review-3-20260928"
PACKET_ID = "m11-p0-rfc-evidence-closure-packet-20260928"
RESULT_ID = "m11-p0-rfc-schema-review-result-20260928"
CATEGORIES = ("license", "revision", "robots_terms", "notice_ipr", "schema", "provenance", "parser", "content_quality")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class RfcSchemaReviewError(ValueError):
    """The owner-authorized RFC schema-only decision is invalid."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> NoReturn:
    raise RfcSchemaReviewError(code)


def _timestamp(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RfcSchemaReviewError("RFC_SCHEMA_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        _fail("RFC_SCHEMA_TIMESTAMP_INVALID")
    return parsed


def validate_rfc_schema_review_authority(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Require the exact-three human_review authority and no escalation flags."""
    try:
        authority = validate_execution_authority(
            payload,
            operation="human_review",
            expected_scope_digest=SCOPE_DIGEST,
            allowed_source_ids={SOURCE_ID: ASSETS},
            now=_timestamp("2026-09-28T12:01:00Z"),
        )
    except ExecutionAuthorityError as exc:
        raise RfcSchemaReviewError(exc.code) from exc
    if authority.authority_id != AUTHORITY_ID or authority.source_ids != (SOURCE_ID,):
        _fail("RFC_SCHEMA_AUTHORITY_IDENTITY_INVALID")
    if tuple(sorted(authority.assets_for(SOURCE_ID))) != tuple(sorted(ASSETS)):
        _fail("RFC_SCHEMA_AUTHORITY_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))


def validate_rfc_schema_review_result(payload: Mapping[str, Any], *, authority: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exactly three schema N/A decisions and all other categories pending."""
    validate_rfc_schema_review_authority(authority)
    required = {"schema", "result_id", "packet_id", "authority_id", "scope_digest", "signed_by", "signed_at", "decision_reference", "asset_count", "closed_cell_count", "pending_cell_count", "failed_cell_count", "closure_effect", "result", "records", "successor_slice_written", "all_other_categories_remain_pending", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included"}
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("RFC_SCHEMA_RESULT_FIELDS_INVALID")
    if payload["schema"] != "sa.m11.p0.rfc-schema-review-result.v1" or payload["result_id"] != RESULT_ID or payload["packet_id"] != PACKET_ID or payload["authority_id"] != AUTHORITY_ID or payload["scope_digest"] != SCOPE_DIGEST:
        _fail("RFC_SCHEMA_RESULT_IDENTITY_INVALID")
    if _timestamp(payload["signed_at"]) < _timestamp(authority["issued_at"]):
        _fail("RFC_SCHEMA_RESULT_TIMESTAMP_ORDER_INVALID")
    if payload["asset_count"] != 3 or payload["closed_cell_count"] != 3 or payload["pending_cell_count"] != 21 or payload["failed_cell_count"] != 0 or payload["closure_effect"] != "PARTIAL" or payload["result"] != "REVIEW_REQUIRED":
        _fail("RFC_SCHEMA_RESULT_COUNTS_INVALID")
    if payload["successor_slice_written"] is not False or payload["all_other_categories_remain_pending"] is not True:
        _fail("RFC_SCHEMA_SUCCESSOR_POLICY_INVALID")
    if any(payload[field] is not False for field in ("formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")):
        _fail("RFC_SCHEMA_ESCALATION_FORBIDDEN")
    records = payload["records"]
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or len(records) != 3:
        _fail("RFC_SCHEMA_RECORD_SCOPE_INVALID")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping) or set(record) != {"asset_id", "schema"} or record["asset_id"] not in ASSETS or record["asset_id"] in seen:
            _fail("RFC_SCHEMA_RECORD_SCOPE_INVALID")
        seen.add(record["asset_id"])
        schema = record["schema"]
        if not isinstance(schema, Mapping) or set(schema) != {"status", "refs", "rationale"} or schema["status"] != "NOT_APPLICABLE" or not isinstance(schema["refs"], list) or not schema["refs"] or not isinstance(schema["rationale"], str) or not schema["rationale"].strip():
            _fail("RFC_SCHEMA_DECISION_INVALID")
    if seen != set(ASSETS):
        _fail("RFC_SCHEMA_RECORD_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))
