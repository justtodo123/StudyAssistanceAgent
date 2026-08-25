"""Shared Markdown parsing primitives for default knowledge-pack consumers."""

from __future__ import annotations

import re
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_YAML_FIELD_RE = re.compile(r"^(\w[\w-]*)\s*:\s*(.*)$")


def parse_frontmatter(text: str) -> dict[str, Any]:
    """解析 Markdown 开头 YAML frontmatter，容错失败（不完整则返回空）。"""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        field = _YAML_FIELD_RE.match(line.strip())
        if not field:
            continue
        key, value = field.group(1), field.group(2).strip().strip('"').strip("'")
        if key == "tags":
            value = [tag.strip().strip('"') for tag in value.strip("[]").split(",") if tag.strip()]
        else:
            value = value.strip()
        data[key] = value
    return data


def split_headings(text: str) -> list[tuple[str, str]]:
    """按 ## 标题切分为小节，返回 [(title, body)]，至少保留一个整块。"""
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                sections.append((current_title, current))
            current_title = line[3:].strip()
            current = []
        else:
            current.append(line)
    if current or not sections:
        sections.append((current_title, current))
    return [(title, "\n".join(body).strip()) for title, body in sections if "\n".join(body).strip()]
