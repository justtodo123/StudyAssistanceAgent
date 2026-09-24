from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11


_DATA_LAYERS = {
    "/data/raw/",
    "/data/normalized/",
    "/data/candidates/",
    "/data/approved/",
    "/data/rejected/",
    "/data/reports/",
    "/data/snapshots/",
}


def test_m11_data_fixture_tree_is_non_empty_and_separate(m11_data_tree):
    assert m11_data_tree
    assert set(m11_data_tree) == {
        "raw", "normalized", "candidates", "approved",
        "rejected", "reports", "snapshots",
    }
    assert len({path.resolve() for path in m11_data_tree.values()}) == len(m11_data_tree)


def test_m11_gitignore_excludes_every_runtime_data_layer(repo_root: Path):
    ignore_rules = {
        line.strip()
        for line in (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("/data/")
    }

    assert _DATA_LAYERS
    assert _DATA_LAYERS <= ignore_rules


def test_m11_data_readme_limits_tracked_content(repo_root: Path):
    data_readme = repo_root / "data" / "README.md"
    assert data_readme.is_file()

    content = data_readme.read_text(encoding="utf-8")
    assert "data/README.md" in content
    assert "data/manifests/" in content


def test_m11_tracked_data_contains_only_readme_and_manifests(repo_root: Path):
    completed = subprocess.run(
        ["git", "ls-files", "--", "data/"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    tracked = {
        line.strip().replace("\\", "/")
        for line in completed.stdout.splitlines()
        if line.strip()
    }

    assert tracked
    assert "data/README.md" in tracked
    assert all(
        path == "data/README.md" or path.startswith("data/manifests/")
        for path in tracked
    )
    assert not any(path.lower().endswith((".pdf", ".zip")) for path in tracked)
