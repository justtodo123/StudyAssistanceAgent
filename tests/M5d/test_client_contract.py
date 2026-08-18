"""Workbench client must call official APIs and not copy the state machine."""

from __future__ import annotations

import re

import pytest

from tests.M5d.conftest import (
    ALLOWED_API_PREFIXES,
    FORBIDDEN_API_PREFIXES,
    WORKBENCH_INDEX,
    WORKBENCH_JS,
)


def _api_paths(text: str) -> set[str]:
    found = set(re.findall(r'["\'](/api/v1/[^"\']+)["\']', text))
    found.update(re.findall(r"`(/api/v1/[^`]+)`", text))
    return found


@pytest.mark.m5d
class TestWorkbenchClientContract:
    def test_js_only_uses_official_session_and_due_apis(self):
        source = WORKBENCH_JS.read_text(encoding="utf-8")
        paths = _api_paths(source)
        assert paths
        for path in paths:
            assert any(path.startswith(prefix) for prefix in ALLOWED_API_PREFIXES), path
            assert not any(path.startswith(prefix) for prefix in FORBIDDEN_API_PREFIXES)

    def test_js_does_not_implement_state_machine(self):
        source = WORKBENCH_JS.read_text(encoding="utf-8")
        forbidden_tokens = (
            "STATE_CREATED",
            "STATE_EXPLAINING",
            "STATE_EVALUATING",
            "MAX_ATTEMPTS",
            "log_review",
            "/api/v1/qa",
            "/api/v1/quiz",
            "/api/v1/review-log",
        )
        for token in forbidden_tokens:
            assert token not in source

    def test_html_has_no_embedded_business_logic(self):
        html = WORKBENCH_INDEX.read_text(encoding="utf-8")
        assert "fetch(" not in html
        assert "/api/v1/qa" not in html
        assert "/api/v1/quiz" not in html