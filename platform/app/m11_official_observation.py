"""Strict, metadata-only official-source observations for M11 P0."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .m11_acquisition import validate_receipt, validate_receipt_batch
from .m11_evidence_closure import validate_evidence_closure
from .m11_execution_authority import validate_execution_authority
from .m11_review import gate0_status, validate_review_history

OFFICIAL_OBSERVATION_SCHEMA = "sa.m11.p0.official-source-observation.v1"
RESULT = "REVIEW_REQUIRED"
CLOSURE_STATE = "PENDING_UNCHANGED"
REVIEW_OUTCOME = "DEFER"
_OBSERVATION_STATES = frozenset({"OBSERVED", "UNRESOLVED"})
_ALLOWED_KINDS = frozenset({
    "ROBOTS_DIGEST_MATCH", "SOURCE_POLICY_METADATA", "SOURCE_POLICY_LIMITATION",
    "RFC_METADATA_DATE", "SCHEMA_METADATA_SIGNAL", "SCHEMA_METADATA_CONFLICT",
})
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*\Z")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_FORBIDDEN = frozenset({
    "body", "content", "text", "raw_content", "raw_path", "host_path", "path",
    "credentials", "password", "token", "learning_state", "private_learning_state",
    "signature",
})
_TOP_FIELDS = frozenset({
    "schema", "observation_id", "scope_digest", "authority_id", "authority_record",
    "digest_record", "receipt_record", "prior_closure_matrix_id", "prior_closure_record",
    "prior_review_slice_id", "prior_review_record", "successor_slice_id", "asset_count", "source_ids", "result",
    "formal_gate0_executed", "formal_3k_executed", "candidate_approval_granted",
    "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation",
    "host_paths_included", "bodies_included", "source_observations", "asset_links",
})
_FINDING_FIELDS = frozenset({
    "finding_id", "source_id", "kind", "status", "applicable_assets", "official_reference_id",
    "facts", "limitation", "requires_follow_up", "closure_effect",
})
_FACT_FIELDS = frozenset({"key", "value"})
_LINK_FIELDS = frozenset({
    "source_id", "asset_id", "candidate_digest", "receipt_digest", "revision",
    "disposition", "observation_refs", "closure_state", "review_outcome",
})


class OfficialObservationError(ValueError):
    """An official-source observation or its linked bundle is invalid."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise OfficialObservationError(code)


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


def observation_digest(payload: Mapping[str, Any]) -> str:
    try:
        text = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise OfficialObservationError("OBSERVATION_DIGEST_INVALID") from exc
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_facts(value: Any) -> None:
    if not isinstance(value, list) or not value:
        _fail("OBSERVATION_FACTS_INVALID")
    for fact in value:
        if not isinstance(fact, Mapping) or set(fact) != _FACT_FIELDS:
            _fail("OBSERVATION_FACT_FIELDS_INVALID")
        _id(fact["key"], "OBSERVATION_FACT_KEY_INVALID")
        fact_value = fact["value"]
        if isinstance(fact_value, bool):
            continue
        if isinstance(fact_value, int):
            if fact_value < 0:
                _fail("OBSERVATION_FACT_VALUE_INVALID")
            continue
        if isinstance(fact_value, str) and fact_value and len(fact_value) <= 160:
            continue
        _fail("OBSERVATION_FACT_VALUE_INVALID")


def _validate_finding(value: Any) -> None:
    if not isinstance(value, Mapping) or set(value) != _FINDING_FIELDS:
        _fail("OBSERVATION_FINDING_FIELDS_INVALID")
    _id(value["finding_id"], "OBSERVATION_FINDING_ID_INVALID")
    _id(value["source_id"], "OBSERVATION_FINDING_SOURCE_INVALID")
    if value["kind"] not in _ALLOWED_KINDS:
        _fail("OBSERVATION_FINDING_KIND_INVALID")
    if value["status"] not in _OBSERVATION_STATES:
        _fail("OBSERVATION_FINDING_STATUS_INVALID")
    assets = value["applicable_assets"]
    if not isinstance(assets, list) or not assets or any(
        not isinstance(item, str) or not _ID.fullmatch(item) for item in assets
    ) or len(set(assets)) != len(assets):
        _fail("OBSERVATION_FINDING_ASSETS_INVALID")
    _id(value["official_reference_id"], "OBSERVATION_REFERENCE_INVALID")
    _validate_facts(value["facts"])
    if not isinstance(value["limitation"], str) or not value["limitation"].strip() or len(value["limitation"]) > 500:
        _fail("OBSERVATION_LIMITATION_INVALID")
    if value["requires_follow_up"] is not True:
        _fail("OBSERVATION_FOLLOW_UP_INVALID")
    if value["closure_effect"] != "NONE":
        _fail("OBSERVATION_CLOSURE_EFFECT_INVALID")
    if value["status"] == "UNRESOLVED" and value["kind"] not in {
        "SOURCE_POLICY_LIMITATION", "SCHEMA_METADATA_CONFLICT",
    }:
        _fail("OBSERVATION_UNRESOLVED_KIND_INVALID")


def validate_official_source_observation(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a detached, non-closing observation manifest."""
    if not isinstance(payload, Mapping) or set(payload) != _TOP_FIELDS:
        _fail("OBSERVATION_FIELDS_INVALID")
    if _privacy(payload):
        _fail("OBSERVATION_PRIVACY_FIELD")
    if payload["schema"] != OFFICIAL_OBSERVATION_SCHEMA:
        _fail("OBSERVATION_SCHEMA_INVALID")
    for key in (
        "observation_id", "authority_id", "authority_record", "digest_record", "receipt_record",
        "prior_closure_matrix_id", "prior_closure_record", "prior_review_slice_id", "prior_review_record", "successor_slice_id",
    ):
        _id(payload[key], "OBSERVATION_ID_INVALID")
    _digest(payload["scope_digest"], "OBSERVATION_SCOPE_INVALID")
    if not isinstance(payload["asset_count"], int) or isinstance(payload["asset_count"], bool):
        _fail("OBSERVATION_ASSET_COUNT_INVALID")
    source_ids = payload["source_ids"]
    if not isinstance(source_ids, list) or not source_ids or len(set(source_ids)) != len(source_ids):
        _fail("OBSERVATION_SOURCE_IDS_INVALID")
    for source_id in source_ids:
        _id(source_id, "OBSERVATION_SOURCE_ID_INVALID")
    if payload["result"] != RESULT:
        _fail("OBSERVATION_RESULT_INVALID")
    for key in (
        "formal_gate0_executed", "formal_3k_executed", "candidate_approval_granted",
        "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation",
        "host_paths_included", "bodies_included",
    ):
        if payload[key] is not False:
            _fail("OBSERVATION_ESCALATION_FLAG")
    findings = payload["source_observations"]
    if not isinstance(findings, list) or not findings:
        _fail("OBSERVATION_FINDINGS_INVALID")
    finding_ids: set[str] = set()
    for finding in findings:
        _validate_finding(finding)
        if finding["finding_id"] in finding_ids:
            _fail("OBSERVATION_DUPLICATE_FINDING")
        finding_ids.add(finding["finding_id"])
        if finding["source_id"] not in source_ids:
            _fail("OBSERVATION_FINDING_SOURCE_INVALID")
    links = payload["asset_links"]
    if not isinstance(links, list) or len(links) != payload["asset_count"]:
        _fail("OBSERVATION_LINK_COUNT_INVALID")
    seen: set[tuple[str, str]] = set()
    for link in links:
        if not isinstance(link, Mapping) or set(link) != _LINK_FIELDS:
            _fail("OBSERVATION_LINK_FIELDS_INVALID")
        _id(link["source_id"], "OBSERVATION_LINK_SOURCE_INVALID")
        if link["source_id"] not in source_ids:
            _fail("OBSERVATION_LINK_SOURCE_INVALID")
        _id(link["asset_id"], "OBSERVATION_LINK_ASSET_INVALID")
        key = (link["source_id"], link["asset_id"])
        if key in seen:
            _fail("OBSERVATION_DUPLICATE_ASSET")
        seen.add(key)
        _digest(link["candidate_digest"], "OBSERVATION_CANDIDATE_DIGEST_INVALID")
        _digest(link["receipt_digest"], "OBSERVATION_RECEIPT_DIGEST_INVALID")
        _digest(link["revision"], "OBSERVATION_REVISION_INVALID")
        if link["disposition"] not in {"ELIGIBLE_FOR_REVIEW", "NORMALIZATION_REJECTED"}:
            _fail("OBSERVATION_DISPOSITION_INVALID")
        refs = link["observation_refs"]
        if not isinstance(refs, list) or not refs or len(set(refs)) != len(refs) or any(
            not isinstance(item, str) or item not in finding_ids for item in refs
        ):
            _fail("OBSERVATION_REFS_INVALID")
        if link["closure_state"] != CLOSURE_STATE:
            _fail("OBSERVATION_CLOSURE_STATE_INVALID")
        if link["review_outcome"] != REVIEW_OUTCOME:
            _fail("OBSERVATION_REVIEW_OUTCOME_INVALID")
    return copy.deepcopy(dict(payload))


def load_official_source_observation(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OfficialObservationError("OBSERVATION_LOAD_FAILED") from exc
    return validate_official_source_observation(payload)


def _receipt_digest(receipt: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(receipt), ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()


def _asset_stub(key: tuple[str, str], receipt: Mapping[str, Any]) -> Any:
    from .m11_acquisition import FrozenAsset
    return FrozenAsset(
        source_id=key[0], asset_id=key[1], canonical_url=receipt["canonical_url"],
        revision=receipt["revision"], sha256=receipt["sha256"],
        source_blob_sha1=receipt["source_blob_sha1"],
    )


def validate_official_observation_bundle(
    observation: Mapping[str, Any], *, digest_assets: Sequence[Mapping[str, Any]],
    receipts: Sequence[Mapping[str, Any]], closure_matrix: Mapping[str, Any],
    closure_reviews: Sequence[Mapping[str, Any]], successor_reviews: Sequence[Mapping[str, Any]],
    expected_assets: Sequence[tuple[str, str]], authority: Mapping[str, Any],
    successor_wrapper: Mapping[str, Any], prior_review_wrapper: Mapping[str, Any],
    robots: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate observations without changing the historical closure projection."""
    validated = validate_official_source_observation(observation)
    closure = validate_evidence_closure(closure_matrix)
    expected = set(expected_assets)
    if not isinstance(authority, Mapping):
        _fail("OBSERVATION_AUTHORITY_MISSING")
    validated_authority = validate_execution_authority(
        authority, operation="human_review", expected_scope_digest=validated["scope_digest"]
    )
    if validated_authority.authority_id != validated["authority_id"]:
        _fail("OBSERVATION_AUTHORITY_LINK_INVALID")
    if set(validated_authority.source_ids) != set(validated["source_ids"]):
        _fail("OBSERVATION_AUTHORITY_SCOPE_INVALID")
    authority_assets = {
        (source_id, asset_id)
        for source_id in validated_authority.source_ids
        for asset_id in validated_authority.assets_for(source_id)
    }
    if authority_assets != expected:
        _fail("OBSERVATION_AUTHORITY_ASSETS_INVALID")

    if not isinstance(prior_review_wrapper, Mapping) or prior_review_wrapper.get("schema") != "sa.m11.p0.human-review-slice.v1":
        _fail("OBSERVATION_PRIOR_WRAPPER_INVALID")
    if prior_review_wrapper.get("slice_id") != validated["prior_review_slice_id"]:
        _fail("OBSERVATION_PRIOR_WRAPPER_INVALID")
    if prior_review_wrapper.get("scope_digest") != validated["scope_digest"]:
        _fail("OBSERVATION_PRIOR_WRAPPER_INVALID")
    if not isinstance(successor_wrapper, Mapping) or successor_wrapper.get("schema") != "sa.m11.p0.human-review-slice.v1":
        _fail("OBSERVATION_SUCCESSOR_WRAPPER_INVALID")
    if successor_wrapper.get("slice_id") != validated["successor_slice_id"]:
        _fail("OBSERVATION_SUCCESSOR_WRAPPER_INVALID")
    if successor_wrapper.get("authority_id") != validated["authority_id"] or successor_wrapper.get("scope_digest") != validated["scope_digest"]:
        _fail("OBSERVATION_SUCCESSOR_WRAPPER_INVALID")
    if successor_wrapper.get("asset_count") != validated["asset_count"] or successor_wrapper.get("decision") != REVIEW_OUTCOME:
        _fail("OBSERVATION_SUCCESSOR_WRAPPER_INVALID")
    if successor_wrapper.get("source_ids") != validated["source_ids"] or successor_wrapper.get("remaining_in_batch") != 0:
        _fail("OBSERVATION_SUCCESSOR_WRAPPER_INVALID")
    for wrapper in (prior_review_wrapper, successor_wrapper):
        for flag in (
            "formal_gate0_executed", "candidate_approval_granted", "publication_authorized",
            "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included",
        ):
            if wrapper.get(flag) is not False:
                _fail("OBSERVATION_WRAPPER_ESCALATION_FLAG")

    actual = {(item["source_id"], item["asset_id"]) for item in validated["asset_links"]}
    if actual != expected or len(expected) != validated["asset_count"]:
        _fail("OBSERVATION_SCOPE_ASSETS_INVALID")
    if validated["scope_digest"] != closure["scope_digest"]:
        _fail("OBSERVATION_SCOPE_LINK_INVALID")
    if validated["prior_closure_matrix_id"] != closure["matrix_id"]:
        _fail("OBSERVATION_CLOSURE_LINK_INVALID")
    digest_by_key = {(item["source_id"], item["asset_id"]): item for item in digest_assets}
    receipt_by_key = {(item["source_id"], item["asset_id"]): item for item in receipts}
    if set(digest_by_key) != expected or set(receipt_by_key) != expected:
        _fail("OBSERVATION_DEPENDENCY_SCOPE_INVALID")
    validated_receipts = tuple(validate_receipt(item) for item in receipts)
    validate_receipt_batch(validated_receipts, {key: _asset_stub(key, item) for key, item in receipt_by_key.items()})
    validate_review_history(closure_reviews)
    successor = validate_review_history(successor_reviews)
    closure_by_key = {(item["source_id"], item["asset_id"]): item for item in closure_reviews}
    successor_by_key = {(item.source_id, item.asset_id): item for item in successor}
    if set(successor_by_key) != expected or set(closure_by_key) != expected:
        _fail("OBSERVATION_REVIEW_SCOPE_INVALID")
    expected_by_source: dict[str, set[str]] = {}
    for source_id, asset_id in expected:
        expected_by_source.setdefault(source_id, set()).add(asset_id)
    for finding in validated["source_observations"]:
        if not set(finding["applicable_assets"]) <= expected_by_source.get(finding["source_id"], set()):
            _fail("OBSERVATION_APPLICABILITY_INVALID")
    robots_by_host = {"mit-ocw-6-004-2017": "ocw.mit.edu", "rfc-editor-index": "www.rfc-editor.org", "iana-registries": "www.iana.org"}
    if not isinstance(robots, Sequence) or isinstance(robots, (str, bytes)):
        _fail("OBSERVATION_ROBOTS_LINK_INVALID")
    robot_by_host = {item.get("host"): item.get("sha256") for item in robots if isinstance(item, Mapping)}
    if set(robot_by_host) != set(robots_by_host.values()):
        _fail("OBSERVATION_ROBOTS_LINK_INVALID")
    for finding in validated["source_observations"]:
        if finding["kind"] == "ROBOTS_DIGEST_MATCH":
            host = robots_by_host.get(finding["source_id"])
            observed = next((fact["value"] for fact in finding["facts"] if fact["key"] == "sha256"), None)
            if host is None or not isinstance(observed, str) or not _HEX.fullmatch(observed) or observed != robot_by_host.get(host):
                _fail("OBSERVATION_ROBOTS_LINK_INVALID")
    finding_by_id = {item["finding_id"]: item for item in validated["source_observations"]}
    used_finding_ids = {ref for link in validated["asset_links"] for ref in link["observation_refs"]}
    if used_finding_ids != set(finding_by_id):
        _fail("OBSERVATION_FINDING_USAGE_INVALID")
    for link in validated["asset_links"]:
        key = (link["source_id"], link["asset_id"])
        digest = digest_by_key[key]
        receipt = receipt_by_key[key]
        if link["candidate_digest"] != digest["sha256"] or link["revision"] != receipt["revision"]:
            _fail("OBSERVATION_IDENTITY_LINK_INVALID")
        if link["receipt_digest"] != _receipt_digest(receipt):
            _fail("OBSERVATION_RECEIPT_LINK_INVALID")
        if link["disposition"] != next(row["disposition"] for row in closure["records"] if (row["source_id"], row["asset_id"]) == key):
            _fail("OBSERVATION_DISPOSITION_LINK_INVALID")
        for ref in link["observation_refs"]:
            finding = finding_by_id[ref]
            if finding["source_id"] != link["source_id"] or link["asset_id"] not in finding["applicable_assets"]:
                _fail("OBSERVATION_APPLICABILITY_INVALID")
        review = successor_by_key[key]
        prior = closure_by_key[key]
        if review.scope_digest != validated["scope_digest"] or review.decision != "DEFER" or review.document_id is not None or review.chunk_ids:
            _fail("OBSERVATION_SUCCESSOR_NOT_DEFERRED")
        if review.supersedes != prior["review_id"]:
            _fail("OBSERVATION_SUCCESSOR_SUPERSESSION_INVALID")
        if review.candidate_digest != link["candidate_digest"] or review.receipt_digest != link["receipt_digest"]:
            _fail("OBSERVATION_SUCCESSOR_IDENTITY_INVALID")
        if validated["observation_id"] not in review.evidence_refs:
            _fail("OBSERVATION_SUCCESSOR_REFERENCE_MISSING")
    if any(item["status"] != "PENDING" for row in closure["records"] for item in row["evidence"].values()):
        _fail("OBSERVATION_CLOSURE_CHANGED")
    status = gate0_status(required_assets=tuple(expected), reviews=successor_reviews, acquisition_receipts=receipts, authority_present=True, scope_digest=closure["scope_digest"])
    if status["status"] != "BLOCKED" or status["reviewed_asset_count"] != 0:
        _fail("OBSERVATION_GATE0_STATE_CHANGED")
    return copy.deepcopy(dict(validated))
