"""M7 normalized-document contracts with in-memory parser-shaped fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.normalized_document import (
    CHUNK_SCHEMA_VERSION,
    NormalizedDocument,
    NormalizedDocumentCache,
    NormalizedDocumentError,
    NormalizedUnit,
    chunk_key,
    normalize_document,
)

pytestmark = pytest.mark.m7

SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
LOGICAL_URI = "课程/第一课.md"
FINGERPRINT = "a" * 64


def _document_id(uri: str = LOGICAL_URI) -> str:
    return hashlib.sha256(f"{SOURCE_ID}\0{uri}".encode("utf-8")).hexdigest()[:32]


def _parsed(*units: object, text: str | None = None) -> SimpleNamespace:
    values: dict[str, object] = {"units": tuple(units)}
    if text is not None:
        values["text"] = text
    return SimpleNamespace(**values)


def _normalize(parsed: object, *, format: str = "md", uri: str = LOGICAL_URI):
    return normalize_document(
        parsed,
        source_id=SOURCE_ID,
        document_id=_document_id(uri),
        logical_uri=uri,
        format=format,
        content_fingerprint=FINGERPRINT,
        parser_id="test-parser",
        parser_version="1.0.0",
    )


def test_markdown_and_text_normalize_to_one_portable_document_unit() -> None:
    document = _normalize(_parsed(text="  cafe\u0301\r\n\r\n 第一课\t内容  "))

    assert document.units == (
        NormalizedUnit("document", 0, text="café\n\n 第一课\t内容"),
    )
    assert document.to_dict()["schema_name"] == "sa.source.normalized-document.v1"
    assert document.to_dict()["logical_uri"] == LOGICAL_URI
    assert str(Path("C:/private/source")) not in document.canonical_bytes().decode("utf-8")


def test_pdf_and_pptx_drop_empty_or_hidden_units_and_preserve_visible_order() -> None:
    pdf = _normalize(
        _parsed(
            SimpleNamespace(text="  第 1 页 ", title="页一", heading_path=("课程",)),
            SimpleNamespace(text="   ", title="空页"),
            SimpleNamespace(text="第 3 页", title="页三"),
        ),
        format="pdf",
    )
    pptx = _normalize(
        _parsed(
            SimpleNamespace(text="可见幻灯片", title="标题", heading_path=("课程",), visible=True),
            SimpleNamespace(text="隐藏内容", title="不要进入检索", visible=False),
            SimpleNamespace(text="", title="空白", visible=True),
        ),
        format="pptx",
    )

    assert [(unit.unit_kind, unit.ordinal, unit.text) for unit in pdf.units] == [
        ("page", 0, "第 1 页"),
        ("page", 1, "第 3 页"),
    ]
    assert [(unit.unit_kind, unit.ordinal, unit.text) for unit in pptx.units] == [
        ("slide", 0, "可见幻灯片"),
    ]
    assert pptx.units[0].heading_path == ("课程",)


def test_docx_normalizes_sections_at_heading_boundaries_including_preamble() -> None:
    document = _normalize(
        _parsed(
            SimpleNamespace(text="标题前内容", heading_level=None),
            SimpleNamespace(text=" 第一章 ", heading_level=1),
            SimpleNamespace(text="章节内容", heading_level=None),
            SimpleNamespace(text="第二节", heading_level=2),
            SimpleNamespace(text="小节内容", heading_level=None),
        ),
        format="docx",
    )

    assert [(unit.ordinal, unit.heading_path, unit.title, unit.text) for unit in document.units] == [
        (0, (), None, "标题前内容"),
        (1, ("第一章",), "第一章", "章节内容"),
        (2, ("第一章", "第二节"), "第二节", "小节内容"),
    ]


def test_normalization_rejects_empty_visible_content_and_invalid_document_identity() -> None:
    with pytest.raises(NormalizedDocumentError):
        _normalize(_parsed(SimpleNamespace(text=" ", visible=True)), format="pdf")

    with pytest.raises(NormalizedDocumentError):
        normalize_document(
            _parsed(text="内容"),
            source_id=SOURCE_ID,
            document_id="f" * 32,
            logical_uri=LOGICAL_URI,
            format="md",
            content_fingerprint=FINGERPRINT,
            parser_id="test-parser",
            parser_version="1.0.0",
        )


def test_chunk_keys_and_chunk_ids_are_stable_content_independent_identities() -> None:
    first = _normalize(_parsed(text="第一版内容"))
    second = _normalize(_parsed(text="第二版内容"))

    first_chunk = first.chunks()[0]
    second_chunk = second.chunks()[0]
    assert first_chunk.chunk_key == chunk_key(_document_id(), "document", 0)
    assert first_chunk.chunk_key == second_chunk.chunk_key
    assert first_chunk.chunk_id == second_chunk.chunk_id
    assert first_chunk.chunk_schema == CHUNK_SCHEMA_VERSION

    with pytest.raises(NormalizedDocumentError):
        chunk_key(_document_id(), "document", 0, chunk_schema_version="future-schema")


def test_normalized_document_canonical_bytes_and_digest_are_reproducible() -> None:
    first = _normalize(_parsed(text="内容\r\n内容"))
    second = _normalize(_parsed(text="内容\n内容"))

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.normalized_text_digest == second.normalized_text_digest
    assert json.loads(first.canonical_bytes())["normalized_text_digest"] == first.normalized_text_digest


def test_normalized_document_cache_stages_only_generated_artifact(tmp_path: Path) -> None:
    document = _normalize(_parsed(text="运行时生成的内容"))
    cache = NormalizedDocumentCache(tmp_path / "cache")

    staged = cache.stage(document)

    assert staged == cache.artifact_path(document)
    assert staged.parts[-5:-1] == ("normalized-documents", "v1", SOURCE_ID, _document_id())
    assert staged.read_bytes() == document.canonical_bytes()
    assert str(tmp_path / "cache") not in staged.read_text(encoding="utf-8")


def test_normalized_document_requires_contiguous_ordinals_and_visible_units() -> None:
    with pytest.raises(NormalizedDocumentError):
        NormalizedUnit("page", 0, text="内容", visible=False)

    with pytest.raises(NormalizedDocumentError):
        NormalizedDocument(
            SOURCE_ID,
            _document_id(),
            LOGICAL_URI,
            "pdf",
            FINGERPRINT,
            "test-parser",
            "1.0.0",
            (NormalizedUnit("page", 1, text="内容"),),
        )
