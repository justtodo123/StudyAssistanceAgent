"""M3b 可观测性测试 fixtures。

提供：
- captured_logs：捕获日志输出
- metrics_collector：模拟指标收集器
"""

from __future__ import annotations

import json
import logging
import sys
from io import StringIO
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.fixture
def captured_logs():
    """捕获日志输出到字符串缓冲区。"""
    logger = logging.getLogger("app")
    handler = logging.StreamHandler(StringIO())
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    yield handler.stream
    logger.removeHandler(handler)


@pytest.fixture
def log_records():
    """收集日志记录对象。"""
    records = []
    logger = logging.getLogger("app")

    class Collector(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = Collector()
    logger.addHandler(handler)
    yield records
    logger.removeHandler(handler)
