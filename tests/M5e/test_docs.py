"""Delivery docs cover start, cache, baselines, and the demo tool chain."""

from __future__ import annotations

import pytest


@pytest.mark.m5e
class TestDeliveryDocs:
    def test_baselines_record_cold_warm_and_session(self, repo_root):
        text = (repo_root / "docs" / "baselines.md").read_text(encoding="utf-8")
        assert "冷启动" in text
        assert "热启动" in text
        assert "学习会话" in text

    def test_platform_docs_explain_bge_cache_and_offline(self, repo_root):
        text = (repo_root / "platform" / "README.md").read_text(encoding="utf-8")
        assert "HF_HUB_OFFLINE" in text
        assert "huggingface" in text.lower() or "HF_HOME" in text
        assert "SA_USE_VECTOR" in text

    def test_demo_and_interview_include_tool_chain(self, repo_root):
        demo = (repo_root / "docs" / "demo.md").read_text(encoding="utf-8")
        interview = (repo_root / "docs" / "interview" / "README.md").read_text(encoding="utf-8")
        for text in (demo, interview):
            assert "qa" in text.lower()
            assert "quiz" in text.lower()
            assert "review-log" in text.lower()
        assert "python tools/start_local.py" in demo