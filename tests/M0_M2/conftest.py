"""M0-M2 基线测试 fixtures。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 确保根 conftest 的路径设置生效
PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))
