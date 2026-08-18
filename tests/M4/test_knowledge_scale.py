"""M4 课程知识库规模与导航测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.knowledge_index import _parse_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = REPO_ROOT / "knowledge"
COURSES = ("os", "ds", "co")
MIN_ENTRIES = 20


@pytest.mark.m4
class TestCourseKnowledgeScale:
    """三门课程达到 M4 规模门槛。"""

    @pytest.mark.parametrize("course", COURSES)
    def test_course_has_at_least_twenty_entries(self, course: str):
        entries = sorted((KNOWLEDGE_ROOT / course).glob("*.md"))
        entries = [path for path in entries if path.name != "README.md"]
        assert len(entries) >= MIN_ENTRIES, (
            f"{course} 条目应 >= {MIN_ENTRIES}，实际 {len(entries)}"
        )

    @pytest.mark.parametrize("course", COURSES)
    def test_course_entries_have_required_frontmatter(self, course: str):
        entries = sorted((KNOWLEDGE_ROOT / course).glob("*.md"))
        entries = [path for path in entries if path.name != "README.md"]
        for path in entries:
            frontmatter = _parse_frontmatter(path.read_text(encoding="utf-8"))
            for field in ("title", "course", "tags", "difficulty", "updated"):
                assert frontmatter.get(field), f"{path} 缺少 frontmatter: {field}"
            assert frontmatter["course"] == course, f"{path} course 不匹配"


@pytest.mark.m4
class TestCourseNavigation:
    """课程 README 覆盖全部实际条目。"""

    @pytest.mark.parametrize("course", COURSES)
    def test_course_readme_links_every_entry(self, course: str):
        course_dir = KNOWLEDGE_ROOT / course
        readme = (course_dir / "README.md").read_text(encoding="utf-8")
        entries = [path for path in course_dir.glob("*.md") if path.name != "README.md"]
        for path in entries:
            assert f"({path.name})" in readme, f"{course}/README.md 未链接 {path.name}"


@pytest.mark.m4
class TestEvaluationCoverage:
    """新增评测集引用必须指向实际知识条目。"""

    @pytest.mark.parametrize("course", COURSES)
    def test_evaluation_references_exist(self, course: str):
        path = REPO_ROOT / "tools" / "evaluations" / f"{course}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data, f"{path} 不应为空"
        for question, files in data.items():
            assert question.strip(), f"{path} 存在空问题"
            for relative in files:
                assert (REPO_ROOT / relative).exists(), (
                    f"{course} 评测问题引用不存在文件: {relative}"
                )
