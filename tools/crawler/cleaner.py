"""HTML 内容清洗器：从 HTML 提取正文纯文本。

使用 trafilatura 进行主内容提取（自动去导航/广告/页脚）。
trafilatura 不可用时降级为 beautifulsoup4 手动提取。
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# trafilatura 可选依赖
try:
    import trafilatura

    _HAS_TRAFILATURA = True
except ImportError:
    _HAS_TRAFILATURA = False
    logger.info("trafilatura not installed, falling back to basic BS4 extraction")

try:
    from bs4 import BeautifulSoup

    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


def clean_html(html: str, *, url: str = "") -> str:
    """从 HTML 提取正文文本。

    优先使用 trafilatura（精度高），降级为 BS4 手动提取。

    Args:
        html: 原始 HTML 字符串
        url: 来源 URL（用于 trafilatura 的 URL 指纹去重）

    Returns:
        清洗后的纯文本（保留段落结构，去除导航/广告/脚本）
    """
    if not html.strip():
        return ""

    text = ""

    # 路径 1: trafilatura（推荐）
    if _HAS_TRAFILATURA:
        text = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
            deduplicate=True,
        ) or ""

    # 路径 2: BS4 降级
    if not text and _HAS_BS4:
        text = _extract_with_bs4(html)

    # 路径 3: 最基础的 regex 去标签
    if not text:
        text = _extract_with_regex(html)

    # 通用后处理
    text = _post_process(text)
    return text


def _extract_with_bs4(html: str) -> str:
    """BS4 手动提取：取 article/main/div.content 内的文本。"""
    soup = BeautifulSoup(html, "html.parser")

    # 移除噪声标签
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # 优先找 article / main
    content = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|post|article|entry"))
    if content:
        return content.get_text(separator="\n", strip=True)

    # 降级取 body
    body = soup.find("body")
    if body:
        return body.get_text(separator="\n", strip=True)

    return soup.get_text(separator="\n", strip=True)


def _extract_with_regex(html: str) -> str:
    """最基础的 regex 去标签（最终降级）。"""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-z]+;", "", text)
    return text


def _post_process(text: str) -> str:
    """通用后处理：去多余空行、strip。"""
    # 合并连续空行为最多两个换行
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 去每行首尾空白
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    # 合并连续空行（再次，因为 strip 可能产生新空行）
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_title(html: str) -> str:
    """从 HTML 提取页面标题。"""
    if _HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()

    # regex 降级
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""
