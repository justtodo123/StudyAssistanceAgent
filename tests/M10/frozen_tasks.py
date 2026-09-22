"""The frozen Agent task set for M10's arm A.

`M10-EVALUATION` requires a **frozen** task set: the gate has to mean the same
thing tomorrow as it does today. Step 6's test plan froze the *shape* — task
category, expected terminal state, unauthorized probe, recovery probe — and
deliberately not a corpus, because the runner did not exist yet and freezing
samples then would have written an unverified assumption into a frozen artifact.

The runner now exists, so this module materialises that shape. What is frozen is
still **not** a corpus of documents: M10's runner drives domain writes and
synthetic step loops, and it has no retrieval path of its own to seed. The
workload is the scenario list below, and its digest is pinned in
`test_runner_evaluation.py` — changing a scenario changes the digest, so the
change has to be deliberate rather than incidental.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

#: Metrics this workload is expected to produce. The 0-tolerance group comes from
#: `M10-EVALUATION`; each name is classified in `ENFORCED_LOCALLY` /
#: `NOT_ENFORCED_LOCALLY` below so a metric cannot read as a gate it is not.
ZERO_TOLERANCE_METRICS = (
    "unauthorized_write_rate",
    "duplicate_effect_count",
    "half_published_generation_count",
)

#: Metrics with a real local execution point in this workload.
ENFORCED_LOCALLY = (
    "unauthorized_write_rate",
    "duplicate_effect_count",
    "half_published_generation_count",
    "crash_matrix_coverage",
    "state_machine_default_rollback",
)

#: Metrics this workload does **not** measure, named rather than omitted.
#:
#: - `default_90_questions` is a protected baseline asserted by `tests/M0_M2/`
#:   and `tests/regression/test_rag_quality.py`; re-running it here would be a
#:   second, weaker copy of an existing gate.
#: - latency, cost and real-provider failure modes belong to arm B, which is
#:   opt-in and non-gating; M10's runner has no provider path at all.
NOT_ENFORCED_LOCALLY = ("default_90_questions", "latency", "cost", "real_provider_failure_modes")


@dataclass(frozen=True, slots=True)
class FrozenTask:
    """One scenario. `expected_terminal` is the observable the gate checks."""

    task_id: str
    category: str
    expected_terminal: str
    unauthorized_probe: str | None
    recovery_probe: str | None


#: The frozen scenario list, in the order the evaluation drives them.
WORKLOAD: tuple[FrozenTask, ...] = (
    FrozenTask("read-only", "read_only", "completed", None, None),
    FrozenTask("single-write", "single_write", "applied",
               "write without capability is refused", None),
    FrozenTask("multi-write", "multi_write", "applied",
               "confirmation for other arguments is refused", None),
    FrozenTask("unauthorized-write", "unauthorized_write", "failed", None, None),
    FrozenTask("long-job-cancel", "long_job_cancel", "cancelled", None, "crash point 8"),
    FrozenTask("crash-recovery", "crash_recovery", "applied", None, "crash points 1-7"),
    FrozenTask("generation-publication", "generation_publication", "applied", None,
               "every publication crash point"),
)


def workload_digest() -> str:
    """Canonical digest of the frozen scenario list.

    Covers every field of every task, so any edit — including a reordering or a
    reworded probe — changes the digest.
    """
    payload = [
        [task.task_id, task.category, task.expected_terminal,
         task.unauthorized_probe, task.recovery_probe]
        for task in WORKLOAD
    ]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ENFORCED_LOCALLY",
    "FrozenTask",
    "NOT_ENFORCED_LOCALLY",
    "WORKLOAD",
    "ZERO_TOLERANCE_METRICS",
    "workload_digest",
]
