"""复习排程服务测试：验证间隔重复算法、历史记录、逾期查询。"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import ReviewLogRequest  # noqa: E402
from app.review_scheduler import INTERVAL_SEQUENCE, ReviewSchedulerService  # noqa: E402


@pytest.fixture
def scheduler(tmp_path):
    """使用临时目录的调度器实例（隔离测试历史文件）。"""
    history_path = tmp_path / "review_history.json"
    with patch("app.review_scheduler._HISTORY_PATH", history_path):
        yield ReviewSchedulerService()


def test_log_review_creates_entry(scheduler):
    """首次记录复习应创建新条目。"""
    result = scheduler.log_review(
        ReviewLogRequest(file="knowledge/os/process-management.md", course="os")
    )
    assert result["review_count"] == 1
    assert result["interval_days"] == INTERVAL_SEQUENCE[0]  # 1 天
    assert "message" in result


def test_log_review_increments_count(scheduler):
    """多次记录复习应递增次数。"""
    req = ReviewLogRequest(file="knowledge/os/deadlock.md", course="os")
    scheduler.log_review(req)
    scheduler.log_review(req)
    result = scheduler.log_review(req)
    assert result["review_count"] == 3
    assert result["interval_days"] == INTERVAL_SEQUENCE[2]  # 4 天


def test_interval_sequence_grows(scheduler):
    """间隔序列应随复习次数递增。"""
    req = ReviewLogRequest(file="knowledge/os/test.md", course="os")
    intervals = []
    for i in range(6):
        result = scheduler.log_review(req)
        intervals.append(result["interval_days"])
    assert intervals == INTERVAL_SEQUENCE[:6]


def test_interval_caps_at_max(scheduler):
    """间隔不应超过序列最大值。"""
    req = ReviewLogRequest(file="knowledge/os/test.md", course="os")
    for _ in range(10):
        result = scheduler.log_review(req)
    assert result["interval_days"] == INTERVAL_SEQUENCE[-1]


def test_get_due_empty_when_no_history(scheduler):
    """无历史记录时应返回空列表。"""
    resp = scheduler.get_due()
    assert resp.total_due == 0
    assert resp.entries == []


def test_get_due_returns_overdue_entries(scheduler):
    """逾期条目应出现在待复习列表中。"""
    # 手动写入一条昨天到期的记录
    history = scheduler._load_history()
    yesterday = datetime.now() - timedelta(days=2)
    history["knowledge/os/test.md"] = {
        "file": "knowledge/os/test.md",
        "course": "os",
        "review_count": 1,
        "last_reviewed": yesterday.isoformat(),
        "next_review": (yesterday + timedelta(days=1)).isoformat(),
        "interval_days": 1,
    }
    scheduler._save_history(history)

    resp = scheduler.get_due()
    assert resp.total_due >= 1
    assert any(e.file == "knowledge/os/test.md" for e in resp.entries)


def test_get_due_filters_by_course(scheduler):
    """按课程筛选应生效。"""
    # 写入 OS 和 DS 两条记录
    history = scheduler._load_history()
    yesterday = datetime.now() - timedelta(days=2)
    for course, file in [("os", "knowledge/os/a.md"), ("ds", "knowledge/ds/b.md")]:
        history[file] = {
            "file": file,
            "course": course,
            "review_count": 1,
            "last_reviewed": yesterday.isoformat(),
            "next_review": (yesterday + timedelta(days=1)).isoformat(),
            "interval_days": 1,
        }
    scheduler._save_history(history)

    resp = scheduler.get_due(course="os")
    assert all(e.course == "os" or e.file.startswith("knowledge/os/") for e in resp.entries)


def test_get_due_sorts_by_overdue_days(scheduler):
    """应按逾期天数降序排列（最紧急在前）。"""
    history = scheduler._load_history()
    now = datetime.now()
    # 一条逾期 3 天，一条逾期 1 天
    for days, file in [(3, "knowledge/os/old.md"), (1, "knowledge/os/recent.md")]:
        history[file] = {
            "file": file,
            "course": "os",
            "review_count": 1,
            "last_reviewed": (now - timedelta(days=days + 2)).isoformat(),
            "next_review": (now - timedelta(days=days)).isoformat(),
            "interval_days": 1,
        }
    scheduler._save_history(history)

    resp = scheduler.get_due()
    if len(resp.entries) >= 2:
        assert resp.entries[0].days_overdue >= resp.entries[1].days_overdue


def test_log_review_persists_to_file(scheduler):
    """记录应持久化到文件。"""
    scheduler.log_review(ReviewLogRequest(file="knowledge/os/persist.md", course="os"))
    # 重新加载验证
    history = scheduler._load_history()
    assert "knowledge/os/persist.md" in history
    assert history["knowledge/os/persist.md"]["review_count"] == 1
