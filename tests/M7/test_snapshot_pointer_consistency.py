from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.normalized_document import normalize_document
from app.parser_matrix import ParsedDocument, ParsedUnit
from app.source_registry import (
    SourceActorType,
    SourceLifecycleService,
    SourceLifecycleState,
    SqliteSourceRegistry,
)
from app.user_source_snapshot import (
    FullSnapshot,
    FullSnapshotError,
    FullSnapshotErrorCode,
    UserSourceSnapshotPublisher,
)

pytestmark = pytest.mark.m7

SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
PRINCIPAL = "principal-owner"
CORRELATION = "corr-m7-pointer"


def _document(text: str):
    uri = "lesson.md"
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


def _snapshot(text: str) -> FullSnapshot:
    document = _document(text)
    manifest_digest = hashlib.sha256(f"manifest:{text}".encode()).hexdigest()
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


def _publish(publisher: UserSourceSnapshotPublisher):
    return publisher.publish_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=Path("unused"),
        correlation_id=CORRELATION,
    )


def test_first_publish_activation_failure_keeps_ready_without_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, publisher = _publisher(tmp_path)
    snapshot = _snapshot("first")
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: snapshot)

    def fail(_snapshot: FullSnapshot) -> None:
        raise OSError("injected pointer failure")

    monkeypatch.setattr(publisher, "_activate_generation", fail)

    with pytest.raises(FullSnapshotError) as error:
        _publish(publisher)

    assert error.value.code is FullSnapshotErrorCode.PUBLICATION_FAILED
    record = service.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert record.state is SourceLifecycleState.READY
    assert record.published_generation == snapshot.generation
    assert publisher.published_path(SOURCE_ID) is None
    assert publisher.load_snapshot(SOURCE_ID) is None
    loaded = publisher.load_snapshot(SOURCE_ID, snapshot.generation)
    assert loaded is not None
    assert loaded.generation == snapshot.generation
    assert len(service._repository.list_revisions(SOURCE_ID)) == 1


def test_activation_failure_keeps_previous_current_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, publisher = _publisher(tmp_path)
    first = _snapshot("first")
    second = _snapshot("second")
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: first)
    _publish(publisher)
    original = publisher._activate_generation

    def fail_new(snapshot: FullSnapshot) -> None:
        if snapshot.generation == second.generation:
            raise OSError("injected pointer failure")
        original(snapshot)

    monkeypatch.setattr(publisher, "_activate_generation", fail_new)
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: second)

    with pytest.raises(FullSnapshotError) as error:
        _publish(publisher)

    assert error.value.code is FullSnapshotErrorCode.PUBLICATION_FAILED
    record = service.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert record.state is SourceLifecycleState.READY
    assert record.published_generation == second.generation
    current = publisher.published_path(SOURCE_ID)
    assert current is not None
    assert current.name == f"gen-{first.generation}"
    stale = publisher.load_snapshot(SOURCE_ID)
    assert stale is not None
    assert stale.generation == first.generation
    published = publisher.load_snapshot(SOURCE_ID, record.published_generation)
    assert published is not None
    assert published.generation == second.generation


def test_retry_repairs_current_after_activation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, publisher = _publisher(tmp_path)
    first = _snapshot("first")
    second = _snapshot("second")
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: first)
    _publish(publisher)
    original = publisher._activate_generation
    calls = {"n": 0}

    def fail_once(snapshot: FullSnapshot) -> None:
        if snapshot.generation == second.generation:
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("injected pointer failure")
        original(snapshot)

    monkeypatch.setattr(publisher, "_activate_generation", fail_once)
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: second)
    with pytest.raises(FullSnapshotError) as error:
        _publish(publisher)
    assert error.value.code is FullSnapshotErrorCode.PUBLICATION_FAILED

    repaired = _publish(publisher)
    record = service.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert repaired.state is SourceLifecycleState.READY
    assert record.state is SourceLifecycleState.READY
    assert record.published_generation == second.generation
    current = publisher.published_path(SOURCE_ID)
    assert current is not None
    assert current.name == f"gen-{second.generation}"
    assert len(service._repository.list_revisions(SOURCE_ID)) == 2


def test_retry_activation_failure_does_not_degrade_ready_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, publisher = _publisher(tmp_path)
    snapshot = _snapshot("first")
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: snapshot)

    def fail(_snapshot: FullSnapshot) -> None:
        raise OSError("injected pointer failure")

    monkeypatch.setattr(publisher, "_activate_generation", fail)

    with pytest.raises(FullSnapshotError):
        _publish(publisher)
    with pytest.raises(FullSnapshotError) as error:
        _publish(publisher)

    assert error.value.code is FullSnapshotErrorCode.PUBLICATION_FAILED
    record = service.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert record.state is SourceLifecycleState.READY
    assert record.published_generation == snapshot.generation
    assert publisher.published_path(SOURCE_ID) is None
    assert publisher.load_snapshot(SOURCE_ID, snapshot.generation) is not None
    assert len(service._repository.list_revisions(SOURCE_ID)) == 1
