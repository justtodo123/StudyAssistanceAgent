"""M10 arm A: the frozen task set, deterministic and gating.

`M10-EVALUATION` splits evidence into two arms. This is arm A — a deterministic
run over the frozen scenario list, in CI, **gating**. Arm B (a real provider)
does not exist for M10: the runner has no provider path at all, which
`test_the_runner_has_no_provider_path_so_arm_b_does_not_apply` pins rather than
leaves to be assumed.

Every metric is classified in `frozen_tasks.ENFORCED_LOCALLY` or
`NOT_ENFORCED_LOCALLY`, and the report carries that classification, because M9
shipped a budget advertised as enforced with no execution point anywhere.

The thresholds are `M10-EVALUATION`'s 0-tolerance group. Each is asserted against
an observable the workload actually produces — a rate computed from a count that
the test also proves can be non-zero, so "0" cannot come from measuring nothing.
"""

from __future__ import annotations

import json

import pytest

from app.effect_ledger import EffectLedgerStore
from app.generation_publication import (
    MANIFEST_NAME,
    GenerationCandidate,
    GenerationGate,
    InjectedPublicationCrash,
    PublicationCrashPoint,
    manifest_digest,
)
from app.job_envelope import JobBudget, JobTerminal
from app.runner_authority import EffectState, RunnerAuthorityError, issue_confirmation
from app.runner_recovery import CrashPoint, EffectTerminal, InjectedCrash
from app.runner_service import RunnerService
from tests.M10.frozen_tasks import (
    ENFORCED_LOCALLY,
    NOT_ENFORCED_LOCALLY,
    WORKLOAD,
    workload_digest,
)

pytestmark = pytest.mark.m10

#: Pinned so an edit to the frozen scenarios is deliberate. Changing the workload
#: without updating this is the one way a "frozen" gate silently drifts.
FROZEN_WORKLOAD_DIGEST = "196df3dd489df4f1398a9e460aeb837ef5d36f3f78999e54f90c4ea00bcaaf95"

_ARGUMENTS = {"file": "knowledge/os/scheduling.md", "course": "os", "source_session_id": ""}


def _service(tmp_path, **kwargs) -> RunnerService:
    return RunnerService(store_path=tmp_path / "runner_state.sqlite3", **kwargs)


def _job(service: RunnerService, job_id: str) -> None:
    service.start_job(job_id=job_id, scope_id="m10-autonomous-runner-v1", learner_id="learner-1")


# -- the frozen workload itself ----------------------------------------------


def test_the_frozen_workload_digest_is_pinned() -> None:
    assert workload_digest() == FROZEN_WORKLOAD_DIGEST
    assert len(WORKLOAD) == 7
    assert [task.task_id for task in WORKLOAD] == [
        "read-only", "single-write", "multi-write", "unauthorized-write",
        "long-job-cancel", "crash-recovery", "generation-publication",
    ]


def test_every_metric_is_classified() -> None:
    """Non-vacuity: an unclassified metric would read as a gate that never runs."""
    metrics = set(ENFORCED_LOCALLY) | set(NOT_ENFORCED_LOCALLY)
    assert ENFORCED_LOCALLY and NOT_ENFORCED_LOCALLY
    assert not (set(ENFORCED_LOCALLY) & set(NOT_ENFORCED_LOCALLY))
    # The three the decision names as 0-tolerance must be enforced, not deferred.
    for name in ("unauthorized_write_rate", "duplicate_effect_count",
                 "half_published_generation_count"):
        assert name in ENFORCED_LOCALLY
        assert name in metrics


# -- scenario drivers ---------------------------------------------------------


def _read_only(tmp_path) -> dict:
    """No write at all: the job records nothing and touches no domain state."""
    service = _service(tmp_path)
    _job(service, "job-read-only")
    store = EffectLedgerStore(tmp_path / "runner_state.sqlite3")
    return {"effects": len(store.all_effects("job-read-only")), "domain_calls": 0}


def _single_write(tmp_path) -> dict:
    service = _service(tmp_path)
    _job(service, "job-single")
    calls: list[int] = []
    outcome = service.log_review(job_id="job-single", arguments=_ARGUMENTS,
                                 apply=lambda: calls.append(1) or "r" * 64)
    # The unauthorized probe carries a **valid** confirmation and lacks only the
    # write capability. Passing `confirmation=None` as well would be refused by
    # the confirmation check instead, so deleting the capability check would not
    # change the reading — the probe would be measuring the wrong guard.
    probe_arguments = {"file": "knowledge/os/other.md"}
    refused = service.submit_write(
        job_id="job-single", effect_id="eff-probe", tool_name="log_review",
        arguments=probe_arguments, permissions=frozenset({"read"}),
        confirmation=issue_confirmation(job_id="job-single", tool_name="log_review",
                                        arguments=probe_arguments),
        scope_id="m10-autonomous-runner-v1", apply=lambda: calls.append(1) or "r" * 64,
    )
    return {"terminal": outcome.terminal.value, "domain_calls": len(calls),
            "probe_terminal": refused.terminal.value,
            "probe_reached_domain": len(calls) > 1}


def _multi_write(tmp_path) -> dict:
    service = _service(tmp_path)
    _job(service, "job-multi")
    calls: list[int] = []
    outcomes = [
        service.log_review(
            job_id="job-multi",
            arguments={"file": f"knowledge/os/note-{index}.md", "course": "os",
                       "source_session_id": ""},
            apply=lambda: calls.append(1) or "r" * 64)
        for index in range(3)
    ]
    store = EffectLedgerStore(tmp_path / "runner_state.sqlite3")
    return {"terminals": [o.terminal.value for o in outcomes],
            "domain_calls": len(calls),
            "ledger_rows": len(store.all_effects("job-multi"))}


def _unauthorized_write(tmp_path) -> dict:
    """Scope-外的写：被拒绝，且领域从未被触及。"""
    service = _service(tmp_path)
    _job(service, "job-refused")
    calls: list[int] = []
    outcome = service.submit_write(
        job_id="job-refused", effect_id="eff-1", tool_name="not_approved",
        arguments=_ARGUMENTS, permissions=frozenset({"write"}), confirmation=None,
        scope_id="m10-autonomous-runner-v1", apply=lambda: calls.append(1) or "r" * 64,
    )
    return {"terminal": outcome.terminal.value, "reason": outcome.reason,
            "domain_calls": len(calls)}


def _long_job_cancel(tmp_path) -> dict:
    service = _service(tmp_path)
    seen: list[int] = []

    def work(index: int) -> None:
        seen.append(index)
        if index == 1:
            service.kill()

    envelope = service.run_bounded(job_id="job-long", kind="synthetic", steps=100, work=work)
    return {"terminal": envelope.terminal.value, "reason": envelope.reason,
            "steps_run": len(seen)}


def _crash_recovery(tmp_path) -> dict:
    """Every crash point, then a resume. Counts coverage and duplicate writes."""
    covered = 0
    duplicate_writes = 0
    for index, point in enumerate(CrashPoint):
        root = tmp_path / f"crash-{index}"
        root.mkdir(parents=True, exist_ok=True)
        domain_calls: list[int] = []

        def hook(candidate: CrashPoint, _point=point) -> None:
            if candidate is _point:
                raise InjectedCrash(candidate.value)

        service = RunnerService(store_path=root / "runner_state.sqlite3", fault_hook=hook)
        _job(service, "job-crash")
        try:
            service.log_review(job_id="job-crash", arguments=_ARGUMENTS,
                               apply=lambda: domain_calls.append(1) or "r" * 64)
        except InjectedCrash:
            pass

        before = len(domain_calls)
        service.resume_job(job_id="job-crash", reconcile=lambda record: True)
        if len(domain_calls) > before:
            duplicate_writes += 1
        covered += 1
    return {"crash_points_covered": covered, "crash_points_total": len(CrashPoint),
            "duplicate_writes_on_resume": duplicate_writes}


def _generation_publication(tmp_path) -> dict:
    """Every publication crash point: never a half-published generation."""
    units = [f"u{i}" for i in range(5)]
    digest = manifest_digest(units)
    candidate = GenerationCandidate(source_id="src-1", manifest_digest=digest,
                                    unit_count=len(units))
    half_published = 0
    covered = 0

    for index, point in enumerate(PublicationCrashPoint):
        root = tmp_path / f"pub-{index}"
        root.mkdir(parents=True, exist_ok=True)
        gate = GenerationGate(root)
        gate.stage(candidate, units)
        gate.validate(candidate)
        gate.publish(candidate)

        crashing = GenerationGate(root, crash_hook=lambda p, _p=point: (
            (_ for _ in ()).throw(InjectedPublicationCrash(p.value)) if p is _p else None))
        fresh = GenerationCandidate(source_id="src-1",
                                    manifest_digest=manifest_digest(units + ["extra"]),
                                    unit_count=len(units) + 1)
        try:
            crashing.stage(fresh, units + ["extra"])
            crashing.validate(fresh)
            crashing.publish(fresh)
        except (InjectedPublicationCrash, Exception):  # noqa: BLE001
            pass

        visible = gate.visible("src-1")
        count = gate.visible_unit_count("src-1")
        if visible is not None and count not in {len(units), len(units) + 1}:
            half_published += 1
        covered += 1

    # The crash points exercise atomicity. They do not exercise the *reader's*
    # re-validation, because none of them leaves a pointer naming a generation
    # whose manifest disagrees. Without this probe the metric would stay at zero
    # even with that validation deleted — measuring half of what it claims.
    tampered_root = tmp_path / "pub-tampered"
    tampered_root.mkdir(parents=True, exist_ok=True)
    tampered = GenerationGate(tampered_root)
    tampered.stage(candidate, units)
    tampered.validate(candidate)
    tampered.publish(candidate)
    manifest_path = (tampered_root / "sources" / "src-1" / "generations"
                     / candidate.generation / MANIFEST_NAME)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["manifest_digest"] = manifest_digest(units + ["extra"])
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    if tampered.visible("src-1") is not None:
        half_published += 1

    return {"publication_points_covered": covered,
            "publication_points_total": len(PublicationCrashPoint),
            "half_published": half_published,
            "reader_revalidation_exercised": True}


# -- the gate -----------------------------------------------------------------


def test_arm_a_meets_every_zero_tolerance_threshold(tmp_path) -> None:
    """The gate. Every number is computed from the workload, not asserted by hand."""
    read_only = _read_only(tmp_path / "read-only")
    single = _single_write(tmp_path / "single")
    multi = _multi_write(tmp_path / "multi")
    refused = _unauthorized_write(tmp_path / "refused")
    cancel = _long_job_cancel(tmp_path / "cancel")
    crash = _crash_recovery(tmp_path / "crash")
    publication = _generation_publication(tmp_path / "publication")

    # Each scenario produced the terminal state the frozen list expects.
    assert read_only["effects"] == 0
    assert single["terminal"] == "applied"
    assert multi["terminals"] == ["applied"] * 3
    assert refused["terminal"] == "failed"
    assert cancel["terminal"] == JobTerminal.CANCELLED.value
    assert crash["crash_points_covered"] == crash["crash_points_total"] == 10
    assert publication["publication_points_covered"] == \
        publication["publication_points_total"] == 6

    report = {
        "arm": "A",
        "workload_digest": workload_digest(),
        "enforced_locally": list(ENFORCED_LOCALLY),
        "not_enforced_locally": list(NOT_ENFORCED_LOCALLY),
        "metrics": {
            # 0-tolerance: unauthorized writes that reached the domain.
            "unauthorized_write_rate": refused["domain_calls"],
            # 0-tolerance: a resume that wrote again, and a replay that wrote twice.
            "duplicate_effect_count": (crash["duplicate_writes_on_resume"]
                                       + (multi["domain_calls"] - 3)),
            # 0-tolerance: a reader ever seeing a partial generation.
            "half_published_generation_count": publication["half_published"],
            "crash_matrix_coverage": crash["crash_points_covered"] / crash["crash_points_total"],
        },
    }
    # The report is the artifact; print it so a CI log carries the reading.
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))

    assert report["metrics"]["unauthorized_write_rate"] == 0
    assert report["metrics"]["duplicate_effect_count"] == 0
    assert report["metrics"]["half_published_generation_count"] == 0
    assert report["metrics"]["crash_matrix_coverage"] == 1.0

    # Non-vacuity: the counters must be able to move. A probe that never ran, or a
    # domain write that never happened, would make the zeros above meaningless.
    assert single["domain_calls"] == 1
    assert multi["domain_calls"] == 3
    assert single["probe_terminal"] == EffectTerminal.FAILED.value
    assert single["probe_reached_domain"] is False
    assert cancel["steps_run"] == 2  # stopped mid-run, not before it


def test_the_state_machine_default_rolls_back_cleanly(tmp_path) -> None:
    """`M10-EVALUATION`'s rollback threshold: disabling strands nothing."""
    service = _service(tmp_path)
    _job(service, "job-rollback")
    service.log_review(job_id="job-rollback", arguments=_ARGUMENTS, apply=lambda: "r" * 64)
    service.kill()

    reopened = EffectLedgerStore(tmp_path / "runner_state.sqlite3")
    assert reopened.get_job_state("job-rollback") == "created"
    assert len(reopened.all_effects("job-rollback")) == 1
    assert reopened.unfinished_effects() == ()
    # And the record is terminal, so nothing is left half-done by the kill.
    assert all(record.state is EffectState.APPLIED
               for record in reopened.all_effects("job-rollback"))


def test_the_runner_has_no_provider_path_so_arm_b_does_not_apply(tmp_path) -> None:
    """Why the frozen list has no "provider unavailable" row.

    The test plan's shape included one. M10's runner never calls a provider, so
    there is no fallback to exercise — and asserting a fallback that cannot be
    reached would be a vacuous case. Pinned here so its absence is a checkable
    fact rather than an oversight.
    """
    from pathlib import Path

    import app

    for module in ("runner_service.py", "runner_recovery.py", "effect_ledger.py"):
        source = (Path(app.__file__).parent / module).read_text(encoding="utf-8")
        assert "llm_client" not in source
        assert "anthropic" not in source.lower()
