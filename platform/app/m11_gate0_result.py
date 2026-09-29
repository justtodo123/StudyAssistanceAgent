"""Validate the immutable, metadata-only record of M11 Formal Gate 0 execution."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .m11_gate0 import EVIDENCE_CATEGORIES

RESULT_SCHEMA = "sa.m11.formal-gate0-result.v1"
RESULT_ID = "m11-p0-formal-gate0-26-result-20260928"
_HEX = re.compile(r"[0-9a-f]{64}")
_KEY = re.compile(r"[0-9a-f]{16}")
_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_PATH = re.compile(r"^(?:\\\\|//)")
_FORBIDDEN_KEYS = frozenset({
    "body", "bodies", "content", "excerpt", "normalized_text", "raw_body",
    "raw_text", "candidate_text", "candidate_body", "host_path", "absolute_path",
    "credential", "credentials", "token", "password", "learning_state",
    "private_learning_state",
})
_RUNNER_FIELDS = frozenset({
    "schema", "version", "status", "scope_digest", "input_digest",
    "required_asset_count", "reviewed_asset_count", "receipt_asset_count",
    "candidate_validated_count", "missing_asset_count", "missing_asset_keys",
    "failed_asset_keys", "evidence_categories", "lifecycle_counts_before", "owner_id",
    "signed_at", "authority_id", "acquisition_authority_id", "authority_present",
    "candidate_promotion_authorized", "publication_authorized",
})
_FIELDS = _RUNNER_FIELDS | {
    "result_id", "formal_gate0_executed", "formal_3k_executed", "network_used",
    "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included",
    "approved_document_count", "approved_chunk_count",
}


class FormalGate0ResultError(ValueError):
    """Raised when a persisted Formal Gate 0 result is not a safe exact record."""


def _fail(code: str) -> None:
    raise FormalGate0ResultError(code)


def _private(value: Any) -> bool:
    if isinstance(value, Mapping):
        if set(value) & _FORBIDDEN_KEYS:
            return True
        return any(_private(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_private(item) for item in value)
    if isinstance(value, str):
        return bool(_DRIVE_PATH.match(value) or _UNC_PATH.match(value))
    return False


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_formal_gate0_result(
    payload: Mapping[str, Any], *, expected_runner_result: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate one committed BLOCKED result against its read-only runner output."""
    if not isinstance(payload, Mapping) or set(payload) != _FIELDS:
        _fail("FORMAL_GATE0_RESULT_FIELDS_INVALID")
    if _private(payload):
        _fail("FORMAL_GATE0_RESULT_PRIVACY_FIELD")
    if payload["schema"] != RESULT_SCHEMA or payload["result_id"] != RESULT_ID:
        _fail("FORMAL_GATE0_RESULT_IDENTITY_INVALID")
    if not isinstance(expected_runner_result, Mapping) or set(expected_runner_result) != _RUNNER_FIELDS:
        _fail("FORMAL_GATE0_RESULT_EXPECTED_INVALID")
    if any(
        payload[field] != expected_runner_result[field]
        for field in _RUNNER_FIELDS - {"schema"}
    ):
        _fail("FORMAL_GATE0_RESULT_BINDING_INVALID")
    if payload["status"] != "BLOCKED":
        _fail("FORMAL_GATE0_RESULT_STATUS_INVALID")
    if not _HEX.fullmatch(payload["scope_digest"]) or not _HEX.fullmatch(payload["input_digest"]):
        _fail("FORMAL_GATE0_RESULT_DIGEST_INVALID")
    if payload["evidence_categories"] != list(EVIDENCE_CATEGORIES):
        _fail("FORMAL_GATE0_RESULT_EVIDENCE_INVALID")
    if not all(_nonnegative_int(payload[field]) for field in (
        "required_asset_count", "reviewed_asset_count", "receipt_asset_count",
        "candidate_validated_count", "missing_asset_count", "approved_document_count",
        "approved_chunk_count",
    )):
        _fail("FORMAL_GATE0_RESULT_COUNT_INVALID")
    if payload["approved_document_count"] != 0 or payload["approved_chunk_count"] != 0:
        _fail("FORMAL_GATE0_RESULT_APPROVAL_FORBIDDEN")
    if not isinstance(payload["missing_asset_keys"], list) or not isinstance(payload["failed_asset_keys"], list):
        _fail("FORMAL_GATE0_RESULT_KEYS_INVALID")
    if any(not isinstance(item, str) or not _KEY.fullmatch(item)
           for item in [*payload["missing_asset_keys"], *payload["failed_asset_keys"]]):
        _fail("FORMAL_GATE0_RESULT_KEYS_INVALID")
    if len(set(payload["missing_asset_keys"])) != len(payload["missing_asset_keys"]):
        _fail("FORMAL_GATE0_RESULT_KEYS_INVALID")
    if payload["missing_asset_count"] != len(payload["missing_asset_keys"]):
        _fail("FORMAL_GATE0_RESULT_COUNT_INVALID")
    if payload["failed_asset_keys"]:
        _fail("FORMAL_GATE0_RESULT_FAILURE_INVALID")
    if payload["authority_present"] is not True:
        _fail("FORMAL_GATE0_RESULT_AUTHORITY_INVALID")
    if any(payload[field] is not False for field in (
        "candidate_promotion_authorized", "publication_authorized", "formal_3k_executed",
        "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included",
        "bodies_included",
    )):
        _fail("FORMAL_GATE0_RESULT_ESCALATION_FORBIDDEN")
    if payload["formal_gate0_executed"] is not True:
        _fail("FORMAL_GATE0_RESULT_EXECUTION_INVALID")
    lifecycle = payload["lifecycle_counts_before"]
    if not isinstance(lifecycle, Mapping) or any(
        not isinstance(key, str) or not _nonnegative_int(value) for key, value in lifecycle.items()
    ):
        _fail("FORMAL_GATE0_RESULT_LIFECYCLE_INVALID")
    return copy.deepcopy(dict(payload))
