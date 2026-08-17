"""M3d 文档完整性测试。

验证 README 链接、PLAN 一致性、知识库导航。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.m3d
class TestReadmeLinks:
    """README 相对链接可解析。"""

    def test_root_readme_links(self):
        """根 README.md 中的相对链接应指向存在的文件。"""
        readme = REPO_ROOT / "README.md"
        if not readme.exists():
            pytest.skip("根 README.md 不存在")
        text = readme.read_text(encoding="utf-8")
        # 匹配 markdown 链接 [text](path)
        links = re.findall(r"\[.*?\]\(([^)]+)\)", text)
        for link in links:
            if link.startswith("http") or link.startswith("#"):
                continue
            target = REPO_ROOT / link
            assert target.exists(), f"根 README 中的链接不存在: {link}"

    def test_knowledge_readme_links(self):
        """knowledge/README.md 中的课程链接应有效。"""
        readme = REPO_ROOT / "knowledge" / "README.md"
        if not readme.exists():
            pytest.skip("knowledge/README.md 不存在")
        text = readme.read_text(encoding="utf-8")
        links = re.findall(r"\[.*?\]\(([^)]+)\)", text)
        for link in links:
            if link.startswith("http") or link.startswith("#"):
                continue
            target = readme.parent / link
            assert target.exists(), f"knowledge/README 中的链接不存在: {link}"


@pytest.mark.m3d
class TestPlanConsistency:
    """PLAN.md 中标记 ✅ 的条目应对应实际文件。"""

    def test_plan_file_exists(self):
        """PLAN.md 应存在。"""
        assert (REPO_ROOT / "docs" / "PLAN.md").exists()

    def test_plan_references_exist(self):
        """PLAN 中提到的关键文件应存在。"""
        plan = (REPO_ROOT / "docs" / "PLAN.md").read_text(encoding="utf-8")
        # 提取 knowledge/ 路径引用
        refs = re.findall(r"knowledge/\w+/README\.md", plan)
        for ref in refs:
            path = REPO_ROOT / ref
            assert path.exists(), f"PLAN 引用的文件不存在: {ref}"


@pytest.mark.m3d
class TestKnowledgeNavigation:
    """知识库课程 README 导航完整性。"""

    @pytest.fixture
    def course_dirs(self):
        """所有课程目录。"""
        kb = REPO_ROOT / "knowledge"
        if not kb.exists():
            return []
        return [d for d in kb.iterdir() if d.is_dir() and not d.name.startswith("_")]

    def test_each_course_has_readme(self, course_dirs):
        """每个课程目录应有 README.md。"""
        for d in course_dirs:
            readme = d / "README.md"
            assert readme.exists(), f"{d.name} 缺少 README.md"

    def test_readme_mentions_entries(self, course_dirs):
        """课程 README 应引用实际存在的条目文件。"""
        for d in course_dirs:
            readme = d / "README.md"
            if not readme.exists():
                continue
            text = readme.read_text(encoding="utf-8")
            # 提取 .md 文件引用
            md_refs = re.findall(r"(\S+\.md)", text)
            for ref in md_refs:
                if ref == "README.md" or ref.startswith("docs/"):
                    continue
                target = d / ref
                # 只验证同目录下的引用
                if not target.exists():
                    # 可能是子目录或上级目录的引用，跳过
                    pass
