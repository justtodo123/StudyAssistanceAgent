from __future__ import annotations

import json
import yaml
import pytest

from tools.validate_m11_p0_metadata_gate0 import (
    ChecklistValidationError,
    validate_checklist,
)
from tools.validate_m11_p0_evidence_gaps import (
    EvidenceGapValidationError,
    validate_evidence_gaps,
)

pytestmark = pytest.mark.m11

APPROVED_P0 = {
    "knowledge-pack", "project-authored-evals", "mit-ocw-6-004-2017",
    "opendsa-main", "rfc-editor-index", "iana-registries",
}
FORBIDDEN = {"network-candidates", "stackexchange-dump", "linux-kernel-docs",
             "m8-backend-assets", "m12-cloud-assets"}


def _inventory(repo_root):
    path = repo_root / "data/manifests/sources/m11-p0-inventory.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_inventory_is_non_empty_and_exactly_the_frozen_p0_set(repo_root):
    inventory = _inventory(repo_root)
    sources = inventory["sources"]
    assert sources
    assert {item["source_id"] for item in sources} == APPROVED_P0
    assert set(inventory["excluded_sources"]) == FORBIDDEN
    assert APPROVED_P0.isdisjoint(FORBIDDEN)


def test_external_sources_fail_closed_until_gate_zero_review(repo_root):
    inventory = _inventory(repo_root)
    external = [item for item in inventory["sources"] if not item["project_authored"]]
    assert external
    assert all(item["official_url"].startswith("https://") for item in external)
    assert all(item["license_status"] == "review_required" for item in external)
    assert all(item.get("revision") for item in external)
    assert all(item.get("license_url", "").startswith("https://") for item in external)
    assert all(item.get("license_basis") for item in external)
    assert all(item.get("allowed_asset_policy") or item.get("approved_asset_policy") for item in external)
    assert all(item.get("candidate_asset_policy") or item.get("candidate_assets") for item in external)
    assert all(item.get("portable_digest_evidence") == "data/manifests/m11-p0-digest-evidence-v1.json" for item in external)
    assert inventory["network_execution_authorized"] is False
    assert inventory["publication_authorized"] is False


def test_candidate_asset_manifest_is_metadata_only_and_matches_inventory(repo_root):
    manifest_path = repo_root / "data/manifests/sources/m11-p0-candidate-assets-v1.json"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "CANDIDATE_PIPELINE_AUTHORIZED"
    assert manifest["pipeline_approval"]["approved_by"] == "justtodo123"
    assert manifest["pipeline_approval"]["approval_reference"] == "User instruction: 批准以下范围进入 candidate pipeline"
    assert manifest["review_policy"]["approved_assets"] == []
    assert manifest["review_policy"]["candidate_pipeline_authorized"] is True
    assert manifest["review_policy"]["network_execution_authorized"] is False
    assert manifest["review_policy"]["publication_authorized"] is False
    assert manifest["review_policy"]["metadata_only"] is True
    sources = manifest["sources"]
    assert set(sources) == {"mit-ocw-6-004-2017", "opendsa-main", "rfc-editor-index", "iana-registries"}
    from app import m11_candidate_pipeline
    assert m11_candidate_pipeline._REQUIRED_SOURCES == set(sources)
    mit_assets = sources["mit-ocw-6-004-2017"]["assets"]
    assert len(mit_assets) == 20
    assert all(asset["url"].startswith("https://ocw.mit.edu/") for asset in mit_assets)
    assert all(not asset["approved"] for asset in mit_assets)
    assert all(asset["license_review_status"] == "pending" for asset in mit_assets)
    assert all(asset["revision_status"] == "pending" for asset in mit_assets)
    assert all(asset["robots_review_status"] == "pending" for asset in mit_assets)
    assert sources["opendsa-main"]["candidate_roots"] == ["RST/en/"]
    assert sources["opendsa-main"]["path_review"]["approved"] is False
    rfcs = sources["rfc-editor-index"]["candidate_rfcs"]
    assert rfcs
    assert all(asset["status"] in {"Internet Standard", "Internet Standards Track document"} for asset in rfcs)
    assert all(asset["notice_review_status"] == "pending" for asset in rfcs)
    assert all(asset["ipr_review_status"] == "pending" for asset in rfcs)
    assert all(not asset["approved"] for asset in rfcs)
    registries = sources["iana-registries"]["candidate_registries"]
    assert registries
    assert registries[0]["license_review_status"] == "scope-confirmed"
    assert registries[0]["revision_digest"] == "captured-in-m11-p0-digest-evidence-v1"
    assert registries[0]["revision_status"] == "digest-captured"
    assert registries[0]["robots_review_status"] == "pending"
    assert registries[0]["schema_review_status"] == "pending"
    assert registries[0]["approved"] is False


def test_asset_review_manifest_matches_frozen_p0_scope_and_stays_fail_closed(repo_root):
    review_path = repo_root / "data/manifests/m11-p0-asset-review-v1.json"
    candidate_path = repo_root / "data/manifests/sources/m11-p0-candidate-assets-v1.json"
    digest_path = repo_root / "data/manifests/m11-p0-digest-evidence-v1.json"
    opendsa_path = repo_root / "data/manifests/sources/m11-opendsa-rst-paths-v1.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    digest = json.loads(digest_path.read_text(encoding="utf-8"))
    opendsa = json.loads(opendsa_path.read_text(encoding="utf-8"))

    expected = []
    for source_id, source in candidate["sources"].items():
        if source_id == "opendsa-main":
            expected.extend((source_id, item["path"]) for item in opendsa["files"])
        elif source_id == "mit-ocw-6-004-2017":
            expected.extend((source_id, item["asset_id"]) for item in source["assets"])
        elif source_id == "rfc-editor-index":
            expected.extend((source_id, f"rfc{item['rfc']}") for item in source["candidate_rfcs"])
        elif source_id == "iana-registries":
            expected.extend(
                (source_id, f"service-names-port-numbers-{suffix}")
                for suffix in ("csv", "xml", "txt")
            )

    records = review["records"]
    actual = [(item["source_id"], item["asset_id"]) for item in records]
    assert len(records) == len(expected) == review["asset_count"] == 887
    assert len(set(actual)) == len(actual)
    assert set(actual) == set(expected)
    assert review["candidate_count"] == 884
    assert review["rejected_count"] == 3
    assert review["candidate_count"] + review["rejected_count"] == review["asset_count"]
    assert review["review_policy"]["approved_assets"] == []
    assert review["review_policy"]["approved_asset_count"] == 0
    assert review["review_policy"]["approved_document_count"] == 0
    assert review["review_policy"]["approved_chunk_count"] == 0
    assert review["review_policy"]["formal_run_authorized"] is False
    assert review["review_policy"]["publication_authorized"] is False
    assert all(item["approved"] is False for item in records)
    assert all(item["normalization_status"] in {"CANDIDATE", "REJECTED"} for item in records)
    assert review["host_paths_included"] is False
    assert review["bodies_included"] is False

    rejected = [item for item in records if item["normalization_status"] == "REJECTED"]
    candidates = [item for item in records if item["normalization_status"] == "CANDIDATE"]
    assert len(rejected) == review["rejected_count"]
    assert len(candidates) == review["candidate_count"]
    assert {
        (item["source_id"], item["asset_id"], item["rejection_reason"])
        for item in rejected
    } == {
        (
            "mit-ocw-6-004-2017",
            "digital_answers",
            "SOURCE_PARSE_FAILED",
        ),
        (
            "mit-ocw-6-004-2017",
            "information_worksheet",
            "INVALID_CANDIDATE_INPUT",
        ),
        (
            "opendsa-main",
            "RST/en/Database/ERDTORDDExample.rst",
            "SOURCE_PARSE_FAILED",
        ),
    }
    assert all(item.get("rejection_reason") in review["rejection_reasons"] for item in rejected)
    assert all(item["rejection_reason"] for item in rejected)
    assert all("rejection_reason" not in item for item in candidates)

    body_fields = {"body", "content", "text", "raw_content", "normalized_content"}
    private_fields = {
        "credential",
        "credentials",
        "password",
        "token",
        "learning_state",
        "private_learning_state",
        "raw_path",
        "normalized_path",
        "candidate_path",
        "rejected_path",
    }
    for item in rejected:
        assert body_fields.isdisjoint(item)
        assert private_fields.isdisjoint(item)
        assert item["source_id"] and item["asset_id"]
        assert item["approved"] is False
        assert item["locator"].startswith(("https://", "git://"))

    digest_ids = {item["asset_id"] for item in digest["assets"]}
    direct_ids = {
        item["asset_id"]
        for item in records
        if item["source_id"] != "opendsa-main"
    }
    assert direct_ids == digest_ids



def _normalization_report_path(repo_root):
    return repo_root / "data/reports/m11-p0-candidate-normalization-report.json"


def _require_normalization_report(repo_root):
    path = _normalization_report_path(repo_root)
    if not path.is_file():
        pytest.skip("gitignored normalization report is absent")
    return path


def test_candidate_report_reconciles_with_review_manifest(repo_root):
    review_path = repo_root / "data/manifests/m11-p0-asset-review-v1.json"
    report_path = _require_normalization_report(repo_root)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))

    for field in (
        "asset_count",
        "candidate_count",
        "rejected_count",
        "rejection_reasons",
        "host_paths_included",
        "bodies_included",
    ):
        assert report[field] == review[field]
    assert report["status"] == "CANDIDATE_ONLY"
    assert report["approved_count"] == 0
    assert report["published_count"] == 0
    assert report["document_count"] == review["candidate_count"]
    assert report["approved_asset_count"] == 0
    assert report["approved_document_count"] == 0
    assert report["approved_chunk_count"] == 0
    assert report["publication_authorized"] is False
    assert review["review_policy"]["formal_run_authorized"] is False
    assert review["review_policy"]["publication_authorized"] is False


def test_portable_digest_evidence_is_complete_but_does_not_approve_assets(repo_root):
    path = repo_root / "data/manifests/m11-p0-digest-evidence-v1.json"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assets = data["assets"]
    assert data["status"] == "DIGESTS_CAPTURED_CANDIDATE_PIPELINE_AUTHORIZED"
    assert data["pipeline_approval"]["approved_by"] == "justtodo123"
    assert data["asset_count"] == 26
    assert len(assets) == 26
    assert all(len(item["sha256"]) == 64 for item in assets)
    assert all(set(item["sha256"]) <= set("0123456789abcdef") for item in assets)
    identities = {(item["source_id"], item["asset_id"]) for item in assets}
    assert len(identities) == len(assets)

    candidate_path = repo_root / "data/manifests/sources/m11-p0-candidate-assets-v1.json"
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    sources = candidate["sources"]
    expected = {
        ("mit-ocw-6-004-2017", item["asset_id"])
        for item in sources["mit-ocw-6-004-2017"]["assets"]
    }
    expected.update(
        ("rfc-editor-index", f"rfc{item['rfc']}")
        for item in sources["rfc-editor-index"]["candidate_rfcs"]
    )
    registry = sources["iana-registries"]["candidate_registries"][0]
    expected.update(
        ("iana-registries", f"{registry['name']}-{suffix}")
        for suffix in ("csv", "xml", "txt")
    )
    assert identities == expected
    assert all(item["temporary_body_deleted"] is True for item in assets)
    assert all(item["format_valid"] is True for item in assets)
    assert data["approved_assets"] == []
    assert data["publication_authorized"] is False
    assert {item["policy"] for item in data["robots"]} == {
        "allow-all", "candidate-paths-not-disallowed"
    }


def test_opendsa_path_manifest_is_pinned_and_not_approved(repo_root):
    path = repo_root / "data/manifests/sources/m11-opendsa-rst-paths-v1.json"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["status"] == "CANDIDATE_PIPELINE_AUTHORIZED"
    assert data["pipeline_approval"]["approved_by"] == "justtodo123"
    assert data["revision"] == "4c183682bbd84b951f2324a36399a3a077250bb9"
    assert data["candidate_root"] == "RST/en/"
    assert data["file_count"] == 861
    assert len(data["files"]) == 861
    candidate_assets_path = (
        repo_root / "data/manifests/sources/m11-p0-candidate-assets-v1.json"
    )
    candidate_assets = yaml.safe_load(
        candidate_assets_path.read_text(encoding="utf-8")
    )
    opendsa = candidate_assets["sources"]["opendsa-main"]
    path_scope = opendsa["candidate_path_scope"]
    assert opendsa["tree_counts"]["rst_en_blobs"] == 865
    assert path_scope["manifest"] == path.relative_to(repo_root).as_posix()
    assert path_scope["explicit_path_count"] == data["file_count"]
    assert path_scope["broader_tree_count_is_informational"] is True
    assert opendsa["tree_counts"]["rst_en_blobs"] > path_scope["explicit_path_count"]
    assert all(item["path"].startswith("RST/en/") for item in data["files"])
    assert all(item["path"].endswith(".rst") for item in data["files"])
    assert all(len(item["blob_sha"]) == 40 for item in data["files"])
    assert all(set(item["blob_sha"]) <= set("0123456789abcdef") for item in data["files"])
    assert len(data["revision"]) == 40
    assert set(data["revision"]) <= set("0123456789abcdef")
    assert all(isinstance(item["size"], int) and item["size"] >= 0 for item in data["files"])
    paths = [item["path"] for item in data["files"]]
    assert len(set(paths)) == len(paths)
    assert sum(item["size"] for item in data["files"]) == data["total_bytes"]
    assert data["approved"] is False


def test_frozen_3k_layer_quotas_are_present(repo_root):
    inventory = _inventory(repo_root)
    constraints = inventory["constraints"]
    assert constraints["authoritative_combined_max_share"] == 0.25
    assert constraints["teaching_min_share"] == 0.50
    assert constraints["evaluation_max_share"] == 0.15
    assert constraints["non_allowlisted_chunk_count"] == 0
    assert constraints["real_download_requires_confirmation"] is True



def _checklist_paths(repo_root):
    return (
        repo_root / "docs/plans/references/m11-p0-metadata-only-gate0-checklist-v1.md",
        repo_root / "data/manifests/m11-p0-asset-review-v1.json",
        _require_normalization_report(repo_root),
    )


def _checklist_contract(repo_root):
    checklist_path, _, _ = _checklist_paths(repo_root)
    text = checklist_path.read_text(encoding="utf-8")
    start = text.index("```json\n") + len("```json\n")
    end = text.index("\n```", start)
    return json.loads(text[start:end])


def _write_checklist_contract(repo_root, tmp_path, mutate):
    checklist_path, review_path, report_path = _checklist_paths(repo_root)
    contract = _checklist_contract(repo_root)
    mutate(contract)
    checklist_copy = tmp_path / "checklist.md"
    checklist_copy.write_text(
        "# test checklist\n\n```json\n"
        + json.dumps(contract, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    return checklist_copy, review_path, report_path


def test_metadata_only_gate0_checklist_validates(repo_root):
    validate_checklist(*_checklist_paths(repo_root))


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda contract: contract.pop("counts"), "contract fields differ"),
        (lambda contract: contract.update({"unexpected": True}), "contract fields differ"),
        (
            lambda contract: contract["statuses"][0].update({"status": "approved"}),
            "unsupported checklist status",
        ),
        (
            lambda contract: contract["counts"].update({"candidate_count": 883}),
            "frozen count drift",
        ),
        (
            lambda contract: contract.update({"formal_3k_executed": True}),
            "unsafe true value",
        ),
        (
            lambda contract: contract.update({"candidate_approval_granted": True}),
            "unsafe true value",
        ),
        (
            lambda contract: contract.update({"publication_authorized": True}),
            "unsafe true value",
        ),
        (
            lambda contract: contract.update({"source_expansion": True}),
            "unsafe true value",
        ),
        (
            lambda contract: contract.update({"network_used": True}),
            "unsafe true value",
        ),
        (
            lambda contract: contract.update({"lifecycle_mutation": True}),
            "unsafe true value",
        ),
        (
            lambda contract: contract.update({"body": "source body"}),
            "contract fields differ",
        ),
    ],
)
def test_metadata_only_gate0_checklist_rejects_unsafe_contract(
    repo_root, tmp_path, mutate, expected
):
    paths = _write_checklist_contract(repo_root, tmp_path, mutate)
    with pytest.raises(ChecklistValidationError, match=expected):
        validate_checklist(*paths)


def test_metadata_only_gate0_checklist_rejects_privacy_fields_in_status_rows(
    repo_root, tmp_path
):
    def mutate(contract):
        contract["statuses"][0]["body"] = "source body"

    paths = _write_checklist_contract(repo_root, tmp_path, mutate)
    with pytest.raises(ChecklistValidationError, match="each checklist status row"):
        validate_checklist(*paths)


def test_metadata_only_gate0_checklist_rejects_manifest_privacy_field(
    repo_root, tmp_path
):
    checklist_path, review_path, report_path = _checklist_paths(repo_root)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["records"][0]["content"] = "source body"
    review_copy = tmp_path / "review.json"
    review_copy.write_text(json.dumps(review), encoding="utf-8")

    with pytest.raises(ChecklistValidationError, match="privacy-bearing fields"):
        validate_checklist(checklist_path, review_copy, report_path)


def test_metadata_only_gate0_checklist_rejects_report_count_drift(repo_root, tmp_path):
    checklist_path, review_path, report_path = _checklist_paths(repo_root)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["candidate_count"] = 883
    report_copy = tmp_path / "report.json"
    report_copy.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ChecklistValidationError, match="report/review mismatch"):
        validate_checklist(checklist_path, review_path, report_copy)



def _evidence_gap_paths(repo_root):
    return (
        repo_root / "docs/plans/references/m11-p0-evidence-gap-checklist-v1.md",
        repo_root / "data/manifests/sources/m11-p0-candidate-assets-v1.json",
        repo_root / "data/manifests/m11-p0-asset-review-v1.json",
        _require_normalization_report(repo_root),
    )


def _write_evidence_gap_contract(repo_root, tmp_path, mutate):
    checklist_path, candidate_path, review_path, report_path = _evidence_gap_paths(repo_root)
    text = checklist_path.read_text(encoding="utf-8")
    start = text.index("```json\n") + len("```json\n")
    end = text.index("\n```", start)
    contract = json.loads(text[start:end])
    mutate(contract)
    checklist_copy = tmp_path / "evidence-gaps.md"
    checklist_copy.write_text(
        "# test checklist\n\n```json\n"
        + json.dumps(contract, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    return checklist_copy, candidate_path, review_path, report_path


def test_evidence_gap_checklist_validates(repo_root):
    validate_evidence_gaps(*_evidence_gap_paths(repo_root))


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda contract: contract.pop("counts"), "contract fields differ"),
        (lambda contract: contract["gap_categories"][0].update({"status": "verified"}), "unsupported evidence-gap status"),
        (lambda contract: contract["counts"].update({"candidate_count": 883}), "frozen count drift"),
        (lambda contract: contract.update({"candidate_approval_granted": True}), "unsafe true value"),
        (lambda contract: contract.update({"owner_decisions_filled": True}), "unsafe true value"),
        (lambda contract: contract["source_gaps"][0]["gaps"].update({"schema": 2}), "source-category gap drift"),
        (lambda contract: contract["gap_categories"][0].update({"body": "source body"}), "privacy-bearing fields in checklist"),
    ],
)
def test_evidence_gap_checklist_rejects_unsafe_drift(repo_root, tmp_path, mutate, expected):
    paths = _write_evidence_gap_contract(repo_root, tmp_path, mutate)
    with pytest.raises(EvidenceGapValidationError, match=expected):
        validate_evidence_gaps(*paths)
