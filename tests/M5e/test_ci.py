"""Offline CI workflow contract."""

from __future__ import annotations

import pytest


@pytest.mark.m5e
class TestOfflineCiWorkflow:
    def test_workflow_file_exists(self, repo_root):
        path = repo_root / ".github" / "workflows" / "offline-ci.yml"
        assert path.is_file()

    def test_stays_on_offline_bm25(self, workflow_text):
        assert "SA_USE_VECTOR" in workflow_text
        assert "false" in workflow_text
        assert "HF_HUB_OFFLINE" in workflow_text
        assert "TRANSFORMERS_OFFLINE" in workflow_text

    def test_does_not_download_models_or_require_llm(self, workflow_text):
        lowered = workflow_text.lower()
        assert "huggingface-cli" not in lowered
        assert "sentence-transformers" not in lowered
        assert "sa_llm_api_key" not in lowered

    def test_runs_stage_regression_and_eval_smoke(self, workflow_text):
        assert "pytest" in workflow_text
        assert "tests/regression" in workflow_text
        assert "tools/run_evaluation.py --smoke" in workflow_text

    def test_dev_requirements_declare_httpx2_for_testclient(self, repo_root):
        text = (repo_root / "platform" / "requirements-dev.txt").read_text(encoding="utf-8")
        assert "httpx2>=2,<3" in text
