"""Offline schema and validation primitives for M8 metadata-discovery governance.

This module deliberately has no network, package-manager, resolver, installer, or
collector capability.  It validates governance documents and preserves the distinction
between project intent, discovery authorization, and later artifact acquisition.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

CANONICALIZATION_ID = "sa-json-c14n-v1"
AUTHORIZATION_TOKEN = "METADATA_DISCOVERY_AUTHORIZATION_APPROVED"
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_FILES = 64
MAX_LIMIT = 0
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class MetadataGovernanceError(ValueError):
    """Raised when a metadata governance document is unsafe or malformed."""


def canonical_bytes(value: Any) -> bytes:
    """Serialize one JSON value using the repository's canonical JSON contract."""
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise MetadataGovernanceError("invalid canonical JSON value") from exc
    return encoded + b"\n"


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MetadataGovernanceError("duplicate JSON key")
        result[key] = value
    return result


def strict_loads(data: bytes) -> Any:
    if type(data) is not bytes or len(data) > MAX_DOCUMENT_BYTES:
        raise MetadataGovernanceError("document bytes exceed safety bound")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicates,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                MetadataGovernanceError("non-finite JSON number")
            ),
        )
    except MetadataGovernanceError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise MetadataGovernanceError("invalid JSON document") from exc
    reject_surrogates(value)
    return value


def reject_surrogates(value: Any) -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise MetadataGovernanceError("surrogate character is not allowed")
    elif isinstance(value, dict):
        for key, item in value.items():
            reject_surrogates(key)
            reject_surrogates(item)
    elif isinstance(value, list):
        for item in value:
            reject_surrogates(item)
    elif isinstance(value, float) and not math.isfinite(value):
        raise MetadataGovernanceError("non-finite number is not allowed")


def parse_canonical_document(data: bytes) -> dict[str, Any]:
    value = strict_loads(data)
    if not isinstance(value, dict):
        raise MetadataGovernanceError("document root must be an object")
    if canonical_bytes(value) != data:
        raise MetadataGovernanceError("document is not canonical")
    return value


def require_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise MetadataGovernanceError(f"{label} keys are not exact")


def require_type(value: Any, expected: type, label: str) -> None:
    if type(value) is not expected:
        raise MetadataGovernanceError(f"{label} has wrong type")


def validate_git_binding(binding: Any, label: str = "git_binding") -> None:
    if not isinstance(binding, dict):
        raise MetadataGovernanceError(f"{label} must be an object")
    require_keys(binding, {"commit", "parent", "tree"}, label)
    for key in ("commit", "parent", "tree"):
        if HEX40.fullmatch(binding[key]) is None:
            raise MetadataGovernanceError(f"{label}.{key} must be a full Git OID")
    if binding["commit"] == binding["parent"]:
        raise MetadataGovernanceError("commit cannot equal parent")


def validate_evidence_item(item: Any) -> None:
    if not isinstance(item, dict):
        raise MetadataGovernanceError("evidence item must be an object")
    require_keys(item, {"path", "git_blob_oid", "byte_count", "sha256", "classification"}, "evidence")
    path = item["path"]
    require_type(path, str, "evidence.path")
    if not path or "\\" in path or path.startswith("/") or ".." in path.split("/"):
        raise MetadataGovernanceError("evidence path is unsafe")
    require_type(item["byte_count"], int, "evidence.byte_count")
    if item["byte_count"] < 0 or item["byte_count"] > MAX_DOCUMENT_BYTES:
        raise MetadataGovernanceError("evidence byte count is out of bounds")
    require_type(item["classification"], str, "evidence.classification")
    if item["classification"] not in {
        "PROJECT_DESCRIPTION", "PRIVATE_TOOLING_METADATA", "API_PRESENTATION_METADATA",
        "RUNTIME_DEPENDENCY_DECLARATION", "DEVELOPMENT_DEPENDENCY_DECLARATION",
        "HISTORICAL_GOVERNANCE_BOUNDARY",
    }:
        raise MetadataGovernanceError("evidence classification is invalid")
    if HEX40.fullmatch(item["git_blob_oid"]) is None:
        raise MetadataGovernanceError("evidence blob OID is invalid")
    if HEX64.fullmatch(item["sha256"]) is None:
        raise MetadataGovernanceError("evidence SHA-256 is invalid")


def validate_candidate(candidate: dict[str, Any]) -> None:
    expected = {
        "canonicalization_id", "format", "cycle_id", "source_commit", "git_binding",
        "evidence", "intent", "proposed_discovery_limits", "current_effective_limits",
        "authorization", "execution_counts", "qa", "status", "allowed_next_action",
        "forbidden_actions",
    }
    require_keys(candidate, expected, "candidate")
    if candidate["canonicalization_id"] != CANONICALIZATION_ID:
        raise MetadataGovernanceError("wrong canonicalization contract")
    if candidate["format"] != "m8-metadata-discovery-candidate-v1":
        raise MetadataGovernanceError("wrong candidate format")
    for key in ("cycle_id", "source_commit", "allowed_next_action", "status"):
        require_type(candidate[key], str, f"candidate.{key}")
    required_status = "METADATA_DISCOVERY_INTENT_OWNER_SELECTION_REQUIRED"
    if candidate["status"] != required_status:
        raise MetadataGovernanceError("candidate must remain failed closed")
    if candidate["allowed_next_action"] != required_status:
        raise MetadataGovernanceError("allowed next action must require Owner selection")
    if HEX40.fullmatch(candidate["source_commit"]) is None:
        raise MetadataGovernanceError("source_commit must be a full Git OID")
    validate_git_binding(candidate["git_binding"])
    if candidate["source_commit"] != candidate["git_binding"]["commit"]:
        raise MetadataGovernanceError("source commit and Git binding differ")
    evidence = candidate["evidence"]
    if type(evidence) is not list or not evidence or len(evidence) > MAX_EVIDENCE_FILES:
        raise MetadataGovernanceError("evidence list is invalid")
    paths: set[str] = set()
    for item in evidence:
        validate_evidence_item(item)
        if item["path"] in paths:
            raise MetadataGovernanceError("duplicate evidence path")
        paths.add(item["path"])
    intent = candidate["intent"]
    require_keys(intent, {"selection_state", "package_name", "version", "artifact", "metadata_url"}, "intent")
    if intent["selection_state"] not in {"UNRESOLVED", "OWNER_SELECTED"}:
        raise MetadataGovernanceError("invalid intent selection state")
    for key in ("package_name", "version", "artifact", "metadata_url"):
        if intent[key] is not None and type(intent[key]) is not str:
            raise MetadataGovernanceError(f"intent.{key} must be string or null")
    if intent["selection_state"] == "UNRESOLVED" and any(
        intent[key] is not None
        for key in ("package_name", "version", "artifact", "metadata_url")
    ):
        raise MetadataGovernanceError(
            "unresolved intent must not contain identity or endpoint values"
        )
    for section in ("proposed_discovery_limits", "current_effective_limits"):
        limits = candidate[section]
        if not isinstance(limits, dict):
            raise MetadataGovernanceError(f"{section} must be an object")
        if set(limits) != {"metadata_requests", "dns_requests", "network_requests", "downloads", "resolvers", "installers"}:
            raise MetadataGovernanceError(f"{section} keys are not exact")
        for key, value in limits.items():
            if type(value) is not int or value < 0:
                raise MetadataGovernanceError(f"{section}.{key} is invalid")
    if any(candidate["current_effective_limits"].values()):
        raise MetadataGovernanceError("current effective limits must remain zero")
    if any(candidate["proposed_discovery_limits"].values()):
        raise MetadataGovernanceError(
            "proposed discovery limits must remain zero before Owner selection"
        )
    authorization = candidate["authorization"]
    require_keys(authorization, {"metadata_discovery_authorized", "authorization_token_present", "token"}, "authorization")
    if any(type(authorization[key]) is not bool for key in ("metadata_discovery_authorized", "authorization_token_present")):
        raise MetadataGovernanceError("authorization flags must be boolean")
    if authorization["metadata_discovery_authorized"] or authorization["authorization_token_present"] or authorization["token"] is not None:
        raise MetadataGovernanceError("authorization must remain absent in candidate")
    counts = candidate["execution_counts"]
    if not isinstance(counts, dict) or set(counts) != {"network", "dns", "metadata", "downloads", "downloaders", "collectors", "resolvers", "installers", "m8"}:
        raise MetadataGovernanceError("execution count keys are not exact")
    if any(type(value) is not int or value != 0 for value in counts.values()):
        raise MetadataGovernanceError("execution counts must remain zero")
    qa = candidate["qa"]
    require_keys(qa, {"builder_internal", "adversarial", "round", "max_rounds"}, "qa")
    if qa["builder_internal"] not in {"PASS", "FAIL"} or qa["adversarial"] not in {"PASS", "FAIL"}:
        raise MetadataGovernanceError("QA result is invalid")
    if (
        type(qa["round"]) is not int
        or type(qa["max_rounds"]) is not int
        or qa["round"] < 1
        or qa["round"] > qa["max_rounds"]
        or qa["max_rounds"] != 3
    ):
        raise MetadataGovernanceError("QA round bound is invalid")
    if qa["builder_internal"] != "PASS" or qa["adversarial"] != "PASS":
        raise MetadataGovernanceError("candidate QA must pass before review")
    forbidden = candidate["forbidden_actions"]
    required_forbidden = {
        "network", "dns", "http", "https", "pypi", "metadata_request",
        "download", "resolver", "installation", "collector", "m8_execution",
    }
    if (
        type(forbidden) is not list
        or len(forbidden) != len(required_forbidden)
        or any(type(action) is not str for action in forbidden)
        or set(forbidden) != required_forbidden
    ):
        raise MetadataGovernanceError("forbidden action list is not exact")


def validate_authorization_token(token: Any) -> bool:
    """Exact-token predicate; it never performs or authorizes an operation itself."""
    return type(token) is str and token == AUTHORIZATION_TOKEN


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
