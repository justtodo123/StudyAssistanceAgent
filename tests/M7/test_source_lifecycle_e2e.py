"""M7 source lifecycle, retrieval, provenance, restart, and deletion acceptance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.source_delete import MIN_AUDIT_RETENTION_DAYS, UserSourceDeleteService
from app.source_registry import (
    SourceActorType,
    SourceLifecycleErrorCode,
    SourceLifecycleException,
    SourceLifecycleService,
    SourceLifecycleState,
    SqliteSourceRegistry,
    generate_uuid7,
)
from app.user_source_search import UserSourceSearchService, ensure_user_provenance, public_uri
from app.source_offline import UserSourceOfflineGuard
from app.user_source_snapshot import UserSourceSnapshotPublisher
from app.user_source_sync import SYNC_RUN_SUCCESS, UserSourceSyncService
from app.user_source_vector import HashVectorEmbedder
from tests.M7.real_fixtures import fixture_bytes

pytestmark = pytest.mark.m7

SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
OWNER = "principal-owner"
OTHER = "principal-other"
CORRELATION = "corr-m7-lifecycle-e2e"


class _Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def _write_docs(root: Path, texts: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (root / name).write_text(text, encoding="utf-8")


def _register(tmp_path: Path) -> tuple[SourceLifecycleService, Path]:
    lifecycle = SourceLifecycleService(
        SqliteSourceRegistry(tmp_path / "registry.sqlite3"),
        source_id_factory=lambda: SOURCE_ID,
    )
    lifecycle.register_source(
        owner_principal_id=OWNER,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION,
        source_id=SOURCE_ID,
    )
    return lifecycle, tmp_path / "source"


def _sync(
    service: UserSourceSyncService,
    source_root: Path,
    *,
    expected_version: int,
    strategy: str = "FULL",
):
    return service.request_sync(
        principal_id=OWNER,
        source_id=SOURCE_ID,
        request_id=generate_uuid7(),
        expected_version=expected_version,
        source_root=source_root,
        correlation_id=CORRELATION,
        strategy=strategy,
    )


def test_real_source_full_incremental_restart_and_provenance(tmp_path: Path) -> None:
    lifecycle, source_root = _register(tmp_path)
    cache_root = tmp_path / "cache"
    offline = UserSourceOfflineGuard(
        cache_root,
        lifecycle,
        vector_embedder=HashVectorEmbedder(),
    )
    sync = UserSourceSyncService(
        cache_root,
        lifecycle,
        publisher=offline._snapshots,
        offline=offline,
        sleeper=lambda _delay: None,
    )
    _write_docs(source_root, {"lesson.md": "# 进程调度\n\n唯一术语 FULL-原文"})

    first_run = _sync(sync, source_root, expected_version=1)
    record = lifecycle.get_source(principal_id=OWNER, source_id=SOURCE_ID)
    assert first_run.status == SYNC_RUN_SUCCESS
    assert record.state is SourceLifecycleState.READY
    assert record.published_generation == first_run.candidate_generation
    assert record.published_revision_no == 1

    publisher = sync._publisher
    snapshot = publisher.load_snapshot(SOURCE_ID, generation=first_run.candidate_generation)
    assert snapshot is not None
    assert snapshot.document_count == 1
    assert snapshot.documents[0].source_id == SOURCE_ID
    assert snapshot.documents[0].chunks()[0].document_id == snapshot.documents[0].document_id

    delete = UserSourceDeleteService(cache_root, lifecycle, publisher=publisher)
    search = UserSourceSearchService(
        cache_root,
        lifecycle,
        snapshot_publisher=publisher,
        delete_service=delete,
        vector_embedder=HashVectorEmbedder(),
    )
    delete.surfaces.seed(
        SOURCE_ID,
        generation=first_run.candidate_generation,
        documents=tuple(
            {
                "logical_uri": document.logical_uri,
                "document_id": document.document_id,
                "chunk_id": chunk.chunk_id,
            }
            for document in snapshot.documents
            for chunk in document.chunks()
        ),
        provenance=tuple(
            {
                "document_id": document.document_id,
                "logical_uri": document.logical_uri,
                "origin_kind": "original",
                "derived_from_document_ids": [],
                "status": "ACTIVE",
            }
            for document in snapshot.documents
        ),
        result_cache={"cached": "pre-incremental"},
    )
    hit = search.search(principal_id=OWNER, query="唯一术语 FULL")
    assert hit.chunks and hit.chunks[0].file == public_uri(SOURCE_ID, "lesson.md")
    ensure_user_provenance(hit.chunks)
    provenance = hit.provenance[0]
    assert provenance.source_id == SOURCE_ID
    assert provenance.document_id == snapshot.documents[0].document_id
    assert provenance.chunk_id == hit.chunks[0].id
    assert provenance.chunk_id in {chunk.chunk_id for chunk in snapshot.documents[0].chunks()}
    assert provenance.generation == first_run.candidate_generation
    assert provenance.origin_kind == "original"

    (source_root / "lesson.md").write_text("# 进程调度\n\n唯一术语 INCREMENTAL-修改后", encoding="utf-8")
    (source_root / "added.md").write_text("新增文档 ADD-文档", encoding="utf-8")
    ready = lifecycle.get_source(principal_id=OWNER, source_id=SOURCE_ID)
    second_run = _sync(
        sync,
        source_root,
        expected_version=ready.record_version,
        strategy="INCREMENTAL",
    )
    assert second_run.status == SYNC_RUN_SUCCESS
    assert second_run.candidate_generation != first_run.candidate_generation
    updated = lifecycle.get_source(principal_id=OWNER, source_id=SOURCE_ID)
    assert updated.published_generation == second_run.candidate_generation
    assert updated.published_revision_no == 2
    updated_snapshot = publisher.load_snapshot(SOURCE_ID, generation=second_run.candidate_generation)
    assert updated_snapshot is not None
    assert {item.logical_uri for item in updated_snapshot.documents} == {"lesson.md", "added.md"}

    # Recreate control-plane and retrieval services; sync already published
    # generation-bound offline indexes, so restart can query directly.
    restarted_lifecycle = SourceLifecycleService(SqliteSourceRegistry(tmp_path / "registry.sqlite3"))
    restarted_publisher = UserSourceSnapshotPublisher(cache_root, restarted_lifecycle)
    assert restarted_publisher.load_snapshot(SOURCE_ID, generation=second_run.candidate_generation) == updated_snapshot
    restarted_search = UserSourceSearchService(
        cache_root,
        restarted_lifecycle,
        snapshot_publisher=restarted_publisher,
        vector_embedder=HashVectorEmbedder(),
    )
    restarted_hit = restarted_search.search(principal_id=OWNER, query="INCREMENTAL 修改后")
    assert restarted_hit.chunks
    assert restarted_hit.provenance[0].generation == second_run.candidate_generation
    assert "INCREMENTAL-修改后" in restarted_hit.chunks[0].content
    assert restarted_search.search(principal_id=OTHER, query="INCREMENTAL").chunks == ()


def test_delete_pending_blocks_e2e_source_and_hard_delete_receipt(tmp_path: Path) -> None:
    lifecycle, source_root = _register(tmp_path)
    cache_root = tmp_path / "cache"
    offline = UserSourceOfflineGuard(
        cache_root,
        lifecycle,
        vector_embedder=HashVectorEmbedder(),
    )
    sync = UserSourceSyncService(
        cache_root,
        lifecycle,
        publisher=offline._snapshots,
        offline=offline,
        sleeper=lambda _delay: None,
    )
    _write_docs(source_root, {"lesson.md": "删除屏障 DELETE-ME"})
    run = _sync(sync, source_root, expected_version=1)
    publisher = sync._publisher
    clock = _Clock(datetime.now(timezone.utc))
    delete = UserSourceDeleteService(
        cache_root,
        lifecycle,
        publisher=publisher,
        clock=clock,
    )
    search = UserSourceSearchService(
        cache_root,
        lifecycle,
        snapshot_publisher=publisher,
        delete_service=delete,
        vector_embedder=HashVectorEmbedder(),
    )
    snapshot = publisher.load_snapshot(SOURCE_ID, generation=run.candidate_generation)
    assert snapshot is not None
    document = snapshot.documents[0]
    chunk = document.chunks()[0]
    delete.surfaces.seed(
        SOURCE_ID,
        generation=run.candidate_generation,
        documents=(
            {
                "logical_uri": document.logical_uri,
                "document_id": document.document_id,
                "chunk_id": chunk.chunk_id,
            },
        ),
        provenance=(
            {
                "document_id": document.document_id,
                "logical_uri": document.logical_uri,
                "origin_kind": "original",
                "derived_from_document_ids": [],
                "status": "ACTIVE",
            },
        ),
        result_cache={"cached": "must-disappear"},
    )
    before_delete = search.search(principal_id=OWNER, query="删除屏障 DELETE-ME")
    assert before_delete.chunks
    assert before_delete.provenance[0].generation == run.candidate_generation

    intent = delete.request_delete(
        principal_id=OWNER,
        source_id=SOURCE_ID,
        request_id=generate_uuid7(),
        expected_version=lifecycle.get_source(principal_id=OWNER, source_id=SOURCE_ID).record_version,
        actor_type=SourceActorType.USER,
        reason="user-requested",
        correlation_id=CORRELATION,
    )
    assert intent.barrier_published is True
    assert intent.surfaces_unreadable is True
    pending = lifecycle._repository.get_source(SOURCE_ID)
    assert pending is not None
    assert pending.state is SourceLifecycleState.DELETE_PENDING
    assert pending.published_generation == run.candidate_generation
    assert delete.is_blocked(SOURCE_ID) is True
    assert delete.surfaces.readable(SOURCE_ID) is False
    assert search.search(principal_id=OWNER, query="删除屏障 DELETE-ME").chunks == ()
    assert delete.surfaces.lookup(SOURCE_ID, "documents", document.document_id) is None
    assert delete.surfaces.lookup(SOURCE_ID, "bm25", document.document_id) is None
    assert delete.surfaces.lookup(SOURCE_ID, "vector", document.document_id) is None
    assert delete.surfaces.lookup(SOURCE_ID, "result_cache", "cached") is None
    assert delete.surfaces.lookup(SOURCE_ID, "provenance", document.document_id) is None
    generation_root = (
        cache_root
        / "user-source-fts5"
        / "v1"
        / SOURCE_ID
        / f"gen-{run.candidate_generation}"
    )
    vector_generation_root = (
        cache_root
        / "user-source-vector"
        / "v1"
        / SOURCE_ID
        / f"gen-{run.candidate_generation}"
    )
    assert generation_root.is_dir()
    assert vector_generation_root.is_dir()
    with pytest.raises(SourceLifecycleException) as caught:
        lifecycle.get_source(principal_id=OWNER, source_id=SOURCE_ID)
    assert caught.value.code is SourceLifecycleErrorCode.SOURCE_NOT_FOUND

    clock.now = clock.now + timedelta(days=MIN_AUDIT_RETENTION_DAYS)
    receipt = delete.sweep_hard_delete(SOURCE_ID, intent.request_id)
    assert receipt is not None
    assert delete.get_receipt(SOURCE_ID, intent.request_id) == receipt
    assert receipt.object_counts["fts5"] == 1
    assert receipt.object_counts["vector"] == 1
    assert set(receipt.store_digests) >= {
        "fts5",
        "vector",
    }
    assert not (
        cache_root
        / "user-source-fts5"
        / "v1"
        / SOURCE_ID
    ).exists()
    assert not (
        cache_root
        / "user-source-vector"
        / "v1"
        / SOURCE_ID
    ).exists()
    deleted = lifecycle._repository.get_source(SOURCE_ID)
    assert deleted is not None
    assert deleted.state is SourceLifecycleState.DELETED
    assert delete.sweep_hard_delete(SOURCE_ID, intent.request_id) == receipt
