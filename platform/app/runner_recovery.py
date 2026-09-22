"""Crash-point recovery for one controlled runner effect (M10 plan §5 step 2).

The pipeline is the whole point: an effect goes `proposed` -> `authorized` ->
`pending` -> `applied`, with a checkpoint at each boundary, and the row reaches
`pending` **before** the domain write. A crash at any boundary therefore leaves a
state a resume can classify without guessing:

- `proposed` / `authorized`: the domain write had not started, so nothing was
  applied. The effect is failed, never re-applied blindly.
- `pending`: the write may or may not have landed, so a resume **reconciles**
  against the domain rather than assuming either way.
- `applied`: done.

`resume_job` revalidates authorization before touching anything, so a revocation
that arrived during the crash window still stops the work.

Nothing here is wired into production: no route, no switch, no worker. The
production write allowlist is still empty, so this machinery has no approved tool
to drive yet.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .effect_ledger import EffectLedgerStore, EffectRecord
from .runner_authority import (
    Confirmation,
    EffectState,
    RevocationRegistry,
    RunnerAuthorityError,
    RunnerWriteRegistry,
    argument_digest,
    idempotency_key,
)

DEFAULT_MAX_ATTEMPTS = 3

JOB_RUNNING = "running"
JOB_CANCELLED = "cancelled"


class CrashPoint(StrEnum):
    """The ten points frozen by `M10-RECOVERY`, single-process scope."""

    BEFORE_PROPOSE = "before_propose"
    AFTER_PROPOSE = "after_propose"
    AFTER_AUTHORIZE = "after_authorize"
    MID_APPLY = "mid_apply"
    AFTER_APPLY_BEFORE_LEDGER = "after_apply_before_ledger"
    AFTER_LEDGER_BEFORE_CHECKPOINT = "after_ledger_before_checkpoint"
    MID_CHECKPOINT = "mid_checkpoint"
    MID_CANCEL = "mid_cancel"
    DISK_FULL = "disk_full"
    PROVIDER_TIMEOUT = "provider_timeout"


class InjectedCrash(RuntimeError):
    """A fault injected at a named crash point. Test-only; never raised in production."""


class EffectTerminal(StrEnum):
    """How an effect ended. `NEEDS_HUMAN_INTERVENTION` is not retryable."""

    APPLIED = "applied"
    FAILED = "failed"
    COMPENSATED = "compensated"
    CANCELLED = "cancelled"
    POISON = "poison"
    NEEDS_HUMAN_INTERVENTION = "needs_human_intervention"


@dataclass(frozen=True, slots=True)
class EffectOutcome:
    """One effect's result. `applied_count` is the duplicate-effect witness."""

    terminal: EffectTerminal
    reason: str
    effect_id: str | None = None
    replayed: bool = False
    applied_count: int = 0


def _no_crash(_point: CrashPoint) -> None:
    return None


class RunnerJobExecutor:
    """Runs one effect through the pipeline and recovers it after a crash."""

    def __init__(self, *, ledger: EffectLedgerStore, authority: RunnerWriteRegistry,
                 revocations: RevocationRegistry | None = None,
                 max_attempts: int = DEFAULT_MAX_ATTEMPTS,
                 crash_hook: Callable[[CrashPoint], None] = _no_crash) -> None:
        self._ledger = ledger
        self._authority = authority
        self._revocations = revocations or RevocationRegistry()
        self._max_attempts = max_attempts
        self._crash = crash_hook
        self._applied_count = 0

    @property
    def authority(self) -> RunnerWriteRegistry:
        """The write registry this executor drives. Tools are registered on it."""
        return self._authority

    @property
    def applied_count(self) -> int:
        """How many times the domain write actually ran. Duplicates show up here."""
        return self._applied_count

    def execute_effect(self, *, job_id: str, effect_id: str, tool_name: str,
                       arguments: Mapping[str, Any], permissions: frozenset[str],
                       confirmation: Confirmation | None, scope_id: str,
                       apply: Callable[[], str]) -> EffectOutcome:
        """Propose, authorize, checkpoint, apply. Raises `InjectedCrash` on injection."""
        self._crash(CrashPoint.BEFORE_PROPOSE)

        key = idempotency_key(job_id=job_id, tool_name=tool_name,
                              arguments=arguments, scope_id=scope_id)
        # Recognise the replay by key **before** touching the state machine.
        # Comparing effect ids instead would let a caller that reuses its own
        # effect id walk an already-terminal effect and hit an illegal transition.
        existing = self._ledger.find_by_idempotency_key(key)
        if existing is not None:
            return EffectOutcome(
                terminal=self._terminal_for(existing),
                reason="idempotent-replay",
                effect_id=existing.effect_id,
                replayed=True,
            )

        record = self._ledger.begin_effect(
            effect_id=effect_id, job_id=job_id, tool_name=tool_name,
            argument_digest=argument_digest(arguments), idempotency_key=key,
        )
        self._crash(CrashPoint.AFTER_PROPOSE)

        try:
            self._authority.authorize(name=tool_name, job_id=job_id, arguments=arguments,
                                      permissions=permissions, confirmation=confirmation)
        except RunnerAuthorityError as exc:
            self._ledger.mark_failed(effect_id)
            return EffectOutcome(terminal=EffectTerminal.FAILED, reason=exc.code,
                                 effect_id=effect_id)

        self._ledger.authorize_effect(effect_id)
        self._crash(CrashPoint.AFTER_AUTHORIZE)

        self._ledger.record_checkpoint(checkpoint_id=f"{effect_id}:before_apply", job_id=job_id,
                                       seq=self._ledger.next_checkpoint_seq(job_id),
                                       stage="before_apply",
                                       input_digest=record.argument_digest,
                                       state_digest=EffectState.AUTHORIZED.value)
        # Died while writing the checkpoint: the checkpoint landed but the ledger
        # is still `authorized`. A resume classifies from the **ledger**, so this
        # state is distinguishable from every other point rather than a repeat of
        # the one above it.
        self._crash(CrashPoint.MID_CHECKPOINT)
        # The row must be `pending` before the domain write; this ordering is the
        # crash window the ledger decision exists to close.
        self._ledger.mark_pending(effect_id)
        self._crash(CrashPoint.MID_APPLY)

        try:
            result_digest = apply()
        except Exception as exc:  # noqa: BLE001 - the domain write refused or died
            self._ledger.mark_failed(effect_id)
            return EffectOutcome(terminal=EffectTerminal.FAILED, reason="apply-failed",
                                 effect_id=effect_id)

        self._applied_count += 1
        self._crash(CrashPoint.AFTER_APPLY_BEFORE_LEDGER)
        self._ledger.mark_applied(effect_id, result_digest)
        self._crash(CrashPoint.AFTER_LEDGER_BEFORE_CHECKPOINT)
        self._ledger.record_checkpoint(checkpoint_id=f"{effect_id}:after_apply", job_id=job_id,
                                       seq=self._ledger.next_checkpoint_seq(job_id),
                                       stage="after_apply",
                                       input_digest=record.argument_digest,
                                       state_digest=EffectState.APPLIED.value)
        return EffectOutcome(terminal=EffectTerminal.APPLIED, reason="applied",
                             effect_id=effect_id, applied_count=self._applied_count)

    def resume_job(self, *, job_id: str,
                   reconcile: Callable[[EffectRecord], bool],
                   revalidate: Callable[[], bool] | None = None,
                   ) -> tuple[EffectOutcome, ...]:
        """Classify every unfinished effect after a crash. Never re-applies blindly.

        `reconcile` answers "is this effect present in the domain?" for effects
        that reached `pending`. `revalidate` answers "is this write still allowed
        at all?" — a revocation or a deleted source arriving during the crash
        window must stop the work rather than be applied on resume.
        """
        outcomes: list[EffectOutcome] = []
        if self._ledger.get_job_state(job_id) == JOB_CANCELLED:
            # A cancel that arrived during the crash window is a terminal intent:
            # nothing unfinished may be applied after it.
            for record in self._ledger.unfinished_effects():
                if record.job_id == job_id:
                    self._ledger.mark_failed(record.effect_id)
                    outcomes.append(EffectOutcome(terminal=EffectTerminal.CANCELLED,
                                                  reason="cancelled-on-resume",
                                                  effect_id=record.effect_id))
            return tuple(outcomes)
        for record in self._ledger.unfinished_effects():
            if record.job_id != job_id:
                continue
            if self._revocations.is_revoked(job_id=job_id, tool_name=record.tool_name):
                self._ledger.mark_failed(record.effect_id)
                outcomes.append(EffectOutcome(terminal=EffectTerminal.FAILED,
                                              reason="revoked-on-resume",
                                              effect_id=record.effect_id))
                continue
            if revalidate is not None and not revalidate():
                self._ledger.mark_failed(record.effect_id)
                outcomes.append(EffectOutcome(terminal=EffectTerminal.FAILED,
                                              reason="revalidation-refused",
                                              effect_id=record.effect_id))
                continue
            if record.state is not EffectState.PENDING:
                # proposed / authorized: the domain write had not started.
                self._ledger.mark_failed(record.effect_id)
                outcomes.append(EffectOutcome(terminal=EffectTerminal.FAILED,
                                              reason="crashed-before-apply",
                                              effect_id=record.effect_id))
                continue
            # pending: only the domain can say whether it landed.
            if reconcile(record):
                self._ledger.mark_applied(record.effect_id, record.result_digest or "")
                outcomes.append(EffectOutcome(terminal=EffectTerminal.APPLIED,
                                              reason="reconciled-present",
                                              effect_id=record.effect_id))
            else:
                self._ledger.mark_failed(record.effect_id)
                outcomes.append(EffectOutcome(terminal=EffectTerminal.FAILED,
                                              reason="reconciled-absent",
                                              effect_id=record.effect_id))
        return tuple(outcomes)

    def cancel_job(self, job_id: str) -> None:
        """Record the cancel intent, then crash at `MID_CANCEL` if injected.

        The intent is persisted **before** the injection point, so a crash while
        handling the cancel still leaves the intent behind — which is what makes
        `MID_CANCEL` recoverable rather than a lost cancellation.
        """
        self._ledger.set_job_state(job_id, JOB_CANCELLED)
        self._crash(CrashPoint.MID_CANCEL)

    def failure_count(self, job_id: str) -> int:
        """Failed effects for one job. Input to the poison threshold."""
        return sum(1 for record in self._ledger.all_effects(job_id)
                   if record.state is EffectState.FAILED)

    def poison_if_exhausted(self, job_id: str) -> EffectOutcome | None:
        """Stop the job once failures reach the threshold instead of retrying forever.

        A failed effect is terminal and the same idempotency key returns that
        terminal record, so retries cannot accumulate on one effect. The counter
        is therefore per **job**: consecutive failed effects, not attempts at a
        single effect.
        """
        if self.failure_count(job_id) < self._max_attempts:
            return None
        return EffectOutcome(terminal=EffectTerminal.POISON, reason="attempts-exhausted")

    @staticmethod
    def non_compensable(reason: str, effect_id: str | None = None) -> EffectOutcome:
        """An effect that cannot be compensated. Never retried; needs a human."""
        return EffectOutcome(terminal=EffectTerminal.NEEDS_HUMAN_INTERVENTION,
                             reason=reason, effect_id=effect_id)

    @staticmethod
    def cancelled(effect_id: str | None = None) -> EffectOutcome:
        return EffectOutcome(terminal=EffectTerminal.CANCELLED, reason="cancelled",
                             effect_id=effect_id)

    @staticmethod
    def _terminal_for(record: EffectRecord) -> EffectTerminal:
        return {
            EffectState.APPLIED: EffectTerminal.APPLIED,
            EffectState.FAILED: EffectTerminal.FAILED,
            EffectState.COMPENSATED: EffectTerminal.COMPENSATED,
        }.get(record.state, EffectTerminal.FAILED)


__all__ = [
    "CrashPoint",
    "DEFAULT_MAX_ATTEMPTS",
    "EffectOutcome",
    "EffectTerminal",
    "InjectedCrash",
    "RunnerJobExecutor",
]
