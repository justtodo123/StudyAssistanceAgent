"""Tests for LangSmith tracing integration.

Covers:
- build_invoke_config returns empty dict when tracing is off
- build_invoke_config attaches callbacks when tracing is on
- build_invoke_config falls back gracefully on import failure
- GraphContainer.invoke_config delegates correctly
- Settings picks up SA_LANGSMITH_TRACING and SA_LANGSMITH_PROJECT
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.graphs import LANGGRAPH_AVAILABLE

pytestmark = pytest.mark.skipif(
    not LANGGRAPH_AVAILABLE,
    reason="langgraph is not installed",
)


class TestBuildInvokeConfig:
    def test_tracing_off_returns_empty(self):
        from app.graphs.dependencies import build_invoke_config

        config = build_invoke_config(tracing=False)
        assert config == {}

    def test_tracing_on_returns_callbacks(self):
        from app.graphs.dependencies import build_invoke_config

        fake_tracer = MagicMock()

        fake_client_cls = MagicMock()
        fake_client_cls.return_value = MagicMock()

        fake_tracer_cls = MagicMock(return_value=fake_tracer)

        with (
            patch(
                "app.graphs.dependencies.LangChainTracer",
                fake_tracer_cls,
                create=True,
            ) if False else patch.dict(
                "sys.modules",
                {},
            )
        ):
            pass

        with (
            patch("langchain_core.tracers.langchain.LangChainTracer", fake_tracer_cls),
            patch("langsmith.Client", fake_client_cls),
        ):
            config = build_invoke_config(tracing=True, project="test-project")

        assert "callbacks" in config
        assert len(config["callbacks"]) == 1
        fake_tracer_cls.assert_called_once_with(
            client=fake_client_cls.return_value,
            project_name="test-project",
        )

    def test_tracing_on_with_session_id(self):
        from app.graphs.dependencies import build_invoke_config

        fake_tracer = MagicMock()
        fake_tracer_cls = MagicMock(return_value=fake_tracer)
        fake_client_cls = MagicMock(return_value=MagicMock())

        with (
            patch("langchain_core.tracers.langchain.LangChainTracer", fake_tracer_cls),
            patch("langsmith.Client", fake_client_cls),
        ):
            config = build_invoke_config(
                tracing=True,
                project="test-project",
                session_id="abc-123",
            )

        assert config["metadata"]["session_id"] == "abc-123"

    def test_tracing_falls_back_on_import_failure(self):
        from app.graphs.dependencies import build_invoke_config

        with patch("langchain_core.tracers.langchain.LangChainTracer", side_effect=ImportError):
            config = build_invoke_config(tracing=True)
        assert config == {}

    def test_tracing_falls_back_on_client_error(self):
        from app.graphs.dependencies import build_invoke_config

        with (
            patch("langsmith.Client", side_effect=Exception("no key")),
        ):
            config = build_invoke_config(tracing=True)
        assert config == {}


class TestContainerInvokeConfig:
    def test_container_invoke_config_delegates(self):
        from app.graphs.dependencies import GraphContainer

        container = GraphContainer(
            recall=MagicMock(),
            qa_service=MagicMock(),
            quiz_service=MagicMock(),
            review_scheduler=MagicMock(),
            goal_planner=MagicMock(),
            plan_lifecycle=MagicMock(),
            tracing=True,
            tracing_project="my-project",
        )

        fake_tracer = MagicMock()
        fake_tracer_cls = MagicMock(return_value=fake_tracer)
        fake_client_cls = MagicMock(return_value=MagicMock())

        with (
            patch("langchain_core.tracers.langchain.LangChainTracer", fake_tracer_cls),
            patch("langsmith.Client", fake_client_cls),
        ):
            config = container.invoke_config(session_id="sess-1")

        assert "callbacks" in config
        assert config["metadata"]["session_id"] == "sess-1"

    def test_container_tracing_off_by_default(self):
        from app.graphs.dependencies import GraphContainer

        container = GraphContainer(
            recall=MagicMock(),
            qa_service=MagicMock(),
            quiz_service=MagicMock(),
            review_scheduler=MagicMock(),
            goal_planner=MagicMock(),
            plan_lifecycle=MagicMock(),
        )
        assert container.tracing is False
        assert container.invoke_config() == {}


class TestLangSmithSettings:
    def test_default_tracing_off(self):
        from app.config import load_settings

        env = {
            "SA_LANGRAPH_ENABLED": "false",
            "SA_LANGRAPH_TOKEN": "",
            "SA_LANGRAPH_LLM_ENABLED": "false",
            "SA_AGENT_PREVIEW_ENABLED": "false",
            "SA_AGENT_PREVIEW_TOKEN": "",
            "SA_PLAN_AI_ENABLED": "false",
            "SA_PLAN_AI_TOKEN": "",
            "SA_RUNNER": "false",
        }
        settings = load_settings(env)
        assert settings.langsmith_tracing is False
        assert settings.langsmith_project == "study-assistant"

    def test_tracing_enabled_via_env(self):
        from app.config import load_settings

        env = {
            "SA_LANGRAPH_ENABLED": "false",
            "SA_LANGRAPH_TOKEN": "",
            "SA_LANGRAPH_LLM_ENABLED": "false",
            "SA_AGENT_PREVIEW_ENABLED": "false",
            "SA_AGENT_PREVIEW_TOKEN": "",
            "SA_PLAN_AI_ENABLED": "false",
            "SA_PLAN_AI_TOKEN": "",
            "SA_RUNNER": "false",
            "SA_LANGSMITH_TRACING": "true",
            "SA_LANGSMITH_PROJECT": "my-study-app",
        }
        settings = load_settings(env)
        assert settings.langsmith_tracing is True
        assert settings.langsmith_project == "my-study-app"
