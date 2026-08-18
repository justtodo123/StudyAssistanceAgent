"""Fixtures for deterministic M3a vector-store tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))

from app.models import RetrievalChunk  # noqa: E402


@pytest.fixture
def mock_vector_store():
    """Mock implementation used to verify the public call contract."""
    store = MagicMock()
    store.search.return_value = []
    store.count.return_value = 0
    store.ids.return_value = set()
    store.is_available.return_value = True
    return store


@pytest.fixture
def sample_chunks():
    """Small stable corpus shared by migration and persistence tests."""
    return [
        RetrievalChunk(
            id="chunk-1",
            file="knowledge/os/process.md",
            title="process",
            course="os",
            content="A process is a program in execution.",
        ),
        RetrievalChunk(
            id="chunk-2",
            file="knowledge/ds/sort.md",
            title="sorting",
            course="ds",
            content="Sorting reorders records by their keys.",
        ),
        RetrievalChunk(
            id="chunk-3",
            file="knowledge/co/cache.md",
            title="cache",
            course="co",
            content="Cache exploits locality to reduce memory latency.",
        ),
    ]


@pytest.fixture
def sample_vectors():
    """Three normalized four-dimensional vectors aligned with sample_chunks."""
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ]


@pytest.fixture
def real_vector_store():
    """SQLite store in memory; no model download is required."""
    from app.vector_store import SqliteVectorStore

    return SqliteVectorStore(db_path=":memory:")


@pytest.fixture
def sample_embeddings():
    """Example 512-dimensional vectors for the legacy dimension contract."""
    import random

    random.seed(42)
    return [[random.random() for _ in range(512)] for _ in range(5)]
