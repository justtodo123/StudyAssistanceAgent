from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.bm25 import _tokenize as default_pack_tokenize
from app.fts5_tokenizer import (
    FTS_SCHEMA_VERSION,
    Fts5TokenizerError,
    Fts5TokenizerErrorCode,
    JIEBA_REQUIRED_VERSION,
    NORMALIZATION_VERSION,
    TOKENIZER_SCHEMA_VERSION,
    TOKENIZER_VERSION,
    fts5_match_query,
    normalize_tokenizer_input,
    require_jieba,
    token_stream,
    tokenize,
    tokenizer_metadata,
    validate_tokenizer_metadata,
)
from app.normalized_document import NormalizedDocument, normalize_document
from app.parser_matrix import ParsedDocument, ParsedUnit
from app.user_source_fts5 import UserSourceFts5Index, identity_set_digest
from app.user_source_snapshot import FullSnapshot

pytestmark = pytest.mark.m7

SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"


def _code(error: pytest.ExceptionInfo[Fts5TokenizerError]) -> Fts5TokenizerErrorCode:
    return error.value.code


def _document(uri: str = "lesson.md", text: str = "进程调度算法 与 PCB 的关系") -> NormalizedDocument:
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


def _snapshot(text: str = "进程调度算法 与 PCB 的关系") -> FullSnapshot:
    document = _document(text=text)
    source_fingerprint = hashlib.sha256(document.canonical_bytes()).hexdigest()
    return FullSnapshot(
        source_id=SOURCE_ID,
        generation=f"m7-{source_fingerprint[:24]}",
        manifest_digest=hashlib.sha256(b"manifest").hexdigest(),
        source_fingerprint=source_fingerprint,
        document_count=1,
        chunk_count=1,
        raw_bytes=len(text.encode()),
        documents=(document,),
    )


def test_require_jieba_uses_the_frozen_exact_version() -> None:
    jieba = require_jieba()
    metadata = tokenizer_metadata()
    assert metadata["jieba_version"] == JIEBA_REQUIRED_VERSION
    assert metadata["tokenizer_schema"] == TOKENIZER_SCHEMA_VERSION
    assert metadata["tokenizer_version"] == TOKENIZER_VERSION
    assert callable(jieba.cut_for_search)


def test_wrong_or_missing_jieba_fails_closed_without_unicode61_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.fts5_tokenizer._installed_jieba_version", lambda: "0.39.0")
    with pytest.raises(Fts5TokenizerError) as wrong:
        tokenize("进程调度")
    assert _code(wrong) is Fts5TokenizerErrorCode.UNAVAILABLE
    assert "unicode61" not in str(wrong.value)
    assert "进程" not in str(wrong.value)

    monkeypatch.setattr("app.fts5_tokenizer._installed_jieba_version", lambda: JIEBA_REQUIRED_VERSION)

    def boom(_name: str):
        raise ModuleNotFoundError("jieba")

    monkeypatch.setattr("app.fts5_tokenizer.import_module", boom)
    with pytest.raises(Fts5TokenizerError) as missing:
        tokenize("进程调度")
    assert _code(missing) is Fts5TokenizerErrorCode.UNAVAILABLE


def test_dictionary_load_failure_is_tokenizer_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    class Dummy:
        def initialize(self) -> None:
            raise RuntimeError("dict failed")

        def cut_for_search(self, *_args, **_kwargs):
            raise AssertionError("fallback tokenizer must not run")

    monkeypatch.setattr("app.fts5_tokenizer._installed_jieba_version", lambda: JIEBA_REQUIRED_VERSION)
    monkeypatch.setattr("app.fts5_tokenizer.import_module", lambda _name: Dummy())
    with pytest.raises(Fts5TokenizerError) as caught:
        tokenize("进程调度")
    assert _code(caught) is Fts5TokenizerErrorCode.UNAVAILABLE


def test_normalization_is_nfc_and_collapses_whitespace() -> None:
    mixed = "进\u0300程\r\n调度\t算法  "
    normalized = normalize_tokenizer_input(mixed, purpose="document")
    assert "\r" not in normalized
    assert "\t" not in normalized
    assert "  " not in normalized
    assert normalized == normalize_tokenizer_input("进\u0300程 调度 算法", purpose="document")
    first = token_stream(mixed)
    second = token_stream("进\u0300程 调度 算法")
    assert first == second
    assert first == token_stream(mixed)


def test_unknown_or_mismatched_tokenizer_metadata_is_rejected() -> None:
    valid = tokenizer_metadata()
    validate_tokenizer_metadata(valid)

    with pytest.raises(Fts5TokenizerError) as unknown:
        validate_tokenizer_metadata({**valid, "tokenizer_schema": "sa.source.fts5-tokenizer.v0"})
    assert _code(unknown) is Fts5TokenizerErrorCode.UNSUPPORTED

    with pytest.raises(Fts5TokenizerError) as mismatch:
        validate_tokenizer_metadata({**valid, "tokenizer_version": "whitespace-v1"})
    assert _code(mismatch) is Fts5TokenizerErrorCode.MISMATCH

    with pytest.raises(Fts5TokenizerError) as missing:
        validate_tokenizer_metadata({"tokenizer_version": TOKENIZER_VERSION})
    assert _code(missing) is Fts5TokenizerErrorCode.UNAVAILABLE
    assert "whitespace-v1" not in str(mismatch.value)


def test_invalid_queries_are_rejected_without_leaking_the_raw_query() -> None:
    raw_control = "进程\x00调度"
    with pytest.raises(Fts5TokenizerError) as control:
        fts5_match_query(raw_control)
    assert _code(control) is Fts5TokenizerErrorCode.INVALID_QUERY
    assert "\x00" not in str(control.value)
    assert "进程" not in str(control.value)

    with pytest.raises(Fts5TokenizerError) as empty:
        fts5_match_query("   \n\t  ")
    assert _code(empty) is Fts5TokenizerErrorCode.INVALID_QUERY

    injected = '") OR 1=1 -- MATCH'
    quoted = fts5_match_query(injected)
    assert injected not in quoted
    assert " OR " not in quoted
    assert quoted.startswith('"')
    assert "1=1" not in quoted or quoted.count('"') >= 2


def test_query_tokenization_matches_document_pipeline() -> None:
    text = "读者写者问题如何用 PV 操作实现"
    assert token_stream(text, purpose="document") == token_stream(text, purpose="query")
    match = fts5_match_query(text)
    for token in tokenize(text, purpose="query"):
        assert f'"{token.replace(chr(34), chr(34)+chr(34))}"' in match


def test_generation_bound_fts5_identity_set_matches_snapshot_chunks(tmp_path: Path) -> None:
    snapshot = _snapshot()
    index = UserSourceFts5Index(tmp_path / "cache")
    metadata = index.build(snapshot)
    loaded = index.validate(SOURCE_ID, snapshot.generation, snapshot)
    assert loaded.identity_set_digest == identity_set_digest(snapshot)
    assert loaded.identity_set_digest == metadata.identity_set_digest
    assert loaded.generation == snapshot.generation
    assert loaded.vector_status == "not_attached"
    hits = index.search(SOURCE_ID, snapshot.generation, "进程调度")
    assert [hit.chunk_id for hit in hits]
    assert hits[0].generation == snapshot.generation
    assert hits[0].source_id == SOURCE_ID
    rebuilt = index.build(snapshot)
    assert rebuilt.token_stream_digest == metadata.token_stream_digest
    assert rebuilt.identity_set_digest == metadata.identity_set_digest
    assert index.published_path(SOURCE_ID).name == f"gen-{snapshot.generation}"


def test_default_pack_bm25_tokenizer_is_unchanged() -> None:
    tokens = default_pack_tokenize("PCB的作用是什么")
    assert "pcb" in tokens
    assert tokenizer_metadata()["tokenizer_version"] == TOKENIZER_VERSION
    assert NORMALIZATION_VERSION.startswith("sa.source.text-norm")
