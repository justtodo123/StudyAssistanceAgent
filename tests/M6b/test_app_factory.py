"""Application-factory isolation and compatibility contracts."""

from __future__ import annotations

import pytest

from app.config import load_settings
from app.main import app, create_app
from app.runner_service import RUNNER_PATH

pytestmark = pytest.mark.m6b

_PREVIEW_PATH = "/api/v1/agent-preview"
_TOKEN = "factory-preview-token-that-is-long-enough"


def _settings(tmp_path, **overrides: str):
    environment = {
        "SA_USE_VECTOR": "false",
        "SA_INDEX_CACHE_PATH": str(tmp_path / overrides.pop("suffix", "default") / "index"),
        "SA_LEARNING_STORE_PATH": str(tmp_path / "learning.sqlite3"),
        "SA_SOURCE_REGISTRY_PATH": str(tmp_path / "sources.sqlite3"),
        "SA_USER_SOURCE_CACHE_PATH": str(tmp_path / "user-sources"),
        **overrides,
    }
    return load_settings(environment)


def test_factory_apps_own_independent_services_and_openapi(tmp_path) -> None:
    default_app = create_app(_settings(tmp_path, suffix="default"))
    preview_app = create_app(
        _settings(
            tmp_path,
            suffix="preview",
            SA_AGENT_PREVIEW_ENABLED="true",
            SA_AGENT_PREVIEW_TOKEN=_TOKEN,
        )
    )
    runner_app = create_app(
        _settings(tmp_path, suffix="runner", SA_RUNNER="true")
    )

    default_paths = default_app.openapi()["paths"]
    preview_paths = preview_app.openapi()["paths"]
    runner_paths = runner_app.openapi()["paths"]

    assert _PREVIEW_PATH not in default_paths
    assert RUNNER_PATH not in default_paths
    assert _PREVIEW_PATH in preview_paths
    assert RUNNER_PATH not in preview_paths
    assert RUNNER_PATH in runner_paths
    assert _PREVIEW_PATH not in runner_paths

    assert default_app.state.services is not preview_app.state.services
    assert preview_app.state.services is not runner_app.state.services
    assert default_app.openapi_schema is not preview_app.openapi_schema
    assert preview_app.openapi_schema is not runner_app.openapi_schema


def test_module_level_app_remains_factory_compatible() -> None:
    assert app.state.services.settings.agent_preview_enabled is False
    assert app.state.services.settings.runner_enabled is False
    assert _PREVIEW_PATH not in app.openapi()["paths"]
    assert RUNNER_PATH not in app.openapi()["paths"]
