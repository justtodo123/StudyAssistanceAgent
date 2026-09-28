"""Strict offline contract for the M11 MIT OCW exact-20 evidence review."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, NoReturn

from app.m11_acquisition import AcquisitionError, validate_receipt
from app.m11_evidence_closure import EvidenceClosureError, validate_closure_bundle
from app.m11_execution_authority import ExecutionAuthorityError, validate_execution_authority
from app.m11_gate0 import EVIDENCE_CATEGORIES
from app.m11_official_observation import OfficialObservationError, validate_official_observation_bundle
from app.m11_review import (
    ReviewError,
    gate0_status,
    project_current_review_heads,
    review_digest,
    validate_review_history,
)

APPLICATION_SCHEMA = "sa.m11.p0.mit-ocw-evidence-review-application.v1"
RESULT_SCHEMA = "sa.m11.p0.mit-ocw-evidence-review-result.v1"
APPLICATION_ID = "m11-p0-mit-ocw-evidence-review-application-v1"
AUTHORITY_ID = "m11-mit-ocw-evidence-review-20-20260927"
RESULT_ID = "m11-p0-mit-ocw-evidence-review-result-v1"
SUCCESSOR_SLICE_ID = "mit-ocw-evidence-review-defer-20-20260927"
CLOSURE_MATRIX_ID = "m11-p0-evidence-closure-26-20260926"
OFFICIAL_OBSERVATION_ID = "m11-p0-official-source-observations-26-v1"
PRIOR_REVIEW_SLICE_ID = "official-observation-defer-26-20260926"
PARENT_SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
SOURCE_ID = "mit-ocw-6-004-2017"
EXACT_ASSETS = {
    SOURCE_ID: (
        "beta_answers", "caches_answers", "cmos_answers", "combinational_answers",
        "compilation_answers", "digital_answers", "fsm_answers", "information_answers",
        "interrupts_answers", "isa_answers", "beta_worksheet", "caches_worksheet",
        "cmos_worksheet", "combinational_worksheet", "compilation_worksheet",
        "digital_worksheet", "fsm_worksheet", "information_worksheet",
        "interrupts_worksheet", "isa_worksheet",
    )
}
CURRENT_OFFICIAL_HEAD_IDS = {
    (SOURCE_ID, asset_id): f"m11-hr-20260926-official-observation-{asset_id}"
    for asset_id in EXACT_ASSETS[SOURCE_ID]
}
HISTORICAL_ASSET_KEYS = frozenset(
    {
        ("rfc-editor-index", "rfc9110"),
        ("rfc-editor-index", "rfc9293"),
        ("rfc-editor-index", "rfc1034"),
        ("iana-registries", "service-names-port-numbers-csv"),
        ("iana-registries", "service-names-port-numbers-xml"),
        ("iana-registries", "service-names-port-numbers-txt"),
        *((SOURCE_ID, asset_id) for asset_id in EXACT_ASSETS[SOURCE_ID]),
    }
)
HISTORICAL_EVIDENCE_FIELDS = frozenset({"status", "refs", "comment"})
EXPECTED_SUCCESSOR_EVIDENCE_REFS = frozenset(
    {
        "m11-p0-digest-evidence-v1",
        "m11-p0-acquisition-26-receipts-v1",
        "m11-p0-evidence-closure-26-v1",
        OFFICIAL_OBSERVATION_ID,
        APPLICATION_ID,
        AUTHORITY_ID,
        RESULT_ID,
    }
)
RESULT = "REVIEW_REQUIRED"
CLOSURE_EFFECT = "NONE"
BATCH_DIGEST_DOMAIN = "sa.m11.p0.mit-ocw-evidence-review.batch.v1"
AUTHORITY_RECORD = "data/manifests/m11-p0-mit-ocw-evidence-review-authority-v1.json"
OBSERVATION_IDS = (
    "mit-robots-digest-match",
    "mit-source-policy",
    "mit-third-party-limitation",
)
NORMALIZATION = {
    "digital_answers": ("NORMALIZATION_REJECTED", "SOURCE_PARSE_FAILED"),
    "information_worksheet": ("NORMALIZATION_REJECTED", "INVALID_CANDIDATE_INPUT"),
}

_HEX = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*")
_DRIVE_PATH = re.compile(r"(?i)(?<![A-Za-z0-9])[a-z]:[\\/]")
_UNC_PATH = re.compile(r"(?<![\\/])(?:\\\\|//)[^\\/\s]+[\\/][^\\/\s]+")
_POSIX_HOST_PATH = re.compile(r"(?<![A-Za-z0-9.])/(?:home|users|private|root|tmp|var/tmp)/", re.IGNORECASE)
_FORBIDDEN_KEYS = frozenset({
    "body", "bodies", "content", "contents", "raw", "raw_text", "raw_path",
    "host_path", "local_path", "absolute_path", "credentials", "token",
})
_BATCH_FIELDS = frozenset({"source_id", "asset_id", "candidate_digest", "receipt_digest", "revision"})
_APPLICATION_FIELDS = frozenset({
    "schema", "application_id", "authority_id", "parent_scope_digest", "batch_digest",
    "source_ids", "asset_ids", "asset_count", "submitted_by", "submitted_at", "operation",
    "metadata_only", "network_used", "source_expansion", "lifecycle_mutation",
    "host_paths_included", "bodies_included", "batch_records",
})
_RESULT_FIELDS = frozenset({
    "schema", "result_id", "application_id", "authority_id", "parent_scope_digest", "batch_digest",
    "prior_closure_matrix_id", "official_observation_id", "prior_review_slice_id", "successor_slice_id",
    "source_ids", "asset_count", "result", "closure_effect", "formal_gate0_executed", "formal_3k_executed",
    "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion",
    "lifecycle_mutation", "host_paths_included", "bodies_included", "records",
})
_RESULT_RECORD_FIELDS = _BATCH_FIELDS | {
    "prior_disposition", "normalization_status", "normalization_reason", "observation_refs",
    "observation_limitations", "third_party_rights", "determination", "evidence",
}
_REVIEW_WRAPPER_FIELDS = frozenset({
    "schema", "slice_id", "authority_id", "authority_record", "scope_digest", "source_ids", "asset_count",
    "remaining_in_batch", "decision", "reviewer_id", "signed_at", "formal_gate0_executed",
    "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion",
    "lifecycle_mutation", "host_paths_included", "bodies_included", "records",
})
_ESCALATION_FLAGS = ("network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")


class MitOcwEvidenceReviewError(ValueError):
    """Stable validation failure for the MIT exact-20 evidence-review contract."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> NoReturn:
    raise MitOcwEvidenceReviewError(code)


def _privacy(value: Any) -> bool:
    if isinstance(value, Mapping):
        if set(value) & _FORBIDDEN_KEYS:
            return True
        return any(_privacy(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_privacy(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return bool(_DRIVE_PATH.search(value) or _UNC_PATH.search(value) or _POSIX_HOST_PATH.search(value) or "111_others" in lowered)
    return False


def _timestamp(value: Any, code: str) -> datetime:
    if not isinstance(value, str) or not value or value != value.strip():
        _fail(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MitOcwEvidenceReviewError(code) from exc
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
    return {(source, asset) for source, assets in EXACT_ASSETS.items() for asset in assets}


def _canonical_batch_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        _fail("MIT_OCW_BATCH_RECORDS_INVALID")
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, Mapping) or set(record) != _BATCH_FIELDS:
            _fail("MIT_OCW_BATCH_RECORD_FIELDS_INVALID")
        source_id, asset_id = record["source_id"], record["asset_id"]
        _id(source_id, "MIT_OCW_BATCH_SOURCE_INVALID")
        _id(asset_id, "MIT_OCW_BATCH_ASSET_INVALID")
        key = (source_id, asset_id)
        if key in seen:
            _fail("MIT_OCW_BATCH_DUPLICATE_ASSET")
        seen.add(key)
        for field in ("candidate_digest", "receipt_digest", "revision"):
            _digest(record[field], "MIT_OCW_BATCH_IDENTITY_INVALID")
        normalized.append({field: str(record[field]) for field in _BATCH_FIELDS})
    if seen != _expected_pairs():
        _fail("MIT_OCW_BATCH_SCOPE_INVALID")
    return sorted(normalized, key=lambda item: (item["source_id"], item["asset_id"]))


def exact_twenty_batch_digest(records: Sequence[Mapping[str, Any]]) -> str:
    payload = {"domain": BATCH_DIGEST_DOMAIN, "parent_scope_digest": PARENT_SCOPE_DIGEST, "records": _canonical_batch_records(records)}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_mit_ocw_evidence_review_application(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != _APPLICATION_FIELDS:
        _fail("MIT_OCW_APPLICATION_FIELDS_INVALID")
    if _privacy(payload):
        _fail("MIT_OCW_APPLICATION_PRIVACY_FIELD")
    if payload["schema"] != APPLICATION_SCHEMA:
        _fail("MIT_OCW_APPLICATION_SCHEMA_INVALID")
    if (
        payload["application_id"] != APPLICATION_ID
        or payload["authority_id"] != AUTHORITY_ID
    ):
        _fail("MIT_OCW_APPLICATION_IDENTITY_INVALID")
    for field in ("application_id", "authority_id", "submitted_by"):
        _id(payload[field], "MIT_OCW_APPLICATION_ID_INVALID")
    _timestamp(payload["submitted_at"], "MIT_OCW_APPLICATION_TIMESTAMP_INVALID")
    if payload["operation"] != "human_review" or payload["metadata_only"] is not True:
        _fail("MIT_OCW_APPLICATION_OPERATION_INVALID")
    if payload["parent_scope_digest"] != PARENT_SCOPE_DIGEST:
        _fail("MIT_OCW_PARENT_SCOPE_CHANGED")
    _digest(payload["batch_digest"], "MIT_OCW_BATCH_DIGEST_INVALID")
    if payload["source_ids"] != [SOURCE_ID] or payload["asset_ids"] != {SOURCE_ID: list(EXACT_ASSETS[SOURCE_ID])} or payload["asset_count"] != 20:
        _fail("MIT_OCW_APPLICATION_SCOPE_INVALID")
    if any(payload[field] is not False for field in _ESCALATION_FLAGS):
        _fail("MIT_OCW_APPLICATION_ESCALATION_FLAG")
    if exact_twenty_batch_digest(payload["batch_records"]) != payload["batch_digest"]:
        _fail("MIT_OCW_BATCH_DIGEST_MISMATCH")
    return copy.deepcopy(dict(payload))


def _validate_result_evidence(evidence: Any) -> None:
    if not isinstance(evidence, Mapping) or set(evidence) != set(EVIDENCE_CATEGORIES):
        _fail("MIT_OCW_RESULT_EVIDENCE_CATEGORIES_INVALID")
    for category in EVIDENCE_CATEGORIES:
        entry = evidence[category]
        if not isinstance(entry, Mapping) or set(entry) != {"status", "refs", "comment"}:
            _fail("MIT_OCW_RESULT_EVIDENCE_FIELDS_INVALID")
        if entry["status"] != "PENDING":
            _fail("MIT_OCW_RESULT_EVIDENCE_NOT_PENDING")
        if not isinstance(entry["refs"], list) or any(not isinstance(ref, str) or not _ID.fullmatch(ref) for ref in entry["refs"]):
            _fail("MIT_OCW_RESULT_EVIDENCE_REFS_INVALID")
        if not isinstance(entry["comment"], str) or not entry["comment"].strip() or len(entry["comment"]) > 500:
            _fail("MIT_OCW_RESULT_EVIDENCE_COMMENT_INVALID")


def validate_mit_ocw_evidence_review_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != _RESULT_FIELDS:
        _fail("MIT_OCW_RESULT_FIELDS_INVALID")
    if _privacy(payload):
        _fail("MIT_OCW_RESULT_PRIVACY_FIELD")
    if payload["schema"] != RESULT_SCHEMA:
        _fail("MIT_OCW_RESULT_SCHEMA_INVALID")
    expected_ids = {
        "result_id": RESULT_ID,
        "application_id": APPLICATION_ID,
        "authority_id": AUTHORITY_ID,
        "prior_closure_matrix_id": CLOSURE_MATRIX_ID,
        "official_observation_id": OFFICIAL_OBSERVATION_ID,
        "prior_review_slice_id": PRIOR_REVIEW_SLICE_ID,
        "successor_slice_id": SUCCESSOR_SLICE_ID,
    }
    if any(payload[field] != expected for field, expected in expected_ids.items()):
        _fail("MIT_OCW_RESULT_IDENTITY_INVALID")
    for field in expected_ids:
        _id(payload[field], "MIT_OCW_RESULT_ID_INVALID")
    if payload["parent_scope_digest"] != PARENT_SCOPE_DIGEST:
        _fail("MIT_OCW_PARENT_SCOPE_CHANGED")
    _digest(payload["batch_digest"], "MIT_OCW_BATCH_DIGEST_INVALID")
    if payload["source_ids"] != [SOURCE_ID] or payload["asset_count"] != 20:
        _fail("MIT_OCW_RESULT_SCOPE_INVALID")
    if payload["result"] != RESULT or payload["closure_effect"] != CLOSURE_EFFECT:
        _fail("MIT_OCW_RESULT_STATE_INVALID")
    flags = ("formal_gate0_executed", "formal_3k_executed", "candidate_approval_granted", "publication_authorized", *_ESCALATION_FLAGS)
    if any(payload[field] is not False for field in flags):
        _fail("MIT_OCW_RESULT_ESCALATION_FLAG")
    records = payload["records"]
    if not isinstance(records, list) or len(records) != 20:
        _fail("MIT_OCW_RESULT_RECORD_COUNT_INVALID")
    batch_records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, Mapping) or set(record) != _RESULT_RECORD_FIELDS:
            _fail("MIT_OCW_RESULT_RECORD_FIELDS_INVALID")
        key = (record["source_id"], record["asset_id"])
        if key in seen:
            _fail("MIT_OCW_RESULT_DUPLICATE_ASSET")
        seen.add(key)
        if key not in _expected_pairs() or record["source_id"] != SOURCE_ID:
            _fail("MIT_OCW_RESULT_SCOPE_INVALID")
        expected_disposition = "NORMALIZATION_REJECTED" if record["asset_id"] in NORMALIZATION else "ELIGIBLE_FOR_REVIEW"
        if record["prior_disposition"] != expected_disposition:
            _fail("MIT_OCW_RESULT_DISPOSITION_INVALID")
        expected_normalization = NORMALIZATION.get(record["asset_id"], ("CANDIDATE", "NONE"))
        if (record["normalization_status"], record["normalization_reason"]) != expected_normalization:
            _fail("MIT_OCW_RESULT_NORMALIZATION_INVALID")
        if record["observation_refs"] != list(OBSERVATION_IDS) or record["third_party_rights"] != "UNRESOLVED":
            _fail("MIT_OCW_RESULT_OBSERVATION_LINK_INVALID")
        if not isinstance(record["observation_limitations"], list) or len(record["observation_limitations"]) != 3 or any(not isinstance(item, str) or not item.strip() for item in record["observation_limitations"]):
            _fail("MIT_OCW_RESULT_OBSERVATION_LIMITATION_INVALID")
        if record["determination"] != "DEFER":
            _fail("MIT_OCW_RESULT_DETERMINATION_INVALID")
        _validate_result_evidence(record["evidence"])
        batch_records.append({field: record[field] for field in _BATCH_FIELDS})
    if seen != _expected_pairs() or exact_twenty_batch_digest(batch_records) != payload["batch_digest"]:
        _fail("MIT_OCW_BATCH_DIGEST_MISMATCH")
    return copy.deepcopy(dict(payload))


def _receipt_digest(receipt: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(receipt), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_successor_wrapper(wrapper: Mapping[str, Any], *, result: Mapping[str, Any], authority_id: str) -> datetime:
    if not isinstance(wrapper, Mapping) or set(wrapper) != _REVIEW_WRAPPER_FIELDS:
        _fail("MIT_OCW_SUCCESSOR_WRAPPER_INVALID")
    if _privacy(wrapper):
        _fail("MIT_OCW_SUCCESSOR_PRIVACY_FIELD")
    if (wrapper["schema"], wrapper["slice_id"], wrapper["authority_id"], wrapper["authority_record"], wrapper["scope_digest"], wrapper["source_ids"], wrapper["asset_count"], wrapper["remaining_in_batch"], wrapper["decision"]) != (
        "sa.m11.p0.human-review-slice.v1", result["successor_slice_id"], authority_id, AUTHORITY_RECORD, PARENT_SCOPE_DIGEST, [SOURCE_ID], 20, 0, "DEFER"
    ):
        _fail("MIT_OCW_SUCCESSOR_WRAPPER_INVALID")
    for flag in ("formal_gate0_executed", "candidate_approval_granted", "publication_authorized", *_ESCALATION_FLAGS):
        if wrapper[flag] is not False:
            _fail("MIT_OCW_SUCCESSOR_ESCALATION_FLAG")
    return _timestamp(wrapper["signed_at"], "MIT_OCW_SUCCESSOR_TIMESTAMP_INVALID")


def _validate_bundle(
    application: Mapping[str, Any], *, authority: Mapping[str, Any], result: Mapping[str, Any], digest_assets: Sequence[Mapping[str, Any]], digest_robots: Sequence[Mapping[str, Any]], receipts: Sequence[Mapping[str, Any]], closure_matrix: Mapping[str, Any], acquisition_review_wrapper: Mapping[str, Any], closure_review_wrapper: Mapping[str, Any], official_observation: Mapping[str, Any], official_authority: Mapping[str, Any], official_review_wrapper: Mapping[str, Any], successor_wrapper: Mapping[str, Any],
) -> dict[str, Any]:
    app = validate_mit_ocw_evidence_review_application(application)
    res = validate_mit_ocw_evidence_review_result(result)
    if (res["application_id"], res["authority_id"], res["batch_digest"]) != (app["application_id"], app["authority_id"], app["batch_digest"]):
        _fail("MIT_OCW_APPLICATION_RESULT_LINK_INVALID")
    try:
        auth = validate_execution_authority(authority, operation="human_review", expected_scope_digest=PARENT_SCOPE_DIGEST, allowed_source_ids=EXACT_ASSETS, now=_timestamp(app["submitted_at"], "MIT_OCW_APPLICATION_TIMESTAMP_INVALID"))
    except ExecutionAuthorityError as exc:
        if exc.code in {"AUTHORITY_SOURCE_SCOPE_INVALID", "AUTHORITY_ASSET_SCOPE_INVALID"}:
            _fail("MIT_OCW_AUTHORITY_NOT_EXACT_TWENTY")
        raise
    if auth.authority_id != app["authority_id"]:
        _fail("MIT_OCW_AUTHORITY_LINK_INVALID")
    auth_assets = {source: tuple(sorted(auth.assets_for(source))) for source in auth.source_ids}
    if set(auth.source_ids) != {SOURCE_ID} or auth_assets != {SOURCE_ID: tuple(sorted(EXACT_ASSETS[SOURCE_ID]))}:
        _fail("MIT_OCW_AUTHORITY_NOT_EXACT_TWENTY")

    all_expected = [(SOURCE_ID, asset) for asset in EXACT_ASSETS[SOURCE_ID]]
    if not isinstance(digest_assets, Sequence) or isinstance(digest_assets, (str, bytes)):
        _fail("MIT_OCW_PREDECESSOR_SCOPE_INVALID")
    historical_keys = {
        (item.get("source_id"), item.get("asset_id"))
        for item in digest_assets
        if isinstance(item, Mapping)
    }
    if len(digest_assets) != 26 or historical_keys != HISTORICAL_ASSET_KEYS:
        _fail("MIT_OCW_PREDECESSOR_SCOPE_INVALID")
    if (
        not isinstance(acquisition_review_wrapper, Mapping)
        or not isinstance(closure_review_wrapper, Mapping)
        or not isinstance(official_review_wrapper, Mapping)
    ):
        _fail("MIT_OCW_PREDECESSOR_WRAPPER_INVALID")
    closure_reviews = closure_review_wrapper.get("records", ())
    prior_reviews = acquisition_review_wrapper.get("records", ())
    closure = validate_closure_bundle(closure_matrix, digest_assets=digest_assets, receipts=receipts, reviews=closure_reviews, prior_reviews=prior_reviews, expected_assets=[(x["source_id"], x["asset_id"]) for x in digest_assets])
    official_reviews = official_review_wrapper.get("records", ()) if isinstance(official_review_wrapper, Mapping) else ()
    observation = validate_official_observation_bundle(official_observation, digest_assets=digest_assets, receipts=receipts, closure_matrix=closure_matrix, closure_reviews=closure_reviews, successor_reviews=official_reviews, expected_assets=[(x["source_id"], x["asset_id"]) for x in digest_assets], authority=official_authority, successor_wrapper=official_review_wrapper, prior_review_wrapper=closure_review_wrapper, robots=digest_robots)
    if (
        closure["scope_digest"] != PARENT_SCOPE_DIGEST
        or closure["matrix_id"] != CLOSURE_MATRIX_ID
        or observation["observation_id"] != OFFICIAL_OBSERVATION_ID
        or official_review_wrapper.get("slice_id") != PRIOR_REVIEW_SLICE_ID
        or (res["prior_closure_matrix_id"], res["official_observation_id"], res["prior_review_slice_id"])
        != (CLOSURE_MATRIX_ID, OFFICIAL_OBSERVATION_ID, PRIOR_REVIEW_SLICE_ID)
    ):
        _fail("MIT_OCW_PREDECESSOR_LINK_INVALID")

    expected = set(all_expected)
    digest_by_key = {(x.get("source_id"), x.get("asset_id")): x for x in digest_assets if isinstance(x, Mapping)}
    receipt_by_key = {(x.get("source_id"), x.get("asset_id")): x for x in receipts if isinstance(x, Mapping)}
    if not expected.issubset(digest_by_key) or not expected.issubset(receipt_by_key):
        _fail("MIT_OCW_DEPENDENCY_SCOPE_INVALID")
    closure_by_key = {(x["source_id"], x["asset_id"]): x for x in closure["records"] if (x["source_id"], x["asset_id"]) in expected}
    result_by_key = {(x["source_id"], x["asset_id"]): x for x in res["records"]}
    app_by_key = {(x["source_id"], x["asset_id"]): x for x in app["batch_records"]}
    if set(result_by_key) != expected or set(app_by_key) != expected or set(closure_by_key) != expected:
        _fail("MIT_OCW_RESULT_SCOPE_INVALID")
    for key in expected:
        receipt = receipt_by_key[key]
        validated_receipt = validate_receipt(receipt)
        if validated_receipt.status != "ACQUIRED" or validated_receipt.scope_digest != PARENT_SCOPE_DIGEST:
            _fail("MIT_OCW_RECEIPT_INVALID")
        identity = {"source_id": key[0], "asset_id": key[1], "candidate_digest": digest_by_key[key].get("sha256"), "receipt_digest": _receipt_digest(receipt), "revision": receipt.get("revision")}
        if app_by_key[key] != identity or any(result_by_key[key][f] != identity[f] for f in _BATCH_FIELDS) or any(closure_by_key[key][f] != identity[f] for f in _BATCH_FIELDS):
            _fail("MIT_OCW_IDENTITY_INVALID")
        for category in EVIDENCE_CATEGORIES:
            predecessor = closure_by_key[key]["evidence"][category]
            if not isinstance(predecessor, Mapping) or set(predecessor) != HISTORICAL_EVIDENCE_FIELDS:
                _fail("MIT_OCW_CLOSURE_EVIDENCE_INVALID")
            if result_by_key[key]["evidence"][category]["status"] != predecessor["status"]:
                _fail("MIT_OCW_CLOSURE_STATUS_CHANGED")
            if set(result_by_key[key]["evidence"][category]["refs"]) != {
                *predecessor["refs"],
                OFFICIAL_OBSERVATION_ID,
            }:
                _fail("MIT_OCW_CLOSURE_REFERENCE_CHANGED")
        if closure_by_key[key]["disposition"] != result_by_key[key]["prior_disposition"]:
            _fail("MIT_OCW_DISPOSITION_CHANGED")

    findings = {x["finding_id"]: x for x in observation["source_observations"]}
    expected_limitations: dict[str, Any] = {}
    for finding_id in OBSERVATION_IDS:
        finding = findings.get(finding_id)
        if not isinstance(finding, Mapping):
            _fail("MIT_OCW_OBSERVATION_CLOSURE_CHANGED")
        if finding.get("closure_effect") != "NONE" or finding.get("requires_follow_up") is not True:
            _fail("MIT_OCW_OBSERVATION_CLOSURE_CHANGED")
        expected_limitations[finding_id] = finding.get("limitation")
    for key in expected:
        record = result_by_key[key]
        limitation_by_ref = dict(
            zip(record["observation_refs"], record["observation_limitations"], strict=True)
        )
        if any(
            limitation_by_ref.get(finding_id) != limitation
            for finding_id, limitation in expected_limitations.items()
        ):
            _fail("MIT_OCW_RESULT_OBSERVATION_LIMITATION_INVALID")
    if any(result_by_key[key]["third_party_rights"] != "UNRESOLVED" for key in expected):
        _fail("MIT_OCW_THIRD_PARTY_RIGHTS_RESOLVED")

    successor_signed_at = _validate_successor_wrapper(successor_wrapper, result=res, authority_id=auth.authority_id)
    validate_execution_authority(authority, operation="human_review", expected_scope_digest=PARENT_SCOPE_DIGEST, allowed_source_ids=EXACT_ASSETS, now=successor_signed_at)
    validated_prior = validate_review_history(official_reviews)
    validated_successor = validate_review_history(successor_wrapper["records"])
    if len(validated_successor) != 20 or {(x.source_id, x.asset_id) for x in validated_successor} != expected:
        _fail("MIT_OCW_SUCCESSOR_SCOPE_INVALID")
    prior_by_key = {(x.source_id, x.asset_id): x for x in validated_prior}
    succ_by_key = {(x.source_id, x.asset_id): x for x in validated_successor}
    submitted_at = _timestamp(app["submitted_at"], "MIT_OCW_APPLICATION_TIMESTAMP_INVALID")
    for key in expected:
        successor = succ_by_key[key]
        prior = prior_by_key.get(key)
        successor_timestamp = _timestamp(
            successor.signed_at,
            "MIT_OCW_SUCCESSOR_TIMESTAMP_INVALID",
        )
        if (
            prior is None
            or prior.review_id != CURRENT_OFFICIAL_HEAD_IDS[key]
            or successor.supersedes != CURRENT_OFFICIAL_HEAD_IDS[key]
        ):
            _fail("MIT_OCW_SUCCESSOR_HEAD_INVALID")
        if successor_timestamp != successor_signed_at:
            _fail("MIT_OCW_SUCCESSOR_TIMESTAMP_INVALID")
        identity = app_by_key[key]
        if successor.decision != "DEFER" or successor.document_id is not None or successor.chunk_ids or successor.scope_digest != PARENT_SCOPE_DIGEST or successor.candidate_digest != identity["candidate_digest"] or successor.receipt_digest != identity["receipt_digest"] or set(successor.evidence_refs) != EXPECTED_SUCCESSOR_EVIDENCE_REFS:
            _fail("MIT_OCW_SUCCESSOR_IDENTITY_INVALID")
        if successor_timestamp < submitted_at:
            _fail("MIT_OCW_SUCCESSOR_TIMESTAMP_ORDER_INVALID")
        successor_payload = successor.as_dict()
        successor_payload.pop("attestation_digest")
        if successor.attestation_digest != review_digest(successor_payload):
            _fail("MIT_OCW_SUCCESSOR_ATTESTATION_INVALID")
    current = project_current_review_heads(
        [*official_reviews, *successor_wrapper["records"]]
    )
    if len(current) != 26:
        _fail("MIT_OCW_CURRENT_HEADS_NOT_UNIQUE")
    status = gate0_status(required_assets=tuple(sorted(expected)), reviews=list(successor_wrapper["records"]), acquisition_receipts=[receipt_by_key[key] for key in expected], authority_present=True, scope_digest=PARENT_SCOPE_DIGEST)
    if status["status"] != "BLOCKED" or status["reviewed_asset_count"] != 0:
        _fail("MIT_OCW_GATE0_STATE_CHANGED")
    return copy.deepcopy(dict(res))


def validate_mit_ocw_evidence_review_bundle(application: Mapping[str, Any], *, authority: Mapping[str, Any], result: Mapping[str, Any], digest_assets: Sequence[Mapping[str, Any]], digest_robots: Sequence[Mapping[str, Any]], receipts: Sequence[Mapping[str, Any]], closure_matrix: Mapping[str, Any], acquisition_review_wrapper: Mapping[str, Any], closure_review_wrapper: Mapping[str, Any], official_observation: Mapping[str, Any], official_authority: Mapping[str, Any], official_review_wrapper: Mapping[str, Any], successor_wrapper: Mapping[str, Any], rfc_iana_successor_wrapper: Mapping[str, Any] | None = None) -> dict[str, Any]:
    try:
        validated = _validate_bundle(application, authority=authority, result=result, digest_assets=digest_assets, digest_robots=digest_robots, receipts=receipts, closure_matrix=closure_matrix, acquisition_review_wrapper=acquisition_review_wrapper, closure_review_wrapper=closure_review_wrapper, official_observation=official_observation, official_authority=official_authority, official_review_wrapper=official_review_wrapper, successor_wrapper=successor_wrapper)
        if rfc_iana_successor_wrapper is not None:
            rfc_records_value = rfc_iana_successor_wrapper.get("records")
            if not isinstance(rfc_records_value, list):
                _fail("MIT_OCW_COMBINED_HISTORY_INVALID")
            rfc_records: list[Mapping[str, Any]] = rfc_records_value
            combined = [
                *official_review_wrapper.get("records", ()),
                *rfc_records,
                *successor_wrapper.get("records", ()),
            ]
            current = project_current_review_heads(combined)
            expected = HISTORICAL_ASSET_KEYS
            if (
                len(combined) != 52
                or len(current) != 26
                or {(item.source_id, item.asset_id) for item in current} != expected
                or any(item.decision != "DEFER" for item in current)
                or any(item.document_id is not None or item.chunk_ids for item in current)
            ):
                _fail("MIT_OCW_COMBINED_HISTORY_INVALID")
        return validated
    except MitOcwEvidenceReviewError:
        raise
    except (AcquisitionError, EvidenceClosureError, ExecutionAuthorityError, OfficialObservationError, ReviewError) as exc:
        raise MitOcwEvidenceReviewError("MIT_OCW_DEPENDENCY_INVALID") from exc
