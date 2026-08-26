"""M6a-3 default/combined generation isolation and cache lifecycle tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.combined_snapshot import CombinedSnapshotBuilder
from app.protocols import SourceType
from app.retrieval import MultiRecallService, RetrievalScope
from app.source_config import SourceLimits, StaticSourceConfig

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


def _write_extra(root: Path, content: str) -> None:
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


def _builder(default_root: Path, extra_root: Path) -> CombinedSnapshotBuilder:
    extras = (
        StaticSourceConfig("notes-1", extra_root.resolve(), SourceType.HUMAN_MARKDOWN),
    )
    return CombinedSnapshotBuilder(default_root, extras, SourceLimits(), strict=True)


def test_default_and_combined_generations_are_separated(tmp_path: Path) -> None:
    default_root = tmp_path / "default"
    extra_root = tmp_path / "extra"
    _write_default(default_root)
    _write_extra(extra_root, "A semaphore coordinates concurrent workers.")
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


def test_extra_change_keeps_default_generation_and_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    default_root = tmp_path / "default"
    extra_root = tmp_path / "extra"
    _write_default(default_root)
    _write_extra(extra_root, "A semaphore coordinates concurrent workers.")
    first = _builder(default_root, extra_root).build()
    current = first
    searches = {"bm25": 0}

    class _CountingBm25:
        def __init__(self, chunks):
            searches["bm25"] += 1
            self._chunks = list(chunks)

        def search(self, question: str, top_k: int = 20):
            return self._chunks[:top_k]

    monkeypatch.setattr("app.retrieval.config.VECTOR_ENABLED", False)
    monkeypatch.setattr("app.retrieval.Bm25Search", _CountingBm25)

    def provider(scope: RetrievalScope):
        return current.view(scope)

    recall = MultiRecallService(snapshot_provider=provider)
    default_first, _ = recall.recall(
        "process isolation",
        top_k=3,
        scope=RetrievalScope.DEFAULT_ONLY,
    )
    combined_first, _ = recall.recall(
        "semaphore",
        top_k=3,
        scope=RetrievalScope.DEFAULT_PLUS_EXTRAS,
    )
    assert searches["bm25"] == 2

    default_cached, _ = recall.recall(
        "process isolation",
        top_k=3,
        scope=RetrievalScope.DEFAULT_ONLY,
    )
    assert searches["bm25"] == 2
    assert [chunk.id for chunk in default_cached] == [chunk.id for chunk in default_first]

    _write_extra(extra_root, "A semaphore safely guards a critical section.")
    current = _builder(default_root, extra_root).build()
    assert current.default_generation == first.default_generation
    assert current.generation != first.generation

    default_after, _ = recall.recall(
        "process isolation",
        top_k=3,
        scope=RetrievalScope.DEFAULT_ONLY,
    )
    combined_after, _ = recall.recall(
        "semaphore",
        top_k=3,
        scope=RetrievalScope.DEFAULT_PLUS_EXTRAS,
    )

    assert searches["bm25"] == 3
    assert [chunk.id for chunk in default_after] == [chunk.id for chunk in default_first]
    assert any("critical section" in chunk.content for chunk in combined_after)
    assert not any("critical section" in chunk.content for chunk in combined_first)


def test_concurrent_scope_reads_keep_isolated_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    default_root = tmp_path / "default"
    extra_root = tmp_path / "extra"
    _write_default(default_root)
    _write_extra(extra_root, "A semaphore coordinates concurrent workers.")
    snapshot = _builder(default_root, extra_root).build()
    monkeypatch.setattr("app.retrieval.config.VECTOR_ENABLED", False)

    recall = MultiRecallService(snapshot_provider=snapshot.view)

    def _search(scope: RetrievalScope) -> list[str]:
        results, _ = recall.recall("semaphore", top_k=5, scope=scope)
        return [chunk.file for chunk in results]

    with ThreadPoolExecutor(max_workers=8) as pool:
        default_futures = [
            pool.submit(_search, RetrievalScope.DEFAULT_ONLY) for _ in range(8)
        ]
        combined_futures = [
            pool.submit(_search, RetrievalScope.DEFAULT_PLUS_EXTRAS) for _ in range(8)
        ]
        default_hits = [future.result() for future in default_futures]
        combined_hits = [future.result() for future in combined_futures]

    assert all(not any(path.startswith("extra://") for path in hits) for hits in default_hits)
    assert all(any(path.startswith("extra://") for path in hits) for hits in combined_hits)
    assert all(hits == default_hits[0] for hits in default_hits)
    assert all(hits == combined_hits[0] for hits in combined_hits)
