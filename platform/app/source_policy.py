"""Data-source types and ingest gates.

Searchable knowledge is an allowlist. Crawler and AI output start as candidates
and never become retrievable until human review plus explicit promotion.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from . import config


class SourceType(StrEnum):
    HUMAN_MARKDOWN = "human_markdown"
    WEB_CANDIDATE = "web_candidate"
    WEB_REVIEWED = "web_reviewed"
    AI_DRAFT = "ai_draft"
    USER_REGISTERED = "user_registered"


class IngestStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"


SEARCHABLE_SOURCE_TYPES = {
    SourceType.HUMAN_MARKDOWN,
    SourceType.WEB_REVIEWED,
    SourceType.USER_REGISTERED,
}

SKIP_DIR_NAMES = {"_templates", "_inbox"}

DEFAULT_CANDIDATE_ROOT = config.REPO_ROOT / "platform" / ".cache" / "crawler-candidates"


class SourceIngestDenied(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "SOURCE_INGEST_DENIED"


def default_crawler_output_dir(course: str) -> Path:
    return DEFAULT_CANDIDATE_ROOT / (course or "unknown")


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def assert_crawler_output_allowed(
    output_dir: Path,
    *,
    allow_knowledge_write: bool = False,
) -> None:
    if allow_knowledge_write:
        return
    knowledge_root = config.KNOWLEDGE_ROOT
    if not is_under(output_dir, knowledge_root):
        return
    rel = output_dir.resolve().relative_to(knowledge_root.resolve())
    if rel.parts and rel.parts[0] == "_inbox":
        return
    raise SourceIngestDenied(
        "crawler output cannot write into knowledge/; use "
        "platform/.cache/crawler-candidates or knowledge/_inbox after review"
    )


def is_indexable_relative_path(rel_posix: str) -> bool:
    parts = [part for part in rel_posix.split("/") if part]
    return not any(part in SKIP_DIR_NAMES for part in parts)


def is_indexable_frontmatter(meta: dict) -> bool:
    raw_type = str(meta.get("source_type") or SourceType.HUMAN_MARKDOWN).strip()
    raw_status = str(meta.get("ingest_status") or IngestStatus.APPROVED).strip()
    try:
        source_type = SourceType(raw_type)
    except ValueError:
        source_type = SourceType.HUMAN_MARKDOWN
    try:
        ingest_status = IngestStatus(raw_status)
    except ValueError:
        ingest_status = IngestStatus.APPROVED
    return ingest_status == IngestStatus.APPROVED and source_type in SEARCHABLE_SOURCE_TYPES
