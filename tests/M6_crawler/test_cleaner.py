"""M6 爬虫测试 — 清洗器单元测试。"""

from __future__ import annotations

import pytest

from tools.crawler.cleaner import clean_html, extract_title

pytestmark = pytest.mark.m6_crawler


class TestCleanHtml:
    """clean_html 测试。"""

    def test_extracts_article_content(self, sample_html: str) -> None:
        """应提取 article 标签内的正文。"""
        text = clean_html(sample_html)
        assert "TCP三次握手" in text
        assert "第一次握手" in text
        assert "SYN=1" in text

    def test_removes_script_content(self, sample_html: str) -> None:
        """应去除 script 标签内容。"""
        text = clean_html(sample_html)
        assert "console.log" not in text

    def test_preserves_main_content(self, sample_html: str) -> None:
        """应保留文章主体内容。"""
        text = clean_html(sample_html)
        assert "TCP" in text
        assert "SYN" in text

    def test_removes_scripts(self, sample_html: str) -> None:
        """应去除 script 标签。"""
        text = clean_html(sample_html)
        assert "console.log" not in text

    def test_empty_html_returns_empty(self) -> None:
        """空 HTML 应返回空字符串。"""
        assert clean_html("") == ""
        assert clean_html("   ") == ""

    def test_plain_text_passthrough(self) -> None:
        """纯文本（无 HTML 标签）应原样返回。"""
        text = "这是一段纯文本，没有HTML标签。"
        result = clean_html(text)
        assert "纯文本" in result


class TestExtractTitle:
    """extract_title 测试。"""

    def test_extracts_title_tag(self, sample_html: str) -> None:
        """应提取 <title> 标签内容。"""
        title = extract_title(sample_html)
        assert title == "TCP三次握手详解 - CSDN博客"

    def test_empty_html_returns_empty(self) -> None:
        """无 <title> 时应返回空字符串。"""
        assert extract_title("<html><body>no title</body></html>") == ""

    def test_empty_string_returns_empty(self) -> None:
        """空字符串应返回空字符串。"""
        assert extract_title("") == ""
