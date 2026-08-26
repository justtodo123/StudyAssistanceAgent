"""M6a-3 combined source scope and retrieval-isolation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.combined_snapshot import CombinedSnapshotBuilder
from app.protocols import SourceType
from app.retrieval import MultiRecallService, RetrievalScope
from app.source_config import SourceLimits, StaticSourceConfig
from app.sources.static_markdown import SourceContentError

pytestmark = pytest.mark.m6a


def _write_default(root: Path) -> None:
    path = root / "os" / "process.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "tags: [process]\n"
        "course: os\n"
        "difficulty: basic\n"
        "updated: 2026-08-26\n"
        "---\n\n"
        "# Process\n\n"
        "## Process isolation\n\n"
        "A process owns resources and an independent virtual address space.\n",
        encoding="utf-8",
    )


def _write_extra(root: Path, content: str = "A semaphore coordinates concurrent workers.") -> None:
    path = root / "week-01.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "source_type: human_markdown\n"
        "ingest_status: approved\n"
        "course: os\n"
        "tags: [semaphore]\n"
        "difficulty: basic\n"
        "updated: 2026-08-26\n"
        "---\n\n"
        "## Semaphore\n\n"
        f"{content}\n",
        encoding="utf-8",
    )


def _builder(default_root: Path, *extras: Path, strict: bool = True) -> CombinedSnapshotBuilder:
    configs = tuple(
        StaticSourceConfig(f"notes-{index}", root.resolve(), SourceType.HUMAN_MARKDOWN)
        for index, root in enumerate(extras, start=1)
    )
    return CombinedSnapshotBuilder(default_root, configs, SourceLimits(), strict=strict)


def test_combined_snapshot_exposes_atomic_scope_views(tmp_path: Path) -> None:
    default_root = tmp_path / "default"
    extra_root = tmp_path / "extra"
    _write_default(default_root)
    _write_extra(extra_root)

    snapshot = _builder(default_root, extra_root).build()
    default_generation, default_chunks = snapshot.view(RetrievalScope.DEFAULT_ONLY)
    combined_generation, combined_chunks = snapshot.view(
        RetrievalScope.DEFAULT_PLUS_EXTRAS
    )

    assert default_generation == snapshot.default_generation
    assert combined_generation == snapshot.generation
    assert default_generation != combined_generation
    assert len(default_chunks) == 1
    assert len(combined_chunks) == 2
    assert all(chunk.file.startswith("knowledge/") for chunk in default_chunks)
    assert combined_chunks[-1].file == "extra://notes-1/week-01.md"
    assert snapshot.source_ids == ("knowledge-pack", "notes-1")


def test_non_strict_mode_omits_a_failed_whole_source(tmp_path: Path) -> None:
    default_root = tmp_path / "default"
    valid_root = tmp_path / "valid"
    invalid_root = tmp_path / "invalid"
    _write_default(default_root)
    _write_extra(valid_root)
    invalid_root.mkdir()

    snapshot = _builder(default_root, valid_root, invalid_root, strict=False).build()

    assert snapshot.source_ids == ("knowledge-pack", "notes-1")
    assert all("notes-2" not in chunk.file for chunk in snapshot.combined_chunks)


def test_strict_mode_rejects_the_complete_candidate(tmp_path: Path) -> None:
    default_root = tmp_path / "default"
    invalid_root = tmp_path / "invalid"
    _write_default(default_root)
    invalid_root.mkdir()

    with pytest.raises(SourceContentError):
        _builder(default_root, invalid_root, strict=True).build()


def test_scope_and_generation_isolate_recall_cache(tmp_path: Path) -> None:
    default_root = tmp_path / "default"
    extra_root = tmp_path / "extra"
    _write_default(default_root)
    _write_extra(extra_root)
    first = _builder(default_root, extra_root).build()
    current = first
    calls: list[RetrievalScope] = []

    def provider(scope: RetrievalScope):
        calls.append(scope)
        return current.view(scope)

    recall = MultiRecallService(snapshot_provider=provider)
    default_results, _ = recall.recall(
        "semaphore",
        top_k=5,
        scope=RetrievalScope.DEFAULT_ONLY,
    )
    extra_results, _ = recall.recall(
        "semaphore",
        top_k=5,
        scope=RetrievalScope.DEFAULT_PLUS_EXTRAS,
    )
    cached_results, _ = recall.recall(
        "semaphore",
        top_k=5,
        scope=RetrievalScope.DEFAULT_PLUS_EXTRAS,
    )

    assert not any(chunk.file.startswith("extra://") for chunk in default_results)
    assert any(chunk.file.startswith("extra://") for chunk in extra_results)
    assert [chunk.id for chunk in cached_results] == [chunk.id for chunk in extra_results]
    assert calls == [
        RetrievalScope.DEFAULT_ONLY,
        RetrievalScope.DEFAULT_PLUS_EXTRAS,
        RetrievalScope.DEFAULT_PLUS_EXTRAS,
    ]

    _write_extra(extra_root, "A semaphore safely guards a critical section and shared state.")
    current = _builder(default_root, extra_root).build()
    refreshed, _ = recall.recall(
        "critical section",
        top_k=5,
        scope=RetrievalScope.DEFAULT_PLUS_EXTRAS,
    )
    assert current.generation != first.generation
    assert any("critical section" in chunk.content for chunk in refreshed)
