"""Concurrent SQLite writes."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.M5c.helpers import make_store, sample_review


@pytest.mark.m5c
class TestConcurrentWrites:
    def test_parallel_review_upserts_are_all_visible(self, tmp_path):
        store = make_store(tmp_path)

        def write(index: int) -> None:
            entry = sample_review(file_key=f"knowledge/os/item-{index}.md", count=1)
            store.save_review(entry["file"], entry)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(write, range(12)))

        assert len(store.all()) == 12
