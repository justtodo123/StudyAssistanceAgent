"""Startup-only configuration for static Markdown retrieval sources."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .protocols import ProtocolValidationError, SourceType, validate_source_id


class SourceConfigError(ValueError):
    """Safe startup failure whose text never includes a local source root."""

    code = "SOURCE_CONFIG_INVALID"


@dataclass(frozen=True, slots=True)
class StaticSourceConfig:
    source_id: str
    root: Path
    source_type: SourceType


@dataclass(frozen=True, slots=True)
class SourceLimits:
    max_files_per_source: int = 250
    max_files_total: int = 500
    max_bytes_per_source: int = 4 * 1024 * 1024
    max_bytes_total: int = 8 * 1024 * 1024
    max_chunks_per_source: int = 750
    max_extra_chunks_per_source: int = 600
    max_chunks_total: int = 1200
    max_file_bytes: int = 256 * 1024


_LIMIT_SPECS = {
    "SA_SOURCE_MAX_FILES_PER_SOURCE": ("max_files_per_source", 250, 500),
    "SA_SOURCE_MAX_FILES_TOTAL": ("max_files_total", 500, 1000),
    "SA_SOURCE_MAX_BYTES_PER_SOURCE": ("max_bytes_per_source", 4 * 1024 * 1024, 8 * 1024 * 1024),
    "SA_SOURCE_MAX_BYTES_TOTAL": ("max_bytes_total", 8 * 1024 * 1024, 16 * 1024 * 1024),
    "SA_SOURCE_MAX_CHUNKS_PER_SOURCE": ("max_chunks_per_source", 750, 1000),
    "SA_SOURCE_MAX_EXTRA_CHUNKS_PER_SOURCE": (
        "max_extra_chunks_per_source",
        600,
        1000,
    ),
    "SA_SOURCE_MAX_CHUNKS_TOTAL": ("max_chunks_total", 1200, 2000),
    "SA_SOURCE_MAX_FILE_BYTES": ("max_file_bytes", 256 * 1024, 512 * 1024),
}


def parse_source_limits(environment: Mapping[str, str] | None = None) -> SourceLimits:
    env = environment if environment is not None else os.environ
    values: dict[str, int] = {}
    for variable, (field_name, default, hard_max) in _LIMIT_SPECS.items():
        raw = env.get(variable, str(default))
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise SourceConfigError("source limits are invalid") from exc
        if value <= 0 or value > hard_max:
            raise SourceConfigError("source limits are invalid")
        values[field_name] = value
    limits = SourceLimits(**values)
    if (
        limits.max_files_per_source > limits.max_files_total
        or limits.max_bytes_per_source > limits.max_bytes_total
        or limits.max_chunks_per_source > limits.max_chunks_total
        or limits.max_extra_chunks_per_source > limits.max_chunks_total
        or limits.max_file_bytes > limits.max_bytes_per_source
    ):
        raise SourceConfigError("source limits are invalid")
    return limits


def parse_extra_sources(
    raw: str | None = None,
    *,
    default_root: Path,
    repository_root: Path,
    crawler_cache_root: Path | None = None,
) -> tuple[StaticSourceConfig, ...]:
    value = os.getenv("SA_EXTRA_SOURCES", "[]") if raw is None else raw
    try:
        entries = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise SourceConfigError("extra source configuration is invalid") from exc
    if not isinstance(entries, list) or len(entries) > 3:
        raise SourceConfigError("extra source configuration is invalid")

    configs: list[StaticSourceConfig] = []
    source_ids: set[str] = set()
    roots = [_resolve_directory(default_root)]
    repository_root = repository_root.resolve()
    forbidden = [
        (repository_root / ".git").resolve(),
        (repository_root / "platform").resolve(),
        (repository_root / "tests").resolve(),
    ]
    if crawler_cache_root is not None:
        forbidden.append(crawler_cache_root.resolve())

    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"source_id", "root", "source_type"}:
            raise SourceConfigError("extra source configuration is invalid")
        try:
            source_id = validate_source_id(entry["source_id"])
            source_type = SourceType(entry["source_type"])
        except (KeyError, TypeError, ValueError, ProtocolValidationError) as exc:
            raise SourceConfigError("extra source configuration is invalid") from exc
        if source_id in source_ids:
            raise SourceConfigError("extra source configuration is invalid")
        root_value = entry.get("root")
        if not isinstance(root_value, str) or not root_value.strip():
            raise SourceConfigError("extra source configuration is invalid")
        root = _resolve_directory(Path(root_value))
        if root == repository_root or any(_contains(blocked, root) for blocked in forbidden):
            raise SourceConfigError("extra source configuration is invalid")
        if any(_contains(existing, root) or _contains(root, existing) for existing in roots):
            raise SourceConfigError("extra source configuration is invalid")
        source_ids.add(source_id)
        roots.append(root)
        configs.append(StaticSourceConfig(source_id, root, source_type))
    return tuple(configs)


def parse_extra_sources_strict(value: str | None = None) -> bool:
    raw = os.getenv("SA_EXTRA_SOURCES_STRICT", "true") if value is None else value
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise SourceConfigError("extra source strict mode is invalid")


def _resolve_directory(path: Path) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SourceConfigError("source root is invalid") from exc
    if not resolved.is_dir():
        raise SourceConfigError("source root is invalid")
    try:
        next(resolved.iterdir(), None)
    except OSError as exc:
        raise SourceConfigError("source root is unreadable") from exc
    return resolved


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


__all__ = [
    "SourceConfigError",
    "SourceLimits",
    "StaticSourceConfig",
    "parse_extra_sources",
    "parse_extra_sources_strict",
    "parse_source_limits",
]
