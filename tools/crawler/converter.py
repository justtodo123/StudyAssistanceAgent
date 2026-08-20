"""Markdown 转换器：将清洗后的纯文本转换为知识库条目格式。

输出遵循 knowledge/_templates/entry-template.md 的结构：
- frontmatter（title, course, tags, difficulty, updated, source_url）
- 正文结构（TL;DR → 核心概念 → 易错点 → 关联条目）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import yaml


@dataclass
class ArticleMeta:
    """文章元数据。"""
    title: str
    course: str
    tags: list[str] = field(default_factory=list)
    difficulty: str = "中等"
    source_url: str = ""


def to_knowledge_markdown(
    text: str,
    meta: ArticleMeta,
    *,
    template_mode: bool = True,
) -> str:
    """将纯文本转换为知识库 Markdown 格式。

    Args:
        text: 清洗后的纯文本内容
        meta: 文章元数据
        template_mode: 是否使用模板结构（TL;DR → 核心概念 → ...）

    Returns:
        完整的知识库 Markdown 文件内容
    """
    frontmatter = _build_frontmatter(meta)

    if template_mode:
        body = _structure_with_template(text, meta.title)
    else:
        body = text

    return f"---\n{frontmatter}---\n\n{body}\n"


def _build_frontmatter(meta: ArticleMeta) -> str:
    """构建 YAML frontmatter。"""
    data = {
        "title": meta.title,
        "course": meta.course,
        "tags": meta.tags,
        "difficulty": meta.difficulty,
        "updated": date.today().isoformat(),
    }
    if meta.source_url:
        data["source_url"] = meta.source_url

    return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _structure_with_template(text: str, title: str) -> str:
    """尝试将纯文本按模板结构组织。

    策略：
    - 如果原文已有 ## 标题结构，保留并补充缺失的模板节
    - 如果原文是连续文本，将其放入「核心概念」节
    """
    sections = _split_existing_sections(text)

    parts: list[str] = []

    # TL;DR
    tldr = sections.get("TL;DR") or sections.get("一句话概括") or _extract_first_sentences(text, 2)
    parts.append(f"## 一句话概括（TL;DR）\n\n> {tldr}")

    # 核心概念
    core = sections.get("核心概念") or sections.get("概述") or text[:min(len(text), 2000)]
    parts.append(f"## 核心概念\n\n{core}")

    # 关键原理（如果原文有的话）
    principle = sections.get("关键原理") or sections.get("算法") or sections.get("原理")
    if principle:
        parts.append(f"## 关键原理 / 算法\n\n{principle}")

    # 易错点
    pitfalls = sections.get("易错点") or sections.get("高频考点") or sections.get("注意事项")
    if pitfalls:
        parts.append(f"## 易错点 / 高频考点\n\n{pitfalls}")

    # 关联条目（占位）
    parts.append("## 关联条目\n\n- （待补充关联条目链接）")

    return "\n\n".join(parts)


def _split_existing_sections(text: str) -> dict[str, str]:
    """如果文本已有 ## 标题结构，按标题拆分为 dict。"""
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        heading_match = re.match(r"^##\s+(.+)$", line)
        if heading_match:
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = heading_match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def _extract_first_sentences(text: str, n: int = 2) -> str:
    """提取前 n 个句子作为 TL;DR。"""
    # 按中文句号或英文句号分句
    sentences = re.split(r"[。！？\.!?]", text)
    clean = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
    return "。".join(clean[:n]) + "。" if clean else text[:200]


def slug_from_title(title: str) -> str:
    """从中文标题生成 kebab-case 文件名。

    策略：用标签关键词拼接，或用拼音首字母。
    这里用简单的策略：去掉特殊字符，用 - 连接。
    """
    # 去掉括号和特殊符号
    slug = re.sub(r"[（）()《》<>「」【】\[\]{}]", "", title)
    # 用空格和中文标点分词
    slug = re.sub(r"[，。、；：\s]+", "-", slug)
    # 去掉首尾 -
    slug = slug.strip("-")
    # 如果太长，截断
    if len(slug) > 50:
        slug = slug[:50].rstrip("-")
    return slug or "untitled"
