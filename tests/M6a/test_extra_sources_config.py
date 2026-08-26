"""M6a-3 startup configuration and strict static Markdown source tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.protocols import SourceType
from app.source_config import (
    SourceConfigError,
    SourceLimits,
    StaticSourceConfig,
    parse_extra_sources,
    parse_extra_sources_strict,
    parse_source_limits,
)
from app.sources.static_markdown import (
    SourceContentError,
    SourceLimitError,
    StaticMarkdownSource,
)

pytestmark = pytest.mark.m6a


def _write_note(
    root: Path,
    relative_path: str = "week-01.md",
    *,
    source_type: str = "human_markdown",
    body: str = "## Process\n\nA process owns resources and an execution context.",
) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"source_type: {source_type}\n"
        "ingest_status: approved\n"
        "course: os\n"
        "tags: [process]\n"
        "difficulty: basic\n"
        "updated: 2026-08-26\n"
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    return path


def _config(root: Path, source_id: str = "notes-1") -> StaticSourceConfig:
    return StaticSourceConfig(source_id, root.resolve(), SourceType.HUMAN_MARKDOWN)


def test_parse_extra_sources_accepts_exact_startup_schema(tmp_path: Path) -> None:
    default_root = tmp_path / "default"
    extra_root = tmp_path / "extra"
    default_root.mkdir()
    extra_root.mkdir()
    raw = json.dumps(
        [
            {
                "source_id": "notes-1",
                "root": str(extra_root),
                "source_type": "human_markdown",
            }
        ]
    )

    assert parse_extra_sources(
        raw,
        default_root=default_root,
        repository_root=tmp_path,
    ) == (_config(extra_root),)


@pytest.mark.parametrize(
    "raw",
    [
        "not-json",
        "{}",
        json.dumps([{"source_id": "notes-1", "root": "missing"}]),
        json.dumps(
            [
                {
                    "source_id": "notes-1",
                    "root": "missing",
                    "source_type": "human_markdown",
                    "extra": True,
                }
            ]
        ),
    ],
)
def test_invalid_extra_configuration_is_safe(tmp_path: Path, raw: str) -> None:
    default_root = tmp_path / "default"
    default_root.mkdir()

    with pytest.raises(SourceConfigError) as caught:
        parse_extra_sources(
            raw,
            default_root=default_root,
            repository_root=tmp_path,
        )

    assert str(tmp_path) not in str(caught.value)


def test_duplicate_ids_and_overlapping_roots_are_rejected(tmp_path: Path) -> None:
    default_root = tmp_path / "default"
    first = tmp_path / "first"
    nested = first / "nested"
    for root in (default_root, nested):
        root.mkdir(parents=True)
    duplicate = json.dumps(
        [
            {"source_id": "notes-1", "root": str(first), "source_type": "human_markdown"},
            {"source_id": "notes-1", "root": str(nested), "source_type": "human_markdown"},
        ]
    )
    overlap = json.dumps(
        [
            {"source_id": "notes-1", "root": str(first), "source_type": "human_markdown"},
            {"source_id": "notes-2", "root": str(nested), "source_type": "human_markdown"},
        ]
    )

    for raw in (duplicate, overlap):
        with pytest.raises(SourceConfigError):
            parse_extra_sources(
                raw,
                default_root=default_root,
                repository_root=tmp_path,
            )


def test_strict_and_limit_configuration_are_validated() -> None:
    assert parse_extra_sources_strict("true") is True
    assert parse_extra_sources_strict("no") is False
    with pytest.raises(SourceConfigError):
        parse_extra_sources_strict("sometimes")
    with pytest.raises(SourceConfigError):
        parse_source_limits({"SA_SOURCE_MAX_FILES_PER_SOURCE": "0"})


def test_static_source_is_relocation_stable_and_namespaced(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_note(first)
    _write_note(second)
    limits = SourceLimits()

    first_snapshot = StaticMarkdownSource(_config(first), limits).materialize()
    relocated_snapshot = StaticMarkdownSource(_config(second), limits).materialize()
    other_snapshot = StaticMarkdownSource(_config(second, "notes-2"), limits).materialize()

    assert first_snapshot.descriptor.generation == relocated_snapshot.descriptor.generation
    assert first_snapshot.chunks[0].chunk_id == relocated_snapshot.chunks[0].chunk_id
    assert first_snapshot.chunks[0].chunk_id != other_snapshot.chunks[0].chunk_id


def test_static_source_requires_approved_retrievable_content(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    invalid = tmp_path / "invalid"
    _write_note(invalid, body="short")

    with pytest.raises(SourceContentError):
        StaticMarkdownSource(_config(empty), SourceLimits()).materialize()
    with pytest.raises(SourceContentError):
        StaticMarkdownSource(_config(invalid), SourceLimits()).materialize()


def test_static_source_enforces_whole_source_limits(tmp_path: Path) -> None:
    root = tmp_path / "extra"
    _write_note(root)

    with pytest.raises(SourceLimitError):
        StaticMarkdownSource(
            _config(root),
            SourceLimits(max_file_bytes=20),
        ).materialize()
