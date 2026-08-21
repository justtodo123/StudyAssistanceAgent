"""M6 crawler P0 — candidates must not enter default knowledge."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.source_policy import (
    SourceIngestDenied,
    assert_crawler_output_allowed,
    default_crawler_output_dir,
    is_indexable_frontmatter,
    is_indexable_relative_path,
)
from tools.crawler.converter import ArticleMeta, to_knowledge_markdown
from tools.crawler.pipeline import run_pipeline

pytestmark = pytest.mark.m6_crawler


class TestCandidateFrontmatter:
    def test_converter_marks_web_candidate(self, sample_text: str) -> None:
        md = to_knowledge_markdown(
            sample_text,
            ArticleMeta(title="TCP三次握手", course="network", tags=["TCP"]),
        )
        assert "source_type: web_candidate" in md
        assert "ingest_status: candidate" in md


class TestCrawlerOutputGate:
    def test_rejects_default_course_dir(self) -> None:
        from app import config

        with pytest.raises(SourceIngestDenied):
            assert_crawler_output_allowed(config.KNOWLEDGE_ROOT / "os")

    def test_allows_cache_dir_and_inbox(self) -> None:
        from app import config

        assert_crawler_output_allowed(default_crawler_output_dir("network"))
        assert_crawler_output_allowed(config.KNOWLEDGE_ROOT / "_inbox")
        assert_crawler_output_allowed(
            config.KNOWLEDGE_ROOT / "os",
            allow_knowledge_write=True,
        )

    def test_pipeline_refuses_knowledge_course_dir(self, tmp_path: Path) -> None:
        from app import config

        url_file = tmp_path / "urls.json"
        url_file.write_text(
            json.dumps([{"url": "https://example.com/a", "topic": "x", "course": "os"}]),
            encoding="utf-8",
        )
        with pytest.raises(SourceIngestDenied):
            with patch("tools.crawler.pipeline.fetch_batch", return_value=[]):
                run_pipeline(url_file, config.KNOWLEDGE_ROOT / "os")


class TestIndexSkip:
    def test_inbox_and_candidates_are_not_indexable(self) -> None:
        assert is_indexable_relative_path("os/deadlock.md")
        assert is_indexable_frontmatter({})
        assert not is_indexable_relative_path("_inbox/raw.md")
        assert not is_indexable_relative_path("_templates/entry-template.md")
        assert not is_indexable_frontmatter(
            {"source_type": "web_candidate", "ingest_status": "candidate"}
        )
        assert not is_indexable_frontmatter({"source_type": "ai_draft"})
        assert is_indexable_frontmatter(
            {"source_type": "web_reviewed", "ingest_status": "approved"}
        )

    def test_built_index_skips_inbox(self, knowledge_chunks) -> None:
        leaked = [
            chunk.file
            for chunk in knowledge_chunks
            if "/_inbox/" in chunk.file.replace("\\", "/")
        ]
        assert leaked == []
