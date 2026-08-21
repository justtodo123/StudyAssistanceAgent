"""Offline crawler P0 contracts: candidate dir, eval isolation, path privacy."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

import run_evaluation as ev
from app.source_policy import default_crawler_output_dir
from tools.crawler.converter import ArticleMeta, to_knowledge_markdown
from tools.crawler.pipeline import run_pipeline

pytestmark = pytest.mark.m6_crawler

_ABS_WIN = re.compile(r"[A-Za-z]:[\\/]")


class TestCandidateOutputDir:
    def test_default_output_is_cache_not_knowledge(self) -> None:
        from app import config

        out = default_crawler_output_dir("network")
        assert "crawler-candidates" in out.as_posix()
        assert "platform" in out.as_posix()
        knowledge = config.KNOWLEDGE_ROOT.resolve()
        try:
            out.resolve().relative_to(knowledge)
            raise AssertionError("default crawler output must not sit under knowledge/")
        except ValueError:
            pass

    def test_pipeline_writes_only_to_given_output(self, tmp_path: Path, sample_html: str) -> None:
        from app import config
        from tools.crawler.fetcher import FetchResult

        url_file = tmp_path / "urls.json"
        url_file.write_text(
            json.dumps(
                [{"url": "https://example.com/a", "topic": "TCP三次握手", "course": "network", "tags": ["TCP"]}]
            ),
            encoding="utf-8",
        )
        output_dir = tmp_path / "candidates" / "network"
        mock_results = [
            FetchResult(url="https://example.com/a", status_code=200, html=sample_html, success=True)
        ]
        with patch("tools.crawler.pipeline.fetch_batch", return_value=mock_results):
            stats = run_pipeline(url_file, output_dir, dry_run=False, delay=0)
        assert stats["written"] >= 1
        assert output_dir.exists()
        course_dir = config.KNOWLEDGE_ROOT / "network"
        leaked = list(course_dir.glob("*handshake*.md")) if course_dir.exists() else []
        assert leaked == []


class TestDefaultEvalIsolation:
    def test_default_discovery_is_os_ds_co_ninety(self, repo_root: Path) -> None:
        assert ev.KNOWN_COURSES == ("os", "ds", "co")
        found = ev.discover_evaluation_sets(repo_root)
        counts = {item["course"]: len(ev.load_test_set(item["path"])) for item in found}
        assert counts == {"os": 38, "ds": 28, "co": 24}
        assert sum(counts.values()) == 90
        assert "network" not in counts

    def test_indexed_knowledge_has_no_web_candidates(self, knowledge_chunks) -> None:
        leaked = [
            chunk.file
            for chunk in knowledge_chunks
            if "/_inbox/" in chunk.file.replace("\\", "/")
        ]
        assert leaked == []


class TestPathPrivacy:
    def test_markdown_has_no_local_absolute_path(self, sample_text: str, repo_root: Path) -> None:
        md = to_knowledge_markdown(
            sample_text,
            ArticleMeta(title="TCP三次握手", course="network", tags=["TCP"]),
        )
        assert str(repo_root.resolve()) not in md
        assert _ABS_WIN.search(md) is None

    def test_pipeline_stats_hide_absolute_paths(
        self, tmp_path: Path, sample_html: str, repo_root: Path
    ) -> None:
        from tools.crawler.fetcher import FetchResult

        url_file = tmp_path / "urls.json"
        url_file.write_text(
            json.dumps([{"url": "https://example.com/a", "topic": "TCP三次握手", "course": "network"}]),
            encoding="utf-8",
        )
        output_dir = tmp_path / "out"
        mock_results = [
            FetchResult(url="https://example.com/a", status_code=200, html=sample_html, success=True)
        ]
        with patch("tools.crawler.pipeline.fetch_batch", return_value=mock_results):
            stats = run_pipeline(url_file, output_dir, dry_run=False, delay=0)
        dumped = json.dumps(stats, ensure_ascii=False)
        assert str(repo_root.resolve()) not in dumped
        assert _ABS_WIN.search(dumped) is None
        assert ":" not in stats["output_dir"] or not _ABS_WIN.search(stats["output_dir"])


class TestStableCandidate:
    def test_converter_output_is_stable_except_date(self, sample_text: str) -> None:
        meta = ArticleMeta(title="TCP三次握手", course="network", tags=["TCP"])
        first = to_knowledge_markdown(sample_text, meta)
        second = to_knowledge_markdown(sample_text, meta)
        def _drop_updated(md: str) -> str:
            return re.sub(r"^updated: .*$", "updated: DATE", md, flags=re.M)
        assert _drop_updated(first) == _drop_updated(second)
        assert "source_type: web_candidate" in first
        assert "ingest_status: candidate" in first