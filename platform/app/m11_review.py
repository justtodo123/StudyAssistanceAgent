"""Metadata-only M11 human-review records and read-only Gate 0 evidence status."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

REVIEW_SCHEMA = "sa.m11.human-review.v1"
GATE0_SCHEMA = "sa.m11.gate0-evidence-package.v1"
_ALLOWED_DECISIONS = frozenset({"ACCEPT_FOR_PROMOTION_REVIEW", "REJECT", "DEFER"})
_REVIEW_FIELDS = frozenset({
    "schema", "review_id", "scope_digest", "source_id", "asset_id", "document_id",
    "chunk_ids", "candidate_digest", "receipt_digest", "reviewer_id", "reviewer_role",
    "sampling_plan", "signed_at", "attestation_digest", "decision", "evidence_refs",
    "supersedes", "comment",
})
_FORBIDDEN_KEYS = frozenset({
    "body", "content", "raw_path", "host_path", "credentials", "password", "token",
    "learning_state", "private_learning_state", "signature",
})
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*\Z")


class ReviewError(ValueError):
    """A review record or Gate 0 package is invalid or incomplete."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    review_id: str
    scope_digest: str
    source_id: str
    asset_id: str
    document_id: str | None
    chunk_ids: tuple[str, ...]
    candidate_digest: str
    receipt_digest: str
    reviewer_id: str
    reviewer_role: str
    sampling_plan: Mapping[str, Any]
    signed_at: str
    attestation_digest: str
    decision: str
    evidence_refs: tuple[str, ...]
    supersedes: str | None = None
    comment: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": REVIEW_SCHEMA,
            "review_id": self.review_id, "scope_digest": self.scope_digest,
            "source_id": self.source_id, "asset_id": self.asset_id,
            "document_id": self.document_id, "chunk_ids": list(self.chunk_ids),
            "candidate_digest": self.candidate_digest, "receipt_digest": self.receipt_digest,
            "reviewer_id": self.reviewer_id, "reviewer_role": self.reviewer_role,
            "sampling_plan": dict(self.sampling_plan), "signed_at": self.signed_at,
            "attestation_digest": self.attestation_digest, "decision": self.decision,
            "evidence_refs": list(self.evidence_refs), "supersedes": self.supersedes,
            "comment": self.comment,
        }


def review_digest(payload: Mapping[str, Any]) -> str:
    try:
        text = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ReviewError("REVIEW_DIGEST_INVALID") from exc
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fail(code: str) -> None:
    raise ReviewError(code)


def _id(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or not _ID.fullmatch(value):
        _fail(code)
    return value


def _digest(value: Any, code: str) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail(code)
    return value


def validate_review_record(payload: Mapping[str, Any]) -> ReviewRecord:
    if not isinstance(payload, Mapping) or set(payload) != _REVIEW_FIELDS:
        _fail("REVIEW_FIELDS_INVALID")
    if set(payload) & _FORBIDDEN_KEYS or _forbidden_nested(payload):
        _fail("REVIEW_PRIVACY_FIELD")
    if payload["schema"] != REVIEW_SCHEMA:
        _fail("REVIEW_SCHEMA_INVALID")
    for key, code in (("review_id", "REVIEW_ID_INVALID"), ("source_id", "REVIEW_SOURCE_ID_INVALID"),
                      ("asset_id", "REVIEW_ASSET_ID_INVALID"), ("reviewer_id", "REVIEWER_ID_INVALID"),
                      ("reviewer_role", "REVIEWER_ROLE_INVALID")):
        _id(payload[key], code)
    _digest(payload["scope_digest"], "REVIEW_SCOPE_INVALID")
    _digest(payload["candidate_digest"], "REVIEW_CANDIDATE_DIGEST_INVALID")
    _digest(payload["receipt_digest"], "REVIEW_RECEIPT_DIGEST_INVALID")
    _digest(payload["attestation_digest"], "REVIEW_ATTESTATION_INVALID")
    if payload["document_id"] is not None:
        _id(payload["document_id"], "REVIEW_DOCUMENT_ID_INVALID")
    chunks = payload["chunk_ids"]
    if not isinstance(chunks, list) or any(not isinstance(item, str) or not _ID.fullmatch(item) for item in chunks):
        _fail("REVIEW_CHUNK_IDS_INVALID")
    if not isinstance(payload["sampling_plan"], Mapping) or not payload["sampling_plan"]:
        _fail("REVIEW_SAMPLING_PLAN_INVALID")
    signed = payload["signed_at"]
    try:
        parsed = datetime.fromisoformat(str(signed).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewError("REVIEW_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        _fail("REVIEW_TIMESTAMP_INVALID")
    if payload["decision"] not in _ALLOWED_DECISIONS:
        _fail("REVIEW_DECISION_INVALID")
    refs = payload["evidence_refs"]
    if not isinstance(refs, list) or not refs or any(not isinstance(item, str) or not _ID.fullmatch(item) for item in refs):
        _fail("REVIEW_EVIDENCE_REFS_INVALID")
    supersedes = payload["supersedes"]
    if supersedes is not None:
        _id(supersedes, "REVIEW_SUPERSESSION_INVALID")
    if not isinstance(payload["comment"], str) or len(payload["comment"]) > 500:
        _fail("REVIEW_COMMENT_INVALID")
    return ReviewRecord(
        review_id=payload["review_id"], scope_digest=payload["scope_digest"],
        source_id=payload["source_id"], asset_id=payload["asset_id"],
        document_id=payload["document_id"], chunk_ids=tuple(payload["chunk_ids"]),
        candidate_digest=payload["candidate_digest"], receipt_digest=payload["receipt_digest"],
        reviewer_id=payload["reviewer_id"], reviewer_role=payload["reviewer_role"],
        sampling_plan=dict(payload["sampling_plan"]), signed_at=str(payload["signed_at"]),
        attestation_digest=payload["attestation_digest"], decision=payload["decision"],
        evidence_refs=tuple(payload["evidence_refs"]), supersedes=supersedes,
        comment=payload["comment"],
    )


def _forbidden_nested(value: Any) -> bool:
    if isinstance(value, Mapping):
        return bool(set(value) & _FORBIDDEN_KEYS) or any(_forbidden_nested(item) for item in value.values())
    if isinstance(value, list):
        return any(_forbidden_nested(item) for item in value)
    return False


def validate_review_history(records: Sequence[Mapping[str, Any]]) -> tuple[ReviewRecord, ...]:
    """Require append-only review records and explicit supersession for conflicts."""
    validated = tuple(validate_review_record(item) for item in records)
    ids = {record.review_id for record in validated}
    if len(ids) != len(validated):
        _fail("REVIEW_DUPLICATE_ID")
    by_target: dict[tuple[str, str], list[ReviewRecord]] = {}
    for record in validated:
        by_target.setdefault((record.source_id, record.asset_id), []).append(record)
    for group in by_target.values():
        decisions = {item.decision for item in group}
        if len(decisions) > 1 and not any(item.supersedes in {other.review_id for other in group if other is not item} for item in group):
            _fail("REVIEW_CONFLICT_UNRESOLVED")
    return validated


def gate0_status(*, required_assets: Sequence[tuple[str, str]], reviews: Sequence[Mapping[str, Any]],
                 acquisition_receipts: Sequence[Mapping[str, Any]], authority_present: bool,
                 scope_digest: str) -> dict[str, Any]:
    """Create a privacy-safe, read-only legacy Gate 0 status projection.

    Reviews and acquisition receipts are deliberately checked as independent
    evidence categories.  A receipt cannot substitute for a human review, and
    vice versa.  Formal per-category evidence is supplied to ``m11_gate0``.
    """
    if not isinstance(scope_digest, str) or not _HEX.fullmatch(scope_digest):
        _fail("GATE0_SCOPE_INVALID")
    validated_reviews = validate_review_history(reviews)
    required = {tuple(item) for item in required_assets}
    reviewed = {
        (item.source_id, item.asset_id)
        for item in validated_reviews
        if item.scope_digest == scope_digest
        and item.decision == "ACCEPT_FOR_PROMOTION_REVIEW"
    }
    receipts = {
        (str(item.get("source_id")), str(item.get("asset_id")))
        for item in acquisition_receipts
        if isinstance(item, Mapping)
        and item.get("scope_digest") == scope_digest
        and item.get("status") == "ACQUIRED"
    }
    missing_review = required - reviewed
    missing_receipt = required - receipts
    missing = missing_review | missing_receipt
    status = "PASS" if authority_present and not missing else "BLOCKED"
    return {
        "schema": GATE0_SCHEMA, "status": status, "scope_digest": scope_digest,
        "required_asset_count": len(required), "reviewed_asset_count": len(reviewed),
        "receipt_asset_count": len(receipts), "missing_asset_count": len(missing),
        "missing_asset_keys": [hashlib.sha256("\\0".join(item).encode()).hexdigest()[:16]
                               for item in sorted(missing)],
        "candidate_promotion_authorized": False, "publication_authorized": False,
    }
