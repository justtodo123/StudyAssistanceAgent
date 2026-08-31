"""现有 Network / Interview 语料的文档级治理契约。"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from app.markdown_parser import parse_frontmatter
from app.protocols import logical_document_id, normalize_logical_uri
from app.source_policy import is_indexable_frontmatter


MAPPING_PATH = "docs/reference/document-mapping.json"
GOVERNED_DIRECTORIES = ("network", "interview")
REQUIRED_FIELDS = {
    "source_id",
    "logical_uri",
    "document_id",
    "project_authored",
    "origin_kind",
    "source_type",
    "format",
    "review_status",
    "ingest_status",
    "registration_method",
    "license_id",
    "license_status",
    "provenance_status",
    "evidence",
}
APPROVED_LICENSE_STATUSES = {"approved"}
APPROVED_REVIEW_STATUSES = {"approved"}
PROVENANCE_VALUES = {
    "project_authored_ai_assisted",
    "web_derived_ai_assisted",
}
SOURCE_TYPES = {"human_markdown"}
FORMATS = {"markdown"}
REVIEW_STATUSES = {"approved", "review"}
INGEST_STATUSES = {"approved", "candidate", "rejected"}
REGISTRATION_METHODS = {"legacy_course_index", "repository_commit"}
LICENSE_STATUSES = {"approved", "unresolved"}
EXPECTED_MAPPING_SHA256 = (
    "d1bb072da917154a95705c7386b432aeba16af46c08a4fb76cd7d5c419a96fbe"
)
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)^[a-z]:[/\\]")
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _load_mapping(repo_root: Path) -> dict:
    return json.loads((repo_root / MAPPING_PATH).read_text(encoding="utf-8"))


def _governed_documents(repo_root: Path) -> list[str]:
    documents: list[str] = []
    for directory in GOVERNED_DIRECTORIES:
        for path in (repo_root / "knowledge" / directory).rglob("*.md"):
            if path.name != "README.md":
                documents.append(path.relative_to(repo_root).as_posix())
    return sorted(documents)


def _parse_frontmatter(path: Path) -> dict[str, str]:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    assert match, f"{path}: missing frontmatter"
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def _has_host_path(value: object) -> bool:
    if isinstance(value, str):
        return value.startswith(("/", "\\\\")) or bool(WINDOWS_ABSOLUTE_PATH.match(value))
    if isinstance(value, list):
        return any(_has_host_path(item) for item in value)
    if isinstance(value, dict):
        return any(_has_host_path(item) for item in value.values())
    return False


class TestDocumentGovernanceMapping:
    def test_mapping_is_one_to_one_with_governed_corpus(self, repo_root):
        mapping = _load_mapping(repo_root)
        records = mapping["records"]
        paths = [record["document_path"] for record in records]

        assert mapping["schema_version"] == "sa.document-governance-mapping.v1"
        assert sorted(paths) == _governed_documents(repo_root)
        assert len(paths) == len(set(paths)) == 82
        assert sum(path.startswith("knowledge/network/") for path in paths) == 31
        assert sum(path.startswith("knowledge/interview/") for path in paths) == 51

    def test_mapping_digest_matches_p0_report(self, repo_root):
        mapping_bytes = (repo_root / MAPPING_PATH).read_bytes()
        assert hashlib.sha256(mapping_bytes).hexdigest() == EXPECTED_MAPPING_SHA256

    def test_identity_and_governance_fields_are_valid(self, repo_root):
        for record in _load_mapping(repo_root)["records"]:
            assert REQUIRED_FIELDS <= record.keys(), record["document_path"]
            logical_uri = normalize_logical_uri(record["logical_uri"])
            assert record["document_path"] == f"knowledge/{logical_uri}"
            assert record["document_id"] == logical_document_id(
                record["source_id"], logical_uri
            )
            assert record["origin_kind"] in PROVENANCE_VALUES
            assert record["source_type"] in SOURCE_TYPES
            assert record["format"] in FORMATS
            assert record["review_status"] in REVIEW_STATUSES
            assert record["ingest_status"] in INGEST_STATUSES
            assert record["registration_method"] in REGISTRATION_METHODS
            assert record["license_status"] in LICENSE_STATUSES
            assert not _has_host_path(record), record["document_path"]

    def test_publication_policy_is_fail_closed(self, repo_root):
        for record in _load_mapping(repo_root)["records"]:
            publishable = record["ingest_status"] == "approved"
            if not publishable:
                continue
            assert record["review_status"] in APPROVED_REVIEW_STATUSES
            assert record["license_status"] in APPROVED_LICENSE_STATUSES
            assert bool(record.get("canonical_url")) ^ bool(record["project_authored"])
            if record["project_authored"]:
                assert record["publisher"]
                assert record["author"]

    def test_network_without_original_urls_remains_candidate(self, repo_root):
        records = [
            record
            for record in _load_mapping(repo_root)["records"]
            if record["logical_uri"].startswith("network/")
        ]
        assert len(records) == 31
        for record in records:
            assert record["canonical_url"] is None
            assert record["project_authored"] is False
            assert record["origin_kind"] == "web_derived_ai_assisted"
            assert record["review_status"] == "review"
            assert record["ingest_status"] == "candidate"
            assert record["license_id"] is None
            assert record["license_status"] == "unresolved"
            assert record["provenance_status"] == "unresolved"

    def test_frontmatter_matches_mapping(self, repo_root):
        for record in _load_mapping(repo_root)["records"]:
            metadata = _parse_frontmatter(repo_root / record["document_path"])
            assert metadata["source_id"] == record["source_id"]
            assert metadata["logical_uri"] == record["logical_uri"]
            assert metadata["document_id"] == record["document_id"]
            assert metadata["provenance"] == record["origin_kind"]
            assert metadata["source_type"] == record["source_type"]
            assert metadata["format"] == record["format"]
            assert metadata["review_status"] == record["review_status"]
            assert metadata["ingest_status"] == record["ingest_status"]
            assert metadata["registration_method"] == record["registration_method"]
            assert metadata["license_id"] == str(record["license_id"] or "unknown")
            assert metadata["license_status"] == record["license_status"]
            expected_project_authored = str(record["project_authored"]).lower()
            assert metadata["project_authored"] == expected_project_authored

    def test_runtime_policy_keeps_candidates_out_of_index(self, repo_root):
        for record in _load_mapping(repo_root)["records"]:
            path = repo_root / record["document_path"]
            metadata = parse_frontmatter(path.read_text(encoding="utf-8"))
            assert is_indexable_frontmatter(metadata) is (
                record["ingest_status"] == "approved"
            ), record["document_path"]

    def test_inventory_classification_does_not_grant_admission(self, repo_root):
        inventory_source = (repo_root / "tools" / "source_inventory.py").read_text(
            encoding="utf-8"
        )
        assert re.search(
            r'"study_document",\s*extraction,\s*flags,\s*"candidate"',
            inventory_source,
            re.DOTALL,
        )
        for record in _load_mapping(repo_root)["records"]:
            assert record["source_type"] != "study_document"
            assert record["registration_method"] != "study_document"
