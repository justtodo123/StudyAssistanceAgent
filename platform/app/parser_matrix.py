"""Fail-closed parser matrix for M7 user-registered sources.

The optional document libraries are deliberately imported only while checking or
using the corresponding parser. Importing this module therefore does not change
M0--M6 startup behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from importlib import import_module, metadata
from io import BytesIO, TextIOWrapper
from pathlib import PurePath
from types import MappingProxyType
from typing import Iterable, Mapping
import platform
import re
import unicodedata
import zipfile


PARSER_MATRIX_SCHEMA = "sa.source.parser-matrix.v1"
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_PDF_PAGES = 500
MAX_PPTX_SLIDES = 500
MAX_DOCX_BODY_PARAGRAPHS = 500


class ParserErrorCode(str, Enum):
    """Stable, content-free parser failure codes."""

    FORMAT_UNSUPPORTED = "SOURCE_FORMAT_UNSUPPORTED"
    FORMAT_MISMATCH = "SOURCE_FORMAT_MISMATCH"
    PARSER_UNAVAILABLE = "SOURCE_PARSER_UNAVAILABLE"
    PARSE_FAILED = "SOURCE_PARSE_FAILED"
    PARSE_LIMIT_EXCEEDED = "SOURCE_PARSE_LIMIT_EXCEEDED"


_ERROR_MESSAGES: Mapping[ParserErrorCode, str] = MappingProxyType(
    {
        ParserErrorCode.FORMAT_UNSUPPORTED: "The declared source format is unsupported.",
        ParserErrorCode.FORMAT_MISMATCH: "The declared source format does not match the file.",
        ParserErrorCode.PARSER_UNAVAILABLE: "The required source parser is unavailable.",
        ParserErrorCode.PARSE_FAILED: "The source document could not be parsed.",
        ParserErrorCode.PARSE_LIMIT_EXCEEDED: "The source document exceeds a parser limit.",
    }
)


class ParserMatrixError(ValueError):
    """A stable parser rejection that never includes content or host paths."""

    def __init__(self, code: ParserErrorCode | str) -> None:
        try:
            stable_code = ParserErrorCode(code)
        except (TypeError, ValueError):
            stable_code = ParserErrorCode.PARSE_FAILED
        self.code = stable_code
        self.repair_category = {
            ParserErrorCode.FORMAT_UNSUPPORTED: "select-supported-format",
            ParserErrorCode.FORMAT_MISMATCH: "correct-format-declaration",
            ParserErrorCode.PARSER_UNAVAILABLE: "repair-local-parser",
            ParserErrorCode.PARSE_FAILED: "repair-source-document",
            ParserErrorCode.PARSE_LIMIT_EXCEEDED: "reduce-source-document",
        }[stable_code]
        super().__init__(_ERROR_MESSAGES[stable_code])


@dataclass(frozen=True, slots=True)
class ParserSpec:
    """Immutable identity and limits for one approved parser."""

    format: str
    parser_id: str
    parser_version: str
    distribution: str | None
    import_name: str | None
    max_units: int | None = None

    @property
    def identity(self) -> str:
        return f"{self.parser_id}@{self.parser_version}"


@dataclass(frozen=True, slots=True)
class ParsedUnit:
    """Immutable, format-agnostic parser output prior to normalization."""

    unit_kind: str
    ordinal: int
    text: str
    title: str | None = None
    heading_path: tuple[str, ...] = ()
    visible: bool = True
    source_ordinal: int | None = None
    heading_level: int | None = None

    def __post_init__(self) -> None:
        if self.unit_kind not in {"document", "page", "slide", "paragraph", "heading"}:
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
        if not isinstance(self.ordinal, int) or isinstance(self.ordinal, bool) or self.ordinal < 0:
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
        if not isinstance(self.text, str):
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
        if self.title is not None and not isinstance(self.title, str):
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
        if not isinstance(self.heading_path, tuple) or not all(isinstance(item, str) for item in self.heading_path):
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
        if not isinstance(self.visible, bool):
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
        if self.source_ordinal is not None and (
            not isinstance(self.source_ordinal, int)
            or isinstance(self.source_ordinal, bool)
            or self.source_ordinal < 0
        ):
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
        if self.heading_level is not None and (
            not isinstance(self.heading_level, int)
            or isinstance(self.heading_level, bool)
            or not 1 <= self.heading_level <= 9
        ):
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Immutable output of exactly one approved parser."""

    format: str
    parser_id: str
    parser_version: str
    units: tuple[ParsedUnit, ...]

    def __post_init__(self) -> None:
        spec = PARSER_SPECS.get(self.format)
        if spec is None or self.parser_id != spec.parser_id or self.parser_version != spec.parser_version:
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
        if not isinstance(self.units, tuple) or not self.units:
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
        if tuple(unit.ordinal for unit in self.units) != tuple(range(len(self.units))):
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)

    @property
    def parser_identity(self) -> str:
        return f"{self.parser_id}@{self.parser_version}"


PARSER_SPECS: Mapping[str, ParserSpec] = MappingProxyType(
    {
        "md": ParserSpec("md", "markdown-it-py", "4.0.0", "markdown-it-py", "markdown_it"),
        "txt": ParserSpec("txt", "cpython-textio", "3.11.9", None, None),
        "pdf": ParserSpec("pdf", "pypdf", "6.0.0", "pypdf", "pypdf", MAX_PDF_PAGES),
        "pptx": ParserSpec("pptx", "python-pptx", "1.0.2", "python-pptx", "pptx", MAX_PPTX_SLIDES),
        "docx": ParserSpec(
            "docx", "python-docx", "1.2.0", "python-docx", "docx", MAX_DOCX_BODY_PARAGRAPHS
        ),
    }
)

_SUPPORTED_SUFFIXES: Mapping[str, str] = MappingProxyType({f".{name}": name for name in PARSER_SPECS})
_TEXT_FORMATS = frozenset({"md", "txt"})
_PDF_MAGIC = b"%PDF-"
_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_HEADING_STYLE = re.compile(r"^Heading\s+([1-9])$", re.IGNORECASE)


def get_parser_spec(format: str) -> ParserSpec:
    """Return the immutable approved spec, rejecting unknown formats."""
    if not isinstance(format, str):
        raise ParserMatrixError(ParserErrorCode.FORMAT_UNSUPPORTED)
    spec = PARSER_SPECS.get(format.lower().lstrip("."))
    if spec is None:
        raise ParserMatrixError(ParserErrorCode.FORMAT_UNSUPPORTED)
    return spec


def _installed_version(spec: ParserSpec) -> str:
    if spec.parser_id == "cpython-textio":
        if platform.python_implementation() != "CPython":
            raise ParserMatrixError(ParserErrorCode.PARSER_UNAVAILABLE)
        return platform.python_version()
    assert spec.distribution is not None
    try:
        return metadata.version(spec.distribution)
    except (metadata.PackageNotFoundError, ValueError, TypeError) as exc:
        raise ParserMatrixError(ParserErrorCode.PARSER_UNAVAILABLE) from exc


def require_parser(format: str) -> ParserSpec:
    """Fail closed unless the format's exact approved dependency can initialize."""
    spec = get_parser_spec(format)
    if _installed_version(spec) != spec.parser_version:
        raise ParserMatrixError(ParserErrorCode.PARSER_UNAVAILABLE)
    if spec.import_name is not None:
        try:
            import_module(spec.import_name)
        except Exception as exc:
            raise ParserMatrixError(ParserErrorCode.PARSER_UNAVAILABLE) from exc
    return spec


def parser_availability(format: str) -> bool:
    """Return exact-version availability without weakening fail-closed parsing."""
    try:
        require_parser(format)
    except ParserMatrixError:
        return False
    return True


def _extension_format(filename: str | PurePath | None) -> str | None:
    if filename is None:
        return None
    suffix = PurePath(str(filename).replace("\\", "/")).suffix.lower()
    return _SUPPORTED_SUFFIXES.get(suffix)


def _container_format(data: bytes) -> str | None:
    if data.startswith(_PDF_MAGIC):
        return "pdf"
    if not data.startswith(_ZIP_MAGICS):
        return None
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = frozenset(archive.namelist())
            if "[Content_Types].xml" not in names:
                return None
            if "ppt/presentation.xml" in names:
                return "pptx"
            if "word/document.xml" in names:
                return "docx"
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError):
        return None
    return None


def detect_format(data: bytes, *, filename: str | PurePath | None = None) -> str | None:
    """Detect binary containers; text formats require a matching extension declaration."""
    if not isinstance(data, bytes):
        raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
    container = _container_format(data)
    if container is not None:
        return container
    extension = _extension_format(filename)
    if extension in _TEXT_FORMATS:
        try:
            data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return None
        return extension
    return None


def _validate_declaration(data: bytes, declared_format: str, filename: str | PurePath | None) -> ParserSpec:
    spec = get_parser_spec(declared_format)
    extension = _extension_format(filename)
    if filename is not None and extension != spec.format:
        raise ParserMatrixError(ParserErrorCode.FORMAT_MISMATCH)

    detected_container = _container_format(data)
    has_container_magic = data.startswith(_PDF_MAGIC) or data.startswith(_ZIP_MAGICS)
    if spec.format in _TEXT_FORMATS:
        if has_container_magic or detected_container is not None:
            raise ParserMatrixError(ParserErrorCode.FORMAT_MISMATCH)
        try:
            data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ParserMatrixError(ParserErrorCode.PARSE_FAILED) from exc
    elif detected_container != spec.format:
        raise ParserMatrixError(ParserErrorCode.FORMAT_MISMATCH)
    return spec


def _clean_text(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n")).strip()


def _unit(kind: str, ordinal: int, text: str, *, title: str | None = None,
          heading_path: Iterable[str] = (), source_ordinal: int | None = None,
          heading_level: int | None = None) -> ParsedUnit:
    clean_text = _clean_text(text)
    clean_title = _clean_text(title) if title is not None else None
    clean_path = tuple(_clean_text(item) for item in heading_path if _clean_text(item))
    return ParsedUnit(kind, ordinal, clean_text, clean_title or None, clean_path, True, source_ordinal, heading_level)


def _parse_markdown(data: bytes) -> tuple[ParsedUnit, ...]:
    try:
        markdown_it = import_module("markdown_it")
        parser = markdown_it.MarkdownIt("commonmark")
        tokens = parser.parse(data.decode("utf-8", errors="strict"))
    except ParserMatrixError:
        raise
    except Exception as exc:
        raise ParserMatrixError(ParserErrorCode.PARSE_FAILED) from exc

    units: list[ParsedUnit] = []
    heading_path: list[str] = []
    pending_kind: str | None = None
    pending_level: int | None = None
    for token in tokens:
        if token.type == "heading_open":
            pending_kind = "heading"
            try:
                pending_level = int(token.tag[1:])
            except (TypeError, ValueError):
                raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
        elif token.type == "paragraph_open":
            pending_kind = "paragraph"
            pending_level = None
        elif token.type == "inline" and pending_kind is not None:
            text = _clean_text(token.content)
            if text:
                if pending_kind == "heading":
                    assert pending_level is not None
                    heading_path[:] = heading_path[: pending_level - 1]
                    heading_path.append(text)
                    units.append(
                        _unit("heading", len(units), text, title=text, heading_path=heading_path,
                              heading_level=pending_level)
                    )
                else:
                    units.append(_unit("paragraph", len(units), text, heading_path=heading_path))
            pending_kind = None
            pending_level = None
        elif token.type in {"fence", "code_block", "html_block"}:
            text = _clean_text(token.content)
            if text:
                units.append(_unit("paragraph", len(units), text, heading_path=heading_path))
    return tuple(units)


def _parse_text(data: bytes) -> tuple[ParsedUnit, ...]:
    try:
        stream = TextIOWrapper(BytesIO(data), encoding="utf-8", errors="strict", newline=None)
        text = stream.read()
        stream.detach()
    except (OSError, UnicodeError, ValueError) as exc:
        raise ParserMatrixError(ParserErrorCode.PARSE_FAILED) from exc
    text = _clean_text(text)
    return (_unit("document", 0, text),) if text else ()


def _parse_pdf(data: bytes, spec: ParserSpec) -> tuple[ParsedUnit, ...]:
    try:
        pypdf = import_module("pypdf")
        reader = pypdf.PdfReader(BytesIO(data), strict=True)
        if len(reader.pages) > (spec.max_units or MAX_PDF_PAGES):
            raise ParserMatrixError(ParserErrorCode.PARSE_LIMIT_EXCEEDED)
        units = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = _clean_text(page.extract_text() or "")
            if text:
                units.append(_unit("page", len(units), text, source_ordinal=page_number))
        return tuple(units)
    except ParserMatrixError:
        raise
    except Exception as exc:
        raise ParserMatrixError(ParserErrorCode.PARSE_FAILED) from exc


def _slide_is_hidden(slide: object) -> bool:
    try:
        value = slide._element.get("show")  # type: ignore[attr-defined]
    except Exception:
        return False
    return isinstance(value, str) and value.strip().lower() in {"0", "false", "off", "no"}


def _parse_pptx(data: bytes, spec: ParserSpec) -> tuple[ParsedUnit, ...]:
    try:
        pptx = import_module("pptx")
        presentation = pptx.Presentation(BytesIO(data))
        if len(presentation.slides) > (spec.max_units or MAX_PPTX_SLIDES):
            raise ParserMatrixError(ParserErrorCode.PARSE_LIMIT_EXCEEDED)
        units = []
        for slide_number, slide in enumerate(presentation.slides, start=1):
            if _slide_is_hidden(slide):
                continue
            title_shape = slide.shapes.title
            title = _clean_text(title_shape.text) if title_shape is not None and hasattr(title_shape, "text") else ""
            texts: list[str] = []
            for shape in slide.shapes:
                if not getattr(shape, "has_text_frame", False):
                    continue
                text = _clean_text(getattr(shape, "text", ""))
                if text and (shape is not title_shape or text != title):
                    texts.append(text)
            body = "\n".join(([title] if title else []) + texts)
            if body.strip():
                units.append(
                    _unit("slide", len(units), body, title=title or None,
                          heading_path=(title,) if title else (), source_ordinal=slide_number)
                )
        return tuple(units)
    except ParserMatrixError:
        raise
    except Exception as exc:
        raise ParserMatrixError(ParserErrorCode.PARSE_FAILED) from exc


def _parse_docx(data: bytes, spec: ParserSpec) -> tuple[ParsedUnit, ...]:
    try:
        docx = import_module("docx")
        document = docx.Document(BytesIO(data))
        paragraphs = document.paragraphs
        if len(paragraphs) > (spec.max_units or MAX_DOCX_BODY_PARAGRAPHS):
            raise ParserMatrixError(ParserErrorCode.PARSE_LIMIT_EXCEEDED)
        units: list[ParsedUnit] = []
        heading_path: list[str] = []
        for paragraph_number, paragraph in enumerate(paragraphs, start=1):
            text = _clean_text(paragraph.text)
            if not text:
                continue
            style_name = getattr(getattr(paragraph, "style", None), "name", "") or ""
            match = _HEADING_STYLE.fullmatch(style_name.strip())
            if match:
                level = int(match.group(1))
                heading_path[:] = heading_path[: level - 1]
                heading_path.append(text)
                units.append(
                    _unit("heading", len(units), text, title=text, heading_path=heading_path,
                          source_ordinal=paragraph_number, heading_level=level)
                )
            else:
                units.append(
                    _unit("paragraph", len(units), text, heading_path=heading_path,
                          source_ordinal=paragraph_number)
                )
        return tuple(units)
    except ParserMatrixError:
        raise
    except Exception as exc:
        raise ParserMatrixError(ParserErrorCode.PARSE_FAILED) from exc


def parse_document(data: bytes, declared_format: str, *, filename: str | PurePath | None = None,
                   max_bytes: int = MAX_FILE_BYTES, enabled_formats: Iterable[str] | None = None) -> ParsedDocument:
    """Parse one complete file under the frozen M7 parser policy.

    The caller supplies bytes and a manifest-declared format. ``filename`` is
    optional for privacy; when supplied, its extension is cross-checked but is
    never retained in output or exceptions.
    """
    if not isinstance(data, bytes):
        raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0 or max_bytes > MAX_FILE_BYTES:
        raise ParserMatrixError(ParserErrorCode.PARSE_LIMIT_EXCEEDED)
    spec = _validate_declaration(data, declared_format, filename)
    if enabled_formats is not None:
        try:
            enabled = frozenset(item.lower().lstrip(".") for item in enabled_formats)
        except (AttributeError, TypeError) as exc:
            raise ParserMatrixError(ParserErrorCode.FORMAT_UNSUPPORTED) from exc
        if spec.format not in enabled:
            raise ParserMatrixError(ParserErrorCode.FORMAT_UNSUPPORTED)
    if len(data) > max_bytes:
        raise ParserMatrixError(ParserErrorCode.PARSE_LIMIT_EXCEEDED)
    spec = require_parser(spec.format)

    parser = {
        "md": lambda: _parse_markdown(data),
        "txt": lambda: _parse_text(data),
        "pdf": lambda: _parse_pdf(data, spec),
        "pptx": lambda: _parse_pptx(data, spec),
        "docx": lambda: _parse_docx(data, spec),
    }[spec.format]
    units = parser()
    if not units or not any(unit.text.strip() for unit in units):
        raise ParserMatrixError(ParserErrorCode.PARSE_FAILED)
    return ParsedDocument(spec.format, spec.parser_id, spec.parser_version, units)


def parse_file(path: str | PurePath, declared_format: str | None = None, *, max_bytes: int = MAX_FILE_BYTES,
               enabled_formats: Iterable[str] | None = None) -> ParsedDocument:
    """Read and parse one file without ever exposing its host path in errors."""
    filename = PurePath(path).name
    declaration = declared_format or _extension_format(filename)
    if declaration is None:
        raise ParserMatrixError(ParserErrorCode.FORMAT_UNSUPPORTED)
    try:
        with open(path, "rb") as stream:
            data = stream.read(max_bytes + 1)
    except OSError as exc:
        raise ParserMatrixError(ParserErrorCode.PARSE_FAILED) from exc
    return parse_document(data, declaration, filename=filename, max_bytes=max_bytes, enabled_formats=enabled_formats)


parse_bytes = parse_document


__all__ = [
    "MAX_DOCX_BODY_PARAGRAPHS",
    "MAX_FILE_BYTES",
    "MAX_PDF_PAGES",
    "MAX_PPTX_SLIDES",
    "PARSER_MATRIX_SCHEMA",
    "PARSER_SPECS",
    "ParsedDocument",
    "ParsedUnit",
    "ParserErrorCode",
    "ParserMatrixError",
    "ParserSpec",
    "detect_format",
    "get_parser_spec",
    "parse_bytes",
    "parse_document",
    "parse_file",
    "parser_availability",
    "require_parser",
]
