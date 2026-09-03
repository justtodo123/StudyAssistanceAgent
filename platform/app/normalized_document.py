"""Canonical M7 normalized documents and source-local staging artifacts."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .source_manifest import canonical_json, normalize_logical_uri, normalize_text
from .source_registry import validate_user_source_id

NORMALIZED_DOCUMENT_SCHEMA = "sa.source.normalized-document.v1"
NORMALIZED_DOCUMENT_VERSION = 1
CHUNK_SCHEMA_VERSION = "sa.chunk.normalized-unit.v1"
_UNIT_KINDS = frozenset({"document", "section", "page", "slide", "heading"})
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_DOCUMENT_ID = re.compile(r"^[0-9a-f]{32}$")


class NormalizedDocumentError(ValueError):
    """A content-free normalization failure."""


def _require_digest(value: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise NormalizedDocumentError("normalized document digest is invalid")
    return value


def _normalized_string(value: str) -> str:
    if not isinstance(value, str):
        raise NormalizedDocumentError("normalized document text is invalid")
    return normalize_text(value)


@dataclass(frozen=True, slots=True)
class NormalizedUnit:
    unit_kind: str
    ordinal: int
    heading_path: tuple[str, ...] = ()
    title: str | None = None
    text: str = ""
    visible: bool = True

    def __post_init__(self) -> None:
        if self.unit_kind not in _UNIT_KINDS:
            raise NormalizedDocumentError("normalized unit kind is invalid")
        if not isinstance(self.ordinal, int) or isinstance(self.ordinal, bool) or self.ordinal < 0:
            raise NormalizedDocumentError("normalized unit ordinal is invalid")
        heading_path = tuple(_normalized_string(item) for item in self.heading_path)
        if any(not item for item in heading_path):
            raise NormalizedDocumentError("normalized heading path is invalid")
        object.__setattr__(self, "heading_path", heading_path)
        if self.title is not None:
            title = _normalized_string(self.title)
            if not title:
                raise NormalizedDocumentError("normalized unit title is invalid")
            object.__setattr__(self, "title", title)
        text = _normalized_string(self.text)
        if not text:
            raise NormalizedDocumentError("normalized unit text is empty")
        object.__setattr__(self, "text", text)
        if not isinstance(self.visible, bool) or not self.visible:
            raise NormalizedDocumentError("normalized unit visibility is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "unit_kind": self.unit_kind,
            "ordinal": self.ordinal,
            "heading_path": list(self.heading_path),
            "title": self.title,
            "text": self.text,
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "NormalizedUnit":
        if not isinstance(payload, Mapping):
            raise NormalizedDocumentError("normalized unit payload is invalid")
        title = payload.get("title")
        heading = payload.get("heading_path") or ()
        return cls(
            unit_kind=str(payload.get("unit_kind")),
            ordinal=int(payload.get("ordinal", -1)),
            heading_path=tuple(str(item) for item in heading),
            title=None if title is None else str(title),
            text=str(payload.get("text", "")),
            visible=bool(payload.get("visible", True)),
        )


@dataclass(frozen=True, slots=True)
class NormalizedChunk:
    """A stable M7 chunk independent of M6a Markdown-only protocols."""

    source_id: str
    document_id: str
    logical_uri: str
    chunk_key: str
    content: str
    title: str
    unit_kind: str
    ordinal: int
    chunk_schema: str = CHUNK_SCHEMA_VERSION
    chunk_id: str = field(init=False)

    def __post_init__(self) -> None:
        try:
            validate_user_source_id(self.source_id)
        except ValueError as exc:
            raise NormalizedDocumentError("normalized chunk source identity is invalid") from exc
        if not isinstance(self.document_id, str) or _DOCUMENT_ID.fullmatch(self.document_id) is None:
            raise NormalizedDocumentError("normalized chunk document identity is invalid")
        if hashlib.sha256(f"{self.source_id}\0{normalize_logical_uri(self.logical_uri)}".encode("utf-8")).hexdigest()[:32] != self.document_id:
            raise NormalizedDocumentError("normalized chunk identity does not match logical identity")
        object.__setattr__(self, "logical_uri", normalize_logical_uri(self.logical_uri))
        expected_key = chunk_key(self.document_id, self.unit_kind, self.ordinal)
        if self.chunk_key != expected_key:
            raise NormalizedDocumentError("normalized chunk key is invalid")
        if self.chunk_schema != CHUNK_SCHEMA_VERSION:
            raise NormalizedDocumentError("normalized chunk schema is invalid")
        content = _normalized_string(self.content)
        if not content:
            raise NormalizedDocumentError("normalized chunk content is empty")
        object.__setattr__(self, "content", content)
        object.__setattr__(self, "title", _normalized_string(self.title))
        object.__setattr__(
            self,
            "chunk_id",
            hashlib.sha256(
                f"{self.document_id}\0{self.chunk_key}\0{self.chunk_schema}".encode("utf-8")
            ).hexdigest()[:32],
        )


@dataclass(frozen=True, slots=True)
class NormalizedDocument:
    source_id: str
    document_id: str
    logical_uri: str
    format: str
    content_fingerprint: str
    parser_id: str
    parser_version: str
    units: tuple[NormalizedUnit, ...]
    normalized_text_digest: str = field(init=False)
    _cached_chunks: tuple["NormalizedChunk", ...] | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            validate_user_source_id(self.source_id)
        except ValueError as exc:
            raise NormalizedDocumentError("normalized document source identity is invalid") from exc
        if not isinstance(self.document_id, str) or _DOCUMENT_ID.fullmatch(self.document_id) is None:
            raise NormalizedDocumentError("normalized document identity is invalid")
        logical_uri = normalize_logical_uri(self.logical_uri)
        object.__setattr__(self, "logical_uri", logical_uri)
        expected_document_id = hashlib.sha256(f"{self.source_id}\0{logical_uri}".encode("utf-8")).hexdigest()[:32]
        if self.document_id != expected_document_id:
            raise NormalizedDocumentError("normalized document identity does not match logical identity")
        if self.format not in {"md", "txt", "pdf", "pptx", "docx"}:
            raise NormalizedDocumentError("normalized document format is invalid")
        _require_digest(self.content_fingerprint)
        if not isinstance(self.parser_id, str) or not self.parser_id:
            raise NormalizedDocumentError("normalized parser identity is invalid")
        if not isinstance(self.parser_version, str) or not self.parser_version:
            raise NormalizedDocumentError("normalized parser version is invalid")
        units = tuple(self.units)
        if not units or any(not isinstance(item, NormalizedUnit) for item in units):
            raise NormalizedDocumentError("normalized units are invalid")
        if tuple(item.ordinal for item in units) != tuple(range(len(units))):
            raise NormalizedDocumentError("normalized unit ordinals are not continuous")
        object.__setattr__(self, "units", units)
        object.__setattr__(self, "normalized_text_digest", hashlib.sha256(canonical_json([item.to_dict() for item in units])).hexdigest())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_name": NORMALIZED_DOCUMENT_SCHEMA,
            "schema_version": NORMALIZED_DOCUMENT_VERSION,
            "source_id": self.source_id,
            "document_id": self.document_id,
            "logical_uri": self.logical_uri,
            "format": self.format,
            "content_fingerprint": self.content_fingerprint,
            "parser_id": self.parser_id,
            "parser_version": self.parser_version,
            "units": [item.to_dict() for item in self.units],
            "normalized_text_digest": self.normalized_text_digest,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "NormalizedDocument":
        if not isinstance(payload, Mapping):
            raise NormalizedDocumentError("normalized document payload is invalid")
        if payload.get("schema_name") != NORMALIZED_DOCUMENT_SCHEMA:
            raise NormalizedDocumentError("normalized document schema is invalid")
        units_payload = payload.get("units") or ()
        document = cls(
            source_id=str(payload.get("source_id")),
            document_id=str(payload.get("document_id")),
            logical_uri=str(payload.get("logical_uri")),
            format=str(payload.get("format")),
            content_fingerprint=str(payload.get("content_fingerprint")),
            parser_id=str(payload.get("parser_id")),
            parser_version=str(payload.get("parser_version")),
            units=tuple(NormalizedUnit.from_dict(item) for item in units_payload),
        )
        digest = payload.get("normalized_text_digest")
        if digest != document.normalized_text_digest:
            raise NormalizedDocumentError("normalized document digest is invalid")
        return document

    def chunks(self) -> tuple["NormalizedChunk", ...]:
        """Return cross-format M7 chunks without applying M6a Markdown rules."""
        if self._cached_chunks is not None:
            return self._cached_chunks
        expected_document_id = hashlib.sha256(
            f"{self.source_id}\0{normalize_logical_uri(self.logical_uri)}".encode("utf-8")
        ).hexdigest()[:32]
        if expected_document_id != self.document_id:
            raise NormalizedDocumentError("normalized document identity does not match logical identity")
        cached = tuple(
            NormalizedChunk(
                source_id=self.source_id,
                document_id=self.document_id,
                logical_uri=self.logical_uri,
                chunk_key=chunk_key(self.document_id, unit.unit_kind, unit.ordinal),
                content=unit.text,
                title=unit.title or (unit.heading_path[-1] if unit.heading_path else ""),
                unit_kind=unit.unit_kind,
                ordinal=unit.ordinal,
            )
            for unit in self.units
        )
        object.__setattr__(self, "_cached_chunks", cached)
        return cached


def chunk_key(document_id: str, unit_kind: str, ordinal: int, *, chunk_schema_version: str = CHUNK_SCHEMA_VERSION) -> str:
    if not isinstance(document_id, str) or _DOCUMENT_ID.fullmatch(document_id) is None:
        raise NormalizedDocumentError("chunk document identity is invalid")
    if unit_kind not in _UNIT_KINDS or not isinstance(ordinal, int) or ordinal < 0:
        raise NormalizedDocumentError("chunk unit identity is invalid")
    if chunk_schema_version != CHUNK_SCHEMA_VERSION:
        raise NormalizedDocumentError("chunk schema is invalid")
    return hashlib.sha256(f"{document_id}\0{unit_kind}\0{ordinal}\0{chunk_schema_version}".encode("utf-8")).hexdigest()


def _field(value: object, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def normalize_document(parsed: object, *, source_id: str, document_id: str, logical_uri: str,
                       format: str, content_fingerprint: str, parser_id: str, parser_version: str) -> NormalizedDocument:
    """Convert a parser-neutral parsed document into its frozen M7 representation."""
    raw_units = tuple(_field(parsed, "units", ()))
    candidates: list[NormalizedUnit] = []
    if format in {"md", "txt"}:
        text = _field(parsed, "text") or "\n".join(str(_field(unit, "text", "")) for unit in raw_units)
        candidates.append(NormalizedUnit("document", 0, text=str(text)))
    elif format == "docx":
        heading_path: list[str] = []
        section_title: str | None = None
        section_lines: list[str] = []
        sections: list[tuple[tuple[str, ...], str | None, str]] = []
        for raw in raw_units:
            text = str(_field(raw, "text", ""))
            level = _field(raw, "heading_level")
            if isinstance(level, int) and level > 0:
                if normalize_text("\n".join(section_lines)):
                    sections.append((tuple(heading_path), section_title, "\n".join(section_lines)))
                heading = normalize_text(text)
                if heading:
                    heading_path = heading_path[: level - 1] + [heading]
                    section_title, section_lines = heading, []
                continue
            section_lines.append(text)
        if normalize_text("\n".join(section_lines)):
            sections.append((tuple(heading_path), section_title, "\n".join(section_lines)))
        candidates.extend(NormalizedUnit("section", index, path, title, text) for index, (path, title, text) in enumerate(sections))
    else:
        expected_kind = "page" if format == "pdf" else "slide"
        for raw in raw_units:
            if not bool(_field(raw, "visible", True)):
                continue
            text = str(_field(raw, "text", ""))
            if not normalize_text(text):
                continue
            heading = _field(raw, "heading_path", ())
            title = _field(raw, "title")
            candidates.append(NormalizedUnit(expected_kind, len(candidates), tuple(heading), title, text))
    if not candidates:
        raise NormalizedDocumentError("parsed document has no visible normalized units")
    if tuple(unit.ordinal for unit in candidates) != tuple(range(len(candidates))):
        candidates = [NormalizedUnit(unit.unit_kind, index, unit.heading_path, unit.title, unit.text, unit.visible) for index, unit in enumerate(candidates)]
    return NormalizedDocument(source_id, document_id, logical_uri, format, content_fingerprint, parser_id, parser_version, tuple(candidates))


class NormalizedDocumentCache:
    """A source-local staging cache; callers decide when a generation is published."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def artifact_path(self, document: NormalizedDocument) -> Path:
        # A 128-bit digest prefix keeps source-local artifacts usable below the
        # traditional Windows MAX_PATH boundary even when pytest supplies a deep
        # temporary root.  The full normalized digest remains in the canonical
        # payload and is verified before publication.
        return self.root / "normalized-documents" / "v1" / document.source_id / document.document_id / f"{document.normalized_text_digest[:32]}.json"

    def stage(self, document: NormalizedDocument) -> Path:
        path = self.artifact_path(document)
        # A nested source/document namespace is created lazily for each staged
        # artifact.  Some Windows file-system providers can discard an empty
        # parent chain between calls, so retain the returned directory and check
        # it before opening the payload.
        parent = path.parent
        parent.mkdir(parents=True, exist_ok=True)
        if not parent.is_dir():
            raise NormalizedDocumentError("normalized document staging path is unavailable")
        payload = document.canonical_bytes()
        with path.open("wb") as stream:
            stream.write(payload)
        if hashlib.sha256(canonical_json([unit.to_dict() for unit in document.units])).hexdigest() != document.normalized_text_digest:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            raise NormalizedDocumentError("staged normalized document digest is invalid")
        return path


__all__ = ["NORMALIZED_DOCUMENT_SCHEMA", "NORMALIZED_DOCUMENT_VERSION", "CHUNK_SCHEMA_VERSION", "NormalizedDocumentError", "NormalizedUnit", "NormalizedChunk", "NormalizedDocument", "chunk_key", "normalize_document", "NormalizedDocumentCache"]
