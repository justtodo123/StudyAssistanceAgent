from __future__ import annotations

import yaml
import pytest

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
