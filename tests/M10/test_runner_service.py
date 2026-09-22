"""M10 step 6: the optional Runner, default off, and off is an identity operation.

This is the first M10 module that touches production wiring, so the tests are
about the boundary as much as the feature:

- **default off is structural.** With `SA_RUNNER` unset the service is not
  constructed and `/api/v1/autonomous-runs` — a reserved *forbidden* prefix in
  the M6a closeout contracts — does not appear in the OpenAPI document at all.
- **the kill switch is checked at every effect boundary**, so a long job is
  stoppable after it starts, not only before.
- **the Runner writes nothing itself.** The domain write is the same
  `ReviewSchedulerService.log_review` the existing review-log route calls.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.effect_ledger import EffectLedgerStore
from app.runner_authority import Confirmation, RunnerAuthorityError, issue_confirmation
from app.job_envelope import JobTerminal
from app.runner_recovery import EffectTerminal
from app.runner_service import RUNNER_PATH, RunnerService

pytestmark = pytest.mark.m10

_ARGUMENTS = {"file": "knowledge/os/scheduling.md", "course": "os", "source_session_id": ""}


@pytest.fixture
def load_main(monkeypatch: pytest.MonkeyPatch):
    """Import `app.main` under a given switch, then put the session's back.

    Restoring is not optional. Loading a module means `pop` plus re-import, which
    mints a **new module object**; later stages hold the collection-time one.
    `tests/M5b/test_api.py` binds `from app.main import app` at module level and
    patches services by the string `"app.main._study_sessions"`, so a leftover
    module makes those patches land on one object while the served app comes from
    another — the fakes stop being used and the real services run. M6a is the
    other half: it asserts the exact default public surface, which a leftover
    enabled app would violate.
    """
    previous = sys.modules.get("app.main")

    def _load(*, enabled: bool) -> Any:
        monkeypatch.setenv("SA_USE_VECTOR", "false")
        monkeypatch.setenv("SA_RUNNER", "true" if enabled else "false")
        import app.config as config

        importlib.reload(config)
        sys.modules.pop("app.main", None)
        return importlib.import_module("app.main")

    yield _load

    monkeypatch.undo()  # drop this test's env overrides before reloading config
    import app.config as config

    importlib.reload(config)
    if previous is None:
        sys.modules.pop("app.main", None)
    else:
        sys.modules["app.main"] = previous


def _service(tmp_path) -> RunnerService:
    return RunnerService(store_path=tmp_path / "runner_state.sqlite3")


def _job(service: RunnerService, job_id: str = "job-1") -> None:
    service.start_job(job_id=job_id, scope_id="m10-autonomous-runner-v1", learner_id="learner-1")


# -- default off --------------------------------------------------------------


def test_the_default_app_does_not_register_the_runner_route(load_main) -> None:
    """Structural, not merely inert: the path is absent from the OpenAPI document."""
    main = load_main(enabled=False)
    assert RUNNER_PATH not in main.app.openapi()["paths"]
    assert not any(getattr(route, "path", None) == RUNNER_PATH for route in main.app.routes)


def test_the_default_app_still_serves_the_state_machine_path(load_main) -> None:
    """Off is an identity operation: the existing surface is untouched."""
    main = load_main(enabled=False)
    paths = main.app.openapi()["paths"]
    for path in ("/api/v1/study-sessions", "/api/v1/review-log", "/api/v1/plans"):
        assert path in paths


def test_enabling_the_runner_registers_the_route(load_main, monkeypatch, tmp_path) -> None:
    """Non-vacuity for the default-off test: the route must be able to appear."""
    monkeypatch.setenv("SA_LEARNING_STORE_PATH", str(tmp_path / "learning.sqlite3"))
    main = load_main(enabled=True)
    assert RUNNER_PATH in main.app.openapi()["paths"]


# -- the approved write -------------------------------------------------------


def test_the_runner_writes_through_the_domain_service(tmp_path) -> None:
    service = _service(tmp_path)
    _job(service)
    written: list[str] = []

    outcome = service.log_review(job_id="job-1", arguments=_ARGUMENTS,
                                 apply=lambda: written.append("logged") or "r" * 64)

    assert outcome.terminal is EffectTerminal.APPLIED
    assert written == ["logged"]
    assert service.status("job-1").progress["completed"] == 1


def test_the_same_write_twice_is_a_replay_not_a_second_write(tmp_path) -> None:
    """The duplicate-effect witness: the domain write count stays at one."""
    service = _service(tmp_path)
    _job(service)
    calls: list[int] = []

    def apply() -> str:
        calls.append(1)
        return "r" * 64

    first = service.log_review(job_id="job-1", arguments=_ARGUMENTS, apply=apply)
    second = service.log_review(job_id="job-1", arguments=_ARGUMENTS, apply=apply)

    assert first.terminal is EffectTerminal.APPLIED
    assert second.replayed is True
    assert len(calls) == 1


def test_a_write_the_registry_does_not_authorize_never_reaches_the_domain(tmp_path) -> None:
    """The rejection path still holds now that a tool is approved."""
    service = _service(tmp_path)
    _job(service)
    called: list[int] = []

    outcome = service.submit_write(
        job_id="job-1", effect_id="eff-1", tool_name="log_review", arguments=_ARGUMENTS,
        permissions=frozenset({"read"}),  # no write capability
        confirmation=issue_confirmation(job_id="job-1", tool_name="log_review",
                                        arguments=_ARGUMENTS),
        scope_id="m10-autonomous-runner-v1", apply=lambda: called.append(1) or "r" * 64,
    )

    assert outcome.terminal is EffectTerminal.FAILED
    assert outcome.reason == "WRITE_CAPABILITY_MISSING"
    assert called == []


def test_a_confirmation_for_different_arguments_never_reaches_the_domain(tmp_path) -> None:
    service = _service(tmp_path)
    _job(service)
    called: list[int] = []

    outcome = service.submit_write(
        job_id="job-1", effect_id="eff-1", tool_name="log_review", arguments=_ARGUMENTS,
        permissions=frozenset({"write"}),
        confirmation=issue_confirmation(job_id="job-1", tool_name="log_review",
                                        arguments={"file": "knowledge/os/other.md"}),
        scope_id="m10-autonomous-runner-v1", apply=lambda: called.append(1) or "r" * 64,
    )

    assert outcome.terminal is EffectTerminal.FAILED
    assert outcome.reason == "WRITE_CONFIRMATION_ARGUMENT_MISMATCH"
    assert called == []


# -- kill switch --------------------------------------------------------------


def test_the_kill_switch_stops_a_write_before_the_domain_is_touched(tmp_path) -> None:
    service = _service(tmp_path)
    _job(service)
    called: list[int] = []
    service.kill()

    with pytest.raises(RunnerAuthorityError) as caught:
        service.log_review(job_id="job-1", arguments=_ARGUMENTS,
                           apply=lambda: called.append(1) or "r" * 64)

    assert caught.value.code == "RUNNER_KILLED"
    assert called == []


def test_the_kill_switch_leaves_the_effect_unresolved_for_reconcile(tmp_path) -> None:
    """A kill must not invent an answer about an effect it interrupted."""
    service = _service(tmp_path)
    _job(service)
    store = EffectLedgerStore(tmp_path / "runner_state.sqlite3")

    def apply() -> str:
        service.kill()  # killed while the write is in flight
        return "r" * 64

    with pytest.raises(RunnerAuthorityError):
        service.log_review(job_id="job-1", arguments=_ARGUMENTS, apply=apply)

    # Not applied and not failed — a reconcile has to classify it.
    assert [record.effect_id for record in store.unfinished_effects()]


def test_a_bounded_job_is_stopped_by_the_kill_switch_mid_run(tmp_path) -> None:
    """The boundary is per step, so a job that already started is still stoppable."""
    service = _service(tmp_path)
    seen: list[int] = []

    def work(index: int) -> None:
        seen.append(index)
        if index == 1:
            service.kill()

    envelope = service.run_bounded(job_id="job-1", kind="synthetic", steps=100, work=work)

    # Reported as a stop, not as a broken step — an operator has to be able to
    # tell "I stopped it" from "it failed".
    assert envelope.terminal is JobTerminal.CANCELLED
    assert envelope.reason == "JOB_KILLED"
    assert seen == [0, 1]


def test_a_killed_runner_reports_killed_status(tmp_path) -> None:
    service = _service(tmp_path)
    _job(service)
    service.kill()
    assert service.status("job-1").state == "killed"

    service.revive()
    assert service.status("job-1").state == "created"


# -- rollback and observability ----------------------------------------------


def test_disabling_the_runner_leaves_every_record_readable(tmp_path) -> None:
    """Rollback: the switch only stops new work; it never strands what exists."""
    service = _service(tmp_path)
    _job(service)
    service.log_review(job_id="job-1", arguments=_ARGUMENTS, apply=lambda: "r" * 64)

    # A fresh service over the same store is what "restarted with the switch off"
    # looks like — the data is still there and still classifiable.
    reopened = EffectLedgerStore(tmp_path / "runner_state.sqlite3")
    assert reopened.get_job_state("job-1") == "created"
    assert len(reopened.all_effects("job-1")) == 1
    assert reopened.unfinished_effects() == ()


def test_the_status_carries_no_arguments_paths_or_user_data(tmp_path) -> None:
    service = _service(tmp_path)
    _job(service)
    service.log_review(job_id="job-1", arguments=_ARGUMENTS, apply=lambda: "r" * 64)

    status = service.status("job-1")
    rendered = repr(status)
    assert status.job_id == "job-1"
    assert set(status.progress) == {"completed", "total"}
    assert "knowledge/os" not in rendered
    assert str(tmp_path) not in rendered


def test_status_for_an_unknown_job_is_none(tmp_path) -> None:
    assert _service(tmp_path).status("missing") is None
