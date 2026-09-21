"""SQLite persistence for study sessions and review history.

The repositories are interfaces plus a stdlib sqlite3 implementation.
Existing review_history.json is migrated once, then left beside the database
as a .migrated backup. A corrupt database file is quarantined and replaced.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol, runtime_checkable

SCHEMA = """
CREATE TABLE IF NOT EXISTS study_sessions (
    session_id TEXT PRIMARY KEY,
    course TEXT NOT NULL,
    topic TEXT NOT NULL,
    state TEXT NOT NULL,
    score REAL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS answer_attempts (
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    attempt_count INTEGER NOT NULL,
    answer_normalized TEXT NOT NULL DEFAULT '',
    correct INTEGER,
    feedback TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    PRIMARY KEY (session_id, question_id, attempt_count)
);

CREATE TABLE IF NOT EXISTS review_history (
    file TEXT PRIMARY KEY,
    course TEXT NOT NULL DEFAULT '',
    review_count INTEGER NOT NULL,
    last_reviewed TEXT NOT NULL,
    next_review TEXT NOT NULL,
    interval_days INTEGER NOT NULL,
    source_session_id TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'generated',
    goal TEXT NOT NULL,
    target_date TEXT NOT NULL,
    total_days INTEGER NOT NULL,
    total_hours REAL NOT NULL,
    parent_revision_id INTEGER,
    adopted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_tasks (
    plan_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    file TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    estimated_minutes INTEGER NOT NULL,
    priority TEXT NOT NULL,
    reviewed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (plan_id, task_id)
);

CREATE TABLE IF NOT EXISTS progress_events (
    event_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    event TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);
"""


@runtime_checkable
class StudySessionRepository(Protocol):
    def get(self, session_id: str) -> dict[str, Any] | None: ...

    def save(self, record: dict[str, Any]) -> None: ...


@runtime_checkable
class ReviewHistoryRepository(Protocol):
    def get(self, file_key: str) -> dict[str, Any] | None: ...

    def save(self, file_key: str, entry: dict[str, Any]) -> dict[str, Any]: ...

    def all(self) -> dict[str, dict[str, Any]]: ...

    def find_by_source_session(self, session_id: str) -> dict[str, Any] | None: ...


class SqliteLearningStore:
    """Single SQLite file that implements both repository interfaces."""

    def __init__(
        self,
        db_path: str | Path,
        json_history_path: str | Path | None = None,
    ) -> None:
        self.db_path = Path(db_path) if str(db_path) != ":memory:" else Path(":memory:")
        self.json_history_path = Path(json_history_path) if json_history_path else None
        self._lock = threading.Lock()
        self._memory: sqlite3.Connection | None = (
            sqlite3.connect(":memory:", check_same_thread=False)
            if str(db_path) == ":memory:"
            else None
        )
        self._prepare_file()
        self._init_schema()
        if self.json_history_path is not None:
            self.migrate_review_history(self.json_history_path)

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM study_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def save(self, record: dict[str, Any]) -> None:
        session_id = str(record["session_id"])
        payload = json.dumps(record, ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO study_sessions(
                    session_id, course, topic, state, score, payload, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    course = excluded.course,
                    topic = excluded.topic,
                    state = excluded.state,
                    score = excluded.score,
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    record.get("course", ""),
                    record.get("topic", ""),
                    record.get("state", ""),
                    record.get("score"),
                    payload,
                    record.get("created_at", ""),
                    record.get("updated_at", ""),
                ),
            )
            connection.execute(
                "DELETE FROM answer_attempts WHERE session_id = ?",
                (session_id,),
            )
            for attempt in record.get("answer_records", []):
                connection.execute(
                    """
                    INSERT OR REPLACE INTO answer_attempts(
                        session_id, question_id, attempt_count, answer_normalized,
                        correct, feedback, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        attempt.get("question_id", ""),
                        int(attempt.get("attempt_count", 0)),
                        attempt.get("answer_normalized", ""),
                        None if attempt.get("correct") is None else int(bool(attempt["correct"])),
                        attempt.get("feedback", ""),
                        attempt.get("created_at", ""),
                    ),
                )

    def list_answer_attempts(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT question_id, attempt_count, answer_normalized, correct, feedback, created_at
                FROM answer_attempts
                WHERE session_id = ?
                ORDER BY attempt_count
                """,
                (session_id,),
            ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "question_id": row[0],
                    "attempt_count": row[1],
                    "answer_normalized": row[2],
                    "correct": None if row[3] is None else bool(row[3]),
                    "feedback": row[4],
                    "created_at": row[5],
                }
            )
        return results

    def aggregate_attempts_by_session(self) -> dict[str, dict[str, Any]]:
        """跨会话答题聚合（只读）：`session_id → {course, topic, source_file,
        question_source_file, attempts, correct, last_mastered}`。

        `list_answer_attempts` 只按单个 session 读；M9 的 mastery 只读投影需要的是跨会话视图，
        因此这里做一次 join 聚合。三点刻意设计：

        - **一次查询**：会话身份列与答题计数在同一条语句里取，既避免 N+1，也避免两次读之间
          被并发写撕裂（`_connect` 的锁只覆盖单次语句）；
        - **不把 payload 整份读进内存**：只用 `json_extract` 取两个出处字段。payload 含讲解
          正文与 tool_trace，整份读出会让投影输入随「会话数 × 载荷大小」膨胀；这里过界的只有
          两个短字符串，输入有界；
        - **`json_valid` 兜底**：`save()` 是唯一写者且总是 `json.dumps`，正常库里 payload 必然
          合法；万一遇到被外部改坏的行，`json_valid` 让该行退化成「无出处 → 走回退」，而不是让
          `json_extract` 抛错把整条只读路径打挂。

        `JOIN` 天然排除没有答题记录的会话——「无答题证据」不进投影，而不是补 0。
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.session_id,
                       s.course,
                       s.topic,
                       json_extract(
                           CASE WHEN json_valid(s.payload) THEN s.payload ELSE '{}' END,
                           '$.sources[0].file'
                       ) AS source_file,
                       json_extract(
                           CASE WHEN json_valid(s.payload) THEN s.payload ELSE '{}' END,
                           '$.questions[0].question.source_file'
                       ) AS question_source_file,
                       COUNT(a.question_id) AS attempts,
                       COALESCE(SUM(CASE WHEN a.correct = 1 THEN 1 ELSE 0 END), 0) AS correct,
                       MAX(CASE WHEN a.correct = 1 THEN a.created_at END) AS last_mastered
                FROM study_sessions AS s
                JOIN answer_attempts AS a ON a.session_id = s.session_id
                GROUP BY s.session_id
                ORDER BY s.session_id
                """
            ).fetchall()
        return {
            row[0]: {
                "course": row[1] or "",
                "topic": row[2] or "",
                "source_file": row[3] or "",
                "question_source_file": row[4] or "",
                "attempts": int(row[5]),
                "correct": int(row[6]),
                "last_mastered": row[7],
            }
            for row in rows
        }

    def get_review(self, file_key: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM review_history WHERE file = ?",
                (file_key,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def save_review(self, file_key: str, entry: dict[str, Any]) -> dict[str, Any]:
        stored = dict(entry)
        stored.setdefault("file", file_key)
        existing = self.get_review(file_key)
        if existing and _review_unchanged(existing, stored):
            return existing
        payload = json.dumps(stored, ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO review_history(
                    file, course, review_count, last_reviewed, next_review,
                    interval_days, source_session_id, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file) DO UPDATE SET
                    course = excluded.course,
                    review_count = excluded.review_count,
                    last_reviewed = excluded.last_reviewed,
                    next_review = excluded.next_review,
                    interval_days = excluded.interval_days,
                    source_session_id = excluded.source_session_id,
                    payload = excluded.payload
                """,
                (
                    file_key,
                    stored.get("course", ""),
                    int(stored.get("review_count", 0)),
                    stored.get("last_reviewed", ""),
                    stored.get("next_review", ""),
                    int(stored.get("interval_days", 0)),
                    stored.get("source_session_id", ""),
                    payload,
                ),
            )
        return stored

    def all_reviews(self) -> dict[str, dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT file, payload FROM review_history").fetchall()
        return {row[0]: json.loads(row[1]) for row in rows}

    def find_by_source_session(self, session_id: str) -> dict[str, Any] | None:
        if not session_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM review_history WHERE source_session_id = ? LIMIT 1",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    # Protocol aliases so one object can be injected as either repository.
    def all(self) -> dict[str, dict[str, Any]]:
        return self.all_reviews()

    def find_review(self, file_key: str) -> dict[str, Any] | None:
        return self.get_review(file_key)

    def migrate_review_history(self, json_path: Path) -> int:
        if not json_path.exists():
            return 0
        if self.all_reviews():
            return 0
        try:
            raw = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0
        if not isinstance(raw, dict):
            return 0
        imported = 0
        for file_key, entry in raw.items():
            if not isinstance(entry, dict):
                continue
            self.save_review(str(file_key), entry)
            imported += 1
        if imported:
            migrated = json_path.with_name(json_path.name + ".migrated")
            try:
                json_path.replace(migrated)
            except OSError:
                pass
        return imported

    def _prepare_file(self) -> None:
        if self._memory is not None:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            return
        try:
            connection = sqlite3.connect(str(self.db_path))
            try:
                connection.execute("SELECT 1 FROM sqlite_master LIMIT 1")
            finally:
                connection.close()
        except sqlite3.Error:
            corrupt = self.db_path.with_name(self.db_path.name + ".corrupt")
            try:
                if corrupt.exists():
                    corrupt.unlink()
                self.db_path.replace(corrupt)
            except OSError:
                self.db_path.unlink(missing_ok=True)

    # ── M9 计划生命周期持久化 ─────────────────────────────────────────────────

    def save_plan(self, plan: dict[str, Any]) -> None:
        payload = json.dumps(plan, ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO plans(
                    plan_id, schema_version, state, goal, target_date, total_days,
                    total_hours, parent_revision_id, adopted_at, created_at, updated_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(plan_id) DO UPDATE SET
                    state = excluded.state,
                    goal = excluded.goal,
                    target_date = excluded.target_date,
                    total_days = excluded.total_days,
                    total_hours = excluded.total_hours,
                    parent_revision_id = excluded.parent_revision_id,
                    adopted_at = excluded.adopted_at,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    plan["plan_id"],
                    plan.get("schema_version", ""),
                    plan.get("state", "generated"),
                    plan.get("goal", ""),
                    plan.get("target_date", ""),
                    int(plan.get("total_days", 0)),
                    float(plan.get("total_hours", 0.0)),
                    plan.get("parent_revision_id"),
                    plan.get("adopted_at"),
                    plan.get("created_at", ""),
                    plan.get("updated_at", ""),
                    payload,
                ),
            )
            connection.execute("DELETE FROM plan_tasks WHERE plan_id = ?", (plan["plan_id"],))
            for task in plan.get("tasks", []):
                connection.execute(
                    """
                    INSERT INTO plan_tasks(
                        plan_id, task_id, topic, file, difficulty,
                        estimated_minutes, priority, reviewed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan["plan_id"],
                        task["task_id"],
                        task.get("topic", ""),
                        task.get("file", ""),
                        task.get("difficulty", ""),
                        int(task.get("estimated_minutes", 0)),
                        task.get("priority", ""),
                        1 if task.get("reviewed") else 0,
                    ),
                )

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM plans WHERE plan_id = ?", (plan_id,)
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def save_progress_event(self, event: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO progress_events(
                    event_id, plan_id, task_id, event, occurred_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event["event_id"],
                    event["plan_id"],
                    event["task_id"],
                    event["event"],
                    event["occurred_at"],
                ),
            )

    def list_progress_events(self, plan_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, plan_id, task_id, event, occurred_at
                FROM progress_events WHERE plan_id = ? ORDER BY occurred_at
                """,
                (plan_id,),
            ).fetchall()
        return [
            {
                "event_id": row[0],
                "plan_id": row[1],
                "task_id": row[2],
                "event": row[3],
                "occurred_at": row[4],
            }
            for row in rows
        ]

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            owned = self._memory is None
            connection = self._memory or sqlite3.connect(
                str(self.db_path),
                timeout=30,
                check_same_thread=False,
            )
            try:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA busy_timeout=30000")
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                if owned:
                    connection.close()


class ReviewHistoryRepositoryAdapter:
    """Adapt SqliteLearningStore to the review-only repository methods."""

    def __init__(self, store: SqliteLearningStore) -> None:
        self._store = store

    def get(self, file_key: str) -> dict[str, Any] | None:
        return self._store.get_review(file_key)

    def save(self, file_key: str, entry: dict[str, Any]) -> dict[str, Any]:
        return self._store.save_review(file_key, entry)

    def all(self) -> dict[str, dict[str, Any]]:
        return self._store.all_reviews()

    def find_by_source_session(self, session_id: str) -> dict[str, Any] | None:
        return self._store.find_by_source_session(session_id)


def _review_unchanged(existing: dict[str, Any], incoming: dict[str, Any]) -> bool:
    keys = ("review_count", "last_reviewed", "next_review", "interval_days", "source_session_id")
    return all(existing.get(key) == incoming.get(key) for key in keys)
