"""确定性目标驱动学习计划服务（M9 第一增量）。

只做计划生成：基于 Goal + 约束 + 只读复习历史、只读 mastery 投影与只读先修关系投影，
产出版本化、可重放的分日计划。不写 mastery、不写学习状态、不引入外部 AI、不读原始 chunk 正文。
"""

from __future__ import annotations

import hashlib
import heapq
import re
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any

from . import config
from .markdown_parser import parse_frontmatter
from .models import (
    GoalPlanConstraints,
    GoalPlanDay,
    GoalPlanRequest,
    GoalPlanResponse,
    GoalPlanRevision,
    GoalPlanTask,
)

SCHEMA_VERSION = "m9-goal-plan-v1"
DIFFICULTY_TIME: dict[str, int] = {"入门": 25, "中等": 35, "进阶": 50}
DIFFICULTY_PRIORITY: dict[str, str] = {"入门": "low", "中等": "medium", "进阶": "high"}
_DIFFICULTY_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}
REVIEW_BUFFER_MINUTES = 10


class GoalPlannerService:
    """确定性目标驱动计划生成器。"""

    def __init__(
        self,
        review_history: dict[str, dict[str, Any]] | None = None,
        mastery_projection: Any | None = None,
        source_summary: Any | None = None,
        topic_graph: Any | None = None,
    ) -> None:
        # review_history 是 file -> {review_count,...} 的只读投影，仅用于排序优先；
        # 不写回、不新建表。缺省空表表示“全部未复习”。
        self._review_history = review_history or {}
        # 权威 mastery 只读投影（只需实现 mastery_by_file()）。传**活对象**而非快照：
        # 快照会让 mastery 在进程生命周期内不更新，派生摘要永不变化，过期计划被幂等分支静默保留。
        self._mastery_projection = mastery_projection
        # 授权 Source 只读摘要投影（只需实现 summaries(principal_id)）。与 mastery 同为活对象、
        # 可空；缺省即不产出 `summary["sources"]`，接入前所有调用方的响应逐字节不变。
        self._source_summary = source_summary
        # 先修关系只读投影（只需实现 graph()）。追加在**末尾**——插在 source_summary 之前会
        # 静默重绑位置参数调用方。缺省即不产出 `summary["prerequisites"]`，排序退回接入前的形态。
        self._topic_graph = topic_graph

    def _mastery(self) -> dict[str, dict[str, Any]]:
        """权威 mastery 只读投影；未注入时返回空表（等价于接入前的行为）。"""
        if self._mastery_projection is None:
            return {}
        return self._mastery_projection.mastery_by_file()

    def _source_scope(self, principal_id: str | None) -> dict[str, dict[str, Any]]:
        """授权 Source 只读摘要；投影未注入或 principal 为假时返回空表。

        与 `_mastery` 同形：依赖缺省是守卫，不是错误。principal 为空时不查控制面，
        因此也不存在「无主体的目录」这种状态。
        """
        if self._source_summary is None or not principal_id:
            return {}
        return self._source_summary.summaries(principal_id)

    def _graph(self) -> dict[str, frozenset[str]]:
        """先修关系只读投影；未注入时返回空表（等价于接入前的行为）。

        与 `_mastery` 同形：依赖缺省是守卫，不是错误。空图让 `_stable_order` 走显式短路分支，
        输出与接入前的 `sorted()` 逐字节相同——这是既有 M9 测试不受影响的**结构**原因。
        """
        if self._topic_graph is None:
            return {}
        return self._topic_graph.graph()

    def generate(
        self, req: GoalPlanRequest, principal_id: str | None = None
    ) -> GoalPlanResponse:
        """根据 Goal 请求生成版本化计划。

        `principal_id` 只影响 `summary["sources"]` 这一处只读计数：它不进入任务载荷、不进入
        分日、也不进入 `_plan_id`。刻意如此——Source 目录变化不改变计划内容，让它 churn 计划身份
        会让正在采纳中的计划被无谓孤立（与 `_derived_digest` 只摘要计划范围内任务同一原则）。
        """
        # 1. 载入条目并去重到 topic（file）粒度，保持稳定顺序
        entries = self._load_entries(req.course)
        # 2. 应用话题约束：先排除，再确定排序，最后置顶必选（保持置顶不被排序破坏）
        entries = self._exclude(entries, req.constraints.excluded_topics)
        mastery = self._mastery()  # 整轮只读一次：保证确定性，且只查一次库
        # 授权 Source 摘要：同样整轮只读一次。它不参与任务构造与排序，只落进 summary 计数。
        source_scope = self._source_scope(principal_id)
        # 先修图同样整轮只读一次：生成途中图若变化，排序与违反计数会基于不同快照。
        graph = self._graph()
        tasks = self._build_tasks(entries, mastery)
        tasks = self._stable_order(tasks, graph)
        tasks = self._pin_required(tasks, req.constraints.required_topics, graph)
        # 4. 解析目标日期
        today = datetime.now().date()
        if req.target_date:
            target = datetime.strptime(req.target_date, "%Y-%m-%d").date()
        else:
            target = today + timedelta(days=14)
        total_days = max((target - today).days, 1)
        # 5. 贪心分日
        daily_minutes = int(req.hours_per_day * 60)
        days = self._distribute(tasks, today, total_days, daily_minutes)
        # 6. 确定性 plan_id（goal 归一化 + 目标日期 + 课程 + 每日学时 + 约束 + 派生输入摘要）
        plan_id = self._plan_id(
            req.goal, target, req.course, req.constraints, req.hours_per_day, tasks
        )
        total_task_minutes = sum(t.estimated_minutes for t in tasks)
        summary: dict[str, Any] = {
            "total_tasks": len(tasks),
            "reviewed": sum(1 for t in tasks if t.reviewed),
            "unreviewed": sum(1 for t in tasks if not t.reviewed),
            "by_difficulty": _count_by(tasks, "difficulty"),
            # 只读 mastery 投影的粗粒度分布；与 _stable_order 共用 _mastery_rank 这一处定义
            "mastery": {
                "no_evidence": sum(1 for t in tasks if _mastery_rank(t) == 0),
                "attempted": sum(1 for t in tasks if _mastery_rank(t) == 1),
                "mastered": sum(1 for t in tasks if _mastery_rank(t) == 2),
            },
        }
        # 出现条件取决于**输入**（有 principal 且注入了投影），不取决于结果是否有可用源：否则
        # 「键不存在」会同时意味着「没传 principal」和「传了但一个可用源都没有」，调用方无法区分。
        # 未传 principal 时 summary 与接入前逐字节一致。
        # 值只报可用源数，不报被排除的源数——排除是构造性的（隐藏态由 list_sources 的 WHERE 挡掉），
        # 投影无法报告它，凭空补一个 0 会把「没读」伪装成「读了且为空」。
        if self._source_summary is not None and principal_id:
            summary["sources"] = {"usable": len(source_scope)}
        # 同一条「键的出现取决于输入」规则：未注入图时不产出该键，否则「键不存在」会同时意味着
        # 「没注入图」和「注入了空图」，调用方无法区分。未注入时 summary 与接入前逐字节一致。
        if self._topic_graph is not None:
            summary["prerequisites"] = _prerequisite_report(tasks, graph)
        return GoalPlanResponse(
            plan_id=plan_id,
            schema_version=SCHEMA_VERSION,
            revision_id=1,
            target_date=str(target),
            total_days=len(days),
            total_hours=round(total_task_minutes / 60, 1),
            revisions=[
                GoalPlanRevision(
                    revision_id=1,
                    generated_at=datetime.now().isoformat(),
                    goal=req.goal,
                    days=days,
                )
            ],
            summary=summary,
            # 请求回显：计划自描述，重规划按此还原范围，不依赖调用方另传上下文
            course=req.course,
            hours_per_day=req.hours_per_day,
            constraints=req.constraints,
        )

    # ── 内部方法 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _load_entries(course: str | None) -> list[dict[str, Any]]:
        """载入课程条目，按 file 去重，标题取自 frontmatter 而非小节标题。

        只读 frontmatter（文件头），不读 chunk 正文，保持输入有界。
        """
        root = config.KNOWLEDGE_ROOT
        entries: OrderedDict[str, dict[str, Any]] = OrderedDict()
        if not root.exists():
            return []
        for path in sorted(root.rglob("*.md")):
            rel = path.relative_to(root).as_posix()
            if course and not rel.startswith(f"{course}/"):
                continue
            if path.name == "README.md":
                continue
            meta = parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            if not meta.get("title"):
                continue
            entries[rel] = {
                "file": f"knowledge/{rel}",
                "topic": str(meta["title"]),
                "difficulty": str(meta.get("difficulty", "") or "中等"),
                "tags": list(meta.get("tags", [])),
            }
        return list(entries.values())

    @staticmethod
    def _exclude(entries: list[dict[str, Any]], excluded_topics: list[str]) -> list[dict[str, Any]]:
        excluded = [t.lower() for t in excluded_topics]
        return [
            e for e in entries
            if not any(term in e["topic"].lower() for term in excluded)
        ]

    def _pin_required(
        self,
        tasks: list[GoalPlanTask],
        required_topics: list[str],
        graph: dict[str, frozenset[str]] | None = None,
    ) -> list[GoalPlanTask]:
        """把必选主题置顶，但**先修优先**：必选主题 ∪ 其传递先修闭包构成置顶块。

        闭包必须**传递**：块对先修封闭 ⇒ 没有边从块外进入 ⇒ 整块前移不可能违反任何边。一级闭包
        （只收直接先修）会让「先修的更上一层先修」留在块外，静默破坏全局序。

        块内**必须再跑一次拓扑排序**：朴素按用户优先级排序是错的——required `[B(0), A(1)]` 而 A 是
        B 的先修时，直接排会产出 `[B, A]`，违反那条边。内层 Kahn 的键用 `(用户优先级, 入参下标)`，
        **不是 `file`**：今日靠 `sorted` 的稳定性处理同名必选主题，改用 `file` 会在那一刻偏离。
        闭包遍历带 `seen`，否则环上死循环。

        短路分支的门是 **`not edges`**（无先修边，含未注入图），不是「闭包没新增节点」。两者不等价：
        必选主题互为先修时（required `[B(0), A(1)]` 且 A 是 B 的先修），闭包恰好只含这两个节点，
        但块内**存在**边——按「闭包没新增」走 `sorted` 就会产出 `[B, A]` 并违反那条边。无先修边时
        `pinned` 恒等于必选主题集，且内层 Kahn 的键退化为 `(user_rank, 入参下标)`，与 `sorted` 的稳定
        排序结果逐字符相同，故该短路纯属可指认的优化，不改变接入前的行为。
        """
        required = [t.lower() for t in required_topics]
        if not required:
            return tasks
        rank = {t: i for i, t in enumerate(required)}
        user_rank = {t.file: rank[t.topic.lower()] for t in tasks if t.topic.lower() in rank}
        if not user_rank:
            # 必选主题不在任务集内：与接入前一致地忽略它，而不是报错或凭空造任务。
            return tasks
        edges = self._present_edges(tasks, graph) if graph else {}
        index = {t.file: i for i, t in enumerate(tasks)}

        pinned = set(user_rank)
        stack = list(user_rank)
        while stack:
            for prereq in edges.get(stack.pop(), ()):
                if prereq not in pinned:
                    pinned.add(prereq)
                    stack.append(prereq)

        if not edges:
            block = sorted(
                (t for t in tasks if t.file in user_rank), key=lambda t: user_rank[t.file]
            )
        else:
            block = self._kahn(
                [t for t in tasks if t.file in pinned],
                edges,
                key=lambda t: (user_rank.get(t.file, len(required)), index[t.file]),
            )
        return block + [t for t in tasks if t.file not in pinned]

    def _build_tasks(
        self,
        entries: list[dict[str, Any]],
        mastery: dict[str, dict[str, Any]] | None = None,
    ) -> list[GoalPlanTask]:
        mastery = mastery or {}
        tasks: list[GoalPlanTask] = []
        for e in entries:
            diff = e["difficulty"]
            minutes = DIFFICULTY_TIME.get(diff, 35)
            priority = DIFFICULTY_PRIORITY.get(diff, "medium")
            reviewed = e["file"] in self._review_history
            evidence = mastery.get(e["file"]) or {}
            tasks.append(
                GoalPlanTask(
                    task_id=_task_id(e["file"]),
                    topic=e["topic"],
                    file=e["file"],
                    difficulty=diff,
                    estimated_minutes=minutes,
                    priority=priority,
                    tags=e.get("tags", []),
                    reviewed=reviewed,
                    mastery_attempts=int(evidence.get("attempts", 0)),
                    mastery_correct=int(evidence.get("correct", 0)),
                    mastery_last_mastered=evidence.get("last_mastered"),
                )
            )
        return tasks

    @staticmethod
    def _stable_order(
        tasks: list[GoalPlanTask],
        graph: dict[str, frozenset[str]] | None = None,
    ) -> list[GoalPlanTask]:
        """确定性排序：先修约束优先，其内按「未复习优先 → mastery 证据由少到多 → 难度优先级降序 → file 字典序」。

        mastery 桶只细化同一 `reviewed` 桶内的相对顺序；`reviewed` 仍是主键（它是最强的已学信号）。
        未注入投影时全部任务落在桶 0，排序结果与接入前逐字节一致——这是既有 M9 测试不受影响的
        **结构**原因，不是巧合。

        注入先修图后，`reviewed` 不再是全局主键：**已复习的先修必须排在未复习的依赖之前**，这是
        拓扑序的必然结果。无图时该断言仍逐字成立，图注入后由 `tests/M9/` 的对应用例钉住新语义。
        """
        if not graph:
            # 显式短路，而不是依赖「Kahn 在空图上恰好退化」：把逐字节相同从巧合升级为可指认的性质，
            # 并让 None 与 {} 走同一条路径，不会各自漂移。
            return sorted(tasks, key=_order_key)
        return GoalPlannerService._kahn(tasks, GoalPlannerService._present_edges(tasks, graph), key=_order_key)

    @staticmethod
    def _present_edges(
        tasks: list[GoalPlanTask],
        graph: dict[str, frozenset[str]],
    ) -> dict[str, frozenset[str]]:
        """把先修图限制到**本计划的任务集**。

        必须求交：先修若被 `excluded_topics` 移除，它在任务集里就不存在，该边在本计划内也不存在。
        用原始计数会让 in-degree 永远 > 0，把「先修缺失」伪装成「环」，再被强制释放机制吞掉。
        求交同时确立了「用户显式排除优先于图边」这一优先级裁定。
        """
        files = {t.file for t in tasks}
        return {
            file: frozenset(p for p in graph.get(file, ()) if p in files)
            for file in files
        }

    @staticmethod
    def _kahn(
        tasks: list[GoalPlanTask],
        edges: dict[str, frozenset[str]],
        key,
    ) -> list[GoalPlanTask]:
        """Kahn 拓扑排序 + 确定性堆。

        堆键是 `(key(task), task.file)`。`file` 唯一（`_load_entries` 按相对路径去重），故全序、无并列，
        且 `heapq` 永远不会去比较 `GoalPlanTask` 对象本身（那会 TypeError）。必须用堆而不是队列：
        队列会让输出依赖邻接表的插入顺序。

        环上的节点在主循环结束后按堆键顺序**强制释放**并继续，保证输出是全序且确定性；本方法不
        静默修复环——环本身由图投影的 `unorderable()` 报告，计划侧只保证终止与可重放。
        """
        by_file = {t.file: t for t in tasks}
        indegree = {f: sum(1 for p in edges.get(f, ()) if p in by_file) for f in by_file}
        dependents: dict[str, list[str]] = {f: [] for f in by_file}
        for file, prereqs in edges.items():
            if file not in by_file:
                continue
            for prereq in prereqs:
                if prereq in dependents:
                    dependents[prereq].append(file)

        def entry(file: str):
            return (key(by_file[file]), file)

        heap = [entry(f) for f, degree in indegree.items() if degree == 0]
        heapq.heapify(heap)
        ordered: list[GoalPlanTask] = []
        emitted: set[str] = set()
        while len(ordered) < len(tasks):
            if not heap:
                stuck = min((f for f in by_file if f not in emitted), key=entry)
                indegree[stuck] = 0
                heapq.heappush(heap, entry(stuck))
            _, file = heapq.heappop(heap)
            ordered.append(by_file[file])
            emitted.add(file)
            for dependent in dependents[file]:
                if dependent in emitted:
                    continue
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    heapq.heappush(heap, entry(dependent))
        return ordered

    @staticmethod
    def _distribute(
        tasks: list[GoalPlanTask],
        start_date,
        total_days: int,
        daily_minutes: int,
    ) -> list[GoalPlanDay]:
        days: list[GoalPlanDay] = []
        task_idx = 0
        for d in range(total_days):
            current_date = start_date + timedelta(days=d)
            available = daily_minutes
            if d > 0:
                available -= REVIEW_BUFFER_MINUTES
            available = max(available, 0)

            day_tasks: list[GoalPlanTask] = []
            used = 0
            while task_idx < len(tasks):
                t = tasks[task_idx]
                if used + t.estimated_minutes > available and day_tasks:
                    break
                day_tasks.append(t)
                used += t.estimated_minutes
                task_idx += 1

            days.append(
                GoalPlanDay(
                    day=d + 1,
                    date=str(current_date),
                    tasks=day_tasks,
                    total_minutes=used + (REVIEW_BUFFER_MINUTES if d > 0 and day_tasks else 0),
                )
            )
            if task_idx >= len(tasks):
                break

        if task_idx < len(tasks):
            remaining = tasks[task_idx:]
            extra_date = start_date + timedelta(days=total_days)
            days.append(
                GoalPlanDay(
                    day=len(days) + 1,
                    date=str(extra_date),
                    tasks=remaining,
                    total_minutes=sum(t.estimated_minutes for t in remaining),
                )
            )
        return days

    @staticmethod
    def _plan_id(
        goal: str,
        target,
        course: str | None = None,
        constraints: GoalPlanConstraints | None = None,
        hours_per_day: float = 2.0,
        tasks: list[GoalPlanTask] | None = None,
    ) -> str:
        """计划身份：请求字段 + 最终任务列表的派生输入摘要。

        身份必须覆盖所有影响任务集合、排序与分日的输入，否则：
          - 同名 Goal 配不同约束会撞同一 plan_id，后生成的计划被 `persist_generated`
            的幂等分支静默丢弃；
          - 同一请求在复习/mastery 状态变化后会撞同一 plan_id，已存计划永远停在旧排序上
            （本增量修复的已证实缺陷）。

        `hours_per_day` 属请求字段却经 `_distribute` 决定分日，漏掉它会让「顺序对、分日错」的
        计划共用身份，故并入请求键。刻意**不含生成日期**：它只影响分日日期锚点与 total_days，
        含它会让正在采纳中的计划每天被孤立——这是一处显式记录的残留（旧计划的日期锚定在生成时刻）。
        """
        constraints = constraints or GoalPlanConstraints()
        normalized = re.sub(r"\s+", " ", goal.strip()).lower()
        key = "|".join(
            [
                normalized,
                target.isoformat(),
                course or "",
                f"{float(hours_per_day):.4f}",
                ",".join(constraints.required_topics),
                ",".join(constraints.excluded_topics),
            ]
        )
        return hashlib.sha256(
            f"{key}|{_derived_digest(tasks or [])}".encode("utf-8")
        ).hexdigest()[:16]


def _order_key(task: GoalPlanTask):
    """无先修约束时的排序键：未复习优先 → mastery 证据由少到多 → 难度优先级降序 → file 字典序。

    单点定义：`_stable_order` 与 `_pin_required` 的内层拓扑排序共用它，避免两处键漂移。
    """
    return (
        task.reviewed,  # False(未复习) 排前
        _mastery_rank(task),
        _DIFFICULTY_RANK.get(task.priority, 1),
        task.file,
    )


def _prerequisite_report(
    tasks: list[GoalPlanTask],
    graph: dict[str, frozenset[str]],
) -> dict[str, int]:
    """先修边数与**被最终顺序违反**的边数。

    `violations` 刻意定义为「最终顺序违反的边数」而不是「置顶块冲突数」：它只从最终顺序算出，
    所以「同一 `plan_id` ⇒ 相同 `summary`」这条不变量**结构上**成立（顺序相同则违反集相同），
    不需要把图折进 `_derived_digest`。它同时把环、被排除的先修、置顶冲突三种成因统一成
    一个可测量的数，直接度量 `M9-EVALUATION` 的「先修违反=0」。

    边只统计**本计划任务集内**的：被 `excluded_topics` 移除的先修不产生边，也就不产生违反。
    """
    edges = GoalPlannerService._present_edges(tasks, graph)
    position = {t.file: index for index, t in enumerate(tasks)}
    total = 0
    violations = 0
    for file, prereqs in edges.items():
        for prereq in prereqs:
            total += 1
            if position[file] < position[prereq]:
                violations += 1
    return {"edges": total, "violations": violations}


def _mastery_rank(task: GoalPlanTask) -> int:
    """mastery 桶：0 无答题证据 / 1 有尝试但从未答对 / 2 已答对过。"""
    if task.mastery_attempts <= 0:
        return 0
    if task.mastery_correct <= 0:
        return 1
    return 2


def _derived_digest(tasks: list[GoalPlanTask]) -> str:
    """派生输入摘要：**按最终顺序**排列的 (task_id, reviewed, mastery…) 元组。

    顺序本身编码在序列里，所以「排序变了」必然换摘要。元组带上 reviewed 与三个 mastery 值，
    是因为它们会落进 plan 记录的 task 载荷——只摘要 task_id 序列会让「单任务计划」这类
    顺序不变、载荷变了的输入撞同一 plan_id，`persist_generated` 又会保留旧载荷。
    摘要只覆盖本计划范围内的任务，故范围外条目的状态变化不会无谓改变 plan_id。
    """
    payload = "\n".join(
        f"{t.task_id}:{int(t.reviewed)}:{t.mastery_attempts}:"
        f"{t.mastery_correct}:{t.mastery_last_mastered or ''}"
        for t in tasks
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _count_by(tasks: list[GoalPlanTask], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tasks:
        value = getattr(t, field)
        counts[value] = counts.get(value, 0) + 1
    return counts


def _task_id(file: str) -> str:
    return hashlib.sha256(file.encode("utf-8")).hexdigest()[:16]
