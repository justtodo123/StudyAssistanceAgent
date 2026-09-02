from __future__ import annotations

import ast
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.source_delete import UserSourceDeleteService
from app.source_isolation import (
    RetrievalHit,
    SourceIsolationError,
    SourceIsolationErrorCode,
    SourceIsolationGate,
)
from app.source_registry import (
    SourceActorType,
    SourceLifecycleService,
    SourceLifecycleState,
    SourceRevisionDraft,
    SqliteSourceRegistry,
    generate_uuid7,
)

pytestmark = pytest.mark.m7

OWNER = "principal-owner"
OTHER = "principal-other"
THIRD = "principal-third"
CORRELATION = "corr-m7-iso"
REASON = "user-requested"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def _source_id(suffix: str) -> str:
    return f"user-01890f52-47e7-7abc-8def-{suffix}"


def _document_id(source_id: str, uri: str) -> str:
    return hashlib.sha256(f"{source_id}\0{uri}".encode("utf-8")).hexdigest()[:32]


def _revision(generation: str = "generation-1") -> SourceRevisionDraft:
    return SourceRevisionDraft(
        build_result="SUCCESS",
        source_fingerprint=DIGEST_A,
        manifest_digest=DIGEST_B,
        parser_schema_version="parser-v1",
        chunk_schema_version="chunk-v1",
        generation=generation,
        document_count=1,
        chunk_count=1,
        raw_bytes=32,
    )


def _ready(tmp_path: Path, *, source_id: str, owner: str):
    registry = SqliteSourceRegistry(tmp_path / "registry.sqlite3")
    lifecycle = SourceLifecycleService(registry, source_id_factory=lambda: source_id)
    record = lifecycle.register_source(
        owner_principal_id=owner,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION,
        source_id=source_id,
    )
    syncing = lifecycle.transition_source(
        principal_id=owner,
        source_id=source_id,
        expected_version=record.record_version,
        target_state=SourceLifecycleState.SYNCING,
        actor_type=SourceActorType.SERVICE,
        correlation_id=CORRELATION,
    )
    ready = lifecycle.transition_source(
        principal_id=owner,
        source_id=source_id,
        expected_version=syncing.record_version,
        target_state=SourceLifecycleState.READY,
        actor_type=SourceActorType.SERVICE,
        correlation_id=CORRELATION,
        revision=_revision(),
    )
    delete = UserSourceDeleteService(tmp_path / "cache", lifecycle)
    gate = SourceIsolationGate(lifecycle, delete)
    return lifecycle, delete, gate, ready


def _shared(tmp_path: Path):
    registry = SqliteSourceRegistry(tmp_path / "registry.sqlite3")
    lifecycle = SourceLifecycleService(registry)
    delete = UserSourceDeleteService(tmp_path / "cache", lifecycle)
    gate = SourceIsolationGate(lifecycle, delete)
    return lifecycle, delete, gate


def _register_ready(lifecycle: SourceLifecycleService, *, source_id: str, owner: str):
    record = lifecycle.register_source(
        owner_principal_id=owner,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION,
        source_id=source_id,
    )
    syncing = lifecycle.transition_source(
        principal_id=owner,
        source_id=source_id,
        expected_version=record.record_version,
        target_state=SourceLifecycleState.SYNCING,
        actor_type=SourceActorType.SERVICE,
        correlation_id=CORRELATION,
    )
    return lifecycle.transition_source(
        principal_id=owner,
        source_id=source_id,
        expected_version=syncing.record_version,
        target_state=SourceLifecycleState.READY,
        actor_type=SourceActorType.SERVICE,
        correlation_id=CORRELATION,
        revision=_revision(),
    )


def _hit(source_id: str, uri: str = "lesson.md", **kwargs) -> RetrievalHit:
    return RetrievalHit(
        source_id=source_id,
        document_id=_document_id(source_id, uri),
        chunk_id="chunk-1",
        logical_uri=uri,
        generation=kwargs.get("generation", "generation-1"),
        origin_kind=kwargs.get("origin_kind", "original"),
        cache_key=kwargs.get("cache_key"),
    )


def test_owner_hits_pass_and_foreign_hits_are_dropped(tmp_path: Path) -> None:
    lifecycle, delete, gate = _shared(tmp_path)
    own = _source_id("0000000000a1")
    foreign = _source_id("0000000000a2")
    own_record = _register_ready(lifecycle, source_id=own, owner=OWNER)
    _register_ready(lifecycle, source_id=foreign, owner=OTHER)
    snapshot = gate.capture_snapshot(OWNER)
    owned = _hit(own, cache_key=f"{snapshot.auth_digest}:{own}")
    leaked = _hit(foreign, cache_key=f"{snapshot.auth_digest}:{foreign}")
    assert gate.filter_hits(OWNER, (owned, leaked)) == (owned,)
    gate.require_source(OWNER, own)
    with pytest.raises(SourceIsolationError) as exc:
        gate.require_source(OWNER, foreign)
    assert exc.value.code is SourceIsolationErrorCode.SOURCE_NOT_FOUND
    del own_record
    del delete


def test_missing_unauthorized_and_deleted_are_uniform_not_found(tmp_path: Path) -> None:
    lifecycle, delete, gate = _shared(tmp_path)
    source_id = _source_id("0000000000b1")
    unknown = _source_id("0000000000b2")
    record = _register_ready(lifecycle, source_id=source_id, owner=OWNER)
    missing = None
    unauthorized = None
    deleted = None
    try:
        gate.require_source(OWNER, unknown)
    except SourceIsolationError as exc:
        missing = (exc.code, str(exc))
    try:
        gate.require_source(OTHER, source_id)
    except SourceIsolationError as exc:
        unauthorized = (exc.code, str(exc))
    delete.request_delete(
        principal_id=OWNER,
        source_id=source_id,
        request_id=generate_uuid7(),
        expected_version=record.record_version,
        actor_type=SourceActorType.USER,
        reason=REASON,
        correlation_id=CORRELATION,
    )
    try:
        gate.require_source(OWNER, source_id)
    except SourceIsolationError as exc:
        deleted = (exc.code, str(exc))
    assert missing == unauthorized == deleted
    assert missing is not None
    assert missing[0] is SourceIsolationErrorCode.SOURCE_NOT_FOUND


def test_missing_principal_and_source_id_fail_closed(tmp_path: Path) -> None:
    _, _, gate = _shared(tmp_path)
    with pytest.raises(SourceIsolationError) as auth:
        gate.filter_hits("", (_hit(_source_id("0000000000c1")),))
    assert auth.value.code is SourceIsolationErrorCode.SOURCE_AUTH_REQUIRED
    with pytest.raises(SourceIsolationError) as unavailable:
        gate.filter_hits(OWNER, (RetrievalHit(source_id=None),))
    assert unavailable.value.code is SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE


def test_cache_key_without_auth_digest_is_unavailable(tmp_path: Path) -> None:
    lifecycle, _, gate = _shared(tmp_path)
    source_id = _source_id("0000000000d1")
    _register_ready(lifecycle, source_id=source_id, owner=OWNER)
    with pytest.raises(SourceIsolationError) as exc:
        gate.filter_hits(OWNER, (_hit(source_id, cache_key="stolen-from-other-principal"),))
    assert exc.value.code is SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE


def test_mid_request_authorization_change_retries_then_fails_closed(tmp_path: Path) -> None:
    lifecycle, delete, gate = _shared(tmp_path)
    first_id = _source_id("0000000000e1")
    second_id = _source_id("0000000000e2")
    first = _register_ready(lifecycle, source_id=first_id, owner=OWNER)
    second = _register_ready(lifecycle, source_id=second_id, owner=OWNER)

    def mutate(source_id: str, record) -> None:
        delete.request_delete(
            principal_id=OWNER,
            source_id=source_id,
            request_id=generate_uuid7(),
            expected_version=record.record_version,
            actor_type=SourceActorType.USER,
            reason=REASON,
            correlation_id=CORRELATION,
        )

    gate.mid_request_mutations = [
        lambda: mutate(first_id, first),
        lambda: mutate(second_id, second),
    ]
    with pytest.raises(SourceIsolationError) as exc:
        gate.filter_hits(OWNER, (_hit(first_id), _hit(second_id)))
    assert exc.value.code is SourceIsolationErrorCode.SOURCE_ISOLATION_UNAVAILABLE


def test_tombstone_and_blocked_origins_are_filtered(tmp_path: Path) -> None:
    lifecycle, delete, gate = _shared(tmp_path)
    source_id = _source_id("0000000000f1")
    record = _register_ready(lifecycle, source_id=source_id, owner=OWNER)
    document_id = _document_id(source_id, "lesson.md")
    delete.surfaces.seed(
        source_id,
        generation="generation-1",
        documents=({"logical_uri": "lesson.md", "document_id": document_id, "chunk_id": "chunk-1"},),
        provenance=(
            {
                "document_id": document_id,
                "logical_uri": "lesson.md",
                "origin_kind": "original",
                "derived_from_document_ids": [],
                "status": "ACTIVE",
            },
        ),
    )
    draft = _hit(source_id, origin_kind="ai_draft")
    kept = _hit(source_id)
    assert gate.filter_hits(OWNER, (kept, draft)) == (kept,)
    delete.request_delete(
        principal_id=OWNER,
        source_id=source_id,
        request_id=generate_uuid7(),
        expected_version=record.record_version,
        actor_type=SourceActorType.USER,
        reason=REASON,
        correlation_id=CORRELATION,
    )
    assert gate.filter_hits(OWNER, (kept, draft)) == ()


def test_default_pack_hits_pass_without_owner_filter(tmp_path: Path) -> None:
    _, _, gate = _shared(tmp_path)
    pack_hit = RetrievalHit(source_id="os", logical_uri="process.md", generation=None)
    assert gate.filter_hits(OWNER, (pack_hit,)) == (pack_hit,)


def test_three_principals_have_zero_cross_owner_leaks(tmp_path: Path) -> None:
    lifecycle, _, gate = _shared(tmp_path)
    principals = (OWNER, OTHER, THIRD)
    sources = {}
    for index, principal in enumerate(principals):
        for offset in range(3):
            source_id = _source_id(f"000000000{index}{offset:02d}")
            _register_ready(lifecycle, source_id=source_id, owner=principal)
            sources.setdefault(principal, []).append(source_id)
    leaks = 0
    for principal in principals:
        hits = tuple(_hit(source_id) for owned in sources.values() for source_id in owned)
        allowed = gate.filter_hits(principal, hits)
        allowed_ids = {hit.source_id for hit in allowed}
        assert allowed_ids == set(sources[principal])
        leaks += len(allowed_ids - set(sources[principal]))
    assert leaks == 0


def test_isolation_errors_omit_privacy_canaries(tmp_path: Path) -> None:
    lifecycle, _, gate = _shared(tmp_path)
    source_id = _source_id("0000000000aa")
    _register_ready(lifecycle, source_id=source_id, owner=OWNER)
    canaries = (
        "PRIVATE_DOCUMENT_BODY_8f31",
        "SECRET_TOKEN_8f31",
        r"C:\Users\private\course.pdf",
        "/home/private/course.pdf",
        r"\\server\share\course.pdf",
    )
    with pytest.raises(SourceIsolationError) as exc:
        gate.require_source(OTHER, source_id)
    blob = str(exc.value)
    for canary in canaries:
        assert canary not in blob
        assert OWNER not in blob


def test_isolation_module_does_not_import_app_main() -> None:
    module = Path("platform/app/source_isolation.py").read_text(encoding="utf-8")
    tree = ast.parse(module)
    names = {
        alias.name
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "app.main" not in module
    assert "main" not in names
