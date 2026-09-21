"""确定性目标驱动学习计划服务（M9 第一增量）。

只做计划生成：基于 Goal + 约束 + 只读复习历史与只读 mastery 投影，产出版本化、可重放的分日计划。
不写 mastery、不写学习状态、不引入外部 AI、不读原始 chunk 正文。
"""

from __future__ import annotations

import hashlib
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
REVIEW_BUFFER_MINUTES = 10


class GoalPlannerService:
    """确定性目标驱动计划生成器。"""

    def __init__(
        self,
        review_history: dict[str, dict[str, Any]] | None = None,
        mastery_projection: Any | None = None,
        source_summary: Any | None = None,
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
        tasks = self._build_tasks(entries, mastery)
        tasks = self._stable_order(tasks)
        tasks = self._pin_required(tasks, req.constraints.required_topics)
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

    @staticmethod
    def _pin_required(tasks: list[GoalPlanTask], required_topics: list[str]) -> list[GoalPlanTask]:
        required = [t.lower() for t in required_topics]
        if not required:
            return tasks
        rank = {t: i for i, t in enumerate(required)}
        pinned = [t for t in tasks if t.topic.lower() in rank]
        pinned.sort(key=lambda t: rank[t.topic.lower()])
        rest = [t for t in tasks if t.topic.lower() not in rank]
        return pinned + rest

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
    def _stable_order(tasks: list[GoalPlanTask]) -> list[GoalPlanTask]:
        """确定性排序：未复习优先 → mastery 证据由少到多 → 难度优先级降序 → file 字典序。

        mastery 桶只细化同一 `reviewed` 桶内的相对顺序；`reviewed` 仍是主键（它是最强的已学信号）。
        未注入投影时全部任务落在桶 0，排序结果与接入前逐字节一致——这是既有 M9 测试不受影响的
        **结构**原因，不是巧合。
        """
        priority_rank = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            tasks,
            key=lambda t: (
                t.reviewed,  # False(未复习) 排前
                _mastery_rank(t),
                priority_rank.get(t.priority, 1),
                t.file,
            ),
        )

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
