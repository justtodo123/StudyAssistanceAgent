"""回归测试 fixtures。

回归套件在每阶段开发完成后运行，确保新增功能不破坏历史链路。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))
