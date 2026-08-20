"""M6 爬虫测试 — 管道集成测试（mock HTTP）。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.crawler.pipeline import run_pipeline


class TestPipeline:
    """run_pipeline 集成测试。"""

    def test_dry_run_does_not_write_files(self, tmp_path: Path, sample_html: str) -> None:
        """dry_run 模式不应写入文件。"""
        # 创建 URL 列表文件
        url_file = tmp_path / "urls.json"
        url_file.write_text(json.dumps([
            {"url": "https://example.com/a", "topic": "测试文章", "course": "network", "tags": ["test"]}
        ]), encoding="utf-8")

        output_dir = tmp_path / "output"

        # mock fetcher 返回成功
        from tools.crawler.fetcher import FetchResult

        mock_results = [
            FetchResult(url="https://example.com/a", status_code=200, html=sample_html, success=True)
        ]

        with patch("tools.crawler.pipeline.fetch_batch", return_value=mock_results):
            stats = run_pipeline(url_file, output_dir, dry_run=True)

        assert stats["converted"] >= 1
        assert stats["written"] >= 1  # dry_run 计数但不实际写
        assert not output_dir.exists()

    def test_writes_files_to_output(self, tmp_path: Path, sample_html: str) -> None:
        """非 dry_run 应写入文件到 output_dir。"""
        url_file = tmp_path / "urls.json"
        url_file.write_text(json.dumps([
            {"url": "https://example.com/a", "topic": "测试文章", "course": "network", "tags": ["test"]}
        ]), encoding="utf-8")

        output_dir = tmp_path / "output"

        from tools.crawler.fetcher import FetchResult

        mock_results = [
            FetchResult(url="https://example.com/a", status_code=200, html=sample_html, success=True)
        ]

        with patch("tools.crawler.pipeline.fetch_batch", return_value=mock_results):
            stats = run_pipeline(url_file, output_dir, dry_run=False)

        assert stats["written"] >= 1
        assert output_dir.exists()
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) >= 1

        # 验证文件内容
        content = md_files[0].read_text(encoding="utf-8")
        assert "course: network" in content

    def test_skip_failed_fetch(self, tmp_path: Path) -> None:
        """抓取失败的 URL 应被跳过。"""
        url_file = tmp_path / "urls.json"
        url_file.write_text(json.dumps([
            {"url": "https://example.com/fail", "topic": "失败", "course": "network"}
        ]), encoding="utf-8")

        output_dir = tmp_path / "output"

        from tools.crawler.fetcher import FetchResult

        mock_results = [
            FetchResult(url="https://example.com/fail", status_code=0, html="", success=False, error="timeout")
        ]

        with patch("tools.crawler.pipeline.fetch_batch", return_value=mock_results):
            stats = run_pipeline(url_file, output_dir, dry_run=False)

        assert stats["fetched"] == 0
        assert stats["written"] == 0

    def test_skip_short_content(self, tmp_path: Path) -> None:
        """内容过短的页面应被跳过。"""
        url_file = tmp_path / "urls.json"
        url_file.write_text(json.dumps([
            {"url": "https://example.com/short", "topic": "短文", "course": "network"}
        ]), encoding="utf-8")

        output_dir = tmp_path / "output"

        from tools.crawler.fetcher import FetchResult

        mock_results = [
            FetchResult(url="https://example.com/short", status_code=200, html="太短", success=True)
        ]

        with patch("tools.crawler.pipeline.fetch_batch", return_value=mock_results):
            stats = run_pipeline(url_file, output_dir, dry_run=False)

        assert stats["cleaned"] == 0
        assert stats["written"] == 0
