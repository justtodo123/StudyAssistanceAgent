"""复习计划服务：根据课程知识库条目生成分日学习计划。

以知识条目文件为单位，按难度分配学习时间，贪心填充每日可用学时。
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any

from .knowledge_index import build_index_cached
from .models import PlanDay, PlanTask, ReviewPlanRequest, ReviewPlanResponse


class ReviewPlanService:
    """复习计划生成器。"""

    # 难度 → 基础学习时间（分钟/条目）
    DIFFICULTY_TIME: dict[str, int] = {"入门": 25, "中等": 35, "进阶": 50}

    # 难度 → 优先级
    DIFFICULTY_PRIORITY: dict[str, str] = {"入门": "low", "中等": "medium", "进阶": "high"}

    # 每天开头复习前一天内容的预留时间（分钟），第 1 天除外
    REVIEW_BUFFER_MINUTES = 10

    def generate(self, req: ReviewPlanRequest) -> ReviewPlanResponse:
        """根据请求生成复习计划。"""
        # 1. 获取该课程全部条目，按文件去重，保持文件系统顺序
        entries = self._load_entries(req.course)

        # 2. 解析目标日期
        today = datetime.now().date()
        if req.target_date:
            target = datetime.strptime(req.target_date, "%Y-%m-%d").date()
        else:
            target = today + timedelta(days=14)
        total_days = max((target - today).days, 1)

        # 3. 计算每条目的学习时间
        tasks = self._build_tasks(entries)

        # 4. 按天分配任务
        daily_minutes = int(req.hours_per_day * 60)
        days = self._distribute(tasks, today, total_days, daily_minutes)

        # 5. 组装响应
        plan_name = req.plan_name or f"{req.course}-plan"
        total_task_minutes = sum(t.estimated_minutes for t in tasks)
        difficulty_counts: dict[str, int] = {}
        for t in tasks:
            difficulty_counts[t.difficulty] = difficulty_counts.get(t.difficulty, 0) + 1

        return ReviewPlanResponse(
            plan_name=plan_name,
            course=req.course,
            generated_at=datetime.now().isoformat(),
            target_date=str(target),
            total_days=total_days,
            total_hours=round(total_task_minutes / 60, 1),
            days=days,
            summary={
                "total_entries": len(tasks),
                "by_difficulty": difficulty_counts,
                "tip": "建议每天先复习前一天内容（10 分钟），再学习新内容。遇到进阶条目可适当延长。",
            },
        )

    # ── 内部方法 ──────────────────────────────────────────────────────────────

    def _load_entries(self, course: str) -> list[dict[str, Any]]:
        """加载指定课程的知识条目，按文件去重，保持文件系统自然顺序。

        返回：[{file, title, difficulty, tags}]，每个文件只出现一次。
        """
        chunks = build_index_cached()
        seen: OrderedDict[str, dict[str, Any]] = OrderedDict()
        for c in chunks:
            if c.course != course:
                continue
            if c.file in seen:
                continue
            seen[c.file] = {
                "file": c.file,
                "title": c.title,
                "difficulty": c.difficulty or "中等",
                "tags": c.tags,
            }
        return list(seen.values())

    def _build_tasks(self, entries: list[dict[str, Any]]) -> list[PlanTask]:
        """将条目列表转为学习任务列表，分配时间与优先级。"""
        tasks: list[PlanTask] = []
        for e in entries:
            diff = e["difficulty"]
            minutes = self.DIFFICULTY_TIME.get(diff, 35)
            priority = self.DIFFICULTY_PRIORITY.get(diff, "medium")
            tasks.append(
                PlanTask(
                    file=e["file"],
                    title=e["title"],
                    difficulty=diff,
                    estimated_minutes=minutes,
                    priority=priority,
                    tags=e.get("tags", []),
                )
            )
        return tasks

    def _distribute(
        self,
        tasks: list[PlanTask],
        start_date,
        total_days: int,
        daily_minutes: int,
    ) -> list[PlanDay]:
        """贪心分配：每天填满 daily_minutes，第 2 天起预留复习时间。"""
        days: list[PlanDay] = []
        task_idx = 0
        for d in range(total_days):
            current_date = start_date + timedelta(days=d)
            available = daily_minutes
            # 第 2 天起预留复习时间
            if d > 0:
                available -= self.REVIEW_BUFFER_MINUTES
            available = max(available, 0)

            day_tasks: list[PlanTask] = []
            used = 0
            while task_idx < len(tasks):
                t = tasks[task_idx]
                if used + t.estimated_minutes > available and day_tasks:
                    break  # 放不下，留给明天
                day_tasks.append(t)
                used += t.estimated_minutes
                task_idx += 1

            days.append(
                PlanDay(
                    day=d + 1,
                    date=str(current_date),
                    tasks=day_tasks,
                    total_minutes=used + (self.REVIEW_BUFFER_MINUTES if d > 0 and day_tasks else 0),
                )
            )

            # 所有任务分配完毕
            if task_idx >= len(tasks):
                break

        # 剩余任务追加到最后一天（如果超出天数）
        if task_idx < len(tasks):
            remaining_tasks = tasks[task_idx:]
            extra_date = start_date + timedelta(days=total_days)
            days.append(
                PlanDay(
                    day=len(days) + 1,
                    date=str(extra_date),
                    tasks=remaining_tasks,
                    total_minutes=sum(t.estimated_minutes for t in remaining_tasks),
                )
            )

        return days
