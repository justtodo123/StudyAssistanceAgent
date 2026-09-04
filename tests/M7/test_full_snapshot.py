from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.normalized_document import NormalizedDocument, normalize_document
from app.parser_matrix import ParsedDocument, ParsedUnit
from app.source_registry import (
    SourceActorType,
    SourceLifecycleService,
    SourceLifecycleState,
    SqliteSourceRegistry,
)
from app.user_source_snapshot import (
    CHUNK_SCHEMA_VERSION,
    FullSnapshot,
    FullSnapshotError,
    FullSnapshotErrorCode,
    PARSER_SCHEMA_VERSION,
    UserSourceSnapshotPublisher,
)

pytestmark = pytest.mark.m7

SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
PRINCIPAL = "principal-owner"
CORRELATION = "corr-m7-full"


def _document(uri: str = "lesson.md", text: str = "稳定内容") -> NormalizedDocument:
    document_id = hashlib.sha256(f"{SOURCE_ID}\0{uri}".encode("utf-8")).hexdigest()[:32]
    parsed = ParsedDocument(
        format="md",
        parser_id="markdown-it-py",
        parser_version="4.0.0",
        units=(ParsedUnit("document", 0, text),),
    )
    return normalize_document(
        parsed,
        source_id=SOURCE_ID,
        document_id=document_id,
        logical_uri=uri,
        format="md",
        content_fingerprint=hashlib.sha256(text.encode()).hexdigest(),
        parser_id=parsed.parser_id,
        parser_version=parsed.parser_version,
    )


def _snapshot(text: str = "稳定内容") -> FullSnapshot:
    document = _document(text=text)
    manifest_digest = hashlib.sha256(b"manifest").hexdigest()
    source_fingerprint = hashlib.sha256(document.canonical_bytes()).hexdigest()
    return FullSnapshot(
        source_id=SOURCE_ID,
        generation=f"m7-{source_fingerprint[:24]}",
        manifest_digest=manifest_digest,
        source_fingerprint=source_fingerprint,
        document_count=1,
        chunk_count=1,
        raw_bytes=len(text.encode()),
        documents=(document,),
    )


def _publisher(tmp_path: Path) -> tuple[SourceLifecycleService, UserSourceSnapshotPublisher]:
    service = SourceLifecycleService(
        SqliteSourceRegistry(tmp_path / "registry.sqlite3"),
        source_id_factory=lambda: SOURCE_ID,
    )
    service.register_source(
        owner_principal_id=PRINCIPAL,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION,
        source_id=SOURCE_ID,
    )
    return service, UserSourceSnapshotPublisher(tmp_path / "cache", service)


def test_full_snapshot_publishes_revision_and_current_pointer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, publisher = _publisher(tmp_path)
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: _snapshot())

    record = publisher.publish_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=tmp_path / "source",
        correlation_id=CORRELATION,
    )

    assert record.state is SourceLifecycleState.READY
    assert record.published_generation == _snapshot().generation
    assert publisher.published_path(SOURCE_ID) == publisher.published_path(SOURCE_ID, _snapshot().generation)
    assert len(service._repository.list_revisions(SOURCE_ID)) == 1
    payload = (publisher.published_path(SOURCE_ID) / "snapshot.json").read_bytes()
    assert b"source_root" not in payload


def test_repeat_full_snapshot_is_idempotent_without_new_revision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, publisher = _publisher(tmp_path)
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: _snapshot())

    first = publisher.publish_full(
        principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=tmp_path, correlation_id=CORRELATION
    )
    second = publisher.publish_full(
        principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=tmp_path, correlation_id=CORRELATION
    )

    assert first.published_generation == second.published_generation
    assert len(service._repository.list_revisions(SOURCE_ID)) == 1
    assert list((tmp_path / "cache" / "user-source-snapshots" / "v1" / SOURCE_ID).glob(".staging-*")) == []


def test_failed_candidate_degrades_and_preserves_last_good(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, publisher = _publisher(tmp_path)
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: _snapshot("first"))
    publisher.publish_full(
        principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=tmp_path, correlation_id=CORRELATION
    )
    good_generation = service.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID).published_generation

    def fail(root: object, source: object) -> FullSnapshot:
        raise FullSnapshotError(FullSnapshotErrorCode.SOURCE_LIMIT_EXCEEDED)

    monkeypatch.setattr(publisher, "_build_candidate", fail)
    with pytest.raises(FullSnapshotError) as error:
        publisher.publish_full(
            principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=tmp_path, correlation_id=CORRELATION
        )

    assert error.value.code is FullSnapshotErrorCode.SOURCE_LIMIT_EXCEEDED
    degraded = service.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert degraded.state is SourceLifecycleState.DEGRADED
    assert degraded.published_generation == good_generation
    assert publisher.published_path(SOURCE_ID).name == f"gen-{good_generation}"
    assert len(service._repository.list_revisions(SOURCE_ID)) == 1


def test_registry_failure_does_not_advance_current_pointer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, publisher = _publisher(tmp_path)
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: _snapshot())
    original = service.transition_source
    calls = 0

    def fail_ready(**kwargs):
        nonlocal calls
        calls += 1
        if kwargs["target_state"] is SourceLifecycleState.READY:
            raise RuntimeError("injected registry failure")
        return original(**kwargs)

    monkeypatch.setattr(service, "transition_source", fail_ready)
    with pytest.raises(FullSnapshotError, match="publication failed"):
        publisher.publish_full(
            principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=tmp_path, correlation_id=CORRELATION
        )

    assert calls == 3
    assert service.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID).state is SourceLifecycleState.DEGRADED
    assert publisher.published_path(SOURCE_ID) is None
    assert list((tmp_path / "cache" / "user-source-snapshots" / "v1" / SOURCE_ID).glob(".staging-*")) == []
