"""Read-only Formal Gate 0 evidence evaluation for M11 P0."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from .m11_acquisition import (
    AcquisitionError,
    FrozenAsset,
    validate_receipt,
    validate_receipt_batch,
)
from .m11_execution_authority import (
    ExecutionAuthorityError,
    assert_batch_authorized,
    validate_execution_authority,
)
from .m11_review import ReviewError, validate_review_history

GATE0_SCHEMA = "sa.m11.gate0-evidence-package.v1"
GATE0_VERSION = "m11-gate0-v1"
EVIDENCE_CATEGORIES = (
    "license",
    "revision",
    "robots_terms",
    "notice_ipr",
    "schema",
    "provenance",
    "parser",
    "content_quality",
)
_VALID_EVIDENCE = frozenset({"VERIFIED", "NOT_APPLICABLE", "PENDING", "FAILED"})
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*\Z")
_FORBIDDEN = frozenset({
    "body", "content", "text", "raw_path", "host_path", "credentials", "password",
    "token", "learning_state", "private_learning_state", "signature",
})


class Gate0Error(ValueError):
    """A Gate 0 input is malformed, incomplete, or explicitly failed."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def gate0_digest(payload: Mapping[str, Any]) -> str:
    """Return a deterministic digest for a metadata-only Gate 0 package."""
    try:
        encoded = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise Gate0Error("GATE0_DIGEST_INVALID") from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _fail(code: str) -> None:
    raise Gate0Error(code)


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and bool(_ID.fullmatch(value))


def _privacy_scan(value: Any) -> bool:
    if isinstance(value, Mapping):
        if set(value) & _FORBIDDEN:
            return True
        return any(_privacy_scan(item) for item in value.values())
    if isinstance(value, list):
        return any(_privacy_scan(item) for item in value)
    return False


def _asset_key(value: tuple[str, str]) -> str:
    return hashlib.sha256("\\0".join(value).encode("utf-8")).hexdigest()[:16]


def _timestamp(value: Any) -> str:
    if not isinstance(value, str):
        _fail("GATE0_SIGNED_AT_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Gate0Error("GATE0_SIGNED_AT_INVALID") from exc
    if parsed.tzinfo is None:
        _fail("GATE0_SIGNED_AT_INVALID")
    return value


def _assert_receipt_captured_under_authority(receipt: Any, authority: Any) -> None:
    try:
        captured_at = datetime.fromisoformat(receipt.captured_at.replace("Z", "+00:00"))
        issued_at = datetime.fromisoformat(authority.issued_at.replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(authority.expires_at.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise Gate0Error("GATE0_RECEIPT_CAPTURED_AT_INVALID") from exc
    if captured_at.tzinfo is None:
        _fail("GATE0_RECEIPT_CAPTURED_AT_INVALID")
    if captured_at < issued_at or captured_at >= expires_at:
        _fail("GATE0_RECEIPT_AUTHORITY_WINDOW_INVALID")


def _normalize_assets(required_assets: Sequence[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    normalized = []
    for item in required_assets:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            _fail("GATE0_ASSET_INVALID")
        source_id, asset_id = item
        if not _valid_id(source_id) or not _valid_id(asset_id):
            _fail("GATE0_ASSET_INVALID")
        normalized.append((source_id, asset_id))
    if len(set(normalized)) != len(normalized):
        _fail("GATE0_ASSET_DUPLICATE")
    return tuple(sorted(normalized))


def _status_for_asset(
    key: tuple[str, str],
    evidence: Mapping[tuple[str, str], Mapping[str, Any]],
) -> tuple[set[str], set[str], set[str]]:
    record = evidence.get(key)
    if not isinstance(record, Mapping) or set(record) != set(EVIDENCE_CATEGORIES):
        return set(EVIDENCE_CATEGORIES), set(), set()
    missing: set[str] = set()
    failed: set[str] = set()
    pending: set[str] = set()
    for category in EVIDENCE_CATEGORIES:
        status = record[category]
        if status not in _VALID_EVIDENCE:
            missing.add(category)
        elif status == "FAILED":
            failed.add(category)
        elif status == "PENDING":
            pending.add(category)
        elif status not in {"VERIFIED", "NOT_APPLICABLE"}:
            missing.add(category)
    return missing, failed, pending


def _gate0_input_digest(
    *,
    assets: tuple[tuple[str, str], ...],
    evidence: Mapping[tuple[str, str], Mapping[str, Any]],
    reviews: Sequence[Any],
    receipts: Sequence[Any],
    candidate_validated: Mapping[tuple[str, str], bool],
    authority: Mapping[str, Any],
    acquisition_authority: Mapping[str, Any] | None,
    lifecycle_counts: Mapping[str, int],
    scope_digest: str,
) -> str:
    """Bind the result digest to every validated metadata input, not only scope."""
    evidence_items = [
        {"source_id": source_id, "asset_id": asset_id, "categories": dict(sorted(record.items()))}
        for (source_id, asset_id), record in sorted(evidence.items())
    ]
    candidate_items = [
        {"source_id": source_id, "asset_id": asset_id, "validated": value}
        for (source_id, asset_id), value in sorted(candidate_validated.items())
    ]
    return gate0_digest({
        "assets": assets,
        "scope_digest": scope_digest,
        "evidence": evidence_items,
        "reviews": [item.as_dict() for item in reviews],
        "acquisition_receipts": [item.as_dict() for item in receipts],
        "candidate_validated": candidate_items,
        "authority": dict(sorted(authority.items())),
        "acquisition_authority": (
            dict(sorted(acquisition_authority.items()))
            if acquisition_authority is not None
            else None
        ),
        "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
    })


def _assert_keyed_scope(
    values: Mapping[Any, Any],
    assets: tuple[tuple[str, str], ...],
    code: str,
) -> None:
    allowed = set(assets)
    for key in values:
        if not isinstance(key, tuple) or len(key) != 2 or key not in allowed:
            _fail(code)


def run_gate0(
    *,
    required_assets: Sequence[tuple[str, str]],
    evidence: Mapping[tuple[str, str], Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    acquisition_receipts: Sequence[Mapping[str, Any]],
    candidate_validated: Mapping[tuple[str, str], bool],
    frozen_assets: Mapping[tuple[str, str], FrozenAsset] | None = None,
    authority: Mapping[str, Any],
    acquisition_authority: Mapping[str, Any] | None = None,
    scope_digest: str,
    lifecycle_counts: Mapping[str, int],
    owner_id: str,
    signed_at: str,
) -> dict[str, Any]:
    """Evaluate formal Gate 0 without changing any lifecycle state."""
    if not isinstance(scope_digest, str) or not _HEX.fullmatch(scope_digest):
        _fail("GATE0_SCOPE_INVALID")
    if not _valid_id(owner_id):
        _fail("GATE0_OWNER_INVALID")
    _timestamp(signed_at)
    if (
        _privacy_scan(evidence)
        or _privacy_scan(lifecycle_counts)
        or _privacy_scan(authority)
        or _privacy_scan(acquisition_authority)
    ):
        _fail("GATE0_PRIVACY_FIELD")
    assets = _normalize_assets(required_assets)
    if not isinstance(evidence, Mapping) or not isinstance(candidate_validated, Mapping):
        _fail("GATE0_EVIDENCE_INVALID")
    _assert_keyed_scope(evidence, assets, "GATE0_EVIDENCE_OUT_OF_SCOPE")
    _assert_keyed_scope(candidate_validated, assets, "GATE0_CANDIDATE_OUT_OF_SCOPE")
    if not isinstance(lifecycle_counts, Mapping) or any(
        not isinstance(key, str) or not isinstance(value, int) or isinstance(value, bool) or value < 0
        for key, value in lifecycle_counts.items()
    ):
        _fail("GATE0_LIFECYCLE_COUNTS_INVALID")
    try:
        signed_datetime = datetime.fromisoformat(signed_at.replace("Z", "+00:00"))
        validated_authority = validate_execution_authority(
            authority,
            operation="gate0",
            expected_scope_digest=scope_digest,
            now=signed_datetime,
        )
        assert_batch_authorized(
            validated_authority,
            {source_id: [asset_id for source, asset_id in assets if source == source_id]
             for source_id in validated_authority.source_ids},
        )
    except ExecutionAuthorityError as exc:
        raise Gate0Error("GATE0_AUTHORITY_INVALID") from exc
    try:
        receipt_authority = validated_authority
        if acquisition_authority is not None:
            receipt_authority = validate_execution_authority(
                acquisition_authority,
                operation="acquisition",
                expected_scope_digest=scope_digest,
            )
            assert_batch_authorized(
                receipt_authority,
                {source_id: [asset_id for source, asset_id in assets if source == source_id]
                 for source_id in receipt_authority.source_ids},
            )
    except ExecutionAuthorityError as exc:
        raise Gate0Error("GATE0_ACQUISITION_AUTHORITY_INVALID") from exc

    try:
        validated_reviews = validate_review_history(reviews)
    except ReviewError as exc:
        raise Gate0Error("GATE0_REVIEWS_INVALID") from exc
    reviewed = {
        (item.source_id, item.asset_id)
        for item in validated_reviews
        if item.scope_digest == scope_digest and item.decision == "ACCEPT_FOR_PROMOTION_REVIEW"
    }

    try:
        parsed_receipts = tuple(validate_receipt(payload) for payload in acquisition_receipts)
        if acquisition_authority is not None:
            for receipt in parsed_receipts:
                _assert_receipt_captured_under_authority(receipt, receipt_authority)
        receipt_assets = None
        if frozen_assets is not None:
            if set(frozen_assets) != set(assets):
                _fail("GATE0_ASSETS_INVALID")
            receipt_assets = dict(frozen_assets)
        if receipt_assets is not None:
            validated_receipts = list(
                validate_receipt_batch(
                    parsed_receipts,
                    receipt_assets,
                    authority=receipt_authority,
                )
            )
        else:
            expected = set(assets)
            seen: set[tuple[str, str]] = set()
            validated_receipts = []
            for receipt in parsed_receipts:
                key = (receipt.source_id, receipt.asset_id)
                if key not in expected:
                    _fail("GATE0_RECEIPT_OUT_OF_SCOPE")
                if key in seen:
                    _fail("GATE0_RECEIPT_DUPLICATE")
                if receipt.scope_digest != scope_digest:
                    _fail("GATE0_RECEIPT_SCOPE_MISMATCH")
                if receipt.authority_id != receipt_authority.authority_id:
                    _fail("GATE0_RECEIPT_AUTHORITY_MISMATCH")
                try:
                    assert_batch_authorized(
                        receipt_authority,
                        {receipt.source_id: [receipt.asset_id]},
                    )
                except ExecutionAuthorityError as exc:
                    raise Gate0Error("GATE0_RECEIPT_OUT_OF_SCOPE") from exc
                seen.add(key)
                validated_receipts.append(receipt)
    except (AcquisitionError, Gate0Error) as exc:
        if isinstance(exc, Gate0Error):
            raise
        raise Gate0Error("GATE0_RECEIPTS_INVALID") from exc
    receipts = {
        (item.source_id, item.asset_id)
        for item in validated_receipts
        if item.status == "ACQUIRED"
    }

    missing_evidence: dict[tuple[str, str], set[str]] = {}
    failed_evidence: dict[tuple[str, str], set[str]] = {}
    pending_evidence: dict[tuple[str, str], set[str]] = {}
    missing_review: set[tuple[str, str]] = set()
    missing_receipt: set[tuple[str, str]] = set()
    missing_candidate: set[tuple[str, str]] = set()
    for key in assets:
        missing, failed, pending = _status_for_asset(key, evidence)
        if missing:
            missing_evidence[key] = missing
        if failed:
            failed_evidence[key] = failed
        if pending:
            pending_evidence[key] = pending
        if key not in reviewed:
            missing_review.add(key)
        if key not in receipts:
            missing_receipt.add(key)
        if candidate_validated.get(key) is not True:
            missing_candidate.add(key)
    blocked = bool(
        missing_evidence or pending_evidence or missing_review
        or missing_receipt or missing_candidate
    )
    failed = bool(failed_evidence)
    status = "FAIL" if failed else "BLOCKED" if blocked else "PASS"
    missing_keys = set(missing_evidence) | set(pending_evidence) | missing_review | missing_receipt | missing_candidate
    failed_keys = set(failed_evidence)
    return {
        "schema": GATE0_SCHEMA,
        "version": GATE0_VERSION,
        "status": status,
        "scope_digest": scope_digest,
        "input_digest": _gate0_input_digest(
            assets=assets,
            evidence=evidence,
            reviews=validated_reviews,
            receipts=validated_receipts,
            candidate_validated=candidate_validated,
            authority=authority,
            acquisition_authority=acquisition_authority,
            lifecycle_counts=lifecycle_counts,
            scope_digest=scope_digest,
        ),
        "required_asset_count": len(assets),
        "reviewed_asset_count": len(reviewed & set(assets)),
        "receipt_asset_count": len(receipts & set(assets)),
        "candidate_validated_count": len(set(assets) - missing_candidate),
        "missing_asset_count": len(missing_keys),
        "missing_asset_keys": sorted(_asset_key(key) for key in missing_keys),
        "failed_asset_keys": sorted(_asset_key(key) for key in failed_keys),
        "evidence_categories": list(EVIDENCE_CATEGORIES),
        "lifecycle_counts_before": dict(sorted(lifecycle_counts.items())),
        "owner_id": owner_id,
        "signed_at": signed_at,
        "authority_id": validated_authority.authority_id,
        "acquisition_authority_id": receipt_authority.authority_id,
        "authority_present": True,
        "candidate_promotion_authorized": False,
        "publication_authorized": False,
    }


__all__ = [
    "EVIDENCE_CATEGORIES", "GATE0_SCHEMA", "Gate0Error", "gate0_digest", "run_gate0",
]
