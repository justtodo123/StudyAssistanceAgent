"""Hermetic fixtures for M11 gate tests."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.m11


@pytest.fixture
def m11_data_tree(tmp_path: Path) -> dict[str, Path]:
    tree = {name: tmp_path / name for name in (
        "raw", "normalized", "candidates", "approved",
        "rejected", "reports", "snapshots",
    )}
    for path in tree.values():
        path.mkdir()
    return tree
