"""Strict, metadata-only evidence-closure projection for M11 P0."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .m11_acquisition import validate_receipt, validate_receipt_batch
from .m11_gate0 import EVIDENCE_CATEGORIES
from .m11_review import validate_review_history

EVIDENCE_CLOSURE_SCHEMA = "sa.m11.p0.evidence-closure.v1"
EVIDENCE_STATUSES = frozenset({"VERIFIED", "NOT_APPLICABLE", "PENDING", "FAILED"})
RESULT = "REVIEW_REQUIRED"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*\Z")
_FORBIDDEN = frozenset({
    "body", "content", "text", "raw_path", "host_path", "credentials", "password",
    "token", "learning_state", "private_learning_state", "signature",
})
_RECORD_FIELDS = frozenset({
    "source_id", "asset_id", "candidate_digest", "receipt_digest", "revision",
    "evidence", "disposition", "no_escalation",
})
_TOP_FIELDS = frozenset({
    "schema", "matrix_id", "scope_digest", "authority_id", "authority_record",
    "acquisition_authority_id", "acquisition_authority_record", "receipt_batch_id",
    "receipt_record", "prior_review_slice_id", "prior_review_record", "asset_count",
    "source_ids", "result", "formal_gate0_executed", "formal_3k_executed",
    "candidate_approval_granted", "publication_authorized", "network_used",
    "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included",
    "records",
})


class EvidenceClosureError(ValueError):
    """A closure matrix or its linked metadata is malformed or incomplete."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise EvidenceClosureError(code)


def _id(value: Any, code: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip() or not _ID.fullmatch(value):
        _fail(code)


def _digest(value: Any, code: str) -> None:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail(code)


def _privacy(value: Any) -> bool:
    if isinstance(value, Mapping):
        if set(value) & _FORBIDDEN:
            return True
        return any(_privacy(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_privacy(item) for item in value)
    return False


def closure_digest(payload: Mapping[str, Any]) -> str:
    try:
        encoded = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise EvidenceClosureError("CLOSURE_DIGEST_INVALID") from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_evidence(value: Any) -> None:
    if not isinstance(value, Mapping) or set(value) != set(EVIDENCE_CATEGORIES):
        _fail("CLOSURE_EVIDENCE_CATEGORIES_INVALID")
    for category in EVIDENCE_CATEGORIES:
        entry = value[category]
        if not isinstance(entry, Mapping) or set(entry) != {"status", "refs", "comment"}:
            _fail("CLOSURE_EVIDENCE_FIELDS_INVALID")
        if entry["status"] not in EVIDENCE_STATUSES:
            _fail("CLOSURE_EVIDENCE_STATUS_INVALID")
        refs = entry["refs"]
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not _ID.fullmatch(ref) for ref in refs):
            _fail("CLOSURE_EVIDENCE_REFS_INVALID")
        if not isinstance(entry["comment"], str) or len(entry["comment"]) > 500:
            _fail("CLOSURE_EVIDENCE_COMMENT_INVALID")
        if entry["status"] == "NOT_APPLICABLE" and not entry["comment"].strip():
            _fail("CLOSURE_EVIDENCE_NA_REASON_REQUIRED")
        if entry["status"] == "PENDING" and not entry["comment"].strip():
            _fail("CLOSURE_EVIDENCE_PENDING_REASON_REQUIRED")


def validate_evidence_closure(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a detached metadata-only closure matrix."""
    if not isinstance(payload, Mapping) or set(payload) != _TOP_FIELDS:
        _fail("CLOSURE_FIELDS_INVALID")
    if _privacy(payload):
        _fail("CLOSURE_PRIVACY_FIELD")
    if payload["schema"] != EVIDENCE_CLOSURE_SCHEMA:
        _fail("CLOSURE_SCHEMA_INVALID")
    for key in (
        "matrix_id", "authority_id", "authority_record", "acquisition_authority_id",
        "acquisition_authority_record", "receipt_batch_id", "receipt_record",
        "prior_review_slice_id", "prior_review_record",
    ):
        _id(payload[key], "CLOSURE_ID_INVALID")
    _digest(payload["scope_digest"], "CLOSURE_SCOPE_INVALID")
    if not isinstance(payload["asset_count"], int) or isinstance(payload["asset_count"], bool):
        _fail("CLOSURE_ASSET_COUNT_INVALID")
    source_ids = payload["source_ids"]
    if not isinstance(source_ids, list) or not source_ids or any(not isinstance(item, str) for item in source_ids):
        _fail("CLOSURE_SOURCE_IDS_INVALID")
    if payload["result"] != RESULT:
        _fail("CLOSURE_RESULT_INVALID")
    for key in (
        "formal_gate0_executed", "formal_3k_executed", "candidate_approval_granted",
        "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation",
        "host_paths_included", "bodies_included",
    ):
        if payload[key] is not False:
            _fail("CLOSURE_ESCALATION_FLAG")
    records = payload["records"]
    if not isinstance(records, list) or len(records) != payload["asset_count"]:
        _fail("CLOSURE_RECORD_COUNT_INVALID")
    seen: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, Mapping) or set(record) != _RECORD_FIELDS:
            _fail("CLOSURE_RECORD_FIELDS_INVALID")
        if _privacy(record):
            _fail("CLOSURE_PRIVACY_FIELD")
        _id(record["source_id"], "CLOSURE_SOURCE_ID_INVALID")
        _id(record["asset_id"], "CLOSURE_ASSET_ID_INVALID")
        key = (record["source_id"], record["asset_id"])
        if key in seen:
            _fail("CLOSURE_DUPLICATE_ASSET")
        seen.add(key)
        _digest(record["candidate_digest"], "CLOSURE_CANDIDATE_DIGEST_INVALID")
        _digest(record["receipt_digest"], "CLOSURE_RECEIPT_DIGEST_INVALID")
        _digest(record["revision"], "CLOSURE_REVISION_INVALID")
        _validate_evidence(record["evidence"])
        if record["disposition"] not in {"ELIGIBLE_FOR_REVIEW", "NORMALIZATION_REJECTED"}:
            _fail("CLOSURE_DISPOSITION_INVALID")
        if not isinstance(record["no_escalation"], Mapping) or set(record["no_escalation"]) != {
            "candidate_promotion", "publication", "source_expansion"
        } or any(record["no_escalation"].values()):
            _fail("CLOSURE_NO_ESCALATION_INVALID")
    if set(seen) and len(seen) != payload["asset_count"]:
        _fail("CLOSURE_ASSET_COUNT_INVALID")
    return copy.deepcopy(dict(payload))


def load_evidence_closure(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceClosureError("CLOSURE_LOAD_FAILED") from exc
    return validate_evidence_closure(payload)


def validate_closure_bundle(
    matrix: Mapping[str, Any],
    *,
    digest_assets: Sequence[Mapping[str, Any]],
    receipts: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    prior_reviews: Sequence[Mapping[str, Any]],
    expected_assets: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    """Validate cross-manifest identity and ensure the projection remains deferred."""
    validated = validate_evidence_closure(matrix)
    expected = set(expected_assets)
    actual = {(item["source_id"], item["asset_id"]) for item in validated["records"]}
    if actual != expected:
        _fail("CLOSURE_SCOPE_ASSETS_INVALID")
    digest_by_key = {(item["source_id"], item["asset_id"]): item for item in digest_assets}
    if set(digest_by_key) != expected:
        _fail("CLOSURE_DIGEST_SCOPE_INVALID")
    receipt_by_key = {(item["source_id"], item["asset_id"]): item for item in receipts}
    if set(receipt_by_key) != expected:
        _fail("CLOSURE_RECEIPT_SCOPE_INVALID")
    validate_receipt_batch(tuple(validate_receipt(item) for item in receipts),
                           {key: _asset_stub(key, item) for key, item in receipt_by_key.items()})
    validate_review_history(reviews)
    validate_review_history(prior_reviews)
    for record in validated["records"]:
        key = (record["source_id"], record["asset_id"])
        digest = digest_by_key[key]
        receipt = receipt_by_key[key]
        if record["candidate_digest"] != digest["sha256"] or record["revision"] != receipt["revision"]:
            _fail("CLOSURE_IDENTITY_LINK_INVALID")
        if record["receipt_digest"] != _receipt_digest(receipt):
            _fail("CLOSURE_RECEIPT_LINK_INVALID")
    if any(item["evidence"][category]["status"] == "FAILED"
           for item in validated["records"] for category in EVIDENCE_CATEGORIES):
        _fail("CLOSURE_FAILED_EVIDENCE")
    return validated


def _receipt_digest(receipt: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(receipt), ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()


def _asset_stub(key: tuple[str, str], receipt: Mapping[str, Any]) -> Any:
    """Provide the narrow FrozenAsset shape required by validate_receipt_batch."""
    from .m11_acquisition import FrozenAsset
    return FrozenAsset(
        source_id=key[0], asset_id=key[1], canonical_url=receipt["canonical_url"],
        revision=receipt["revision"], sha256=receipt["sha256"],
        source_blob_sha1=receipt["source_blob_sha1"],
    )