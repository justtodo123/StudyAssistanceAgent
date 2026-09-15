#!/usr/bin/env python3
"""Validate a persistent M8 v3 artifact directory.

Exit 0 means the directory is either a valid success graph or a valid,
fail-closed failure graph. Invalid or internally inconsistent graphs exit 1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/plans/references/schemas/m8-minimal-1k-artifacts-v3.schema.json"
PROTOCOL_PATH = ROOT / "docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md"
ROLE_SCHEMA = {
    "identity": "sa.m8.minimal.experiment-identity.v3",
    "input-manifest": "sa.m8.minimal.input-manifest.v3",
    "run-report": "sa.m8.minimal.run-report.v3",
    "validation-report": "sa.m8.minimal.validation-report.v3",
    "cleanup-receipt": "sa.m8.minimal.cleanup-receipt.v3",
    "s0": "sa.m8.minimal.decision-record.v3",
    "s1": "sa.m8.minimal.decision-record.v3",
    "s2": "sa.m8.minimal.decision-record.v3",
    "s3": "sa.m8.minimal.decision-record.v3",
}
GATE_MAP = {
    "S0": {"role": "s0", "actor": "independent-reviewer", "pairs": {("PROTOCOL_ACCEPTED", "request-s1"), ("PROTOCOL_REJECTED", "stop")}},
    "S1": {"role": "s1", "actor": "owner", "pairs": {("DRY_RUN_AUTHORIZED", "run-s2"), ("NOT_AUTHORIZED", "stop")}},
    "S2": {"role": "s2", "actor": "executor", "pairs": {("EVIDENCE_READY", "request-s3"), ("DRY_RUN_FAILED", "stop")}},
    "S3": {"role": "s3", "actor": "independent-reviewer", "pairs": {("ACCEPT_1K_EVIDENCE", "stop"), ("REJECT_1K_EVIDENCE", "stop")}},
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def jsonl_count(data: bytes) -> int:
    if not data or not data.endswith(b"\n"):
        raise ValueError("JSONL must be non-empty and LF terminated")
    lines = data.splitlines()
    for line in lines:
        obj = json.loads(line)
        if line + b"\n" != canonical(obj):
            raise ValueError("JSONL line is not canonical JSON")
    return len(lines)



class Validator:
    def __init__(self, graph_dir: Path):
        self.root = graph_dir.resolve()
        self.artifact_dir = self.root / "artifacts"
        self.errors: list[str] = []
        self.objects: dict[str, dict] = {}
        self.paths: dict[str, Path] = {}

    def check(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def safe_path(self, relative: str) -> Path:
        self.check("\\" not in relative and not relative.startswith("/") and ".." not in Path(relative).parts, f"unsafe relative path: {relative}")
        target = (self.root / relative).resolve()
        self.check(target == self.root or self.root in target.parents, f"path escapes graph: {relative}")
        return target

    def load_artifacts(self) -> None:
        expected = set(ROLE_SCHEMA)
        found = {path.stem for path in self.artifact_dir.glob("*.json")}
        self.check(found == expected, f"artifact role set mismatch: {sorted(found)}")
        for role in sorted(expected & found):
            path = self.artifact_dir / f"{role}.json"
            data = path.read_bytes()
            try:
                obj = json.loads(data)
            except Exception as exc:
                self.errors.append(f"{role}: invalid JSON: {exc}")
                continue
            self.check(data == canonical(obj), f"{role}: not canonical JSON")
            self.check(set(obj) == {"canonicalization_id", "logical_name", "payload", "schema_id", "schema_version"}, f"{role}: envelope keys")
            self.check(obj.get("canonicalization_id") == "sa-json-c14n-v1", f"{role}: canonicalization")
            self.check(obj.get("schema_version") == 3, f"{role}: schema version")
            self.check(obj.get("schema_id") == ROLE_SCHEMA[role], f"{role}: schema role mismatch")
            payload = obj.get("payload", {})
            exp = payload.get("experiment_id")
            self.check(isinstance(exp, str) and bool(re.fullmatch(r"[a-z0-9-]+", exp)), f"{role}: experiment id")
            self.check(obj.get("logical_name") == f"minimal-1k/{exp}/{role}.json", f"{role}: logical name")
            self.objects[role] = obj
            self.paths[role] = path

    def verify_ref(self, ref: dict, expected_role: str) -> None:
        self.check(set(ref) == {"logical_name", "role", "schema_id", "sha256", "byte_count"}, f"{expected_role}: ref keys")
        self.check(ref.get("role") == expected_role, f"{expected_role}: ref role")
        target = self.objects.get(expected_role)
        path = self.paths.get(expected_role)
        if not target or not path:
            self.errors.append(f"{expected_role}: missing ref target")
            return
        data = path.read_bytes()
        self.check(ref.get("logical_name") == target["logical_name"], f"{expected_role}: ref logical name")
        self.check(ref.get("schema_id") == target["schema_id"], f"{expected_role}: ref schema id")
        self.check(ref.get("sha256") == sha(data), f"{expected_role}: ref digest")
        self.check(ref.get("byte_count") == len(data), f"{expected_role}: ref byte count")

    def validate_identity(self) -> None:
        p = self.objects["identity"]["payload"]
        required = {"backends", "chunk_count", "dimension", "dtype", "experiment_id", "generator_algorithm", "normalization", "protocol_sha256", "seed", "synthetic_only", "top_k"}
        self.check(set(p) == required, "identity: payload keys")
        self.check(p.get("backends") == ["sqlite-linear-exact", "lancedb-embedded-exact-flat"], "identity: backends")
        self.check((p.get("chunk_count"), p.get("dimension"), p.get("dtype"), p.get("normalization")) == (1000, 512, "float32", "l2"), "identity: workload shape")
        self.check(p.get("seed") == 20260914 and p.get("top_k") == [1, 3, 5], "identity: deterministic constants")
        self.check(p.get("generator_algorithm") == "sa-m8-synthetic-unit-v3" and p.get("synthetic_only") is True, "identity: synthetic algorithm")
        protocol_digest = p.get("protocol_sha256")
        self.check(isinstance(protocol_digest, str) and bool(HEX64.fullmatch(protocol_digest)), "identity: protocol digest format")
        self.check(PROTOCOL_PATH.is_file(), "identity: protocol file missing")
        if PROTOCOL_PATH.is_file():
            self.check(protocol_digest == sha(PROTOCOL_PATH.read_bytes()), "identity: protocol digest bytes")

    def validate_manifest(self) -> None:
        p = self.objects["input-manifest"]["payload"]
        self.check(set(p) == {"experiment_id", "identity_ref", "members", "synthetic_fixture_only"}, "manifest: payload keys")
        self.verify_ref(p.get("identity_ref", {}), "identity")
        members = p.get("members", [])
        expected_paths = ["input/chunks.jsonl", "input/gold.jsonl", "input/queries.jsonl", "input/vectors.bin"]
        self.check([item.get("path") for item in members] == expected_paths, "manifest: exact sorted members")
        for item in members:
            self.check(set(item) == {"path", "sha256", "byte_count", "record_count"}, "manifest: member keys")
            path = self.safe_path(item.get("path", ""))
            self.check(path.is_file(), f"manifest: missing {item.get('path')}")
            if not path.is_file():
                continue
            data = path.read_bytes()
            self.check(item.get("sha256") == sha(data), f"manifest: digest {item.get('path')}")
            self.check(item.get("byte_count") == len(data), f"manifest: bytes {item.get('path')}")
            count = jsonl_count(data) if path.suffix == ".jsonl" else item.get("record_count")
            self.check(item.get("record_count") == count, f"manifest: records {item.get('path')}")

    def validate_events_and_run(self) -> bool:
        p = self.objects["run-report"]["payload"]
        required = {"backend_results", "experiment_id", "input_manifest_ref", "observers", "runtime_errors", "status"}
        self.check(set(p) == required, "run: payload keys")
        self.verify_ref(p.get("input_manifest_ref", {}), "input-manifest")
        backends = p.get("backend_results")
        self.check(backends == [
            {"backend": "sqlite-linear-exact", "mode": "linear-exact", "status": p.get("status")},
            {"backend": "lancedb-embedded-exact-flat", "mode": "embedded-exact-flat-no-ann", "status": p.get("status")},
        ], "run: backend modes and shared status")
        self.check(p.get("status") in {"PASS", "FAIL"}, "run: status")
        self.check((p.get("status") == "PASS") == (p.get("runtime_errors") == []), "run: errors/status")
        observers = p.get("observers", {})
        self.check(set(observers) == {"network", "write", "process", "redaction"}, "run: observer set")
        all_observers_pass = True
        allowed_kinds = {
            "network": {"observer-start", "observer-stop", "outbound-connection"},
            "write": {"observer-start", "observer-stop", "allowed-write", "denied-write"},
            "process": {"observer-start", "observer-stop", "child-count", "unexpected-child"},
            "redaction": {"observer-start", "observer-stop", "utf8-scan", "sensitive-match"},
        }
        for name, summary in observers.items():
            self.check(set(summary) == {"path", "sha256", "byte_count", "event_count", "status"}, f"observer {name}: summary keys")
            path = self.safe_path(summary.get("path", ""))
            self.check(path == self.root / f"events/{name}.jsonl", f"observer {name}: path")
            if not path.is_file():
                self.errors.append(f"observer {name}: missing ledger")
                continue
            data = path.read_bytes()
            self.check(summary.get("sha256") == sha(data), f"observer {name}: digest")
            self.check(summary.get("byte_count") == len(data), f"observer {name}: bytes")
            try:
                events = []
                for line in data.splitlines():
                    item = json.loads(line)
                    self.check(line + b"\n" == canonical(item), f"observer {name}: non-canonical JSONL line")
                    events.append(item)
            except Exception as exc:
                self.errors.append(f"observer {name}: invalid JSONL {exc}")
                continue
            self.check(summary.get("event_count") == len(events), f"observer {name}: count")
            self.check([item.get("sequence") for item in events] == list(range(len(events))), f"observer {name}: sequence")
            for item in events:
                self.check(set(item) == {"detail", "kind", "sequence", "status"}, f"observer {name}: event keys")
                self.check(item.get("kind") in allowed_kinds[name], f"observer {name}: event kind")
                self.check(item.get("status") in {"PASS", "FAIL"}, f"observer {name}: event status")
            self.check(events and events[0].get("kind") == "observer-start" and events[-1].get("kind") == "observer-stop", f"observer {name}: lifecycle")
            computed = "FAIL" if any(item.get("status") == "FAIL" for item in events) else "PASS"
            self.check(summary.get("status") == computed, f"observer {name}: aggregate status")
            all_observers_pass &= computed == "PASS"
        return all_observers_pass

    def validate_cleanup_validation(self, observers_pass: bool) -> tuple[bool, bool]:
        cleanup = self.objects["cleanup-receipt"]["payload"]
        self.check(set(cleanup) == {"after_count", "experiment_id", "failure_code", "status", "temporary_root_exists"}, "cleanup: payload keys")
        cleaned = cleanup.get("status") == "CLEANED"
        self.check(cleanup.get("status") in {"CLEANED", "FAIL"}, "cleanup: status")
        self.check(cleaned == (cleanup.get("after_count") == 0 and cleanup.get("temporary_root_exists") is False and cleanup.get("failure_code") == "none"), "cleanup: status facts")
        validation = self.objects["validation-report"]["payload"]
        self.check(set(validation) == {"checks", "cleanup_receipt_ref", "experiment_id", "run_report_ref", "verdict"}, "validation: payload keys")
        self.verify_ref(validation.get("cleanup_receipt_ref", {}), "cleanup-receipt")
        self.verify_ref(validation.get("run_report_ref", {}), "run-report")
        checks = validation.get("checks", {})
        self.check(set(checks) == {"cleanup", "observer", "runtime", "same_input"}, "validation: check set")
        run_pass = self.objects["run-report"]["payload"].get("status") == "PASS"
        self.check(checks.get("cleanup") == cleaned, "validation: cleanup check")
        self.check(checks.get("observer") == observers_pass, "validation: observer check")
        self.check(checks.get("runtime") == run_pass, "validation: runtime check")
        computed_pass = all(value is True for value in checks.values())
        self.check(validation.get("verdict") == ("PASS" if computed_pass else "FAIL"), "validation: verdict")
        return cleaned, computed_pass

    def validate_gates(self, cleaned: bool, validation_pass: bool) -> None:
        for gate_id, spec in GATE_MAP.items():
            role = spec["role"]
            p = self.objects[role]["payload"]
            self.check(set(p) == {"actor_role", "allowed_next_action", "decision", "experiment_id", "gate_id", "read_refs"}, f"{role}: payload keys")
            self.check(p.get("gate_id") == gate_id and p.get("actor_role") == spec["actor"], f"{role}: gate actor mapping")
            self.check((p.get("decision"), p.get("allowed_next_action")) in spec["pairs"], f"{role}: decision/action mapping")
        s0 = self.objects["s0"]["payload"]
        self.check(s0.get("read_refs") == [], "s0: predecessor refs must be empty")
        refs = self.objects["s1"]["payload"].get("read_refs", [])
        self.check(len(refs) == 1, "s1: predecessor count")
        if refs:
            self.verify_ref(refs[0], "s0")
        s1 = self.objects["s1"]["payload"]
        s0_accepted = s0.get("decision") == "PROTOCOL_ACCEPTED"
        self.check((s1.get("decision") == "DRY_RUN_AUTHORIZED") == s0_accepted, "s1: predecessor authority")
        refs = self.objects["s2"]["payload"].get("read_refs", [])
        expected_roles = ["s1", "run-report", "cleanup-receipt", "validation-report"]
        self.check([ref.get("role") for ref in refs] == expected_roles, "s2: authority refs")
        for ref, role in zip(refs, expected_roles): self.verify_ref(ref, role)
        s2 = self.objects["s2"]["payload"]
        should_ready = s1.get("decision") == "DRY_RUN_AUTHORIZED" and cleaned and validation_pass
        self.check((s2.get("decision") == "EVIDENCE_READY") == should_ready, "s2: evidence authority")
        refs = self.objects["s3"]["payload"].get("read_refs", [])
        self.check(len(refs) == 1, "s3: predecessor count")
        if refs: self.verify_ref(refs[0], "s2")
        s3 = self.objects["s3"]["payload"]
        self.check((s3.get("decision") == "ACCEPT_1K_EVIDENCE") == should_ready, "s3: evidence outcome")

    def validate_experiment_consistency(self) -> None:
        ids = {obj["payload"].get("experiment_id") for obj in self.objects.values()}
        self.check(len(ids) == 1, "graph: experiment IDs differ")

    def run(self) -> bool:
        self.check(SCHEMA_PATH.is_file(), "schema file missing")
        self.load_artifacts()
        if set(self.objects) != set(ROLE_SCHEMA):
            return False
        self.validate_experiment_consistency()
        self.validate_identity()
        self.validate_manifest()
        observers_pass = self.validate_events_and_run()
        cleaned, validation_pass = self.validate_cleanup_validation(observers_pass)
        self.validate_gates(cleaned, validation_pass)
        return not self.errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph_dir", type=Path)
    args = parser.parse_args()
    validator = Validator(args.graph_dir)
    ok = validator.run()
    if ok:
        outcome = validator.objects["validation-report"]["payload"]["verdict"]
        print(f"VALID_GRAPH verdict={outcome} path={args.graph_dir}")
        return 0
    for error in validator.errors:
        print(f"FAIL {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
