from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import config
from app.parser_matrix import ParsedDocument, ParsedUnit
from app.retrieval import MultiRecallService, RetrievalScope
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
from app.user_source_fts5 import (
    VECTOR_STATUS_ATTACHED,
    UserSourceFts5Index,
    identity_set_digest,
)
from app.user_source_search import UserSourceSearchService, public_uri
from app.user_source_snapshot import UserSourceSnapshotPublisher
from app.user_source_vector import (
    HashVectorEmbedder,
    SentenceTransformerEmbedder,
    UserSourceVectorIndex,
    VectorIndexError,
    VectorIndexErrorCode,
)

pytestmark = pytest.mark.m7

SOURCE_A = "user-01890f52-47e7-7abc-8def-0123456789ab"
SOURCE_B = "user-01890f52-47e7-7abc-8def-0123456789ac"
PRINCIPAL = "principal-owner"
OTHER = "principal-other"
CORRELATION = "corr-m7-vector"


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


def _service(tmp_path: Path) -> tuple[SourceLifecycleService, UserSourceSearchService, Path]:
    lifecycle = SourceLifecycleService(SqliteSourceRegistry(tmp_path / "registry.sqlite3"))
    embedder = HashVectorEmbedder()
    service = UserSourceSearchService(tmp_path / "cache", lifecycle, vector_embedder=embedder)
    return lifecycle, service, tmp_path / "cache"


def _register(lifecycle: SourceLifecycleService, source_id: str, owner: str = PRINCIPAL) -> None:
    lifecycle.register_source(
        owner_principal_id=owner,
        expected_version=0,
        actor_type=SourceActorType.USER,
        correlation_id=CORRELATION,
        source_id=source_id,
    )


def _publish(service: UserSourceSearchService, *, source_id: str, source_root: Path) -> None:
    service._offline.repair_full(
        principal_id=PRINCIPAL,
        source_id=source_id,
        source_root=source_root,
        correlation_id=CORRELATION,
    )


def _code(error: pytest.ExceptionInfo[SourceOfflineError]) -> SourceOfflineErrorCode:
    return error.value.code


def test_search_non_positive_top_k_does_not_load_runtime_or_encode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = UserSourceVectorIndex(tmp_path / "cache", embedder=HashVectorEmbedder())
    calls = {"runtime": 0, "encode": 0}

    def fail_runtime(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["runtime"] += 1
        raise AssertionError("runtime must not be loaded")

    def fail_encode(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["encode"] += 1
        raise AssertionError("query must not be encoded")

    monkeypatch.setattr(index, "_ensure_runtime", fail_runtime)
    monkeypatch.setattr(index, "encode_query", fail_encode)
    for top_k in (0, -1):
        assert index.search(SOURCE_A, "m7-missing-generation", "任意查询", top_k=top_k) == ()
    assert calls == {"runtime": 0, "encode": 0}


def test_keyword_only_positive_query_skips_all_vector_entry_points(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle, service, _ = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "keyword-only-vector-spy"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    calls = {"runtime": 0, "validate": 0, "encode": 0, "search": 0}

    def fail(name: str):  # type: ignore[no-untyped-def]
        def unexpected(*args, **kwargs):  # type: ignore[no-untyped-def]
            del args, kwargs
            calls[name] += 1
            raise AssertionError(f"vector {name} must be skipped")

        return unexpected

    monkeypatch.setattr(service._offline._vector, "require_runtime", fail("runtime"))
    monkeypatch.setattr(service._offline._vector, "validate", fail("validate"))
    monkeypatch.setattr(service._offline, "encode_query", fail("encode"))
    monkeypatch.setattr(service._offline._vector, "search", fail("search"))
    result = service.search(
        principal_id=PRINCIPAL,
        query="keyword-only-vector-spy",
        top_k=5,
        use_vector=False,
    )
    assert result.mode == "keyword-only"
    assert result.chunks
    assert calls == {"runtime": 0, "validate": 0, "encode": 0, "search": 0}


def test_sentence_transformer_lazy_init_does_not_mutate_global_torch_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    global_calls: list[tuple[str, object]] = []
    inference_active = False
    constructed: list[tuple[str, dict[str, object]]] = []
    eval_calls = 0
    encode_calls: list[tuple[list[str], dict[str, object], bool]] = []

    class FakeInferenceMode:
        def __enter__(self):  # type: ignore[no-untyped-def]
            nonlocal inference_active
            inference_active = True

        def __exit__(self, *args):  # type: ignore[no-untyped-def]
            nonlocal inference_active
            inference_active = False

    class FakeEncoded:
        def tolist(self) -> list[list[float]]:
            return [[0.0] * int(config.EMBEDDING_EXPECTED_DIM)]

    class FakeSentenceTransformer:
        def __init__(self, model_name: str, **kwargs: object) -> None:
            constructed.append((model_name, kwargs))

        def eval(self) -> None:
            nonlocal eval_calls
            eval_calls += 1

        def encode(self, texts: list[str], **kwargs: object) -> FakeEncoded:
            encode_calls.append((texts, kwargs, inference_active))
            return FakeEncoded()

    fake_torch = SimpleNamespace(
        set_grad_enabled=lambda enabled: global_calls.append(("set_grad_enabled", enabled)),
        get_num_threads=lambda: global_calls.append(("get_num_threads", None)) or 8,
        set_num_threads=lambda threads: global_calls.append(("set_num_threads", threads)),
        inference_mode=lambda: FakeInferenceMode(),
    )
    fake_sentence_transformers = SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_sentence_transformers)

    embedder = SentenceTransformerEmbedder()
    monkeypatch.setattr(embedder, "require_runtime", lambda: None)

    assert embedder.encode(["进程调度"]) == [[0.0] * embedder.dimension]
    assert embedder.encode(["虚拟内存"]) == [[0.0] * embedder.dimension]
    assert global_calls == []
    assert constructed == [(embedder.model_name, {"local_files_only": True})]
    assert eval_calls == 1
    assert encode_calls == [
        (
            ["进程调度"],
            {
                "batch_size": 32,
                "convert_to_numpy": True,
                "normalize_embeddings": embedder.normalize,
                "show_progress_bar": False,
            },
            True,
        ),
        (
            ["虚拟内存"],
            {
                "batch_size": 32,
                "convert_to_numpy": True,
                "normalize_embeddings": embedder.normalize,
                "show_progress_bar": False,
            },
            True,
        ),
    ]


def test_fts5_and_vector_identity_sets_are_identical(tmp_path: Path) -> None:
    lifecycle, service, cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法 与 PCB 的关系", "memory.md": "虚拟内存 与 缺页中断"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    snapshot = UserSourceSnapshotPublisher(cache, lifecycle).load_snapshot(
        SOURCE_A, record.published_generation
    )
    assert snapshot is not None
    fts = UserSourceFts5Index(cache)
    vector = UserSourceVectorIndex(cache, embedder=HashVectorEmbedder())
    fts_meta = fts.validate(SOURCE_A, record.published_generation, snapshot)
    vec_meta = vector.validate(
        SOURCE_A,
        record.published_generation,
        snapshot,
        revision_no=record.published_revision_no,
    )
    expected_ids = {chunk.chunk_id for document in snapshot.documents for chunk in document.chunks()}
    assert fts_meta.vector_status == VECTOR_STATUS_ATTACHED
    assert fts_meta.identity_set_digest == identity_set_digest(snapshot)
    assert fts_meta.vector_identity_set_digest == fts_meta.identity_set_digest
    assert vec_meta.identity_set_digest == fts_meta.identity_set_digest
    assert vector.chunk_ids(SOURCE_A, record.published_generation) == expected_ids
    assert vec_meta.embedding_model == HashVectorEmbedder().model_name
    assert vec_meta.chunk_schema_version.endswith("v1")
    assert vec_meta.revision_no == record.published_revision_no
    assert vec_meta.generation == record.published_generation
    assert vec_meta.source_id == SOURCE_A


def test_generation_switch_does_not_query_old_vector(tmp_path: Path) -> None:
    lifecycle, service, cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "旧世代独有术语OLDGENUNIQUE"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    first = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    old_generation = first.published_generation
    queried: list[str] = []
    original = service._offline._vector.search

    def wrapped(source_id: str, generation: str, query: str, *, top_k: int = 5, **kwargs):
        queried.append(generation)
        return original(source_id, generation, query, top_k=top_k, **kwargs)

    service._offline._vector.search = wrapped  # type: ignore[method-assign]
    _write_docs(root, {"lesson.md": "新世代独有术语NEWGENUNIQUE"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    second = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    result = service.search(principal_id=PRINCIPAL, query="NEWGENUNIQUE")
    assert second.published_generation != old_generation
    assert all(item.generation == second.published_generation for item in result.provenance)
    assert "OLDGENUNIQUE" not in "".join(chunk.content for chunk in result.chunks)
    assert queried
    assert old_generation not in queried
    assert second.published_generation in queried


def test_delete_pending_hides_fts5_vector_cache_and_provenance(tmp_path: Path) -> None:
    lifecycle, service, cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    first = service.search(principal_id=PRINCIPAL, query="进程调度")
    assert first.chunks
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    UserSourceDeleteService(cache, lifecycle).request_delete(
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
    assert result.provenance == ()
    with pytest.raises(SourceIsolationError) as caught:
        service.search(principal_id=PRINCIPAL, query="进程调度", source_id=SOURCE_A)
    assert caught.value.code is SourceIsolationErrorCode.SOURCE_NOT_FOUND
    cached = service.search(principal_id=PRINCIPAL, query="进程调度")
    assert cached.chunks == ()


def test_owner_allowlist_runs_before_fts5_and_vector(tmp_path: Path) -> None:
    lifecycle, service, _cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    calls = {"fts": 0, "vector": 0}
    original_fts = service._offline._fts5.search
    original_vector = service._offline._vector.search

    def wrap_fts(*args, **kwargs):
        calls["fts"] += 1
        return original_fts(*args, **kwargs)

    def wrap_vector(*args, **kwargs):
        calls["vector"] += 1
        return original_vector(*args, **kwargs)

    service._offline._fts5.search = wrap_fts  # type: ignore[method-assign]
    service._offline._vector.search = wrap_vector  # type: ignore[method-assign]
    empty = service.search(principal_id=OTHER, query="进程调度")
    assert empty.chunks == ()
    assert calls == {"fts": 0, "vector": 0}
    with pytest.raises(SourceIsolationError) as caught:
        service.search(principal_id=OTHER, query="进程调度", source_id=SOURCE_A)
    assert caught.value.code is SourceIsolationErrorCode.SOURCE_NOT_FOUND
    assert calls == {"fts": 0, "vector": 0}
    owned = service.search(principal_id=PRINCIPAL, query="进程调度")
    assert owned.chunks
    assert calls["fts"] == 1
    assert calls["vector"] == 1


def test_authorization_digest_change_invalidates_cache(tmp_path: Path) -> None:
    lifecycle, service, _cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    first = service.search(principal_id=PRINCIPAL, query="进程调度")
    second = service.search(principal_id=PRINCIPAL, query="进程调度")
    assert first.cache_hit is False
    assert second.cache_hit is True
    _register(lifecycle, SOURCE_B)
    third = service.search(principal_id=PRINCIPAL, query="进程调度")
    assert third.cache_hit is False
    assert third.auth_digest != first.auth_digest


def test_missing_or_corrupt_vector_metadata_returns_stable_offline_error(tmp_path: Path) -> None:
    lifecycle, service, cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    path = UserSourceVectorIndex(cache, embedder=HashVectorEmbedder()).published_path(
        SOURCE_A, record.published_generation
    )
    assert path is not None
    metadata_path = path / "metadata.json"
    original = metadata_path.read_text(encoding="utf-8")
    metadata_path.unlink()
    with pytest.raises(SourceOfflineError) as missing:
        service.search(principal_id=PRINCIPAL, query="进程调度", source_id=SOURCE_A)
    assert _code(missing) is SourceOfflineErrorCode.INDEX_INVALID
    assert "进程" not in str(missing.value)

    metadata_path.write_text(original, encoding="utf-8")
    payload = json.loads(original)
    payload["embedding_version"] = "tampered-model"
    from app.source_manifest import canonical_json

    metadata_path.write_bytes(canonical_json(payload))
    (path / "SHA256").write_text(hashlib_sha(canonical_json(payload)), encoding="ascii")
    with pytest.raises(SourceOfflineError) as mismatch:
        service.search(principal_id=PRINCIPAL, query="进程调度", source_id=SOURCE_A)
    assert _code(mismatch) is SourceOfflineErrorCode.INDEX_INVALID


def test_embedding_normalize_metadata_mismatch_fails_closed(
    tmp_path: Path,
) -> None:
    lifecycle, service, cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    path = UserSourceVectorIndex(cache, embedder=HashVectorEmbedder()).published_path(
        SOURCE_A, record.published_generation
    )
    assert path is not None
    metadata_path = path / "metadata.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["embedding_normalize"] = not payload["embedding_normalize"]
    from app.source_manifest import canonical_json

    encoded = canonical_json(payload)
    metadata_path.write_bytes(encoded)
    metadata_path.with_name("SHA256").write_text(hashlib_sha(encoded), encoding="ascii")
    with pytest.raises(SourceOfflineError) as mismatch:
        service.search(principal_id=PRINCIPAL, query="进程调度", source_id=SOURCE_A)
    assert _code(mismatch) is SourceOfflineErrorCode.INDEX_INVALID


def hashlib_sha(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest() + "\n"


def test_identity_set_mismatch_fails_closed(tmp_path: Path) -> None:
    lifecycle, service, cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法", "extra.md": "读者写者问题"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    path = UserSourceVectorIndex(cache, embedder=HashVectorEmbedder()).published_path(
        SOURCE_A, record.published_generation
    )
    assert path is not None
    import sqlite3

    connection = sqlite3.connect(path / "index.sqlite3")
    connection.execute("DELETE FROM vectors WHERE chunk_id IN (SELECT chunk_id FROM vectors LIMIT 1)")
    connection.commit()
    connection.close()
    with pytest.raises(SourceOfflineError) as caught:
        service.search(principal_id=PRINCIPAL, query="进程调度", source_id=SOURCE_A)
    assert _code(caught) is SourceOfflineErrorCode.INDEX_INVALID



def test_warm_vector_identity_mismatch_still_fails_closed(tmp_path: Path) -> None:
    lifecycle, service, cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "process-schedule-unique", "extra.md": "banker-algorithm-unique"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    warmed = service.search(principal_id=PRINCIPAL, query="process-schedule-unique")
    assert warmed.chunks
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    path = service._offline._vector.published_path(SOURCE_A, record.published_generation)
    assert path is not None
    import sqlite3

    connection = sqlite3.connect(path / "index.sqlite3")
    connection.execute("DELETE FROM vectors WHERE chunk_id IN (SELECT chunk_id FROM vectors LIMIT 1)")
    connection.commit()
    connection.close()
    with pytest.raises(SourceOfflineError) as caught:
        service.search(principal_id=PRINCIPAL, query="process-schedule-unique", source_id=SOURCE_A)
    assert _code(caught) is SourceOfflineErrorCode.INDEX_INVALID


def test_warm_fts5_cache_hit_revalidates_index_contract(tmp_path: Path) -> None:
    lifecycle, service, _ = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "fts5-warm-cache-unique"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    first = service.search(
        principal_id=PRINCIPAL,
        query="fts5-warm-cache-unique",
        use_vector=False,
    )
    assert first.chunks
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    path = service._offline._fts5.published_path(SOURCE_A, record.published_generation)
    assert path is not None
    import sqlite3

    connection = sqlite3.connect(path / "index.sqlite3")
    connection.execute("DELETE FROM chunks")
    connection.commit()
    connection.close()
    with pytest.raises(SourceOfflineError) as caught:
        service.search(
            principal_id=PRINCIPAL,
            query="fts5-warm-cache-unique",
            use_vector=False,
        )
    assert caught.value.code is SourceOfflineErrorCode.INDEX_INVALID


def test_warm_vector_cache_hit_revalidates_index_contract(tmp_path: Path) -> None:
    lifecycle, service, _ = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "vector-warm-cache-unique"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    first = service.search(
        principal_id=PRINCIPAL,
        query="vector-warm-cache-unique",
    )
    assert first.chunks
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    path = service._offline._vector.published_path(SOURCE_A, record.published_generation)
    assert path is not None
    import sqlite3

    connection = sqlite3.connect(path / "index.sqlite3")
    connection.execute("DELETE FROM vectors")
    connection.commit()
    connection.close()
    with pytest.raises(SourceOfflineError) as caught:
        service.search(
            principal_id=PRINCIPAL,
            query="vector-warm-cache-unique",
        )
    assert caught.value.code is SourceOfflineErrorCode.INDEX_INVALID


def test_last_good_generation_kept_when_new_vector_build_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lifecycle, service, cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    first = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    good = first.published_generation

    def boom(self):  # type: ignore[no-untyped-def]
        raise VectorIndexError(VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE)

    _write_docs(root, {"lesson.md": "读者写者问题"})
    with monkeypatch.context() as ctx:
        ctx.setattr(UserSourceVectorIndex, "require_runtime", boom)
        with pytest.raises(SourceOfflineError) as caught:
            _publish(service, source_id=SOURCE_A, source_root=root)
        assert _code(caught) is SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE
    current = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    assert current.published_generation == good
    result = service.search(principal_id=PRINCIPAL, query="进程调度")
    assert "进程调度算法" in result.chunks[0].content
    assert all(item.generation == good for item in result.provenance)


def test_missing_vector_runtime_does_not_fallback_to_keyword_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lifecycle, service, _cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    _publish(service, source_id=SOURCE_A, source_root=root)

    def boom(self):  # type: ignore[no-untyped-def]
        raise VectorIndexError(VectorIndexErrorCode.DEPENDENCY_UNAVAILABLE)

    monkeypatch.setattr(UserSourceVectorIndex, "require_runtime", boom)
    with pytest.raises(SourceOfflineError) as caught:
        service.search(principal_id=PRINCIPAL, query="进程调度", source_id=SOURCE_A)
    assert _code(caught) is SourceOfflineErrorCode.DEPENDENCY_UNAVAILABLE
    assert caught.value.public_dict()["repair"] == "repair-local-dependency"


def test_fts5_only_generation_fails_closed(tmp_path: Path) -> None:
    lifecycle = SourceLifecycleService(SqliteSourceRegistry(tmp_path / "registry.sqlite3"))
    _register(lifecycle, SOURCE_A)
    cache = tmp_path / "cache"
    guard = UserSourceOfflineGuard(cache, lifecycle, vector_embedder=HashVectorEmbedder())
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "进程调度算法"})
    UserSourceSnapshotPublisher(cache, lifecycle).publish_full(
        principal_id=PRINCIPAL,
        source_id=SOURCE_A,
        source_root=root,
        correlation_id=CORRELATION,
    )
    record = lifecycle.get_source(principal_id=PRINCIPAL, source_id=SOURCE_A)
    snapshot = UserSourceSnapshotPublisher(cache, lifecycle).load_snapshot(
        SOURCE_A, record.published_generation
    )
    assert snapshot is not None
    UserSourceFts5Index(cache).build(snapshot, activate=True)
    with pytest.raises(SourceOfflineError) as caught:
        guard.search(principal_id=PRINCIPAL, source_id=SOURCE_A, query="进程调度")
    assert _code(caught) is SourceOfflineErrorCode.INDEX_INVALID


def test_no_principal_keeps_default_pack_and_scope_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.retrieval.config.VECTOR_ENABLED", False)
    lifecycle, service, _cache = _service(tmp_path)
    _register(lifecycle, SOURCE_A)
    root = tmp_path / "src-a"
    _write_docs(root, {"lesson.md": "用户源独有术语XYZUNIQUEVECTOR"})
    _publish(service, source_id=SOURCE_A, source_root=root)
    recall = MultiRecallService(user_source_search=service)
    default_only, _mode = recall.recall(
        "XYZUNIQUEVECTOR", top_k=5, scope=RetrievalScope.DEFAULT_ONLY
    )
    extras, _mode = recall.recall(
        "XYZUNIQUEVECTOR", top_k=5, scope=RetrievalScope.DEFAULT_PLUS_EXTRAS
    )
    assert all(not chunk.file.startswith("user://") for chunk in default_only)
    assert all(not chunk.file.startswith("user://") for chunk in extras)
    merged, _mode = recall.recall(
        "XYZUNIQUEVECTOR",
        top_k=5,
        scope=RetrievalScope.DEFAULT_ONLY,
        principal_id=PRINCIPAL,
    )
    assert any(chunk.file.startswith("user://") for chunk in merged)
    assert public_uri(SOURCE_A, "lesson.md") in {chunk.file for chunk in merged}


def test_default_pack_keyword_fallback_is_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.retrieval.config.VECTOR_ENABLED", False)
    recall = MultiRecallService()
    results, mode = recall.recall("进程调度", top_k=3, scope=RetrievalScope.DEFAULT_ONLY)
    assert mode == "keyword-only"
    assert results
    assert all(not chunk.file.startswith("user://") for chunk in results)
