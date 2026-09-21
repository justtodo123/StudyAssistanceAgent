"""M9 只读先修关系（topic graph）投影测试。

覆盖五类主张：
- **解析**：只支持行内方括号形式；块状 YAML 被静默丢弃（真实陷阱，必须钉住）；
  `tags` 的既有解码行为逐字节不变。
- **投影**：先修解析为**同目录兄弟**文件；悬空边、自环、越界 stem、模板/待审目录、无 title 文件一律丢弃；
  `graph()` 的键是全部在场条目（无边者为空集）；`unorderable()` 是 Kahn 剩余集（环 ∪ 环下游）。
- **只读与有界**：零文件系统写入、每个条目恰好解析一次、**刻意不缓存**。
- **与确定性 Planner 的接缝（本设计的命门）**：未注入图 / 注入空图 / 空操作投影三者产出逐字节相同；
  注入真图产出拓扑序且 `violations == 0`；三种违反成因（环、被排除的先修、置顶冲突）都有用例。
- **知识数据完整性**：60 条课程条目全部声明该键、只用行内形式、**无悬空边**、真语料 `unorderable` 为空。

本文件自带合成知识树夹具（`monkeypatch` 指向 `config.KNOWLEDGE_ROOT`），不写仓库内的任何知识文件。
"""

from __future__ import annotations

import hashlib
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest

from app import config
from app.goal_planner import GoalPlannerService
from app.learning_store import SqliteLearningStore
from app.markdown_parser import parse_frontmatter
from app.mastery_projection import MasteryProjectionService
from app.models import GoalPlanConstraints, GoalPlanRequest
from app.topic_graph_projection import (
    TOPIC_GRAPH_SCHEMA_VERSION,
    TopicGraphProjection,
    _is_bare_stem,
)

import app.topic_graph_projection as topic_graph_projection


pytestmark = pytest.mark.m9

_COURSES = ("os", "ds", "co")
_OS_SYNC = "knowledge/os/synchronization.md"
_OS_DEADLOCK = "knowledge/os/deadlock.md"
_OS_PROCESS = "knowledge/os/process-management.md"
_OS_SCHED = "knowledge/os/process-scheduling.md"


# ── 工具 ──────────────────────────────────────────────────────────────────────


def _entry(
    title: str,
    *,
    course: str = "os",
    prereqs: list[str] | None = None,
    difficulty: str = "中等",
    body: str = "",
) -> str:
    """构造一个与真实课程条目同形的知识条目文本（LF 结尾）。"""
    lines = [
        "---",
        f"title: {title}",
        f"course: {course}",
        "tags: [测试]",
        f"difficulty: {difficulty}",
        "updated: 2026-09-21",
        "source: docs/reference/test.md",
    ]
    if prereqs is not None:
        lines.append("prerequisites: [" + ", ".join(prereqs) + "]")
    lines += ["---", "", f"# {title}", "", body]
    return "\n".join(lines) + "\n"


@contextmanager
def _tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, files: dict[str, str]
) -> Iterator[Path]:
    """写一棵合成知识树并把 `config.KNOWLEDGE_ROOT` 指过去。

    同时影响 `TopicGraphProjection._scan` 与 `GoalPlannerService._load_entries`（两者都读同一配置），
    因此可以端到端地测「图 → 计划顺序」而完全不碰仓库知识库。
    """
    root = tmp_path / "knowledge"
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    monkeypatch.setattr(config, "KNOWLEDGE_ROOT", root)
    yield root


def _tree_state(root: Path) -> dict[str, str]:
    """路径 → 内容摘要；用于断言只读（内容与文件集合都不变）。"""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _request(**kwargs: Any) -> GoalPlanRequest:
    defaults: dict[str, Any] = {"goal": "两周内掌握进程调度与死锁", "course": "os"}
    defaults.update(kwargs)
    return GoalPlanRequest(**defaults)


def _order(plan: Any) -> list[str]:
    return [t.file for d in plan.revisions[0].days for t in d.tasks]


class _StaticGraph:
    """返回固定边集的假投影；用于注入受控的图（含环）。"""

    def __init__(self, edges: dict[str, frozenset[str]]) -> None:
        self._edges = edges

    def graph(self) -> dict[str, frozenset[str]]:
        return self._edges


class _CountingGraph:
    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.calls = 0

    def graph(self) -> dict[str, frozenset[str]]:
        self.calls += 1
        return self._inner.graph()


def _course_entries(repo_root: Path) -> list[Path]:
    return [
        path
        for course in _COURSES
        for path in sorted((repo_root / "knowledge" / course).glob("*.md"))
        if path.name != "README.md"
    ]


# ── A. frontmatter 解析 ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [
        ("[a, b]", ["a", "b"]),
        ("[a]", ["a"]),
        ("[]", []),
        ("", []),
        ("a", ["a"]),
        ('["a", "b"]', ["a", "b"]),
        ("['a', 'b']", ["a", "b"]),
        ("[ a ,  b ]", ["a", "b"]),
        ("[a, , b]", ["a", "b"]),
        ("[段页式, 虚拟内存]", ["段页式", "虚拟内存"]),
    ],
)
def test_inline_list_forms(value: str, expected: list[str]) -> None:
    assert parse_frontmatter(f"---\nprerequisites: {value}\n---\n")["prerequisites"] == expected


def test_missing_key_is_absent_not_empty() -> None:
    """缺键与 `[]` 在取值形态上可区分；投影层把两者都当空集。"""
    frontmatter = parse_frontmatter("---\ntitle: t\n---\n")

    assert "prerequisites" not in frontmatter


def test_block_form_is_silently_dropped() -> None:
    """真实陷阱：块状 YAML 不匹配 `_YAML_FIELD_RE`，被静默解析成空列表。

    这正是 `tests/M9` 的数据完整性用例必须按**原始文件**断言只用行内形式的原因——解析器不会报错。
    """
    text = "---\ntitle: t\nprerequisites:\n  - a\n  - b\n---\n"

    assert parse_frontmatter(text)["prerequisites"] == []


def test_tags_decoding_is_unchanged() -> None:
    """抽出共用 helper 不得改变既有 `tags` 取值形态。"""
    frontmatter = parse_frontmatter("---\ntags: [分页, 分段]\ntitle: t\n---\n")

    assert frontmatter["tags"] == ["分页", "分段"]
    assert frontmatter["title"] == "t"


def test_non_list_fields_are_not_decoded() -> None:
    """刻意不「看到方括号就当列表」：未知键的取值形态必须与接入前一致。"""
    frontmatter = parse_frontmatter("---\nrelated: [a, b]\n---\n")

    assert frontmatter["related"] == "[a, b]"


@pytest.mark.parametrize("stem,expected", [("a", True), ("", False), ("a.md", False), ("a/b", False), ("a\\b", False), (".", False), ("..", False)])
def test_bare_stem_validation(stem: str, expected: bool) -> None:
    assert _is_bare_stem(stem) is expected


# ── B. 投影解析规则 ───────────────────────────────────────────────────────────


def test_edges_resolve_to_sibling_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`graph()` 的键是**全部在场条目**，无边者为空集。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/a.md": _entry("A", prereqs=None),
            "os/b.md": _entry("B", prereqs=["a"]),
        },
    ):
        graph = TopicGraphProjection().graph()

    assert graph == {
        "knowledge/os/a.md": frozenset(),
        "knowledge/os/b.md": frozenset({"knowledge/os/a.md"}),
    }


def test_same_basename_in_a_nested_directory_stays_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """同目录解析的决定性用例：`interview/os/` 与 `os/` 各有 `cache-mapping`，先修不得跨目录连边。

    按「同课程」解析会把 `os` 的先修确定性地连到 `interview/os` 的同名文件上；因为是确定性的，
    不会有任何 flaky 测试暴露它。
    """
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/cache-mapping.md": _entry("Cache 映射", prereqs=["memory-system"]),
            "os/memory-system.md": _entry("存储系统"),
            "interview/os/cache-mapping.md": _entry("面经 Cache", prereqs=["memory-system"]),
            "interview/os/memory-system.md": _entry("面经存储"),
        },
    ):
        graph = TopicGraphProjection().graph()

    assert graph["knowledge/os/cache-mapping.md"] == frozenset({"knowledge/os/memory-system.md"})
    assert graph["knowledge/interview/os/cache-mapping.md"] == frozenset(
        {"knowledge/interview/os/memory-system.md"}
    )


@pytest.mark.parametrize("stem", ["missing", "a/b", "a\\b", "a.md", ".", "..", "A"])
def test_unresolvable_stems_are_dropped_not_guessed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stem: str
) -> None:
    """丢弃而非补：悬空、越界、大小写不符的 stem 都不产生边（也不产生错误）。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {"os/a.md": _entry("A"), "os/b.md": _entry("B", prereqs=[stem])},
    ):
        graph = TopicGraphProjection().graph()

    assert graph["knowledge/os/b.md"] == frozenset()


def test_self_loop_is_dropped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with _tree(tmp_path, monkeypatch, {"os/a.md": _entry("A", prereqs=["a"])}):
        projection = TopicGraphProjection()

        assert projection.graph()["knowledge/os/a.md"] == frozenset()
        assert projection.unorderable() == frozenset()


def test_duplicate_stems_collapse_to_one_edge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _tree(
        tmp_path,
        monkeypatch,
        {"os/a.md": _entry("A"), "os/b.md": _entry("B", prereqs=["a", "a", "a"])},
    ):
        graph = TopicGraphProjection().graph()

    assert graph["knowledge/os/b.md"] == frozenset({"knowledge/os/a.md"})


@pytest.mark.parametrize("relative", ["_templates/x.md", "_inbox/y.md", "os/_templates/z.md"])
def test_skipped_directories_never_enter_the_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: str
) -> None:
    """模板与待审候选不进检索，也不进先修图。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {"os/a.md": _entry("A"), relative: _entry("X", prereqs=["a"])},
    ):
        graph = TopicGraphProjection().graph()

    assert set(graph) == {"knowledge/os/a.md"}


def test_readme_and_titleless_files_are_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """README 与无 frontmatter 的文件不进入图；指向它们的先修也随之丢弃。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/README.md": _entry("课程导航"),
            "os/plain.md": "# 没有 frontmatter\n",
            "os/b.md": _entry("B", prereqs=["README", "plain", "missing"]),
        },
    ):
        graph = TopicGraphProjection().graph()

    assert set(graph) == {"knowledge/os/b.md"}
    assert graph["knowledge/os/b.md"] == frozenset()


def test_absent_knowledge_root_yields_an_empty_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """根不存在是守卫，不是错误。"""
    monkeypatch.setattr(config, "KNOWLEDGE_ROOT", tmp_path / "does-not-exist")
    projection = TopicGraphProjection()

    assert projection.graph() == {}
    assert projection.unorderable() == frozenset()


def test_graph_is_not_cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """docstring 声称「刻意不缓存」：图必须反映当前条目内容，而不是首次扫描的快照。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {"os/a.md": _entry("A"), "os/b.md": _entry("B")},
    ) as root:
        projection = TopicGraphProjection()
        assert projection.graph()["knowledge/os/b.md"] == frozenset()

        (root / "os" / "b.md").write_text(
            _entry("B", prereqs=["a"]), encoding="utf-8", newline="\n"
        )

        assert projection.graph()["knowledge/os/b.md"] == frozenset({"knowledge/os/a.md"})


def test_graph_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/a.md": _entry("A"),
            "os/b.md": _entry("B", prereqs=["a"]),
            "os/c.md": _entry("C", prereqs=["a", "b"]),
        },
    ):
        projection = TopicGraphProjection()

        assert projection.graph() == projection.graph()
        assert projection.unorderable() == projection.unorderable()


def test_schema_version_is_declared() -> None:
    assert TOPIC_GRAPH_SCHEMA_VERSION == "m9-topic-graph-v1"


# ── C. unorderable：环与环下游 ────────────────────────────────────────────────


def test_cycle_and_its_downstream_are_unorderable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`unorderable` 是 Kahn 剩余集 = 环 ∪ 环下游；刻意不叫 `cyclic`，它不冒充精确 SCC。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/a.md": _entry("A", prereqs=["b"]),
            "os/b.md": _entry("B", prereqs=["a"]),
            "os/c.md": _entry("C", prereqs=["a"]),
            "os/free.md": _entry("Free"),
        },
    ):
        projection = TopicGraphProjection()

        assert projection.unorderable() == frozenset(
            {"knowledge/os/a.md", "knowledge/os/b.md", "knowledge/os/c.md"}
        )
        # 环上的边仍然被报告，投影不因环而丢弃它们
        assert projection.graph()["knowledge/os/a.md"] == frozenset({"knowledge/os/b.md"})


def test_acyclic_graph_has_no_unorderable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with _tree(
        tmp_path,
        monkeypatch,
        {"os/a.md": _entry("A"), "os/b.md": _entry("B", prereqs=["a"])},
    ):
        assert TopicGraphProjection().unorderable() == frozenset()


# ── D. 只读与有界 ─────────────────────────────────────────────────────────────


def test_projection_preserves_the_knowledge_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """领域级只读：内容与文件集合都不变，且调用窗口内任何写入口都被换成 fail。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/a.md": _entry("A"),
            "os/b.md": _entry("B", prereqs=["a"]),
            "os/c.md": _entry("C", prereqs=["b"]),
        },
    ) as root:
        before = _tree_state(root)
        for name in ("write_text", "write_bytes", "unlink", "touch", "mkdir", "rename", "replace"):
            monkeypatch.setattr(
                Path,
                name,
                lambda *a, _n=name, **k: pytest.fail(f"projection attempted Path.{_n}"),
                raising=False,
            )
        projection = TopicGraphProjection()
        graph = projection.graph()
        stuck = projection.unorderable()
        after = _tree_state(root)

    assert graph["knowledge/os/c.md"] == frozenset({"knowledge/os/b.md"})
    assert stuck == frozenset()
    assert before == after


def test_each_entry_is_parsed_exactly_once_per_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """有界输入：`_scan` 一次遍历，`graph()` 不得顺手把每个文件读两遍。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/a.md": _entry("A"),
            "os/b.md": _entry("B", prereqs=["a"]),
            "os/c.md": _entry("C", prereqs=["a"]),
        },
    ):
        calls = {"n": 0}
        original = topic_graph_projection.parse_frontmatter

        def counted(text: str) -> dict[str, Any]:
            calls["n"] += 1
            return original(text)

        monkeypatch.setattr(topic_graph_projection, "parse_frontmatter", counted)

        TopicGraphProjection().graph()

    assert calls["n"] == 3


def test_planner_reads_the_graph_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """整轮只读一次：生成途中图若变化，排序与违反计数会基于不同快照。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {"os/a.md": _entry("A"), "os/b.md": _entry("B", prereqs=["a"])},
    ):
        counter = _CountingGraph(TopicGraphProjection())
        planner = GoalPlannerService(topic_graph=counter)

        planner.generate(_request())
        assert counter.calls == 1

        planner.generate(_request())
        assert counter.calls == 2


# ── E. Planner 接缝：空图等价于无图 ───────────────────────────────────────────


def test_empty_graph_is_byte_identical_to_no_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`None` / 注入空图 / **空操作投影**三者：顺序、`plan_id`、`summary` 全等。

    既有 M9 用例只覆盖 `None`，这条不变量此前无人钉。`summary` 里新增的 `prerequisites`
    键是唯一差异，且它的值必须是零——「注入了空图」不等于「没注入」，键的存在性即证据。

    「空操作投影」用一棵**无先修声明**的合成树上的真投影，而不是 `knowledge/os/` 上的真投影：
    后者非空，本就该产出不同顺序。混为一谈会把「等价于无图」错当成「等价于任何图」。
    """
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/a.md": _entry("A"),
            "os/b.md": _entry("B"),
            "os/c.md": _entry("C", difficulty="进阶"),
        },
    ):
        baseline = GoalPlannerService().generate(_request())
        variants = [
            GoalPlannerService(topic_graph=_StaticGraph({})).generate(_request()),
            GoalPlannerService(topic_graph=TopicGraphProjection()).generate(_request()),
        ]

    assert "prerequisites" not in baseline.summary
    for plan in variants:
        assert plan.plan_id == baseline.plan_id
        assert _order(plan) == _order(baseline)
        assert plan.revisions[0].days == baseline.revisions[0].days
        assert {k: v for k, v in plan.summary.items() if k != "prerequisites"} == baseline.summary
        assert plan.summary["prerequisites"] == {"edges": 0, "violations": 0}


def test_empty_graph_reports_zero_rather_than_omitting_the_key() -> None:
    """键的出现取决于**输入**（是否注入图），不取决于图是否为空。"""
    plan = GoalPlannerService(topic_graph=_StaticGraph({})).generate(_request())

    assert plan.summary["prerequisites"] == {"edges": 0, "violations": 0}


def test_empty_graph_ordering_matches_the_full_four_tuple(tmp_path: Path) -> None:
    """无图路径用**完整 4 元组**复核排序。

    既有 `test_response_without_projection_matches_legacy_ordering` 用的是去掉 mastery 桶的
    3 元组，抓不住「堆键漏了 mastery」这类回归；这里独立重建 4 元组（不复用 `_order_key`），
    并用真实 mastery / review 状态让四个键都具备区分度。
    """
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    store.save(
        {
            "session_id": "s1",
            "course": "os",
            "topic": "",
            "state": "completed",
            "score": None,
            "sources": [{"file": _OS_PROCESS}],
            "questions": [],
            "created_at": "2026-09-01T08:00:00",
            "updated_at": "2026-09-01T08:05:00",
            "answer_records": [
                {
                    "question_id": "q1",
                    "attempt_count": 1,
                    "answer_normalized": "q1",
                    "correct": True,
                    "feedback": "",
                    "created_at": "2026-09-01T09:00:00",
                }
            ],
        }
    )
    planner = GoalPlannerService(
        review_history={_OS_SCHED: {"review_count": 1}},
        mastery_projection=MasteryProjectionService(store),
        topic_graph=_StaticGraph({}),
    )

    plan = planner.generate(_request())
    tasks = [t for d in plan.revisions[0].days for t in d.tasks]

    def mastery_bucket(task: Any) -> int:
        if task.mastery_attempts <= 0:
            return 0
        return 1 if task.mastery_correct <= 0 else 2

    difficulty_rank = {"high": 0, "medium": 1, "low": 2}
    expected = sorted(
        tasks,
        key=lambda t: (t.reviewed, mastery_bucket(t), difficulty_rank.get(t.priority, 1), t.file),
    )

    assert [t.file for t in tasks] == [t.file for t in expected]
    assert len({(t.reviewed, mastery_bucket(t)) for t in tasks}) > 1  # 断言本身有区分度


# ── F. Planner 接缝：真图产出拓扑序 ───────────────────────────────────────────


def test_real_corpus_graph_yields_a_topological_order() -> None:
    """M9 退出判据「先修违反=0」的正面证据：真实语料 + 真实投影 ⇒ 零违反。"""
    projection = TopicGraphProjection()
    graph = projection.graph()
    planner = GoalPlannerService(topic_graph=projection)

    plan = planner.generate(_request(course="os"))
    order = _order(plan)
    position = {file: index for index, file in enumerate(order)}
    present = set(order)

    for file, prereqs in graph.items():
        if file not in present:
            continue
        for prereq in prereqs:
            if prereq in present:
                assert position[prereq] < position[file], f"{prereq} 必须先于 {file}"

    expected_edges = sum(1 for f in present for p in graph[f] if p in present)
    assert plan.summary["prerequisites"] == {"edges": expected_edges, "violations": 0}
    assert expected_edges > 0  # 否则「零违反」是空话


def test_prerequisite_outranks_the_base_ordering_keys() -> None:
    """拓扑序必然打破「未复习全部排在已复习之前」这一**局部**保证。

    已复习的先修仍必须排在未复习的依赖之前——这是图注入后刻意引入的新语义，由本用例钉住。
    """
    planner = GoalPlannerService(
        review_history={_OS_SYNC: {"review_count": 1}},
        topic_graph=TopicGraphProjection(),
    )

    order = _order(planner.generate(_request(course="os")))

    assert order.index(_OS_SYNC) < order.index(_OS_DEADLOCK)


def test_excluded_prerequisite_produces_no_violation_and_no_dangling_edge() -> None:
    """被 `excluded_topics` 移除的先修：该边在本计划内不存在，故不计违反、也不留悬空。

    若 in-degree 用原始计数，被排除的先修会让入度永远 > 0，把「先修缺失」伪装成「环」。
    """
    projection = TopicGraphProjection()
    graph = projection.graph()
    excluded_title = "内存管理"
    planner = GoalPlannerService(topic_graph=projection)

    plan = planner.generate(
        _request(course="os", constraints=GoalPlanConstraints(excluded_topics=[excluded_title]))
    )
    order = _order(plan)
    present = set(order)

    assert "knowledge/os/memory-management.md" not in present
    assert "knowledge/os/segmentation-paging.md" in present  # 依赖仍被调度，未被卡住
    expected_edges = sum(1 for f in present for p in graph[f] if p in present)
    assert plan.summary["prerequisites"] == {"edges": expected_edges, "violations": 0}
    assert expected_edges < sum(len(v) for v in graph.values())  # 确实少了边，不是空断言


def test_cycle_is_force_released_and_counted_as_a_violation() -> None:
    """环：Planner 保证终止与可重放，不静默修复；违反由 `violations` 报告。"""
    cyclic = _StaticGraph(
        {
            _OS_SYNC: frozenset({_OS_DEADLOCK}),
            _OS_DEADLOCK: frozenset({_OS_SYNC}),
        }
    )
    planner = GoalPlannerService(topic_graph=cyclic)

    first = planner.generate(_request())
    second = planner.generate(_request())

    assert first.summary["prerequisites"] == {"edges": 2, "violations": 1}
    assert first.plan_id == second.plan_id
    assert _order(first) == _order(second)
    assert len(_order(first)) == len(_order(second)) == 20  # 全序，无节点丢失


# ── G. Planner 接缝：置顶与先修的交互 ─────────────────────────────────────────


def test_pin_required_respects_prerequisites_inside_the_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """块内必须再跑一次拓扑排序：朴素按用户优先级排会产出 `[B, A]`，违反 A→B 这条边。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/a.md": _entry("A 先修"),
            "os/b.md": _entry("B 依赖", prereqs=["a"]),
            "os/z.md": _entry("Z 无关"),
        },
    ):
        graph = TopicGraphProjection()
        plan = GoalPlannerService(topic_graph=graph).generate(
            _request(course="os", constraints=GoalPlanConstraints(required_topics=["B 依赖", "A 先修"]))
        )

    assert plan.summary["prerequisites"] == {"edges": 1, "violations": 0}
    assert _order(plan)[:2] == ["knowledge/os/a.md", "knowledge/os/b.md"]


def test_pin_required_pulls_the_transitive_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """闭包必须**传递**：一级闭包会让「先修的先修」留在块外，静默破坏全局序。

    `z` 难度更高（排序键更靠前），所以「整块前移」若没发生，`z` 就会排在链前面。
    """
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/a.md": _entry("A 先修"),
            "os/b.md": _entry("B 中间", prereqs=["a"]),
            "os/c.md": _entry("C 必选", prereqs=["b"]),
            "os/z.md": _entry("Z 高难", difficulty="进阶"),
        },
    ):
        graph = TopicGraphProjection()
        pinned = GoalPlannerService(topic_graph=graph).generate(
            _request(course="os", constraints=GoalPlanConstraints(required_topics=["C 必选"]))
        )
        unpinned = GoalPlannerService().generate(
            _request(course="os", constraints=GoalPlanConstraints(required_topics=["C 必选"]))
        )

    assert _order(pinned) == [
        "knowledge/os/a.md",
        "knowledge/os/b.md",
        "knowledge/os/c.md",
        "knowledge/os/z.md",
    ]
    assert pinned.summary["prerequisites"]["violations"] == 0
    # 未注入图时退回今日语义：只有必选主题自己被置顶，其先修留在原处
    assert _order(unpinned)[0] == "knowledge/os/c.md"


def test_unrelated_required_topics_keep_the_user_rank_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """有先修边但必选主题彼此无关时，块内顺序仍是用户优先级顺序。

    短路分支的门是 `not edges` 而不是「闭包没新增节点」，所以这条路径走的是内层 Kahn；
    它的键必须退化为 `(用户优先级, 入参下标)`，与接入前的 `sorted` 稳定排序逐字符相同。
    """
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/a.md": _entry("A"),
            "os/b.md": _entry("B", prereqs=["a"]),
            "os/x.md": _entry("X 必选"),
            "os/y.md": _entry("Y 必选"),
        },
    ):
        plan = GoalPlannerService(topic_graph=TopicGraphProjection()).generate(
            _request(
                course="os",
                constraints=GoalPlanConstraints(required_topics=["Y 必选", "X 必选"]),
            )
        )

    # 用户把 Y 排在 X 之前，两者无先修关系 → 保持用户顺序
    assert _order(plan)[:2] == ["knowledge/os/y.md", "knowledge/os/x.md"]


def test_required_topic_absent_from_the_task_set_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """必选主题不在任务集内时与接入前一致地忽略它，不报错也不凭空造任务。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {"os/a.md": _entry("A"), "os/b.md": _entry("B", prereqs=["a"])},
    ):
        plan = GoalPlannerService(topic_graph=TopicGraphProjection()).generate(
            _request(course="os", constraints=GoalPlanConstraints(required_topics=["不存在的主题"]))
        )

    assert set(_order(plan)) == {"knowledge/os/a.md", "knowledge/os/b.md"}
    assert plan.summary["prerequisites"] == {"edges": 1, "violations": 0}


def test_excluded_topic_wins_over_pinning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """优先级裁定：用户显式排除优先于图边——被排除的必选主题不产生边，也不产生违反。"""
    with _tree(
        tmp_path,
        monkeypatch,
        {
            "os/a.md": _entry("A 先修"),
            "os/b.md": _entry("B 依赖", prereqs=["a"]),
        },
    ):
        plan = GoalPlannerService(topic_graph=TopicGraphProjection()).generate(
            _request(
                course="os",
                constraints=GoalPlanConstraints(
                    required_topics=["B 依赖"], excluded_topics=["A 先修"]
                ),
            )
        )

    assert _order(plan) == ["knowledge/os/b.md"]
    assert plan.summary["prerequisites"] == {"edges": 0, "violations": 0}


# ── H. 知识数据完整性（真语料） ───────────────────────────────────────────────


def test_every_course_entry_declares_prerequisites(repo_root: Path) -> None:
    entries = _course_entries(repo_root)

    assert len(entries) == 60
    for path in entries:
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8-sig"))
        assert "prerequisites" in frontmatter, f"{path.name} 缺 prerequisites"
        assert isinstance(frontmatter["prerequisites"], list), f"{path.name} 未解析成列表"


def test_prerequisites_use_the_inline_bracket_form_only(repo_root: Path) -> None:
    """按**原始文件**断言：块状 YAML 会被解析器静默丢成空列表，只有这里能拦住它。"""
    for path in _course_entries(repo_root):
        lines = [
            line
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.startswith("prerequisites:")
        ]
        assert len(lines) == 1, f"{path.name} 应恰好有一行 prerequisites"
        assert re.fullmatch(r"prerequisites: \[[^\]]*\]", lines[0]), f"{path.name}: {lines[0]!r}"


def test_real_corpus_has_no_dangling_edges(repo_root: Path) -> None:
    """每一条声明的 stem 都必须解析成真实兄弟文件——拼错一个词就会在这里失败。"""
    graph = TopicGraphProjection().graph()

    for path in _course_entries(repo_root):
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8-sig"))
        declared = frontmatter["prerequisites"]
        resolved = graph[f"knowledge/{path.parent.name}/{path.stem}.md"]
        assert len(resolved) == len(declared), (
            f"{path.name}: 声明 {declared}，只解析出 {sorted(resolved)}"
        )


def test_real_corpus_is_acyclic_and_fully_covered(repo_root: Path) -> None:
    projection = TopicGraphProjection()
    graph = projection.graph()

    assert projection.unorderable() == frozenset()
    assert set(graph) >= {
        f"knowledge/{path.parent.name}/{path.stem}.md" for path in _course_entries(repo_root)
    }
    for course in _COURSES:
        edges = sum(
            len(prereqs) for file, prereqs in graph.items() if file.startswith(f"knowledge/{course}/")
        )
        assert edges > 0, f"{course} 没有任何先修边"
    # network/ 与 interview/ 不在本次范围：无声明即无边
    for other in ("network", "interview"):
        edges = sum(
            len(prereqs) for file, prereqs in graph.items() if file.startswith(f"knowledge/{other}/")
        )
        assert edges == 0


# ── I. 模块守卫 ───────────────────────────────────────────────────────────────


def test_module_is_bounded_by_source() -> None:
    """源码级护栏：不 import 检索/生成链路，不出现正文相关符号，也不含任何写入口。"""
    import app.topic_graph_projection as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("knowledge_index", "llm_client", "split_headings", "content"):
        assert forbidden not in source, f"topic graph 不应出现 {forbidden!r}"
    for write_api in ("write_text", "write_bytes", "unlink", "mkdir", "shutil"):
        assert write_api not in source, f"只读投影不应出现 {write_api!r}"
