"""Opt-in crawler online smoke; skipped unless CRAWLER_ONLINE=1."""

from __future__ import annotations

import os

import pytest

from tools.crawler.fetcher import fetch_url

pytestmark = [pytest.mark.m6_crawler, pytest.mark.online]


def test_fetch_example_dot_com_when_enabled() -> None:
    enabled = os.getenv("CRAWLER_ONLINE", "").strip().lower() in {"1", "true", "yes"}
    if not enabled:
        pytest.skip("online crawler smoke is opt-in via CRAWLER_ONLINE=1")
    result = fetch_url("https://example.com", timeout=10.0, retries=1)
    assert result.success is True
    assert result.status_code == 200
    assert "Example" in result.html or len(result.html) > 0