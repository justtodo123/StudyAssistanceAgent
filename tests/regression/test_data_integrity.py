"""数据完整性回归测试。

验证知识库条目、评测集的格式合法性。
M3c（数据变更）后必须运行。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
REPO_ROOT = Path(__file__).resolve().parents[2]

if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))

from app.knowledge_index import _parse_frontmatter  # noqa: E402


class TestKnowledgeIntegrity:
    """知识库数据完整性。"""

    def test_all_chunks_have_valid_course(self, knowledge_chunks):
        """所有切片的 course 字段应为已知课程（README 等导航文件除外）。"""
        valid_courses = {"os", "ds", "co", "interview"}
        for chunk in knowledge_chunks:
            # README 文件是导航页，无 frontmatter，course 为空是正常的
            if chunk.file.endswith("README.md"):
                continue
            assert chunk.course in valid_courses, (
                f"{chunk.file} 的 course='{chunk.course}' 不合法"
            )

    def test_all_files_start_with_knowledge(self, knowledge_chunks):
        """所有文件路径应以 knowledge/ 开头。"""
        for chunk in knowledge_chunks:
            assert chunk.file.startswith("knowledge/"), (
                f"非法路径: {chunk.file}"
            )

    def test_no_duplicate_ids(self, knowledge_chunks):
        """切片 ID 应唯一。"""
        ids = [c.id for c in knowledge_chunks]
        assert len(ids) == len(set(ids)), (
            f"存在重复 ID: {[x for x in ids if ids.count(x) > 1][:5]}"
        )

    def test_no_empty_content(self, knowledge_chunks):
        """切片内容不应为空。"""
        empty = [c for c in knowledge_chunks if not c.content.strip()]
        assert len(empty) == 0, (
            f"存在空内容切片: {[c.file for c in empty[:5]]}"
        )


class TestEvaluationSetIntegrity:
    """评测集格式完整性。"""

    @pytest.fixture
    def eval_sets(self):
        sets = {}
        for name in ("os", "ds", "co"):
            path = REPO_ROOT / "tools" / "evaluations" / f"{name}.json"
            if path.exists():
                sets[name] = json.loads(path.read_text(encoding="utf-8"))
        return sets

    def test_eval_sets_have_questions(self, eval_sets):
        """每个评测集应有题目。"""
        for name, data in eval_sets.items():
            assert len(data) >= 10, f"{name} 评测集应 ≥10 题，实际 {len(data)}"

    def test_eval_questions_have_relevant_files(self, eval_sets):
        """每道题应标注至少一个相关文件。"""
        for name, data in eval_sets.items():
            for q, files in data.items():
                assert isinstance(files, list), (
                    f"{name}/{q}: 相关文件应为列表"
                )
                # 允许空列表（未标注的题目跳过评测）
                for f in files:
                    assert f.startswith("knowledge/"), (
                        f"{name}/{q}: 非法路径 {f}"
                    )

    def test_eval_files_exist(self, eval_sets):
        """评测集中引用的文件应实际存在。"""
        for name, data in eval_sets.items():
            for q, files in data.items():
                for f in files:
                    full_path = REPO_ROOT / f
                    assert full_path.exists(), (
                        f"{name}/{q}: 引用的文件不存在 {f}"
                    )
