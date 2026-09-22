"""M10 write authorization: the rejection path comes first.

`M10-WRITE-AUTHORIZATION` requires a write allowlist separate from the read-only
preview, deny-by-default capability, a confirmation bound to one exact write, and
append-only audit holding digests only. M10 plan §5 step 1 implements the
refusals before the acceptance path, so most of this file drives rejections.

The production allowlist is frozen empty, so the acceptance path is exercised
through an injected allowlist — which the registry still requires to be disjoint
from the preview allowlist.
"""

from __future__ import annotations

import pytest

from app.protocols import SideEffect, ToolCapability, ToolSpec
from app.runner_authority import (
    RUNNER_WRITE_TOOL_ALLOWLIST,
    Confirmation,
    EffectState,
    RevocationRegistry,
    RunnerAuthorityError,
    RunnerWriteRegistry,
    argument_digest,
    assert_transition_allowed,
    idempotency_key,
    issue_confirmation,
)
from app.tool_registry import PREVIEW_TOOL_ALLOWLIST

pytestmark = pytest.mark.m10

_SCHEMA = {"type": "object", "properties": {"file": {"type": "string"}}, "required": ["file"]}


def _write_spec(name: str = "log_review", **overrides) -> ToolSpec:
    fields = {
        "name": name,
        "description": "record one review",
        "input_schema": _SCHEMA,
        "capability": ToolCapability.WRITE,
        "side_effect": SideEffect.DOMAIN_WRITE,
        "idempotent": True,
    }
    fields.update(overrides)
    return ToolSpec(**fields)


def _registry(**kwargs) -> RunnerWriteRegistry:
    return RunnerWriteRegistry({"log_review"}, **kwargs)


def test_the_production_allowlist_is_empty_so_nothing_can_be_registered() -> None:
    """Deny by default is the frozen starting state, not a configuration."""
    assert RUNNER_WRITE_TOOL_ALLOWLIST == frozenset()
    registry = RunnerWriteRegistry()
    with pytest.raises(RunnerAuthorityError) as caught:
        registry.register(_write_spec())
    assert caught.value.code == "WRITE_TOOL_NOT_ALLOWED"


def test_the_write_allowlist_must_be_disjoint_from_the_preview_allowlist() -> None:
    """A read-only preview name must not become writable by reusing its identity."""
    preview_name = sorted(PREVIEW_TOOL_ALLOWLIST)[0]
    with pytest.raises(RunnerAuthorityError) as caught:
        RunnerWriteRegistry({preview_name})
    assert caught.value.code == "WRITE_ALLOWLIST_OVERLAP"

    # Non-vacuity: the overlap check must actually have something to compare.
    assert PREVIEW_TOOL_ALLOWLIST


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"capability": ToolCapability.READ, "side_effect": SideEffect.NONE},
         "WRITE_TOOL_NOT_WRITE"),
        ({"idempotent": False}, "WRITE_TOOL_NOT_IDEMPOTENT"),
    ],
)
def test_registration_refuses_anything_that_is_not_an_idempotent_domain_write(
    overrides, code
) -> None:
    registry = _registry()
    with pytest.raises(RunnerAuthorityError) as caught:
        registry.register(_write_spec(**overrides))
    assert caught.value.code == code
    assert registry.get("log_review") is None


def test_upstream_contract_write_requires_a_declared_side_effect() -> None:
    """Pin the invariant the registry deliberately does not re-check.

    `RunnerWriteRegistry.register` has no `WRITE_TOOL_NO_SIDE_EFFECT` branch
    because `ToolSpec` already refuses that combination — a duplicate check would
    be unreachable. If this ever stops holding, the registry must re-add it.
    """
    with pytest.raises(Exception) as caught:
        _write_spec(side_effect=SideEffect.NONE)
    assert "side effect" in str(caught.value)


def test_upstream_contract_keeps_the_two_allowlists_disjoint() -> None:
    """The registry's per-name preview check is unreachable for the same reason."""
    preview_name = sorted(PREVIEW_TOOL_ALLOWLIST)[0]
    registry = _registry()
    # A preview name is not in the write allowlist, so it is refused there first.
    with pytest.raises(RunnerAuthorityError) as caught:
        registry.register(_write_spec(name=preview_name))
    assert caught.value.code == "WRITE_TOOL_NOT_ALLOWED"
    assert registry.allowlist.isdisjoint(PREVIEW_TOOL_ALLOWLIST)


def test_authorize_refuses_every_incomplete_authorization() -> None:
    registry = _registry()
    registry.register(_write_spec())
    arguments = {"file": "knowledge/os/scheduling.md"}
    confirmation = issue_confirmation(
        job_id="job-1", tool_name="log_review", arguments=arguments
    )

    # Unregistered tool.
    with pytest.raises(RunnerAuthorityError) as caught:
        registry.authorize(name="other", job_id="job-1", arguments=arguments,
                           permissions=frozenset({"write"}), confirmation=confirmation)
    assert caught.value.code == "WRITE_TOOL_NOT_REGISTERED"

    # Missing write capability: fail closed rather than fall back to read.
    with pytest.raises(RunnerAuthorityError) as caught:
        registry.authorize(name="log_review", job_id="job-1", arguments=arguments,
                           permissions=frozenset({"read"}), confirmation=confirmation)
    assert caught.value.code == "WRITE_CAPABILITY_MISSING"

    # No confirmation at all.
    with pytest.raises(RunnerAuthorityError) as caught:
        registry.authorize(name="log_review", job_id="job-1", arguments=arguments,
                           permissions=frozenset({"write"}), confirmation=None)
    assert caught.value.code == "WRITE_CONFIRMATION_REQUIRED"


def test_a_confirmation_is_bound_to_one_exact_write() -> None:
    registry = _registry()
    registry.register(_write_spec())
    original = {"file": "knowledge/os/scheduling.md"}
    confirmation = issue_confirmation(
        job_id="job-1", tool_name="log_review", arguments=original
    )
    permissions = frozenset({"write"})

    # Same confirmation, different arguments: the replay shape M9's source delete
    # refuses. The write must not proceed.
    with pytest.raises(RunnerAuthorityError) as caught:
        registry.authorize(name="log_review", job_id="job-1",
                           arguments={"file": "knowledge/os/deadlock.md"},
                           permissions=permissions, confirmation=confirmation)
    assert caught.value.code == "WRITE_CONFIRMATION_ARGUMENT_MISMATCH"

    # Confirmation issued for a different job or tool.
    with pytest.raises(RunnerAuthorityError) as caught:
        registry.authorize(name="log_review", job_id="job-2", arguments=original,
                           permissions=permissions, confirmation=confirmation)
    assert caught.value.code == "WRITE_CONFIRMATION_MISMATCH"

    # The matching write is the only one that passes.
    record = registry.authorize(name="log_review", job_id="job-1", arguments=original,
                                permissions=permissions, confirmation=confirmation)
    assert record.decision == "authorized"


def test_a_revoked_authorization_can_never_be_applied() -> None:
    revocations = RevocationRegistry()
    registry = _registry(revocations=revocations)
    registry.register(_write_spec())
    arguments = {"file": "knowledge/os/scheduling.md"}
    confirmation = issue_confirmation(
        job_id="job-1", tool_name="log_review", arguments=arguments
    )
    permissions = frozenset({"write"})

    revocations.revoke(job_id="job-1", tool_name="log_review")
    with pytest.raises(RunnerAuthorityError) as caught:
        registry.authorize(name="log_review", job_id="job-1", arguments=arguments,
                           permissions=permissions, confirmation=confirmation)
    assert caught.value.code == "WRITE_AUTHORIZATION_REVOKED"


def test_the_audit_is_append_only_and_holds_digests_only() -> None:
    registry = _registry()
    registry.register(_write_spec())
    secret = "knowledge/os/private-note.md"
    arguments = {"file": secret}
    audit: list = []

    with pytest.raises(RunnerAuthorityError):
        registry.authorize(name="log_review", job_id="job-1", arguments=arguments,
                           permissions=frozenset({"read"}), confirmation=None, audit=audit)
    confirmation = issue_confirmation(
        job_id="job-1", tool_name="log_review", arguments=arguments
    )
    registry.authorize(name="log_review", job_id="job-1", arguments=arguments,
                       permissions=frozenset({"write"}), confirmation=confirmation,
                       audit=audit)

    # One entry per decision, refusals included.
    assert [entry.decision for entry in audit] == ["refused-no-capability", "authorized"]
    # Digests only: the argument value must not appear anywhere in the audit.
    assert all(entry.argument_digest == argument_digest(arguments) for entry in audit)
    assert secret not in repr(audit)


def test_effect_state_transitions_are_checked() -> None:
    assert_transition_allowed(EffectState.PROPOSED, EffectState.AUTHORIZED)
    assert_transition_allowed(EffectState.PENDING, EffectState.APPLIED)
    assert_transition_allowed(EffectState.APPLIED, EffectState.COMPENSATED)

    for current, target in (
        (EffectState.APPLIED, EffectState.PENDING),
        (EffectState.FAILED, EffectState.APPLIED),
        (EffectState.COMPENSATED, EffectState.PENDING),
        (EffectState.PROPOSED, EffectState.APPLIED),
    ):
        with pytest.raises(RunnerAuthorityError) as caught:
            assert_transition_allowed(current, target)
        assert caught.value.code == "EFFECT_TRANSITION_INVALID"


def test_the_idempotency_key_is_derived_from_job_tool_arguments_and_scope() -> None:
    arguments = {"file": "knowledge/os/scheduling.md"}
    base = idempotency_key(job_id="job-1", tool_name="log_review",
                           arguments=arguments, scope_id="m10-autonomous-runner-v1")
    assert len(base) == 64

    for changed in (
        {"job_id": "job-2", "tool_name": "log_review", "arguments": arguments,
         "scope_id": "m10-autonomous-runner-v1"},
        {"job_id": "job-1", "tool_name": "other", "arguments": arguments,
         "scope_id": "m10-autonomous-runner-v1"},
        {"job_id": "job-1", "tool_name": "log_review",
         "arguments": {"file": "knowledge/os/deadlock.md"},
         "scope_id": "m10-autonomous-runner-v1"},
        {"job_id": "job-1", "tool_name": "log_review", "arguments": arguments,
         "scope_id": "other-scope"},
    ):
        assert idempotency_key(**changed) != base


def test_confirmation_rejects_an_incomplete_binding() -> None:
    for field in ("job_id", "tool_name", "argument_digest"):
        values = {"job_id": "job-1", "tool_name": "log_review",
                  "argument_digest": "a" * 64, "confirmed_at": "2026-09-22T00:00:00Z"}
        values[field] = ""
        with pytest.raises(RunnerAuthorityError) as caught:
            Confirmation(**values)
        assert caught.value.code == "WRITE_CONFIRMATION_INVALID"
