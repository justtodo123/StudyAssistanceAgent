"""M9 只读复习历史投影测试：成员资格、活投影与 Planner 接缝。

覆盖一处**已证实的缺陷**：`main.py` 原先把 `_learning_store.all_reviews()` 传给 Planner，那是构造时
求值一次的**快照**，于是同一进程内新记录的复习永不反映到计划上——`reviewed` 标志、排序优先级，以及经
`_derived_digest` 参与 `plan_id` 的那部分身份全部停在进程启动时刻。紧邻的 mastery 投影刻意传活对象
（注释原文「使计划身份与排序随答题状态刷新」），两条同源只读输入一个实时一个冻结。

本文件的核心用例是 `test_review_logged_after_construction_is_visible_to_the_planner`：它在**构造
Planner 之后**才落一条复习，断言该条目变为 `reviewed`。旧代码下这一条必然失败，故它不是空转的。
"""

from __future__ import annotations

import ast
import inspect
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

import app.review_history_projection as projection_module
from app.goal_planner import GoalPlannerService
from app.learning_store import SqliteLearningStore
from app.models import GoalPlanRequest
from app.review_history_projection import (
    REVIEW_HISTORY_PROJECTION_SCHEMA_VERSION,
    ReviewHistoryProjection,
)

pytestmark = pytest.mark.m9

# 语料里真实存在的条目（`knowledge/os/`），Planner 按 frontmatter 载入
OS_FILE = "knowledge/os/process-management.md"
OTHER_OS_FILE = "knowledge/os/deadlock.md"


def _store(tmp_path: Path) -> SqliteLearningStore:
    return SqliteLearningStore(tmp_path / "learning.sqlite3")


def _log(store: SqliteLearningStore, file_key: str) -> None:
    """经仓储真实写入一条复习记录。

    刻意**不**经 `ReviewSchedulerService.log_review`：它的 `_load_history` 会把**共享的 legacy JSON
    历史文件**（`_HISTORY_PATH`）并进仓储，`_save_history` 再把合并结果整体写回，于是本文件的 store
    会带上别的用例遗留的条目，精确断言不可复现。那是该服务既有的行为，不是本投影的问题。
    """
    store.save_review(file_key, {"file": file_key, "course": "os", "review_count": 1})


def _request(**kwargs: Any) -> GoalPlanRequest:
    defaults = {"goal": "两周内掌握进程调度与死锁", "course": "os"}
    defaults.update(kwargs)
    return GoalPlanRequest(**defaults)


def _tasks(plan) -> list:
    return [t for day in plan.revisions[0].days for t in day.tasks]


def _task_for(plan, file_key: str):
    return next((t for t in _tasks(plan) if t.file == file_key), None)


class _CountingSource:
    """统计批量读次数的 reader 桩。"""

    def __init__(self, files: set[str] | None = None) -> None:
        self._files = files or set()
        self.calls = 0

    def all_reviews(self) -> dict[str, dict[str, Any]]:
        self.calls += 1
        return {f: {"review_count": 1} for f in self._files}


# ── A. 投影本身 ───────────────────────────────────────────────────────────────


def test_schema_version_is_declared() -> None:
    assert REVIEW_HISTORY_PROJECTION_SCHEMA_VERSION == "m9-review-history-projection-v1"


def test_empty_history_yields_an_empty_set(tmp_path: Path) -> None:
    projection = ReviewHistoryProjection(_store(tmp_path))
    assert projection.reviewed_files() == frozenset()


def test_reviewed_files_returns_the_file_keys(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _log(store, OS_FILE)
    _log(store, OTHER_OS_FILE)

    assert ReviewHistoryProjection(store).reviewed_files() == frozenset({OS_FILE, OTHER_OS_FILE})


def test_projection_reads_exactly_once_per_call() -> None:
    """输入有界：一次批量读，不按条目逐个回查。"""
    source = _CountingSource({OS_FILE})
    projection = ReviewHistoryProjection(source)

    projection.reviewed_files()

    assert source.calls == 1


def test_projection_is_live_and_does_not_cache() -> None:
    """刻意不缓存：新落库的复习在下一次调用就必须可见。"""
    source = _CountingSource()
    projection = ReviewHistoryProjection(source)

    assert projection.reviewed_files() == frozenset()
    source._files.add(OS_FILE)
    assert projection.reviewed_files() == frozenset({OS_FILE})


def test_projection_returns_only_membership_not_payloads() -> None:
    """只回答成员资格：不把 review payload 交出去。"""
    source = _CountingSource({OS_FILE})
    result = ReviewHistoryProjection(source).reviewed_files()

    assert isinstance(result, frozenset)
    assert all(isinstance(item, str) for item in result)


def test_projection_exposes_no_write_surface() -> None:
    """只读守卫：公开面里没有任何写方法。"""
    public = [n for n, _ in inspect.getmembers(ReviewHistoryProjection, callable) if not n.startswith("_")]
    assert public == ["reviewed_files"], public


def test_module_imports_no_write_path() -> None:
    """源码级护栏：只 import 标准库。

    只扫 **import 语句**而非整份源码：docstring 里必然要提到 `_learning_store` 才能解释这处缺陷，
    全文扫描会把那段说明当成违规（同 `test_goal_planner.py` 那类全文扫描的误报陷阱）。
    """
    tree = ast.parse(inspect.getsource(projection_module))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert imported == ["__future__", "typing"], imported


def test_projection_does_not_write_to_the_store(tmp_path: Path, monkeypatch) -> None:
    """真只读守卫：写入口全部 fail + 连接级 `total_changes` 审计 + 库快照比对。

    沿用 `test_goal_planner.py::test_planner_does_not_write_state` 的真守卫写法。**不能**在
    `with store._connect()` 内部再调 `reviewed_files()`：`_connect` 持有非可重入的 `self._lock`，
    嵌套获取会死锁（这正是本用例第一版的写法）。
    """
    store = _store(tmp_path)
    _log(store, OS_FILE)
    observer = sqlite3.connect(str(store.db_path))
    observer.execute("PRAGMA query_only=ON")
    before = "\n".join(observer.iterdump())
    deltas: list[int] = []
    original_connect = store._connect

    @contextmanager
    def audited_connect():
        with original_connect() as connection:
            started = connection.total_changes
            yield connection
            deltas.append(connection.total_changes - started)

    monkeypatch.setattr(store, "_connect", audited_connect)
    for name in ("save", "save_review", "save_plan", "save_progress_event"):
        monkeypatch.setattr(
            SqliteLearningStore, name, lambda *a, **k: pytest.fail("projection wrote state")
        )

    assert ReviewHistoryProjection(store).reviewed_files() == frozenset({OS_FILE})

    assert deltas == [0], deltas
    assert "\n".join(observer.iterdump()) == before


# ── B. Planner 接缝：缺陷证明 ─────────────────────────────────────────────────


def test_review_logged_after_construction_is_visible_to_the_planner(tmp_path: Path) -> None:
    """**核心用例**：构造 Planner 之后才落的复习，必须反映到下一次生成上。

    旧代码（`review_history=store.all_reviews()`）下本用例失败：快照在构造时求值一次，
    此后 `reviewed` 永远是 False。
    """
    store = _store(tmp_path)
    planner = GoalPlannerService(review_history_projection=ReviewHistoryProjection(store))

    before = _task_for(planner.generate(_request()), OS_FILE)
    assert before is not None and before.reviewed is False

    _log(store, OS_FILE)

    after = _task_for(planner.generate(_request()), OS_FILE)
    assert after is not None and after.reviewed is True


def test_the_snapshot_parameter_still_freezes(tmp_path: Path) -> None:
    """回落路径语义不变：显式传快照的调用方仍拿到冻结视图。

    这条同时证明上面那个用例测的是**投影**，而不是「生成时反正会重读」——快照参数是反例。
    """
    store = _store(tmp_path)
    planner = GoalPlannerService(review_history=store.all_reviews())

    _log(store, OS_FILE)

    task = _task_for(planner.generate(_request()), OS_FILE)
    assert task is not None and task.reviewed is False


def test_plan_id_tracks_reviews_within_the_process(tmp_path: Path) -> None:
    """身份随复习变化：`reviewed` 参与 `_derived_digest`，故新复习必须换 `plan_id`。"""
    store = _store(tmp_path)
    planner = GoalPlannerService(review_history_projection=ReviewHistoryProjection(store))

    first = planner.generate(_request()).plan_id
    _log(store, OS_FILE)
    second = planner.generate(_request()).plan_id

    assert first != second


def test_live_projection_matches_a_snapshot_taken_at_the_same_moment(tmp_path: Path) -> None:
    """活投影与「同一时刻取的快照」产出逐字段相同的计划：它只改**何时**读，不改**读什么**。"""
    store = _store(tmp_path)
    _log(store, OS_FILE)

    live = GoalPlannerService(review_history_projection=ReviewHistoryProjection(store)).generate(
        _request()
    )
    snapshot = GoalPlannerService(review_history=store.all_reviews()).generate(_request())

    assert live.plan_id == snapshot.plan_id
    assert live.revisions[0].days == snapshot.revisions[0].days
    assert live.summary == snapshot.summary


def test_without_projection_behavior_is_unchanged(tmp_path: Path) -> None:
    """依赖缺省是守卫，不是错误：未注入投影时等价于空快照。"""
    store = _store(tmp_path)
    _log(store, OS_FILE)

    plan = GoalPlannerService().generate(_request())

    assert all(t.reviewed is False for t in _tasks(plan))


def test_reviewed_still_outranks_everything_else(tmp_path: Path) -> None:
    """排序不变量不因活投影而改变：已复习任务仍排在其后的未复习任务之后。"""
    store = _store(tmp_path)
    planner = GoalPlannerService(review_history_projection=ReviewHistoryProjection(store))
    _log(store, OS_FILE)

    tasks = _tasks(planner.generate(_request()))
    index = next(i for i, t in enumerate(tasks) if t.file == OS_FILE)

    assert all(not t.reviewed for t in tasks[:index])


def test_projection_is_read_once_per_generate(tmp_path: Path) -> None:
    """整轮只读一次：生成途中若有新复习落库，不能让不同任务看到不同快照。"""
    source = _CountingSource()
    planner = GoalPlannerService(review_history_projection=ReviewHistoryProjection(source))

    planner.generate(_request())

    assert source.calls == 1


def test_main_wires_a_live_review_history_projection() -> None:
    """装配护栏：`main.py` 必须注入**活投影**，而不是构造时求值的快照。

    这处缺陷原本就在**装配**上——Planner 本身没错，是 `main.py` 传了
    `_learning_store.all_reviews()`。故只在 Planner 层测不够：把装配改回快照，上面那些用例
    仍然全绿。本用例是唯一会因此变红的一条。
    """
    from app import main

    projection = main._goal_planner._review_history_projection
    assert projection is not None, "main.py must inject the live projection, not a snapshot"
    # 必须绑定到同一个 learning store：绑错对象会静默读到空历史，且不会有任何报错
    assert projection._source is main._learning_store
    # 快照参数不得同时传入：两者并存会让「到底读哪个」取决于 `_reviews` 的分支顺序
    assert main._goal_planner._review_history == {}


def test_generate_writes_nothing(tmp_path: Path) -> None:
    """活投影不引入写入：生成前后库快照逐字节相同。"""
    store = _store(tmp_path)
    _log(store, OS_FILE)
    planner = GoalPlannerService(review_history_projection=ReviewHistoryProjection(store))

    before = json.dumps(store.all_reviews(), sort_keys=True)
    planner.generate(_request())
    after = json.dumps(store.all_reviews(), sort_keys=True)

    assert before == after
