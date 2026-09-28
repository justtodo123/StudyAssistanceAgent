from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.m11_acquisition import (
    resolve_authorized_assets,
    validate_receipt,
    validate_receipt_batch,
)
from app.m11_execution_authority import (
    AUTHORITY_SCHEMA,
    ExecutionAuthorityError,
    M11Operation,
    assert_batch_authorized,
    load_execution_authority,
    scope_digest,
    validate_execution_authority,
)
from app.m11_review import gate0_status, validate_review_history

pytestmark = pytest.mark.m11

AUTHORITY_PATH = Path("data/manifests/m11-p0-human-review-26-authority-v1.json")
DIGEST_PATH = Path("data/manifests/m11-p0-digest-evidence-v1.json")
CHECKLIST_PATH = Path("docs/plans/references/m11-p0-human-review-26-checklist-v1.md")
REVIEW_SLICE_PATH = Path("data/manifests/m11-p0-human-review-rfc-iana-6-v1.json")
OCW_SLICE_PATH = Path("data/manifests/m11-p0-human-review-mit-ocw-20-v1.json")
ACQ_AUTHORITY_PATH = Path("data/manifests/m11-p0-acquisition-26-authority-v1.json")
ACQ_RECEIPTS_PATH = Path("data/manifests/m11-p0-acquisition-26-receipts-v1.json")
ACQ_DEFER_SLICE_PATH = Path("data/manifests/m11-p0-human-review-acq-defer-26-v1.json")
RFC_IANA_ASSETS = {
    "rfc-editor-index": ["rfc9110", "rfc9293", "rfc1034"],
    "iana-registries": [
        "service-names-port-numbers-csv",
        "service-names-port-numbers-xml",
        "service-names-port-numbers-txt",
    ],
}
OCW_ASSETS = {
    "mit-ocw-6-004-2017": [
        "beta_answers",
        "caches_answers",
        "cmos_answers",
        "combinational_answers",
        "compilation_answers",
        "digital_answers",
        "fsm_answers",
        "information_answers",
        "interrupts_answers",
        "isa_answers",
        "beta_worksheet",
        "caches_worksheet",
        "cmos_worksheet",
        "combinational_worksheet",
        "compilation_worksheet",
        "digital_worksheet",
        "fsm_worksheet",
        "information_worksheet",
        "interrupts_worksheet",
        "isa_worksheet",
    ],
}
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


def _review_slice(repo_root: Path) -> dict:
    return json.loads((repo_root / REVIEW_SLICE_PATH).read_text(encoding="utf-8"))


def _ocw_review_slice(repo_root: Path) -> dict:
    return json.loads((repo_root / OCW_SLICE_PATH).read_text(encoding="utf-8"))


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
    assert contract["review_records_written"] is True
    assert contract["rfc_iana_slice_written"] is True
    assert contract["rfc_iana_slice_asset_count"] == 6
    assert contract["rfc_iana_slice_decision"] == "DEFER"
    assert contract["rfc_iana_slice_record"] == str(REVIEW_SLICE_PATH).replace("\\", "/")
    assert contract["mit_ocw_slice_written"] is True
    assert contract["mit_ocw_slice_asset_count"] == 20
    assert contract["mit_ocw_slice_decision"] == "DEFER"
    assert contract["mit_ocw_slice_record"] == str(OCW_SLICE_PATH).replace("\\", "/")
    assert contract["rfc_iana_evidence_review_asset_count"] == 6
    assert contract["rfc_iana_evidence_review_pending_cell_count"] == 48
    assert contract["rfc_iana_evidence_review_decision"] == "DEFER"
    assert contract["rfc_iana_evidence_review_closure_effect"] == "NONE"
    assert contract["rfc_iana_evidence_review_xml_conflict_status"] == "UNRESOLVED"
    assert contract["rfc_iana_evidence_review_txt_parser_state"] == "FAIL_CLOSED"
    assert contract["mit_ocw_evidence_review_asset_count"] == 20
    assert contract["mit_ocw_evidence_review_pending_cell_count"] == 160
    assert contract["mit_ocw_evidence_review_decision"] == "DEFER"
    assert contract["mit_ocw_evidence_review_closure_effect"] == "NONE"
    assert contract["mit_ocw_evidence_review_third_party_rights"] == "UNRESOLVED"
    assert contract["mit_ocw_candidate_asset_count"] == 18
    assert contract["mit_ocw_candidate_chunk_count"] == 93
    assert contract["mit_ocw_candidate_rejected_count"] == 2
    assert contract["mit_ocw_candidate_counts_toward_3k"] is False
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
    assert statuses["rfc-iana-slice"] == "verified"
    assert statuses["mit-ocw-slice"] == "verified"
    assert statuses["mit-ocw-candidate-materialization"] == "verified"
    assert statuses["review-records"] == "verified"
    assert statuses["formal-gate0"] == "blocked"
    assert statuses["candidate-promotion"] == "blocked"
    assert statuses["publication"] == "blocked"
    assert statuses["source-expansion"] == "blocked"
    assert statuses["network-acquisition"] == "blocked"
    text = (repo_root / CHECKLIST_PATH).read_text(encoding="utf-8")
    assert "ACCEPT_FOR_PROMOTION_REVIEW" not in text


def test_rfc_iana_slice_is_deferred_and_does_not_pass_gate0(repo_root):
    payload = _review_slice(repo_root)
    digest = json.loads((repo_root / DIGEST_PATH).read_text(encoding="utf-8"))
    sha_by_asset = {
        (item["source_id"], item["asset_id"]): item["sha256"] for item in digest["assets"]
    }
    records = payload["records"]
    validated = validate_review_history(records)

    assert payload["schema"] == "sa.m11.p0.human-review-slice.v1"
    assert payload["slice_id"] == "rfc-iana-6-20260926"
    assert payload["authority_id"] == "m11-human-review-26-20260926"
    assert payload["authority_record"] == str(AUTHORITY_PATH).replace("\\", "/")
    assert payload["asset_count"] == 6
    assert payload["remaining_in_batch"] == 20
    assert payload["decision"] == "DEFER"
    assert payload["reviewer_id"] == "justtodo123"
    assert payload["source_ids"] == ["rfc-editor-index", "iana-registries"]
    for field in (
        "formal_gate0_executed",
        "candidate_approval_granted",
        "publication_authorized",
        "network_used",
        "source_expansion",
        "lifecycle_mutation",
        "host_paths_included",
        "bodies_included",
    ):
        assert payload[field] is False
    assert len(records) == 6
    assert len(validated) == 6

    expected_pairs = [
        (source_id, asset_id)
        for source_id, asset_ids in RFC_IANA_ASSETS.items()
        for asset_id in asset_ids
    ]
    assert [(item.source_id, item.asset_id) for item in validated] == expected_pairs
    assert {item.decision for item in validated} == {"DEFER"}
    assert {item.document_id for item in validated} == {None}
    assert {item.chunk_ids for item in validated} == {()}
    assert {item.reviewer_id for item in validated} == {"justtodo123"}
    assert {item.reviewer_role for item in validated} == {"owner"}
    assert {item.scope_digest for item in validated} == {payload["scope_digest"]}
    for item in validated:
        assert item.candidate_digest == sha_by_asset[(item.source_id, item.asset_id)]
        assert item.signed_at == "2026-09-26T12:00:00Z"
        assert item.supersedes is None
        assert item.comment.startswith("DEFER:")
        assert "ACCEPT_FOR_PROMOTION_REVIEW" not in item.comment
        assert item.source_id not in {"mit-ocw-6-004-2017", "opendsa-main"}

    authority = load_execution_authority(
        repo_root / AUTHORITY_PATH,
        operation=M11Operation.HUMAN_REVIEW,
        expected_scope_digest=payload["scope_digest"],
        now=NOW,
    )
    batch = {
        source_id: [item.asset_id for item in validated if item.source_id == source_id]
        for source_id in payload["source_ids"]
    }
    assert_batch_authorized(authority, batch)

    status = gate0_status(
        required_assets=expected_pairs,
        reviews=records,
        acquisition_receipts=[],
        authority_present=True,
        scope_digest=payload["scope_digest"],
    )
    assert status["status"] == "BLOCKED"
    assert status["reviewed_asset_count"] == 0
    assert status["candidate_promotion_authorized"] is False
    assert status["publication_authorized"] is False

    raw = (repo_root / REVIEW_SLICE_PATH).read_text(encoding="utf-8")
    assert "ACCEPT_FOR_PROMOTION_REVIEW" not in raw
    assert '"decision": "APPROVED"' not in raw
    assert "D:\\" not in raw
    assert "C:\\" not in raw
    assert "111_Others" not in raw


def test_mit_ocw_slice_is_deferred_and_does_not_pass_gate0(repo_root):
    payload = _ocw_review_slice(repo_root)
    digest = json.loads((repo_root / DIGEST_PATH).read_text(encoding="utf-8"))
    sha_by_asset = {
        (item["source_id"], item["asset_id"]): item["sha256"] for item in digest["assets"]
    }
    records = payload["records"]
    validated = validate_review_history(records)

    assert payload["schema"] == "sa.m11.p0.human-review-slice.v1"
    assert payload["slice_id"] == "mit-ocw-20-20260926"
    assert payload["authority_id"] == "m11-human-review-26-20260926"
    assert payload["authority_record"] == str(AUTHORITY_PATH).replace("\\", "/")
    assert payload["asset_count"] == 20
    assert payload["remaining_in_batch"] == 0
    assert payload["decision"] == "DEFER"
    assert payload["reviewer_id"] == "justtodo123"
    assert payload["source_ids"] == ["mit-ocw-6-004-2017"]
    for field in (
        "formal_gate0_executed",
        "candidate_approval_granted",
        "publication_authorized",
        "network_used",
        "source_expansion",
        "lifecycle_mutation",
        "host_paths_included",
        "bodies_included",
    ):
        assert payload[field] is False
    assert len(records) == 20
    assert len(validated) == 20

    expected_pairs = [
        (source_id, asset_id)
        for source_id, asset_ids in OCW_ASSETS.items()
        for asset_id in asset_ids
    ]
    assert [(item.source_id, item.asset_id) for item in validated] == expected_pairs
    assert {item.decision for item in validated} == {"DEFER"}
    assert {item.document_id for item in validated} == {None}
    assert {item.chunk_ids for item in validated} == {()}
    assert {item.reviewer_id for item in validated} == {"justtodo123"}
    assert {item.reviewer_role for item in validated} == {"owner"}
    assert {item.scope_digest for item in validated} == {payload["scope_digest"]}
    assert REJECTED_OCW <= {item.asset_id for item in validated}
    for item in validated:
        assert item.candidate_digest == sha_by_asset[(item.source_id, item.asset_id)]
        assert item.signed_at == "2026-09-26T12:00:00Z"
        assert item.supersedes is None
        assert item.comment.startswith("DEFER:")
        assert "ACCEPT_FOR_PROMOTION_REVIEW" not in item.comment
        assert item.source_id == "mit-ocw-6-004-2017"

    authority = load_execution_authority(
        repo_root / AUTHORITY_PATH,
        operation=M11Operation.HUMAN_REVIEW,
        expected_scope_digest=payload["scope_digest"],
        now=NOW,
    )
    batch = {
        source_id: [item.asset_id for item in validated if item.source_id == source_id]
        for source_id in payload["source_ids"]
    }
    assert_batch_authorized(authority, batch)

    status = gate0_status(
        required_assets=expected_pairs,
        reviews=records,
        acquisition_receipts=[],
        authority_present=True,
        scope_digest=payload["scope_digest"],
    )
    assert status["status"] == "BLOCKED"
    assert status["reviewed_asset_count"] == 0
    assert status["candidate_promotion_authorized"] is False
    assert status["publication_authorized"] is False

    rfc_records = _review_slice(repo_root)["records"]
    combined = rfc_records + records
    assert len(combined) == 26
    validate_review_history(combined)
    combined_pairs = [
        (source_id, asset_id)
        for source_id, asset_ids in {**RFC_IANA_ASSETS, **OCW_ASSETS}.items()
        for asset_id in asset_ids
    ]
    combined_status = gate0_status(
        required_assets=combined_pairs,
        reviews=combined,
        acquisition_receipts=[],
        authority_present=True,
        scope_digest=payload["scope_digest"],
    )
    assert combined_status["status"] == "BLOCKED"
    assert combined_status["reviewed_asset_count"] == 0
    assert combined_status["candidate_promotion_authorized"] is False
    assert combined_status["publication_authorized"] is False

    raw = (repo_root / OCW_SLICE_PATH).read_text(encoding="utf-8")
    assert "ACCEPT_FOR_PROMOTION_REVIEW" not in raw
    assert '"decision": "APPROVED"' not in raw
    assert "D:\\\\" not in raw
    assert "C:\\\\" not in raw
    assert "111_Others" not in raw


def test_acquired_receipts_and_superseding_re_review_stay_deferred(repo_root):
    acq_payload = json.loads((repo_root / ACQ_AUTHORITY_PATH).read_text(encoding="utf-8"))
    acquisition = load_execution_authority(
        repo_root / ACQ_AUTHORITY_PATH,
        operation=M11Operation.ACQUISITION,
        expected_scope_digest=acq_payload["scope_digest"],
        now=datetime(2026, 9, 26, 14, tzinfo=timezone.utc),
    )
    assets = resolve_authorized_assets(repo_root, acquisition)
    wrapper = json.loads((repo_root / ACQ_RECEIPTS_PATH).read_text(encoding="utf-8"))
    receipts = [validate_receipt(item) for item in wrapper["receipts"]]
    assert len(validate_receipt_batch(receipts, assets, authority=acquisition)) == 26

    payload = json.loads((repo_root / ACQ_DEFER_SLICE_PATH).read_text(encoding="utf-8"))
    records = payload["records"]
    validated = validate_review_history(records)
    assert payload["decision"] == "DEFER"
    assert payload["network_used"] is False
    assert len(validated) == 26
    assert {item.decision for item in validated} == {"DEFER"}
    historical = (
        _review_slice(repo_root)["records"] + _ocw_review_slice(repo_root)["records"]
    )
    historical_by_asset = {
        (item["source_id"], item["asset_id"]): item["review_id"]
        for item in historical
    }
    assert all(
        item.supersedes == historical_by_asset[(item.source_id, item.asset_id)]
        for item in validated
    )
    assert all(item.document_id is None and item.chunk_ids == () for item in validated)

    validate_review_history(historical + records)
    required = [
        (source_id, asset_id)
        for source_id, asset_ids in {**RFC_IANA_ASSETS, **OCW_ASSETS}.items()
        for asset_id in asset_ids
    ]
    status = gate0_status(
        required_assets=required,
        reviews=historical + records,
        acquisition_receipts=[item.as_dict() for item in receipts],
        authority_present=True,
        scope_digest=payload["scope_digest"],
    )
    assert status["status"] == "BLOCKED"
    assert status["reviewed_asset_count"] == 0
    assert status["receipt_asset_count"] == 26
    assert status["candidate_promotion_authorized"] is False
    assert status["publication_authorized"] is False
