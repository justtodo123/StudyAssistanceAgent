from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.normalized_document import NormalizedDocument, NormalizedUnit, normalize_document
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
    SNAPSHOT_CACHE_MAX_ENTRIES,
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


def test_repeat_full_snapshot_ignores_volatile_manifest_timestamp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "lesson.md").write_text("# heading\n\nstable body\n", encoding="utf-8")
    service, publisher = _publisher(tmp_path)

    def fake_parse(path, fmt, max_bytes=None):  # type: ignore[no-untyped-def]
        lines = [line for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
        units = tuple(ParsedUnit("heading", index, line) for index, line in enumerate(lines))
        return ParsedDocument(
            format="md",
            parser_id="markdown-it-py",
            parser_version="4.0.0",
            units=units or (ParsedUnit("document", 0, "empty"),),
        )

    def fake_normalize(parsed, **kwargs):  # type: ignore[no-untyped-def]
        units = tuple(
            NormalizedUnit("heading", index, title=unit.text[:20], text=unit.text)
            for index, unit in enumerate(parsed.units)
        )
        return NormalizedDocument(units=units, **kwargs)

    monkeypatch.setattr("app.user_source_snapshot.parse_file", fake_parse)
    monkeypatch.setattr("app.user_source_snapshot.normalize_document", fake_normalize)

    first = publisher.publish_full(
        principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=source_root, correlation_id=CORRELATION
    )
    first_snapshot = publisher.load_snapshot(SOURCE_ID, first.published_generation)
    second = publisher.publish_full(
        principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=source_root, correlation_id=CORRELATION
    )
    second_snapshot = publisher.load_snapshot(SOURCE_ID, second.published_generation)

    assert first.state is SourceLifecycleState.READY
    assert second.state is SourceLifecycleState.READY
    assert first.published_generation == second.published_generation
    assert first_snapshot is not None and second_snapshot is not None
    assert first_snapshot.source_fingerprint == second_snapshot.source_fingerprint
    assert first_snapshot.manifest_digest == second_snapshot.manifest_digest
    assert len(service._repository.list_revisions(SOURCE_ID)) == 1


def test_snapshot_cache_is_bounded_to_frozen_capacity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, publisher = _publisher(tmp_path)
    monkeypatch.setattr(
        publisher,
        "_build_candidate",
        lambda root, source: _snapshot(text="generation-0"),
    )
    publisher.publish_full(
        principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=tmp_path, correlation_id=CORRELATION
    )
    publisher.load_snapshot(SOURCE_ID)
    assert len(publisher._snapshot_cache) == 1

    for index in range(1, SNAPSHOT_CACHE_MAX_ENTRIES + 4):
        monkeypatch.setattr(
            publisher,
            "_build_candidate",
            lambda root, source, i=index: _snapshot(text=f"generation-{i}"),
        )
        publisher.publish_full(
            principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=tmp_path, correlation_id=CORRELATION
        )
        publisher.load_snapshot(SOURCE_ID)

    assert len(publisher._snapshot_cache) <= SNAPSHOT_CACHE_MAX_ENTRIES
    current = publisher.load_snapshot(SOURCE_ID)
    assert current is not None
    assert current.document_count == 1


def test_snapshot_identity_mismatch_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _service, publisher = _publisher(tmp_path)
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: _snapshot())
    publisher.publish_full(
        principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=tmp_path, correlation_id=CORRELATION
    )
    path = publisher.published_path(SOURCE_ID)
    assert path is not None
    (path / "SHA256").write_text("0" * 64 + "\n", encoding="ascii")
    publisher._snapshot_cache.clear()

    with pytest.raises(FullSnapshotError) as error:
        publisher.load_snapshot(SOURCE_ID)
    assert error.value.code is FullSnapshotErrorCode.PUBLICATION_FAILED
    assert publisher.published_path(SOURCE_ID) == path



def test_warm_cache_rechecks_snapshot_payload_integrity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _service, publisher = _publisher(tmp_path)
    monkeypatch.setattr(publisher, "_build_candidate", lambda root, source: _snapshot())
    publisher.publish_full(
        principal_id=PRINCIPAL, source_id=SOURCE_ID, source_root=tmp_path, correlation_id=CORRELATION
    )
    path = publisher.published_path(SOURCE_ID)
    assert path is not None
    assert publisher.load_snapshot(SOURCE_ID) is not None
    payload = (path / "snapshot.json").read_bytes()
    (path / "snapshot.json").write_bytes(payload + b"\n")

    with pytest.raises(FullSnapshotError) as error:
        publisher.load_snapshot(SOURCE_ID)
    assert error.value.code is FullSnapshotErrorCode.PUBLICATION_FAILED


def test_pointer_and_direct_generation_paths_are_strictly_validated(tmp_path: Path) -> None:
    _service, publisher = _publisher(tmp_path)
    with pytest.raises(FullSnapshotError):
        publisher.published_path("../outside")
    with pytest.raises(FullSnapshotError):
        publisher.published_path(SOURCE_ID, "m7-../../outside")

    root = tmp_path / "cache" / "user-source-snapshots" / "v1" / SOURCE_ID
    root.mkdir(parents=True)
    (root / "CURRENT").write_text("gen-m7-0123456789abcdef01234567/../../outside", encoding="ascii")
    assert publisher.published_path(SOURCE_ID) is None
