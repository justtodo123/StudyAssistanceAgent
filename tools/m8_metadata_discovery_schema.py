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
MAX_CHAIN_BYTES = 8 * MAX_DOCUMENT_BYTES
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
    if type(value) is not dict:
        raise MetadataGovernanceError(f"{label} must be an object")
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
        if type(binding[key]) is not str or HEX40.fullmatch(binding[key]) is None:
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
        "RUNTIME_PARSER_IMPLEMENTATION_BINDING", "RUNTIME_PARSER_CONTRACT_TEST",
        "FROZEN_RUNTIME_PARSER_POLICY", "HISTORICAL_GOVERNANCE_BOUNDARY",
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


SCOPE_CANDIDATE_FORMAT = "m8-metadata-discovery-scope-candidate-v1"
SCOPE_REVIEW_FORMAT = "m8-metadata-discovery-scope-review-v1"
SCOPE_REVIEW_REQUIRED = "METADATA_DISCOVERY_SCOPE_INDEPENDENT_REVIEW_REQUIRED"
SCOPE_OWNER_GATE_READY = "METADATA_DISCOVERY_SCOPE_OWNER_GATE_READY"
SCOPE_REVIEW_PASSED = "METADATA_DISCOVERY_SCOPE_REVIEW_PASSED_NO_AUTHORIZATION"
SCOPE_CANDIDATE_VALIDATED = "METADATA_DISCOVERY_SCOPE_CANDIDATE_VALIDATED_FOR_EXTERNAL_REVIEW"
SCOPE_BUILDER_ID = "M8_METADATA_DISCOVERY_SCOPE_BUILDER"
SCOPE_CYCLE_ID = "m8-metadata-discovery-scope-pypdf-6.0.0-20260920-r02"
SCOPE_EVIDENCE_CLASSIFICATIONS = {
    "platform/requirements.txt": "RUNTIME_DEPENDENCY_DECLARATION",
    "platform/app/parser_matrix.py": "RUNTIME_PARSER_IMPLEMENTATION_BINDING",
    "tests/M7/test_parser_matrix.py": "RUNTIME_PARSER_CONTRACT_TEST",
    "docs/plans/m7-source-lifecycle-plan.md": "FROZEN_RUNTIME_PARSER_POLICY",
    "docs/plans/references/m8-network-acquisition-owner-failed-closed-decision-20260919-r03.md": "HISTORICAL_GOVERNANCE_BOUNDARY",
}
SCOPE_FORBIDDEN_ACTIONS = {
    "network", "dns", "http", "https", "pypi", "metadata_request",
    "download", "resolver", "installation", "collector", "m8_execution",
    "endpoint_selection", "artifact_selection", "authorization",
}
SCOPE_LIMIT_KEYS = {
    "metadata_requests", "dns_requests", "network_requests", "network_bytes", "redirects",
    "downloads", "resolvers", "installers", "collectors", "m8_execution",
}
SCOPE_EXECUTION_KEYS = {
    "network", "dns", "metadata", "redirects", "downloads", "downloaders",
    "collectors", "resolvers", "installers", "m8",
}
SCOPE_EVIDENCE_PATHS = (
    "platform/requirements.txt",
    "platform/app/parser_matrix.py",
    "tests/M7/test_parser_matrix.py",
    "docs/plans/m7-source-lifecycle-plan.md",
    "docs/plans/references/m8-network-acquisition-owner-failed-closed-decision-20260919-r03.md",
)
SCOPE_ASSERTION_PATHS = SCOPE_EVIDENCE_PATHS[:4]
SCOPE_ASSERTIONS = {
    "platform/requirements.txt": (
        "runtime-requirement-pin",
        "pypdf==6.0.0",
        "The committed runtime dependency declaration contains the exact Owner-selected requirement.",
    ),
    "platform/app/parser_matrix.py": (
        "runtime-parser-binding",
        '"pdf": ParserSpec("pdf", "pypdf", "6.0.0", "pypdf", "pypdf", MAX_PDF_PAGES)',
        "The committed parser matrix binds PDF parsing to pypdf 6.0.0.",
    ),
    "tests/M7/test_parser_matrix.py": (
        "runtime-parser-contract",
        '"pdf": ("pypdf", "6.0.0")',
        "The committed parser contract test expects pypdf 6.0.0 for PDF.",
    ),
    "docs/plans/m7-source-lifecycle-plan.md": (
        "frozen-parser-policy",
        "`pdf` → `pypdf==6.0.0`",
        "The committed M7 policy freezes pypdf 6.0.0 for PDF.",
    ),
}


def _require_zero_object(value: Any, keys: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != keys:
        raise MetadataGovernanceError(f"{label} keys are not exact")
    if any(type(item) is not int or item != 0 for item in value.values()):
        raise MetadataGovernanceError(f"{label} must remain zero")


def _validate_scope_policy(policy: Any) -> None:
    require_keys(
        policy,
        {
            "policy_state", "host_allowlist", "endpoint_type", "methods",
            "headers", "tls", "redirects", "timeouts_seconds", "retries",
            "max_responses", "response_size_cap_bytes", "response_purpose",
            "follows_file_urls", "authorization_granted",
        },
        "proposed_metadata_policy",
    )
    if policy["policy_state"] != "PROPOSED_NOT_EFFECTIVE":
        raise MetadataGovernanceError("metadata policy must remain proposed")
    if type(policy["redirects"]) is not int or type(policy["retries"]) is not int:
        raise MetadataGovernanceError("metadata policy counters must be integers")
    if type(policy["max_responses"]) is not int or type(policy["response_size_cap_bytes"]) is not int:
        raise MetadataGovernanceError("metadata policy caps must be integers")
    timeouts = policy["timeouts_seconds"]
    if type(timeouts) is not dict or set(timeouts) != {"connect", "read", "total"}:
        raise MetadataGovernanceError("metadata timeouts are not exact")
    if any(type(value) is not int for value in timeouts.values()):
        raise MetadataGovernanceError("metadata timeouts must be integers")
    if policy["host_allowlist"] != ["pypi.org"]:
        raise MetadataGovernanceError("metadata host proposal is not exact")
    if policy["endpoint_type"] != "EXACT_VERSION_JSON_METADATA":
        raise MetadataGovernanceError("metadata endpoint proposal is not exact")
    if policy["methods"] != ["GET"]:
        raise MetadataGovernanceError("metadata method proposal is not exact")
    if policy["headers"] != {
        "Accept": "application/json",
        "User-Agent": "StudyAssistanceAgent-M8-Metadata-Discovery/1",
    }:
        raise MetadataGovernanceError("metadata headers proposal is not exact")
    if policy["tls"] != {
        "https_only": True,
        "certificate_verification": True,
        "hostname_verification": True,
        "minimum_version": "TLSv1.2",
    }:
        raise MetadataGovernanceError("TLS proposal is not exact")
    if policy["redirects"] != 0 or policy["retries"] != 0 or policy["max_responses"] != 1:
        raise MetadataGovernanceError("metadata policy caps are not exact")
    if policy["timeouts_seconds"] != {"connect": 5, "read": 10, "total": 15}:
        raise MetadataGovernanceError("metadata timeout proposal is not exact")
    if policy["response_size_cap_bytes"] != 2 * 1024 * 1024:
        raise MetadataGovernanceError("metadata response cap is not exact")
    if policy["response_purpose"] != "PACKAGE_VERSION_METADATA_ONLY":
        raise MetadataGovernanceError("metadata response purpose is invalid")
    if policy["follows_file_urls"] is not False or policy["authorization_granted"] is not False:
        raise MetadataGovernanceError("metadata policy cannot grant execution")


def _validate_scope_evidence_item(item: Any) -> None:
    validate_evidence_item(item)
    expected_classification = SCOPE_EVIDENCE_CLASSIFICATIONS.get(item["path"])
    if expected_classification is None:
        raise MetadataGovernanceError("scope evidence path is not allowlisted")
    if item["classification"] != expected_classification:
        raise MetadataGovernanceError("scope evidence classification does not match path")


def _validate_scope_assertion(item: Any) -> None:
    require_keys(
        item,
        {
            "assertion_id", "evidence_path", "git_blob_oid", "sha256",
            "required_utf8_fragment", "expected_occurrences", "claim",
        },
        "scope_assertion",
    )
    expected_assertion = SCOPE_ASSERTIONS.get(item["evidence_path"])
    if expected_assertion is None:
        raise MetadataGovernanceError("scope assertion path is not allowlisted")
    if tuple(item[key] for key in ("assertion_id", "required_utf8_fragment", "claim")) != expected_assertion:
        raise MetadataGovernanceError("scope assertion definition is not exact")
    if HEX40.fullmatch(item["git_blob_oid"]) is None or HEX64.fullmatch(item["sha256"]) is None:
        raise MetadataGovernanceError("scope assertion digest is invalid")
    for key in ("assertion_id", "evidence_path", "required_utf8_fragment", "claim"):
        require_type(item[key], str, f"scope_assertion.{key}")
    if type(item["expected_occurrences"]) is not int or item["expected_occurrences"] != 1:
        raise MetadataGovernanceError("scope assertion occurrence count is invalid")
    if not item["required_utf8_fragment"] or "http" in item["required_utf8_fragment"].lower():
        raise MetadataGovernanceError("scope assertion contains a URL-like fragment")


def validate_scope_candidate(candidate: dict[str, Any]) -> None:
    expected = {
        "canonicalization_id", "format", "candidate_type", "cycle_id", "source_commit",
        "source_git_binding", "evidence", "scope_assertion_bindings", "scope",
        "proposed_metadata_policy", "historical_constraints", "current_effective_limits",
        "authorization", "execution_counts", "qa", "builder_id", "status", "m8_status",
        "allowed_next_action", "forbidden_actions",
    }
    require_keys(candidate, expected, "scope candidate")
    if candidate["canonicalization_id"] != CANONICALIZATION_ID:
        raise MetadataGovernanceError("wrong canonicalization contract")
    if candidate["format"] != SCOPE_CANDIDATE_FORMAT:
        raise MetadataGovernanceError("wrong scope candidate format")
    if candidate["candidate_type"] != "RUNTIME_DEPENDENCY_METADATA_DISCOVERY_SCOPE":
        raise MetadataGovernanceError("wrong scope candidate type")
    for key in ("cycle_id", "source_commit", "builder_id", "status", "allowed_next_action"):
        require_type(candidate[key], str, f"scope candidate.{key}")
    if candidate["cycle_id"] != SCOPE_CYCLE_ID:
        raise MetadataGovernanceError("scope cycle ID is not exact")
    if candidate["builder_id"] != SCOPE_BUILDER_ID:
        raise MetadataGovernanceError("scope builder ID is not exact")
    if candidate["status"] != SCOPE_REVIEW_REQUIRED or candidate["allowed_next_action"] != SCOPE_REVIEW_REQUIRED:
        raise MetadataGovernanceError("scope candidate must require independent review")
    if candidate["m8_status"] != "BLOCKED / NOT_STARTED":
        raise MetadataGovernanceError("M8 must remain blocked and not started")
    if HEX40.fullmatch(candidate["source_commit"]) is None:
        raise MetadataGovernanceError("scope source_commit must be a full Git OID")
    validate_git_binding(candidate["source_git_binding"], "source_git_binding")
    if candidate["source_commit"] != candidate["source_git_binding"]["commit"]:
        raise MetadataGovernanceError("scope source binding differs from source commit")
    evidence = candidate["evidence"]
    if (
        type(evidence) is not list
        or len(evidence) != len(SCOPE_EVIDENCE_PATHS)
        or any(type(item) is not dict for item in evidence)
    ):
        raise MetadataGovernanceError("scope evidence inventory is not exact")
    for index, item in enumerate(evidence):
        _validate_scope_evidence_item(item)
        if item["path"] != SCOPE_EVIDENCE_PATHS[index]:
            raise MetadataGovernanceError("scope evidence order is not exact")
    assertions = candidate["scope_assertion_bindings"]
    if (
        type(assertions) is not list
        or len(assertions) != len(SCOPE_ASSERTION_PATHS)
        or any(type(item) is not dict for item in assertions)
    ):
        raise MetadataGovernanceError("scope assertion inventory is not exact")
    evidence_by_path = {item["path"]: item for item in evidence}
    for index, item in enumerate(assertions):
        _validate_scope_assertion(item)
        if item["evidence_path"] != SCOPE_ASSERTION_PATHS[index]:
            raise MetadataGovernanceError("scope assertion order is not exact")
        evidence_item = evidence_by_path[item["evidence_path"]]
        if item["git_blob_oid"] != evidence_item["git_blob_oid"]:
            raise MetadataGovernanceError("scope assertion blob binding differs from evidence")
        if item["sha256"] != evidence_item["sha256"]:
            raise MetadataGovernanceError("scope assertion digest binding differs from evidence")
    scope = candidate["scope"]
    require_keys(scope, {
        "scope_state", "scope_origin", "purpose", "distribution_name", "exact_version",
        "exact_requirement", "import_name", "consumer_format", "parser_id", "parser_version",
        "dependency_scope", "artifact", "metadata_url", "project_url",
        "endpoint_selection_state", "artifact_selection_state", "metadata_request_authorized",
    }, "scope")
    required_scope = {
        "scope_state": "OWNER_SUPPLIED_EXACT_SCOPE",
        "scope_origin": "USER_REQUIREMENT",
        "purpose": "M7_PDF_PARSER_RUNTIME_DEPENDENCY_METADATA_DISCOVERY_ONLY",
        "distribution_name": "pypdf",
        "exact_version": "6.0.0",
        "exact_requirement": "pypdf==6.0.0",
        "import_name": "pypdf",
        "consumer_format": "pdf",
        "parser_id": "pypdf",
        "parser_version": "6.0.0",
        "dependency_scope": ["pypdf"],
        "artifact": None,
        "metadata_url": None,
        "project_url": None,
        "endpoint_selection_state": "NOT_SELECTED",
        "artifact_selection_state": "NOT_SELECTED",
        "metadata_request_authorized": False,
    }
    if scope != required_scope:
        raise MetadataGovernanceError("scope assertion is not exact")
    _validate_scope_policy(candidate["proposed_metadata_policy"])
    historical = candidate["historical_constraints"]
    if type(historical) is not list or len(historical) != 1 or type(historical[0]) is not dict:
        raise MetadataGovernanceError("historical constraints are not exact")
    require_keys(historical[0], {"path", "classification", "non_authorizing", "statement"}, "historical constraint")
    if historical[0]["path"] != SCOPE_EVIDENCE_PATHS[-1] or historical[0]["classification"] != "HISTORICAL_GOVERNANCE_BOUNDARY":
        raise MetadataGovernanceError("historical constraint binding is invalid")
    if historical[0]["non_authorizing"] is not True or historical[0]["statement"] != "IMMUTABLE_FAILED_CLOSED_BOUNDARY_ONLY":
        raise MetadataGovernanceError("historical constraint must remain non-authorizing")
    _require_zero_object(candidate["current_effective_limits"], SCOPE_LIMIT_KEYS, "current effective limits")
    _require_zero_object(candidate["execution_counts"], SCOPE_EXECUTION_KEYS, "execution counts")
    auth = candidate["authorization"]
    require_keys(auth, {"metadata_discovery_authorized", "authorization_token_present", "token", "network_access_authorized", "wheel_download_authorized", "resolver_execution_authorized", "installation_authorized"}, "authorization")
    if any(auth[key] is not False for key in auth if key != "token") or auth["token"] is not None:
        raise MetadataGovernanceError("scope authorization must remain absent")
    qa = candidate["qa"]
    require_keys(qa, {"builder_internal", "adversarial", "round", "max_rounds", "independent_review_completed"}, "scope qa")
    if qa["builder_internal"] != "PASS" or qa["adversarial"] != "PASS" or qa["independent_review_completed"] is not False:
        raise MetadataGovernanceError("scope QA role boundary is invalid")
    if type(qa["round"]) is not int or type(qa["max_rounds"]) is not int or qa["round"] < 1 or qa["round"] > qa["max_rounds"] or qa["max_rounds"] != 3:
        raise MetadataGovernanceError("scope QA round bound is invalid")
    if candidate["forbidden_actions"] != sorted(SCOPE_FORBIDDEN_ACTIONS):
        raise MetadataGovernanceError("scope forbidden action list is not exact")


def validate_scope_review(review: dict[str, Any]) -> None:
    """Reject the legacy self-attested review format at the provenance boundary."""
    if type(review) is not dict:
        raise MetadataGovernanceError("scope review must be an object")
    raise MetadataGovernanceError(
        "independent review provenance is unverified; self-attestation cannot "
        "produce independent approval or Owner Gate readiness"
    )


SCOPE_CHAIN_FORMAT = "m8-metadata-discovery-scope-chain-v1"
SCOPE_SELF_CHECK_FORMAT = "m8-metadata-discovery-scope-self-check-v1"
SCOPE_REVIEW_REQUEST_FORMAT = "m8-metadata-discovery-scope-review-request-v1"
SCOPE_REVIEW_PROMPT_FORMAT = "m8-metadata-discovery-scope-review-prompt-v1"
SCOPE_REVIEW_TARGET_FORMAT = "m8-metadata-discovery-scope-review-target-v1"
SCOPE_DISPATCH_FORMAT = "m8-metadata-discovery-scope-dispatch-v1"
SCOPE_READY_FOR_EXTERNAL_REVIEW = "READY_FOR_EXTERNAL_INDEPENDENT_REVIEW"
SCOPE_SINGLE_PARENT_POLICY = "ordinary_single_parent_commit_only"
SCOPE_REVIEW_PROTOCOL_ID = "m8-metadata-discovery-scope-review-protocol-v1"
SCOPE_REVIEW_ROLE = "INDEPENDENT_METADATA_DISCOVERY_SCOPE_REVIEWER"
SCOPE_RESPONSE_FORMAT = "m8-metadata-discovery-scope-external-review-v1"
SCOPE_SELF_CHECK_DECISION = "CANDIDATE_READY_FOR_EXTERNAL_REVIEW"
SCOPE_REVIEW_REQUIRED_CHECKS = (
    "canonical_candidate",
    "source_binding",
    "evidence_bindings",
    "scope_assertions",
    "policy_closed",
    "zero_authority",
    "history_immutable",
    "no_artifact_selection",
    "chain_binding",
    "reviewer_provenance",
)
SCOPE_REVIEW_PROTOCOL = {
    "protocol_id": SCOPE_REVIEW_PROTOCOL_ID,
    "required_checks": list(SCOPE_REVIEW_REQUIRED_CHECKS),
    "prohibited_actions": sorted(SCOPE_FORBIDDEN_ACTIONS),
    "response_format": SCOPE_RESPONSE_FORMAT,
}
SCOPE_REVIEW_PROTOCOL_SHA256 = hashlib.sha256(
    canonical_bytes(SCOPE_REVIEW_PROTOCOL)
).hexdigest()
SCOPE_CHAIN_STAGES = (
    "candidate_publication",
    "builder_self_check",
    "review_request",
    "review_prompt",
    "review_target",
    "dispatch_manifest",
)
SCOPE_CHAIN_PREDECESSORS = {
    "candidate_publication": (),
    "builder_self_check": ("candidate_publication",),
    "review_request": ("candidate_publication", "builder_self_check"),
    "review_prompt": ("candidate_publication", "review_request"),
    "review_target": (
        "candidate_publication",
        "builder_self_check",
        "review_request",
        "review_prompt",
    ),
    "dispatch_manifest": (
        "candidate_publication",
        "builder_self_check",
        "review_request",
        "review_prompt",
        "review_target",
    ),
}
SCOPE_CHAIN_PATHS = {
    "candidate_publication": "m8/metadata-discovery/scope-candidate.json",
    "builder_self_check": "m8/metadata-discovery/builder-self-check.json",
    "review_request": "m8/metadata-discovery/review-request.json",
    "review_prompt": "m8/metadata-discovery/review-prompt.json",
    "review_target": "m8/metadata-discovery/review-target.json",
    "dispatch_manifest": "m8/metadata-discovery/dispatch-manifest.json",
}
SCOPE_CHAIN_BINDING_KEYS = {
    "commit", "parent", "tree", "path", "git_blob_oid", "byte_count", "sha256",
}
SCOPE_CHAIN_REF_KEYS = {
    "stage", "record_id", "commit", "parent", "tree", "path", "git_blob_oid", "byte_count", "sha256",
}
SCOPE_STAGE_GOVERNANCE_KEYS = {
    "m8_status", "current_effective_limits", "execution_counts", "authorization",
}
SCOPE_STAGE_AUTHORIZATION_KEYS = {
    "metadata_discovery_authorized", "network_access_authorized",
    "wheel_download_authorized", "resolver_execution_authorized",
    "installation_authorized", "token",
}


def _validate_scope_chain_publication(binding: Any) -> None:
    if type(binding) is not dict:
        raise MetadataGovernanceError("scope chain publication must be an object")
    require_keys(binding, SCOPE_CHAIN_BINDING_KEYS, "scope chain publication")
    validate_git_binding(
        {key: binding[key] for key in ("commit", "parent", "tree")},
        "scope chain publication commit",
    )
    if type(binding["path"]) is not str or not binding["path"]:
        raise MetadataGovernanceError("scope chain publication path is invalid")
    path_parts = binding["path"].split("/")
    if (
        "\\" in binding["path"]
        or binding["path"].startswith("/")
        or any(part in {"", ".", ".."} for part in path_parts)
    ):
        raise MetadataGovernanceError("scope chain publication path is unsafe")
    if type(binding["git_blob_oid"]) is not str or HEX40.fullmatch(binding["git_blob_oid"]) is None:
        raise MetadataGovernanceError("scope chain publication blob OID is invalid")
    if type(binding["byte_count"]) is not int or binding["byte_count"] < 1:
        raise MetadataGovernanceError("scope chain publication byte count is invalid")
    if type(binding["sha256"]) is not str or HEX64.fullmatch(binding["sha256"]) is None:
        raise MetadataGovernanceError("scope chain publication digest is invalid")


def _validate_scope_chain_ref(ref: Any) -> None:
    if type(ref) is not dict:
        raise MetadataGovernanceError("scope chain predecessor must be an object")
    require_keys(ref, SCOPE_CHAIN_REF_KEYS, "scope chain predecessor")
    for key in ("stage", "record_id"):
        if type(ref[key]) is not str or not ref[key]:
            raise MetadataGovernanceError(f"scope chain predecessor.{key} is invalid")
    if ref["stage"] not in SCOPE_CHAIN_STAGES:
        raise MetadataGovernanceError("scope chain predecessor stage is invalid")
    _validate_scope_chain_publication({
        key: ref[key] for key in SCOPE_CHAIN_BINDING_KEYS
    })


def _validate_stage_governance(governance: Any) -> None:
    require_keys(governance, SCOPE_STAGE_GOVERNANCE_KEYS, "stage governance")
    if governance["m8_status"] != "BLOCKED / NOT_STARTED":
        raise MetadataGovernanceError("stage governance must keep M8 blocked")
    _require_zero_object(
        governance["current_effective_limits"],
        SCOPE_LIMIT_KEYS,
        "stage current effective limits",
    )
    _require_zero_object(
        governance["execution_counts"],
        SCOPE_EXECUTION_KEYS,
        "stage execution counts",
    )
    authorization = governance["authorization"]
    require_keys(
        authorization,
        SCOPE_STAGE_AUTHORIZATION_KEYS,
        "stage authorization",
    )
    if (
        any(
            authorization[key] is not False
            for key in authorization
            if key != "token"
        )
        or authorization["token"] is not None
    ):
        raise MetadataGovernanceError("stage authorization must remain absent")


def _validate_protocol_binding(binding: Any) -> None:
    require_keys(binding, {"protocol_id", "sha256"}, "review protocol binding")
    if binding != {
        "protocol_id": SCOPE_REVIEW_PROTOCOL_ID,
        "sha256": SCOPE_REVIEW_PROTOCOL_SHA256,
    }:
        raise MetadataGovernanceError("review protocol binding is not exact")


def _validate_stage_common(
    payload: Any,
    expected_keys: set[str],
    expected_format: str,
    expected_stage: str,
) -> None:
    require_keys(payload, expected_keys, f"{expected_stage} payload")
    if payload["canonicalization_id"] != CANONICALIZATION_ID:
        raise MetadataGovernanceError("stage canonicalization is invalid")
    if payload["format"] != expected_format:
        raise MetadataGovernanceError("stage payload format is invalid")
    if payload["cycle_id"] != SCOPE_CYCLE_ID:
        raise MetadataGovernanceError("stage cycle ID is not exact")
    if payload["stage"] != expected_stage:
        raise MetadataGovernanceError("stage payload identity is invalid")
    _validate_stage_governance(payload["governance"])


def validate_scope_stage_payload(stage: str, payload: Any) -> None:
    """Validate one canonical pre-review payload without performing Git I/O."""
    if type(stage) is not str or stage not in SCOPE_CHAIN_STAGES:
        raise MetadataGovernanceError("scope stage is invalid")
    if stage == "candidate_publication":
        validate_scope_candidate(payload)
        return
    common = {
        "canonicalization_id", "format", "cycle_id", "stage", "governance",
    }
    if stage == "builder_self_check":
        _validate_stage_common(
            payload,
            common | {
                "candidate_binding", "checks", "decision",
                "independent_review_completed", "commit_policy",
            },
            SCOPE_SELF_CHECK_FORMAT,
            stage,
        )
        _validate_scope_chain_ref(payload["candidate_binding"])
        if payload["candidate_binding"]["stage"] != "candidate_publication":
            raise MetadataGovernanceError("self-check candidate binding is invalid")
        expected_checks = set(SCOPE_REVIEW_REQUIRED_CHECKS[:-2])
        if (
            type(payload["checks"]) is not dict
            or set(payload["checks"]) != expected_checks
            or any(value is not True for value in payload["checks"].values())
        ):
            raise MetadataGovernanceError("builder self-check results are not exact")
        if payload["decision"] != SCOPE_SELF_CHECK_DECISION:
            raise MetadataGovernanceError("builder self-check decision is invalid")
        if payload["independent_review_completed"] is not False:
            raise MetadataGovernanceError("builder cannot complete independent review")
        if payload["commit_policy"] != SCOPE_SINGLE_PARENT_POLICY:
            raise MetadataGovernanceError("builder self-check commit policy is invalid")
        return
    if stage == "review_request":
        _validate_stage_common(
            payload,
            common | {
                "candidate_binding", "self_check_binding", "request_id",
                "requested_reviewer_role", "protocol_binding", "status",
                "review_completed",
            },
            SCOPE_REVIEW_REQUEST_FORMAT,
            stage,
        )
        bindings = (
            ("candidate_binding", "candidate_publication"),
            ("self_check_binding", "builder_self_check"),
        )
        for key, expected in bindings:
            _validate_scope_chain_ref(payload[key])
            if payload[key]["stage"] != expected:
                raise MetadataGovernanceError("review request binding is invalid")
        if type(payload["request_id"]) is not str or not payload["request_id"]:
            raise MetadataGovernanceError("review request ID is invalid")
        if payload["requested_reviewer_role"] != SCOPE_REVIEW_ROLE:
            raise MetadataGovernanceError("requested reviewer role is invalid")
        _validate_protocol_binding(payload["protocol_binding"])
        if payload["status"] != SCOPE_REVIEW_REQUIRED or payload["review_completed"] is not False:
            raise MetadataGovernanceError("review request status is invalid")
        return
    if stage == "review_prompt":
        _validate_stage_common(
            payload,
            common | {
                "candidate_binding", "request_binding", "protocol",
                "protocol_sha256", "review_not_completed",
            },
            SCOPE_REVIEW_PROMPT_FORMAT,
            stage,
        )
        for key, expected in (
            ("candidate_binding", "candidate_publication"),
            ("request_binding", "review_request"),
        ):
            _validate_scope_chain_ref(payload[key])
            if payload[key]["stage"] != expected:
                raise MetadataGovernanceError("review prompt binding is invalid")
        if payload["protocol"] != SCOPE_REVIEW_PROTOCOL:
            raise MetadataGovernanceError("review prompt protocol is not exact")
        if payload["protocol_sha256"] != SCOPE_REVIEW_PROTOCOL_SHA256:
            raise MetadataGovernanceError("review prompt protocol digest is invalid")
        if payload["review_not_completed"] is not True:
            raise MetadataGovernanceError("review prompt cannot claim review completion")
        return
    if stage == "review_target":
        _validate_stage_common(
            payload,
            common | {
                "target_id", "candidate_binding", "self_check_binding",
                "request_binding", "prompt_binding", "protocol_binding",
                "status",
            },
            SCOPE_REVIEW_TARGET_FORMAT,
            stage,
        )
        for key, expected in (
            ("candidate_binding", "candidate_publication"),
            ("self_check_binding", "builder_self_check"),
            ("request_binding", "review_request"),
            ("prompt_binding", "review_prompt"),
        ):
            _validate_scope_chain_ref(payload[key])
            if payload[key]["stage"] != expected:
                raise MetadataGovernanceError("review target binding is invalid")
        if type(payload["target_id"]) is not str or not payload["target_id"]:
            raise MetadataGovernanceError("review target ID is invalid")
        _validate_protocol_binding(payload["protocol_binding"])
        if payload["status"] != SCOPE_REVIEW_REQUIRED:
            raise MetadataGovernanceError("review target status is invalid")
        return
    _validate_stage_common(
        payload,
        common | {
            "dispatch_id", "candidate_binding", "self_check_binding",
            "request_binding", "prompt_binding", "target_binding",
            "protocol_binding", "selected_target_count", "status",
        },
        SCOPE_DISPATCH_FORMAT,
        stage,
    )
    for key, expected in (
        ("candidate_binding", "candidate_publication"),
        ("self_check_binding", "builder_self_check"),
        ("request_binding", "review_request"),
        ("prompt_binding", "review_prompt"),
        ("target_binding", "review_target"),
    ):
        _validate_scope_chain_ref(payload[key])
        if payload[key]["stage"] != expected:
            raise MetadataGovernanceError("dispatch binding is invalid")
    if type(payload["dispatch_id"]) is not str or not payload["dispatch_id"]:
        raise MetadataGovernanceError("dispatch ID is invalid")
    _validate_protocol_binding(payload["protocol_binding"])
    if type(payload["selected_target_count"]) is not int or payload["selected_target_count"] != 1:
        raise MetadataGovernanceError("dispatch must select exactly one review target")
    if payload["status"] != SCOPE_READY_FOR_EXTERNAL_REVIEW:
        raise MetadataGovernanceError("dispatch status is invalid")


def validate_scope_chain_record(
    record: dict[str, Any],
    expected_stage: str | None = None,
) -> None:
    """Validate one non-authorizing staged publication record."""
    expected = {
        "canonicalization_id", "format", "stage", "record_id",
        "publication", "predecessors", "non_authorizing",
    }
    require_keys(record, expected, "scope chain record")
    if record["canonicalization_id"] != CANONICALIZATION_ID:
        raise MetadataGovernanceError("scope chain canonicalization is invalid")
    if record["format"] != SCOPE_CHAIN_FORMAT:
        raise MetadataGovernanceError("scope chain format is invalid")
    if type(record["stage"]) is not str or record["stage"] not in SCOPE_CHAIN_STAGES:
        raise MetadataGovernanceError("scope chain stage is invalid")
    if expected_stage is not None and record["stage"] != expected_stage:
        raise MetadataGovernanceError("scope chain stage is not in the required position")
    if type(record["record_id"]) is not str or not record["record_id"]:
        raise MetadataGovernanceError("scope chain record ID is invalid")
    if record["non_authorizing"] is not True:
        raise MetadataGovernanceError("scope chain record must remain non-authorizing")
    _validate_scope_chain_publication(record["publication"])
    if record["publication"]["path"] != SCOPE_CHAIN_PATHS[record["stage"]]:
        raise MetadataGovernanceError("scope chain publication path is not fixed")
    predecessors = record["predecessors"]
    if type(predecessors) is not list:
        raise MetadataGovernanceError("scope chain predecessors must be a list")
    expected_predecessors = SCOPE_CHAIN_PREDECESSORS[record["stage"]]
    if (
        len(predecessors) != len(expected_predecessors)
        or any(type(ref) is not dict for ref in predecessors)
        or [ref["stage"] if "stage" in ref else None for ref in predecessors]
        != list(expected_predecessors)
    ):
        raise MetadataGovernanceError("scope chain predecessor stages are not exact")
    for ref in predecessors:
        _validate_scope_chain_ref(ref)
        if ref["commit"] == record["publication"]["commit"]:
            raise MetadataGovernanceError("scope chain cannot self-reference its publication")


def validate_scope_chain(records: list[dict[str, Any]]) -> None:
    """Validate the complete candidate-to-dispatch envelope chain without Git I/O."""
    if type(records) is not list or any(type(record) is not dict for record in records):
        raise MetadataGovernanceError("scope chain records must be an object list")
    if (
        len(records) != len(SCOPE_CHAIN_STAGES)
        or [record.get("stage") for record in records] != list(SCOPE_CHAIN_STAGES)
    ):
        raise MetadataGovernanceError("scope chain stages are not exact")
    by_stage: dict[str, dict[str, Any]] = {}
    record_ids: set[str] = set()
    for index, record in enumerate(records):
        validate_scope_chain_record(record, SCOPE_CHAIN_STAGES[index])
        if record["record_id"] in record_ids:
            raise MetadataGovernanceError("scope chain record IDs must be unique")
        record_ids.add(record["record_id"])
        by_stage[record["stage"]] = record
        if index and record["publication"]["parent"] != records[index - 1]["publication"]["commit"]:
            raise MetadataGovernanceError("scope chain publication is not a direct forward step")
        if index == 0 and record["predecessors"]:
            raise MetadataGovernanceError("candidate publication cannot have predecessors")
        for ref in record["predecessors"]:
            predecessor = by_stage.get(ref["stage"])
            if predecessor is None:
                raise MetadataGovernanceError("scope chain contains a forward or deferred reference")
            expected_ref = {
                "stage": predecessor["stage"],
                "record_id": predecessor["record_id"],
                **predecessor["publication"],
            }
            if ref != expected_ref:
                raise MetadataGovernanceError("scope chain predecessor binding mismatch")
