"""M6a-3 atomic snapshot publication and durable last-good tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.combined_snapshot import CombinedRetrievalSnapshot
from app.models import RetrievalChunk
from app.retrieval import RetrievalScope
from app.snapshot_publisher import (
    CombinedSnapshotPublisher,
    SnapshotPublicationError,
    SnapshotReductionError,
)

pytestmark = pytest.mark.m6a


def _chunk(identifier: str, file: str, content: str = "content") -> RetrievalChunk:
    return RetrievalChunk(
        id=identifier,
        file=file,
        title=identifier,
        course="os",
        content=content,
    )


def _snapshot(
    revision: str,
    *,
    default_count: int = 2,
    include_extra: bool = False,
) -> CombinedRetrievalSnapshot:
    default_chunks = tuple(
        _chunk(f"default-{index}", f"knowledge/note-{index}.md")
        for index in range(default_count)
    )
    combined = default_chunks
    source_ids = ("knowledge-pack",)
    source_generations = (("knowledge-pack", f"default-gen-{revision}"),)
    if include_extra:
        combined += (_chunk("extra-1", "extra://notes-1/week-01.md"),)
        source_ids += ("notes-1",)
        source_generations += (("notes-1", f"extra-gen-{revision}"),)
    from app.snapshot_publisher import _combined_generation

    generation = _combined_generation(source_generations, len(default_chunks), len(combined))
    return CombinedRetrievalSnapshot(
        generation=generation,
        default_generation=f"default-gen-{revision}",
        default_revision=revision,
        default_chunks=default_chunks,
        combined_chunks=combined,
        source_ids=source_ids,
        source_generations=source_generations,
    )


def test_publish_writes_portable_manifest_and_scope_views(tmp_path: Path) -> None:
    snapshot = _snapshot("r1", include_extra=True)
    publisher = CombinedSnapshotPublisher(tmp_path, builder=lambda: snapshot)

    published = publisher.publish()
    manifest = json.loads(
        (tmp_path / f"gen-{snapshot.generation}" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert published == snapshot
    assert (tmp_path / "CURRENT").read_text(encoding="ascii") == f"gen-{snapshot.generation}"
    assert manifest["source_ids"] == ["knowledge-pack", "notes-1"]
    assert str(tmp_path) not in json.dumps(manifest)
    default_generation, default_chunks = publisher.view(RetrievalScope.DEFAULT_ONLY)
    combined_generation, combined_chunks = publisher.view(
        RetrievalScope.DEFAULT_PLUS_EXTRAS
    )
    assert default_generation == snapshot.default_generation
    assert combined_generation == snapshot.generation
    assert default_generation != combined_generation
    assert len(default_chunks) == 2
    assert len(combined_chunks) == 3


def test_new_process_loads_durable_current_without_building(tmp_path: Path) -> None:
    snapshot = _snapshot("r1", include_extra=True)
    CombinedSnapshotPublisher(tmp_path, builder=lambda: snapshot).publish()

    def fail() -> CombinedRetrievalSnapshot:
        raise AssertionError("builder must not run while reading durable CURRENT")

    recovered = CombinedSnapshotPublisher(tmp_path, builder=fail)

    assert recovered.current == snapshot
    assert recovered.view(RetrievalScope.DEFAULT_PLUS_EXTRAS)[0] == snapshot.generation


def test_corrupt_current_falls_back_to_previous_after_restart(tmp_path: Path) -> None:
    first = _snapshot("r1")
    second = _snapshot("r2")
    values = iter((first, second))
    publisher = CombinedSnapshotPublisher(tmp_path, builder=lambda: next(values))
    publisher.publish()
    publisher.publish()
    current_dir = tmp_path / f"gen-{second.generation}"
    (current_dir / "chunks.json").write_text("corrupt", encoding="utf-8")

    recovered = CombinedSnapshotPublisher(tmp_path, builder=lambda: second)

    assert recovered.current == first


def test_failed_rebuild_returns_last_good_without_partial_switch(tmp_path: Path) -> None:
    first = _snapshot("r1")
    calls = 0

    def builder() -> CombinedRetrievalSnapshot:
        nonlocal calls
        calls += 1
        if calls == 1:
            return first
        raise RuntimeError("host root must stay private")

    publisher = CombinedSnapshotPublisher(tmp_path, builder=builder)
    publisher.publish()
    current_before = (tmp_path / "CURRENT").read_text(encoding="ascii")

    assert publisher.publish() == first
    assert (tmp_path / "CURRENT").read_text(encoding="ascii") == current_before
    assert not list(tmp_path.glob(".staging-*"))


def test_first_publication_failure_is_safe(tmp_path: Path) -> None:
    private_root = str(tmp_path / "private")

    def fail() -> CombinedRetrievalSnapshot:
        raise RuntimeError(private_root)

    publisher = CombinedSnapshotPublisher(tmp_path / "cache", builder=fail)

    with pytest.raises(SnapshotPublicationError) as caught:
        publisher.publish()

    assert private_root not in str(caught.value)


def test_large_default_reduction_requires_exact_revision_confirmation(
    tmp_path: Path,
) -> None:
    first = _snapshot("r1", default_count=4)
    reduced = _snapshot("r2", default_count=1)
    values = iter((first, reduced))
    publisher = CombinedSnapshotPublisher(tmp_path, builder=lambda: next(values))
    publisher.publish()

    with pytest.raises(SnapshotReductionError) as caught:
        publisher.publish()

    assert "revision=r2" in str(caught.value)
    assert publisher.current == first

    confirmed = CombinedSnapshotPublisher(
        tmp_path,
        builder=lambda: reduced,
        expected_default_revision="r2",
    )
    assert confirmed.publish() == reduced


def test_removed_extra_is_not_retained_in_previous_generation(tmp_path: Path) -> None:
    with_extra = _snapshot("r1", include_extra=True)
    without_extra = _snapshot("r2")
    values = iter((with_extra, without_extra))
    publisher = CombinedSnapshotPublisher(tmp_path, builder=lambda: next(values))
    publisher.publish()
    old_generation = tmp_path / f"gen-{with_extra.generation}"
    publisher.publish()

    assert not old_generation.exists()
    assert not (tmp_path / "PREVIOUS").exists()
