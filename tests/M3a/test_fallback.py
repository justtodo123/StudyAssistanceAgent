"""M3a 降级路径测试。

验证新存储不可用时的自动降级行为。
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.mark.m3a
class TestVectorFallback:
    """向量存储降级路径。"""

    def test_keyword_only_when_vector_disabled(self):
        """禁用向量时应降级为纯关键词检索。"""
        from app.retrieval import MultiRecallService, _VectorHolder

        # 重置惰性单例缓存 + 禁用向量
        _VectorHolder._loaded = False
        _VectorHolder._store = None
        with patch("app.config.VECTOR_ENABLED", False):
            service = MultiRecallService()
            results, mode = service.recall("进程调度", top_k=3)
            assert mode == "keyword-only"
            assert len(results) >= 1, "纯关键词检索仍应返回结果"

    def test_fallback_returns_results(self):
        """降级模式下检索不应为空。"""
        from app.retrieval import MultiRecallService, _VectorHolder

        _VectorHolder._loaded = False
        _VectorHolder._store = None
        with patch("app.config.VECTOR_ENABLED", False):
            service = MultiRecallService()
            for query in ["死锁", "快速排序", "Cache 替换"]:
                results, _ = service.recall(query, top_k=3)
                assert len(results) >= 1, f"降级检索不应为空: {query}"

    def test_fallback_preserves_source_paths(self):
        """降级模式返回的结果路径仍以 knowledge/ 开头。"""
        from app.retrieval import MultiRecallService, _VectorHolder

        _VectorHolder._loaded = False
        _VectorHolder._store = None
        with patch("app.config.VECTOR_ENABLED", False):
            service = MultiRecallService()
            results, _ = service.recall("虚拟内存", top_k=3)
            for r in results:
                assert r.file.startswith("knowledge/")
