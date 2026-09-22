"""M10 reconcile, compensation and human intervention.

Three rules carry the weight here, and each has a non-vacuity partner:

- reconcile is **idempotent** — the second pass finds nothing, because the first
  left every examined effect terminal;
- **inconclusive is not success** — an unanswerable probe defers, and a bounded
  number of deferrals escalates instead of looping;
- **escalation is terminal and manual** — a later sweep never resolves it, and
  nothing retries it automatically.

Also covered: the v1 -> v2 ledger migration, since step 5 is the first change
that actually needs one.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.effect_ledger import (
    LEDGER_SCHEMA_VERSION,
    EffectLedgerError,
    EffectLedgerStore,
)
from app.effect_reconcile import (
    OUTCOME_APPLIED,
    OUTCOME_DEFERRED,
    OUTCOME_ESCALATED,
    OUTCOME_FAILED,
    ReconcileVerdict,
    Reconciler,
)
from app.runner_authority import EffectState

pytestmark = pytest.mark.m10


def _store(tmp_path) -> EffectLedgerStore:
    store = EffectLedgerStore(tmp_path / "runner_state.sqlite3")
    store.create_job(job_id="job-1", scope_id="m10-autonomous-runner-v1",
                     learner_id="learner-1")
    return store


def _pending(store: EffectLedgerStore, effect_id: str, *, key: str = "key-1") -> None:
    store.begin_effect(effect_id=effect_id, job_id="job-1", tool_name="log_review",
                       argument_digest="a" * 64, idempotency_key=key)
    store.authorize_effect(effect_id)
    store.mark_pending(effect_id)


def _verdict(value: ReconcileVerdict):
    return lambda _record: value


def test_a_present_effect_converges_to_applied(tmp_path) -> None:
    store = _store(tmp_path)
    _pending(store, "eff-1")
    report = Reconciler(store).sweep(probe=_verdict(ReconcileVerdict.PRESENT))

    assert (report.examined, report.applied, report.changed) == (1, 1, 1)
    assert store.get_effect("eff-1").state is EffectState.APPLIED
    assert store.reconcile_attempts("eff-1") == (OUTCOME_APPLIED,)


def test_an_absent_effect_converges_to_failed(tmp_path) -> None:
    store = _store(tmp_path)
    _pending(store, "eff-1")
    report = Reconciler(store).sweep(probe=_verdict(ReconcileVerdict.ABSENT))

    assert (report.examined, report.failed) == (1, 1)
    assert store.get_effect("eff-1").state is EffectState.FAILED
    assert store.reconcile_attempts("eff-1") == (OUTCOME_FAILED,)


def test_a_second_sweep_changes_nothing(tmp_path) -> None:
    """Idempotence, stated as the observable property: nothing left to examine."""
    store = _store(tmp_path)
    _pending(store, "eff-1")
    reconciler = Reconciler(store)

    first = reconciler.sweep(probe=_verdict(ReconcileVerdict.PRESENT))
    second = reconciler.sweep(probe=_verdict(ReconcileVerdict.PRESENT))

    assert first.examined == 1
    assert second.examined == 0
    assert second.changed == 0
    # And the attempt log did not grow either.
    assert store.reconcile_attempts("eff-1") == (OUTCOME_APPLIED,)


def test_an_unanswerable_probe_defers_rather_than_guessing(tmp_path) -> None:
    """Inconclusive is neither applied nor failed — it stays pending."""
    store = _store(tmp_path)
    _pending(store, "eff-1")
    report = Reconciler(store, max_deferrals=3).sweep(
        probe=_verdict(ReconcileVerdict.UNKNOWN))

    assert (report.deferred, report.applied, report.failed) == (1, 0, 0)
    assert store.get_effect("eff-1").state is EffectState.PENDING
    assert store.reconcile_attempts("eff-1") == (OUTCOME_DEFERRED,)


def test_repeated_deferrals_escalate_instead_of_looping(tmp_path) -> None:
    store = _store(tmp_path)
    _pending(store, "eff-1")
    reconciler = Reconciler(store, max_deferrals=3)
    probe = _verdict(ReconcileVerdict.UNKNOWN)

    reports = [reconciler.sweep(probe=probe) for _ in range(3)]
    assert [r.deferred for r in reports] == [1, 1, 0]
    assert [r.escalated for r in reports] == [0, 0, 1]
    assert store.reconcile_attempts("eff-1") == (
        OUTCOME_DEFERRED, OUTCOME_DEFERRED, OUTCOME_ESCALATED)


def test_an_escalated_effect_is_never_resolved_by_a_later_sweep(tmp_path) -> None:
    """The point of escalation: it must not be quietly converged afterwards."""
    store = _store(tmp_path)
    _pending(store, "eff-1")
    reconciler = Reconciler(store, max_deferrals=1)
    reconciler.sweep(probe=_verdict(ReconcileVerdict.UNKNOWN))

    # A later sweep with a probe that now knows the answer must not apply it.
    report = reconciler.sweep(probe=_verdict(ReconcileVerdict.PRESENT))
    assert report.examined == 0
    assert store.get_effect("eff-1").state is EffectState.PENDING

    queue = reconciler.open_interventions()
    assert [item.effect_id for item in queue] == ["eff-1"]
    assert queue[0].tool_name == "log_review"
    assert queue[0].reason == OUTCOME_ESCALATED


def test_a_human_decision_is_the_only_way_an_escalation_moves(tmp_path) -> None:
    store = _store(tmp_path)
    _pending(store, "eff-1")
    reconciler = Reconciler(store, max_deferrals=1)
    reconciler.sweep(probe=_verdict(ReconcileVerdict.UNKNOWN))

    record = reconciler.resolve_intervention("eff-1", verdict=ReconcileVerdict.PRESENT)
    assert record.state is EffectState.APPLIED
    assert store.reconcile_attempts("eff-1") == (OUTCOME_ESCALATED, "resolved-present")
    assert reconciler.open_interventions() == ()

    with pytest.raises(ValueError):
        reconciler.resolve_intervention("eff-1", verdict=ReconcileVerdict.UNKNOWN)


def test_compensation_moves_an_applied_effect_to_compensated(tmp_path) -> None:
    store = _store(tmp_path)
    _pending(store, "eff-1")
    store.mark_applied("eff-1", "b" * 64)

    record = Reconciler(store).compensate("eff-1")
    assert record.state is EffectState.COMPENSATED


def test_compensating_a_never_applied_effect_does_not_claim_an_undo(tmp_path) -> None:
    """A failed effect was never applied; calling it compensated would be a lie."""
    store = _store(tmp_path)
    _pending(store, "eff-1")
    store.mark_failed("eff-1")

    record = Reconciler(store).compensate("eff-1")
    assert record.state is EffectState.FAILED
    assert store.events("eff-1")[-1] == ("pending", "failed")


def test_compensating_an_unknown_effect_is_refused(tmp_path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        Reconciler(store).compensate("missing")


def test_a_v1_ledger_migrates_to_v2_and_keeps_its_data(tmp_path) -> None:
    """Step 5 is the first change that needs a migration, so it is exercised."""
    path = tmp_path / "runner_state.sqlite3"
    store = _store(tmp_path)
    _pending(store, "eff-1")
    store.mark_applied("eff-1", "b" * 64)

    # Rewind to v1: drop the v2 table and set the version back.
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE reconcile_attempts")
        connection.execute("UPDATE runner_meta SET schema_version = 1 WHERE singleton = 1")

    upgraded = EffectLedgerStore(path)
    assert upgraded.get_effect("eff-1").state is EffectState.APPLIED  # data survived
    upgraded.record_reconcile_attempt(effect_id="eff-1", outcome=OUTCOME_APPLIED)
    with sqlite3.connect(path) as connection:
        version = connection.execute(
            "SELECT schema_version FROM runner_meta WHERE singleton = 1").fetchone()[0]
    assert version == LEDGER_SCHEMA_VERSION


def test_a_future_schema_version_is_still_refused(tmp_path) -> None:
    """Non-vacuity for the migration: it must not accept anything it does not know."""
    path = tmp_path / "runner_state.sqlite3"
    _store(tmp_path)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE runner_meta SET schema_version = 99 WHERE singleton = 1")

    with pytest.raises(EffectLedgerError) as caught:
        EffectLedgerStore(path)
    assert caught.value.code == "LEDGER_SCHEMA_UNSUPPORTED"
