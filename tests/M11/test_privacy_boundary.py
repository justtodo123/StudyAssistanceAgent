from __future__ import annotations

import pytest

pytestmark = pytest.mark.m11


def test_m11_data_fixture_tree_is_non_empty_and_separate(m11_data_tree):
    assert m11_data_tree
    assert set(m11_data_tree) == {
        "raw", "normalized", "candidates", "approved",
        "rejected", "reports", "snapshots",
    }
    assert len({path.resolve() for path in m11_data_tree.values()}) == len(m11_data_tree)
