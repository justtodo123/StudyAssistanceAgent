"""Fixtures for M5e reproducible delivery tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def workflow_text(repo_root: Path) -> str:
    path = repo_root / ".github" / "workflows" / "offline-ci.yml"
    return path.read_text(encoding="utf-8")