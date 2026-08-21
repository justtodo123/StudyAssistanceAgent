"""M6 爬虫测试 — 去重器单元测试。"""

from __future__ import annotations

import pytest

from tools.crawler.dedup import DedupIndex

pytestmark = pytest.mark.m6_crawler


class TestDedupIndex:
    """DedupIndex 测试。"""

    def test_same_url_is_duplicate(self) -> None:
        """同一 URL 应判为重复。"""
        idx = DedupIndex()
        idx.add("https://example.com/article1", "标题A", "内容A" * 50)
        is_dup, reason = idx.is_duplicate("https://example.com/article1", "标题B", "内容B" * 50)
        assert is_dup
        assert "URL" in reason

    def test_same_title_is_duplicate(self) -> None:
        """同标题不同 URL 应判为重复。"""
        idx = DedupIndex()
        idx.add("https://example.com/a", "TCP三次握手详解", "内容A" * 50)
        is_dup, reason = idx.is_duplicate("https://example.com/b", "TCP三次握手详解", "内容B" * 50)
        assert is_dup
        assert "title" in reason

    def test_same_content_is_duplicate(self) -> None:
        """不同 URL/标题但相同内容前 500 字应判为重复。"""
        idx = DedupIndex()
        content = "TCP是一种面向连接的可靠传输协议。" * 20
        idx.add("https://example.com/a", "标题A", content)
        is_dup, reason = idx.is_duplicate("https://example.com/b", "标题B", content)
        assert is_dup
        assert "content" in reason or "fingerprint" in reason

    def test_different_content_not_duplicate(self) -> None:
        """不同内容不应判为重复。"""
        idx = DedupIndex()
        idx.add("https://example.com/a", "标题A", "TCP三次握手" * 20)
        is_dup, _ = idx.is_duplicate("https://example.com/b", "标题B", "UDP无连接" * 20)
        assert not is_dup

    def test_check_and_add_returns_tuple(self) -> None:
        """check_and_add 应返回 (is_dup, reason)。"""
        idx = DedupIndex()
        is_dup, _ = idx.check_and_add("https://example.com/a", "标题", "内容" * 20)
        assert not is_dup
        # 重复添加
        is_dup, reason = idx.check_and_add("https://example.com/a", "标题", "内容" * 20)
        assert is_dup

    def test_size_property(self) -> None:
        """size 应返回已添加的 URL 数量。"""
        idx = DedupIndex()
        assert idx.size == 0
        idx.add("https://example.com/a", "A", "内容" * 20)
        assert idx.size == 1
        idx.add("https://example.com/b", "B", "其他" * 20)
        assert idx.size == 2

    def test_url_normalization(self) -> None:
        """http/https、www、末尾斜杠应视为同一 URL。"""
        idx = DedupIndex()
        idx.add("https://www.example.com/article/", "标题", "内容" * 20)
        is_dup, _ = idx.is_duplicate("http://example.com/article", "其他标题", "其他内容" * 20)
        assert is_dup

    def test_title_normalization(self) -> None:
        """标题去标点和空白后应视为相同。"""
        idx = DedupIndex()
        idx.add("https://example.com/a", "TCP 三次握手详解！", "内容" * 20)
        is_dup, _ = idx.is_duplicate("https://example.com/b", "TCP三次握手详解", "其他" * 20)
        assert is_dup
