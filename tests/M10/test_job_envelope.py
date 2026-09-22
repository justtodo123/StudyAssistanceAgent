"""M10 job envelope: budget, progress, cancel and terminal state.

Validated with **synthetic** step loops, as M10 plan §5 step 3 requires — there
is no production release and nothing constructs the runner outside this file.

The load-bearing test here is `test_every_budget_field_is_classified`: M9 once
advertised `max_output_tokens` as a budget with no runtime enforcement point at
all. Every field must therefore appear in exactly one of `ENFORCED_LOCALLY` /
`NOT_ENFORCED_LOCALLY`, so a new field cannot be added and silently read as a
gate it is not.
"""

from __future__ import annotations

import time

import pytest

from app.job_envelope import (
    DEFAULT_CONCURRENCY,
    DEFAULT_CPU_SECONDS,
    DEFAULT_DISK_BYTES,
    DEFAULT_WALL_CLOCK_SECONDS,
    ENFORCED_ELSEWHERE,
    ENFORCED_LOCALLY,
    NOT_ENFORCED_LOCALLY,
    ConcurrencyGate,
    JobBudget,
    JobBudgetError,
    JobEnvelope,
    JobTerminal,
    SyntheticJobRunner,
    directory_bytes,
)

pytestmark = pytest.mark.m10


def _envelope(**budget_overrides) -> JobEnvelope:
    return JobEnvelope(job_id="job-1", kind="synthetic", scope_id="m10-autonomous-runner-v1",
                       budget=JobBudget(**budget_overrides))


def _spin(seconds: float):
    def work(_index: int) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            pass
    return work


def test_every_budget_field_is_in_exactly_one_enforcement_class() -> None:
    """Partition the fields three ways so none can be added unclassified.

    A string-scan for the field name would pass on the declaration alone; the
    behavioural sweep below is what actually establishes enforcement.
    """
    fields = set(JobBudget.__dataclass_fields__)
    classes = [set(ENFORCED_LOCALLY), set(ENFORCED_ELSEWHERE), set(NOT_ENFORCED_LOCALLY)]
    assert set().union(*classes) == fields
    for left in range(len(classes)):
        for right in range(left + 1, len(classes)):
            assert not (classes[left] & classes[right])
    # The two named as not enforced are named for a reason, not by omission.
    assert set(NOT_ENFORCED_LOCALLY) == {"ai_tokens", "ai_cost_usd"}


def test_each_elsewhere_enforced_budget_names_a_real_symbol() -> None:
    """The named execution point must resolve, not just read plausibly."""
    import importlib

    for field_name, dotted in ENFORCED_ELSEWHERE.items():
        parts = dotted.split(".")  # module.path.Owner.method
        module = importlib.import_module(".".join(parts[:-2]))
        owner = getattr(module, parts[-2])
        assert callable(getattr(owner, parts[-1])), (
            f"{dotted} does not resolve for {field_name}"
        )


@pytest.mark.parametrize(("overrides", "work", "reason"), [
    ({"wall_clock_seconds": 0.05}, _spin(0.02), "JOB_DEADLINE_EXCEEDED"),
    ({"cpu_seconds": 0.01}, _spin(0.02), "JOB_CPU_EXCEEDED"),
])
def test_each_loop_enforced_budget_can_actually_stop_a_job(overrides, work, reason) -> None:
    """Behavioural, not nominal: the job must stop, and early."""
    envelope = SyntheticJobRunner().run(_envelope(**overrides), steps=1000, work=work)

    assert envelope.reason == reason
    assert envelope.terminal in {JobTerminal.DEADLINE_EXCEEDED, JobTerminal.BUDGET_EXCEEDED}
    assert envelope.progress.completed < 1000


def test_a_bounded_job_completes_and_reports_progress() -> None:
    envelope = SyntheticJobRunner().run(_envelope(), steps=4)

    assert envelope.terminal is JobTerminal.COMPLETED
    assert envelope.progress.completed == 4
    assert envelope.progress.total == 4
    assert envelope.progress.updated_at


def test_a_zero_step_job_completes_without_running_anything() -> None:
    calls: list[int] = []
    envelope = SyntheticJobRunner().run(_envelope(), steps=0, work=calls.append)

    assert envelope.terminal is JobTerminal.COMPLETED
    assert calls == []


def test_a_failing_step_fails_the_job_without_escaping() -> None:
    def work(_index: int) -> None:
        raise RuntimeError("synthetic step failure")

    envelope = SyntheticJobRunner().run(_envelope(), steps=3, work=work)
    assert envelope.terminal is JobTerminal.FAILED
    assert envelope.reason == "step-failed"


def test_the_wall_clock_budget_stops_the_job_at_a_step_boundary() -> None:
    envelope = SyntheticJobRunner().run(
        _envelope(wall_clock_seconds=0.05), steps=100, work=_spin(0.02)
    )
    assert envelope.terminal is JobTerminal.DEADLINE_EXCEEDED
    assert envelope.reason == "JOB_DEADLINE_EXCEEDED"
    # Stopped early rather than running the full loop.
    assert envelope.progress.completed < 100


def test_the_cpu_budget_stops_a_spinning_job() -> None:
    """Wall-clock and CPU are separate: a spinning loop burns both, so this pins
    that the CPU counter is a real, separately-measured gate."""
    envelope = SyntheticJobRunner().run(
        _envelope(cpu_seconds=0.01, wall_clock_seconds=DEFAULT_WALL_CLOCK_SECONDS),
        steps=1000, work=_spin(0.02),
    )
    assert envelope.terminal is JobTerminal.BUDGET_EXCEEDED
    assert envelope.reason == "JOB_CPU_EXCEEDED"


def test_the_disk_budget_stops_the_job(tmp_path) -> None:
    envelope = _envelope(disk_bytes=64)
    envelope.workspace = tmp_path

    def work(index: int) -> None:
        (tmp_path / f"chunk-{index}.bin").write_bytes(b"x" * 128)

    SyntheticJobRunner().run(envelope, steps=10, work=work)
    assert envelope.terminal is JobTerminal.BUDGET_EXCEEDED
    assert envelope.reason == "JOB_DISK_EXCEEDED"
    assert directory_bytes(tmp_path) > 64


def test_cancellation_is_checked_at_every_step_boundary() -> None:
    envelope = _envelope()
    seen: list[int] = []

    def work(index: int) -> None:
        seen.append(index)
        if index == 1:
            envelope.cancel()

    SyntheticJobRunner().run(envelope, steps=10, work=work)

    assert envelope.terminal is JobTerminal.CANCELLED
    assert envelope.reason == "JOB_CANCELLED"
    # The step that requested the cancel finished; the next boundary stopped it.
    assert seen == [0, 1]


def test_cancellation_wins_over_a_budget_that_is_also_exhausted() -> None:
    """Deterministic ordering: a caller asking to stop is not told about a budget."""
    envelope = _envelope(wall_clock_seconds=0.0)
    envelope.cancel()
    with pytest.raises(JobBudgetError) as caught:
        envelope.check()
    assert caught.value.code == "JOB_CANCELLED"


def test_the_concurrency_cap_is_acquired_and_released(tmp_path) -> None:
    """Non-vacuity: the job must really hold the slot, or 'released' means nothing."""
    gate = ConcurrencyGate(DEFAULT_CONCURRENCY)
    runner = SyntheticJobRunner(concurrency=gate)
    envelope = _envelope()
    held: list[int] = []

    def work(_index: int) -> None:
        held.append(gate.active)  # observed while the job is running

    runner.run(envelope, steps=1, work=work)

    assert envelope.terminal is JobTerminal.COMPLETED
    assert held == [1]  # the slot was actually held during the step
    assert gate.active == 0  # and released afterwards


def test_the_concurrency_slot_is_released_even_when_a_step_fails() -> None:
    gate = ConcurrencyGate(DEFAULT_CONCURRENCY)

    def work(_index: int) -> None:
        raise RuntimeError("synthetic step failure")

    SyntheticJobRunner(concurrency=gate).run(_envelope(), steps=1, work=work)
    assert gate.active == 0


def test_the_concurrency_cap_refuses_a_second_job(tmp_path) -> None:
    gate = ConcurrencyGate(1)
    gate.acquire(1)
    envelope = _envelope()

    SyntheticJobRunner(concurrency=gate).run(envelope, steps=1)
    assert envelope.terminal is JobTerminal.BUDGET_EXCEEDED
    assert envelope.reason == "JOB_CONCURRENCY_EXCEEDED"
    gate.release(1)


def test_a_budget_may_only_be_tightened() -> None:
    JobBudget(wall_clock_seconds=DEFAULT_WALL_CLOCK_SECONDS / 2)  # tightening is fine

    for overrides in (
        {"wall_clock_seconds": DEFAULT_WALL_CLOCK_SECONDS + 1},
        {"cpu_seconds": DEFAULT_CPU_SECONDS + 1},
        {"disk_bytes": DEFAULT_DISK_BYTES + 1},
        {"concurrency": DEFAULT_CONCURRENCY + 1},
        {"wall_clock_seconds": -1},
        {"disk_bytes": -1},
        {"wall_clock_seconds": float("nan")},
        {"cpu_seconds": float("inf")},
        {"concurrency": True},
        {"disk_bytes": 1.5},
    ):
        with pytest.raises(JobBudgetError) as caught:
            JobBudget(**overrides)
        assert caught.value.code == "JOB_BUDGET_INVALID"


def test_the_job_status_carries_no_workspace_path_or_user_data(tmp_path) -> None:
    envelope = _envelope()
    envelope.workspace = tmp_path
    envelope.progress.total = 2
    envelope.progress.advance("step")
    status = envelope.as_dict()

    assert set(status) == {"job_id", "kind", "scope_id", "terminal", "reason",
                           "progress", "started_at"}
    assert str(tmp_path) not in repr(status)
    assert set(status["progress"]) == {"completed", "total", "message", "updated_at"}
