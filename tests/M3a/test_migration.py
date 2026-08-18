"""M3a migration, persistence, and retrieval-consistency tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))

from app.vector_store import LocalVectorStore, SqliteVectorStore, migrate_store  # noqa: E402


@pytest.mark.m3a
class TestMigrationCompleteness:
    def test_chunk_count_preserved(self, knowledge_chunks, tmp_path):
        store = SqliteVectorStore(db_path=tmp_path / "vectors.sqlite3")
        vectors = [[1.0, 0.0] for _ in knowledge_chunks]
        store.replace_all(knowledge_chunks, vectors)
        assert store.count() == len(knowledge_chunks)

    def test_all_files_covered(self, knowledge_chunks, tmp_path):
        store = SqliteVectorStore(db_path=tmp_path / "vectors.sqlite3")
        store.replace_all(knowledge_chunks, [[1.0, 0.0] for _ in knowledge_chunks])
        assert store.ids() == {chunk.id for chunk in knowledge_chunks}

    def test_retrieval_consistency(self, sample_chunks, sample_vectors, tmp_path):
        linear = LocalVectorStore(embedder=None)
        # Explicit vectors keep this test independent of sentence-transformers.
        linear.add(sample_chunks, sample_vectors)
        sqlite = SqliteVectorStore(db_path=tmp_path / "vectors.sqlite3")
        migrate_store(linear, sqlite)

        linear_ids = [chunk.id for chunk in linear.search(query_vector=sample_vectors[0], top_k=3)]
        sqlite_ids = [chunk.id for chunk in sqlite.search(query_vector=sample_vectors[0], top_k=3)]
        assert sqlite_ids == linear_ids


@pytest.mark.m3a
class TestMigrationIdempotency:
    def test_double_build_same_count(self, knowledge_chunks):
        from app.knowledge_index import build_index

        chunks2 = build_index()
        assert len(chunks2) == len(knowledge_chunks)

    def test_ids_unique(self, knowledge_chunks):
        ids = [chunk.id for chunk in knowledge_chunks]
        assert len(ids) == len(set(ids))

    def test_replace_all_is_idempotent(self, sample_chunks, sample_vectors, tmp_path):
        store = SqliteVectorStore(db_path=tmp_path / "vectors.sqlite3")
        store.replace_all(sample_chunks, sample_vectors)
        store.replace_all(sample_chunks, sample_vectors)
        assert store.count() == len(sample_chunks)

    def test_content_change_is_not_treated_as_synced(self, sample_chunks, sample_vectors, tmp_path):
        store = SqliteVectorStore(db_path=tmp_path / "vectors.sqlite3")
        store.replace_all(sample_chunks, sample_vectors)
        changed = [chunk.model_copy(deep=True) for chunk in sample_chunks]
        changed[0].content = "Updated content"
        assert not store.is_synced(changed)

    def test_model_change_is_not_treated_as_synced(self, sample_chunks, sample_vectors, tmp_path):
        path = tmp_path / "vectors.sqlite3"
        SqliteVectorStore(model_name="model-a", db_path=path).replace_all(sample_chunks, sample_vectors)
        reopened = SqliteVectorStore(model_name="model-b", db_path=path)
        assert not reopened.is_synced(sample_chunks)


@pytest.mark.m3a
class TestSqlitePersistence:
    def test_data_survives_reopen(self, sample_chunks, sample_vectors, tmp_path):
        path = tmp_path / "vectors.sqlite3"
        first = SqliteVectorStore(db_path=path)
        first.add(sample_chunks, sample_vectors)
        assert first.count() == 3

        second = SqliteVectorStore(db_path=path)
        assert second.count() == 3
        assert second.ids() == {chunk.id for chunk in sample_chunks}
        assert second.search(query_vector=sample_vectors[1], top_k=1)[0].id == "chunk-2"
