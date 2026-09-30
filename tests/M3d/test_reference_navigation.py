"""M3d 外部资料导航与用户可见治理状态回归测试。"""

from __future__ import annotations

import json

import pytest

from tests.utils.markdown_links import assert_local_markdown_references

pytestmark = pytest.mark.m3d


def test_reference_readme_links_resolve(repo_root):
    """docs/reference 主索引中的本地文件与锚点都应可解析。"""
    assert_local_markdown_references(
        repo_root / "docs" / "reference" / "README.md",
        repo_root,
    )


def test_network_navigation_does_not_claim_completion_while_candidate(repo_root):
    """canonical Network 记录仍为 candidate 时，总导航不得声称课程已完成。"""
    mapping = json.loads(
        (repo_root / "docs" / "reference" / "document-mapping.json").read_text(
            encoding="utf-8"
        )
    )
    network_records = [
        record
        for record in mapping["records"]
        if record["logical_uri"].startswith("network/")
    ]
    assert network_records
    assert all(record["ingest_status"] == "candidate" for record in network_records)

    knowledge_index = (repo_root / "knowledge" / "README.md").read_text(
        encoding="utf-8"
    )
    network_row = next(
        line for line in knowledge_index.splitlines() if "| network |" in line
    )
    assert "✅" not in network_row
    assert "candidate" in network_row
    assert "不进入默认索引" in network_row
