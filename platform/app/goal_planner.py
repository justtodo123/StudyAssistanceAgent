"""确定性目标驱动学习计划服务（M9 第一增量）。

只做计划生成：基于 Goal + 约束 + 只读复习历史投影，产出版本化、可重放的分日计划。
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

    def __init__(self, review_history: dict[str, dict[str, Any]] | None = None) -> None:
        # review_history 是 file -> {review_count,...} 的只读投影，仅用于排序优先；
        # 不写回、不新建表。缺省空表表示“全部未复习”。
        self._review_history = review_history or {}

    def generate(self, req: GoalPlanRequest) -> GoalPlanResponse:
        """根据 Goal 请求生成版本化计划。"""
        # 1. 载入条目并去重到 topic（file）粒度，保持稳定顺序
        entries = self._load_entries(req.course)
        # 2. 应用话题约束：先排除，再确定排序，最后置顶必选（保持置顶不被排序破坏）
        entries = self._exclude(entries, req.constraints.excluded_topics)
        tasks = self._build_tasks(entries)
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
        # 6. 确定性 plan_id（goal 归一化 + 目标日期）
        plan_id = self._plan_id(req.goal, target)
        total_task_minutes = sum(t.estimated_minutes for t in tasks)
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
            summary={
                "total_tasks": len(tasks),
                "reviewed": sum(1 for t in tasks if t.reviewed),
                "unreviewed": sum(1 for t in tasks if not t.reviewed),
                "by_difficulty": _count_by(tasks, "difficulty"),
            },
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

    def _build_tasks(self, entries: list[dict[str, Any]]) -> list[GoalPlanTask]:
        tasks: list[GoalPlanTask] = []
        for e in entries:
            diff = e["difficulty"]
            minutes = DIFFICULTY_TIME.get(diff, 35)
            priority = DIFFICULTY_PRIORITY.get(diff, "medium")
            reviewed = e["file"] in self._review_history
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
                )
            )
        return tasks

    @staticmethod
    def _stable_order(tasks: list[GoalPlanTask]) -> list[GoalPlanTask]:
        """确定性排序：未复习优先，其次难度优先级降序，最后 file 字典序。"""
        priority_rank = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            tasks,
            key=lambda t: (
                t.reviewed,  # False(未复习) 排前
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
    def _plan_id(goal: str, target) -> str:
        normalized = re.sub(r"\s+", " ", goal.strip()).lower()
        key = f"{normalized}|{target.isoformat()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _count_by(tasks: list[GoalPlanTask], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tasks:
        value = getattr(t, field)
        counts[value] = counts.get(value, 0) + 1
    return counts


def _task_id(file: str) -> str:
    return hashlib.sha256(file.encode("utf-8")).hexdigest()[:16]
