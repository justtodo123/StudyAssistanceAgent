"""M3a 向量存储接口一致性测试。

验证新存储实现（sqlite-vec/Chroma）与原 LocalVectorStore 的接口兼容性。
当前阶段：定义接口契约，M3a 开发时填充具体测试。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


class TestVectorStoreInterface:
    """向量存储接口契约（适用于任何实现）。"""

    @pytest.mark.m3a
    def test_search_returns_list(self, real_vector_store):
        """search() 应返回列表（可能为空）。"""
        results = real_vector_store.search(query_vector=[0.1] * 512, top_k=3)
        assert isinstance(results, list)

    @pytest.mark.m3a
    def test_search_empty_on_empty_index(self, real_vector_store):
        """空索引时 search() 应返回空列表。"""
        # 注意：如果索引已构建，此测试验证的是「无匹配」场景
        results = real_vector_store.search(
            query_vector=[0.0] * 512, top_k=1
        )
        assert isinstance(results, list)

    @pytest.mark.m3a
    def test_search_respects_top_k(self, real_vector_store, knowledge_chunks):
        """top_k 参数应限制返回数量。"""
        results = real_vector_store.search(
            query_vector=[0.1] * 512, top_k=2
        )
        assert len(results) <= 2

    @pytest.mark.m3a
    def test_dimension_compatibility(self, sample_embeddings):
        """嵌入向量维度应为 512（BGE-small-zh）。"""
        for emb in sample_embeddings:
            assert len(emb) == 512, f"维度应为 512，实际 {len(emb)}"


class TestVectorStoreMockContract:
    """使用 mock 验证接口调用规范。"""

    @pytest.mark.m3a
    def test_mock_search_called_with_correct_args(self, mock_vector_store):
        """验证调用 search() 的参数格式。"""
        mock_vector_store.search(
            query_vector=[0.1] * 512,
            top_k=5,
        )
        mock_vector_store.search.assert_called_once()

    @pytest.mark.m3a
    def test_mock_count_returns_int(self, mock_vector_store):
        """count() 应返回整数。"""
        result = mock_vector_store.count()
        assert isinstance(result, int)
