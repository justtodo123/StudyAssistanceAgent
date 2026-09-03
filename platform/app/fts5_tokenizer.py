"""Fail-closed M7 FTS5 tokenizer contract.

This module is source-local. Importing it must not change M0-M6 startup, default
pack BM25, M6a extras, or M6b preview retrieval.
"""
from __future__ import annotations

from enum import StrEnum
from importlib import import_module, metadata
from types import MappingProxyType, ModuleType
from typing import Iterable, Mapping
import unicodedata

from .source_manifest import normalize_text


TOKENIZER_SCHEMA_VERSION = "sa.source.fts5-tokenizer.v1"
TOKENIZER_VERSION = "jieba-0.42.1-search"
NORMALIZATION_VERSION = "sa.source.text-norm.nfc-ws.v1"
FTS_SCHEMA_VERSION = "sa.source.fts5-index.v1"
JIEBA_REQUIRED_VERSION = "0.42.1"
JIEBA_HMM = True


class Fts5TokenizerErrorCode(StrEnum):
    """Stable, content-free tokenizer failure codes."""

    UNSUPPORTED = "SOURCE_TOKENIZER_UNSUPPORTED"
    MISMATCH = "SOURCE_TOKENIZER_MISMATCH"
    UNAVAILABLE = "SOURCE_TOKENIZER_UNAVAILABLE"
    INVALID_QUERY = "SOURCE_TOKENIZER_INVALID_QUERY"


_ERROR_MESSAGES: Mapping[Fts5TokenizerErrorCode, str] = MappingProxyType(
    {
        Fts5TokenizerErrorCode.UNSUPPORTED: "The source tokenizer is unsupported.",
        Fts5TokenizerErrorCode.MISMATCH: "The source tokenizer metadata does not match.",
        Fts5TokenizerErrorCode.UNAVAILABLE: "The required source tokenizer is unavailable.",
        Fts5TokenizerErrorCode.INVALID_QUERY: "The source tokenizer query is invalid.",
    }
)


class Fts5TokenizerError(RuntimeError):
    """A stable tokenizer rejection that never includes content or host paths."""

    def __init__(self, code: Fts5TokenizerErrorCode) -> None:
        self.code = code
        self.repair_category = {
            Fts5TokenizerErrorCode.UNSUPPORTED: "select-supported-tokenizer",
            Fts5TokenizerErrorCode.MISMATCH: "rebuild-source-index-full",
            Fts5TokenizerErrorCode.UNAVAILABLE: "repair-local-tokenizer",
            Fts5TokenizerErrorCode.INVALID_QUERY: "correct-tokenizer-query",
        }[code]
        super().__init__(_ERROR_MESSAGES[code])


def _installed_jieba_version() -> str:
    try:
        return metadata.version("jieba")
    except metadata.PackageNotFoundError as exc:
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNAVAILABLE) from exc


def require_jieba() -> ModuleType:
    """Fail closed unless jieba==0.42.1 can import and initialize."""
    if _installed_jieba_version() != JIEBA_REQUIRED_VERSION:
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNAVAILABLE)
    try:
        jieba = import_module("jieba")
        initialize = getattr(jieba, "initialize", None)
        if initialize is not None:
            initialize()
        cut_for_search = getattr(jieba, "cut_for_search", None)
        if not callable(cut_for_search):
            raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNAVAILABLE)
    except Fts5TokenizerError:
        raise
    except Exception as exc:
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNAVAILABLE) from exc
    return jieba


def _has_disallowed_characters(text: str) -> bool:
    for char in text:
        if unicodedata.category(char).startswith("C") and char not in "\t\n\r":
            return True
    return False


def normalize_tokenizer_input(text: str, *, purpose: str) -> str:
    """Apply the frozen NFC/whitespace policy without exposing the original text."""
    if purpose not in {"document", "query"}:
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNSUPPORTED)
    if not isinstance(text, str):
        code = (
            Fts5TokenizerErrorCode.INVALID_QUERY
            if purpose == "query"
            else Fts5TokenizerErrorCode.UNSUPPORTED
        )
        raise Fts5TokenizerError(code)
    if _has_disallowed_characters(text):
        code = (
            Fts5TokenizerErrorCode.INVALID_QUERY
            if purpose == "query"
            else Fts5TokenizerErrorCode.UNSUPPORTED
        )
        raise Fts5TokenizerError(code)
    try:
        normalized = normalize_text(text)
    except Exception as exc:
        code = (
            Fts5TokenizerErrorCode.INVALID_QUERY
            if purpose == "query"
            else Fts5TokenizerErrorCode.UNSUPPORTED
        )
        raise Fts5TokenizerError(code) from exc
    if _has_disallowed_characters(normalized):
        code = (
            Fts5TokenizerErrorCode.INVALID_QUERY
            if purpose == "query"
            else Fts5TokenizerErrorCode.UNSUPPORTED
        )
        raise Fts5TokenizerError(code)
    if purpose == "query" and not normalized:
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.INVALID_QUERY)
    return normalized


def tokenize(text: str, *, purpose: str = "document") -> tuple[str, ...]:
    """Return jieba search-mode tokens for one normalized string."""
    normalized = normalize_tokenizer_input(text, purpose=purpose)
    jieba = require_jieba()
    try:
        raw_tokens = jieba.cut_for_search(normalized, HMM=JIEBA_HMM)
        tokens = tuple(token for token in raw_tokens if token and not token.isspace())
    except Fts5TokenizerError:
        raise
    except Exception as exc:
        if purpose == "query":
            raise Fts5TokenizerError(Fts5TokenizerErrorCode.INVALID_QUERY) from exc
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNAVAILABLE) from exc
    if purpose == "query" and not tokens:
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.INVALID_QUERY)
    return tokens


def token_stream(text: str, *, purpose: str = "document") -> str:
    """Join search-mode tokens with a single space for FTS5 unicode61."""
    return " ".join(tokenize(text, purpose=purpose))


def fts5_match_query(text: str) -> str:
    """Build a quoted MATCH query from the same tokenization pipeline.

    Raw query text is never concatenated into the MATCH expression.
    """
    tokens = tokenize(text, purpose="query")
    return " ".join('"' + token.replace('"', '""') + '"' for token in tokens)


def tokenizer_metadata() -> dict[str, str]:
    require_jieba()
    return {
        "tokenizer_schema": TOKENIZER_SCHEMA_VERSION,
        "tokenizer_version": TOKENIZER_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "fts_schema_version": FTS_SCHEMA_VERSION,
        "jieba_version": JIEBA_REQUIRED_VERSION,
    }


def validate_tokenizer_metadata(payload: Mapping[str, object]) -> None:
    """Reject unknown or mismatched tokenizer/index metadata without fallback."""
    if not isinstance(payload, Mapping):
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNSUPPORTED)
    schema = payload.get("tokenizer_schema")
    fts_schema = payload.get("fts_schema_version")
    if schema is None or fts_schema is None:
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNAVAILABLE)
    if schema != TOKENIZER_SCHEMA_VERSION:
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNSUPPORTED)
    if fts_schema != FTS_SCHEMA_VERSION:
        raise Fts5TokenizerError(Fts5TokenizerErrorCode.UNSUPPORTED)
    expected = tokenizer_metadata()
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Fts5TokenizerError(Fts5TokenizerErrorCode.MISMATCH)


def tokenizer_versions_for_digest() -> dict[str, str]:
    return tokenizer_metadata()


def iter_token_streams(texts: Iterable[str], *, purpose: str = "document") -> tuple[str, ...]:
    return tuple(token_stream(text, purpose=purpose) for text in texts)


__all__ = [
    "TOKENIZER_SCHEMA_VERSION",
    "TOKENIZER_VERSION",
    "NORMALIZATION_VERSION",
    "FTS_SCHEMA_VERSION",
    "JIEBA_REQUIRED_VERSION",
    "Fts5TokenizerErrorCode",
    "Fts5TokenizerError",
    "require_jieba",
    "normalize_tokenizer_input",
    "tokenize",
    "token_stream",
    "fts5_match_query",
    "tokenizer_metadata",
    "validate_tokenizer_metadata",
    "tokenizer_versions_for_digest",
    "iter_token_streams",
]
