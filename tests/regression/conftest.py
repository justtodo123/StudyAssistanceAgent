"""回归测试 fixtures。

回归套件在每阶段开发完成后运行，确保新增功能不破坏历史链路。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.fixture(scope="session", autouse=True)
def disable_optional_vector_encoder():
    """Force regression retrieval to remain offline and BM25-only."""
    from app import config
    from app.retrieval import _VectorHolder

    previous_use = config.USE_VECTOR
    previous_enabled = config.VECTOR_ENABLED
    previous_env = {
        key: os.environ.get(key)
        for key in ("SA_USE_VECTOR", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
    }
    config.USE_VECTOR = False
    config.VECTOR_ENABLED = False
    os.environ["SA_USE_VECTOR"] = "false"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    _VectorHolder.reset()
    try:
        yield
    finally:
        config.USE_VECTOR = previous_use
        config.VECTOR_ENABLED = previous_enabled
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        _VectorHolder.reset()
