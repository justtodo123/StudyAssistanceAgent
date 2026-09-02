"""Canonical file manifests for registered M7 user sources.

This module is deliberately independent from the default Markdown pack.  A
manifest contains portable metadata only; file contents are represented by
SHA-256 fingerprints and are never serialized into the manifest.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Mapping

from .source_registry import validate_user_source_id

SCHEMA_NAME = "sa.source.manifest.v1"
SCHEMA_VERSION = 1
SOURCE_TYPE = "user_registered"
FINGERPRINT_ALGORITHM = "sha256"
_SUPPORTED_FORMATS = frozenset({"md", "txt", "pdf", "pptx", "docx"})
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:([\\/]|$)")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class ManifestErrorCode(StrEnum):
    SCHEMA_UNSUPPORTED = "SOURCE_MANIFEST_SCHEMA_UNSUPPORTED"
    INVALID = "SOURCE_MANIFEST_INVALID"
    IDENTITY_CONFLICT = "SOURCE_MANIFEST_IDENTITY_CONFLICT"
    FINGERPRINT_MISMATCH = "SOURCE_MANIFEST_FINGERPRINT_MISMATCH"
    UNREADABLE = "SOURCE_MANIFEST_UNREADABLE"
    FORMAT_UNSUPPORTED = "SOURCE_FORMAT_UNSUPPORTED"
    FORMAT_MISMATCH = "SOURCE_FORMAT_MISMATCH"
    SIZE_LIMIT_EXCEEDED = "SOURCE_FILE_LIMIT_EXCEEDED"


class SourceManifestError(ValueError):
    """Stable, content-free manifest validation failure."""

    def __init__(self, code: ManifestErrorCode, message: str = "The source manifest is invalid.") -> None:
        self.code = code
        super().__init__(message)


class ManifestAcceptance(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNSUPPORTED = "unsupported"


def normalize_text(value: str) -> str:
    """Apply the manifest's portable text normalization policy."""
    if not isinstance(value, str):
        raise SourceManifestError(ManifestErrorCode.INVALID)
    value = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", value).strip()


def normalize_logical_uri(value: str) -> str:
    """Normalize and validate a root-relative POSIX logical URI."""
    if not isinstance(value, str) or not value:
        raise SourceManifestError(ManifestErrorCode.INVALID)
    uri = unicodedata.normalize("NFC", value).replace("\\", "/")
    if uri.startswith("/") or uri.startswith("//") or _WINDOWS_DRIVE.match(uri):
        raise SourceManifestError(ManifestErrorCode.INVALID)
    if any(ord(char) < 32 or ord(char) == 127 for char in uri):
        raise SourceManifestError(ManifestErrorCode.INVALID)
    parts = uri.split("/")
    if not parts or any(not part or part in {".", ".."} for part in parts):
        raise SourceManifestError(ManifestErrorCode.INVALID)
    return uri


def _document_id(source_id: str, logical_uri: str) -> str:
    return hashlib.sha256(f"{source_id}\0{logical_uri}".encode("utf-8")).hexdigest()[:32]


def _digest(value: str, *, field: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise SourceManifestError(ManifestErrorCode.INVALID, f"{field} is invalid")
    return value


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SourceManifestError(ManifestErrorCode.INVALID)
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def detect_format(path: str | Path, data: bytes | None = None) -> str | None:
    """Return the format detected from magic/container markers and suffix."""
    name = str(path).lower()
    data = b"" if data is None else data
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        # OOXML containers are ZIP files.  The directory marker distinguishes
        # the three supported document families without extracting contents.
        if b"ppt/" in data:
            return "pptx"
        if b"word/" in data:
            return "docx"
        return None
    suffix = Path(name).suffix.lower()
    if suffix == ".md":
        return "md"
    if suffix == ".txt":
        return "txt"
    if suffix == ".pdf":
        return None
    if suffix == ".pptx":
        return None
    if suffix == ".docx":
        return None
    return None


def _declared_format(path: Path) -> str | None:
    return {".md": "md", ".txt": "txt", ".pdf": "pdf", ".pptx": "pptx", ".docx": "docx"}.get(path.suffix.lower())


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    logical_uri: str
    document_id: str
    source_type: str
    format: str | None
    acceptance: ManifestAcceptance | str
    size_bytes: int
    content_fingerprint: str
    fingerprint_algorithm: str = FINGERPRINT_ALGORITHM
    reject_code: str | None = None

    def __post_init__(self) -> None:
        uri = normalize_logical_uri(self.logical_uri)
        object.__setattr__(self, "logical_uri", uri)
        if not isinstance(self.document_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.document_id):
            raise SourceManifestError(ManifestErrorCode.INVALID)
        if self.source_type != SOURCE_TYPE or self.format not in _SUPPORTED_FORMATS | {None}:
            raise SourceManifestError(ManifestErrorCode.INVALID)
        try:
            acceptance = ManifestAcceptance(self.acceptance)
        except ValueError as exc:
            raise SourceManifestError(ManifestErrorCode.INVALID) from exc
        object.__setattr__(self, "acceptance", acceptance)
        if not isinstance(self.size_bytes, int) or isinstance(self.size_bytes, bool) or self.size_bytes < 0:
            raise SourceManifestError(ManifestErrorCode.INVALID)
        _digest(self.content_fingerprint, field="content_fingerprint")
        if self.fingerprint_algorithm != FINGERPRINT_ALGORITHM:
            raise SourceManifestError(ManifestErrorCode.INVALID)
        if acceptance is ManifestAcceptance.ACCEPTED and self.reject_code is not None:
            raise SourceManifestError(ManifestErrorCode.INVALID)
        if acceptance is ManifestAcceptance.ACCEPTED and self.format not in _SUPPORTED_FORMATS:
            raise SourceManifestError(ManifestErrorCode.INVALID)
        if acceptance is not ManifestAcceptance.ACCEPTED and (not isinstance(self.reject_code, str) or not self.reject_code):
            raise SourceManifestError(ManifestErrorCode.INVALID)

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "logical_uri": self.logical_uri,
            "document_id": self.document_id,
            "source_type": self.source_type,
            "format": self.format,
            "acceptance": self.acceptance.value,
            "size_bytes": self.size_bytes,
            "content_fingerprint": self.content_fingerprint,
            "fingerprint_algorithm": self.fingerprint_algorithm,
        }
        if self.reject_code is not None:
            result["reject_code"] = self.reject_code
        return result


@dataclass(frozen=True, slots=True)
class SourceManifest:
    source_id: str
    created_at: str
    entries: tuple[ManifestEntry, ...]
    accepted_count: int = field(init=False)
    rejected_count: int = field(init=False)
    unsupported_count: int = field(init=False)
    accepted_bytes: int = field(init=False)
    manifest_digest: str = field(init=False)

    def __post_init__(self) -> None:
        try:
            validate_user_source_id(self.source_id)
        except ValueError as exc:
            raise SourceManifestError(ManifestErrorCode.INVALID) from exc
        if not isinstance(self.created_at, str):
            raise SourceManifestError(ManifestErrorCode.INVALID)
        try:
            parsed = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
            canonical_created_at = _timestamp(parsed)
        except (TypeError, ValueError) as exc:
            raise SourceManifestError(ManifestErrorCode.INVALID) from exc
        if self.created_at != canonical_created_at:
            raise SourceManifestError(ManifestErrorCode.INVALID)
        entries = tuple(self.entries)
        if any(not isinstance(entry, ManifestEntry) for entry in entries):
            raise SourceManifestError(ManifestErrorCode.INVALID)
        for entry in entries:
            if entry.document_id != _document_id(self.source_id, entry.logical_uri):
                raise SourceManifestError(ManifestErrorCode.IDENTITY_CONFLICT)
        keys = [unicodedata.normalize("NFC", e.logical_uri).casefold() for e in entries]
        if len(keys) != len(set(keys)):
            raise SourceManifestError(ManifestErrorCode.IDENTITY_CONFLICT)
        ordered = tuple(sorted(entries, key=lambda e: (e.logical_uri.casefold(), e.logical_uri)))
        object.__setattr__(self, "entries", ordered)
        accepted = tuple(e for e in ordered if e.acceptance is ManifestAcceptance.ACCEPTED)
        object.__setattr__(self, "accepted_count", len(accepted))
        object.__setattr__(self, "rejected_count", sum(e.acceptance is ManifestAcceptance.REJECTED for e in ordered))
        object.__setattr__(self, "unsupported_count", sum(e.acceptance is ManifestAcceptance.UNSUPPORTED for e in ordered))
        object.__setattr__(self, "accepted_bytes", sum(e.size_bytes for e in accepted))
        payload = self.to_dict(include_digest=False)
        object.__setattr__(self, "manifest_digest", hashlib.sha256(canonical_json(payload)).hexdigest())

    def to_dict(self, *, include_digest: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "schema_name": SCHEMA_NAME,
            "schema_version": SCHEMA_VERSION,
            "source_id": self.source_id,
            "created_at": self.created_at,
            "entries": [entry.to_dict() for entry in self.entries],
            "counts": {
                "accepted": self.accepted_count,
                "rejected": self.rejected_count,
                "unsupported": self.unsupported_count,
                "accepted_bytes": self.accepted_bytes,
            },
        }
        if include_digest:
            result["manifest_digest"] = self.manifest_digest
        return result

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())


def canonical_json(value: Mapping[str, object] | object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_fingerprint(data: bytes, *, text: bool = False) -> str:
    if text:
        data = normalize_text(data.decode("utf-8")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def build_manifest(source_root: str | Path, source_id: str, *, created_at: datetime | None = None,
                   max_file_bytes: int = 32 * 1024 * 1024, max_documents: int = 100,
                   allowed_formats: Iterable[str] = _SUPPORTED_FORMATS) -> SourceManifest:
    """Enumerate and fingerprint one source root without writing any artifact."""
    root = Path(source_root)
    allowed = frozenset(allowed_formats)
    entries: list[ManifestEntry] = []
    paths = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: normalize_logical_uri(p.relative_to(root).as_posix()).casefold())
    for path in paths:
        uri = normalize_logical_uri(path.relative_to(root).as_posix())
        declared = _declared_format(path)
        detected: str | None = None
        try:
            data = path.read_bytes()
            detected = detect_format(path, data)
            size = len(data)
            is_text = declared in {"md", "txt"} and detected == declared
            fingerprint = content_fingerprint(data, text=is_text)
            if declared in {"pdf", "pptx", "docx"} and detected != declared:
                acceptance, code, fmt = ManifestAcceptance.REJECTED, ManifestErrorCode.FORMAT_MISMATCH.value, detected or declared
            elif detected is None or detected not in _SUPPORTED_FORMATS or detected not in allowed:
                acceptance, code, fmt = ManifestAcceptance.UNSUPPORTED, ManifestErrorCode.FORMAT_UNSUPPORTED.value, detected or declared
            elif size > max_file_bytes:
                acceptance, code, fmt = ManifestAcceptance.REJECTED, ManifestErrorCode.SIZE_LIMIT_EXCEEDED.value, detected
            elif len([e for e in entries if e.acceptance is ManifestAcceptance.ACCEPTED]) >= max_documents:
                acceptance, code, fmt = ManifestAcceptance.REJECTED, ManifestErrorCode.SIZE_LIMIT_EXCEEDED.value, detected
            else:
                acceptance, code, fmt = ManifestAcceptance.ACCEPTED, None, detected
        except (OSError, UnicodeError):
            size = 0
            fingerprint = hashlib.sha256(b"").hexdigest()
            acceptance, code, fmt = ManifestAcceptance.REJECTED, ManifestErrorCode.UNREADABLE.value, declared
        entries.append(ManifestEntry(uri, _document_id(source_id, uri), SOURCE_TYPE, fmt, acceptance, size, fingerprint, reject_code=code))
    timestamp = created_at or datetime.now(timezone.utc)
    return SourceManifest(source_id, _timestamp(timestamp), tuple(entries))

# Friendly aliases used by callers/tests.
build_source_manifest = build_manifest
validate_manifest = lambda manifest: SourceManifest(manifest.source_id, manifest.created_at, manifest.entries)

__all__ = ["SCHEMA_NAME", "SCHEMA_VERSION", "SOURCE_TYPE", "ManifestAcceptance", "ManifestEntry", "SourceManifest", "SourceManifestError", "ManifestErrorCode", "normalize_text", "normalize_logical_uri", "detect_format", "content_fingerprint", "canonical_json", "build_manifest", "build_source_manifest", "validate_manifest"]
