"""M3a 向量库迁移测试 fixtures。

提供：
- mock_vector_store：模拟新存储引擎
- real_vector_store：真实本地向量存储（跳过未安装场景）
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.fixture
def mock_vector_store():
    """模拟向量存储引擎（用于接口一致性测试）。"""
    store = MagicMock()
    store.search.return_value = []
    store.count.return_value = 0
    store.is_available.return_value = True
    return store


@pytest.fixture
def real_vector_store():
    """真实本地向量存储（如 sentence-transformers 未安装则跳过）。"""
    try:
        from app.vector_store import LocalVectorStore

        return LocalVectorStore()
    except Exception:
        pytest.skip("sentence-transformers 未安装，跳过真实向量存储测试")


@pytest.fixture
def sample_embeddings():
    """示例嵌入向量（512 维，BGE-small-zh 输出维度）。"""
    import random

    random.seed(42)
    return [[random.random() for _ in range(512)] for _ in range(5)]
