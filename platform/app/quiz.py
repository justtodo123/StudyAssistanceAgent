"""测验生成服务：从知识条目例题、评测集、概念标签生成测验题目。

三个数据源：
1. 经典例题（knowledge 条目中 ## 经典例题 段落的 **题干**/**解答** 对）
2. 评测集（tools/evaluations/{course}.json 的检索问题）
3. 概念模板（从 tags 生成 "什么是 X？" 型问题）
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from . import config
from .knowledge_index import build_index_cached
from .models import QuizQuestion, QuizRequest, QuizResponse

_EXAMPLE_SECTION_RE = re.compile(
    r"## 经典例题.*?\n(.*?)(?=\n## |\Z)", re.DOTALL
)
_QA_PAIR_RE = re.compile(
    r"\*\*题干\*\*\s*[：:]\s*(.*?)\n\*\*解答\*\*\s*[：:]\s*(.*?)(?=\n\*\*题干\*\*|\Z)",
    re.DOTALL,
)

# 概念题模板：从 tags 生成
_CONCEPT_TEMPLATES = [
    "{tag}是什么？简述其核心概念。",
    "请解释{tag}的原理和作用。",
    "{tag}在实际系统中是如何应用的？",
    "比较{tag}与相关概念的区别。",
]


class QuizService:
    """测验生成器。"""

    def generate(self, req: QuizRequest) -> QuizResponse:
        """根据请求生成测验。"""
        # 收集三个数据源的题目
        pool: list[QuizQuestion] = []
        pool.extend(self._load_example_questions(req.course))
        pool.extend(self._load_retrieval_questions(req.course))
        pool.extend(self._load_concept_questions(req.course))

        # 按条件筛选
        filtered = self._filter(pool, req.difficulty, req.topics)

        # 随机采样
        count = min(req.count, len(filtered))
        if count > 0:
            questions = random.sample(filtered, count)
        else:
            questions = []

        # 统计
        by_type: dict[str, int] = {}
        for q in questions:
            by_type[q.type] = by_type.get(q.type, 0) + 1

        return QuizResponse(
            quiz_name=f"{req.course}-quiz",
            course=req.course,
            generated_at=datetime.now().isoformat(),
            count=len(questions),
            questions=questions,
            summary={
                "total_pool": len(pool),
                "filtered": len(filtered),
                "by_type": by_type,
                "tip": "example 题型含参考答案，concept/retrieval 题型供自测，可查阅对应知识条目验证。",
            },
        )

    # ── 数据源 1：经典例题 ────────────────────────────────────────────────────

    def _load_example_questions(self, course: str) -> list[QuizQuestion]:
        """从知识条目的 ## 经典例题 段落提取题干/解答对。"""
        chunks = build_index_cached()
        questions: list[QuizQuestion] = []
        seen_files: set[str] = set()

        for c in chunks:
            if c.course != course:
                continue
            if c.file in seen_files:
                continue
            # 读取原始文件内容（chunks 是按 ## 切分的，需要原文件来解析经典例题）
            seen_files.add(c.file)

        # 直接扫描文件
        root = config.KNOWLEDGE_ROOT / course
        if not root.exists():
            return questions

        for md in sorted(root.glob("*.md")):
            if md.name.startswith("_"):
                continue
            text = md.read_text(encoding="utf-8")
            meta = self._extract_meta(text)
            m = _EXAMPLE_SECTION_RE.search(text)
            if not m:
                continue
            section = m.group(1)
            for pair in _QA_PAIR_RE.finditer(section):
                q_text = pair.group(1).strip()
                a_text = pair.group(2).strip()
                if not q_text:
                    continue
                rel = f"knowledge/{course}/{md.name}"
                questions.append(
                    QuizQuestion(
                        question=q_text,
                        type="example",
                        answer=a_text,
                        source_file=rel,
                        source_title=meta.get("title", md.stem),
                        tags=meta.get("tags", []),
                        difficulty=meta.get("difficulty", "中等"),
                    )
                )

        return questions

    # ── 数据源 2：评测集 ──────────────────────────────────────────────────────

    def _load_retrieval_questions(self, course: str) -> list[QuizQuestion]:
        """从评测集 JSON 加载检索问题。"""
        eval_path = Path(__file__).resolve().parents[1] / ".." / "tools" / "evaluations" / f"{course}.json"
        if not eval_path.exists():
            return []

        try:
            data = json.loads(eval_path.read_text(encoding="utf-8"))
        except Exception:
            return []

        questions: list[QuizQuestion] = []
        for q_text, files in data.items():
            if not files:  # 无标注答案的跳过
                continue
            source = files[0] if files else ""
            questions.append(
                QuizQuestion(
                    question=q_text,
                    type="retrieval",
                    answer="",  # 评测集无答案，需查阅知识条目
                    source_file=source,
                    source_title="",
                    tags=[],
                    difficulty="中等",
                )
            )

        return questions

    # ── 数据源 3：概念模板 ────────────────────────────────────────────────────

    def _load_concept_questions(self, course: str) -> list[QuizQuestion]:
        """从知识条目的 tags 生成概念型问题。"""
        chunks = build_index_cached()
        # 收集该课程所有 tags（去重）
        all_tags: dict[str, str] = {}  # tag → source_file
        for c in chunks:
            if c.course != course:
                continue
            for tag in c.tags:
                if tag not in all_tags:
                    all_tags[tag] = c.file

        questions: list[QuizQuestion] = []
        for tag, source in all_tags.items():
            template = random.choice(_CONCEPT_TEMPLATES)
            questions.append(
                QuizQuestion(
                    question=template.format(tag=tag),
                    type="concept",
                    answer="",
                    source_file=source,
                    source_title="",
                    tags=[tag],
                    difficulty="中等",
                )
            )

        return questions

    # ── 筛选 ──────────────────────────────────────────────────────────────────

    def _filter(
        self,
        pool: list[QuizQuestion],
        difficulty: str | None,
        topics: list[str],
    ) -> list[QuizQuestion]:
        """按难度和标签筛选题目。"""
        result = pool
        if difficulty:
            result = [q for q in result if q.difficulty == difficulty]
        if topics:
            topic_set = set(topics)
            result = [
                q for q in result
                if topic_set & set(q.tags)
                or any(t in q.question for t in topics)
            ]
        return result

    # ── 工具方法 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_meta(text: str) -> dict[str, Any]:
        """从 Markdown frontmatter 提取元数据。"""
        from .knowledge_index import _parse_frontmatter

        return _parse_frontmatter(text)
