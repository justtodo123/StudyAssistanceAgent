"""Markdown local-reference parsing and validation helpers."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


_LINK_RE = re.compile(r"\[[^]]*\]\(([^)]+)\)")
_EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:")


def _heading_slug(text: str) -> str:
    """Return the GitHub-style slug used for a Markdown heading."""
    text = re.sub(r"<[^>]+>", "", text)
    text = unquote(text).strip().lower()
    text = re.sub(r"[^\w\-一-鿿 ]+", "", text, flags=re.UNICODE)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def _heading_slugs(text: str) -> set[str]:
    """Return GitHub-style slugs, including duplicate-heading suffixes."""
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for match in re.finditer(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", text, re.MULTILINE):
        base = _heading_slug(match.group(1))
        if not base:
            continue
        occurrence = counts.get(base, 0)
        candidate = base if occurrence == 0 else f"{base}-{occurrence}"
        while candidate in slugs:
            occurrence += 1
            candidate = f"{base}-{occurrence}"
        counts[base] = occurrence + 1
        slugs.add(candidate)
    return slugs


def local_markdown_references(text: str):
    """Yield decoded local Markdown targets and optional fragments."""
    for raw_link in _LINK_RE.findall(text):
        link = raw_link.strip().split(maxsplit=1)[0].strip("<>\"")
        if not link or link.startswith(_EXTERNAL_SCHEMES):
            continue
        target, separator, fragment = link.partition("#")
        yield unquote(target), unquote(fragment) if separator else None


def assert_local_markdown_target(
    reference: str,
    base_directory: Path,
    repo_root: Path,
) -> None:
    """Assert one repository-relative file/directory reference and optional anchor."""
    target_name, separator, fragment = reference.partition("#")
    assert target_name, f"empty repository reference: {reference!r}"
    assert not Path(target_name).is_absolute(), f"absolute reference: {reference!r}"
    assert not re.match(r"^[A-Za-z]:[\\/]", target_name), (
        f"absolute reference: {reference!r}"
    )
    assert not target_name.startswith(("/", "\\\\")), (
        f"absolute reference: {reference!r}"
    )

    target = (base_directory / unquote(target_name)).resolve()
    resolved_root = repo_root.resolve()
    assert target.is_relative_to(resolved_root), f"reference escapes repository: {reference!r}"
    assert target.exists(), f"missing repository reference: {reference!r}"
    if not separator:
        return

    assert fragment, f"empty anchor: {reference!r}"
    assert target.is_file(), f"anchor target is not a file: {reference!r}"
    slugs = _heading_slugs(target.read_text(encoding="utf-8"))
    normalized_fragment = _heading_slug(fragment)
    assert normalized_fragment in slugs, f"missing anchor: {reference!r}"


def assert_local_markdown_references(document: Path, repo_root: Path) -> None:
    """Assert local files and fragments resolve without ambiguous headings."""
    text = document.read_text(encoding="utf-8")
    for target_name, fragment in local_markdown_references(text):
        if not target_name:
            target_name = document.name
        reference = target_name if fragment is None else f"{target_name}#{fragment}"
        assert_local_markdown_target(reference, document.parent, repo_root)
