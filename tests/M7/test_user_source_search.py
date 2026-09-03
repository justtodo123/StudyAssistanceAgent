from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models import QaRequest, RetrievalChunk
from app.parser_matrix import ParsedDocument, ParsedUnit
from app.qa import QaService
from app.retrieval import MultiRecallService, RetrievalScope
from app.source_delete import UserSourceDeleteService
from app.source_isolation import SourceIsolationError, SourceIsolationErrorCode
from app.source_offline import SourceOfflineError, SourceOfflineErrorCode
from app.source_registry import (
    SourceActorType,
    SourceLifecycleService,
    SqliteSourceRegistry,
)
from app.user_source_search import (
    LazyUserSourceSearch,
    UserSourceSearchService,
    ensure_user_provenance,
    public_uri,
)
from app.user_source_vector import HashVectorEmbedder

pytestmark = pytest.mark.m7

SOURCE_A = "user-01890f52-47e7-7abc-8def-0123456789ab"
SOURCE_B = "user-01890f52-47e7-7abc-8def-0123456789ac"
PRINCIPAL = "principal-owner"
OTHER = "principal-other"
CORRELATION = "corr-m7-search"


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


def _service(tmp_path: Path) -> tuple[SourceLifecycleService, UserSourceSearchService]:
    lifecycle = SourceLifecycleService(SqliteSourceRegistry(tmp_path / "registry.sqlite3"))
    return lifecycle, UserSourceSearchService(
        tmp_path / "cache",
        lifecycle,
        vector_embedder=HashVectorEmbedder(),
    )


def _register(lifecycle: SourceLifecycleService, source_id: str, owner: str = PRINCIPAL) -> None:
    lifecycle.register_source(
        owner_principal_id=owner,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION,
        source_id=source_id,
    )


def _publish(
    service: UserSourceSearchService,
    *,
    source_id: str,
    source_root: Path,
) -> None:
    service._offline.repair_full(
        principal_id=PRINCIPAL,
        source_id=source_id,
        source_root=source_root,
        correlation_id=CORRELATION,
    )


def test_owner_search_returns_user_provenance_and_original_content(tmp_path: Path) -> None:
    lifecycle, service = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法 与 PCB 的关系"})
    _publish(service, source_id=SOURCE_A, source_root=root)

    result = service.search(principal_id=PRINCIPAL, query="进程调度", top_k=5)
    assert result.mode == "hybrid"
    assert result.cache_hit is False
    assert result.auth_digest
    assert len(result.chunks) == 1
    chunk = result.chunks[0]
    assert chunk.file == public_uri(SOURCE_A, "lesson.md")
    assert "进程调度算法" in chunk.content
    assert result.provenance[0].public_uri == chunk.file
    assert result.provenance[0].generation.startswith("m7-")
    ensure_user_provenance(result.chunks)
    assert "D:\\" not in chunk.file
    assert str(tmp_path) not in chunk.file
    assert str(tmp_path) not in chunk.content


def test_foreign_principal_does_not_see_owner_hits(tmp_path: Path) -> None:
    lifecycle, service = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    _publish(service, source_id=SOURCE_A, source_root=root)

    result = service.search(principal_id=OTHER, query="进程调度")
    assert result.chunks == ()
    with pytest.raises(SourceIsolationError) as caught:
        service.search(principal_id=OTHER, query="进程调度", source_id=SOURCE_A)
    assert caught.value.code is SourceIsolationErrorCode.SOURCE_NOT_FOUND
    assert SOURCE_A not in str(caught.value)


def test_result_cache_hits_until_generation_changes(tmp_path: Path) -> None:
    lifecycle, service = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    _publish(service, source_id=SOURCE_A, source_root=root)

    first = service.search(principal_id=PRINCIPAL, query="进程调度")
    second = service.search(principal_id=PRINCIPAL, query="进程调度")
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.auth_digest == first.auth_digest
    assert [key[0] for key in service._cache] == [first.auth_digest]

    _write_docs(root, {"lesson.md": "读者写者问题 与 进程调度"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    third = service.search(principal_id=PRINCIPAL, query="读者写者")
    assert third.cache_hit is False
    assert third.generation_digest != first.generation_digest
    assert "读者写者问题" in third.chunks[0].content


def test_rrf_fuses_two_authorized_sources(tmp_path: Path) -> None:
    lifecycle, service = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    _register(lifecycle, SOURCE_B)
    root_a = tmp_path / "src-a"
    root_b = tmp_path / "src-b"
    _write_docs(root_a, {"a.md": "银行家算法 避免死锁"})
    _write_docs(root_b, {"b.md": "死锁检测 与 银行家算法"})
    _publish(service, source_id=SOURCE_A, source_root=root_a)
    _publish(service, source_id=SOURCE_B, source_root=root_b)

    result = service.search(principal_id=PRINCIPAL, query="银行家算法", top_k=5)
    files = {chunk.file for chunk in result.chunks}
    assert public_uri(SOURCE_A, "a.md") in files
    assert public_uri(SOURCE_B, "b.md") in files
    assert all(item.origin_kind == "original" for item in result.provenance)


def test_deleted_source_is_not_recalled(tmp_path: Path) -> None:
    lifecycle, service = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    from app.source_registry import generate_uuid7

    UserSourceDeleteService(tmp_path / "cache", lifecycle).request_delete(
        principal_id=PRINCIPAL,
        source_id=SOURCE_A,
        request_id=generate_uuid7(),
        expected_version=record.record_version,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION,
        reason="user-requested",
    )
    result = service.search(principal_id=PRINCIPAL, query="进程调度")
    assert result.chunks == ()


def test_missing_index_fails_closed_in_aggregate_and_explicit(tmp_path: Path) -> None:
    lifecycle, service = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    from app.user_source_snapshot import UserSourceSnapshotPublisher

    publisher = UserSourceSnapshotPublisher(tmp_path / "cache", lifecycle)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    publisher.publish_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_A,
        source_root=root,
        correlation_id=CORRELATION,
    )
    with pytest.raises(SourceOfflineError) as aggregate:
        service.search(principal_id=PRINCIPAL, query="进程调度")
    assert aggregate.value.code is SourceOfflineErrorCode.REPAIR_REQUIRED
    with pytest.raises(SourceOfflineError) as caught:
        service.search(principal_id=PRINCIPAL, query="进程调度", source_id=SOURCE_A)
    assert caught.value.code is SourceOfflineErrorCode.REPAIR_REQUIRED


def test_errors_omit_host_paths_and_query_text(tmp_path: Path) -> None:
    lifecycle, service = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    with pytest.raises(SourceOfflineError) as caught:
        service.search(principal_id=PRINCIPAL, query="秘密查询", source_id=SOURCE_A)
    message = str(caught.value)
    assert "秘密查询" not in message
    assert str(tmp_path) not in message
    assert "C:\\" not in message


def test_multirecall_without_principal_keeps_default_pack(tmp_path: Path) -> None:
    lifecycle, service = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "这是一段不会出现在默认知识包中的用户源独有术语XYZUNIQUE"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    recall = MultiRecallService(user_source_search=service)
    results, _mode = recall.recall("XYZUNIQUE", top_k=5, scope=RetrievalScope.DEFAULT_ONLY)
    assert all(not chunk.file.startswith("user://") for chunk in results)

    merged, mode = recall.recall(
        "XYZUNIQUE",
        top_k=5,
        scope=RetrievalScope.DEFAULT_ONLY,
        principal_id=PRINCIPAL,
    )
    assert any(chunk.file.startswith("user://") for chunk in merged)
    assert any("XYZUNIQUE" in chunk.content for chunk in merged)


def test_qa_with_principal_uses_user_provenance(tmp_path: Path) -> None:
    lifecycle, service = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "这是一段不会出现在默认知识包中的用户源独有术语XYZUNIQUE"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    qa = QaService(MultiRecallService(user_source_search=service), scope=RetrievalScope.DEFAULT_ONLY)
    without = qa.answer(QaRequest(question="XYZUNIQUE", use_llm=False))
    assert all(not source.file.startswith("user://") for source in without.sources)
    with_principal = qa.answer(
        QaRequest(question="XYZUNIQUE", use_llm=False, principal_id=PRINCIPAL)
    )
    assert any(source.file.startswith("user://") for source in with_principal.sources)
    assert "XYZUNIQUE" in with_principal.answer or with_principal.sources


def test_api_optional_principal_does_not_change_default_search() -> None:
    from app.main import app

    client = TestClient(app)
    response = client.post("/api/v1/search", json={"question": "进程调度", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert all(item["file"].startswith(("knowledge/", "extra://")) for item in payload["results"])


def test_api_with_principal_can_include_user_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lifecycle, service = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "用户源独有术语XYZUNIQUE"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    import app.main as main

    monkeypatch.setattr(main._recall, "_user_source_search", service)
    client = TestClient(main.app)
    response = client.post(
        "/api/v1/search",
        json={"question": "XYZUNIQUE", "top_k": 5, "principal_id": PRINCIPAL},
    )
    assert response.status_code == 200
    files = [item["file"] for item in response.json()["results"]]
    assert any(item.startswith("user://") for item in files)
    qa = client.post(
        "/api/v1/qa",
        json={"question": "XYZUNIQUE", "use_llm": False, "principal_id": PRINCIPAL},
    )
    assert qa.status_code == 200
    assert any(item["file"].startswith("user://") for item in qa.json()["sources"])


def test_lazy_search_does_not_create_registry(tmp_path: Path) -> None:
    registry = tmp_path / "missing.sqlite3"
    lazy = LazyUserSourceSearch(registry, tmp_path / "cache")
    result = lazy.search(principal_id=PRINCIPAL, query="进程调度")
    assert result.chunks == ()
    assert not registry.exists()


def test_preview_quiz_and_sessions_do_not_import_user_source_search() -> None:
    for relative in (
        "platform/app/quiz.py",
        "platform/app/review_plan.py",
        "platform/app/study_session.py",
        "platform/app/tools/retrieve.py",
        "platform/app/preview_service.py",
    ):
        tree = ast.parse(Path(relative).read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        assert "user_source_search" not in imported
        assert "user_source_fts5" not in imported
        assert "user_source_vector" not in imported
        text = Path(relative).read_text(encoding="utf-8")
        assert "principal_id" not in text


def test_invalid_user_provenance_fails_closed() -> None:
    chunk = RetrievalChunk(id="x", file=r"user://not-a-source/C:\Users\secret.md", content="leak")
    with pytest.raises(SourceOfflineError) as caught:
        ensure_user_provenance([chunk])
    assert caught.value.code is SourceOfflineErrorCode.INDEX_INVALID
    assert "secret" not in str(caught.value)
    assert "C:\\" not in str(caught.value)