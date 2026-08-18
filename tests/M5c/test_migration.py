"""JSON review-history migration tests."""

from __future__ import annotations

import pytest

from tests.M5c.helpers import make_store, sample_review, write_json_history


@pytest.mark.m5c
class TestReviewHistoryMigration:
    def test_imports_json_when_sqlite_empty(self, tmp_path):
        json_path = tmp_path / "review_history.json"
        entry = sample_review()
        write_json_history(json_path, {entry["file"]: entry})
        store = make_store(tmp_path, json_history=json_path)
        loaded = store.get_review(entry["file"])
        assert loaded is not None
        assert loaded["review_count"] == 2
        assert not json_path.exists()
        assert json_path.with_name("review_history.json.migrated").exists()

    def test_does_not_overwrite_existing_sqlite_rows(self, tmp_path):
        store = make_store(tmp_path)
        existing = sample_review(count=5)
        store.save_review(existing["file"], existing)
        json_path = tmp_path / "review_history.json"
        write_json_history(json_path, {existing["file"]: sample_review(count=1)})
        imported = store.migrate_review_history(json_path)
        assert imported == 0
        assert store.get_review(existing["file"])["review_count"] == 5
        assert json_path.exists()

    def test_corrupt_json_is_ignored(self, tmp_path):
        json_path = tmp_path / "review_history.json"
        json_path.write_text("{not-json", encoding="utf-8")
        store = make_store(tmp_path, json_history=json_path)
        assert store.all() == {}
        assert json_path.exists()
