"""URL 抓取器：基于 httpx 的网页内容获取。

特性：
- 自动重试（默认 3 次，指数退避）
- 超时控制（默认 30s）
- 限速（默认每请求间隔 1s，避免被封）
- User-Agent 伪装
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


@dataclass
class FetchResult:
    """抓取结果。"""
    url: str
    status_code: int
    html: str
    success: bool
    error: str | None = None


def fetch_url(
    url: str,
    *,
    timeout: float = 30.0,
    retries: int = 3,
    retry_delay: float = 2.0,
) -> FetchResult:
    """抓取单个 URL 的 HTML 内容。

    Args:
        url: 目标 URL
        timeout: 请求超时（秒）
        retries: 最大重试次数
        retry_delay: 重试间隔基数（秒），实际间隔 = delay * 2^attempt

    Returns:
        FetchResult 包含 HTML 或错误信息
    """
    last_error: str | None = None

    for attempt in range(retries):
        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                headers=_DEFAULT_HEADERS,
            ) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return FetchResult(
                    url=url,
                    status_code=resp.status_code,
                    html=resp.text,
                    success=True,
                )
        except httpx.HTTPStatusError as exc:
            last_error = f"HTTP {exc.response.status_code}: {exc}"
            logger.warning("fetch %s attempt %d failed: %s", url, attempt + 1, last_error)
        except httpx.RequestError as exc:
            last_error = f"Request error: {exc}"
            logger.warning("fetch %s attempt %d failed: %s", url, attempt + 1, last_error)

        if attempt < retries - 1:
            delay = retry_delay * (2 ** attempt)
            logger.info("retrying %s in %.1fs...", url, delay)
            time.sleep(delay)

    return FetchResult(url=url, status_code=0, html="", success=False, error=last_error)


def fetch_batch(
    urls: list[str],
    *,
    delay: float = 1.0,
    timeout: float = 30.0,
    retries: int = 3,
) -> list[FetchResult]:
    """批量抓取 URL 列表，自动限速。

    Args:
        urls: URL 列表
        delay: 每次请求间的最小间隔（秒）
        timeout: 单次请求超时
        retries: 最大重试次数

    Returns:
        FetchResult 列表，顺序与输入一致
    """
    results: list[FetchResult] = []
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(delay)
        logger.info("fetching [%d/%d] %s", i + 1, len(urls), url)
        results.append(fetch_url(url, timeout=timeout, retries=retries))
    success = sum(1 for r in results if r.success)
    logger.info("fetch complete: %d/%d succeeded", success, len(urls))
    return results
