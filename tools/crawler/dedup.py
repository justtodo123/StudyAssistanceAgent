"""去重器：基于标题+内容指纹的重复检测。

策略：
1. URL 精确去重（同一 URL 不重复处理）
2. 标题相似度去重（标题相同或高度相似）
3. 内容前 500 字的 hash 去重（近似重复检测）
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_TITLE_STRIP_CHARS = "，。、；：？！\"'《》（）()[]{}"
_CONTENT_STRIP_CHARS = _TITLE_STRIP_CHARS + "-#*>`"
_TITLE_STRIP_TABLE = str.maketrans("", "", _TITLE_STRIP_CHARS)
_CONTENT_STRIP_TABLE = str.maketrans("", "", _CONTENT_STRIP_CHARS)


@dataclass
class DedupIndex:
    """去重索引：记录已处理的 URL、标题、内容指纹。"""
    _seen_urls: set[str] = field(default_factory=set)
    _seen_titles: set[str] = field(default_factory=set)
    _seen_hashes: set[str] = field(default_factory=set)

    def is_duplicate(self, url: str, title: str, content: str) -> tuple[bool, str]:
        """检查是否重复。

        Returns:
            (is_dup, reason) — reason 说明重复类型
        """
        # URL 精确匹配
        normalized_url = _normalize_url(url)
        if normalized_url in self._seen_urls:
            return True, "duplicate URL"

        # 标题匹配
        normalized_title = _normalize_title(title)
        if normalized_title in self._seen_titles:
            return True, "duplicate title"

        # 内容指纹（前 500 字）
        content_hash = _content_fingerprint(content)
        if content_hash in self._seen_hashes:
            return True, "duplicate content (fingerprint match)"

        return False, ""

    def add(self, url: str, title: str, content: str) -> None:
        """将文章加入去重索引。"""
        self._seen_urls.add(_normalize_url(url))
        self._seen_titles.add(_normalize_title(title))
        self._seen_hashes.add(_content_fingerprint(content))

    def check_and_add(self, url: str, title: str, content: str) -> tuple[bool, str]:
        """检查并自动添加（非重复时）。"""
        is_dup, reason = self.is_duplicate(url, title, content)
        if not is_dup:
            self.add(url, title, content)
        return is_dup, reason

    @property
    def size(self) -> int:
        return len(self._seen_urls)


def _normalize_url(url: str) -> str:
    """URL 归一化：去协议前缀、末尾斜杠、查询参数。"""
    url = url.strip().lower()
    url = re.sub(r"^https?://(www\.)?", "", url)
    url = url.split("?")[0].split("#")[0]
    return url.rstrip("/")


def _normalize_title(title: str) -> str:
    """标题归一化：去空白、标点、统一大小写。"""
    title = title.strip().lower()
    title = re.sub(r"\s+", "", title)
    return title.translate(_TITLE_STRIP_TABLE)


def _content_fingerprint(content: str) -> str:
    """内容指纹：取前 500 个有效字符的 SHA-1。"""
    # 去空白和标点，取前 500 字符
    cleaned = re.sub(r"\s+", "", content)
    cleaned = cleaned.translate(_CONTENT_STRIP_TABLE)
    sample = cleaned[:500]
    return hashlib.sha1(sample.encode("utf-8")).hexdigest()
