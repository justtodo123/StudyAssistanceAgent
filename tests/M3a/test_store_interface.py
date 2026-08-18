"""M3a contract tests for pluggable vector stores."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))


@pytest.mark.m3a
class TestVectorStoreInterface:
    """The SQLite implementation must satisfy the shared store contract."""

    def test_search_returns_list(self, real_vector_store, sample_chunks, sample_vectors):
        real_vector_store.add(sample_chunks, sample_vectors)
        results = real_vector_store.search(
            query_vector=[1.0, 0.0, 0.0, 0.0],
            top_k=3,
        )
        assert isinstance(results, list)
        assert results[0].id == "chunk-1"

    def test_search_empty_on_empty_index(self, real_vector_store):
        results = real_vector_store.search(
            query_vector=[1.0, 0.0, 0.0, 0.0],
            top_k=1,
        )
        assert results == []

    def test_search_respects_top_k(self, real_vector_store, sample_chunks, sample_vectors):
        real_vector_store.add(sample_chunks, sample_vectors)
        results = real_vector_store.search(
            query_vector=[1.0, 0.0, 0.0, 0.0],
            top_k=2,
        )
        assert len(results) == 2

    def test_dimension_compatibility(self, real_vector_store, sample_chunks, sample_vectors):
        real_vector_store.add(sample_chunks, sample_vectors)
        assert real_vector_store.count() == len(sample_chunks)

    def test_duplicate_add_is_idempotent(self, real_vector_store, sample_chunks, sample_vectors):
        real_vector_store.add(sample_chunks, sample_vectors)
        real_vector_store.add(sample_chunks, sample_vectors)
        assert real_vector_store.count() == len(sample_chunks)
        assert real_vector_store.ids() == {chunk.id for chunk in sample_chunks}

    def test_add_upserts_without_dropping_existing_chunks(self, real_vector_store, sample_chunks, sample_vectors):
        real_vector_store.add(sample_chunks[:2], sample_vectors[:2])
        real_vector_store.add(sample_chunks[2:], sample_vectors[2:])
        assert real_vector_store.count() == 3
        assert real_vector_store.ids() == {chunk.id for chunk in sample_chunks}

    def test_threshold_is_applied_before_top_k(self, real_vector_store, sample_chunks, sample_vectors):
        real_vector_store.add(sample_chunks, sample_vectors)
        results = real_vector_store.search(
            query_vector=[1.0, 0.0, 0.0, 0.0],
            top_k=2,
            threshold=0.5,
        )
        assert [chunk.id for chunk in results] == ["chunk-1"]

    def test_query_dimension_mismatch_is_explicit(self, real_vector_store, sample_chunks, sample_vectors):
        real_vector_store.add(sample_chunks, sample_vectors)
        with pytest.raises(ValueError, match="dimension mismatch"):
            real_vector_store.search(query_vector=[1.0, 0.0], top_k=1)


@pytest.mark.m3a
class TestVectorStoreMockContract:
    """Verify the call shape expected by integration code."""

    def test_mock_search_called_with_correct_args(self, mock_vector_store):
        mock_vector_store.search(query_vector=[0.1] * 512, top_k=5)
        mock_vector_store.search.assert_called_once_with(
            query_vector=[0.1] * 512,
            top_k=5,
        )

    def test_mock_count_returns_int(self, mock_vector_store):
        assert isinstance(mock_vector_store.count(), int)
