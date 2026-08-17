"""根 conftest.py — 跨阶段共享 fixtures 与工具函数。

设计原则：
- 提供 app_client、knowledge_chunks 等公共 fixture
- 各阶段 conftest（M3a/M3b/M3c）仅 import 本文件，不互相依赖
- 新增阶段只需在子目录建 conftest.py，无需修改本文件
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator

import pytest

# ── 路径设置 ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_DIR = REPO_ROOT / "platform"

# 确保 platform/app 可 import
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


# ── 通用 Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """仓库根目录路径。"""
    return REPO_ROOT


@pytest.fixture(scope="session")
def knowledge_root(repo_root: Path) -> Path:
    """知识库根目录路径。"""
    return repo_root / "knowledge"


@pytest.fixture(scope="session")
def platform_dir() -> Path:
    """platform/ 目录路径。"""
    return PLATFORM_DIR


@pytest.fixture(scope="session")
def knowledge_chunks():
    """构建知识库索引（session 级，避免重复构建）。"""
    from app.knowledge_index import build_index

    return build_index()


@pytest.fixture(scope="session")
def retrieval_service():
    """多路召回服务实例（session 级）。"""
    from app.retrieval import MultiRecallService

    return MultiRecallService()


@pytest.fixture(scope="session")
def qa_service():
    """问答服务实例（session 级）。"""
    from app.qa import QaService

    return QaService()


@pytest.fixture(scope="session")
def quiz_service():
    """测验生成服务实例（session 级）。"""
    from app.quiz import QuizService

    return QuizService()


@pytest.fixture(scope="session")
def review_plan_service():
    """复习计划服务实例（session 级）。"""
    from app.review_plan import ReviewPlanService

    return ReviewPlanService()


@pytest.fixture
def isolated_scheduler(tmp_path):
    """使用临时目录的复习排程服务（函数级隔离）。"""
    from unittest.mock import patch

    from app.review_scheduler import ReviewSchedulerService

    history_path = tmp_path / "review_history.json"
    with patch("app.review_scheduler._HISTORY_PATH", history_path):
        yield ReviewSchedulerService()


@pytest.fixture(scope="session")
def test_client():
    """FastAPI 测试客户端（session 级）。"""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


# ── 工具函数 ──────────────────────────────────────────────────────────────────


def assert_valid_knowledge_path(file_path: str) -> None:
    """断言文件路径是合法的知识库路径。"""
    assert file_path.startswith("knowledge/"), f"非法知识库路径: {file_path}"
    assert file_path.endswith(".md"), f"非 Markdown 文件: {file_path}"


def assert_valid_course(file_path: str, expected_course: str) -> None:
    """断言文件属于指定课程目录。"""
    assert f"knowledge/{expected_course}/" in file_path, (
        f"文件 {file_path} 不属于课程 {expected_course}"
    )


COURSES = ("os", "ds", "co")
