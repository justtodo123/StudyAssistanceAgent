"""复习排程服务：基于遗忘曲线的间隔重复提醒。

存储：platform/.cache/review_history.json
算法：间隔序列 1 → 2 → 4 → 8 → 16 天，下次复习 = 上次复习 + interval
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .knowledge_index import build_index_cached
from .learning_store import ReviewHistoryRepository
from .models import ReviewDueResponse, ReviewEntry, ReviewLogRequest

# 间隔序列（天）：复习次数 → 下次间隔
INTERVAL_SEQUENCE = [1, 2, 4, 8, 16, 32]

# 历史文件路径
_HISTORY_PATH = Path(__file__).resolve().parents[1] / ".cache" / "review_history.json"


class ReviewSchedulerService:
    """复习排程器。"""

    def __init__(self, repository: ReviewHistoryRepository | None = None) -> None:
        self._repository = repository

    def log_review(self, req: ReviewLogRequest) -> dict[str, Any]:
        """记录一次复习完成，更新历史并返回下次复习时间。"""
        if req.source_session_id:
            existing = self._find_by_source_session(req.source_session_id)
            if existing is not None:
                return self._result_from_entry(existing)
        history = self._load_history()
        file_key = req.file
        now = datetime.now()

        if file_key in history:
            entry = history[file_key]
            entry["review_count"] = entry.get("review_count", 0) + 1
            entry["last_reviewed"] = now.isoformat()
        else:
            entry = {
                "file": file_key,
                "course": req.course,
                "review_count": 1,
                "last_reviewed": now.isoformat(),
            }

        # 计算下次复习时间
        count = entry["review_count"]
        interval = self._get_interval(count)
        next_review = now + timedelta(days=interval)
        entry["next_review"] = next_review.isoformat()
        entry["interval_days"] = interval

        if req.source_session_id:
            entry["source_session_id"] = req.source_session_id
        history[file_key] = entry
        self._save_history(history)

        return self._result_from_entry(entry)

    def get_due(self, course: str | None = None) -> ReviewDueResponse:
        """查询今日待复习条目。"""
        history = self._load_history()
        now = datetime.now()
        today = now.date()

        # 构建知识条目索引（用于补充 title 等元信息）
        entry_meta = self._build_meta_index()

        due_entries: list[ReviewEntry] = []
        all_entries: list[ReviewEntry] = []

        for file_key, record in history.items():
            # 课程筛选
            record_course = record.get("course", "")
            if course and record_course != course:
                # 尝试从文件路径推断课程
                if not file_key.startswith(f"knowledge/{course}/"):
                    continue

            last_str = record.get("last_reviewed", "")
            next_str = record.get("next_review", "")
            count = record.get("review_count", 0)
            interval = record.get("interval_days", 1)

            if not last_str:
                continue

            last_dt = datetime.fromisoformat(last_str)
            if next_str:
                next_dt = datetime.fromisoformat(next_str)
            else:
                next_dt = last_dt + timedelta(days=interval)

            days_overdue = (today - next_dt.date()).days

            meta = entry_meta.get(file_key, {})
            entry = ReviewEntry(
                file=file_key,
                title=meta.get("title", file_key.split("/")[-1].replace(".md", "")),
                course=record_course or meta.get("course", ""),
                last_reviewed=last_str,
                review_count=count,
                next_review=next_dt.isoformat(),
                days_overdue=days_overdue,
                interval_days=interval,
            )

            all_entries.append(entry)
            if days_overdue >= 0:
                due_entries.append(entry)

        # 按逾期天数降序排列（最紧急的在前）
        due_entries.sort(key=lambda e: e.days_overdue, reverse=True)

        # 统计
        overdue_count = sum(1 for e in due_entries if e.days_overdue > 0)
        today_count = sum(1 for e in due_entries if e.days_overdue == 0)

        return ReviewDueResponse(
            course=course,
            checked_at=now.isoformat(),
            total_due=len(due_entries),
            entries=due_entries,
            summary={
                "total_tracked": len(all_entries),
                "overdue": overdue_count,
                "due_today": today_count,
                "upcoming": len(all_entries) - len(due_entries),
                "tip": "优先复习逾期最久的条目。每天花 10-15 分钟复习旧内容，效果最佳。"
                if due_entries
                else "当前没有待复习条目，继续保持！",
            },
        )

    # ── 内部方法 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _get_interval(review_count: int) -> int:
        """根据复习次数返回下次间隔天数。"""
        idx = min(review_count - 1, len(INTERVAL_SEQUENCE) - 1)
        idx = max(idx, 0)
        return INTERVAL_SEQUENCE[idx]

    def _load_history(self) -> dict[str, Any]:
        """加载复习历史。"""
        json_history = self._load_json_history()
        if self._repository is None:
            return json_history
        stored = self._repository.all()
        merged = dict(json_history)
        merged.update(stored)
        return merged

    @staticmethod
    def _load_json_history() -> dict[str, Any]:
        if _HISTORY_PATH.exists():
            try:
                loaded = json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
            if isinstance(loaded, dict):
                return loaded
        return {}

    def _save_history(self, history: dict[str, Any]) -> None:
        """保存复习历史。"""
        if self._repository is not None:
            for file_key, entry in history.items():
                self._repository.save(file_key, entry)
            return
        _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _HISTORY_PATH.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _find_by_source_session(self, session_id: str) -> dict[str, Any] | None:
        if self._repository is not None:
            return self._repository.find_by_source_session(session_id)
        for entry in self._load_history().values():
            if entry.get("source_session_id") == session_id:
                return entry
        return None

    @staticmethod
    def _result_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
        count = int(entry.get("review_count", 0))
        interval = int(entry.get("interval_days", 1))
        next_review = entry.get("next_review", "")
        day = next_review[:10] if next_review else ""
        return {
            "file": entry.get("file", ""),
            "review_count": count,
            "next_review": next_review,
            "interval_days": interval,
            "message": f"已记录复习（第 {count} 次），下次复习：{day}（{interval} 天后）",
        }

    @staticmethod
    def _build_meta_index() -> dict[str, dict[str, str]]:
        """从知识索引构建 file → {title, course} 映射。"""
        chunks = build_index_cached()
        meta: dict[str, dict[str, str]] = {}
        for c in chunks:
            if c.file not in meta:
                meta[c.file] = {"title": c.title, "course": c.course}
        return meta
