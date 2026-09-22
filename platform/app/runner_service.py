"""The optional autonomous Runner: default off, and off is an identity operation.

M10 plan §5 step 6. This is the first module that touches production wiring, so
three rules from `M10-ROLLOUT` are load-bearing:

- **default off is an identity operation.** `SA_RUNNER` unset means the service is
  not constructed and its router is not registered, so the default public surface
  and the state-machine path are unchanged rather than merely unchanged-in-effect.
- **the kill switch is checked at every effect boundary**, not once at job start.
  A long job that could only be stopped before it began is not stoppable.
- **the Runner writes nothing itself.** The domain write is a callable the caller
  supplies — in production the same `ReviewSchedulerService.log_review` the
  existing `/api/v1/review-log` route calls. `M10-AUTHORITY` is not weakened by
  giving the Runner a second path to domain state.

The public path is `/api/v1/autonomous-runs`, already reserved as a *forbidden*
prefix in the M6a closeout contracts: it must not appear in the default OpenAPI
document, which is exactly what conditional registration gives.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .effect_ledger import EffectLedgerStore, EffectRecord
from .effect_reconcile import ReconcileReport, ReconcileVerdict, Reconciler
from .job_envelope import JobBudget, JobBudgetError, JobEnvelope, SyntheticJobRunner
from .protocols import SideEffect, ToolCapability, ToolSpec
from .runner_authority import (
    Confirmation,
    RevocationRegistry,
    RunnerAuthorityError,
    RunnerWriteRegistry,
    argument_digest,
    issue_confirmation,
)
from .runner_recovery import CrashPoint, EffectOutcome, RunnerJobExecutor

RUNNER_PATH = "/api/v1/autonomous-runs"

#: The first and only approved write tool. Its spec is what the write registry
#: validates; the domain write itself is supplied by the caller (see the route).
LOG_REVIEW_SPEC = ToolSpec(
    name="log_review",
    description="record one completed review through the review scheduler",
    input_schema={"type": "object",
                  "properties": {"file": {"type": "string"},
                                 "course": {"type": "string"},
                                 "source_session_id": {"type": "string"}},
                  "required": ["file"]},
    capability=ToolCapability.WRITE,
    side_effect=SideEffect.DOMAIN_WRITE,
    idempotent=True,
)


@dataclass(frozen=True, slots=True)
class RunnerStatus:
    """Content-free job status. No workspace path, no arguments, no user data."""

    job_id: str
    state: str
    progress: dict[str, object]
    terminal: str | None


class RunnerService:
    """Owns the ledger, the write authority and the recovery pipeline for one process."""

    def __init__(self, *, store_path: str | Path,
                 authority: RunnerWriteRegistry | None = None,
                 revocations: RevocationRegistry | None = None,
                 max_deferrals: int = 3) -> None:
        self._ledger = EffectLedgerStore(store_path)
        self._revocations = revocations or RevocationRegistry()
        self._authority = authority or RunnerWriteRegistry(revocations=self._revocations)
        self._killed = False
        # The executor's boundary hook is where the kill switch lives: it runs at
        # every effect boundary, which is what makes a long job stoppable.
        self._executor = RunnerJobExecutor(
            ledger=self._ledger, authority=self._authority,
            revocations=self._revocations, crash_hook=self._boundary,
        )
        self._reconciler = Reconciler(self._ledger, max_deferrals=max_deferrals)
        if self._authority.get(LOG_REVIEW_SPEC.name) is None:
            self._authority.register(LOG_REVIEW_SPEC)

    # -- kill switch --------------------------------------------------------

    def kill(self) -> None:
        """Stop the Runner. Checked at every effect boundary from here on."""
        self._killed = True

    def revive(self) -> None:
        self._killed = False

    @property
    def killed(self) -> bool:
        return self._killed

    def _boundary(self, _point: CrashPoint) -> None:
        if self._killed:
            raise RunnerAuthorityError("RUNNER_KILLED", "the runner was stopped.")

    # -- jobs ---------------------------------------------------------------

    def start_job(self, *, job_id: str, scope_id: str, learner_id: str) -> None:
        self._ledger.create_job(job_id=job_id, scope_id=scope_id, learner_id=learner_id)

    def submit_write(self, *, job_id: str, effect_id: str, tool_name: str,
                     arguments: Mapping[str, Any], permissions: frozenset[str],
                     confirmation: Confirmation | None, scope_id: str,
                     apply: Callable[[], str]) -> EffectOutcome:
        """Run one write through the pipeline. `apply` is the domain write.

        A kill raises out of the boundary hook rather than returning an outcome:
        the effect is left non-terminal on purpose, so a reconcile can classify it
        afterwards instead of the kill inventing an answer.
        """
        return self._executor.execute_effect(
            job_id=job_id, effect_id=effect_id, tool_name=tool_name, arguments=arguments,
            permissions=permissions, confirmation=confirmation, scope_id=scope_id, apply=apply,
        )

    def log_review(self, *, job_id: str, arguments: Mapping[str, Any],
                   apply: Callable[[], str]) -> EffectOutcome:
        """Run the one approved write through the full pipeline.

        The confirmation is issued **here, from these exact arguments**, rather
        than accepted from the caller. A caller-supplied token could describe a
        different write than the one being submitted — the replay shape
        `M10-WRITE-AUTHORIZATION` refuses — and there is no way to tell from the
        token alone. Binding it server-side makes that state unreachable.
        """
        effect_id = f"{job_id}:log_review:{argument_digest(arguments)[:16]}"
        return self.submit_write(
            job_id=job_id, effect_id=effect_id, tool_name=LOG_REVIEW_SPEC.name,
            arguments=arguments, permissions=frozenset({"write"}),
            confirmation=issue_confirmation(job_id=job_id, tool_name=LOG_REVIEW_SPEC.name,
                                            arguments=arguments),
            scope_id="m10-autonomous-runner-v1", apply=apply,
        )

    def resume_job(self, *, job_id: str, reconcile: Callable[[EffectRecord], bool],
                   revalidate: Callable[[], bool] | None = None) -> tuple[EffectOutcome, ...]:
        return self._executor.resume_job(job_id=job_id, reconcile=reconcile,
                                         revalidate=revalidate)

    def reconcile(self, *, probe: Callable[[EffectRecord], ReconcileVerdict]) -> ReconcileReport:
        return self._reconciler.sweep(probe=probe)

    # -- observability ------------------------------------------------------

    def status(self, job_id: str) -> RunnerStatus | None:
        state = self._ledger.get_job_state(job_id)
        if state is None:
            return None
        effects = self._ledger.all_effects(job_id)
        applied = sum(1 for record in effects
                      if record.state.value in {"applied", "failed", "compensated"})
        return RunnerStatus(
            job_id=job_id,
            state="killed" if self._killed else state,
            progress={"completed": applied, "total": len(effects)},
            terminal=None,
        )

    def run_bounded(self, *, job_id: str, kind: str, steps: int,
                    budget: JobBudget | None = None,
                    work: Callable[[int], None] | None = None) -> JobEnvelope:
        """Drive a bounded synthetic job. The kill switch is checked per step.

        `SyntheticJobRunner` reports budget exhaustion through the envelope's
        terminal state rather than by raising, so there is nothing to catch here.
        """
        envelope = JobEnvelope(job_id=job_id, kind=kind, scope_id="m10-autonomous-runner-v1",
                               budget=budget or JobBudget(), guard=self._kill_guard)
        return SyntheticJobRunner().run(envelope, steps=steps, work=work)

    def _kill_guard(self) -> None:
        """The boundary guard. Raises the same error family the loop already maps."""
        if self._killed:
            raise JobBudgetError("JOB_KILLED", "the runner was stopped.")


__all__ = ["RUNNER_PATH", "RunnerService", "RunnerStatus"]
