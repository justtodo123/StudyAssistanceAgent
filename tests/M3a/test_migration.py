"""M3a 数据迁移完整性测试。

验证从旧存储迁移到新存储后的数据一致性。
M3a 开发时实现具体迁移逻辑后，补充实际迁移测试。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.mark.m3a
class TestMigrationCompleteness:
    """迁移完整性验证。"""

    def test_chunk_count_preserved(self, knowledge_chunks):
        """迁移后切片数量应与知识库索引一致。"""
        # 当前基线：knowledge_chunks 的数量
        baseline_count = len(knowledge_chunks)
        assert baseline_count >= 30, f"基线切片数应 ≥30，实际 {baseline_count}"
        # M3a 开发后：新存储的 count() 应 >= baseline_count

    def test_all_files_covered(self, knowledge_chunks):
        """迁移后应覆盖所有知识库文件。"""
        baseline_files = {c.file for c in knowledge_chunks}
        assert len(baseline_files) >= 15, (
            f"基线文件数应 ≥15，实际 {len(baseline_files)}"
        )
        # M3a 开发后：新存储应包含所有 baseline_files

    def test_retrieval_consistency(self, retrieval_service):
        """相同 query 的检索结果文件集合应一致（允许排序微调）。"""
        results, _ = retrieval_service.recall("进程调度", top_k=5)
        result_files = {r.file for r in results}
        assert len(result_files) >= 1, "应至少命中 1 个文件"
        # M3a 开发后：新引擎的 result_files 应与基线一致


@pytest.mark.m3a
class TestMigrationIdempotency:
    """迁移幂等性。"""

    def test_double_build_same_count(self, knowledge_chunks):
        """重复构建索引不应产生重复切片。"""
        from app.knowledge_index import build_index

        chunks2 = build_index()
        assert len(chunks2) == len(knowledge_chunks)

    def test_ids_unique(self, knowledge_chunks):
        """所有切片 ID 应唯一。"""
        ids = [c.id for c in knowledge_chunks]
        assert len(ids) == len(set(ids)), "存在重复 ID"
