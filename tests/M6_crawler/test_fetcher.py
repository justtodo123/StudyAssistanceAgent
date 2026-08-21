"""Offline fetcher tests with mocked HTTP."""

from __future__ import annotations

import pytest

from tools.crawler.fetcher import fetch_batch, fetch_url

pytestmark = pytest.mark.m6_crawler


class _DummyResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("GET", "https://example.com/a")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)


class _DummyClient:
    def __init__(self, *args, **kwargs) -> None:
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url: str) -> _DummyResponse:
        return _DummyResponse("<html><body><p>hello from mock</p></body></html>")


def test_fetch_url_uses_mocked_client(monkeypatch, sample_html: str) -> None:
    class HtmlClient(_DummyClient):
        def get(self, url: str) -> _DummyResponse:
            return _DummyResponse(sample_html)

    monkeypatch.setattr("tools.crawler.fetcher.httpx.Client", HtmlClient)
    result = fetch_url("https://example.com/tcp", timeout=1.0, retries=1)
    assert result.success is True
    assert result.status_code == 200
    assert "TCP" in result.html


def test_fetch_url_records_http_error(monkeypatch) -> None:
    class FailClient(_DummyClient):
        def get(self, url: str) -> _DummyResponse:
            return _DummyResponse("nope", status_code=500)

    monkeypatch.setattr("tools.crawler.fetcher.httpx.Client", FailClient)
    result = fetch_url("https://example.com/fail", timeout=1.0, retries=1)
    assert result.success is False
    assert result.html == ""
    assert result.error


def test_fetch_batch_preserves_order(monkeypatch, sample_html: str) -> None:
    class HtmlClient(_DummyClient):
        def get(self, url: str) -> _DummyResponse:
            return _DummyResponse(sample_html)

    monkeypatch.setattr("tools.crawler.fetcher.httpx.Client", HtmlClient)
    results = fetch_batch(
        ["https://example.com/a", "https://example.com/b"],
        delay=0,
        timeout=1.0,
        retries=1,
    )
    assert [item.url for item in results] == ["https://example.com/a", "https://example.com/b"]
    assert all(item.success for item in results)