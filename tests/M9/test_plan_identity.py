"""M9 计划身份往返保真测试（步骤 4b）。

覆盖两组已证实缺陷及其修复：

1. **`_plan_id` 碰撞**：身份键此前不含 principal，而 `plan_lifecycle` 的 `event_id` 是
   `(plan_id, task_id, event)` 的哈希、同样不含 principal 成分。两个 principal 生成同一 Goal
   会撞同一 `plan_id`，后者的 `completed` 被 `INSERT OR IGNORE` 静默去重，把前者的任务标成完成。
2. **往返丢字段**：`_response_to_record` 没有 `summary` 键；`_plan_to_request` 只还原 5 个请求字段，
   principal 一旦进入计划路径，`replan` 会以「无 principal」重新生成、源范围静默改变。

同时钉住三条不变量：
- `principal_id=None` 时身份与接入前**逐字节相同**（不 churn 既有计划）；
- principal 是**内部记录键**，绝不出现在任何 HTTP 返回路径上；
- 无 principal 的记录与接入前逐字节相同（不新增键）。
"""

from __future__ import annotations

import hashlib
import inspect
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

import app.plan_lifecycle as plan_lifecycle_module
from app.goal_planner import GoalPlannerService, _derived_digest
from app.learning_store import SqliteLearningStore
from app.models import GoalPlanConstraints, GoalPlanRequest, GoalPlanTask, PlanProgressRequest
from app.plan_lifecycle import (
    INTERNAL_RECORD_KEYS,
    PRINCIPAL_RECORD_KEY,
    PlanLifecycleService,
)
from app.source_registry import SourceLifecycleState, SourceRecord
from app.source_summary_projection import SourceSummaryProjection

pytestmark = pytest.mark.m9

PRINCIPAL_A = "principal-a"
PRINCIPAL_B = "principal-b"
SOURCE_ID = "user-01890f52-47e7-7abc-8def-0123456789ab"

# 与 `test_source_summary_projection.py` 同形的最小 registry 夹具（不修改 M7 测试目录）
_READY_STATES = ("SYNCING", "READY")


def _request(**kwargs) -> GoalPlanRequest:
    defaults = {"goal": "两周内掌握进程调度与死锁", "course": "os"}
    defaults.update(kwargs)
    return GoalPlanRequest(**defaults)


def _task(task_id: str) -> GoalPlanTask:
    return GoalPlanTask(
        task_id=task_id,
        topic=task_id,
        file=f"os/{task_id}.md",
        difficulty="中等",
        estimated_minutes=30,
        priority="medium",
    )


def _pre_4b_plan_id(
    goal: str,
    target: date,
    course: str | None,
    constraints: GoalPlanConstraints,
    hours_per_day: float,
    tasks: list[GoalPlanTask],
) -> str:
    """接入 4b **之前**的 `_plan_id` 公式，逐字复刻，用于钉住「None 时逐字节相同」。"""
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
    return hashlib.sha256(f"{key}|{_derived_digest(tasks)}".encode("utf-8")).hexdigest()[:16]


def _lifecycle(planner: GoalPlannerService):
    store = SqliteLearningStore(":memory:")
    return PlanLifecycleService(store, planner), store


def _generate_and_persist(
    lifecycle: PlanLifecycleService,
    planner: GoalPlannerService,
    principal: str | None = None,
    **kwargs,
):
    response = planner.generate(_request(**kwargs), principal_id=principal)
    lifecycle.persist_generated(response, principal)
    return response


# ── A. 身份键：principal 分隔与 None 字节保真 ──────────────────────────────────


def test_principal_none_plan_id_is_byte_identical_to_pre_4b() -> None:
    """反 churn 护栏：`principal_id=None` 时身份与接入前逐字节相同，既有计划 id 不变。

    直接调 `_plan_id` 并喂合成任务列表，使本断言**不依赖知识库语料**——否则语料一变，
    这条护栏就会变成误报源，而不是守卫。
    """
    tasks = [_task("a"), _task("b")]
    constraints = GoalPlanConstraints(required_topics=["a"], excluded_topics=["b"])
    args = ("掌握 死锁", date(2026, 9, 15), "os", constraints, 2.0)

    assert GoalPlannerService._plan_id(*args, tasks, principal_id=None) == _pre_4b_plan_id(
        *args, tasks
    )


@pytest.mark.parametrize(
    "principal",
    [PRINCIPAL_A, PRINCIPAL_B, "a|b", "principal=b", "|", "  ", "中文主体"],
)
def test_plan_id_is_domain_separated_by_principal(principal: str) -> None:
    """带标签的 principal 段：任取一个非 None 值都必须与 None 空间及彼此不同。"""
    tasks = [_task("a")]
    constraints = GoalPlanConstraints()
    args = ("掌握 死锁", date(2026, 9, 15), "os", constraints, 2.0)

    anonymous = GoalPlannerService._plan_id(*args, tasks, principal_id=None)
    scoped = GoalPlannerService._plan_id(*args, tasks, principal_id=principal)

    assert scoped != anonymous


def test_goal_text_cannot_forge_a_principal_segment() -> None:
    """`goal` 是自由文本、可含 `|`：裸追加会被伪造成 principal 段，带标签则不会。

    构造：goal 结尾恰好拼出 `|principal=p`。裸追加下它与「goal 去掉该后缀 + principal=p」
    会得到同一 key；带标签后不会。
    """
    tasks = [_task("a")]
    constraints = GoalPlanConstraints()
    forged = "掌握 死锁|principal=p"

    as_text = GoalPlannerService._plan_id(
        forged, date(2026, 9, 15), "os", constraints, 2.0, tasks, principal_id=None
    )
    as_principal = GoalPlannerService._plan_id(
        "掌握 死锁", date(2026, 9, 15), "os", constraints, 2.0, tasks, principal_id="p"
    )

    assert as_text != as_principal


def test_two_principals_same_goal_get_different_plan_ids() -> None:
    """端到端：同一 Goal、同一语料，两个 principal 得到不同 `plan_id`。"""
    planner = GoalPlannerService()
    anonymous = planner.generate(_request())
    scoped_a = planner.generate(_request(), principal_id=PRINCIPAL_A)
    scoped_b = planner.generate(_request(), principal_id=PRINCIPAL_B)

    assert len({anonymous.plan_id, scoped_a.plan_id, scoped_b.plan_id}) == 3
    # 任务载荷与分日仍逐字段相同：churn 的是隔离边界，不是计划内容
    assert anonymous.revisions[0].days == scoped_a.revisions[0].days


def test_generate_without_principal_is_unchanged_and_deterministic() -> None:
    planner = GoalPlannerService()
    assert planner.generate(_request()).plan_id == planner.generate(_request()).plan_id
    assert (
        planner.generate(_request()).plan_id
        == planner.generate(_request(), principal_id=None).plan_id
    )


# ── B. 进度事件不跨 principal 污染 ────────────────────────────────────────────


def test_progress_events_do_not_cross_principals() -> None:
    """两个 principal 各自 `completed` 同一 task_id：事件不碰撞、不被静默去重。"""
    planner = GoalPlannerService()
    lifecycle, store = _lifecycle(planner)
    plan_a = _generate_and_persist(lifecycle, planner, PRINCIPAL_A)
    plan_b = _generate_and_persist(lifecycle, planner, PRINCIPAL_B)

    assert plan_a.plan_id != plan_b.plan_id
    task_id = plan_a.revisions[0].days[0].tasks[0].task_id

    event_a = lifecycle.record_progress(
        PlanProgressRequest(plan_id=plan_a.plan_id, task_id=task_id, event="completed")
    )
    event_b = lifecycle.record_progress(
        PlanProgressRequest(plan_id=plan_b.plan_id, task_id=task_id, event="completed")
    )

    assert event_a.event_id != event_b.event_id
    assert len(store.list_progress_events(plan_a.plan_id)) == 1
    assert len(store.list_progress_events(plan_b.plan_id)) == 1


def test_two_principals_get_separate_persisted_records() -> None:
    planner = GoalPlannerService()
    lifecycle, store = _lifecycle(planner)
    plan_a = _generate_and_persist(lifecycle, planner, PRINCIPAL_A)
    plan_b = _generate_and_persist(lifecycle, planner, PRINCIPAL_B)

    assert store.get_plan(plan_a.plan_id) is not None
    assert store.get_plan(plan_b.plan_id) is not None
    assert store.get_plan(plan_a.plan_id)[PRINCIPAL_RECORD_KEY] == PRINCIPAL_A
    assert store.get_plan(plan_b.plan_id)[PRINCIPAL_RECORD_KEY] == PRINCIPAL_B


# ── C. summary 落记录 ─────────────────────────────────────────────────────────


def test_summary_is_persisted_in_the_record() -> None:
    """`_response_to_record` 此前没有 `summary` 键，读回记录拿不到摘要。"""
    planner = GoalPlannerService()
    lifecycle, store = _lifecycle(planner)
    response = _generate_and_persist(lifecycle, planner)

    stored = store.get_plan(response.plan_id)
    assert stored["summary"] == response.summary
    assert stored["summary"]["total_tasks"] > 0


def test_persisted_summary_matches_the_response_for_a_scoped_plan() -> None:
    planner = GoalPlannerService()
    lifecycle, store = _lifecycle(planner)
    response = _generate_and_persist(lifecycle, planner, PRINCIPAL_A)

    assert store.get_plan(response.plan_id)["summary"] == response.summary


# ── D. replan 保真还原 principal 与源范围 ─────────────────────────────────────


class _AllUsableReader:
    """`SourceRecordReader` 桩：把给定 source_id 全部报成可用（READY + 已发布 generation）。

    直接构造 `SourceRecord` 而非起真 registry：本文件测的是**身份与往返**，可用性规则矩阵
    已由 `test_source_summary_projection.py` 覆盖，这里只需一个「有可用源」的稳定输入。
    """

    def __init__(self, *source_ids: str) -> None:
        now = datetime(2026, 9, 1, tzinfo=timezone.utc)
        self._records = tuple(
            SourceRecord(
                source_id=source_id,
                owner_principal_id=PRINCIPAL_A,
                state=SourceLifecycleState.READY,
                record_version=3,
                created_at=now,
                updated_at=now,
                published_revision_no=1,
                published_generation="generation-1",
            )
            for source_id in source_ids
        )

    def list_sources(self, *, principal_id: str) -> tuple[SourceRecord, ...]:
        return self._records


def _scoped_planner() -> GoalPlannerService:
    """注入了只读摘要投影的 Planner：`summary["sources"]` 只在有 principal 时出现。"""
    return GoalPlannerService(source_summary=SourceSummaryProjection(_AllUsableReader(SOURCE_ID)))


def _trigger_replan(lifecycle: PlanLifecycleService, plan_id: str, tasks) -> dict:
    """记满 3 个 skipped 以跨过 `REPLAN_DEVIATION_THRESHOLD`。"""
    for task in tasks[:3]:
        lifecycle.record_progress(
            PlanProgressRequest(plan_id=plan_id, task_id=task.task_id, event="skipped")
        )
    return lifecycle.replan(plan_id)


def test_replan_preserves_principal_and_source_scope() -> None:
    """核心用例：重规划后源范围不变。

    修复前 `_plan_to_request` 丢 principal → `generate(target)` 无 principal → `summary` 里的
    `sources` 键**消失**，源范围静默改变。故这里以 `sources` 键的存在与取值作为 principal 被
    还原的证据——它只在「有 principal 且注入了投影」时出现。
    """
    planner = _scoped_planner()
    lifecycle, store = _lifecycle(planner)
    response = _generate_and_persist(lifecycle, planner, PRINCIPAL_A)
    assert response.summary["sources"] == {"usable": 1}

    tasks = [t for day in response.revisions[0].days for t in day.tasks]
    replanned = _trigger_replan(lifecycle, response.plan_id, tasks)

    assert replanned["state"] == "replanned"
    assert replanned["summary"]["sources"] == {"usable": 1}
    assert store.get_plan(response.plan_id)[PRINCIPAL_RECORD_KEY] == PRINCIPAL_A
    assert store.get_plan(response.plan_id)["summary"]["sources"] == {"usable": 1}


def test_replan_without_principal_keeps_the_record_principal_free() -> None:
    """反 churn：无 principal 的计划重规划后仍不带内部键，记录形状与接入前一致。"""
    planner = GoalPlannerService()
    lifecycle, store = _lifecycle(planner)
    response = _generate_and_persist(lifecycle, planner)

    tasks = [t for day in response.revisions[0].days for t in day.tasks]
    _trigger_replan(lifecycle, response.plan_id, tasks)

    assert PRINCIPAL_RECORD_KEY not in store.get_plan(response.plan_id)


def test_replan_preserves_summary_across_revisions() -> None:
    planner = GoalPlannerService()
    lifecycle, store = _lifecycle(planner)
    response = _generate_and_persist(lifecycle, planner)

    tasks = [t for day in response.revisions[0].days for t in day.tasks]
    _trigger_replan(lifecycle, response.plan_id, tasks)

    stored = store.get_plan(response.plan_id)
    assert stored["summary"] == response.summary
    # 旧 revision 只读保留，新 revision 追加为链尾
    assert [r["revision_id"] for r in stored["revisions"]] == [1, 2]


# ── E. principal 不出现在任何读取路径 ─────────────────────────────────────────


def test_principal_is_absent_from_every_public_read_path() -> None:
    """`get` / `adopt` / `replan`（含未触发重规划的提前返回）都不带内部键。

    同时断言**落盘记录里有**该键——否则本用例对着一份从未写入的键做否定断言，是空转的。
    """
    planner = _scoped_planner()
    lifecycle, store = _lifecycle(planner)
    response = _generate_and_persist(lifecycle, planner, PRINCIPAL_A)
    plan_id = response.plan_id
    tasks = [t for day in response.revisions[0].days for t in day.tasks]

    # 落盘记录**有**该键：证明下面的否定断言不是对着空集做的
    assert store.get_plan(plan_id)[PRINCIPAL_RECORD_KEY] == PRINCIPAL_A

    assert PRINCIPAL_RECORD_KEY not in lifecycle.get(plan_id)
    assert PRINCIPAL_RECORD_KEY not in lifecycle.adopt(plan_id)
    # 未达阈值 → 提前返回当前计划，这条路径同样不得泄露
    lifecycle.record_progress(
        PlanProgressRequest(plan_id=plan_id, task_id=tasks[0].task_id, event="skipped")
    )
    assert PRINCIPAL_RECORD_KEY not in lifecycle.replan(plan_id)
    # 达阈值 → 重规划路径
    assert PRINCIPAL_RECORD_KEY not in _trigger_replan(lifecycle, plan_id, tasks)


def test_public_plan_strips_every_internal_key() -> None:
    """`_public_plan` 对 `INTERNAL_RECORD_KEYS` 的每个键都生效，不是只对 principal 硬编码。"""
    for key in INTERNAL_RECORD_KEYS:
        assert key not in plan_lifecycle_module._public_plan({"plan_id": "x", key: "secret"})
    # 非内部键原样保留
    assert plan_lifecycle_module._public_plan({"plan_id": "x"}) == {"plan_id": "x"}


def test_internal_key_set_is_exactly_the_principal_key() -> None:
    """键集是显式白名单：新增内部键必须同时改这里，避免「加了键忘了剥离」。"""
    assert INTERNAL_RECORD_KEYS == frozenset({PRINCIPAL_RECORD_KEY})


def test_principal_is_not_a_field_of_any_plan_model() -> None:
    """principal 不是任何计划模型的字段：它一旦成为模型字段就会自动进 OpenAPI schema。"""
    from app import models

    for name in ("GoalPlanRequest", "GoalPlanResponse", "PlanProgressRequest", "PlanReplanRequest"):
        assert PRINCIPAL_RECORD_KEY not in models.__dict__[name].model_fields, name


def _public_methods() -> list[str]:
    """`PlanLifecycleService` 的全部公开方法名。

    **动态枚举而非硬编码名单**：写死 `("get", "adopt", "replan")` 的话，将来新增一个
    `def summarize(self): return plan` 就能悄悄绕过下面那道护栏。这里扫类上所有非下划线开头
    的可调用属性，新增方法自动进入扫描范围。
    """
    return sorted(
        name
        for name, member in inspect.getmembers(PlanLifecycleService, callable)
        if not name.startswith("_")
    )


def test_service_returns_go_through_public_plan() -> None:
    """源码级护栏：公开方法里返回计划记录的每一处都过 `_public_plan`。

    这是**结构性**保证——若将来有人加了 `return plan` 的快捷路径，本用例失败，而不是等到
    某个 principal 从 `GET /api/v1/plans/{id}` 泄露出去才被发现。
    只扫公开方法：`_require_plan` 与 `_response_to_record` 返回裸记录是**内部**约定，
    落盘与还原都依赖完整记录。
    """
    offenders: list[str] = []
    for name in _public_methods():
        for line in inspect.getsource(getattr(PlanLifecycleService, name)).splitlines():
            if re.match(r"\s*return\s+(self\._require_plan\(|plan$|record$)", line):
                if "_public_plan" not in line:
                    offenders.append(f"{name}: {line.strip()}")
    assert offenders == [], f"returns a raw plan record: {offenders}"


def test_public_method_scan_covers_the_routes() -> None:
    """护栏的护栏：扫描集合必须非空，且覆盖 `main.py` 真正调用的那几个返回计划的方法。

    否则把 `_public_methods` 改成返回空列表，`test_service_returns_go_through_public_plan`
    就会空转通过。
    """
    scanned = set(_public_methods())
    assert {"get", "adopt", "replan"} <= scanned
    # 三个返回计划记录的方法确实都过了 `_public_plan`；`persist_generated` 返回 None，
    # `record_progress` 返回 PlanProgressEvent，两者不含计划记录，故不要求。
    for name in ("get", "adopt", "replan"):
        assert "_public_plan" in inspect.getsource(getattr(PlanLifecycleService, name)), name


def test_no_http_route_reads_the_store_directly() -> None:
    """路由层护栏：`main.py` 的计划路由只经服务方法返回，不直接读 store。

    直接读 store 会绕过 `_public_plan`，把内部键原样送进响应体。
    """
    from app import main

    source = inspect.getsource(main)
    assert "_store.get_plan(" not in source
    assert "_learning_store.get_plan(" not in source


# ── F. 真只读：身份改造不引入写入 ─────────────────────────────────────────────


def test_identity_path_writes_nothing_but_the_plan(tmp_path: Path) -> None:
    """`generate` + `persist_generated` 只写 plans 表，不碰会话 / 复习 / registry。"""
    planner = GoalPlannerService()
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    lifecycle = PlanLifecycleService(store, planner)
    response = planner.generate(_request(), principal_id=PRINCIPAL_A)
    lifecycle.persist_generated(response, PRINCIPAL_A)

    assert store.get(response.plan_id) is None
    assert store.get_review(response.plan_id) is None
    assert store.get_plan(response.plan_id) is not None
