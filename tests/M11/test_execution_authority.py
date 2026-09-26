from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

import pytest

from app.m11_execution_authority import (
    AUTHORITY_SCHEMA,
    ExecutionAuthorityError,
    M11Operation,
    assert_batch_authorized,
    scope_digest,
    validate_execution_authority,
)

pytestmark = pytest.mark.m11


SOURCE_IDS = ["rfc-editor-index", "iana-registries"]
ASSETS = {
    "rfc-editor-index": ["rfc9110", "rfc9293"],
    "iana-registries": ["service-names-port-numbers-csv"],
}
SCOPE = scope_digest({"sources": SOURCE_IDS, "assets": ASSETS, "version": 1})
NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


def _authority() -> dict:
    return {
        "schema": AUTHORITY_SCHEMA,
        "operation": "acquisition",
        "authority_id": "m11-acquisition-20260925",
        "issued_by": "owner",
        "issued_at": "2026-09-25T00:00:00Z",
        "expires_at": "2026-09-26T00:00:00Z",
        "scope_digest": SCOPE,
        "source_ids": SOURCE_IDS,
        "asset_ids": ASSETS,
        "metadata_only": False,
        "publication_authorized": False,
        "status": "AUTHORIZED",
    }


def test_valid_authority_is_operation_and_scope_bound():
    authority = validate_execution_authority(
        _authority(), operation=M11Operation.ACQUISITION,
        expected_scope_digest=SCOPE, now=NOW,
    )
    assert authority.operation == "acquisition"
    assert authority.assets_for("rfc-editor-index") == {"rfc9110", "rfc9293"}
    assert_batch_authorized(authority, ASSETS)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda p: p.pop("schema"), "AUTHORITY_FIELDS_INVALID"),
        (lambda p: p.update(metadata_only=True), "AUTHORITY_NOT_EXECUTABLE"),
        (lambda p: p.update(operation="formal_3k"), "AUTHORITY_OPERATION_MISMATCH"),
        (lambda p: p.update(publication_authorized=True), "AUTHORITY_PUBLICATION_FORBIDDEN"),
        (lambda p: p.update(scope_digest="0" * 64), "AUTHORITY_SCOPE_MISMATCH"),
        (lambda p: p.update(source_ids=["network-candidates"]), "AUTHORITY_SOURCE_SCOPE_INVALID"),
        (lambda p: p.update(asset_ids={"rfc-editor-index": ["../secret"], "iana-registries": ["x"]}), "AUTHORITY_ASSET_ID_INVALID"),
        (lambda p: p.update(content="secret"), "AUTHORITY_FIELDS_INVALID"),
    ],
)
def test_authority_rejects_mutations(mutation, code):
    payload = copy.deepcopy(_authority())
    mutation(payload)
    with pytest.raises(ExecutionAuthorityError) as exc_info:
        validate_execution_authority(payload, operation="acquisition", expected_scope_digest=SCOPE, now=NOW)
    assert str(exc_info.value) == code


def test_authority_rejects_expired_or_future_records():
    payload = _authority()
    with pytest.raises(ExecutionAuthorityError, match="AUTHORITY_EXPIRED"):
        validate_execution_authority(payload, operation="acquisition", expected_scope_digest=SCOPE,
                                     now=NOW + timedelta(days=2))
    payload["issued_at"] = "2026-09-25T13:00:00Z"
    with pytest.raises(ExecutionAuthorityError, match="AUTHORITY_EXPIRED"):
        validate_execution_authority(payload, operation="acquisition", expected_scope_digest=SCOPE, now=NOW)


def test_authority_rejects_batch_expansion_without_leaking_values():
    authority = validate_execution_authority(_authority(), operation="acquisition",
                                             expected_scope_digest=SCOPE, now=NOW)
    with pytest.raises(ExecutionAuthorityError) as exc_info:
        assert_batch_authorized(authority, {"rfc-editor-index": ["rfc1034"]})
    assert str(exc_info.value) == "AUTHORITY_BATCH_OUT_OF_SCOPE"
    assert "rfc1034" not in str(exc_info.value)


def test_scope_digest_is_deterministic_and_rejects_non_json_values():
    assert scope_digest({"b": 2, "a": 1}) == scope_digest({"a": 1, "b": 2})
    with pytest.raises(ExecutionAuthorityError, match="AUTHORITY_SCOPE_INVALID"):
        scope_digest({"bad": object()})
