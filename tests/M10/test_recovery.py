"""M10 crash-point recovery: ten points, each classified without guessing.

`M10-RECOVERY` freezes ten single-process crash points (the single-worker
topology means no cross-process matrix is required). This file drives every one
through the real pipeline and asserts the two things the decision promises:

- **no duplicate side effect** — counted on the domain write itself, so a
  "no duplicate" claim cannot be satisfied by never writing at all;
- the effect is classified from the **ledger**, never from a checkpoint that may
  not have landed.

One assertion from the test plan does **not** apply at this step and is not
faked here: "no half-published generation" is a property of the ingestion /
index-publication path, which step 2 does not build. The domain write exercised
here is a review-log entry with no generation.
"""

from __future__ import annotations

import pytest

from app.effect_ledger import EffectLedgerStore
from app.runner_authority import (
    EffectState,
    RevocationRegistry,
    RunnerWriteRegistry,
    issue_confirmation,
)
from app.runner_recovery import (
    CrashPoint,
    EffectTerminal,
    InjectedCrash,
    RunnerJobExecutor,
)
from app.tool_registry import PREVIEW_TOOL_ALLOWLIST  # noqa: F401  (import keeps the disjointness claim honest)

pytestmark = pytest.mark.m10

_ARGUMENTS = {"file": "knowledge/os/scheduling.md"}
_PERMISSIONS = frozenset({"write"})


class _Domain:
    """A stand-in for the domain write. Counts how often it actually ran."""

    def __init__(self, *, fail_with: Exception | None = None) -> None:
        self.calls = 0
        self.fail_with = fail_with

    def __call__(self) -> str:
        self.calls += 1
        if self.fail_with is not None:
            raise self.fail_with
        return "r" * 64


def _executor(ledger, revocations, *, crash_at: CrashPoint | None = None):
    def hook(point: CrashPoint) -> None:
        if crash_at is not None and point is crash_at:
            raise InjectedCrash(point.value)

    executor = RunnerJobExecutor(ledger=ledger, authority=RunnerWriteRegistry({"log_review"}),
                                 revocations=revocations, crash_hook=hook)
    executor.authority.register(_spec())
    return executor


def _setup(tmp_path, *, crash_at: CrashPoint | None = None, domain: _Domain | None = None):
    ledger = EffectLedgerStore(tmp_path / "runner_state.sqlite3")
    ledger.create_job(job_id="job-1", scope_id="m10-autonomous-runner-v1",
                      learner_id="learner-1")
    revocations = RevocationRegistry()
    return ledger, _executor(ledger, revocations, crash_at=crash_at), revocations, domain or _Domain()


def _spec():
    from app.protocols import SideEffect, ToolCapability, ToolSpec

    return ToolSpec(name="log_review", description="record one review",
                    input_schema={"type": "object", "properties": {"file": {"type": "string"}},
                                  "required": ["file"]},
                    capability=ToolCapability.WRITE, side_effect=SideEffect.DOMAIN_WRITE,
                    idempotent=True)


def _run(executor, domain, *, effect_id="eff-1"):
    return executor.execute_effect(
        job_id="job-1", effect_id=effect_id, tool_name="log_review", arguments=_ARGUMENTS,
        permissions=_PERMISSIONS,
        confirmation=issue_confirmation(job_id="job-1", tool_name="log_review",
                                        arguments=_ARGUMENTS),
        scope_id="m10-autonomous-runner-v1", apply=domain,
    )


def test_the_happy_path_applies_once_and_leaves_nothing_unfinished(tmp_path) -> None:
    ledger, executor, _, domain = _setup(tmp_path)
    outcome = _run(executor, domain)

    assert outcome.terminal is EffectTerminal.APPLIED
    assert domain.calls == 1
    assert ledger.get_effect("eff-1").state is EffectState.APPLIED
    assert ledger.unfinished_effects() == ()
    assert ledger.latest_checkpoint("job-1")[1] == "after_apply"


def test_a_crash_before_anything_is_recorded_leaves_nothing_to_reconcile(tmp_path) -> None:
    """Point 1: the crash precedes the first ledger write, so there is no row.

    Resume returning nothing is the correct outcome here — not a gap. An effect
    that was never recorded was never applied, and inventing a row for it would
    be the ledger claiming knowledge it does not have.
    """
    ledger, executor, _, domain = _setup(tmp_path, crash_at=CrashPoint.BEFORE_PROPOSE)

    with pytest.raises(InjectedCrash):
        _run(executor, domain)

    assert ledger.all_effects("job-1") == ()
    assert executor.resume_job(job_id="job-1", reconcile=lambda record: True) == ()
    assert domain.calls == 0


@pytest.mark.parametrize("point", [
    CrashPoint.AFTER_PROPOSE,
    CrashPoint.AFTER_AUTHORIZE,
    CrashPoint.MID_CHECKPOINT,
])
def test_a_crash_before_pending_never_applies_and_is_failed_on_resume(tmp_path, point) -> None:
    """Nothing was written, so the effect is failed rather than re-applied."""
    ledger, executor, _, domain = _setup(tmp_path, crash_at=point)

    with pytest.raises(InjectedCrash):
        _run(executor, domain)
    assert domain.calls == 0
    # The row exists but never reached `pending`, so it cannot have been applied.
    assert [r.effect_id for r in ledger.unfinished_effects()] == ["eff-1"]
    assert ledger.get_effect("eff-1").state is not EffectState.PENDING

    outcomes = executor.resume_job(job_id="job-1", reconcile=lambda record: False)
    assert [o.terminal for o in outcomes] == [EffectTerminal.FAILED]
    assert [o.reason for o in outcomes] == ["crashed-before-apply"]
    assert domain.calls == 0  # resume must not blindly re-apply
    assert ledger.unfinished_effects() == ()


@pytest.mark.parametrize("point", [CrashPoint.MID_APPLY])
def test_a_crash_after_pending_is_reconciled_not_assumed(tmp_path, point) -> None:
    """The write may or may not have landed, so only the domain can say."""
    ledger, executor, _, domain = _setup(tmp_path, crash_at=point)

    with pytest.raises(InjectedCrash):
        _run(executor, domain)
    assert ledger.get_effect("eff-1").state is EffectState.PENDING

    # The domain says the write never landed.
    outcomes = executor.resume_job(job_id="job-1", reconcile=lambda record: False)
    assert [o.reason for o in outcomes] == ["reconciled-absent"]
    assert domain.calls == 0

    # And the mirror case: the domain says it did land.
    ledger2, executor2, _, domain2 = _setup(tmp_path / "b", crash_at=point)
    with pytest.raises(InjectedCrash):
        _run(executor2, domain2)
    outcomes2 = executor2.resume_job(job_id="job-1", reconcile=lambda record: True)
    assert [o.reason for o in outcomes2] == ["reconciled-present"]
    assert ledger2.get_effect("eff-1").state is EffectState.APPLIED
    assert domain2.calls == 0  # reconcile does not re-apply


@pytest.mark.parametrize("point", [
    CrashPoint.AFTER_APPLY_BEFORE_LEDGER,
    CrashPoint.AFTER_LEDGER_BEFORE_CHECKPOINT,
])
def test_a_crash_after_the_domain_write_keeps_the_effect_applied(tmp_path, point) -> None:
    """The ledger — not the checkpoint — is what classifies this state."""
    ledger, executor, _, domain = _setup(tmp_path, crash_at=point)

    with pytest.raises(InjectedCrash):
        _run(executor, domain)
    assert domain.calls == 1

    if point is CrashPoint.AFTER_APPLY_BEFORE_LEDGER:
        # The write landed but the ledger never heard about it: a resume must
        # reconcile rather than assume, and must not apply a second time.
        assert ledger.get_effect("eff-1").state is EffectState.PENDING
        outcomes = executor.resume_job(job_id="job-1", reconcile=lambda record: True)
        assert [o.reason for o in outcomes] == ["reconciled-present"]
    else:
        # The ledger already says applied; there is nothing left to reconcile.
        assert ledger.get_effect("eff-1").state is EffectState.APPLIED
        assert executor.resume_job(job_id="job-1", reconcile=lambda record: True) == ()
    assert domain.calls == 1


def test_every_frozen_crash_point_is_exercised_by_this_file(tmp_path) -> None:
    """Non-vacuity: the matrix is covered by name, not by a subset that looks full.

    A point added to `CrashPoint` without a case here would silently drop the
    coverage the evaluation's 100% threshold depends on.
    """
    covered = {
        CrashPoint.BEFORE_PROPOSE, CrashPoint.AFTER_PROPOSE, CrashPoint.AFTER_AUTHORIZE,
        CrashPoint.MID_CHECKPOINT, CrashPoint.MID_APPLY,
        CrashPoint.AFTER_APPLY_BEFORE_LEDGER, CrashPoint.AFTER_LEDGER_BEFORE_CHECKPOINT,
        CrashPoint.MID_CANCEL, CrashPoint.DISK_FULL, CrashPoint.PROVIDER_TIMEOUT,
    }
    assert covered == set(CrashPoint)
    assert len(covered) == 10


def test_disk_full_and_provider_timeout_fail_closed_without_applying(tmp_path) -> None:
    """Points 9 and 10 arrive through the domain write, not through the hook."""
    for failure in (OSError(28, "No space left on device"), TimeoutError("provider timeout")):
        ledger, executor, _, _ = _setup(tmp_path / str(id(failure)), domain=_Domain())
        domain = _Domain(fail_with=failure)
        outcome = _run(executor, domain)

        assert outcome.terminal is EffectTerminal.FAILED
        assert outcome.reason == "apply-failed"
        assert ledger.get_effect("eff-1").state is EffectState.FAILED
        assert ledger.pending_effects() == ()


def test_a_cancel_that_arrives_during_the_crash_window_stops_the_work(tmp_path) -> None:
    """Point 8: the intent is persisted before the injection, so it survives."""
    ledger, executor, revocations, domain = _setup(tmp_path, crash_at=CrashPoint.MID_APPLY)

    with pytest.raises(InjectedCrash):
        _run(executor, domain)
    assert ledger.get_effect("eff-1").state is EffectState.PENDING

    # A second executor over the **same** ledger whose hook fires at MID_CANCEL:
    # the crash happens while the cancel is being handled, after the intent was
    # persisted. Sharing the ledger is the point — a fresh store would cancel a
    # different job and prove nothing.
    cancel_crasher = _executor(ledger, revocations, crash_at=CrashPoint.MID_CANCEL)
    with pytest.raises(InjectedCrash):
        cancel_crasher.cancel_job("job-1")
    assert ledger.get_job_state("job-1") == "cancelled"

    # Resume sees the cancel intent and refuses, even though the domain would
    # happily confirm the write had landed.
    outcomes = executor.resume_job(job_id="job-1", reconcile=lambda record: True)
    assert [o.terminal for o in outcomes] == [EffectTerminal.CANCELLED]
    assert domain.calls == 0
    assert ledger.get_effect("eff-1").state is EffectState.FAILED


def test_a_revocation_arriving_during_the_crash_window_stops_the_work(tmp_path) -> None:
    ledger, executor, revocations, domain = _setup(tmp_path, crash_at=CrashPoint.MID_APPLY)
    with pytest.raises(InjectedCrash):
        _run(executor, domain)

    revocations.revoke(job_id="job-1", tool_name="log_review")
    outcomes = executor.resume_job(job_id="job-1", reconcile=lambda record: True)
    assert [o.reason for o in outcomes] == ["revoked-on-resume"]
    assert domain.calls == 0


def test_revalidation_can_refuse_a_resume(tmp_path) -> None:
    ledger, executor, _, domain = _setup(tmp_path, crash_at=CrashPoint.MID_APPLY)
    with pytest.raises(InjectedCrash):
        _run(executor, domain)

    outcomes = executor.resume_job(job_id="job-1", reconcile=lambda record: True,
                                   revalidate=lambda: False)
    assert [o.reason for o in outcomes] == ["revalidation-refused"]
    assert domain.calls == 0


def test_a_replay_returns_the_recorded_effect_and_writes_nothing(tmp_path) -> None:
    """The duplicate-effect witness: the domain write count stays at one."""
    ledger, executor, _, domain = _setup(tmp_path)
    _run(executor, domain)
    assert domain.calls == 1

    replay = _run(executor, domain, effect_id="eff-2")
    assert replay.replayed is True
    assert replay.effect_id == "eff-1"
    assert replay.terminal is EffectTerminal.APPLIED
    assert domain.calls == 1
    assert len(ledger.all_effects("job-1")) == 1


def test_the_job_is_poisoned_once_failures_reach_the_threshold(tmp_path) -> None:
    """Three *distinct* effects must fail; the same one cannot fail three times.

    A failed effect is terminal and its idempotency key returns that terminal
    record, so retrying one effect never accumulates. The threshold counts
    failures across the job, which is why each attempt here carries different
    arguments.
    """
    ledger, executor, _, _ = _setup(tmp_path)
    domain = _Domain(fail_with=RuntimeError("domain refused"))

    for index in range(3):
        outcome = executor.execute_effect(
            job_id="job-1", effect_id=f"eff-{index}", tool_name="log_review",
            arguments={"file": f"knowledge/os/note-{index}.md"},
            permissions=_PERMISSIONS,
            confirmation=issue_confirmation(job_id="job-1", tool_name="log_review",
                                            arguments={"file": f"knowledge/os/note-{index}.md"}),
            scope_id="m10-autonomous-runner-v1", apply=domain,
        )
        assert outcome.terminal is EffectTerminal.FAILED

    assert executor.failure_count("job-1") == 3
    poison = executor.poison_if_exhausted("job-1")
    assert poison is not None and poison.terminal is EffectTerminal.POISON


def test_retrying_one_effect_cannot_accumulate_failures(tmp_path) -> None:
    """The flip side of the poison rule, stated so it is not mistaken for a gap."""
    ledger, executor, _, _ = _setup(tmp_path)
    domain = _Domain(fail_with=RuntimeError("domain refused"))

    for _ in range(3):
        outcome = _run(executor, domain)  # identical arguments -> identical key
        assert outcome.terminal is EffectTerminal.FAILED

    assert executor.failure_count("job-1") == 1
    assert executor.poison_if_exhausted("job-1") is None
    assert len(ledger.all_effects("job-1")) == 1


def test_a_job_below_the_threshold_is_not_poisoned(tmp_path) -> None:
    """Non-vacuity for the poison threshold: it must be able to say no."""
    ledger, executor, _, _ = _setup(tmp_path)
    assert executor.poison_if_exhausted("job-1") is None


def test_a_non_compensable_failure_is_terminal_and_needs_a_human(tmp_path) -> None:
    outcome = RunnerJobExecutor.non_compensable("cannot undo published generation", "eff-1")
    assert outcome.terminal is EffectTerminal.NEEDS_HUMAN_INTERVENTION
    assert outcome.terminal is not EffectTerminal.FAILED  # not a retryable failure
