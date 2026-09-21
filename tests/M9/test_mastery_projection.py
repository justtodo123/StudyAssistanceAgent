"""M9 只读 mastery 投影与计划身份修复测试。

覆盖四类主张：
- 跨会话答题聚合（跨会话读取是本次新增的数据面）；
- 聚合身份 = 知识条目 file 路径，三分支解析与 `StudySessionService._log_review` 同序；
- 只读保证（真守卫）、有界输入、确定性；
- 计划身份含派生输入摘要（复习/mastery/每日学时），以及存量计划的兼容语义。
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import pytest

from app.goal_planner import GoalPlannerService
from app.learning_store import SqliteLearningStore
from app.mastery_projection import (
    MasteryProjectionService,
    knowledge_entry_exists,
    resolve_mastery_file_key,
)
from app.models import (
    GoalPlanConstraints,
    GoalPlanRequest,
    GoalPlanResponse,
    GoalPlanTask,
    PlanProgressRequest,
    RetrievalChunk,
)
from app.plan_lifecycle import PlanLifecycleService
from app.study_session import StudySessionService, deserialize_session


pytestmark = pytest.mark.m9

_OS_FILE = "knowledge/os/process-management.md"
_OS_FILE_2 = "knowledge/os/process-scheduling.md"
_MISSING_TOPIC = "不存在的主题"
_TABLES = (
    "answer_attempts",
    "review_history",
    "study_sessions",
    "plans",
    "plan_tasks",
    "progress_events",
)


# ── 工具 ──────────────────────────────────────────────────────────────────────


def _attempt(qid: str, correct: bool, at: str) -> dict[str, Any]:
    return {
        "question_id": qid,
        "attempt_count": 1,
        "answer_normalized": qid,
        "correct": correct,
        "feedback": "",
        "created_at": at,
    }


def _record(
    session_id: str,
    *,
    course: str = "os",
    topic: str = "",
    sources: list[dict[str, Any]] | None = None,
    questions: list[dict[str, Any]] | None = None,
    attempts: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """与 `serialize_session` 同形的会话记录（`store.save` 会据此落 study_sessions + answer_attempts）。"""
    record = {
        "session_id": session_id,
        "course": course,
        "topic": topic,
        "state": "completed",
        "score": None,
        "sources": sources or [],
        "questions": questions or [],
        "created_at": "2026-09-01T08:00:00",
        "updated_at": "2026-09-01T08:05:00",
        "answer_records": attempts or [],
    }
    record.update(extra)
    return record


def _request(**kwargs: Any) -> GoalPlanRequest:
    defaults: dict[str, Any] = {"goal": "两周内掌握进程调度与死锁", "course": "os"}
    defaults.update(kwargs)
    return GoalPlanRequest(**defaults)


@pytest.fixture
def store(tmp_path: Path) -> SqliteLearningStore:
    return SqliteLearningStore(tmp_path / "learning.sqlite3")


class _SpyScheduler:
    def __init__(self) -> None:
        self.logged: list[str] = []

    def log_review(self, req: Any) -> dict[str, Any]:
        self.logged.append(req.file)
        return {"file": req.file, "review_count": len(self.logged)}


# ── A. 跨会话聚合 ─────────────────────────────────────────────────────────────


def test_aggregate_is_cross_session(store: SqliteLearningStore) -> None:
    store.save(
        _record(
            "s1",
            sources=[{"file": _OS_FILE}],
            attempts=[
                _attempt("q1", True, "2026-09-01T09:00:00"),
                _attempt("q2", False, "2026-09-01T09:05:00"),
            ],
        )
    )
    store.save(
        _record(
            "s2",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q3", True, "2026-09-02T09:00:00")],
        )
    )

    rows = store.aggregate_attempts_by_session()

    assert set(rows) == {"s1", "s2"}
    assert (rows["s1"]["attempts"], rows["s1"]["correct"]) == (2, 1)
    assert rows["s1"]["last_mastered"] == "2026-09-01T09:00:00"
    assert (rows["s2"]["attempts"], rows["s2"]["correct"]) == (1, 1)


def test_aggregate_excludes_sessions_without_attempts(store: SqliteLearningStore) -> None:
    """无答题证据的会话不进投影，而不是补 0。"""
    store.save(_record("s1", sources=[{"file": _OS_FILE}]))
    store.save(
        _record(
            "s2",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )

    assert set(store.aggregate_attempts_by_session()) == {"s2"}


def test_aggregate_does_not_leak_payload_fields(store: SqliteLearningStore) -> None:
    """有界输入契约：跨界的只有两个短出处字符串，不是整份 payload。"""
    store.save(
        _record(
            "s1",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
            explanation="讲解正文" * 500,
            remediation="补救说明",
            tool_trace=[{"step": "explain"}],
        )
    )

    rows = store.aggregate_attempts_by_session()

    assert set(rows["s1"]) == {
        "course",
        "topic",
        "source_file",
        "question_source_file",
        "attempts",
        "correct",
        "last_mastered",
    }


def test_aggregate_survives_malformed_payload(store: SqliteLearningStore) -> None:
    """payload 被外部改坏时退化为「无出处」，而不是把整条只读路径打挂。"""
    store.save(
        _record(
            "s1",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )
    with store._connect() as connection:
        connection.execute(
            "UPDATE study_sessions SET payload = ? WHERE session_id = ?", ("{not json", "s1")
        )

    rows = store.aggregate_attempts_by_session()

    assert rows["s1"]["source_file"] == ""
    assert rows["s1"]["attempts"] == 1


# ── B. 聚合身份 = 知识条目 file 路径 ───────────────────────────────────────────


def test_mastery_key_is_the_knowledge_file_not_the_free_text_topic(
    store: SqliteLearningStore,
) -> None:
    store.save(
        _record(
            "s1",
            topic="进程调度",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )

    projection = MasteryProjectionService(store).mastery_by_file()

    assert set(projection) == {_OS_FILE}
    assert f"knowledge/os/进程调度.md" not in projection


def test_mastery_fallback_uses_course_and_topic_and_merges(
    store: SqliteLearningStore,
) -> None:
    """无出处会话经回退键归入同一条目，计数累加、last_mastered 取较晚者。"""
    store.save(
        _record(
            "s1",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )
    store.save(
        _record(
            "s2",
            topic="process-management",
            sources=[],
            attempts=[_attempt("q2", True, "2026-09-03T09:00:00")],
        )
    )

    projection = MasteryProjectionService(store).mastery_by_file()

    assert set(projection) == {_OS_FILE}
    assert projection[_OS_FILE]["attempts"] == 2
    assert projection[_OS_FILE]["last_mastered"] == "2026-09-03T09:00:00"


def test_mastery_fallback_is_dropped_when_entry_does_not_exist(
    store: SqliteLearningStore,
) -> None:
    store.save(
        _record(
            "s1",
            topic=_MISSING_TOPIC,
            sources=[],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )

    assert MasteryProjectionService(store).mastery_by_file() == {}


def test_mastery_prefers_question_source_file_over_topic_fallback(
    store: SqliteLearningStore,
) -> None:
    """`_log_review` 的中间分支：无检索出处但有出题出处时，出处是题目文件而非 topic 猜测。"""
    store.save(
        _record(
            "s1",
            topic=_MISSING_TOPIC,
            sources=[],
            questions=[{"id": "q1", "question": {"source_file": _OS_FILE_2}}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )

    projection = MasteryProjectionService(store).mastery_by_file()

    assert set(projection) == {_OS_FILE_2}


def test_mastery_excludes_non_knowledge_source_files(store: SqliteLearningStore) -> None:
    """额外资料源的标识（extra://）不是知识条目，不进以条目路径为身份的键空间。"""
    store.save(
        _record(
            "s1",
            sources=[{"file": "extra://notes-1/week-01.md"}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )

    assert MasteryProjectionService(store).mastery_by_file() == {}


def test_resolve_mastery_file_key_branches() -> None:
    assert resolve_mastery_file_key("os", "t", _OS_FILE, _OS_FILE_2) == _OS_FILE
    assert resolve_mastery_file_key("os", "t", "", _OS_FILE_2) == _OS_FILE_2
    assert resolve_mastery_file_key("os", "t", "", "") == "knowledge/os/t.md"
    assert resolve_mastery_file_key("", "", "", "") is None
    assert resolve_mastery_file_key("os", "", "", "") is None


def test_knowledge_entry_exists_rejects_escaping_and_bad_suffixes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("app.mastery_projection.config.KNOWLEDGE_ROOT", tmp_path)
    (tmp_path / "os").mkdir()
    (tmp_path / "os" / "ok.md").write_text("---\ntitle: x\n---\n", encoding="utf-8")

    assert knowledge_entry_exists("knowledge/os/ok.md") is True
    assert knowledge_entry_exists("knowledge/os/missing.md") is False
    assert knowledge_entry_exists("knowledge/os/../../etc/passwd.md") is False
    assert knowledge_entry_exists("knowledge/os/ok.txt") is False
    assert knowledge_entry_exists("knowledge/os/") is False
    assert knowledge_entry_exists("extra://notes-1/w.md") is False


@pytest.mark.parametrize(
    "shape",
    ["sources", "questions", "fallback"],
)
def test_resolution_matches_log_review_rule(shape: str) -> None:
    """投影的键解析必须与 `_log_review` 同序。

    两者不能共享代码：`_log_review` 必须**记录**不可映射的回退，投影必须**丢弃**它。
    因此等价性由测试钉住，而不是靠耦合。
    """
    source = {
        "id": "s",
        "file": _OS_FILE,
        "title": "进程管理",
        "course": "os",
        "tags": [],
        "content": "正文",
    }
    question = {
        "question": "进程与线程的区别？",
        "type": "example",
        "answer": "资源分配 vs 调度",
        "source_file": _OS_FILE_2,
        "source_title": "进程调度",
        "tags": [],
        "difficulty": "中等",
    }
    record = _record("s1", topic="process-management")
    if shape == "sources":
        record["sources"] = [source]
    elif shape == "questions":
        record["questions"] = [{"id": "q1", "question": question, "attempt_count": 1, "correct": True}]
    session = deserialize_session(record)

    spy = _SpyScheduler()
    service = StudySessionService(
        qa_service=object(), quiz_service=object(), review_scheduler=spy
    )
    service._log_review(session)

    expected = resolve_mastery_file_key(
        course=session.course,
        topic=session.topic,
        source_file=session.sources[0].file if session.sources else "",
        question_source_file=(
            session.questions[0].question.source_file if session.questions else ""
        ),
    )
    assert spy.logged == [expected]


def test_retrieval_chunk_file_field_is_the_identity_source() -> None:
    """钉住上游契约：投影读的 `$.sources[0].file` 确实来自 RetrievalChunk.file。"""
    chunk = RetrievalChunk(
        id="c", file=_OS_FILE, title="t", course="os", tags=[], content="正文"
    )
    assert chunk.model_dump()["file"] == _OS_FILE


# ── C. 只读保证 ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _DbState:
    dump: str
    digest: str
    counts: dict[str, int]
    data_version: int
    observer_total_changes: int


def _db_state(observer: sqlite3.Connection) -> _DbState:
    dump = "\n".join(observer.iterdump())
    counts = {
        table: int(observer.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in _TABLES
    }
    return _DbState(
        dump=dump,
        digest=hashlib.sha256(dump.encode("utf-8")).hexdigest(),
        counts=counts,
        data_version=int(observer.execute("PRAGMA data_version").fetchone()[0]),
        observer_total_changes=observer.total_changes,
    )


def _seeded_store(tmp_path: Path) -> SqliteLearningStore:
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    store.save(
        _record(
            "s1",
            sources=[{"file": _OS_FILE}],
            attempts=[
                _attempt("q1", True, "2026-09-01T09:00:00"),
                _attempt("q2", False, "2026-09-01T09:05:00"),
            ],
        )
    )
    store.save_review(
        _OS_FILE,
        {
            "file": _OS_FILE,
            "course": "os",
            "review_count": 1,
            "last_reviewed": "2026-09-01T09:00:00",
            "next_review": "2026-09-02T09:00:00",
            "interval_days": 1,
            "source_session_id": "s1",
        },
    )
    return store


def _install_write_traps(monkeypatch: pytest.MonkeyPatch, store: SqliteLearningStore):
    """把每个写入口换成 fail，并审计每个连接的 total_changes 增量。"""
    observer = sqlite3.connect(str(store.db_path))
    observer.execute("PRAGMA query_only=ON")
    deltas: list[int] = []
    original_connect = store._connect

    @contextmanager
    def audited_connect() -> Iterator[sqlite3.Connection]:
        with original_connect() as connection:
            started = connection.total_changes
            yield connection
            deltas.append(connection.total_changes - started)

    monkeypatch.setattr(store, "_connect", audited_connect)
    for name, message in (
        ("save", "projection attempted a session write"),
        ("save_review", "projection attempted a review write"),
        ("save_plan", "projection attempted a plan write"),
        ("save_progress_event", "projection attempted a progress write"),
        ("migrate_review_history", "projection attempted a migration write"),
    ):
        monkeypatch.setattr(
            SqliteLearningStore,
            name,
            lambda *a, _m=message, **k: pytest.fail(_m),
        )
    return observer, deltas


def test_mastery_projection_preserves_learning_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _seeded_store(tmp_path)
    observer, deltas = _install_write_traps(monkeypatch, store)
    before = _db_state(observer)

    projection = MasteryProjectionService(store).mastery_by_file()

    after = _db_state(observer)
    observer.close()

    assert projection[_OS_FILE]["attempts"] == 2
    assert before.dump == after.dump
    assert before.digest == after.digest
    assert before.counts == after.counts
    assert before.data_version == after.data_version
    assert before.observer_total_changes == after.observer_total_changes == 0
    assert all(delta == 0 for delta in deltas)


def test_planner_with_live_projection_does_not_write_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """复合路径的只读保证：投影接入 Planner 后整条生成链路仍零写入。"""
    store = _seeded_store(tmp_path)
    observer, deltas = _install_write_traps(monkeypatch, store)
    before = _db_state(observer)

    planner = GoalPlannerService(
        review_history=store.all_reviews(),
        mastery_projection=MasteryProjectionService(store),
    )
    plan = planner.generate(_request())

    after = _db_state(observer)
    observer.close()

    assert plan.plan_id
    assert before == after
    assert all(delta == 0 for delta in deltas)


def test_mastery_projection_does_not_build_chunk_index(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.knowledge_index as knowledge_index

    def _explode(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("mastery projection must not build the chunk index")

    monkeypatch.setattr(knowledge_index, "build_index_cached", _explode, raising=False)
    monkeypatch.setattr(knowledge_index, "build_index", _explode, raising=False)
    store = SqliteLearningStore(":memory:")
    store.save(
        _record(
            "s1",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )

    assert MasteryProjectionService(store).mastery_by_file()[_OS_FILE]["attempts"] == 1


def test_mastery_projection_module_is_bounded_by_source() -> None:
    """源码级护栏：不 import 检索/生成链路，也不出现正文相关符号。"""
    import app.mastery_projection as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("knowledge_index", "llm_client", "split_headings", "content"):
        assert forbidden not in source, f"mastery projection 不应出现 {forbidden!r}"


def test_mastery_projection_reads_the_aggregate_exactly_once(store: SqliteLearningStore) -> None:
    store.save(
        _record(
            "s1",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )
    calls = {"n": 0}
    original = store.aggregate_attempts_by_session

    def _counted() -> dict[str, dict[str, Any]]:
        calls["n"] += 1
        return original()

    store.aggregate_attempts_by_session = _counted  # type: ignore[method-assign]

    projection = MasteryProjectionService(store)
    projection.mastery_by_file()
    assert calls["n"] == 1

    planner = GoalPlannerService(mastery_projection=projection)
    planner.generate(_request())
    assert calls["n"] == 2


# ── D. 确定性 ─────────────────────────────────────────────────────────────────


def test_mastery_projection_is_deterministic(tmp_path: Path) -> None:
    store = _seeded_store(tmp_path)
    projection = MasteryProjectionService(store)

    assert projection.mastery_by_file() == projection.mastery_by_file()


def test_mastery_projection_is_independent_of_insertion_order(tmp_path: Path) -> None:
    first = SqliteLearningStore(tmp_path / "a.sqlite3")
    second = SqliteLearningStore(tmp_path / "b.sqlite3")
    for store, order in ((first, ("s1", "s2")), (second, ("s2", "s1"))):
        for session_id in order:
            store.save(
                _record(
                    session_id,
                    sources=[{"file": _OS_FILE}],
                    attempts=[_attempt(f"q-{session_id}", True, "2026-09-01T09:00:00")],
                )
            )

    assert (
        MasteryProjectionService(first).mastery_by_file()
        == MasteryProjectionService(second).mastery_by_file()
    )


def test_plan_is_deterministic_with_mastery(tmp_path: Path) -> None:
    store = _seeded_store(tmp_path)
    planner = GoalPlannerService(mastery_projection=MasteryProjectionService(store))

    first = planner.generate(_request())
    second = planner.generate(_request())

    assert first.plan_id == second.plan_id
    assert first.revisions[0].days == second.revisions[0].days
    assert first.summary == second.summary


# ── E. 计划身份含派生输入摘要 ──────────────────────────────────────────────────


def test_plan_id_changes_when_review_history_changes() -> None:
    """已证实缺陷的回归：派生状态变了却共用 plan_id，会让过期计划被幂等分支静默保留。"""
    clean = GoalPlannerService(review_history={})
    reviewed = GoalPlannerService(review_history={_OS_FILE: {"review_count": 2}})

    assert clean.generate(_request()).plan_id != reviewed.generate(_request()).plan_id


def test_plan_id_changes_when_mastery_changes(tmp_path: Path) -> None:
    store = _seeded_store(tmp_path)
    with_mastery = GoalPlannerService(mastery_projection=MasteryProjectionService(store))
    without = GoalPlannerService()

    assert with_mastery.generate(_request()).plan_id != without.generate(_request()).plan_id


def test_plan_id_changes_when_hours_per_day_changes() -> None:
    """第二个独立实例：hours_per_day 经 _distribute 决定分日，必须进身份键。"""
    planner = GoalPlannerService()

    short = planner.generate(_request(hours_per_day=1.0))
    long = planner.generate(_request(hours_per_day=8.0))

    assert short.plan_id != long.plan_id
    assert (short.total_days, long.total_days) == (15, 2)


def test_plan_id_is_stable_when_derived_inputs_are_unchanged(tmp_path: Path) -> None:
    store = _seeded_store(tmp_path)
    first = GoalPlannerService(
        review_history=store.all_reviews(), mastery_projection=MasteryProjectionService(store)
    )
    second = GoalPlannerService(
        review_history=store.all_reviews(), mastery_projection=MasteryProjectionService(store)
    )

    assert first.generate(_request()).plan_id == second.generate(_request()).plan_id


def test_plan_id_ignores_derived_state_outside_the_plan_scope(tmp_path: Path) -> None:
    """摘要只覆盖本计划范围内的任务，范围外的状态变化不churn plan_id。"""
    store = _seeded_store(tmp_path)
    planner = GoalPlannerService(
        review_history=store.all_reviews(), mastery_projection=MasteryProjectionService(store)
    )
    before = planner.generate(_request(course="os")).plan_id

    store.save(
        _record(
            "ds-1",
            course="ds",
            sources=[{"file": "knowledge/ds/sorting.md"}],
            attempts=[_attempt("q1", True, "2026-09-05T09:00:00")],
        )
    )

    assert planner.generate(_request(course="os")).plan_id == before


def test_same_plan_id_implies_identical_task_payload(tmp_path: Path) -> None:
    """身份不变量：plan_id 相同 ⇒ 任务载荷与 summary 相同。"""
    store = _seeded_store(tmp_path)
    planner = GoalPlannerService(mastery_projection=MasteryProjectionService(store))

    first = planner.generate(_request())
    second = planner.generate(_request())

    assert first.plan_id == second.plan_id
    flatten = lambda p: [t.model_dump() for d in p.revisions[0].days for t in d.tasks]
    assert flatten(first) == flatten(second)
    assert first.summary == second.summary


def test_stale_plan_is_not_silently_retained(tmp_path: Path) -> None:
    """端到端：派生状态变化后重生成会写新记录，旧记录逐字节保留且仍可读。"""
    store = _seeded_store(tmp_path)
    planner = GoalPlannerService(mastery_projection=MasteryProjectionService(store))
    lifecycle = PlanLifecycleService(store, planner)

    first = planner.generate(_request())
    lifecycle.persist_generated(first)
    lifecycle.adopt(first.plan_id)
    before = store.get_plan(first.plan_id)

    store.save(
        _record(
            "s2",
            sources=[{"file": _OS_FILE_2}],
            attempts=[_attempt("q9", True, "2026-09-09T09:00:00")],
        )
    )
    second = planner.generate(_request())
    lifecycle.persist_generated(second)

    assert second.plan_id != first.plan_id
    assert store.get_plan(second.plan_id) is not None
    assert store.get_plan(first.plan_id) == before
    assert store.get_plan(first.plan_id)["state"] == "adopted"


# ── F. 存量计划兼容 ───────────────────────────────────────────────────────────


def _legacy_plan_id(goal: str, target_date: str, course: str | None) -> str:
    """修复前的身份公式（内联冻结，用于构造存量记录）。"""
    normalized = re.sub(r"\s+", " ", goal.strip()).lower()
    key = "|".join([normalized, target_date, course or "", "", ""])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _legacy_record(plan_id: str) -> dict[str, Any]:
    task = {
        "task_id": "abc123",
        "topic": "进程管理",
        "file": _OS_FILE,
        "difficulty": "中等",
        "estimated_minutes": 35,
        "priority": "medium",
        "reviewed": False,
    }
    return {
        "plan_id": plan_id,
        "schema_version": "m9-goal-plan-v1",
        "state": "generated",
        "revision_id": 1,
        "goal": "两周内掌握进程调度与死锁",
        "target_date": "2026-09-15",
        "total_days": 2,
        "total_hours": 0.6,
        "course": "os",
        "hours_per_day": 2.0,
        "constraints": {"required_topics": [], "excluded_topics": []},
        "parent_revision_id": None,
        "adopted_at": None,
        "created_at": "2026-09-01T08:00:00",
        "updated_at": "2026-09-01T08:00:00",
        "revisions": [],
        "tasks": [task],
    }


def test_legacy_task_payload_without_mastery_fields_validates() -> None:
    """纯增量带默认值字段：存量 payload 缺键也能反序列化。"""
    task = _legacy_record("x")["tasks"][0]
    validated = GoalPlanTask.model_validate(task)

    assert (validated.mastery_attempts, validated.mastery_correct) == (0, 0)
    assert validated.mastery_last_mastered is None

    response = GoalPlanResponse.model_validate(
        {
            "plan_id": "x",
            "schema_version": "m9-goal-plan-v1",
            "revision_id": 1,
            "target_date": "2026-09-15",
            "total_days": 2,
            "total_hours": 0.6,
            "revisions": [],
            "summary": {},
            "tasks": [task],
        }
    )
    assert response.plan_id == "x"


def test_legacy_plan_record_remains_readable(tmp_path: Path) -> None:
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    legacy_id = _legacy_plan_id("两周内掌握进程调度与死锁", "2026-09-15", "os")
    store.save_plan(_legacy_record(legacy_id))
    lifecycle = PlanLifecycleService(store, GoalPlannerService())

    assert store.get_plan(legacy_id) is not None
    assert lifecycle.get(legacy_id)["plan_id"] == legacy_id


def test_legacy_plan_id_stops_matching_newly_generated_plan(tmp_path: Path) -> None:
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    legacy_id = _legacy_plan_id("两周内掌握进程调度与死锁", "2026-09-15", "os")
    store.save_plan(_legacy_record(legacy_id))
    lifecycle = PlanLifecycleService(store, GoalPlannerService())

    fresh = GoalPlannerService().generate(_request(target_date="2026-09-15"))
    assert fresh.plan_id != legacy_id

    lifecycle.persist_generated(fresh)
    assert store.get_plan(legacy_id) == _legacy_record(legacy_id)


def test_legacy_plan_can_still_be_replanned(tmp_path: Path) -> None:
    """重规划不改写身份：保留 parent revision 链与已采纳状态。"""
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    legacy_id = _legacy_plan_id("两周内掌握进程调度与死锁", "2026-09-15", "os")
    store.save_plan(_legacy_record(legacy_id))
    lifecycle = PlanLifecycleService(store, GoalPlannerService())

    for i in range(3):
        lifecycle.record_progress(
            PlanProgressRequest(plan_id=legacy_id, task_id=f"t{i}", event="skipped")
        )
    replanned = lifecycle.replan(legacy_id)

    assert replanned["plan_id"] == legacy_id
    assert replanned["revision_id"] == 2


def test_response_without_projection_matches_legacy_ordering(
    goal_planner_service: GoalPlannerService,
) -> None:
    """未注入投影时行为与接入前一致：mastery 桶全为 0，排序退化为 (reviewed, priority, file)。"""
    plan = goal_planner_service.generate(_request())

    assert plan.summary["mastery"] == {
        "no_evidence": plan.summary["total_tasks"],
        "attempted": 0,
        "mastered": 0,
    }
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    tasks = [t for d in plan.revisions[0].days for t in d.tasks]
    expected = sorted(
        tasks, key=lambda t: (t.reviewed, priority_rank.get(t.priority, 1), t.file)
    )
    assert [t.task_id for t in tasks] == [t.task_id for t in expected]


# ── G. Planner 与 mastery 集成 ────────────────────────────────────────────────


def test_mastery_reorders_within_the_same_reviewed_bucket(tmp_path: Path) -> None:
    """同为中等难度：无证据的条目排到已掌握条目之前（字典序原本相反）。"""
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    store.save(
        _record(
            "s1",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )
    planner = GoalPlannerService(mastery_projection=MasteryProjectionService(store))

    plan = planner.generate(_request())
    order = [t.file for d in plan.revisions[0].days for t in d.tasks]

    assert order.index(_OS_FILE_2) < order.index(_OS_FILE)


def test_mastery_never_outranks_the_reviewed_flag(tmp_path: Path) -> None:
    """reviewed 仍是排序主键：已掌握但未复习的任务仍排在已复习任务之后。"""
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    store.save(
        _record(
            "s1",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )
    planner = GoalPlannerService(
        review_history={_OS_FILE_2: {"review_count": 1}},
        mastery_projection=MasteryProjectionService(store),
    )

    plan = planner.generate(_request())
    tasks = [t for d in plan.revisions[0].days for t in d.tasks]
    flags = [t.reviewed for t in tasks]

    assert any(flags) and not all(flags)
    assert flags == sorted(flags)  # False(未复习) 全部排在 True(已复习) 之前
    unreviewed_files = [t.file for t in tasks[: flags.count(False)]]
    # 已掌握但未复习 → mastery 不能把它提升出未复习桶；已复习的条目不得落进该桶
    assert _OS_FILE in unreviewed_files
    assert _OS_FILE_2 not in unreviewed_files
    assert tasks[flags.count(False)].file == _OS_FILE_2


def test_nullable_mastery_projection_is_a_guard_not_an_error(
    goal_planner_service: GoalPlannerService,
) -> None:
    """与 `_overdue_task_ids` 同形：依赖缺省是守卫，不是错误。"""
    plan = goal_planner_service.generate(_request())

    assert all(
        (t.mastery_attempts, t.mastery_correct, t.mastery_last_mastered) == (0, 0, None)
        for d in plan.revisions[0].days
        for t in d.tasks
    )


def test_mastery_fields_survive_persistence(tmp_path: Path) -> None:
    """记录扁平化修复：plan["tasks"] 与 plan["revisions"] 对同一批任务给出一致表示。"""
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    store.save(
        _record(
            "s1",
            sources=[{"file": _OS_FILE}],
            attempts=[_attempt("q1", True, "2026-09-01T09:00:00")],
        )
    )
    planner = GoalPlannerService(mastery_projection=MasteryProjectionService(store))
    lifecycle = PlanLifecycleService(store, planner)

    plan = planner.generate(_request())
    lifecycle.persist_generated(plan)
    stored = store.get_plan(plan.plan_id)

    flat = {t["task_id"]: t for t in stored["tasks"]}
    nested = {
        t["task_id"]: t
        for revision in stored["revisions"]
        for day in revision["days"]
        for t in day["tasks"]
    }
    assert set(flat) == set(nested)
    for task_id, task in flat.items():
        for field in ("mastery_attempts", "mastery_correct", "mastery_last_mastered"):
            assert task[field] == nested[task_id][field]
    by_file = {t["file"]: t for t in flat.values()}
    assert by_file[_OS_FILE]["mastery_attempts"] == 1
    assert by_file[_OS_FILE]["mastery_correct"] == 1
