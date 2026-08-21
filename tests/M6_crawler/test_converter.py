"""M6 爬虫测试 — Markdown 转换器单元测试。"""

from __future__ import annotations

import pytest
import yaml

from tools.crawler.converter import ArticleMeta, slug_from_title, to_knowledge_markdown

pytestmark = pytest.mark.m6_crawler


class TestToKnowledgeMarkdown:
    """to_knowledge_markdown 测试。"""

    def test_contains_frontmatter(self, sample_text: str) -> None:
        """输出应包含 YAML frontmatter。"""
        meta = ArticleMeta(title="TCP三次握手", course="network", tags=["TCP"])
        md = to_knowledge_markdown(sample_text, meta)
        assert md.startswith("---\n")
        assert "title: TCP三次握手" in md
        assert "course: network" in md
        assert "source_type: web_candidate" in md
        assert "ingest_status: candidate" in md

    def test_frontmatter_has_updated_date(self, sample_text: str) -> None:
        """frontmatter 应包含 updated 日期。"""
        meta = ArticleMeta(title="测试", course="network")
        md = to_knowledge_markdown(sample_text, meta)
        # 提取 frontmatter
        fm_text = md.split("---\n")[1]
        fm = yaml.safe_load(fm_text)
        assert "updated" in fm
        assert len(fm["updated"]) == 10  # YYYY-MM-DD

    def test_contains_tldr_section(self, sample_text: str) -> None:
        """输出应包含 TL;DR 节。"""
        meta = ArticleMeta(title="TCP三次握手", course="network")
        md = to_knowledge_markdown(sample_text, meta)
        assert "一句话概括" in md or "TL;DR" in md

    def test_contains_core_section(self, sample_text: str) -> None:
        """输出应包含核心概念节。"""
        meta = ArticleMeta(title="TCP三次握手", course="network")
        md = to_knowledge_markdown(sample_text, meta)
        assert "核心概念" in md

    def test_source_url_in_frontmatter(self, sample_text: str) -> None:
        """有 source_url 时应出现在 frontmatter 中。"""
        meta = ArticleMeta(title="测试", course="network", source_url="https://example.com")
        md = to_knowledge_markdown(sample_text, meta)
        assert "https://example.com" in md

    def test_no_source_url_when_empty(self, sample_text: str) -> None:
        """无 source_url 时 frontmatter 中不应出现该字段。"""
        meta = ArticleMeta(title="测试", course="network")
        md = to_knowledge_markdown(sample_text, meta)
        assert "source_url" not in md


class TestSlugFromTitle:
    """slug_from_title 测试。"""

    def test_chinese_title(self) -> None:
        """中文标题应生成合理的 slug。"""
        slug = slug_from_title("TCP三次握手详解")
        assert len(slug) > 0
        assert not slug.startswith("-")
        assert not slug.endswith("-")

    def test_removes_special_chars(self) -> None:
        """应去除括号等特殊字符。"""
        slug = slug_from_title("IP地址（含子网划分）")
        assert "（" not in slug
        assert "）" not in slug

    def test_empty_title(self) -> None:
        """空标题应返回 'untitled'。"""
        assert slug_from_title("") == "untitled"

    def test_length_limit(self) -> None:
        """超长标题应截断到 50 字符。"""
        long_title = "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的标题"
        slug = slug_from_title(long_title)
        assert len(slug) <= 50
