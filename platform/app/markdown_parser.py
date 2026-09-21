"""Shared Markdown parsing primitives for default knowledge-pack consumers."""

from __future__ import annotations

import re
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_YAML_FIELD_RE = re.compile(r"^(\w[\w-]*)\s*:\s*(.*)$")
# 值按行内列表解码的键。其余键一律保留为字符串——刻意不「看到方括号就当列表」，
# 那会改变既有消费方对未知键的取值形态。
_LIST_FIELDS = frozenset({"tags", "prerequisites"})


def _decode_inline_list(value: str) -> list[str]:
    """`[a, b]` → `['a', 'b']`；非列表值按单项处理，空值得到空列表。

    只支持**行内**形式：块状 YAML（后续行写 `- a`）不匹配 `_YAML_FIELD_RE`，会被静默丢弃成
    空列表。该陷阱由 `tests/M9/test_topic_graph_projection.py` 的数据完整性用例钉住。
    """
    items = value.strip().strip("[]").split(",")
    return [item.strip().strip('"').strip("'") for item in items if item.strip()]


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
        if key in _LIST_FIELDS:
            value = _decode_inline_list(value)
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
