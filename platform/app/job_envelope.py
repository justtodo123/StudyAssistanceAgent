"""Generic async job envelope: budget, progress, cancel, terminal state.

M10 plan §5 step 3, validated with **synthetic long tasks that have no
production release** — nothing here is wired into `main.py`, and the production
write allowlist is still empty.

Two disciplines are inherited rather than reinvented:

- **Every budget names its local execution point, or it is not a gate.** M9
  shipped `max_output_tokens` advertised as a budget with no runtime enforcement
  at all. Each field here is classified in `ENFORCED_LOCALLY` or
  `NOT_ENFORCED_LOCALLY`, and a test asserts every field appears in exactly one
  of the two — so a new field cannot slip in unclassified.
- **Only tightening.** Defaults are frozen module constants; a caller may pass a
  smaller budget and is refused a larger one, exactly as `max_bytes` and
  `PlanAILimits` work.

Resource coverage follows M10 plan §1.1: wall-clock, CPU, disk, concurrency,
external AI token/cost (if enabled) and retention.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

DEFAULT_WALL_CLOCK_SECONDS = 60.0
DEFAULT_CPU_SECONDS = 30.0
DEFAULT_DISK_BYTES = 64 * 1024 * 1024
DEFAULT_CONCURRENCY = 1
DEFAULT_RETENTION_SECONDS = 24 * 60 * 60
DEFAULT_AI_TOKENS = 0
DEFAULT_AI_COST_USD = 0.0

#: Fields the **step loop** enforces, at every step boundary. A test drives each
#: one to exhaustion and asserts the job actually stops, so the claim is
#: behavioural rather than a name appearing in the source.
ENFORCED_LOCALLY: tuple[str, ...] = (
    "wall_clock_seconds",
    "cpu_seconds",
    "disk_bytes",
    "concurrency",
)

#: Fields enforced in-process but **not** by the step loop, mapped to the symbol
#: that enforces them. Kept separate from `ENFORCED_LOCALLY` so "enforced by the
#: loop" is not quietly stretched to mean "enforced somewhere".
ENFORCED_ELSEWHERE: Mapping[str, str] = MappingProxyType(
    {"retention_seconds": "app.effect_ledger.EffectLedgerStore.purge_expired"}
)

#: Fields this module does **not** enforce. Named rather than omitted, because an
#: unenforced field that reads like a gate is worse than an absent one.
#:
#: - `ai_tokens` / `ai_cost_usd`: a job that never calls a provider has nothing to
#:   meter. When the runner gains an AI path these move to the enforced list, or
#:   they stay here and must not be advertised as gates.
NOT_ENFORCED_LOCALLY: tuple[str, ...] = ("ai_tokens", "ai_cost_usd")


class JobBudgetError(ValueError):
    """A job was refused. Carries a stable code and never any user content."""

    def __init__(self, code: str, message: str = "the job budget was exceeded.") -> None:
        self.code = code
        super().__init__(message)


class JobTerminal(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    BUDGET_EXCEEDED = "budget_exceeded"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class JobBudget:
    """Frozen-defaults budget. A caller may only tighten it."""

    wall_clock_seconds: float = DEFAULT_WALL_CLOCK_SECONDS
    cpu_seconds: float = DEFAULT_CPU_SECONDS
    disk_bytes: int = DEFAULT_DISK_BYTES
    concurrency: int = DEFAULT_CONCURRENCY
    retention_seconds: int = DEFAULT_RETENTION_SECONDS
    ai_tokens: int = DEFAULT_AI_TOKENS
    ai_cost_usd: float = DEFAULT_AI_COST_USD

    def __post_init__(self) -> None:
        for name, ceiling in (
            ("wall_clock_seconds", DEFAULT_WALL_CLOCK_SECONDS),
            ("cpu_seconds", DEFAULT_CPU_SECONDS),
            ("ai_cost_usd", DEFAULT_AI_COST_USD),
        ):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) \
                    or value != value or value in (float("inf"), float("-inf")) \
                    or value < 0 or value > ceiling:
                raise JobBudgetError(
                    "JOB_BUDGET_INVALID", f"{name} must be a finite value within the frozen default."
                )
        for name, ceiling in (
            ("disk_bytes", DEFAULT_DISK_BYTES),
            ("concurrency", DEFAULT_CONCURRENCY),
            ("retention_seconds", DEFAULT_RETENTION_SECONDS),
            ("ai_tokens", DEFAULT_AI_TOKENS),
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > ceiling:
                raise JobBudgetError(
                    "JOB_BUDGET_INVALID", f"{name} must be a non-negative integer within the frozen default."
                )


@dataclass
class JobProgress:
    """Bounded, content-free progress. Never carries user data."""

    completed: int = 0
    total: int = 0
    message: str = ""
    updated_at: str = ""

    def advance(self, message: str = "") -> None:
        self.completed += 1
        self.message = message
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def as_dict(self) -> dict[str, object]:
        return {"completed": self.completed, "total": self.total,
                "message": self.message, "updated_at": self.updated_at}


class ConcurrencyGate:
    """Process-wide concurrency cap. The single-worker topology makes this enough."""

    def __init__(self, limit: int = DEFAULT_CONCURRENCY) -> None:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise JobBudgetError("JOB_BUDGET_INVALID", "concurrency must be a positive integer.")
        self._limit = limit
        self._active = 0
        self._lock = threading.Lock()

    @property
    def active(self) -> int:
        with self._lock:
            return self._active

    def acquire(self, requested: int) -> None:
        if not isinstance(requested, int) or isinstance(requested, bool) or requested < 1:
            raise JobBudgetError("JOB_BUDGET_INVALID", "concurrency must be a positive integer.")
        with self._lock:
            if self._active + requested > self._limit:
                raise JobBudgetError(
                    "JOB_CONCURRENCY_EXCEEDED", "the concurrency budget is exhausted."
                )
            self._active += requested

    def release(self, requested: int) -> None:
        with self._lock:
            self._active = max(0, self._active - requested)


def directory_bytes(root: Path) -> int:
    """Total size of a job workspace. The disk budget's local execution point."""
    if not root.exists():
        return 0
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


@dataclass
class JobEnvelope:
    """One job's identity, budget, progress and terminal state."""

    job_id: str
    kind: str
    scope_id: str
    budget: JobBudget
    workspace: Path | None = None
    progress: JobProgress = field(default_factory=JobProgress)
    terminal: JobTerminal | None = None
    reason: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _cancelled: bool = False
    _wall_start: float = field(default_factory=time.monotonic, repr=False)
    _cpu_start: float = field(default_factory=time.process_time, repr=False)

    def cancel(self) -> None:
        """Request cancellation. Checked at every step boundary, not just at start."""
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def finished(self) -> bool:
        return self.terminal is not None

    def check(self, *, concurrency: ConcurrencyGate | None = None,
              requested_concurrency: int = 1) -> None:
        """The step-boundary guard. Raises on the first budget that is exhausted.

        Order matters for reproducibility: cancellation first (a caller asking to
        stop should not be told about a budget), then wall-clock, then CPU, then
        disk, then concurrency.
        """
        if self._cancelled:
            raise JobBudgetError("JOB_CANCELLED", "the job was cancelled.")
        if time.monotonic() - self._wall_start > self.budget.wall_clock_seconds:
            raise JobBudgetError("JOB_DEADLINE_EXCEEDED", "the wall-clock budget is exhausted.")
        if time.process_time() - self._cpu_start > self.budget.cpu_seconds:
            raise JobBudgetError("JOB_CPU_EXCEEDED", "the CPU budget is exhausted.")
        if self.workspace is not None and directory_bytes(self.workspace) > self.budget.disk_bytes:
            raise JobBudgetError("JOB_DISK_EXCEEDED", "the disk budget is exhausted.")
        if concurrency is not None:
            concurrency.acquire(requested_concurrency)

    def as_dict(self) -> dict[str, object]:
        """Content-free job status. No workspace path, no user data."""
        return {
            "job_id": self.job_id,
            "kind": self.kind,
            "scope_id": self.scope_id,
            "terminal": self.terminal.value if self.terminal else None,
            "reason": self.reason,
            "progress": self.progress.as_dict(),
            "started_at": self.started_at,
        }


class SyntheticJobRunner:
    """Runs a bounded step loop. **No production release**: nothing constructs this.

    The step callable is supplied by the caller, which is how this is validated
    with synthetic work rather than a real ingestion or embedding path.
    """

    def __init__(self, *, concurrency: ConcurrencyGate | None = None) -> None:
        self._concurrency = concurrency

    def run(self, envelope: JobEnvelope, *, steps: int,
            work: Callable[[int], None] | None = None,
            requested_concurrency: int = 1) -> JobEnvelope:
        """Run `steps` bounded steps and record exactly one terminal state."""
        if not isinstance(steps, int) or isinstance(steps, bool) or steps < 0:
            raise JobBudgetError("JOB_STEPS_INVALID", "steps must be a non-negative integer.")
        envelope.progress.total = steps

        acquired = False
        try:
            # One gate acquisition for the whole job, released in `finally`, so a
            # crash mid-job cannot leak a slot.
            envelope.check(concurrency=self._concurrency,
                           requested_concurrency=requested_concurrency)
            acquired = self._concurrency is not None
            for index in range(steps):
                envelope.check()
                if work is not None:
                    work(index)
                envelope.progress.advance()
            envelope.terminal = JobTerminal.COMPLETED
            envelope.reason = "completed"
        except JobBudgetError as exc:
            envelope.terminal = {
                "JOB_CANCELLED": JobTerminal.CANCELLED,
                "JOB_DEADLINE_EXCEEDED": JobTerminal.DEADLINE_EXCEEDED,
            }.get(exc.code, JobTerminal.BUDGET_EXCEEDED)
            envelope.reason = exc.code
        except Exception:  # noqa: BLE001 - a failing step is a failed job, not a crash
            envelope.terminal = JobTerminal.FAILED
            envelope.reason = "step-failed"
        finally:
            if acquired:
                self._concurrency.release(requested_concurrency)
        return envelope


__all__ = [
    "ConcurrencyGate",
    "DEFAULT_AI_COST_USD",
    "DEFAULT_AI_TOKENS",
    "DEFAULT_CONCURRENCY",
    "DEFAULT_CPU_SECONDS",
    "DEFAULT_DISK_BYTES",
    "DEFAULT_RETENTION_SECONDS",
    "DEFAULT_WALL_CLOCK_SECONDS",
    "ENFORCED_ELSEWHERE",
    "ENFORCED_LOCALLY",
    "NOT_ENFORCED_LOCALLY",
    "JobBudget",
    "JobBudgetError",
    "JobEnvelope",
    "JobProgress",
    "JobTerminal",
    "SyntheticJobRunner",
    "directory_bytes",
]
