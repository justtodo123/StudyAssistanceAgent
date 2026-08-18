"""Structured logging and sensitive-data redaction assertions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


def _records(log_output: str) -> list[dict]:
    return [json.loads(line) for line in log_output.splitlines() if line.strip()]


@pytest.mark.m3b
class TestStructuredLogging:
    def test_search_produces_log_output(self, retrieval_service, captured_logs):
        retrieval_service.recall("\u6d4b\u8bd5\u67e5\u8be2", top_k=3)
        records = _records(captured_logs.getvalue())
        search_records = [record for record in records if record.get("event") == "search"]
        assert search_records
        assert search_records[-1]["duration_ms"] >= 0
        assert search_records[-1]["result_count"] >= 0

    def test_qa_produces_log_output(self, qa_service, captured_logs):
        from app.models import QaRequest

        qa_service.answer(QaRequest(question="\u6d4b\u8bd5", use_llm=False))
        records = _records(captured_logs.getvalue())
        qa_records = [record for record in records if record.get("event") == "qa"]
        assert qa_records
        assert qa_records[-1]["duration_ms"] >= 0
        assert qa_records[-1]["result_count"] >= 0


@pytest.mark.m3b
class TestSensitiveInfoFilter:
    def test_no_api_key_in_logs(self, captured_logs):
        from app.config import LLM_API_KEY
        from app.retrieval import MultiRecallService

        MultiRecallService().recall("\u6d4b\u8bd5", top_k=1)
        log_output = captured_logs.getvalue()
        if LLM_API_KEY:
            assert LLM_API_KEY not in log_output
        assert "authorization" not in log_output.lower()

    def test_no_env_secrets_in_health(self, test_client):
        response = test_client.get("/health")
        body = response.text.lower()
        data = response.json()
        for secret_field in ("api_key", "secret", "password", "token"):
            assert secret_field not in data
            assert secret_field not in body
        assert "authorization" not in body
