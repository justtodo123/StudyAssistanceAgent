"""Write-side-effect authority for the M10 autonomous runner.

Default off and **deny by default**: `RUNNER_WRITE_TOOL_ALLOWLIST` is empty, so no
write tool can be registered at all until an owner decision puts one there. This
module implements the rejection path first (M10 plan §5 step 1) — the acceptance
path exists but nothing in production reaches it.

The write surface is deliberately separate from the M6b read-only preview
(`tool_registry.PREVIEW_TOOL_ALLOWLIST`). The two allowlists must stay disjoint:
a name that is read-only in the preview must not become writable here by
reusing its identity.

Authority boundary (`M10-AUTHORITY`): nothing in this module writes domain
state. It decides *whether* a write may proceed; the domain service still
performs it and may still refuse.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from .protocols import SideEffect, ToolCapability, ToolSpec
from .tool_registry import PREVIEW_TOOL_ALLOWLIST

# Deny by default. Empty until an owner decision approves a specific write tool;
# adding a name here is a governance act, not a code change (M10-WRITE-AUTHORIZATION).
RUNNER_WRITE_TOOL_ALLOWLIST: frozenset[str] = frozenset()


class RunnerAuthorityError(ValueError):
    """A write was refused. Carries a stable code and never any user content."""

    def __init__(self, code: str, message: str = "the write is not authorized.") -> None:
        self.code = code
        super().__init__(message)


class EffectState(StrEnum):
    """The six ledger states frozen by `M10-EFFECT-LEDGER`."""

    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    COMPENSATED = "compensated"


# Legality of one step. Terminal states have no outgoing edges, so an applied
# effect can never be silently rewritten — the ledger is append-only in effect.
_LEGAL_TRANSITIONS: Mapping[EffectState, frozenset[EffectState]] = {
    EffectState.PROPOSED: frozenset({EffectState.AUTHORIZED, EffectState.FAILED}),
    EffectState.AUTHORIZED: frozenset({EffectState.PENDING, EffectState.FAILED,
                                       EffectState.COMPENSATED}),
    EffectState.PENDING: frozenset({EffectState.APPLIED, EffectState.FAILED}),
    EffectState.APPLIED: frozenset({EffectState.COMPENSATED}),
    EffectState.FAILED: frozenset(),
    EffectState.COMPENSATED: frozenset(),
}


def assert_transition_allowed(current: EffectState, target: EffectState) -> None:
    """Refuse an illegal ledger step with a stable code."""
    if target not in _LEGAL_TRANSITIONS[current]:
        raise RunnerAuthorityError(
            "EFFECT_TRANSITION_INVALID",
            "the requested effect state transition is not allowed.",
        )


@dataclass(frozen=True, slots=True)
class WriteScope:
    """Who and what a write may touch. Narrowing only; never widened by a caller."""

    learner_id: str
    source_scope: str
    course: str | None = None

    def __post_init__(self) -> None:
        if not self.learner_id or not isinstance(self.learner_id, str):
            raise RunnerAuthorityError("WRITE_SCOPE_INVALID", "a learner id is required.")
        if self.source_scope not in {"DEFAULT_ONLY", "DEFAULT_PLUS_EXTRAS"}:
            raise RunnerAuthorityError("WRITE_SCOPE_INVALID", "the source scope is invalid.")


def argument_digest(arguments: Mapping[str, Any]) -> str:
    """Canonical digest of tool arguments.

    Only the digest is ever persisted or audited — never the argument values,
    which may carry user content (M10-WRITE-AUTHORIZATION, privacy).
    """
    if not isinstance(arguments, Mapping):
        raise RunnerAuthorityError("WRITE_ARGUMENTS_INVALID", "arguments must be an object.")
    try:
        encoded = json.dumps(dict(arguments), ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise RunnerAuthorityError(
            "WRITE_ARGUMENTS_INVALID", "arguments must be JSON-serializable."
        ) from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def idempotency_key(*, job_id: str, tool_name: str, arguments: Mapping[str, Any],
                    scope_id: str) -> str:
    """`sha256(job_id | tool_name | argument digest | scope_id)` (M10-IDEMPOTENCY)."""
    material = "|".join((job_id, tool_name, argument_digest(arguments), scope_id))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Confirmation:
    """An explicit user confirmation bound to one exact write."""

    job_id: str
    tool_name: str
    argument_digest: str
    confirmed_at: str

    def __post_init__(self) -> None:
        for value in (self.job_id, self.tool_name, self.argument_digest):
            if not isinstance(value, str) or not value:
                raise RunnerAuthorityError(
                    "WRITE_CONFIRMATION_INVALID", "the confirmation is incomplete."
                )


def issue_confirmation(*, job_id: str, tool_name: str,
                       arguments: Mapping[str, Any]) -> Confirmation:
    """Build the confirmation a caller must present to write."""
    return Confirmation(
        job_id=job_id,
        tool_name=tool_name,
        argument_digest=argument_digest(arguments),
        confirmed_at=datetime.now(timezone.utc).isoformat(),
    )


@dataclass(frozen=True, slots=True)
class AuthorizationRecord:
    """One append-only authorization decision. Holds a digest, never arguments."""

    job_id: str
    tool_name: str
    argument_digest: str
    decision: str
    recorded_at: str


@dataclass
class RevocationRegistry:
    """Revoked authorizations. A revoked write must never be applied."""

    _revoked: set[str] = field(default_factory=set)

    @staticmethod
    def _key(job_id: str, tool_name: str) -> str:
        return f"{job_id}|{tool_name}"

    def revoke(self, *, job_id: str, tool_name: str) -> None:
        self._revoked.add(self._key(job_id, tool_name))

    def is_revoked(self, *, job_id: str, tool_name: str) -> bool:
        return self._key(job_id, tool_name) in self._revoked


class RunnerWriteRegistry:
    """Register and execute only explicitly approved write tools.

    The allowlist is injectable so tests can exercise the acceptance path, but
    the production default is the frozen empty set and any injected allowlist
    must still be disjoint from the read-only preview allowlist.
    """

    def __init__(self, allowlist: Iterable[str] = RUNNER_WRITE_TOOL_ALLOWLIST,
                 *, revocations: RevocationRegistry | None = None) -> None:
        self._allowlist = frozenset(allowlist)
        overlap = self._allowlist & PREVIEW_TOOL_ALLOWLIST
        if overlap:
            raise RunnerAuthorityError(
                "WRITE_ALLOWLIST_OVERLAP",
                "the write allowlist must be disjoint from the read-only preview allowlist.",
            )
        self._tools: dict[str, ToolSpec] = {}
        self._revocations = revocations or RevocationRegistry()

    @property
    def allowlist(self) -> frozenset[str]:
        return self._allowlist

    def register(self, spec: ToolSpec) -> None:
        """Refuse any spec that is not an approved write tool.

        Two checks are deliberately **not** duplicated here, because they are
        already structural and a copy would be unreachable — which is worse than
        no guard, since it reads as enforcement that never runs:

        - a write spec must declare a side effect: `ToolSpec.__post_init__`
          refuses `WRITE` with `SideEffect.NONE` outright;
        - the name must not be a preview name: the constructor already refuses an
          allowlist overlapping the preview allowlist, so any name that passes
          the allowlist check below is by construction not a preview name.

        `tests/M10/test_write_authorization.py` pins both upstream contracts, so
        relaxing either one fails a test instead of silently opening a hole.
        """
        if spec.name not in self._allowlist:
            raise RunnerAuthorityError(
                "WRITE_TOOL_NOT_ALLOWED", "the tool is not in the write allowlist."
            )
        if spec.capability is not ToolCapability.WRITE:
            raise RunnerAuthorityError(
                "WRITE_TOOL_NOT_WRITE", "the tool does not declare write capability."
            )
        if not spec.idempotent:
            raise RunnerAuthorityError(
                "WRITE_TOOL_NOT_IDEMPOTENT", "the tool is not idempotent."
            )
        if spec.name in self._tools:
            raise RunnerAuthorityError("WRITE_TOOL_DUPLICATE", "the tool is already registered.")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def authorize(self, *, name: str, job_id: str, arguments: Mapping[str, Any],
                  permissions: frozenset[str], confirmation: Confirmation | None,
                  audit: list[AuthorizationRecord] | None = None) -> AuthorizationRecord:
        """Decide whether one write may proceed. Raises on every refusal path.

        Every decision, granted or refused, is recorded append-only with the
        argument **digest** only.
        """
        spec = self._tools.get(name)
        if spec is None:
            raise RunnerAuthorityError(
                "WRITE_TOOL_NOT_REGISTERED", "the tool is not registered for writes."
            )
        if "write" not in permissions:
            self._record(audit, job_id, name, arguments, "refused-no-capability")
            raise RunnerAuthorityError(
                "WRITE_CAPABILITY_MISSING", "the context does not grant write capability."
            )
        if confirmation is None:
            self._record(audit, job_id, name, arguments, "refused-no-confirmation")
            raise RunnerAuthorityError(
                "WRITE_CONFIRMATION_REQUIRED", "an explicit confirmation is required."
            )
        if confirmation.job_id != job_id or confirmation.tool_name != name:
            self._record(audit, job_id, name, arguments, "refused-confirmation-mismatch")
            raise RunnerAuthorityError(
                "WRITE_CONFIRMATION_MISMATCH",
                "the confirmation is bound to a different job or tool.",
            )
        if confirmation.argument_digest != argument_digest(arguments):
            # Same confirmation, different arguments: the replay shape M9's
            # source delete refuses with SOURCE_DELETE_REQUEST_CONFLICT.
            self._record(audit, job_id, name, arguments, "refused-argument-mismatch")
            raise RunnerAuthorityError(
                "WRITE_CONFIRMATION_ARGUMENT_MISMATCH",
                "the confirmation does not match these arguments.",
            )
        if self._revocations.is_revoked(job_id=job_id, tool_name=name):
            self._record(audit, job_id, name, arguments, "refused-revoked")
            raise RunnerAuthorityError(
                "WRITE_AUTHORIZATION_REVOKED", "the authorization has been revoked."
            )
        return self._record(audit, job_id, name, arguments, "authorized")

    @staticmethod
    def _record(audit: list[AuthorizationRecord] | None, job_id: str, name: str,
                arguments: Mapping[str, Any], decision: str) -> AuthorizationRecord:
        record = AuthorizationRecord(
            job_id=job_id,
            tool_name=name,
            argument_digest=argument_digest(arguments),
            decision=decision,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
        if audit is not None:
            audit.append(record)
        return record


__all__ = [
    "AuthorizationRecord",
    "Confirmation",
    "EffectState",
    "RevocationRegistry",
    "RunnerAuthorityError",
    "RunnerWriteRegistry",
    "RUNNER_WRITE_TOOL_ALLOWLIST",
    "WriteScope",
    "argument_digest",
    "assert_transition_allowed",
    "idempotency_key",
    "issue_confirmation",
]
