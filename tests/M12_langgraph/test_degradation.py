"""Tests for LangGraph degradation — behaviour when langgraph is unavailable."""

from __future__ import annotations

import pytest


class TestLangGraphAvailability:
    def test_flag_reflects_install_state(self):
        from app.graphs import LANGGRAPH_AVAILABLE

        assert isinstance(LANGGRAPH_AVAILABLE, bool)

    def test_config_fields_exist(self):
        from app.config import Settings, load_settings

        settings = load_settings(environ={})
        assert hasattr(settings, "langgraph_enabled")
        assert hasattr(settings, "langgraph_token")
        assert hasattr(settings, "langgraph_llm_enabled")
        assert settings.langgraph_enabled is False

    def test_langgraph_disabled_by_default(self):
        from app.config import load_settings

        settings = load_settings(environ={})
        assert settings.langgraph_enabled is False

    def test_langgraph_token_required_when_enabled(self):
        from app.config import load_settings

        with pytest.raises(ValueError, match="SA_LANGRAPH_TOKEN"):
            load_settings(environ={
                "SA_LANGRAPH_ENABLED": "true",
                "SA_LANGRAPH_TOKEN": "short",
            })

    def test_langgraph_token_accepted_when_sufficient(self):
        from app.config import load_settings

        settings = load_settings(environ={
            "SA_LANGRAPH_ENABLED": "true",
            "SA_LANGRAPH_TOKEN": "a" * 32,
        })
        assert settings.langgraph_enabled is True
        assert settings.langgraph_token == "a" * 32

    def test_v2_routes_not_registered_when_disabled(self):
        from fastapi.testclient import TestClient

        from app.config import load_settings
        from app.main import create_app

        settings = load_settings(environ={})
        app = create_app(settings)
        client = TestClient(app)

        response = client.post(
            "/api/v2/assist",
            json={"intent": "general", "question": "test"},
        )
        assert response.status_code == 404

    def test_health_reports_langgraph_status(self):
        from fastapi.testclient import TestClient

        from app.config import load_settings
        from app.main import create_app

        settings = load_settings(environ={})
        app = create_app(settings)
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "langgraph_enabled" in data
        assert data["langgraph_enabled"] is False


class TestLangGraphLimits:
    def test_default_limits(self):
        from app.graphs.config import LangGraphLimits

        limits = LangGraphLimits()
        assert limits.max_nodes_per_graph == 50
        assert limits.max_remediation_attempts == 2

    def test_validate_accepts_defaults(self):
        from app.graphs.config import LangGraphLimits, validate_limits

        validate_limits(LangGraphLimits())

    def test_validate_rejects_oversized(self):
        from app.graphs.config import LangGraphLimits, validate_limits

        limits = LangGraphLimits(max_nodes_per_graph=100)
        with pytest.raises(ValueError, match="max_nodes_per_graph"):
            validate_limits(limits)
