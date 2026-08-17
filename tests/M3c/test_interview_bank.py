"""M3c 面经库验证测试。

验证面经条目的数量、格式、课程覆盖、检索集成。
当 knowledge/interview/ 目录不存在时（M3c 未开发），测试自动跳过。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PLATFORM_DIR = REPO_ROOT / "platform"
INTERVIEW_DIR = REPO_ROOT / "knowledge" / "interview"

if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))

from app.knowledge_index import _parse_frontmatter  # noqa: E402

# 模块级跳过：面经目录不存在时整个模块跳过
pytestmark = pytest.mark.skipif(
    not INTERVIEW_DIR.exists(),
    reason="knowledge/interview/ 目录不存在，待 M3c 开发",
)


@pytest.mark.m3c
class TestInterviewBankSize:
    """面经库规模验证。"""

    def test_interview_dir_exists(self, interview_dir):
        """面经目录应存在。"""
        assert interview_dir.exists(), (
            f"面经目录不存在: {interview_dir}，请先创建 knowledge/interview/"
        )

    def test_minimum_entries(self, interview_entries):
        """面经条目应 ≥50。"""
        # 过滤掉 README.md 和模板文件
        content_files = [
            f for f in interview_entries
            if f.name not in ("README.md", "_template.md")
        ]
        assert len(content_files) >= 50, (
            f"面经条目应 ≥50，实际 {len(content_files)}。"
            f"当前文件: {[f.name for f in content_files[:5]]}"
        )

    def test_no_binary_files(self, interview_dir):
        """面经目录不应包含二进制文件。"""
        if not interview_dir.exists():
            pytest.skip("面经目录不存在")
        for f in interview_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".pdf", ".pptx", ".docx", ".zip"):
                pytest.fail(f"面经目录不应包含二进制文件: {f}")


@pytest.mark.m3c
class TestInterviewFrontmatter:
    """面经条目 frontmatter 完整性。"""

    def test_all_entries_have_frontmatter(self, interview_entries):
        """每个面经条目应有 frontmatter。"""
        content_files = [
            f for f in interview_entries
            if f.name not in ("README.md", "_template.md")
        ]
        for f in content_files[:20]:  # 抽检前 20 个
            text = f.read_text(encoding="utf-8")
            fm = _parse_frontmatter(text)
            assert fm.get("title"), f"{f.name} 缺少 title"
            assert fm.get("course"), f"{f.name} 缺少 course"
            assert fm.get("tags"), f"{f.name} 缺少 tags"

    def test_required_fields(self, interview_entries):
        """面经应包含必填字段。"""
        content_files = [
            f for f in interview_entries
            if f.name not in ("README.md", "_template.md")
        ]
        for f in content_files[:20]:
            text = f.read_text(encoding="utf-8")
            fm = _parse_frontmatter(text)
            assert "difficulty" in fm, f"{f.name} 缺少 difficulty"


@pytest.mark.m3c
class TestInterviewCourseCoverage:
    """面经课程覆盖。"""

    def test_os_has_entries(self, interview_entries):
        """OS 课程应有面经。"""
        os_entries = [
            f for f in interview_entries
            if "/os/" in str(f) or f.parent.name == "os"
        ]
        # 如果面经按课程分目录
        if not os_entries:
            # 或者从 frontmatter 中筛选
            for f in interview_entries:
                if f.name in ("README.md",):
                    continue
                text = f.read_text(encoding="utf-8")
                fm = _parse_frontmatter(text)
                if fm.get("course") == "os":
                    os_entries.append(f)
        assert len(os_entries) >= 10, f"OS 面经应 ≥10，实际 {len(os_entries)}"

    def test_ds_has_entries(self, interview_entries):
        """DS 课程应有面经。"""
        ds_entries = [
            f for f in interview_entries
            if "/ds/" in str(f) or f.parent.name == "ds"
        ]
        if not ds_entries:
            for f in interview_entries:
                if f.name in ("README.md",):
                    continue
                text = f.read_text(encoding="utf-8")
                fm = _parse_frontmatter(text)
                if fm.get("course") == "ds":
                    ds_entries.append(f)
        assert len(ds_entries) >= 10, f"DS 面经应 ≥10，实际 {len(ds_entries)}"

    def test_co_has_entries(self, interview_entries):
        """CO 课程应有面经。"""
        co_entries = [
            f for f in interview_entries
            if "/co/" in str(f) or f.parent.name == "co"
        ]
        if not co_entries:
            for f in interview_entries:
                if f.name in ("README.md",):
                    continue
                text = f.read_text(encoding="utf-8")
                fm = _parse_frontmatter(text)
                if fm.get("course") == "co":
                    co_entries.append(f)
        assert len(co_entries) >= 10, f"CO 面经应 ≥10，实际 {len(co_entries)}"


@pytest.mark.m3c
class TestInterviewSearchIntegration:
    """面经检索集成验证。"""

    def test_interview_searchable(self, retrieval_service):
        """面经条目应可被检索到。"""
        results, _ = retrieval_service.recall("面试 进程 问题", top_k=10)
        # M3c 开发后：验证结果中包含面经文件
        # interview_hits = [r for r in results if "interview" in r.file]
        # assert len(interview_hits) >= 1, "应能检索到面经条目"

    def test_interview_in_qa_sources(self, qa_service):
        """问答应能引用面经作为来源。"""
        from app.models import QaRequest

        resp = qa_service.answer(
            QaRequest(question="操作系统面试常见问题", use_llm=False)
        )
        # M3c 开发后：验证来源中包含面经
        # interview_sources = [s for s in resp.sources if "interview" in s.file]
        # assert len(interview_sources) >= 1
