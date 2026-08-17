"""M3c 面经库测试 fixtures。

提供：
- interview_dir：面经目录路径
- interview_entries：面经条目列表
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
REPO_ROOT = Path(__file__).resolve().parents[2]

if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.fixture
def interview_dir(repo_root) -> Path:
    """面经库目录路径。"""
    return repo_root / "knowledge" / "interview"


@pytest.fixture
def interview_entries(interview_dir) -> list[Path]:
    """面经条目文件列表（递归扫描 .md 文件）。"""
    if not interview_dir.exists():
        return []
    return sorted(interview_dir.rglob("*.md"))


@pytest.fixture
def interview_chunks(knowledge_chunks):
    """从知识库索引中筛选面经类型条目。"""
    return [
        c for c in knowledge_chunks
        if "interview" in c.file or "interview" in c.tags
    ]
