"""M6b fixtures: keep preview retrieval offline and BM25-only."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def disable_optional_vector_encoder():
    """Force BM25-only preview retrieval without local embedding models."""
    from app import config
    from app.retrieval import _VectorHolder

    previous_use = config.USE_VECTOR
    previous_enabled = config.VECTOR_ENABLED
    previous_env = {
        "SA_USE_VECTOR": os.environ.get("SA_USE_VECTOR"),
        "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE"),
        "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE"),
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