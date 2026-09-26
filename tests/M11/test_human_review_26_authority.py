from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.m11_execution_authority import (
    AUTHORITY_SCHEMA,
    ExecutionAuthorityError,
    M11Operation,
    assert_batch_authorized,
    load_execution_authority,
    scope_digest,
    validate_execution_authority,
)

pytestmark = pytest.mark.m11

AUTHORITY_PATH = Path("data/manifests/m11-p0-human-review-26-authority-v1.json")
DIGEST_PATH = Path("data/manifests/m11-p0-digest-evidence-v1.json")
CHECKLIST_PATH = Path("docs/plans/references/m11-p0-human-review-26-checklist-v1.md")
NOW = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
EXPIRES_AT = datetime(2026, 10, 10, tzinfo=timezone.utc)
REJECTED_OCW = {"digital_answers", "information_worksheet"}
BLOCKED_OPERATIONS = (
    M11Operation.GATE0,
    M11Operation.PROMOTION,
    M11Operation.FORMAL_3K,
    M11Operation.ACQUISITION,
)


def _authority_payload(repo_root: Path) -> dict:
    return json.loads((repo_root / AUTHORITY_PATH).read_text(encoding="utf-8"))


def _digest_assets(repo_root: Path) -> dict[str, list[str]]:
    digest = json.loads((repo_root / DIGEST_PATH).read_text(encoding="utf-8"))
    assets: dict[str, list[str]] = {}
    for item in digest["assets"]:
        assets.setdefault(item["source_id"], []).append(item["asset_id"])
    return assets


def _checklist_contract(repo_root: Path) -> dict:
    text = (repo_root / CHECKLIST_PATH).read_text(encoding="utf-8")
    matches = re.findall(r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL)
    assert len(matches) == 1
    return json.loads(matches[0])


def test_human_review_26_authority_binds_digest_identities_only(repo_root):
    payload = _authority_payload(repo_root)
    digest_assets = _digest_assets(repo_root)
    expected_digest = scope_digest(
        {
            "sources": payload["source_ids"],
            "assets": payload["asset_ids"],
            "version": 1,
        }
    )
    authority = load_execution_authority(
        repo_root / AUTHORITY_PATH,
        operation=M11Operation.HUMAN_REVIEW,
        expected_scope_digest=expected_digest,
        now=NOW,
    )

    assert payload["schema"] == AUTHORITY_SCHEMA
    assert payload["authority_id"] == "m11-human-review-26-20260926"
    assert payload["issued_by"] == "justtodo123"
    assert payload["metadata_only"] is False
    assert payload["publication_authorized"] is False
    assert payload["status"] == "AUTHORIZED"
    assert authority.operation == "human_review"
    assert set(payload["source_ids"]) == set(digest_assets)
    assert "opendsa-main" not in payload["source_ids"]
    assert sum(len(ids) for ids in payload["asset_ids"].values()) == 26
    assert payload["asset_ids"] == digest_assets
    assert REJECTED_OCW <= set(payload["asset_ids"]["mit-ocw-6-004-2017"])
    assert_batch_authorized(authority, digest_assets)
    assert datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00")) == EXPIRES_AT
    assert NOW < EXPIRES_AT


@pytest.mark.parametrize("operation", BLOCKED_OPERATIONS)
def test_human_review_26_authority_does_not_grant_other_operations(repo_root, operation):
    payload = _authority_payload(repo_root)
    with pytest.raises(ExecutionAuthorityError, match="AUTHORITY_OPERATION_MISMATCH"):
        validate_execution_authority(
            payload,
            operation=operation,
            expected_scope_digest=payload["scope_digest"],
            now=NOW,
        )


def test_human_review_26_authority_rejects_opendsa_and_publication(repo_root):
    payload = _authority_payload(repo_root)
    authority = validate_execution_authority(
        payload,
        operation=M11Operation.HUMAN_REVIEW,
        expected_scope_digest=payload["scope_digest"],
        now=NOW,
    )
    with pytest.raises(ExecutionAuthorityError, match="AUTHORITY_BATCH_OUT_OF_SCOPE"):
        assert_batch_authorized(
            authority,
            {"opendsa-main": ["RST/en/Database/ERDTORDDExample.rst"]},
        )
    mutated = dict(payload)
    mutated["publication_authorized"] = True
    with pytest.raises(ExecutionAuthorityError, match="AUTHORITY_PUBLICATION_FORBIDDEN"):
        validate_execution_authority(
            mutated,
            operation=M11Operation.HUMAN_REVIEW,
            expected_scope_digest=payload["scope_digest"],
            now=NOW,
        )


def test_human_review_26_checklist_stays_review_required(repo_root):
    contract = _checklist_contract(repo_root)
    assert contract["result"] == "REVIEW_REQUIRED"
    assert contract["asset_count"] == 26
    assert contract["authority_id"] == "m11-human-review-26-20260926"
    assert contract["includes_rejected_ocw_assets"] is True
    assert contract["opendsa_included"] is False
    assert contract["review_records_written"] is False
    for field in (
        "formal_gate0_executed",
        "formal_3k_executed",
        "candidate_approval_granted",
        "publication_authorized",
        "network_used",
        "source_expansion",
        "lifecycle_mutation",
        "host_paths_included",
        "bodies_included",
    ):
        assert contract[field] is False
    statuses = {row["id"]: row["status"] for row in contract["statuses"]}
    assert statuses["human-review-authority"] == "verified"
    assert statuses["scope-26-digest-assets"] == "verified"
    assert statuses["rejected-ocw-still-in-batch"] == "verified"
    assert statuses["opendsa-excluded"] == "verified"
    assert statuses["asset-license-review"] == "pending"
    assert statuses["revision-review"] == "pending"
    assert statuses["robots-review"] == "pending"
    assert statuses["rfc-notice-ipr-review"] == "pending"
    assert statuses["iana-schema-review"] == "pending"
    assert statuses["content-quality-review"] == "pending"
    assert statuses["review-records"] == "pending"
    assert statuses["formal-gate0"] == "blocked"
    assert statuses["candidate-promotion"] == "blocked"
    assert statuses["publication"] == "blocked"
    assert statuses["source-expansion"] == "blocked"
    assert statuses["network-acquisition"] == "blocked"
    text = (repo_root / CHECKLIST_PATH).read_text(encoding="utf-8")
    assert "ACCEPT_FOR_PROMOTION_REVIEW" not in text
