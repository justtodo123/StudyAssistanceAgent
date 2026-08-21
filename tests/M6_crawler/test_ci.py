"""Offline CI contract for crawler P0."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.m6_crawler

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "offline-ci.yml"


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


class TestCrawlerOfflineCi:
    def test_workflow_installs_crawler_requirements(self, workflow_text: str) -> None:
        assert "tools/crawler/requirements.txt" in workflow_text

    def test_crawler_job_runs_marker_offline(self, workflow_text: str) -> None:
        assert "crawler-offline" in workflow_text
        assert "tests/M6_crawler" in workflow_text
        assert 'm6_crawler and not online' in workflow_text

    def test_online_smoke_is_not_default(self, workflow_text: str) -> None:
        assert "crawler-online-smoke" in workflow_text
        assert "workflow_dispatch" in workflow_text
        assert "crawler_online_smoke" in workflow_text
        offline_job = workflow_text.split("crawler-online-smoke:")[0]
        assert "CRAWLER_ONLINE: \"true\"" not in offline_job
        assert "CRAWLER_ONLINE: 'true'" not in offline_job

    def test_crawler_failure_is_named(self, workflow_text: str) -> None:
        assert "crawler-offline failed" in workflow_text or "Crawler offline tests failed" in workflow_text