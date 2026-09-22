"""M10 effect ledger: separate file, versioned schema, pending before the write.

`M10-CHECKPOINT` put runner state in its own SQLite file and `M10-EFFECT-LEDGER`
made outbox/reconcile mandatory as the price of that choice. The two properties
this file exists to pin are the ones a crash would otherwise expose:

- a row is persisted as `pending` **before** the domain write, so a crash cannot
  leave an applied effect with no ledger row;
- replaying an idempotency key returns the recorded effect instead of applying a
  second one, and the same key with different arguments is refused outright.
"""

from __future__ import annotations

import hashlib
import sqlite3

import pytest

from app.effect_ledger import (
    LEDGER_SCHEMA_FAMILY,
    LEDGER_SCHEMA_VERSION,
    EffectLedgerError,
    EffectLedgerStore,
)
from app.runner_authority import EffectState, RunnerAuthorityError

pytestmark = pytest.mark.m10

_ARG_DIGEST = "a" * 64


def _store(tmp_path) -> EffectLedgerStore:
    return EffectLedgerStore(tmp_path / "runner_state.sqlite3")


def _job(store: EffectLedgerStore, job_id: str = "job-1") -> None:
    store.create_job(job_id=job_id, scope_id="m10-autonomous-runner-v1", learner_id="learner-1")


def _begin(store: EffectLedgerStore, *, effect_id: str = "eff-1", key: str = "key-1",
           argument_digest: str = _ARG_DIGEST, tool_name: str = "log_review"):
    return store.begin_effect(effect_id=effect_id, job_id="job-1", tool_name=tool_name,
                              argument_digest=argument_digest, idempotency_key=key)


def test_the_ledger_lives_in_its_own_file_with_a_versioned_meta_row(tmp_path) -> None:
    store = _store(tmp_path)
    assert store.path.name == "runner_state.sqlite3"

    with sqlite3.connect(store.path) as connection:
        family, version = connection.execute(
            "SELECT schema_family, schema_version FROM runner_meta WHERE singleton = 1"
        ).fetchone()
    assert (family, version) == (LEDGER_SCHEMA_FAMILY, LEDGER_SCHEMA_VERSION)


def test_reopening_an_existing_ledger_is_idempotent(tmp_path) -> None:
    first = _store(tmp_path)
    _job(first)
    second = EffectLedgerStore(first.path)
    assert second.get_effect("eff-1") is None  # nothing written yet
    assert second.pending_effects() == ()


def test_an_unsupported_schema_version_fails_closed(tmp_path) -> None:
    store = _store(tmp_path)
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE runner_meta SET schema_version = 99 WHERE singleton = 1")
    with pytest.raises(EffectLedgerError) as caught:
        EffectLedgerStore(store.path)
    assert caught.value.code == "LEDGER_SCHEMA_UNSUPPORTED"


def test_a_job_is_created_once(tmp_path) -> None:
    store = _store(tmp_path)
    _job(store)
    with pytest.raises(EffectLedgerError) as caught:
        _job(store)
    assert caught.value.code == "JOB_DUPLICATE"


def test_an_effect_is_pending_before_any_domain_write(tmp_path) -> None:
    """The ordering that closes the "applied but unrecorded" crash window."""
    store = _store(tmp_path)
    _job(store)
    record = _begin(store)

    assert record.state is EffectState.PENDING
    assert [row.effect_id for row in store.pending_effects()] == ["eff-1"]
    # The pending row exists while nothing has been applied yet.
    assert store.events("eff-1") == ((None, "pending"),)


def test_replaying_a_key_returns_the_recorded_effect_instead_of_a_second_one(tmp_path) -> None:
    store = _store(tmp_path)
    _job(store)
    first = _begin(store)
    store.transition(effect_id=first.effect_id, target=EffectState.APPLIED,
                     result_digest="b" * 64)

    replay = _begin(store, effect_id="eff-2")  # a caller retrying after a crash
    assert replay.effect_id == "eff-1"
    assert replay.state is EffectState.APPLIED
    assert replay.result_digest == "b" * 64
    assert store.get_effect("eff-2") is None


def test_the_same_key_with_different_arguments_is_refused(tmp_path) -> None:
    store = _store(tmp_path)
    _job(store)
    _begin(store)
    with pytest.raises(EffectLedgerError) as caught:
        _begin(store, effect_id="eff-2", argument_digest="c" * 64)
    assert caught.value.code == "IDEMPOTENCY_CONFLICT"
    assert store.get_effect("eff-2") is None


def test_illegal_state_transitions_are_refused(tmp_path) -> None:
    store = _store(tmp_path)
    _job(store)
    _begin(store)
    store.transition(effect_id="eff-1", target=EffectState.APPLIED)

    with pytest.raises(RunnerAuthorityError) as caught:
        store.transition(effect_id="eff-1", target=EffectState.PENDING)
    assert caught.value.code == "EFFECT_TRANSITION_INVALID"

    # The refusal left the ledger unchanged and the history append-only.
    assert store.get_effect("eff-1").state is EffectState.APPLIED
    assert store.events("eff-1") == ((None, "pending"), ("pending", "applied"))


def test_an_unknown_effect_cannot_be_transitioned(tmp_path) -> None:
    store = _store(tmp_path)
    with pytest.raises(EffectLedgerError) as caught:
        store.transition(effect_id="missing", target=EffectState.APPLIED)
    assert caught.value.code == "EFFECT_UNKNOWN"


def test_checkpoints_are_monotonic_per_job(tmp_path) -> None:
    store = _store(tmp_path)
    _job(store)
    store.record_checkpoint(checkpoint_id="cp-1", job_id="job-1", seq=1, stage="propose",
                            input_digest="d" * 64, state_digest="e" * 64)
    store.record_checkpoint(checkpoint_id="cp-2", job_id="job-1", seq=2, stage="apply",
                            input_digest="d" * 64, state_digest="f" * 64)

    assert store.latest_checkpoint("job-1") == (2, "apply", "d" * 64, "f" * 64)
    with pytest.raises(EffectLedgerError) as caught:
        store.record_checkpoint(checkpoint_id="cp-3", job_id="job-1", seq=2, stage="apply",
                                input_digest="d" * 64, state_digest="f" * 64)
    assert caught.value.code == "CHECKPOINT_CONFLICT"


def test_the_ledger_schema_has_no_column_for_argument_or_result_values(tmp_path) -> None:
    """Privacy is structural: there is nowhere to put user content."""
    store = _store(tmp_path)
    with sqlite3.connect(store.path) as connection:
        columns = {
            row[1]
            for table in ("effect_ledger", "effect_events", "job_checkpoints")
            for row in connection.execute(f"PRAGMA table_info({table})")
        }
    assert "argument_digest" in columns
    assert "result_digest" in columns
    assert columns.isdisjoint({"arguments", "result", "payload", "content", "file", "path"})


def test_using_the_ledger_leaves_the_learning_store_untouched(tmp_path) -> None:
    """The runner's own file must not be the domain store, and must not touch it."""
    learning_path = tmp_path / "learning_state.sqlite3"
    with sqlite3.connect(learning_path) as connection:
        connection.execute("CREATE TABLE study_sessions (session_id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO study_sessions VALUES ('s-1')")
    before = hashlib.sha256(learning_path.read_bytes()).hexdigest()

    store = _store(tmp_path)
    _job(store)
    _begin(store)
    store.transition(effect_id="eff-1", target=EffectState.APPLIED)

    assert store.path != learning_path
    assert hashlib.sha256(learning_path.read_bytes()).hexdigest() == before
