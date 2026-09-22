"""Runner-owned effect ledger in its own SQLite file.

`M10-CHECKPOINT` decided the runner's job/checkpoint/ledger state lives in a
**separate** database, so the learning-state store (`learning_store.py`) is never
touched. The cost of that decision is explicit and is paid here: there is no
cross-file transaction, so `M10-EFFECT-LEDGER` makes outbox + reconcile
mandatory rather than optional, and a row must be persisted as `pending`
**before** the domain write so a crash cannot leave an applied effect with no
ledger row.

This module owns no domain state. It records what was attempted and what
happened; the domain service still performs the write and may still refuse.

Nothing in production constructs this store yet — M10 is `IN_PROGRESS` at step 1
of its plan, which freezes the schema and implements the rejection path first.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .runner_authority import EffectState, RunnerAuthorityError, assert_transition_allowed

# Meta-table versioning follows `source_registry.py`: a family plus a numeric
# version, refused on mismatch. The `ALTER TABLE` migration path in
# `source_delete.py` deliberately does not apply — this database is new, so there
# is no older one to migrate.
LEDGER_SCHEMA_FAMILY = "sa.runner.effect-ledger.v1"
LEDGER_SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE runner_meta (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    schema_family TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE runner_jobs (
    job_id TEXT PRIMARY KEY,
    scope_id TEXT NOT NULL,
    learner_id TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE effect_ledger (
    effect_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES runner_jobs(job_id),
    tool_name TEXT NOT NULL,
    argument_digest TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL,
    result_digest TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE effect_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    effect_id TEXT NOT NULL REFERENCES effect_ledger(effect_id),
    from_state TEXT,
    to_state TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE job_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES runner_jobs(job_id),
    seq INTEGER NOT NULL,
    stage TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    state_digest TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(job_id, seq)
);
"""


class EffectLedgerError(RunnerAuthorityError):
    """A ledger operation was refused."""


@dataclass(frozen=True, slots=True)
class EffectRecord:
    """One ledger row. Carries digests only — never argument or result values."""

    effect_id: str
    job_id: str
    tool_name: str
    argument_digest: str
    idempotency_key: str
    state: EffectState
    result_digest: str | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EffectLedgerStore:
    """Append-only effect ledger over one dedicated SQLite file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            self._initialize(connection)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @staticmethod
    def _initialize(connection: sqlite3.Connection) -> None:
        existing = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='runner_meta'"
        ).fetchone()
        if existing is None:
            now = _now()
            connection.executescript(_SCHEMA)
            connection.execute(
                "INSERT INTO runner_meta (singleton, schema_family, schema_version,"
                " created_at, updated_at) VALUES (1, ?, ?, ?, ?)",
                (LEDGER_SCHEMA_FAMILY, LEDGER_SCHEMA_VERSION, now, now),
            )
            return
        row = connection.execute(
            "SELECT schema_family, schema_version FROM runner_meta WHERE singleton = 1"
        ).fetchone()
        if row is None or row["schema_family"] != LEDGER_SCHEMA_FAMILY \
                or row["schema_version"] != LEDGER_SCHEMA_VERSION:
            # Fail closed rather than guess at an unknown layout.
            raise EffectLedgerError(
                "LEDGER_SCHEMA_UNSUPPORTED",
                "the runner ledger schema is not the supported version.",
            )

    # -- jobs ---------------------------------------------------------------

    def create_job(self, *, job_id: str, scope_id: str, learner_id: str) -> None:
        now = _now()
        with self._lock, self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO runner_jobs (job_id, scope_id, learner_id, state,"
                    " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (job_id, scope_id, learner_id, "created", now, now),
                )
            except sqlite3.IntegrityError as exc:
                raise EffectLedgerError("JOB_DUPLICATE", "the job already exists.") from exc

    # -- effects ------------------------------------------------------------

    def begin_effect(self, *, effect_id: str, job_id: str, tool_name: str,
                     argument_digest: str, idempotency_key: str) -> EffectRecord:
        """Persist `pending` **before** the domain write, or return the replay.

        Returns the existing record when the idempotency key was already used, so
        the caller can see the effect is already accounted for instead of
        applying it twice.
        """
        with self._lock, self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM effect_ledger WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["argument_digest"] != argument_digest \
                        or existing["tool_name"] != tool_name:
                    # Same key, different arguments: refuse rather than reuse.
                    raise EffectLedgerError(
                        "IDEMPOTENCY_CONFLICT",
                        "the idempotency key was used with different arguments.",
                    )
                return self._record_from_row(existing)

            now = _now()
            try:
                connection.execute(
                    "INSERT INTO effect_ledger (effect_id, job_id, tool_name,"
                    " argument_digest, idempotency_key, state, result_digest,"
                    " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)",
                    (effect_id, job_id, tool_name, argument_digest, idempotency_key,
                     EffectState.PENDING.value, now, now),
                )
            except sqlite3.IntegrityError as exc:
                raise EffectLedgerError(
                    "EFFECT_DUPLICATE", "the effect already exists."
                ) from exc
            self._append_event(connection, effect_id, None, EffectState.PENDING)
            row = connection.execute(
                "SELECT * FROM effect_ledger WHERE effect_id = ?", (effect_id,)
            ).fetchone()
            return self._record_from_row(row)

    def transition(self, *, effect_id: str, target: EffectState,
                   result_digest: str | None = None) -> EffectRecord:
        """Move one effect to `target`, refusing illegal steps."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM effect_ledger WHERE effect_id = ?", (effect_id,)
            ).fetchone()
            if row is None:
                raise EffectLedgerError("EFFECT_UNKNOWN", "the effect does not exist.")
            current = EffectState(row["state"])
            assert_transition_allowed(current, target)
            connection.execute(
                "UPDATE effect_ledger SET state = ?, result_digest = COALESCE(?, result_digest),"
                " updated_at = ? WHERE effect_id = ?",
                (target.value, result_digest, _now(), effect_id),
            )
            self._append_event(connection, effect_id, current, target)
            updated = connection.execute(
                "SELECT * FROM effect_ledger WHERE effect_id = ?", (effect_id,)
            ).fetchone()
            return self._record_from_row(updated)

    def get_effect(self, effect_id: str) -> EffectRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM effect_ledger WHERE effect_id = ?", (effect_id,)
            ).fetchone()
        return self._record_from_row(row) if row else None

    def pending_effects(self) -> tuple[EffectRecord, ...]:
        """Effects awaiting reconcile. Outbox input, not an optional nicety."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM effect_ledger WHERE state = ? ORDER BY created_at, effect_id",
                (EffectState.PENDING.value,),
            ).fetchall()
        return tuple(self._record_from_row(row) for row in rows)

    def events(self, effect_id: str) -> tuple[tuple[str | None, str], ...]:
        """The append-only transition history for one effect."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT from_state, to_state FROM effect_events WHERE effect_id = ?"
                " ORDER BY event_id", (effect_id,),
            ).fetchall()
        return tuple((row["from_state"], row["to_state"]) for row in rows)

    # -- checkpoints --------------------------------------------------------

    def record_checkpoint(self, *, checkpoint_id: str, job_id: str, seq: int, stage: str,
                          input_digest: str, state_digest: str) -> None:
        """One checkpoint per effect boundary; `seq` is monotonic per job."""
        with self._lock, self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO job_checkpoints (checkpoint_id, job_id, seq, stage,"
                    " input_digest, state_digest, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (checkpoint_id, job_id, seq, stage, input_digest, state_digest, _now()),
                )
            except sqlite3.IntegrityError as exc:
                raise EffectLedgerError(
                    "CHECKPOINT_CONFLICT", "the checkpoint sequence is not unique."
                ) from exc

    def latest_checkpoint(self, job_id: str) -> tuple[int, str, str, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT seq, stage, input_digest, state_digest FROM job_checkpoints"
                " WHERE job_id = ? ORDER BY seq DESC LIMIT 1", (job_id,),
            ).fetchone()
        if row is None:
            return None
        return (row["seq"], row["stage"], row["input_digest"], row["state_digest"])

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _append_event(connection: sqlite3.Connection, effect_id: str,
                      from_state: EffectState | None, to_state: EffectState) -> None:
        connection.execute(
            "INSERT INTO effect_events (effect_id, from_state, to_state, recorded_at)"
            " VALUES (?, ?, ?, ?)",
            (effect_id, from_state.value if from_state else None, to_state.value, _now()),
        )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> EffectRecord:
        return EffectRecord(
            effect_id=row["effect_id"],
            job_id=row["job_id"],
            tool_name=row["tool_name"],
            argument_digest=row["argument_digest"],
            idempotency_key=row["idempotency_key"],
            state=EffectState(row["state"]),
            result_digest=row["result_digest"],
        )


__all__ = [
    "EffectLedgerError",
    "EffectLedgerStore",
    "EffectRecord",
    "LEDGER_SCHEMA_FAMILY",
    "LEDGER_SCHEMA_VERSION",
]
