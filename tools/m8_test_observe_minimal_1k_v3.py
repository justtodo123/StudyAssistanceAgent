#!/usr/bin/env python3
"""Tests for the synthetic-only M8 minimal-1K v3 observer orchestrator."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Mapping, cast
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import m8_observe_minimal_1k_v3 as observe
from m8_validate_minimal_1k_graph_v3 import valid_observer_detail


PHASES = observe.PHASES


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def detail_for(observer: str, phase: str, kind: str) -> dict[str, object]:
    common = {"code": "none", "phase": phase}
    if observer == "process" and kind == "child-count":
        return {**common, "count": 0, "tree_digest": digest(f"tree:{phase}")}
    if observer == "redaction" and kind == "utf8-scan":
        return {
            "byte_count": 3,
            "code": "none",
            "path": "artifacts/result.json",
            "phase": phase,
            "sha256": digest("result-bytes"),
        }
    if observer == "write" and kind == "allowed-write":
        return {
            "code": "none",
            "operation": "create",
            "path_digest": digest("synthetic-path"),
            "phase": phase,
            "process_identity_digest": digest("synthetic-process"),
            "root_id": "temporary-root",
        }
    raise AssertionError((observer, phase, kind))


class FakeCollector:
    def __init__(
        self,
        events: Mapping[str, Iterable[Mapping[str, object]]] | None = None,
        fail: str | None = None,
        *,
        coverage: Mapping[str, object] | None = None,
        coverage_failure: bool = False,
    ) -> None:
        self.events = {phase: list(values) for phase, values in (events or {}).items()}
        self.fail = fail
        self.coverage_receipt = coverage
        self.coverage_failure = coverage_failure
        self.calls: list[str] = []

    def start(self) -> None:
        self.calls.append("start")
        if self.fail == "start" or self.fail == "start+stop":
            raise RuntimeError("synthetic secret must not escape")

    def collect(self, phase: str) -> Iterable[Mapping[str, object]]:
        self.calls.append(f"collect:{phase}")
        if self.fail in {f"collect:{phase}", f"collect:{phase}+stop"}:
            raise RuntimeError("synthetic collector detail")
        return list(self.events.get(phase, ()))

    def seal(self) -> None:
        self.calls.append("seal")
        if self.fail == "seal" or self.fail == "seal+stop":
            raise RuntimeError("synthetic seal detail")

    def coverage(self) -> Mapping[str, object]:
        self.calls.append("coverage")
        if self.coverage_failure:
            raise RuntimeError("synthetic coverage detail")
        if self.coverage_receipt is None:
            raise RuntimeError("coverage receipt missing")
        return dict(self.coverage_receipt)

    def stop(self) -> None:
        self.calls.append("stop")
        if self.fail == "stop" or (self.fail or "").endswith("+stop"):
            raise RuntimeError("synthetic stop detail")


def collectors(
    *,
    network: FakeCollector | None = None,
    process: FakeCollector | None = None,
    redaction: FakeCollector | None = None,
    write: FakeCollector | None = None,
) -> dict[str, FakeCollector]:
    process_events = {
        phase: [
            {
                "detail": detail_for("process", phase, "child-count"),
                "kind": "child-count",
                "status": "PASS",
            }
        ]
        for phase in PHASES
    }

    def complete(observer: str) -> Mapping[str, object]:
        return {
            "complete": True,
            "observer": observer,
            "phases": PHASES,
        }

    return {
        "network": network or FakeCollector(coverage=complete("network")),
        "process": process
        or FakeCollector(process_events, coverage=complete("process")),
        "redaction": redaction or FakeCollector(coverage=complete("redaction")),
        "write": write or FakeCollector(coverage=complete("write")),
    }


class ObserverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.evidence = Path(self.temporary.name).resolve()
        self.context = observe.synthetic_context("observer-tests")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def ledger(self, observer: str) -> bytes:
        return (self.evidence / "events" / f"{observer}.jsonl").read_bytes()

    def test_success_writes_four_canonical_ledgers_and_binary_summaries(self) -> None:
        result = observe.observe_synthetic(self.evidence, collectors(), self.context)
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, ())
        self.assertEqual(set(result.observers), set(observe.OBSERVERS))
        for observer in observe.OBSERVERS:
            data = self.ledger(observer)
            summary = result.observers[observer]
            self.assertTrue(data.endswith(b"\n"))
            self.assertNotIn(b"\r", data)
            self.assertEqual(summary, observe.summarize_ledger_bytes(observer, data))
            self.assertEqual(summary["byte_count"], len(data))
            self.assertEqual(summary["sha256"], hashlib.sha256(data).hexdigest())
            records = observe.validate_ledger_bytes(observer, data)
            self.assertEqual(records[0]["kind"], "observer-start")
            self.assertEqual(records[-1]["kind"], "observer-stop")
            for record in records:
                self.assertEqual(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode("utf-8")
                    + b"\n",
                    observe.canonical(record),
                )
                self.assertTrue(
                    valid_observer_detail(
                        observer,
                        record["kind"],
                        record["status"],
                        record["detail"],
                    )
                )

    def test_closed_event_details_cover_each_non_lifecycle_branch(self) -> None:
        network = FakeCollector(
            {
                "measured": [
                    {
                        "detail": {
                            "address_family": "ipv4",
                            "code": "network-measured-outbound-observed",
                            "local_endpoint_digest": digest("local"),
                            "phase": "measured",
                            "process_identity_digest": digest("process"),
                            "protocol": "tcp",
                            "remote_endpoint_digest": digest("remote"),
                        },
                        "kind": "outbound-connection",
                        "status": "FAIL",
                    }
                ]
            }
        )
        write = FakeCollector(
            {
                "measured": [
                    {
                        "detail": detail_for("write", "measured", "allowed-write"),
                        "kind": "allowed-write",
                        "status": "PASS",
                    },
                    {
                        "detail": {
                            **detail_for("write", "measured", "allowed-write"),
                            "code": "write-outside-allowed-root",
                        },
                        "kind": "denied-write",
                        "status": "FAIL",
                    },
                ]
            }
        )
        process_events = {
            phase: [
                {
                    "detail": detail_for("process", phase, "child-count"),
                    "kind": "child-count",
                    "status": "PASS",
                }
            ]
            for phase in PHASES
        }
        process_events["measured"].append(
            {
                "detail": {
                    "code": "process-unexpected-child",
                    "executable_digest": digest("exe"),
                    "parent_identity_digest": digest("parent"),
                    "phase": "measured",
                    "process_identity_digest": digest("child"),
                },
                "kind": "unexpected-child",
                "status": "FAIL",
            }
        )
        redaction = FakeCollector(
            {
                "redaction-and-seal": [
                    {
                        "detail": detail_for(
                            "redaction", "redaction-and-seal", "utf8-scan"
                        ),
                        "kind": "utf8-scan",
                        "status": "PASS",
                    },
                    {
                        "detail": {
                            "code": "redaction-sensitive-match",
                            "match_count": 1,
                            "path": "artifacts/result.json",
                            "pattern_id": "synthetic-pattern",
                            "phase": "redaction-and-seal",
                        },
                        "kind": "sensitive-match",
                        "status": "FAIL",
                    },
                ]
            }
        )
        result = observe.observe_synthetic(
            self.evidence,
            collectors(
                network=FakeCollector(
                    network.events,
                    coverage={
                        "complete": True,
                        "observer": "network",
                        "phases": PHASES,
                    },
                ),
                process=FakeCollector(
                    process_events,
                    coverage={
                        "complete": True,
                        "observer": "process",
                        "phases": PHASES,
                    },
                ),
                redaction=FakeCollector(
                    redaction.events,
                    coverage={
                        "complete": True,
                        "observer": "redaction",
                        "phases": PHASES,
                    },
                ),
                write=FakeCollector(
                    write.events,
                    coverage={
                        "complete": True,
                        "observer": "write",
                        "phases": PHASES,
                    },
                ),
            ),
            self.context,
        )
        self.assertFalse(result.passed)
        for observer in observe.OBSERVERS:
            records = observe.validate_ledger_bytes(observer, self.ledger(observer))
            for record in records:
                self.assertTrue(
                    valid_observer_detail(
                        observer,
                        record["kind"],
                        record["status"],
                        record["detail"],
                    )
                )
        self.assertEqual(result.observers["network"]["status"], "FAIL")
        self.assertEqual(result.observers["write"]["status"], "FAIL")
        self.assertEqual(result.observers["process"]["status"], "FAIL")
        self.assertEqual(result.observers["redaction"]["status"], "FAIL")


    def test_acquisition_outbound_pass_and_measured_outbound_fail(self) -> None:
        def outbound(phase: str, status: str, code: str) -> dict[str, object]:
            return {
                "detail": {
                    "address_family": "ipv4",
                    "code": code,
                    "local_endpoint_digest": digest(f"local:{phase}"),
                    "phase": phase,
                    "process_identity_digest": digest(f"process:{phase}"),
                    "protocol": "tcp",
                    "remote_endpoint_digest": digest(f"remote:{phase}"),
                },
                "kind": "outbound-connection",
                "status": status,
            }

        network = FakeCollector(
            {
                "acquisition": [outbound("acquisition", "PASS", "none")],
                "measured": [
                    outbound(
                        "measured",
                        "FAIL",
                        "network-measured-outbound-observed",
                    )
                ],
            },
            coverage={
                "complete": True,
                "observer": "network",
                "phases": PHASES,
            },
        )
        result = observe.observe_synthetic(
            self.evidence, collectors(network=network), self.context
        )
        records = observe.validate_ledger_bytes("network", self.ledger("network"))
        outbound_records = [
            record for record in records if record["kind"] == "outbound-connection"
        ]
        self.assertFalse(result.passed)
        phases_and_statuses = []
        for record in outbound_records:
            detail = record["detail"]
            self.assertIsInstance(detail, dict)
            assert isinstance(detail, dict)
            phases_and_statuses.append((detail["phase"], record["status"]))
        self.assertEqual(
            phases_and_statuses,
            [("acquisition", "PASS"), ("measured", "FAIL")],
        )
        invalid = dict(outbound_records[0])
        invalid_detail = invalid["detail"]
        self.assertIsInstance(invalid_detail, dict)
        assert isinstance(invalid_detail, dict)
        invalid["status"] = "PASS"
        invalid["detail"] = {**invalid_detail, "phase": "measured"}
        with self.assertRaises(observe.ObserverContractError):
            observe.seal_ledger(
                "network", [records[0], invalid, {**records[-1], "sequence": 2}]
            )

    def test_collector_event_phase_must_match_active_phase(self) -> None:
        mismatched = FakeCollector(
            {
                "acquisition": [
                    {
                        "detail": detail_for("write", "measured", "allowed-write"),
                        "kind": "allowed-write",
                        "status": "PASS",
                    }
                ]
            },
            coverage={
                "complete": True,
                "observer": "write",
                "phases": PHASES,
            },
        )
        result = observe.observe_synthetic(
            self.evidence, collectors(write=mismatched), self.context
        )
        records = observe.validate_ledger_bytes("write", self.ledger("write"))
        self.assertFalse(result.passed)
        self.assertEqual(result.errors, ("write:collector-event-invalid",))
        self.assertEqual(
            [record["kind"] for record in records],
            ["observer-start", "observer-stop"],
        )
        self.assertEqual(records[-1]["status"], "FAIL")

    def test_start_read_seal_and_stop_fail_closed_with_stable_codes(self) -> None:
        cases = (
            ("start", "collector-start-failed"),
            ("collect:measured", "collector-read-failed"),
            ("seal", "collector-seal-failed"),
            ("stop", "collector-stop-failed"),
            ("start+stop", "collector-start-failed"),
            ("collect:measured+stop", "collector-read-failed"),
            ("seal+stop", "collector-seal-failed"),
        )
        for index, (failure, code) in enumerate(cases):
            with self.subTest(failure=failure):
                evidence = self.evidence / f"case-{index}"
                evidence.mkdir()
                result = observe.observe_synthetic(
                    evidence,
                    collectors(network=FakeCollector(
                        fail=failure,
                        coverage={
                            "complete": True,
                            "observer": "network",
                            "phases": PHASES,
                        },
                    )),
                    self.context,
                )
                records = observe.validate_ledger_bytes(
                    "network", (evidence / "events/network.jsonl").read_bytes()
                )
                self.assertFalse(result.passed)
                self.assertEqual(result.errors, (f"network:{code}",))
                self.assertEqual(records[0]["kind"], "observer-start")
                self.assertEqual(records[-1]["kind"], "observer-stop")
                self.assertEqual(records[-1]["status"], "FAIL")
                stop_detail = records[-1]["detail"]
                self.assertIsInstance(stop_detail, dict)
                assert isinstance(stop_detail, dict)
                self.assertEqual(stop_detail["code"], code)
                persisted = (evidence / "events/network.jsonl").read_text("utf-8")
                self.assertNotIn("synthetic secret", persisted)
                self.assertNotIn("synthetic collector detail", persisted)

    def test_invalid_open_event_becomes_fail_closed_lifecycle(self) -> None:
        invalid = FakeCollector(
            {
                "measured": [
                    {
                        "detail": {
                            **detail_for("write", "measured", "allowed-write"),
                            "extra": "open-shape",
                        },
                        "kind": "allowed-write",
                        "status": "PASS",
                    }
                ]
            }
        )
        invalid.coverage_receipt = {
            "complete": True,
            "observer": "write",
            "phases": PHASES,
        }
        result = observe.observe_synthetic(
            self.evidence, collectors(write=invalid), self.context
        )
        records = observe.validate_ledger_bytes("write", self.ledger("write"))
        self.assertFalse(result.passed)
        self.assertEqual(result.errors, ("write:collector-event-invalid",))
        self.assertEqual([item["kind"] for item in records], ["observer-start", "observer-stop"])
        self.assertEqual(records[-1]["status"], "FAIL")

    def test_process_phase_coverage_and_redaction_file_coverage_fail_closed(self) -> None:
        process_events = {
            phase: [
                {
                    "detail": detail_for("process", phase, "child-count"),
                    "kind": "child-count",
                    "status": "PASS",
                }
            ]
            for phase in PHASES
            if phase != "cleanup"
        }
        context = observe.SyntheticObserverContext(
            **{
                **self.context.__dict__,
                "expected_redaction_paths": (
                    "artifacts/result.json",
                    "events/network.jsonl",
                ),
            }
        )
        redaction = FakeCollector(
            {
                "redaction-and-seal": [
                    {
                        "detail": detail_for(
                            "redaction", "redaction-and-seal", "utf8-scan"
                        ),
                        "kind": "utf8-scan",
                        "status": "PASS",
                    }
                ]
            }
        )
        result = observe.observe_synthetic(
            self.evidence,
            collectors(
                process=FakeCollector(
                    process_events,
                    coverage={
                        "complete": True,
                        "observer": "process",
                        "phases": PHASES,
                    },
                ),
                redaction=FakeCollector(
                    redaction.events,
                    coverage={
                        "complete": True,
                        "observer": "redaction",
                        "phases": PHASES,
                    },
                ),
            ),
            context,
        )
        self.assertFalse(result.passed)
        self.assertEqual(
            result.errors,
            (
                "process:collector-coverage-failed",
                "redaction:collector-coverage-failed",
            ),
        )
        self.assertEqual(result.observers["process"]["status"], "FAIL")
        self.assertEqual(result.observers["redaction"]["status"], "FAIL")

    def test_process_coverage_requires_exactly_one_count_per_phase_in_order(
        self,
    ) -> None:
        duplicate = {
            phase: [
                {
                    "detail": detail_for("process", phase, "child-count"),
                    "kind": "child-count",
                    "status": "PASS",
                }
            ]
            for phase in PHASES
        }
        duplicate["measured"].append(
            {
                "detail": detail_for("process", "measured", "child-count"),
                "kind": "child-count",
                "status": "PASS",
            }
        )
        process = FakeCollector(
            duplicate,
            coverage={
                "complete": True,
                "observer": "process",
                "phases": PHASES,
            },
        )
        result = observe.observe_synthetic(
            self.evidence,
            collectors(process=process),
            self.context,
        )
        self.assertFalse(result.passed)
        self.assertEqual(
            result.errors,
            ("process:collector-coverage-failed",),
        )
        process_events = observe.validate_ledger_bytes(
            "process", self.ledger("process")
        )
        count_phases = [
            detail["phase"]
            for event in process_events
            if event["kind"] == "child-count"
            and isinstance((detail := event["detail"]), dict)
        ]
        self.assertEqual(
            count_phases,
            [*PHASES[:3], "measured", *PHASES[3:]],
        )
        self.assertEqual(process_events[-1]["status"], "FAIL")

    def test_explicit_coverage_receipts_fail_closed_for_all_observers(self) -> None:
        class NonMappingCoverageCollector(FakeCollector):
            def coverage(self) -> Mapping[str, object]:
                self.calls.append("coverage")
                return cast(Mapping[str, object], ("not", "an", "object"))

        cases = (
            ("network-missing", "network", FakeCollector()),
            (
                "network-open-shape",
                "network",
                FakeCollector(
                    coverage={
                        "complete": True,
                        "observer": "network",
                        "phases": PHASES,
                        "unexpected": True,
                    }
                ),
            ),
            (
                "network-non-mapping",
                "network",
                NonMappingCoverageCollector(),
            ),
            (
                "network-exception",
                "network",
                FakeCollector(coverage_failure=True),
            ),
            (
                "write-wrong-observer",
                "write",
                FakeCollector(
                    coverage={
                        "complete": True,
                        "observer": "network",
                        "phases": PHASES,
                    }
                ),
            ),
            (
                "redaction-incomplete-phases",
                "redaction",
                FakeCollector(
                    coverage={
                        "complete": True,
                        "observer": "redaction",
                        "phases": PHASES[:-1],
                    }
                ),
            ),
            (
                "redaction-reordered-phases",
                "redaction",
                FakeCollector(
                    coverage={
                        "complete": True,
                        "observer": "redaction",
                        "phases": tuple(reversed(PHASES)),
                    }
                ),
            ),
            (
                "redaction-duplicate-phases",
                "redaction",
                FakeCollector(
                    coverage={
                        "complete": True,
                        "observer": "redaction",
                        "phases": PHASES[:-1] + (PHASES[-2],),
                    }
                ),
            ),
            (
                "process-incomplete",
                "process",
                FakeCollector(
                    coverage={
                        "complete": False,
                        "observer": "process",
                        "phases": PHASES,
                    }
                ),
            ),
        )
        for index, (name, observer, collector) in enumerate(cases):
            with self.subTest(name=name, observer=observer):
                evidence = self.evidence / f"coverage-{index}"
                evidence.mkdir()
                supplied = collectors(**{observer: collector})
                result = observe.observe_synthetic(evidence, supplied, self.context)
                self.assertFalse(result.passed)
                self.assertIn(
                    f"{observer}:collector-coverage-failed",
                    result.errors,
                )
                records = observe.validate_ledger_bytes(
                    observer, (evidence / f"events/{observer}.jsonl").read_bytes()
                )
                self.assertEqual(records[-1]["status"], "FAIL")
                stop_detail = records[-1]["detail"]
                self.assertIsInstance(stop_detail, dict)
                assert isinstance(stop_detail, dict)
                self.assertEqual(
                    stop_detail["code"],
                    "collector-coverage-failed",
                )

    def test_empty_redaction_expectation_still_requires_explicit_receipt(self) -> None:
        result = observe.observe_synthetic(
            self.evidence,
            collectors(redaction=FakeCollector()),
            self.context,
        )
        self.assertFalse(result.passed)
        self.assertEqual(
            result.errors,
            ("redaction:collector-coverage-failed",),
        )

    def test_canonical_jsonl_rejects_missing_lf_crlf_noncanonical_and_sequence(self) -> None:
        data, _ = observe.seal_ledger(
            "network",
            [
                observe._event(
                    "network",
                    "observer-start",
                    0,
                    "PASS",
                    observe._lifecycle_detail(
                        "network", "observer-bootstrap", "none", self.context
                    ),
                ),
                observe._event(
                    "network",
                    "observer-stop",
                    1,
                    "PASS",
                    observe._lifecycle_detail(
                        "network", "observer-finalize", "none", self.context
                    ),
                ),
            ],
        )
        mutations = [
            data[:-1],
            data.replace(b"\n", b"\r\n"),
            data.replace(b'"detail":', b'"detail" :', 1),
            data.replace(b'"sequence":1', b'"sequence":2', 1),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation[:40]):
                with self.assertRaises(observe.ObserverContractError):
                    observe.validate_ledger_bytes("network", mutation)


    def test_ledger_rejects_boolean_sequence_and_invalid_lifecycle(self) -> None:
        start = observe._event(
            "network",
            "observer-start",
            0,
            "PASS",
            observe._lifecycle_detail(
                "network", "observer-bootstrap", "none", self.context
            ),
        )
        stop = observe._event(
            "network",
            "observer-stop",
            1,
            "PASS",
            observe._lifecycle_detail(
                "network", "observer-finalize", "none", self.context
            ),
        )
        mutations = [
            [{**start, "sequence": False}, stop],
            [start, {**start, "sequence": 1}, {**stop, "sequence": 2}],
            [start, {**stop, "sequence": 1}, {**stop, "sequence": 2}],
        ]
        for events in mutations:
            with self.subTest(kinds=[event["kind"] for event in events]):
                data = b"".join(observe.canonical(event) for event in events)
                with self.assertRaises(observe.ObserverContractError):
                    observe.validate_ledger_bytes("network", data)

    def test_lifecycle_phase_and_success_code_are_closed(self) -> None:
        valid_start = observe._lifecycle_detail(
            "network", "observer-bootstrap", "none", self.context
        )
        valid_stop = observe._lifecycle_detail(
            "network", "observer-finalize", "none", self.context
        )
        cases = [
            (
                "observer-start",
                "PASS",
                {**valid_start, "phase": "measured"},
            ),
            (
                "observer-stop",
                "PASS",
                {**valid_stop, "phase": "cleanup"},
            ),
            (
                "observer-start",
                "PASS",
                {**valid_start, "code": "collector-startup-failed"},
            ),
        ]
        for kind, status, detail in cases:
            with self.subTest(kind=kind, detail=detail):
                self.assertFalse(
                    valid_observer_detail("network", kind, status, detail)
                )

    def test_redaction_paths_must_be_canonical_relative(self) -> None:
        invalid_paths = (
            ".",
            "./x",
            "a//b",
            "a/",
            "C:foo",
            "file:stream",
            "/absolute",
            "a\\b",
            "../x",
        )
        for path in invalid_paths:
            with self.subTest(path=path):
                detail = {
                    **detail_for("redaction", "redaction-and-seal", "utf8-scan"),
                    "path": path,
                }
                self.assertFalse(
                    valid_observer_detail(
                        "redaction", "utf8-scan", "PASS", detail
                    )
                )
                context = replace(
                    observe.synthetic_context(),
                    expected_redaction_paths=(path,),
                )
                with self.assertRaises(observe.ObserverContractError):
                    context.validate()

    def test_summary_counts_binary_utf8_bytes_not_characters(self) -> None:
        redaction = FakeCollector(
            {
                "redaction-and-seal": [
                    {
                        "detail": {
                            "byte_count": 3,
                            "code": "none",
                            "path": "artifacts/结果.json",
                            "phase": "redaction-and-seal",
                            "sha256": digest("unicode"),
                        },
                        "kind": "utf8-scan",
                        "status": "PASS",
                    }
                ]
            }
        )
        result = observe.observe_synthetic(
            self.evidence, collectors(redaction=redaction), self.context
        )
        data = self.ledger("redaction")
        self.assertGreater(len(data), len(data.decode("utf-8")))
        self.assertEqual(result.observers["redaction"]["byte_count"], len(data))

    def test_publication_is_fail_closed_and_never_overwrites_existing_events(self) -> None:
        existing = self.evidence / "events"
        existing.mkdir()
        marker = existing / "marker.txt"
        marker.write_bytes(b"preserve")
        with self.assertRaises(observe.ObserverPublicationError):
            observe.observe_synthetic(self.evidence, collectors(), self.context)
        self.assertEqual(marker.read_bytes(), b"preserve")
        self.assertEqual(sorted(path.name for path in existing.iterdir()), ["marker.txt"])

    @unittest.skipUnless(os.name == "nt", "Windows junction semantics")
    def test_publication_rejects_junction_in_evidence_ancestor(self) -> None:
        parent = self.evidence / "junction-parent"
        external = self.evidence / "external-parent"
        evidence = parent / "evidence"
        external.mkdir()
        created = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(parent), str(external)],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(
            created.returncode,
            0,
            created.stdout + created.stderr,
        )
        evidence.mkdir()
        try:
            with self.assertRaises(observe.ObserverPublicationError):
                observe.observe_synthetic(evidence, collectors(), self.context)
            self.assertEqual(list(evidence.iterdir()), [])
        finally:
            shutil.rmtree(parent, ignore_errors=True)
            shutil.rmtree(external, ignore_errors=True)

    def test_publication_failure_removes_staging_and_publishes_no_partial_set(self) -> None:
        original_replace = observe.os.replace

        def fail_replace(source: object, destination: object) -> None:
            raise OSError("synthetic publish failure")

        with mock.patch.object(observe.os, "replace", side_effect=fail_replace):
            with self.assertRaises(observe.ObserverPublicationError):
                observe.observe_synthetic(self.evidence, collectors(), self.context)
        self.assertFalse((self.evidence / "events").exists())
        self.assertEqual(list(self.evidence.iterdir()), [])
        self.assertIsNotNone(original_replace)

    def test_missing_collector_and_non_synthetic_context_are_rejected_before_write(self) -> None:
        missing = collectors()
        del missing["network"]
        with self.assertRaises(observe.ObserverContractError):
            observe.observe_synthetic(self.evidence, missing, self.context)
        unauthorized = observe.SyntheticObserverContext(
            **{**self.context.__dict__, "authorization_state": "S1_AUTHORIZED"}
        )
        with self.assertRaises(observe.ObserverContractError):
            observe.observe_synthetic(self.evidence, collectors(), unauthorized)
        self.assertFalse((self.evidence / "events").exists())

    def test_no_real_io_or_authorization_entry_point_exists(self) -> None:
        forbidden = {
            "socket",
            "subprocess",
            "ctypes",
            "psutil",
            "requests",
            "urllib",
            "sqlite3",
            "lancedb",
        }
        source = Path(observe.__file__).read_text("utf-8")
        for name in forbidden:
            self.assertNotIn(f"import {name}", source)
            self.assertNotIn(f"from {name}", source)
        public = {name for name in dir(observe) if not name.startswith("_")}
        self.assertFalse(any("authorize" in name.lower() or "backend" in name.lower() for name in public))


if __name__ == "__main__":
    unittest.main(verbosity=2)
