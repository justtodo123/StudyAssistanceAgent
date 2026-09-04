"""M7 source-manifest contracts using only temporary source trees."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.source_manifest import (
    FINGERPRINT_ALGORITHM,
    SOURCE_TYPE,
    ManifestAcceptance,
    ManifestEntry,
    SourceManifest,
    SourceManifestError,
    build_manifest,
    content_fingerprint,
    normalize_logical_uri,
)

pytestmark = pytest.mark.m7

SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"
CREATED_AT = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)


def _document_id(logical_uri: str) -> str:
    return hashlib.sha256(f"{SOURCE_ID}\0{logical_uri}".encode("utf-8")).hexdigest()[:32]


def _entry(
    logical_uri: str,
    *,
    acceptance: ManifestAcceptance = ManifestAcceptance.ACCEPTED,
    format: str | None = "md",
    size_bytes: int = 1,
    content_fingerprint: str = "a" * 64,
    reject_code: str | None = None,
) -> ManifestEntry:
    if acceptance is not ManifestAcceptance.ACCEPTED and reject_code is None:
        reject_code = "SOURCE_FORMAT_UNSUPPORTED"
    return ManifestEntry(
        logical_uri=logical_uri,
        document_id=_document_id(logical_uri),
        source_type=SOURCE_TYPE,
        format=format,
        acceptance=acceptance,
        size_bytes=size_bytes,
        content_fingerprint=content_fingerprint,
        reject_code=reject_code,
    )


def test_manifest_text_fingerprint_is_portable_but_binary_is_byte_exact() -> None:
    composed = "课程\r\n  café\t内容  ".encode("utf-8")
    decomposed = "课程\n café 内容".replace("é", "e\u0301").encode("utf-8")

    assert content_fingerprint(composed, text=True) == content_fingerprint(decomposed, text=True)
    assert content_fingerprint(composed, text=False) != content_fingerprint(decomposed, text=False)


def test_manifest_rejects_nonportable_logical_uris() -> None:
    assert normalize_logical_uri("目录\\第一课.md") == "目录/第一课.md"

    for value in ("/private/note.md", "C:/private/note.md", "../note.md", "a//b.md", "a/\x00b.md"):
        with pytest.raises(SourceManifestError):
            normalize_logical_uri(value)


def test_manifest_entries_require_consistent_acceptance_and_fingerprint_contracts() -> None:
    accepted = _entry("accepted.md")
    assert accepted.acceptance is ManifestAcceptance.ACCEPTED
    assert accepted.fingerprint_algorithm == FINGERPRINT_ALGORITHM
    assert "reject_code" not in accepted.to_dict()

    rejected = _entry(
        "rejected.pdf",
        acceptance=ManifestAcceptance.REJECTED,
        format="pdf",
        reject_code="SOURCE_FORMAT_MISMATCH",
    )
    assert rejected.to_dict()["reject_code"] == "SOURCE_FORMAT_MISMATCH"

    with pytest.raises(SourceManifestError):
        _entry("bad.md", reject_code="SOURCE_PARSE_FAILED")
    with pytest.raises(SourceManifestError):
        ManifestEntry(
            logical_uri="bad.txt",
            document_id=_document_id("bad.txt"),
            source_type=SOURCE_TYPE,
            format="txt",
            acceptance=ManifestAcceptance.UNSUPPORTED,
            size_bytes=1,
            content_fingerprint="a" * 64,
            reject_code=None,
        )
    with pytest.raises(SourceManifestError):
        ManifestEntry(
            logical_uri="missing-format",
            document_id=_document_id("missing-format"),
            source_type=SOURCE_TYPE,
            format=None,
            acceptance=ManifestAcceptance.ACCEPTED,
            size_bytes=1,
            content_fingerprint="a" * 64,
        )
    with pytest.raises(SourceManifestError):
        ManifestEntry(
            logical_uri="bad.md",
            document_id=_document_id("bad.md"),
            source_type=SOURCE_TYPE,
            format="md",
            acceptance=ManifestAcceptance.ACCEPTED,
            size_bytes=1,
            content_fingerprint="not-a-digest",
        )


def test_manifest_is_canonical_sorted_and_counts_only_accepted_bytes() -> None:
    manifest = SourceManifest(
        SOURCE_ID,
        "2026-09-02T12:00:00.000000Z",
        (
            _entry("zeta.md", size_bytes=7),
            _entry("alpha.txt", size_bytes=3, format="txt"),
            _entry(
                "unsupported.bin",
                acceptance=ManifestAcceptance.UNSUPPORTED,
                format=None,
                size_bytes=19,
            ),
            _entry(
                "rejected.pdf",
                acceptance=ManifestAcceptance.REJECTED,
                format="pdf",
                size_bytes=23,
                reject_code="SOURCE_FORMAT_MISMATCH",
            ),
        ),
    )

    assert [entry.logical_uri for entry in manifest.entries] == [
        "alpha.txt",
        "rejected.pdf",
        "unsupported.bin",
        "zeta.md",
    ]
    assert (manifest.accepted_count, manifest.rejected_count, manifest.unsupported_count) == (2, 1, 1)
    assert manifest.accepted_bytes == 10
    assert manifest.to_dict()["counts"] == {
        "accepted": 2,
        "rejected": 1,
        "unsupported": 1,
        "accepted_bytes": 10,
    }
    assert manifest.canonical_bytes() == SourceManifest(
        SOURCE_ID,
        "2026-09-02T12:00:00.000000Z",
        tuple(reversed(manifest.entries)),
    ).canonical_bytes()


def test_manifest_rejects_identity_casefold_conflicts_and_noncanonical_timestamps() -> None:
    with pytest.raises(SourceManifestError):
        SourceManifest(
            SOURCE_ID,
            "2026-09-02T12:00:00.000000Z",
            (_entry("Week.md"), _entry("week.md")),
        )

    with pytest.raises(SourceManifestError):
        SourceManifest(SOURCE_ID, "2026-09-02T12:00:00+00:00", (_entry("week.md"),))

    with pytest.raises(SourceManifestError):
        SourceManifest(
            SOURCE_ID,
            "2026-09-02T12:00:00.000000Z",
            (
                ManifestEntry(
                    logical_uri="week.md",
                    document_id="f" * 32,
                    source_type=SOURCE_TYPE,
                    format="md",
                    acceptance=ManifestAcceptance.ACCEPTED,
                    size_bytes=1,
                    content_fingerprint="a" * 64,
                ),
            ),
        )


def test_build_manifest_uses_runtime_files_and_never_records_source_root(tmp_path: Path) -> None:
    source_root = tmp_path / "private-source-root"
    source_root.mkdir()
    (source_root / "lesson.md").write_text("# 第一课\r\n\r\n内容", encoding="utf-8")
    (source_root / "large.txt").write_text("超过限制", encoding="utf-8")
    (source_root / "unknown.bin").write_bytes(b"\x00\x01")

    manifest = build_manifest(
        source_root,
        SOURCE_ID,
        created_at=CREATED_AT,
        max_file_bytes=8,
    )
    entries = {entry.logical_uri: entry for entry in manifest.entries}

    assert entries["lesson.md"].acceptance is ManifestAcceptance.REJECTED
    assert entries["lesson.md"].reject_code == "SOURCE_FILE_LIMIT_EXCEEDED"
    assert entries["large.txt"].acceptance is ManifestAcceptance.REJECTED
    assert entries["unknown.bin"].acceptance is ManifestAcceptance.UNSUPPORTED
    assert entries["unknown.bin"].reject_code == "SOURCE_FORMAT_UNSUPPORTED"
    assert str(source_root) not in manifest.canonical_bytes().decode("utf-8")
