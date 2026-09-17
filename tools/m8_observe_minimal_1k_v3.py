#!/usr/bin/env python3
"""Synthetic-only M8 minimal-1K v3 observer ledger orchestration.

This module deliberately contains no Win32, socket, process-enumeration, backend,
or authorization implementation.  It accepts injected collectors so S0 tests can
exercise the closed ledger/lifecycle contract without touching real roots.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Protocol

try:
    from m8_validate_minimal_1k_graph_v3 import (
        canonical,
        canonical_jsonl_records,
        canonical_relative_path,
        valid_observer_detail,
    )
except ModuleNotFoundError:  # Supports import as tools.m8_observe_minimal_1k_v3.
    from tools.m8_validate_minimal_1k_graph_v3 import (
        canonical,
        canonical_jsonl_records,
        canonical_relative_path,
        valid_observer_detail,
    )


SYNTHETIC_PURPOSE = "S0_SYNTHETIC_TEST_ONLY"
AUTHORIZATION_STATE = "NOT_S1_AUTHORIZED"
OBSERVERS = ("network", "process", "redaction", "write")
PHASES = (
    "observer-bootstrap",
    "acquisition",
    "measured",
    "redaction-and-seal",
    "cleanup",
    "observer-finalize",
)
ALLOWED_KINDS = {
    "network": {"outbound-connection"},
    "write": {"allowed-write", "denied-write"},
    "process": {"child-count", "unexpected-child"},
    "redaction": {"utf8-scan", "sensitive-match"},
}
CLOSED_FAILURE_KINDS = {
    "network": set(),
    "write": {"denied-write"},
    "process": {"unexpected-child"},
    "redaction": {"sensitive-match"},
}


class ObserverContractError(ValueError):
    """Raised when synthetic input cannot satisfy the frozen observer contract."""


class ObserverPublicationError(RuntimeError):
    """Raised when a complete four-ledger set cannot be published atomically."""


class Collector(Protocol):
    """Minimal injectable collector interface used only by the orchestrator."""

    def start(self) -> None: ...

    def collect(self, phase: str) -> Iterable[Mapping[str, object]]: ...

    def seal(self) -> None: ...

    def coverage(self) -> Mapping[str, object]: ...

    def stop(self) -> None: ...


@dataclass(frozen=True)
class SyntheticObserverContext:
    """Non-authoritative digests and coverage expectations for synthetic tests."""

    root_process_identity: str
    allowed_root_set_sha256: str
    registry_sha256: str
    scanned_set_sha256: str
    api_ids: Mapping[str, tuple[str, ...]]
    expected_redaction_paths: tuple[str, ...] = ()
    purpose: str = SYNTHETIC_PURPOSE
    authorization_state: str = AUTHORIZATION_STATE

    def validate(self) -> None:
        if self.purpose != SYNTHETIC_PURPOSE:
            raise ObserverContractError("only synthetic S0 observation is supported")
        if self.authorization_state != AUTHORIZATION_STATE:
            raise ObserverContractError("this helper cannot represent S1 authorization")
        for name, value in (
            ("root_process_identity", self.root_process_identity),
            ("allowed_root_set_sha256", self.allowed_root_set_sha256),
            ("registry_sha256", self.registry_sha256),
            ("scanned_set_sha256", self.scanned_set_sha256),
        ):
            if not _is_sha256(value):
                raise ObserverContractError(f"{name} must be a lowercase SHA-256")
        if set(self.api_ids) != {"network", "process", "write"}:
            raise ObserverContractError("api_ids must cover network, process, and write")
        for observer, values in self.api_ids.items():
            if (
                not isinstance(values, tuple)
                or not values
                or any(not isinstance(item, str) or not item for item in values)
                or list(values) != sorted(set(values), key=lambda item: item.encode("utf-8"))
            ):
                raise ObserverContractError(f"{observer} api_ids are not sorted and unique")
        expected = list(self.expected_redaction_paths)
        if expected != sorted(set(expected), key=lambda item: item.encode("utf-8")):
            raise ObserverContractError("expected redaction paths must be sorted and unique")
        for path in expected:
            if not _safe_relative_path(path):
                raise ObserverContractError("expected redaction path is not canonical relative")


@dataclass(frozen=True)
class ObservationRun:
    """Published summaries plus stable fail-closed diagnostic codes."""

    observers: Mapping[str, Mapping[str, object]]
    passed: bool
    errors: tuple[str, ...] = field(default_factory=tuple)


def synthetic_context(label: str = "fixture") -> SyntheticObserverContext:
    """Build deterministic non-authoritative context values for S0 tests."""

    def digest(suffix: str) -> str:
        return hashlib.sha256(f"{label}:{suffix}".encode("utf-8")).hexdigest()

    return SyntheticObserverContext(
        root_process_identity=digest("root-process"),
        allowed_root_set_sha256=digest("allowed-roots"),
        registry_sha256=digest("redaction-registry"),
        scanned_set_sha256=digest("scanned-set"),
        api_ids={
            "network": ("fake-network-api",),
            "process": ("fake-process-api",),
            "write": ("fake-write-api",),
        },
    )


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_relative_path(value: object) -> bool:
    return canonical_relative_path(value)


def _lifecycle_detail(
    observer: str,
    phase: str,
    code: str,
    context: SyntheticObserverContext,
) -> dict[str, object]:
    if observer == "redaction":
        return {
            "code": code,
            "phase": phase,
            "registry_sha256": context.registry_sha256,
            "scanned_set_sha256": context.scanned_set_sha256,
        }
    detail: dict[str, object] = {
        "api_ids": list(context.api_ids[observer]),
        "code": code,
        "phase": phase,
        "root_process_identity": context.root_process_identity,
    }
    if observer == "write":
        detail["allowed_root_set_sha256"] = context.allowed_root_set_sha256
    return detail


def _event(
    observer: str,
    kind: str,
    sequence: int,
    status: str,
    detail: Mapping[str, object],
) -> dict[str, object]:
    value = {
        "detail": dict(detail),
        "kind": kind,
        "sequence": sequence,
        "status": status,
    }
    if not valid_observer_detail(observer, kind, status, value["detail"]):
        raise ObserverContractError(f"{observer}: detail rejected by graph validator")
    return value


def _stable_failure_code(stage: str) -> str:
    return {
        "start": "collector-start-failed",
        "collect": "collector-read-failed",
        "coverage": "collector-coverage-failed",
        "event": "collector-event-invalid",
        "seal": "collector-seal-failed",
        "stop": "collector-stop-failed",
    }[stage]


def _append_candidate(
    observer: str,
    events: list[dict[str, object]],
    phase: str,
    candidate: Mapping[str, object],
) -> None:
    if not isinstance(candidate, Mapping) or set(candidate) != {"detail", "kind", "status"}:
        raise ObserverContractError("collector event must contain detail, kind, and status")
    kind = candidate.get("kind")
    status = candidate.get("status")
    detail = candidate.get("detail")
    if kind not in ALLOWED_KINDS[observer]:
        raise ObserverContractError("collector event kind is not allowed")
    if status not in {"PASS", "FAIL"}:
        raise ObserverContractError("collector event status is not allowed")
    if not isinstance(detail, Mapping):
        raise ObserverContractError("collector event detail must be an object")
    if detail.get("phase") != phase:
        raise ObserverContractError("collector event phase does not match active phase")
    if kind in CLOSED_FAILURE_KINDS[observer] and status != "FAIL":
        raise ObserverContractError("closed failure event must have FAIL status")
    events.append(_event(observer, str(kind), len(events), str(status), detail))


def _coverage_failure(
    observer: str,
    collector: Collector,
    events: list[dict[str, object]],
    context: SyntheticObserverContext,
) -> bool:
    try:
        receipt = collector.coverage()
    except Exception:
        return True
    if not isinstance(receipt, Mapping) or set(receipt) != {
        "complete",
        "observer",
        "phases",
    }:
        return True
    if (
        receipt.get("complete") is not True
        or receipt.get("observer") != observer
        or receipt.get("phases") != PHASES
    ):
        return True

    body = events[1:]
    if observer == "process":
        phases = [
            detail["phase"]
            for event in body
            if event["kind"] == "child-count"
            and isinstance((detail := event["detail"]), dict)
        ]
        return phases != list(PHASES)
    if observer == "redaction":
        paths = [
            detail["path"]
            for event in body
            if event["kind"] == "utf8-scan"
            and isinstance((detail := event["detail"]), dict)
        ]
        return paths != list(context.expected_redaction_paths)
    return False


def _run_collector(
    observer: str,
    collector: Collector,
    context: SyntheticObserverContext,
) -> tuple[list[dict[str, object]], tuple[str, ...]]:
    events: list[dict[str, object]] = []
    errors: list[str] = []
    internal_failure: str | None = None

    try:
        collector.start()
    except Exception:  # Collector boundaries must fail closed without leaking detail.
        internal_failure = "start"
        code = _stable_failure_code("start")
        events.append(
            _event(
                observer,
                "observer-start",
                0,
                "FAIL",
                _lifecycle_detail(observer, "observer-bootstrap", code, context),
            )
        )
    else:
        events.append(
            _event(
                observer,
                "observer-start",
                0,
                "PASS",
                _lifecycle_detail(observer, "observer-bootstrap", "none", context),
            )
        )

    if internal_failure is None:
        try:
            for phase in PHASES:
                candidates = collector.collect(phase)
                if candidates is None:
                    raise ObserverContractError("collector returned no iterable")
                for candidate in candidates:
                    _append_candidate(observer, events, phase, candidate)
        except ObserverContractError:
            internal_failure = "event"
        except Exception:
            internal_failure = "collect"

    if internal_failure is None and _coverage_failure(
        observer, collector, events, context
    ):
        internal_failure = "coverage"

    if internal_failure is None:
        try:
            collector.seal()
        except Exception:
            internal_failure = "seal"

    try:
        collector.stop()
    except Exception:
        if internal_failure is None:
            internal_failure = "stop"

    if internal_failure is not None:
        code = _stable_failure_code(internal_failure)
        errors.append(f"{observer}:{code}")
        status = "FAIL"
    else:
        code = "none"
        status = "PASS"
    events.append(
        _event(
            observer,
            "observer-stop",
            len(events),
            status,
            _lifecycle_detail(observer, "observer-finalize", code, context),
        )
    )
    return events, tuple(errors)


def validate_ledger_bytes(observer: str, data: bytes) -> list[dict[str, object]]:
    """Validate framing, sequence, lifecycle, closed kinds, and graph detail schema."""

    if observer not in OBSERVERS:
        raise ObserverContractError("unknown observer")
    if not data or not data.endswith(b"\n"):
        raise ObserverContractError("ledger must be non-empty and end with LF")
    try:
        records = canonical_jsonl_records(data)
    except (UnicodeError, ValueError) as exc:
        raise ObserverContractError(f"ledger is not canonical JSONL: {exc}") from exc
    if len(records) < 2:
        raise ObserverContractError("ledger must contain at least two events")
    if records[0].get("kind") != "observer-start" or records[-1].get("kind") != "observer-stop":
        raise ObserverContractError("ledger lifecycle is not closed")
    allowed = ALLOWED_KINDS[observer] | {"observer-start", "observer-stop"}
    for sequence, record in enumerate(records):
        if set(record) != {"detail", "kind", "sequence", "status"}:
            raise ObserverContractError("event has an open top-level shape")
        kind = record.get("kind")
        status = record.get("status")
        event_sequence = record.get("sequence")
        if (
            not isinstance(event_sequence, int)
            or isinstance(event_sequence, bool)
            or event_sequence != sequence
        ):
            raise ObserverContractError("event sequence is not contiguous")
        if kind not in allowed or status not in {"PASS", "FAIL"}:
            raise ObserverContractError("event kind or status is not allowed")
        if kind == "observer-start" and sequence != 0:
            raise ObserverContractError("observer-start must be the first event")
        if kind == "observer-stop" and sequence != len(records) - 1:
            raise ObserverContractError("observer-stop must be the final event")
        if kind in CLOSED_FAILURE_KINDS[observer] and status != "FAIL":
            raise ObserverContractError("closed failure event must fail")
        if not valid_observer_detail(observer, kind, status, record.get("detail")):
            raise ObserverContractError("event detail was rejected by graph validator")
    return records


def seal_ledger(
    observer: str,
    events: Iterable[Mapping[str, object]],
) -> tuple[bytes, dict[str, object]]:
    """Canonicalize and summarize the exact binary bytes, including the final LF."""

    data = b"".join(canonical(dict(event)) for event in events)
    records = validate_ledger_bytes(observer, data)
    status = "FAIL" if any(record["status"] == "FAIL" for record in records) else "PASS"
    summary = {
        "path": f"events/{observer}.jsonl",
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
        "event_count": len(records),
        "status": status,
    }
    return data, summary


def summarize_ledger_bytes(observer: str, data: bytes) -> dict[str, object]:
    """Revalidate and recompute a summary from binary ledger bytes."""

    records = validate_ledger_bytes(observer, data)
    return {
        "path": f"events/{observer}.jsonl",
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
        "event_count": len(records),
        "status": "FAIL" if any(item["status"] == "FAIL" for item in records) else "PASS",
    }


def _has_reparse_point(file_stat: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(file_stat, "st_file_attributes", 0) & reparse_flag)


def _inspect_publication_path(path: Path) -> Path:
    """Reject links/reparse points in each existing publication component."""
    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current /= part
        try:
            file_stat = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise ObserverPublicationError(
                "evidence directory cannot be inspected"
            ) from exc
        if stat.S_ISLNK(file_stat.st_mode) or _has_reparse_point(file_stat):
            raise ObserverPublicationError(
                "evidence directory contains a symlink or reparse point"
            )
    return absolute


def _publish_ledgers(evidence_dir: Path, ledgers: Mapping[str, bytes]) -> None:
    if not evidence_dir.is_absolute():
        raise ObserverPublicationError(
            "evidence directory must be an existing absolute directory"
        )
    evidence_dir = _inspect_publication_path(evidence_dir)
    if not evidence_dir.is_dir():
        raise ObserverPublicationError(
            "evidence directory must be an existing absolute directory"
        )
    events_dir = evidence_dir / "events"
    _inspect_publication_path(events_dir)
    if events_dir.exists():
        raise ObserverPublicationError(
            "events directory already exists; overwrite is forbidden"
        )
    staging = Path(tempfile.mkdtemp(prefix=".m8-observer-", dir=evidence_dir))
    try:
        for observer in OBSERVERS:
            path = staging / f"{observer}.jsonl"
            with path.open("xb") as handle:
                handle.write(ledgers[observer])
                handle.flush()
                os.fsync(handle.fileno())
        os.replace(staging, events_dir)
    except Exception as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise ObserverPublicationError("complete ledger publication failed") from exc


def observe_synthetic(
    evidence_dir: Path,
    collectors: Mapping[str, Collector],
    context: SyntheticObserverContext,
) -> ObservationRun:
    """Run injected collectors and atomically publish four synthetic ledgers.

    This entry point cannot grant, consume, or emulate S1 authorization.
    """

    context.validate()
    if set(collectors) != set(OBSERVERS):
        raise ObserverContractError("exactly four named collectors are required")
    ledgers: dict[str, bytes] = {}
    summaries: dict[str, Mapping[str, object]] = {}
    errors: list[str] = []
    for observer in OBSERVERS:
        events, collector_errors = _run_collector(observer, collectors[observer], context)
        data, summary = seal_ledger(observer, events)
        ledgers[observer] = data
        summaries[observer] = summary
        errors.extend(collector_errors)
    _publish_ledgers(Path(evidence_dir), ledgers)
    passed = not errors and all(summary["status"] == "PASS" for summary in summaries.values())
    return ObservationRun(observers=summaries, passed=passed, errors=tuple(errors))
