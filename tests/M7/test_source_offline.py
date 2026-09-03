from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.fts5_tokenizer import Fts5TokenizerError, Fts5TokenizerErrorCode
from app.parser_matrix import ParsedDocument, ParsedUnit
from app.source_delete import UserSourceDeleteService
from app.source_isolation import SourceIsolationError, SourceIsolationErrorCode
from app.source_offline import (
    SourceOfflineError,
    SourceOfflineErrorCode,
    UserSourceOfflineGuard,
)
from app.source_registry import (
    SourceActorType,
    SourceLifecycleService,
    SourceLifecycleState,
    SqliteSourceRegistry,
    generate_uuid7,
)
from app.user_source_fts5 import UserSourceFts5Index
from app.user_source_snapshot import UserSourceSnapshotPublisher

pytestmark = pytest.mark.m7

SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
PRINCIPAL = "principal-owner"
OTHER = "principal-other"
CORRELATION = "corr-m7-fts5"


@pytest.fixture(autouse=True)
def _synthetic_markdown_parser(monkeypatch: pytest.MonkeyPatch):
    def fake_parse(path, fmt, max_bytes=None):  # type: ignore[no-untyped-def]
        text = Path(path).read_text(encoding="utf-8")
        return ParsedDocument(
            format=fmt or "md",
            parser_id="markdown-it-py",
            parser_version="4.0.0",
            units=(ParsedUnit("document", 0, text),),
        )

    monkeypatch.setattr("app.user_source_snapshot.parse_file", fake_parse)
    return fake_parse


def _write_docs(root: Path, texts: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (root / name).write_text(text, encoding="utf-8")


def _guard(tmp_path: Path) -> tuple[SourceLifecycleService, UserSourceOfflineGuard, Path]:
    lifecycle = SourceLifecycleService(
        SqliteSourceRegistry(tmp_path / "registry.sqlite3"),
        source_id_factory=lambda: SOURCE_ID,
    )
    lifecycle.register_source(
        owner_principal_id=PRINCIPAL,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION,
        source_id=SOURCE_ID,
    )
    cache = tmp_path / "cache"
    guard = UserSourceOfflineGuard(cache, lifecycle)
    source_root = tmp_path / "source"
    return lifecycle, guard, source_root


def _code(error: pytest.ExceptionInfo[SourceOfflineError]) -> SourceOfflineErrorCode:
    return error.value.code


def test_query_without_fts5_requires_explicit_full_repair_and_does_not_autorun(tmp_path: Path) -> None:
    lifecycle, guard, source_root = _guard(tmp_path)
    _write_docs(source_root, {"lesson.md": "进程调度算法"})
    UserSourceSnapshotPublisher(tmp_path / "cache", lifecycle).publish_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=source_root,
        correlation_id=CORRELATION,
    )
    called = {"repair": 0}
    original = guard.repair_full

    def wrapped(**kwargs):
        called["repair"] += 1
        return original(**kwargs)

    guard.repair_full = wrapped  # type: ignore[method-assign]
    with pytest.raises(SourceOfflineError) as caught:
        guard.validate_for_query(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert _code(caught) is SourceOfflineErrorCode.REPAIR_REQUIRED
    assert called["repair"] == 0
    assert lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_ID).state is SourceLifecycleState.READY


def test_missing_jieba_is_dependency_unavailable_and_does_not_start_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _lifecycle, guard, source_root = _guard(tmp_path)
    _write_docs(source_root, {"lesson.md": "进程调度算法"})
    guard.repair_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=source_root,
        correlation_id=CORRELATION,
    )
    searches: list[str] = []
    monkeypatch.setattr(
        "app.fts5_tokenizer._installed_jieba_version",
        lambda: "0.39.0",
    )
    monkeypatch.setattr(
        guard._fts5,
        "search",
        lambda *args, **kwargs: searches.append("started") or (),
    )
    with pytest.raises(SourceOfflineError) as caught:
        guard.search(principal_id=PRINCIPAL, source_id=SOURCE_ID, query="进程调度")
    assert _code(caught) is SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE
    assert searches == []
    assert "0.39.0" not in str(caught.value)
    assert "进程" not in str(caught.value)
    public = caught.value.public_dict()
    assert public["error"] == "SOURCE_OFFLINE_DEPENDENCY_UNAVAILABLE"
    assert public["repair"] == "repair-local-dependency"


def test_corrupt_index_and_identity_mismatch_fail_closed(tmp_path: Path) -> None:
    _lifecycle, guard, source_root = _guard(tmp_path)
    _write_docs(source_root, {"lesson.md": "进程调度算法 与 读者写者问题"})
    record = guard.repair_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=source_root,
        correlation_id=CORRELATION,
    )
    path = guard._fts5.published_path(SOURCE_ID, record.published_generation)
    assert path is not None

    sqlite_path = path / "index.sqlite3"
    payload = sqlite_path.read_bytes()
    sqlite_path.write_bytes(payload[:20] + b"\xff" + payload[21:])
    with pytest.raises(SourceOfflineError) as corrupt:
        guard.validate_for_query(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert _code(corrupt) is SourceOfflineErrorCode.INDEX_INVALID
    sqlite_path.write_bytes(payload)

    metadata_path = path / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["identity_set_digest"] = hashlib.sha256(b"tampered").hexdigest()
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SourceOfflineError) as mismatch:
        guard.validate_for_query(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert _code(mismatch) is SourceOfflineErrorCode.INDEX_INVALID


def test_missing_or_required_vector_metadata_does_not_fallback(tmp_path: Path) -> None:
    _lifecycle, guard, source_root = _guard(tmp_path)
    _write_docs(source_root, {"lesson.md": "进程调度算法"})
    record = guard.repair_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=source_root,
        correlation_id=CORRELATION,
    )
    path = guard._fts5.published_path(SOURCE_ID, record.published_generation)
    assert path is not None
    metadata_path = path / "metadata.json"
    original = metadata_path.read_text(encoding="utf-8")
    metadata = json.loads(original)
    metadata.pop("vector_status")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    (path / "SHA256").write_text(hashlib.sha256(metadata_path.read_bytes()).hexdigest() + "\n", encoding="ascii")
    with pytest.raises(SourceOfflineError) as missing:
        guard.validate_for_query(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert _code(missing) is SourceOfflineErrorCode.INDEX_INVALID

    metadata = json.loads(original)
    metadata["vector_status"] = "required"
    canonical = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    # Keep canonical_json mismatch by writing the raw dict through the same encoder used by production.
    from app.source_manifest import canonical_json

    payload = json.loads(original)
    payload["vector_status"] = "required"
    metadata_path.write_bytes(canonical_json(payload))
    (path / "SHA256").write_text(hashlib.sha256(canonical_json(payload)).hexdigest() + "\n", encoding="ascii")
    with pytest.raises(SourceOfflineError) as required:
        guard.validate_for_query(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert _code(required) is SourceOfflineErrorCode.INDEX_INVALID


def test_unauthorized_source_stays_not_found_not_offline(tmp_path: Path) -> None:
    _lifecycle, guard, source_root = _guard(tmp_path)
    _write_docs(source_root, {"lesson.md": "进程调度算法"})
    guard.repair_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=source_root,
        correlation_id=CORRELATION,
    )
    with pytest.raises(SourceIsolationError) as caught:
        guard.search(principal_id=OTHER, source_id=SOURCE_ID, query="进程调度")
    assert caught.value.code is SourceIsolationErrorCode.SOURCE_NOT_FOUND
    assert SOURCE_ID not in str(caught.value)


def test_explicit_full_repair_makes_source_queryable_and_keeps_identity(tmp_path: Path) -> None:
    lifecycle, guard, source_root = _guard(tmp_path)
    _write_docs(source_root, {"lesson.md": "进程调度算法 与 PCB 的关系"})
    record = guard.repair_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=source_root,
        correlation_id=CORRELATION,
    )
    assert record.state is SourceLifecycleState.READY
    validated = guard.validate_for_query(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert validated.generation == record.published_generation
    hits = guard.search(principal_id=PRINCIPAL, source_id=SOURCE_ID, query="进程调度")
    assert hits[0].source_id == SOURCE_ID
    assert hits[0].generation == record.published_generation
    snapshot = UserSourceSnapshotPublisher(tmp_path / "cache", lifecycle).load_snapshot(
        SOURCE_ID, record.published_generation
    )
    assert snapshot is not None
    from app.user_source_fts5 import identity_set_digest

    assert validated.metadata.identity_set_digest == identity_set_digest(snapshot)


def test_failed_repair_keeps_last_good_fts5(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _lifecycle, guard, source_root = _guard(tmp_path)
    _write_docs(source_root, {"lesson.md": "进程调度算法"})
    first = guard.repair_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=source_root,
        correlation_id=CORRELATION,
    )
    good_generation = first.published_generation
    def boom() -> None:
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNAVAILABLE)

    with monkeypatch.context() as ctx:
        ctx.setattr("app.source_offline.require_jieba", boom)
        with pytest.raises(SourceOfflineError) as caught:
            guard.repair_full(
                principal_id=PRINCIPAL,
                source_id=SOURCE_ID,
                source_root=source_root,
                correlation_id="corr-m7-fts5-fail",
            )
        assert _code(caught) is SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE
    validated = guard.validate_for_query(principal_id=PRINCIPAL, source_id=SOURCE_ID)
    assert validated.generation == good_generation
    assert UserSourceFts5Index(tmp_path / "cache").published_path(SOURCE_ID).name == f"gen-{good_generation}"


def test_deleted_source_is_not_resurrected_by_repair(tmp_path: Path) -> None:
    lifecycle, guard, source_root = _guard(tmp_path)
    _write_docs(source_root, {"lesson.md": "进程调度算法"})
    record = guard.repair_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=source_root,
        correlation_id=CORRELATION,
    )
    delete = UserSourceDeleteService(tmp_path / "cache", lifecycle)
    delete.request_delete(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        request_id=generate_uuid7(),
        expected_version=record.record_version,
        actor_type=SourceActorType.USER,
        reason="owner-requested",
        correlation_id=CORRELATION,
    )
    with pytest.raises(SourceIsolationError) as caught:
        guard.repair_full(
            principal_id=PRINCIPAL,
            source_id=SOURCE_ID,
            source_root=source_root,
            correlation_id="corr-m7-fts5-deleted",
        )
    assert caught.value.code is SourceIsolationErrorCode.SOURCE_NOT_FOUND


def test_errors_do_not_include_host_paths_or_query_text(tmp_path: Path) -> None:
    _lifecycle, guard, source_root = _guard(tmp_path)
    secret = tmp_path / "C:" / "Users" / "secret-root"
    _write_docs(source_root, {"lesson.md": "进程调度算法"})
    guard.repair_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_ID,
        source_root=source_root,
        correlation_id=CORRELATION,
    )
    with pytest.raises(Fts5TokenizerError) as caught:
        guard.search(principal_id=PRINCIPAL, source_id=SOURCE_ID, query="进程\x00调度")
    assert caught.value.code is Fts5TokenizerErrorCode.INVALID_QUERY
    assert "进程" not in str(caught.value)
    assert str(secret) not in str(caught.value)
    assert str(tmp_path) not in str(caught.value)


def test_fts5_modules_are_not_wired_into_app_main() -> None:
    main_text = Path("platform/app/main.py").read_text(encoding="utf-8")
    retrieval_text = Path("platform/app/retrieval.py").read_text(encoding="utf-8")
    qa_text = Path("platform/app/qa.py").read_text(encoding="utf-8")
    for text in (main_text, retrieval_text, qa_text):
        assert "user_source_fts5" not in text
        assert "source_offline" not in text
        assert "fts5_tokenizer" not in text
