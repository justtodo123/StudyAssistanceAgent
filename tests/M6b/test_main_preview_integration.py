"""M6b tests for default-off main application integration."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


pytestmark = pytest.mark.m6b
_TOKEN = "preview-token-that-is-at-least-thirty-two-bytes"
_PREVIEW_PATH = "/api/v1/agent-preview"


def _application(tmp_path, *, enabled: bool):
    environment = {
        "SA_USE_VECTOR": "false",
        "SA_AGENT_PREVIEW_ENABLED": "true" if enabled else "false",
        "SA_INDEX_CACHE_PATH": str(tmp_path / "index"),
        "SA_LEARNING_STORE_PATH": str(tmp_path / "learning.sqlite3"),
        "SA_SOURCE_REGISTRY_PATH": str(tmp_path / "sources.sqlite3"),
        "SA_USER_SOURCE_CACHE_PATH": str(tmp_path / "user-sources"),
    }
    if enabled:
        environment["SA_AGENT_PREVIEW_TOKEN"] = _TOKEN
    return create_app(load_settings(environment))


def test_default_main_app_omits_preview_route(tmp_path) -> None:
    application = _application(tmp_path, enabled=False)

    assert _PREVIEW_PATH not in application.openapi()["paths"]


def test_enabled_main_app_registers_preview_before_openapi(tmp_path) -> None:
    application = _application(tmp_path, enabled=True)

    assert _PREVIEW_PATH in application.openapi()["paths"]
    with TestClient(application) as client:
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
