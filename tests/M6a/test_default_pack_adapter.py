"""Real-chain tests for the M6a default Markdown knowledge-pack adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app import config
from app.knowledge_index import build_index_snapshot_cached, materialize_index
from app.protocols import (
    ProtocolValidationError,
    RetrievalIndex,
    RetrievalSnapshot,
    RetrievalSnapshotWriter,
    SourceChunk,
    SourceDescriptor,
    SourceIdentity,
    SourceType,
    validate_source_snapshot,
)
from app.retrieval import MultiRecallService
from app.retrieval_index import DefaultPackRetrievalIndex
from app.source_policy import is_indexable_frontmatter
from app.sources.markdown_pack import MarkdownPackSource


@dataclass
class _SnapshotSource:
    descriptor: SourceDescriptor
    chunks: tuple[SourceChunk, ...]

    def describe(self) -> SourceDescriptor:
        return self.descriptor

    def iter_chunks(self):
        return iter(self.chunks)


def _write_note(root: Path, relative_path: str, body: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "title: Deadlock notes\n"
        "course: os\n"
        "tags: [进程, 同步]\n"
        "difficulty: 中等\n"
        "updated: 2026-08-25\n"
        "---\n\n"
        f"## Deadlock\n{body}\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.m6a
class TestDefaultMarkdownPackSource:
    def test_real_pack_has_portable_deterministic_identity(self, knowledge_root: Path) -> None:
        first = MarkdownPackSource(knowledge_root).materialize()
        second = MarkdownPackSource(knowledge_root).materialize()

        assert first.descriptor.source_id == "knowledge-pack"
        assert first.descriptor.source_type is SourceType.HUMAN_MARKDOWN
        assert first.descriptor.revision
        assert first.descriptor.fingerprint
        assert first.descriptor.generation == second.descriptor.generation
        assert first.chunks
        assert len({chunk.identity.logical_uri for chunk in first.chunks}) <= len(first.chunks)
        assert len({chunk.chunk_id for chunk in first.chunks}) == len(first.chunks)
        assert len({chunk.identity.logical_uri.casefold() for chunk in first.chunks}) == len(
            {chunk.identity.logical_uri for chunk in first.chunks}
        )
        for chunk in first.chunks:
            assert not Path(chunk.identity.logical_uri).is_absolute()
            assert "\\" not in chunk.identity.logical_uri
            assert str(knowledge_root.resolve()) not in repr(chunk)

    def test_relocated_equivalent_pack_keeps_generation_and_legacy_provenance(self, tmp_path: Path) -> None:
        original_root = tmp_path / "first-root"
        relocated_root = tmp_path / "second-root"
        body = "死锁的四个必要条件包括互斥、占有并等待、不可抢占和循环等待。"
        _write_note(original_root, "os/deadlock.md", body)
        _write_note(relocated_root, "os/deadlock.md", body)

        first = MarkdownPackSource(original_root).materialize()
        second = MarkdownPackSource(relocated_root).materialize()
        legacy = materialize_index(relocated_root)

        assert first.descriptor == second.descriptor
        assert [chunk.chunk_id for chunk in first.chunks] == [chunk.chunk_id for chunk in second.chunks]
        assert legacy.generation == second.descriptor.generation
        assert all(chunk.file == "knowledge/os/deadlock.md" for chunk in legacy.chunks)
        assert str(relocated_root.resolve()) not in repr(legacy)

    def test_content_change_and_deletion_publish_new_complete_generation(self, tmp_path: Path) -> None:
        root = tmp_path / "knowledge"
        first_note = _write_note(root, "os/first.md", "死锁需要资源互斥和循环等待。")
        second_note = _write_note(root, "os/second.md", "银行家算法通过安全序列避免死锁。")

        initial = MarkdownPackSource(root).materialize()
        first_note.write_text(first_note.read_text(encoding="utf-8") + "\n补充：资源可被抢占。\n", encoding="utf-8")
        edited = MarkdownPackSource(root).materialize()
        second_note.unlink()
        deleted = MarkdownPackSource(root).materialize()

        assert edited.descriptor.generation != initial.descriptor.generation
        assert deleted.descriptor.generation != edited.descriptor.generation
        assert {chunk.identity.logical_uri for chunk in deleted.chunks} == {"os/first.md"}

    def test_invalid_frontmatter_enums_are_not_indexable(self) -> None:
        assert not is_indexable_frontmatter({"course": "os", "source_type": "unknown"})
        assert not is_indexable_frontmatter({"course": "os", "ingest_status": "unknown"})


@pytest.mark.m6a
class TestDefaultPackRetrievalAdapter:
    def test_adapter_preserves_legacy_chunks_and_contracts(self, knowledge_root: Path) -> None:
        source_snapshot = MarkdownPackSource(knowledge_root).materialize()
        index = DefaultPackRetrievalIndex.from_source_snapshot(source_snapshot)

        assert isinstance(index, RetrievalIndex)
        assert isinstance(index, RetrievalSnapshotWriter)
        assert index.generation == source_snapshot.descriptor.generation
        assert len(index.chunks) == len(source_snapshot.chunks)
        assert all(chunk.id in {source.chunk_id for source in source_snapshot.chunks} for chunk in index.chunks)
        assert all(chunk.file.startswith("knowledge/") for chunk in index.chunks)

    def test_snapshot_replacement_is_complete_and_atomic(self, tmp_path: Path) -> None:
        root = tmp_path / "knowledge"
        _write_note(root, "os/first.md", "第一个完整快照包含死锁知识。")
        first = MarkdownPackSource(root).materialize()
        index = DefaultPackRetrievalIndex.from_source_snapshot(first)

        _write_note(root, "os/second.md", "第二个完整快照包含调度知识。")
        replacement = MarkdownPackSource(root).materialize()
        index.replace_all(RetrievalSnapshot(replacement.descriptor.generation, replacement.chunks))

        assert index.generation == replacement.descriptor.generation
        assert {chunk.file for chunk in index.chunks} == {
            f"knowledge/{chunk.identity.logical_uri}" for chunk in replacement.chunks
        }
        assert len(index.chunks) == len(replacement.chunks)


@pytest.mark.m6a
class TestSourceSnapshotValidation:
    def test_casefold_uri_collision_is_rejected(self) -> None:
        descriptor = SourceDescriptor(
            source_id="reference-pack",
            source_type=SourceType.HUMAN_MARKDOWN,
            revision="r1",
            fingerprint="f1",
            generation="g1",
        )
        source = _SnapshotSource(
            descriptor,
            (
                SourceChunk(SourceIdentity("reference-pack", "os/Deadlock.md"), "h2-0", "first"),
                SourceChunk(SourceIdentity("reference-pack", "os/deadlock.md"), "h2-0", "second"),
            ),
        )

        with pytest.raises(ProtocolValidationError, match="case-fold"):
            validate_source_snapshot(source)

    def test_duplicate_chunk_identity_is_rejected(self) -> None:
        descriptor = SourceDescriptor(
            source_id="reference-pack",
            source_type=SourceType.HUMAN_MARKDOWN,
            revision="r1",
            fingerprint="f1",
            generation="g1",
        )
        chunk = SourceChunk(SourceIdentity("reference-pack", "os/deadlock.md"), "h2-0", "content")
        source = _SnapshotSource(descriptor, (chunk, chunk))

        with pytest.raises(ProtocolValidationError, match="chunk IDs"):
            validate_source_snapshot(source)


@pytest.mark.m6a
class TestGenerationAwareRecall:
    def test_recall_discards_cached_results_when_default_pack_generation_changes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "knowledge"
        _write_note(root, "os/deadlock.md", "死锁的四个必要条件是互斥、占有并等待、不可抢占和循环等待。")
        monkeypatch.setattr(config, "KNOWLEDGE_ROOT", root)
        monkeypatch.setattr("app.knowledge_index._INDEX_CACHE_DIR", tmp_path / "index-cache")
        monkeypatch.setattr(config, "VECTOR_ENABLED", False)
        service = MultiRecallService()

        first, _ = service.recall("死锁", top_k=3)
        first_generation = service._generation
        assert first
        service.recall("死锁", top_k=3)
        assert len(service._result_cache) == 1

        _write_note(root, "os/avoidance.md", "死锁避免算法可通过银行家算法验证安全序列。")
        second, _ = service.recall("银行家算法", top_k=3)

        assert service._generation != first_generation
        assert any(chunk.file == "knowledge/os/avoidance.md" for chunk in second)
        assert len(service._result_cache) == 1

    def test_cached_index_rejects_different_root_even_with_a_shared_cache_location(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first_root = tmp_path / "first"
        second_root = tmp_path / "second"
        _write_note(first_root, "os/first.md", "第一份知识包讨论死锁的必要条件和资源分配。")
        _write_note(second_root, "os/second.md", "第二份知识包讨论进程调度的策略和平均等待时间。")
        monkeypatch.setattr("app.knowledge_index._INDEX_CACHE_DIR", tmp_path / "index-cache")

        first = build_index_snapshot_cached(first_root)
        second = build_index_snapshot_cached(second_root)

        assert first.generation != second.generation
        assert {chunk.file for chunk in second.chunks} == {"knowledge/os/second.md"}
