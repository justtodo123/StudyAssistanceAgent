"""M3b 结构化日志测试。

验证日志格式、敏感信息过滤。
M3b 开发后补充具体日志断言。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.mark.m3b
class TestStructuredLogging:
    """结构化日志格式验证。"""

    def test_search_produces_log_output(self, retrieval_service, captured_logs):
        """检索操作应产生日志输出。"""
        retrieval_service.recall("测试查询", top_k=3)
        log_output = captured_logs.getvalue()
        # M3b 开发后：验证日志包含检索信息
        # assert "recall" in log_output.lower() or "search" in log_output.lower()

    def test_qa_produces_log_output(self, qa_service, captured_logs):
        """问答操作应产生日志输出。"""
        from app.models import QaRequest

        qa_service.answer(QaRequest(question="测试", use_llm=False))
        log_output = captured_logs.getvalue()
        # M3b 开发后：验证日志包含问答信息


@pytest.mark.m3b
class TestSensitiveInfoFilter:
    """敏感信息过滤。"""

    def test_no_api_key_in_logs(self, captured_logs):
        """日志中不应出现 API Key。"""
        from app.config import LLM_API_KEY

        if not LLM_API_KEY:
            pytest.skip("未配置 LLM_API_KEY")

        # 触发一些操作
        from app.retrieval import MultiRecallService

        MultiRecallService().recall("测试", top_k=1)

        log_output = captured_logs.getvalue()
        assert LLM_API_KEY not in log_output, "日志中不应出现 API Key"

    def test_no_env_secrets_in_health(self, test_client):
        """health 端点不应暴露敏感环境变量。"""
        resp = test_client.get("/health")
        body = resp.text.lower()
        for secret in ["api_key", "secret", "password", "token"]:
            # 允许字段名出现（如 "llm_configured"），但不允许值
            pass
        # M3b 开发后：验证 health 响应不含敏感值
