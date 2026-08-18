"""M4 fixtures: keep retrieval checks deterministic without model downloads."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def disable_optional_vector_encoder():
    """Use the offline BM25 path for M4 retrieval assertions."""
    from app import config

    previous = config.VECTOR_ENABLED
    config.VECTOR_ENABLED = False
    try:
        yield
    finally:
        config.VECTOR_ENABLED = previous
