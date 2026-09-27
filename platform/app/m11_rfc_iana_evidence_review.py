"""Strict offline contract for the M11 RFC/IANA exact-six evidence review."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from app.m11_acquisition import AcquisitionError, validate_receipt
from app.m11_evidence_closure import EvidenceClosureError, validate_closure_bundle
from app.m11_execution_authority import ExecutionAuthorityError, validate_execution_authority
from app.m11_gate0 import EVIDENCE_CATEGORIES
from app.m11_official_observation import OfficialObservationError, validate_official_observation_bundle
from app.m11_review import ReviewError, gate0_status, validate_review_history

APPLICATION_SCHEMA = "sa.m11.p0.rfc-iana-evidence-review-application.v1"
RESULT_SCHEMA = "sa.m11.p0.rfc-iana-evidence-review-result.v1"
PARENT_SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
EXACT_ASSETS = {
    "iana-registries": (
        "service-names-port-numbers-csv",
        "service-names-port-numbers-txt",
        "service-names-port-numbers-xml",
    ),
    "rfc-editor-index": ("rfc1034", "rfc9110", "rfc9293"),
}
CURRENT_OFFICIAL_HEAD_IDS = {
    (source_id, asset_id): f"m11-hr-20260926-official-observation-{asset_id}"
    for source_id, asset_ids in EXACT_ASSETS.items()
    for asset_id in asset_ids
}
RESULT = "REVIEW_REQUIRED"
CLOSURE_EFFECT = "NONE"
XML_CONFLICT_STATUS = "UNRESOLVED"
TXT_PARSER_STATE = "FAIL_CLOSED"
BATCH_DIGEST_DOMAIN = "sa.m11.p0.rfc-iana-evidence-review.batch.v1"
AUTHORITY_RECORD = "data/manifests/m11-p0-rfc-iana-evidence-review-authority-v1.json"
TXT_COMMENT = (
    "DEFER: exact-six evidence review leaves all eight categories PENDING; "
    "TXT parsing remains fail-closed; closure effect is NONE and Gate 0 remains blocked."
)

_HEX = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*")
_DRIVE_PATH = re.compile(r"(?i)(?<![A-Za-z0-9])[a-z]:[\\/]")
_UNC_PATH = re.compile(r"(?<![\\/])(?:\\\\|//)[^\\/\s]+[\\/][^\\/\s]+")
_POSIX_HOST_PATH = re.compile(r"(?<![A-Za-z0-9.])/(?:home|users|private|root|tmp|var/tmp)/", re.IGNORECASE)
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "bodies",
        "content",
        "contents",
        "raw",
        "raw_text",
        "raw_path",
        "host_path",
        "local_path",
        "absolute_path",
        "credentials",
        "token",
    }
)
_BATCH_FIELDS = frozenset(
    {"source_id", "asset_id", "candidate_digest", "receipt_digest", "revision"}
)
_APPLICATION_FIELDS = frozenset(
    {
        "schema",
        "application_id",
        "authority_id",
        "parent_scope_digest",
        "batch_digest",
        "source_ids",
        "asset_ids",
        "asset_count",
        "submitted_by",
        "submitted_at",
        "operation",
        "metadata_only",
        "network_used",
        "source_expansion",
        "lifecycle_mutation",
        "host_paths_included",
        "bodies_included",
        "batch_records",
    }
)
_RESULT_FIELDS = frozenset(
    {
        "schema",
        "result_id",
        "application_id",
        "authority_id",
        "parent_scope_digest",
        "batch_digest",
        "prior_closure_matrix_id",
        "official_observation_id",
        "prior_review_slice_id",
        "successor_slice_id",
        "source_ids",
        "asset_count",
        "result",
        "closure_effect",
        "xml_conflict_status",
        "txt_parser_state",
        "formal_gate0_executed",
        "formal_3k_executed",
        "candidate_approval_granted",
        "publication_authorized",
        "network_used",
        "source_expansion",
        "lifecycle_mutation",
        "host_paths_included",
        "bodies_included",
        "records",
    }
)
_RESULT_RECORD_FIELDS = _BATCH_FIELDS | {"evidence"}
_ESCALATION_FLAGS = (
    "network_used",
    "source_expansion",
    "lifecycle_mutation",
    "host_paths_included",
    "bodies_included",
)
_RESULT_ESCALATION_FLAGS = (
    "formal_gate0_executed",
    "formal_3k_executed",
    "candidate_approval_granted",
    "publication_authorized",
    *_ESCALATION_FLAGS,
)
_REVIEW_WRAPPER_FIELDS = frozenset(
    {
        "schema",
        "slice_id",
        "authority_id",
        "authority_record",
        "scope_digest",
        "source_ids",
        "asset_count",
        "remaining_in_batch",
        "decision",
        "reviewer_id",
        "signed_at",
        "formal_gate0_executed",
        "candidate_approval_granted",
        "publication_authorized",
        "network_used",
        "source_expansion",
        "lifecycle_mutation",
        "host_paths_included",
        "bodies_included",
        "records",
    }
)


class RfcIanaEvidenceReviewError(ValueError):
    """Stable validation failure for the exact-six evidence-review contract."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise RfcIanaEvidenceReviewError(code)


def _privacy(value: Any) -> bool:
    if isinstance(value, Mapping):
        if set(value) & _FORBIDDEN_KEYS:
            return True
        return any(_privacy(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_privacy(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return bool(
            _DRIVE_PATH.search(value)
            or _UNC_PATH.search(value)
            or _POSIX_HOST_PATH.search(value)
            or "111_others" in lowered
        )
    return False


def _timestamp(value: Any, code: str) -> datetime:
    if not isinstance(value, str) or not value or value != value.strip():
        _fail(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RfcIanaEvidenceReviewError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(code)
    return parsed.astimezone(timezone.utc)


def _id(value: Any, code: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip() or not _ID.fullmatch(value):
        _fail(code)


def _digest(value: Any, code: str) -> None:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail(code)


def _expected_pairs() -> set[tuple[str, str]]:
    return {
        (source_id, asset_id)
        for source_id, asset_ids in EXACT_ASSETS.items()
        for asset_id in asset_ids
    }


def _canonical_batch_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        _fail("RFC_IANA_BATCH_RECORDS_INVALID")
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, Mapping) or set(record) != _BATCH_FIELDS:
            _fail("RFC_IANA_BATCH_RECORD_FIELDS_INVALID")
        source_id = record["source_id"]
        asset_id = record["asset_id"]
        _id(source_id, "RFC_IANA_BATCH_SOURCE_INVALID")
        _id(asset_id, "RFC_IANA_BATCH_ASSET_INVALID")
        key = (source_id, asset_id)
        if key in seen:
            _fail("RFC_IANA_BATCH_DUPLICATE_ASSET")
        seen.add(key)
        for field in ("candidate_digest", "receipt_digest", "revision"):
            _digest(record[field], "RFC_IANA_BATCH_IDENTITY_INVALID")
        normalized.append({field: str(record[field]) for field in _BATCH_FIELDS})
    if seen != _expected_pairs():
        _fail("RFC_IANA_BATCH_SCOPE_INVALID")
    return sorted(normalized, key=lambda item: (item["source_id"], item["asset_id"]))


def exact_six_batch_digest(records: Sequence[Mapping[str, Any]]) -> str:
    """Bind the parent scope and sorted exact-six identity under a versioned domain."""
    payload = {
        "domain": BATCH_DIGEST_DOMAIN,
        "parent_scope_digest": PARENT_SCOPE_DIGEST,
        "records": _canonical_batch_records(records),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_evidence_review_application(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and detach an exact-six, metadata-only review application."""
    if not isinstance(payload, Mapping) or set(payload) != _APPLICATION_FIELDS:
        _fail("RFC_IANA_APPLICATION_FIELDS_INVALID")
    if _privacy(payload):
        _fail("RFC_IANA_APPLICATION_PRIVACY_FIELD")
    if payload["schema"] != APPLICATION_SCHEMA:
        _fail("RFC_IANA_APPLICATION_SCHEMA_INVALID")
    for field in ("application_id", "authority_id", "submitted_by"):
        _id(payload[field], "RFC_IANA_APPLICATION_ID_INVALID")
    _timestamp(payload["submitted_at"], "RFC_IANA_APPLICATION_TIMESTAMP_INVALID")
    if payload["operation"] != "human_review" or payload["metadata_only"] is not True:
        _fail("RFC_IANA_APPLICATION_OPERATION_INVALID")
    if payload["parent_scope_digest"] != PARENT_SCOPE_DIGEST:
        _fail("RFC_IANA_PARENT_SCOPE_CHANGED")
    _digest(payload["batch_digest"], "RFC_IANA_BATCH_DIGEST_INVALID")
    if payload["source_ids"] != list(EXACT_ASSETS):
        _fail("RFC_IANA_APPLICATION_SOURCE_SCOPE_INVALID")
    expected_assets = {source: list(assets) for source, assets in EXACT_ASSETS.items()}
    if payload["asset_ids"] != expected_assets or payload["asset_count"] != 6:
        _fail("RFC_IANA_APPLICATION_ASSET_SCOPE_INVALID")
    if any(payload[field] is not False for field in _ESCALATION_FLAGS):
        _fail("RFC_IANA_APPLICATION_ESCALATION_FLAG")
    if exact_six_batch_digest(payload["batch_records"]) != payload["batch_digest"]:
        _fail("RFC_IANA_BATCH_DIGEST_MISMATCH")
    return copy.deepcopy(dict(payload))


def _validate_result_evidence(evidence: Any) -> None:
    if not isinstance(evidence, Mapping) or set(evidence) != set(EVIDENCE_CATEGORIES):
        _fail("RFC_IANA_RESULT_EVIDENCE_CATEGORIES_INVALID")
    for category in EVIDENCE_CATEGORIES:
        entry = evidence[category]
        if not isinstance(entry, Mapping) or set(entry) != {"status", "refs", "comment"}:
            _fail("RFC_IANA_RESULT_EVIDENCE_FIELDS_INVALID")
        if entry["status"] != "PENDING":
            _fail("RFC_IANA_RESULT_EVIDENCE_NOT_PENDING")
        if not isinstance(entry["refs"], list) or any(
            not isinstance(ref, str) or not _ID.fullmatch(ref) for ref in entry["refs"]
        ):
            _fail("RFC_IANA_RESULT_EVIDENCE_REFS_INVALID")
        if not isinstance(entry["comment"], str) or not entry["comment"].strip() or len(entry["comment"]) > 500:
            _fail("RFC_IANA_RESULT_EVIDENCE_COMMENT_INVALID")


def validate_evidence_review_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and detach the non-closing exact-six review result."""
    if not isinstance(payload, Mapping) or set(payload) != _RESULT_FIELDS:
        _fail("RFC_IANA_RESULT_FIELDS_INVALID")
    if _privacy(payload):
        _fail("RFC_IANA_RESULT_PRIVACY_FIELD")
    if payload["schema"] != RESULT_SCHEMA:
        _fail("RFC_IANA_RESULT_SCHEMA_INVALID")
    for field in (
        "result_id",
        "application_id",
        "authority_id",
        "prior_closure_matrix_id",
        "official_observation_id",
        "prior_review_slice_id",
        "successor_slice_id",
    ):
        _id(payload[field], "RFC_IANA_RESULT_ID_INVALID")
    if payload["parent_scope_digest"] != PARENT_SCOPE_DIGEST:
        _fail("RFC_IANA_PARENT_SCOPE_CHANGED")
    _digest(payload["batch_digest"], "RFC_IANA_BATCH_DIGEST_INVALID")
    if payload["source_ids"] != list(EXACT_ASSETS) or payload["asset_count"] != 6:
        _fail("RFC_IANA_RESULT_SCOPE_INVALID")
    if payload["result"] != RESULT or payload["closure_effect"] != CLOSURE_EFFECT:
        _fail("RFC_IANA_RESULT_STATE_INVALID")
    if payload["xml_conflict_status"] != XML_CONFLICT_STATUS:
        _fail("RFC_IANA_XML_CONFLICT_CHANGED")
    if payload["txt_parser_state"] != TXT_PARSER_STATE:
        _fail("RFC_IANA_TXT_PARSER_FAIL_OPEN")
    if any(payload[field] is not False for field in _RESULT_ESCALATION_FLAGS):
        _fail("RFC_IANA_RESULT_ESCALATION_FLAG")
    records = payload["records"]
    if not isinstance(records, list) or len(records) != 6:
        _fail("RFC_IANA_RESULT_RECORD_COUNT_INVALID")
    batch_records: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping) or set(record) != _RESULT_RECORD_FIELDS:
            _fail("RFC_IANA_RESULT_RECORD_FIELDS_INVALID")
        _validate_result_evidence(record["evidence"])
        batch_records.append({field: record[field] for field in _BATCH_FIELDS})
    if exact_six_batch_digest(batch_records) != payload["batch_digest"]:
        _fail("RFC_IANA_BATCH_DIGEST_MISMATCH")
    return copy.deepcopy(dict(payload))


def _receipt_digest(receipt: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(receipt), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_successor_wrapper(
    wrapper: Mapping[str, Any], *, result: Mapping[str, Any], authority_id: str
) -> datetime:
    if not isinstance(wrapper, Mapping) or set(wrapper) != _REVIEW_WRAPPER_FIELDS:
        _fail("RFC_IANA_SUCCESSOR_WRAPPER_INVALID")
    if _privacy(wrapper):
        _fail("RFC_IANA_SUCCESSOR_PRIVACY_FIELD")
    expected_sources = list(EXACT_ASSETS)
    if (
        wrapper["schema"] != "sa.m11.p0.human-review-slice.v1"
        or wrapper["slice_id"] != result["successor_slice_id"]
        or wrapper["authority_id"] != authority_id
        or wrapper["authority_record"] != AUTHORITY_RECORD
        or wrapper["scope_digest"] != PARENT_SCOPE_DIGEST
        or wrapper["source_ids"] != expected_sources
        or wrapper["asset_count"] != 6
        or wrapper["remaining_in_batch"] != 0
        or wrapper["decision"] != "DEFER"
    ):
        _fail("RFC_IANA_SUCCESSOR_WRAPPER_INVALID")
    for flag in (
        "formal_gate0_executed",
        "candidate_approval_granted",
        "publication_authorized",
        *_ESCALATION_FLAGS,
    ):
        if wrapper[flag] is not False:
            _fail("RFC_IANA_SUCCESSOR_ESCALATION_FLAG")
    return _timestamp(wrapper["signed_at"], "RFC_IANA_SUCCESSOR_TIMESTAMP_INVALID")


def _validate_rfc_iana_evidence_review_bundle(
    application: Mapping[str, Any],
    *,
    authority: Mapping[str, Any],
    result: Mapping[str, Any],
    digest_assets: Sequence[Mapping[str, Any]],
    digest_robots: Sequence[Mapping[str, Any]],
    receipts: Sequence[Mapping[str, Any]],
    closure_matrix: Mapping[str, Any],
    acquisition_review_wrapper: Mapping[str, Any],
    closure_review_wrapper: Mapping[str, Any],
    official_observation: Mapping[str, Any],
    official_authority: Mapping[str, Any],
    official_review_wrapper: Mapping[str, Any],
    successor_wrapper: Mapping[str, Any],
) -> dict[str, Any]:
    """Cross-check the full predecessor chain and exact-six append-only batch."""
    validated_application = validate_evidence_review_application(application)
    validated_result = validate_evidence_review_result(result)
    if (
        validated_result["application_id"] != validated_application["application_id"]
        or validated_result["authority_id"] != validated_application["authority_id"]
        or validated_result["batch_digest"] != validated_application["batch_digest"]
    ):
        _fail("RFC_IANA_APPLICATION_RESULT_LINK_INVALID")

    try:
        validated_authority = validate_execution_authority(
            authority,
            operation="human_review",
            expected_scope_digest=PARENT_SCOPE_DIGEST,
            allowed_source_ids=EXACT_ASSETS,
            now=_timestamp(
                validated_application["submitted_at"],
                "RFC_IANA_APPLICATION_TIMESTAMP_INVALID",
            ),
        )
    except ExecutionAuthorityError as exc:
        if exc.code in {"AUTHORITY_SOURCE_SCOPE_INVALID", "AUTHORITY_ASSET_SCOPE_INVALID"}:
            _fail("RFC_IANA_AUTHORITY_NOT_EXACT_SIX")
        raise
    if validated_authority.authority_id != validated_application["authority_id"]:
        _fail("RFC_IANA_AUTHORITY_LINK_INVALID")
    authority_assets = {
        source_id: tuple(sorted(validated_authority.assets_for(source_id)))
        for source_id in validated_authority.source_ids
    }
    if set(validated_authority.source_ids) != set(EXACT_ASSETS) or authority_assets != EXACT_ASSETS:
        _fail("RFC_IANA_AUTHORITY_NOT_EXACT_SIX")

    all_expected: list[tuple[str, str]] = []
    for item in digest_assets:
        if not isinstance(item, Mapping):
            _fail("RFC_IANA_PREDECESSOR_SCOPE_INVALID")
        source_id = item.get("source_id")
        asset_id = item.get("asset_id")
        if not isinstance(source_id, str) or not isinstance(asset_id, str):
            _fail("RFC_IANA_PREDECESSOR_SCOPE_INVALID")
        all_expected.append((str(source_id), str(asset_id)))
    if len(all_expected) != 26 or len(set(all_expected)) != 26:
        _fail("RFC_IANA_PREDECESSOR_SCOPE_INVALID")
    for wrapper in (
        acquisition_review_wrapper,
        closure_review_wrapper,
        official_review_wrapper,
    ):
        if not isinstance(wrapper, Mapping):
            _fail("RFC_IANA_PREDECESSOR_WRAPPER_INVALID")
    closure_reviews = closure_review_wrapper.get("records", ())
    closure = validate_closure_bundle(
        closure_matrix,
        digest_assets=digest_assets,
        receipts=receipts,
        reviews=closure_reviews,
        prior_reviews=acquisition_review_wrapper.get("records", ()),
        expected_assets=all_expected,
    )
    official_reviews = official_review_wrapper.get("records", ())
    observation = validate_official_observation_bundle(
        official_observation,
        digest_assets=digest_assets,
        receipts=receipts,
        closure_matrix=closure_matrix,
        closure_reviews=closure_reviews,
        successor_reviews=official_reviews,
        expected_assets=all_expected,
        authority=official_authority,
        successor_wrapper=official_review_wrapper,
        prior_review_wrapper=closure_review_wrapper,
        robots=digest_robots,
    )
    if (
        closure["scope_digest"] != PARENT_SCOPE_DIGEST
        or validated_result["prior_closure_matrix_id"] != closure["matrix_id"]
        or validated_result["official_observation_id"] != observation["observation_id"]
        or validated_result["prior_review_slice_id"] != official_review_wrapper.get("slice_id")
    ):
        _fail("RFC_IANA_PREDECESSOR_LINK_INVALID")

    expected = _expected_pairs()
    digest_by_key = {
        (item.get("source_id"), item.get("asset_id")): item
        for item in digest_assets
        if isinstance(item, Mapping) and (item.get("source_id"), item.get("asset_id")) in expected
    }
    receipt_by_key = {
        (item.get("source_id"), item.get("asset_id")): item
        for item in receipts
        if isinstance(item, Mapping) and (item.get("source_id"), item.get("asset_id")) in expected
    }
    if set(digest_by_key) != expected or set(receipt_by_key) != expected:
        _fail("RFC_IANA_DEPENDENCY_SCOPE_INVALID")
    for receipt in receipt_by_key.values():
        validated_receipt = validate_receipt(receipt)
        if validated_receipt.status != "ACQUIRED" or validated_receipt.scope_digest != PARENT_SCOPE_DIGEST:
            _fail("RFC_IANA_RECEIPT_INVALID")

    closure_by_key = {
        (item["source_id"], item["asset_id"]): item
        for item in closure["records"]
        if (item["source_id"], item["asset_id"]) in expected
    }
    result_by_key = {
        (item["source_id"], item["asset_id"]): item for item in validated_result["records"]
    }
    if set(closure_by_key) != expected or set(result_by_key) != expected:
        _fail("RFC_IANA_RESULT_SCOPE_INVALID")

    application_by_key = {
        (item["source_id"], item["asset_id"]): item
        for item in validated_application["batch_records"]
    }
    for key in expected:
        digest_asset = digest_by_key[key]
        receipt = receipt_by_key[key]
        closure_record = closure_by_key[key]
        result_record = result_by_key[key]
        identity = {
            "source_id": key[0],
            "asset_id": key[1],
            "candidate_digest": digest_asset.get("sha256"),
            "receipt_digest": _receipt_digest(receipt),
            "revision": receipt.get("revision"),
        }
        if application_by_key[key] != identity:
            _fail("RFC_IANA_APPLICATION_IDENTITY_INVALID")
        if any(result_record[field] != identity[field] for field in _BATCH_FIELDS):
            _fail("RFC_IANA_RESULT_IDENTITY_INVALID")
        if any(closure_record[field] != identity[field] for field in _BATCH_FIELDS):
            _fail("RFC_IANA_CLOSURE_IDENTITY_INVALID")
        if result_record["evidence"] != closure_record["evidence"]:
            _fail("RFC_IANA_CLOSURE_CHANGED")

    finding_by_id = {item["finding_id"]: item for item in observation["source_observations"]}
    xml_conflict = finding_by_id.get("iana-xml-date-conflict")
    if (
        not isinstance(xml_conflict, Mapping)
        or xml_conflict.get("status") != XML_CONFLICT_STATUS
        or xml_conflict.get("closure_effect") != CLOSURE_EFFECT
        or xml_conflict.get("applicable_assets") != ["service-names-port-numbers-xml"]
    ):
        _fail("RFC_IANA_XML_CONFLICT_CHANGED")
    exact_findings = [
        item for item in observation["source_observations"] if item["source_id"] in EXACT_ASSETS
    ]
    if not exact_findings or any(item["closure_effect"] != CLOSURE_EFFECT for item in exact_findings):
        _fail("RFC_IANA_OBSERVATION_CLOSURE_CHANGED")

    successor_signed_at = _validate_successor_wrapper(
        successor_wrapper, result=validated_result, authority_id=validated_authority.authority_id
    )
    validate_execution_authority(
        authority,
        operation="human_review",
        expected_scope_digest=PARENT_SCOPE_DIGEST,
        allowed_source_ids=EXACT_ASSETS,
        now=successor_signed_at,
    )
    successor_reviews = successor_wrapper["records"]
    validated_prior = validate_review_history(official_reviews)
    validated_successor = validate_review_history(successor_reviews)
    successor_keys = [(item.source_id, item.asset_id) for item in validated_successor]
    if len(validated_successor) != 6 or len(set(successor_keys)) != 6 or set(successor_keys) != expected:
        _fail("RFC_IANA_SUCCESSOR_SCOPE_INVALID")
    prior_by_key = {(item.source_id, item.asset_id): item for item in validated_prior}
    successor_by_key = {(item.source_id, item.asset_id): item for item in validated_successor}
    for key, expected_head in CURRENT_OFFICIAL_HEAD_IDS.items():
        prior = prior_by_key.get(key)
        successor = successor_by_key[key]
        identity = application_by_key[key]
        if _timestamp(successor.signed_at, "RFC_IANA_SUCCESSOR_TIMESTAMP_INVALID") != successor_signed_at:
            _fail("RFC_IANA_SUCCESSOR_TIMESTAMP_INVALID")
        if prior is None or prior.review_id != expected_head or successor.supersedes != expected_head:
            _fail("RFC_IANA_SUCCESSOR_HEAD_INVALID")
        if (
            successor.decision != "DEFER"
            or successor.document_id is not None
            or successor.chunk_ids
        ):
            _fail("RFC_IANA_SUCCESSOR_NOT_DEFERRED")
        if (
            successor.scope_digest != PARENT_SCOPE_DIGEST
            or successor.candidate_digest != identity["candidate_digest"]
            or successor.receipt_digest != identity["receipt_digest"]
            or validated_result["result_id"] not in successor.evidence_refs
        ):
            _fail("RFC_IANA_SUCCESSOR_IDENTITY_INVALID")
    validate_review_history(list(official_reviews) + list(successor_reviews))

    txt = successor_by_key[("iana-registries", "service-names-port-numbers-txt")]
    if txt.comment != TXT_COMMENT:
        _fail("RFC_IANA_TXT_PARSER_FAIL_OPEN")
    status = gate0_status(
        required_assets=tuple(sorted(expected)),
        reviews=successor_reviews,
        acquisition_receipts=list(receipt_by_key.values()),
        authority_present=True,
        scope_digest=PARENT_SCOPE_DIGEST,
    )
    if status["status"] != "BLOCKED" or status["reviewed_asset_count"] != 0:
        _fail("RFC_IANA_GATE0_STATE_CHANGED")
    return copy.deepcopy(dict(validated_result))


def validate_rfc_iana_evidence_review_bundle(
    application: Mapping[str, Any],
    *,
    authority: Mapping[str, Any],
    result: Mapping[str, Any],
    digest_assets: Sequence[Mapping[str, Any]],
    digest_robots: Sequence[Mapping[str, Any]],
    receipts: Sequence[Mapping[str, Any]],
    closure_matrix: Mapping[str, Any],
    acquisition_review_wrapper: Mapping[str, Any],
    closure_review_wrapper: Mapping[str, Any],
    official_observation: Mapping[str, Any],
    official_authority: Mapping[str, Any],
    official_review_wrapper: Mapping[str, Any],
    successor_wrapper: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize dependency failures to the exact-six validation boundary."""
    try:
        return _validate_rfc_iana_evidence_review_bundle(
            application,
            authority=authority,
            result=result,
            digest_assets=digest_assets,
            digest_robots=digest_robots,
            receipts=receipts,
            closure_matrix=closure_matrix,
            acquisition_review_wrapper=acquisition_review_wrapper,
            closure_review_wrapper=closure_review_wrapper,
            official_observation=official_observation,
            official_authority=official_authority,
            official_review_wrapper=official_review_wrapper,
            successor_wrapper=successor_wrapper,
        )
    except RfcIanaEvidenceReviewError:
        raise
    except (
        AcquisitionError,
        EvidenceClosureError,
        ExecutionAuthorityError,
        OfficialObservationError,
        ReviewError,
    ) as exc:
        raise RfcIanaEvidenceReviewError("RFC_IANA_DEPENDENCY_INVALID") from exc
