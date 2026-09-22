"""Reconcile, compensation and human intervention for stuck effects.

M10 plan §5 step 5. `M10-EFFECT-LEDGER` makes outbox + reconcile mandatory as the
price of keeping runner state in its own database, and `M10-RECOVERY` requires
that an effect which cannot be compensated ends in a **non-retryable** terminal
state needing a human, with a trace, and is never silently retried.

Three rules carry the weight:

- **reconcile is idempotent.** A second pass over the same ledger finds nothing
  to do, because the first pass left every examined effect in a terminal state.
  A reconciler that could apply something twice would manufacture exactly the
  duplicate side effects the ledger exists to prevent.
- **inconclusive is not success.** When the domain probe cannot answer, the
  effect stays `pending` and the pass is recorded as `deferred`; after a bounded
  number of deferrals it escalates rather than looping forever.
- **escalation is terminal and manual.** An escalated effect is never picked up
  by a later sweep, and nothing retries it automatically.

No production release: nothing constructs the reconciler outside its tests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from .effect_ledger import EffectLedgerStore, EffectRecord
from .runner_authority import EffectState

DEFAULT_MAX_DEFERRALS = 3

#: Outcomes recorded per reconcile pass. `deferred` and `escalated` are distinct
#: on purpose: one means "ask again later", the other means "a human must decide".
OUTCOME_APPLIED = "applied"
OUTCOME_FAILED = "failed"
OUTCOME_DEFERRED = "deferred"
OUTCOME_ESCALATED = "escalated"


class ReconcileVerdict(StrEnum):
    """What the domain probe says about a `pending` effect."""

    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ReconcileReport:
    """One sweep's tally. `examined == 0` is the idempotent second pass."""

    examined: int = 0
    applied: int = 0
    failed: int = 0
    deferred: int = 0
    escalated: int = 0

    @property
    def changed(self) -> int:
        return self.applied + self.failed + self.escalated


@dataclass(frozen=True, slots=True)
class Intervention:
    """One effect waiting on a human. Carries digests only, never content."""

    effect_id: str
    job_id: str
    tool_name: str
    reason: str


class Reconciler:
    """Converges `pending` effects against the domain, and escalates what it cannot."""

    def __init__(self, ledger: EffectLedgerStore, *,
                 max_deferrals: int = DEFAULT_MAX_DEFERRALS) -> None:
        if not isinstance(max_deferrals, int) or isinstance(max_deferrals, bool) \
                or max_deferrals < 1:
            raise ValueError("max_deferrals must be a positive integer.")
        self._ledger = ledger
        self._max_deferrals = max_deferrals

    def sweep(self, *, probe: Callable[[EffectRecord], ReconcileVerdict]) -> ReconcileReport:
        """One pass over every `pending` effect. Idempotent by construction.

        The probe answers for the domain; this class never assumes. A `present`
        verdict marks the effect applied, `absent` marks it failed, and `unknown`
        defers — deferring is not a failure, and is not a success either.
        """
        examined = applied = failed = deferred = escalated = 0
        for record in self._ledger.pending_effects():
            if self._is_escalated(record.effect_id):
                # Already handed to a human. Converging it here would make the
                # escalation advisory, which is exactly what it must not be.
                continue
            examined += 1
            verdict = probe(record)
            if verdict is ReconcileVerdict.PRESENT:
                self._ledger.mark_applied(record.effect_id, record.result_digest or "")
                self._ledger.record_reconcile_attempt(effect_id=record.effect_id,
                                                      outcome=OUTCOME_APPLIED)
                applied += 1
            elif verdict is ReconcileVerdict.ABSENT:
                self._ledger.mark_failed(record.effect_id)
                self._ledger.record_reconcile_attempt(effect_id=record.effect_id,
                                                      outcome=OUTCOME_FAILED)
                failed += 1
            elif self._deferrals(record.effect_id) + 1 >= self._max_deferrals:
                # Bounded: an unanswerable effect escalates instead of looping.
                self._ledger.record_reconcile_attempt(effect_id=record.effect_id,
                                                      outcome=OUTCOME_ESCALATED)
                escalated += 1
            else:
                self._ledger.record_reconcile_attempt(effect_id=record.effect_id,
                                                      outcome=OUTCOME_DEFERRED)
                deferred += 1
        return ReconcileReport(examined=examined, applied=applied, failed=failed,
                               deferred=deferred, escalated=escalated)

    def compensate(self, effect_id: str) -> EffectRecord:
        """Undo an applied effect, or record that it cannot be undone.

        `M10-RECOVERY` distinguishes the two: a compensable effect moves to
        `compensated`; an uncompensable one is escalated and must not be retried.
        """
        record = self._ledger.get_effect(effect_id)
        if record is None:
            raise ValueError("the effect does not exist.")
        if record.state is EffectState.FAILED:
            # Already terminal and never applied — nothing to undo, and saying
            # "compensated" would claim an undo that never happened.
            return record
        return self._ledger.mark_compensated(effect_id)

    def open_interventions(self) -> tuple[Intervention, ...]:
        """Effects escalated to a human, oldest first.

        Escalated effects are still `pending` in the ledger — they are not
        applied and not failed, because neither is true. That is deliberate: a
        later sweep must not quietly resolve them, so this queue is the only way
        they move.
        """
        interventions: list[Intervention] = []
        for record in self._ledger.pending_effects():
            if self._is_escalated(record.effect_id):
                interventions.append(Intervention(
                    effect_id=record.effect_id,
                    job_id=record.job_id,
                    tool_name=record.tool_name,
                    reason=OUTCOME_ESCALATED,
                ))
        return tuple(interventions)

    def resolve_intervention(self, effect_id: str, *, verdict: ReconcileVerdict) -> EffectRecord:
        """A human's answer for an escalated effect. The only way it moves."""
        if verdict is ReconcileVerdict.UNKNOWN:
            raise ValueError("a human decision must be present or absent.")
        if verdict is ReconcileVerdict.PRESENT:
            record = self._ledger.mark_applied(effect_id, "")
            self._ledger.record_reconcile_attempt(effect_id=effect_id,
                                                  outcome="resolved-present")
            return record
        record = self._ledger.mark_failed(effect_id)
        self._ledger.record_reconcile_attempt(effect_id=effect_id,
                                              outcome="resolved-absent")
        return record

    def _deferrals(self, effect_id: str) -> int:
        return sum(1 for outcome in self._ledger.reconcile_attempts(effect_id)
                   if outcome == OUTCOME_DEFERRED)

    def _is_escalated(self, effect_id: str) -> bool:
        """Whether the last pass over this effect handed it to a human.

        A resolution (`resolved-present` / `resolved-absent`) is a later row, so
        this is false again once a human has decided — and by then the effect is
        terminal and no longer `pending`, so no sweep sees it anyway.
        """
        attempts = self._ledger.reconcile_attempts(effect_id)
        return bool(attempts) and attempts[-1] == OUTCOME_ESCALATED


__all__ = [
    "DEFAULT_MAX_DEFERRALS",
    "Intervention",
    "OUTCOME_APPLIED",
    "OUTCOME_DEFERRED",
    "OUTCOME_ESCALATED",
    "OUTCOME_FAILED",
    "ReconcileReport",
    "ReconcileVerdict",
    "Reconciler",
]
