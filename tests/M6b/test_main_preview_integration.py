"""M6b tests for default-off main application integration."""

from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.m6b
_TOKEN = "preview-token-that-is-at-least-thirty-two-bytes"
_PREVIEW_PATH = "/api/v1/agent-preview"


def _load_main(monkeypatch: pytest.MonkeyPatch, *, enabled: bool) -> Any:
    monkeypatch.setenv("SA_USE_VECTOR", "false")
    monkeypatch.setenv("SA_AGENT_PREVIEW_ENABLED", "true" if enabled else "false")
    if enabled:
        monkeypatch.setenv("SA_AGENT_PREVIEW_TOKEN", _TOKEN)
    else:
        monkeypatch.delenv("SA_AGENT_PREVIEW_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import app.config as config

    importlib.reload(config)
    sys.modules.pop("app.main", None)
    return importlib.import_module("app.main")


def test_default_main_app_omits_preview_route(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _load_main(monkeypatch, enabled=False)

    assert _PREVIEW_PATH not in main.app.openapi()["paths"]


def test_enabled_main_app_registers_preview_before_openapi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = _load_main(monkeypatch, enabled=True)

    assert _PREVIEW_PATH in main.app.openapi()["paths"]
    with TestClient(main.app) as client:
        unauthorized = client.post(_PREVIEW_PATH, json={"prompt": "question"})
        unavailable = client.post(
            _PREVIEW_PATH,
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={"prompt": "question"},
        )

    assert unauthorized.status_code == 401
    assert unauthorized.json()["detail"]["error"]["code"] == "PREVIEW_UNAUTHORIZED"
    assert unavailable.status_code == 503
    assert (
        unavailable.json()["detail"]["error"]["code"]
        == "PREVIEW_PROVIDER_NOT_CONFIGURED"
    )
