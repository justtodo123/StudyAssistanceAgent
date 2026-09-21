"""M9 只读先修关系（topic graph）投影：知识条目之间的先修边。

只读（领域级）：不写知识库、不写学习会话、不构建 chunk 索引、不读 chunk 正文。权威写入仍是知识条目
自身（frontmatter 由人工维护），本模块只解析与校验，不改任何生产文件。

数据来源是条目 frontmatter 的 `prerequisites:` 行内列表，值是**与依赖条目同目录的兄弟文件 stem**：

    knowledge/os/segmentation-paging.md:
        prerequisites: [memory-management]

**为什么是「同目录兄弟」而不是「同课程」**：`knowledge/interview/co/` 是嵌套目录，全树有多个 basename
撞名（`cache-mapping`、`heap-priority-queue`、`sorting`、`stack-queue`），而 `GoalPlanRequest.course`
默认 `None` 表示覆盖全部课程。按课程解析会把 `co` 的先修**确定性地**连到 `interview/co` 的同名文件上，
且因为是确定性的，不会引发任何 flaky 测试来暴露它。同目录解析无歧义。

**只支持行内方括号形式**：块状 YAML（后续行写 `- a`）不匹配 `markdown_parser._YAML_FIELD_RE`，
会被静默解析成空列表。该陷阱由 `tests/M9/test_topic_graph_projection.py` 的数据完整性用例钉住。

**丢弃而非补**：目标条目不存在、自环、含 `/` 或 `\\` 或以 `.md` 结尾的 stem、`_templates`/`_inbox`、
无 `title` 的文件一律**丢弃该边**，不猜测、不补 0——与 `mastery_projection` 的「不可映射则排除」
同一纪律。
"""

from __future__ import annotations

from collections import deque
from pathlib import PurePosixPath
from typing import Any

from . import config
from .markdown_parser import parse_frontmatter

TOPIC_GRAPH_SCHEMA_VERSION = "m9-topic-graph-v1"
_KNOWLEDGE_PREFIX = "knowledge/"
# 与 `source_policy.SKIP_DIR_NAMES` 同名同义：模板与待审候选不进入检索，也不进入先修图。
_SKIP_DIR_NAMES = frozenset({"_templates", "_inbox"})


class TopicGraphProjection:
    """先修关系只读投影。刻意不缓存：图必须反映当前条目内容。"""

    def graph(self) -> dict[str, frozenset[str]]:
        """`file -> 先修 file 集合`，键为**全部在场条目**（无边者为空集）。

        边已与在场条目求交：指向不存在条目的先修在本投影里**不存在**，而不是留一个悬空引用。
        """
        edges, _ = self._scan()
        return edges

    def unorderable(self) -> frozenset[str]:
        """无法被拓扑排序的文件集 = **参与环或环下游**。

        Kahn 剩余集就是这两者的并集，本方法刻意不冒充精确 SCC，故不叫 `cyclic`——与
        `source_summary_projection` 把集合叫 `usable` 而不叫 `authorized` 同一纪律。

        注意这是**图级**诊断：Planner 侧「强制释放」的剩余集是按本计划任务集算的，两者不同名同义，
        调用方不要混用。
        """
        _, stuck = self._scan()
        return stuck

    def _scan(self) -> tuple[dict[str, frozenset[str]], frozenset[str]]:
        """一次遍历同时得出边集与不可排序集，避免两个公开方法各读一次而互相漂移。"""
        root = config.KNOWLEDGE_ROOT
        if not root.exists():
            return {}, frozenset()

        present: set[str] = set()
        declared: dict[str, list[str]] = {}
        for path in sorted(root.rglob("*.md")):
            rel = path.relative_to(root).as_posix()
            parts = rel.split("/")
            if path.name == "README.md" or _SKIP_DIR_NAMES.intersection(parts[:-1]):
                continue
            meta = parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            if not meta.get("title"):
                continue
            file_key = f"{_KNOWLEDGE_PREFIX}{rel}"
            present.add(file_key)
            declared[file_key] = _stems(meta.get("prerequisites"))

        edges: dict[str, frozenset[str]] = {}
        for file_key, stems in declared.items():
            parent = PurePosixPath(file_key).parent
            targets = set()
            for stem in stems:
                if not _is_bare_stem(stem):
                    continue
                target = f"{parent}/{stem}.md"
                # 自环丢弃：一个条目把自己列为先修既无意义，也会让 Kahn 永远排不出它。
                if target != file_key and target in present:
                    targets.add(target)
            edges[file_key] = frozenset(targets)
        return edges, _unorderable(edges)


def _stems(value: Any) -> list[str]:
    """把 frontmatter 取值归一成 stem 列表。

    解析器对本模块关心的键返回列表；标量写法返回裸字符串；空值返回 `""`。三者都要接受，
    因为「标量」无歧义，不算猜测。
    """
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _is_bare_stem(stem: str) -> bool:
    """裸 slug 校验：带路径分隔符或带 `.md` 后缀一律视为不存在，不猜其意图。"""
    if not stem or stem.endswith(".md"):
        return False
    if "/" in stem or "\\" in stem:
        return False
    return stem not in (".", "..")


def _unorderable(edges: dict[str, frozenset[str]]) -> frozenset[str]:
    """Kahn 剩余集：排不出去的节点 = 参与环或环下游。"""
    indegree = {node: len(prereqs) for node, prereqs in edges.items()}
    dependents: dict[str, list[str]] = {node: [] for node in edges}
    for node, prereqs in edges.items():
        for prereq in prereqs:
            dependents[prereq].append(node)

    ready = deque(node for node, degree in indegree.items() if degree == 0)
    emitted = 0
    while ready:
        node = ready.popleft()
        emitted += 1
        for dependent in dependents[node]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)

    if emitted == len(edges):
        return frozenset()
    return frozenset(node for node, degree in indegree.items() if degree > 0)
