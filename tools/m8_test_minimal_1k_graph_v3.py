#!/usr/bin/env python3
"""Run persistent positive/failure fixtures and fail-closed mutations for M8 v3."""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools/m8_generate_minimal_1k_v3_fixtures.py"
VALIDATOR = ROOT / "tools/m8_validate_minimal_1k_graph_v3.py"
COMMITTED_FIXTURES = (
    ROOT
    / "docs/plans/references/fixtures/m8-minimal-1k-v3"
)

from m8_validate_minimal_1k_graph_v3 import reject_duplicate_pairs


def run(
    path: Path,
    validator: Path = VALIDATOR,
) -> subprocess.CompletedProcess[str]:
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.upper().startswith("PYTHON")
    }
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(validator), str(path)],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        check=False,
        timeout=30,
    )


def reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def load(path: Path) -> dict:
    value = json.loads(
        path.read_bytes(),
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_pairs,
    )
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def canonical_json(obj: object) -> bytes:
    return (
        json.dumps(
            obj,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def save(path: Path, obj: dict) -> None:
    path.write_bytes(canonical_json(obj))


def mutate_json(relative: str, change):
    def apply(root: Path) -> None:
        path = root / relative
        obj = load(path)
        change(obj)
        save(path, obj)
    return apply


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def fail_lines(result: subprocess.CompletedProcess[str]) -> list[str]:
    """Return validator diagnostics and reject uncontrolled exceptions."""
    output = result.stdout + result.stderr
    check("traceback" not in output.lower(), f"validator traceback: {output}")
    check(
        "internal validator error:" not in output,
        f"validator internal error: {output}",
    )
    return [line for line in output.splitlines() if line.startswith("FAIL ")]


def exact_failure(
    result: subprocess.CompletedProcess[str],
    expected: list[str] | tuple[str, ...],
) -> bool:
    """Require a controlled failure with exactly the causal diagnostics."""
    try:
        actual = fail_lines(result)
    except AssertionError:
        return False
    return result.returncode != 0 and actual == list(expected)


@dataclass(frozen=True)
class MutationSpec:
    """Describe one mutation and its required causal oracle."""

    name: str
    mutation: Callable[[Path], object]
    source: str = "success"
    semantic: bool = False
    expected_failures: tuple[str, ...] = ()


def mutation_result(
    spec: MutationSpec,
    result: subprocess.CompletedProcess[str],
) -> bool:
    """Require exact diagnostics for semantic mutations and causal prefixes otherwise."""
    if spec.semantic:
        return exact_failure(result, spec.expected_failures)
    output = result.stdout + result.stderr
    if result.returncode == 0 or "traceback" in output.lower():
        return False
    if "internal validator error:" in output:
        return False
    actual = fail_lines(result)
    return all(
        any(line.startswith(expected) for line in actual)
        for expected in spec.expected_failures
    )


def junction_regression(
    source: Path,
    mutation_root: Path,
) -> tuple[bool, str]:
    """Prove Windows directory junctions are rejected before traversal."""
    if os.name != "nt":
        return True, "unsupported platform"
    target = mutation_root / "junction-artifacts"
    external = mutation_root / "external-artifacts"
    shutil.copytree(source, target)
    artifacts = target / "artifacts"
    shutil.copytree(artifacts, external)
    shutil.rmtree(artifacts)
    created = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(artifacts), str(external)],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=30,
    )
    if created.returncode != 0:
        return False, f"junction creation failed: {created.stdout}{created.stderr}"
    marker = external / "external-read-marker.json"
    marker.write_bytes(b"not-json\n")
    expectation = target / "expectation.json"
    expectation_obj = load(expectation)
    expectation_obj["graph"] = target.name
    save(expectation, expectation_obj)
    result = run(target)
    output = result.stdout + result.stderr
    ok = (
        result.returncode != 0
        and "FAIL graph inventory non-regular member: artifacts" in output
        and "external-read-marker" not in output
        and "internal validator error:" not in output
        and "traceback" not in output.lower()
    )
    return ok, output


def file_ref(role: str, path: Path) -> dict:
    data = path.read_bytes()
    obj = load(path)
    logical_name = obj.get("logical_name")
    actual_role = (
        logical_name.rsplit("/", 1)[-1].removesuffix(".json")
        if isinstance(logical_name, str)
        else None
    )
    check(actual_role == role, f"{path}: expected role {role!r}, got {actual_role!r}")
    return {
        "logical_name": logical_name,
        "role": actual_role,
        "schema_id": obj["schema_id"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
    }


def artifact_ref(role: str, path: Path) -> dict:
    """Build a typed REF from the current artifact bytes without inferring its role."""
    data = path.read_bytes()
    obj = load(path)
    return {
        "logical_name": obj.get("logical_name"),
        "role": role,
        "schema_id": obj.get("schema_id"),
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
    }


def reseal_artifact_refs(root: Path) -> None:
    """Rebind the complete transitive artifact REF chain after a semantic edit."""
    artifacts = root / "artifacts"
    identity_path = artifacts / "identity.json"
    manifest_path = artifacts / "input-manifest.json"
    run_path = artifacts / "run-report.json"
    cleanup_path = artifacts / "cleanup-receipt.json"
    validation_path = artifacts / "validation-report.json"
    s0_path = artifacts / "s0.json"
    s1_path = artifacts / "s1.json"
    s2_path = artifacts / "s2.json"
    s3_path = artifacts / "s3.json"

    manifest = load(manifest_path)
    manifest["payload"]["identity_ref"] = artifact_ref("identity", identity_path)
    save(manifest_path, manifest)

    run = load(run_path)
    run["payload"]["input_manifest_ref"] = artifact_ref(
        "input-manifest", manifest_path
    )
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    for result in run["payload"]["backend_results"]:
        result["input_manifest_sha256"] = manifest_digest
    save(run_path, run)

    validation = load(validation_path)
    validation["payload"]["run_report_ref"] = artifact_ref("run-report", run_path)
    validation["payload"]["cleanup_receipt_ref"] = artifact_ref(
        "cleanup-receipt", cleanup_path
    )
    save(validation_path, validation)

    s1 = load(s1_path)
    s1["payload"]["read_refs"] = [artifact_ref("s0", s0_path)]
    save(s1_path, s1)

    s2 = load(s2_path)
    s2["payload"]["read_refs"] = [
        artifact_ref("s1", s1_path),
        artifact_ref("run-report", run_path),
        artifact_ref("cleanup-receipt", cleanup_path),
        artifact_ref("validation-report", validation_path),
    ]
    save(s2_path, s2)

    s3 = load(s3_path)
    s3["payload"]["read_refs"] = [artifact_ref("s2", s2_path)]
    save(s3_path, s3)

    for path in (
        identity_path,
        manifest_path,
        run_path,
        cleanup_path,
        validation_path,
        s0_path,
        s1_path,
        s2_path,
        s3_path,
    ):
        assert_canonical_json(path)


def reseal_input_chain(root: Path, relative: str) -> None:
    """Rebind input metadata and every downstream REF after an input edit."""
    input_path = root / relative
    data = input_path.read_bytes()
    manifest_path = root / "artifacts/input-manifest.json"
    manifest = load(manifest_path)
    matching = [
        member
        for member in manifest["payload"]["members"]
        if member.get("path") == relative
    ]
    check(len(matching) == 1, f"manifest member cannot be safely resealed: {relative}")
    member = matching[0]
    member["sha256"] = hashlib.sha256(data).hexdigest()
    member["byte_count"] = len(data)
    if relative.endswith(".jsonl"):
        check(bool(data) and data.endswith(b"\n"), f"invalid JSONL boundary: {relative}")
        member["record_count"] = len(data[:-1].split(b"\n"))
    save(manifest_path, manifest)
    reseal_artifact_refs(root)

    run_path = root / "artifacts/run-report.json"
    validation_path = root / "artifacts/validation-report.json"
    s2_path = root / "artifacts/s2.json"
    s3_path = root / "artifacts/s3.json"
    manifest_ref = file_ref("input-manifest", manifest_path)
    run = load(run_path)
    check(
        run["payload"]["input_manifest_ref"] == manifest_ref,
        "resealed input-manifest reference differs",
    )
    for index, result in enumerate(run["payload"]["backend_results"]):
        check(
            result["input_manifest_sha256"] == manifest_ref["sha256"],
            f"resealed backend {index} input digest differs",
        )
    check(
        load(validation_path)["payload"]["run_report_ref"]
        == file_ref("run-report", run_path),
        "resealed validation run-report reference differs",
    )
    s2_refs = load(s2_path)["payload"]["read_refs"]
    check(
        s2_refs[1] == file_ref("run-report", run_path)
        and s2_refs[3] == file_ref("validation-report", validation_path),
        "resealed s2 references differ",
    )
    check(
        load(s3_path)["payload"]["read_refs"] == [file_ref("s2", s2_path)],
        "resealed s3 reference differs",
    )


def make_noncanonical_input(root: Path) -> None:
    """Change only the JSON encoding of chunks and reseal its evidence chain."""
    path = root / "input/chunks.jsonl"
    original = path.read_bytes()
    check(bool(original) and original.endswith(b"\n"), "chunks JSONL boundary differs")
    records = [json.loads(line) for line in original[:-1].split(b"\n")]
    replacement = b"".join(
        (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        for record in records
    )
    check(replacement != original, "noncanonical input mutation changed no bytes")
    check(
        [json.loads(line) for line in replacement[:-1].split(b"\n")] == records,
        "noncanonical input mutation changed decoded records",
    )
    path.write_bytes(replacement)
    reseal_input_chain(root, "input/chunks.jsonl")


def build_validator_variant(
    destination: Path,
    *,
    variant_name: str,
    source_line: bytes,
    replacement_line: bytes,
) -> dict[str, object]:
    """Create one target-only validator variant in a temporary repo layout."""
    source = VALIDATOR.read_bytes()
    source_text = source.decode("utf-8")
    source_pattern = source_line.decode("utf-8").rstrip("\n")
    replacement = replacement_line.decode("utf-8").rstrip("\n")
    check(
        source_text.count(source_pattern) == 1,
        f"{variant_name}: source pattern is not unique",
    )
    check("\n" not in source_pattern, f"{variant_name}: source pattern is not one line")
    check("\n" not in replacement, f"{variant_name}: replacement is not one line")
    variant_text = source_text.replace(source_pattern, replacement, 1)
    source_pattern_bytes = source_pattern.encode("utf-8")
    replacement_bytes = replacement.encode("utf-8")
    variant = source.replace(source_pattern_bytes, replacement_bytes, 1)
    check(
        variant.decode("utf-8") == variant_text,
        f"{variant_name}: variant contains changes beyond the target line",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(variant)

    schema_source = ROOT / "docs/plans/references/schemas/m8-minimal-1k-artifacts-v3.schema.json"
    protocol_source = ROOT / "docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md"
    temporary_root = destination.parent.parent
    schema_destination = (
        temporary_root
        / "docs/plans/references/schemas/m8-minimal-1k-artifacts-v3.schema.json"
    )
    protocol_destination = (
        temporary_root
        / "docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md"
    )
    schema_destination.parent.mkdir(parents=True, exist_ok=True)
    schema_destination.write_bytes(schema_source.read_bytes())
    protocol_destination.write_bytes(protocol_source.read_bytes())

    source_lines = source_text.replace("\r\n", "\n").splitlines(keepends=True)
    variant_lines = variant_text.replace("\r\n", "\n").splitlines(keepends=True)
    diff = "".join(
        difflib.unified_diff(
            source_lines,
            variant_lines,
            fromfile="tools/m8_validate_minimal_1k_graph_v3.py",
            tofile=f"tools/{variant_name}.py",
            n=0,
        )
    )
    check(diff.count("@@") == 2, f"{variant_name}: unified diff is not one hunk")
    check(
        [line for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
        == [f"-{source_pattern}"],
        f"{variant_name}: unified diff removes unexpected lines",
    )
    check(
        [line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
        == [f"+{replacement}"],
        f"{variant_name}: unified diff adds unexpected lines",
    )
    return {
        "name": variant_name,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "variant_sha256": hashlib.sha256(variant).hexdigest(),
        "source_line": source_pattern,
        "replacement_line": replacement,
        "unified_diff": diff,
    }


def forbidden_causal_failure(lines: list[str]) -> bool:
    """Reject diagnostics that indicate stale evidence rather than the target rule."""
    forbidden = ("digest", "bytes", "count", " ref", "reference")
    return any(any(token in line.lower() for token in forbidden) for line in lines)


def assert_canonical_json(path: Path) -> None:
    data = path.read_bytes()
    check(data == canonical_json(load(path)), f"{path}: JSON is not canonical")
    check(data.endswith(b"\n"), f"{path}: JSON lacks final LF")
    check(not data.endswith(b"\n\n"), f"{path}: JSON has trailing blank record")


def tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def reseal_observer_chain(
    root: Path,
    observer: str = "network",
) -> None:
    """Rebind every downstream summary and REF after an observer-ledger edit."""
    ledger = root / f"events/{observer}.jsonl"
    data = ledger.read_bytes()
    physical_lines = (
        data[:-1].split(b"\n")
        if data.endswith(b"\n")
        else (data.split(b"\n") if data else [])
    )
    parsed_events: list[dict] = []
    parse_failed = False
    for line in physical_lines:
        try:
            value = json.loads(
                line,
                parse_constant=reject_constant,
                object_pairs_hook=reject_duplicate_pairs,
            )
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            parse_failed = True
            continue
        if not isinstance(value, dict):
            parse_failed = True
            continue
        parsed_events.append(value)

    closed_failure_kinds = {
        "network": {"outbound-connection"},
        "write": {"denied-write"},
        "process": {"unexpected-child"},
        "redaction": {"sensitive-match"},
    }
    allowed_kinds = {
        "network": {"observer-start", "observer-stop", "outbound-connection"},
        "write": {"observer-start", "observer-stop", "allowed-write", "denied-write"},
        "process": {"observer-start", "observer-stop", "child-count", "unexpected-child"},
        "redaction": {"observer-start", "observer-stop", "utf8-scan", "sensitive-match"},
    }
    lifecycle_valid = (
        bool(parsed_events)
        and parsed_events[0].get("kind") == "observer-start"
        and parsed_events[-1].get("kind") == "observer-stop"
    )
    sequences = [event.get("sequence") for event in parsed_events]
    sequence_valid = (
        all(isinstance(value, int) and not isinstance(value, bool) for value in sequences)
        and sequences == list(range(len(parsed_events)))
    )
    canonical_valid = (
        len(parsed_events) == len(physical_lines)
        and all(
            line + b"\n" == canonical_json(event)
            for line, event in zip(physical_lines, parsed_events)
        )
    )
    event_shapes_valid = all(
        set(event) == {"detail", "kind", "sequence", "status"}
        and isinstance(event.get("detail"), str)
        and event.get("kind") in allowed_kinds[observer]
        and event.get("status") in {"PASS", "FAIL"}
        and (
            event.get("kind") not in closed_failure_kinds[observer]
            or event.get("status") == "FAIL"
        )
        for event in parsed_events
    )
    aggregate_status = (
        "FAIL"
        if any(event.get("status") == "FAIL" for event in parsed_events)
        else "PASS"
    )
    observer_valid = (
        bool(data)
        and data.endswith(b"\n")
        and not parse_failed
        and lifecycle_valid
        and sequence_valid
        and canonical_valid
        and event_shapes_valid
        and aggregate_status == "PASS"
    )

    expectation_path = root / "expectation.json"
    if expectation_path.is_file():
        expectation_obj = load(expectation_path)
        expectation_obj["intended_outcome"] = (
            "PASS" if observer_valid else "VALID_FAILURE_GRAPH"
        )
        expectation_obj["represented_failure"] = (
            "none" if observer_valid else "observer"
        )
        save(expectation_path, expectation_obj)

    run_path = root / "artifacts/run-report.json"
    run_obj = load(run_path)
    summary = run_obj["payload"]["observers"][observer]
    summary.update(
        {
            "sha256": hashlib.sha256(data).hexdigest(),
            "byte_count": len(data),
            "event_count": len(physical_lines),
            "status": aggregate_status,
        }
    )
    save(run_path, run_obj)

    validation_path = root / "artifacts/validation-report.json"
    validation_obj = load(validation_path)
    validation_obj["payload"]["run_report_ref"] = file_ref(
        "run-report",
        run_path,
    )
    validation_obj["payload"]["checks"]["observer"] = observer_valid
    validation_obj["payload"]["verdict"] = (
        "PASS"
        if all(
            value is True
            for value in validation_obj["payload"]["checks"].values()
        )
        else "FAIL"
    )
    save(validation_path, validation_obj)

    s2_path = root / "artifacts/s2.json"
    s2_obj = load(s2_path)
    validation_pass = validation_obj["payload"]["verdict"] == "PASS"
    s2_obj["payload"]["decision"] = (
        "EVIDENCE_READY" if validation_pass else "DRY_RUN_FAILED"
    )
    s2_obj["payload"]["allowed_next_action"] = (
        "request-s3" if validation_pass else "stop"
    )
    replacements = {
        "s1": root / "artifacts/s1.json",
        "run-report": run_path,
        "cleanup-receipt": root / "artifacts/cleanup-receipt.json",
        "validation-report": validation_path,
    }
    read_refs = s2_obj["payload"]["read_refs"]
    roles = [ref.get("role") if isinstance(ref, dict) else None for ref in read_refs]
    check(
        roles == ["s1", "run-report", "cleanup-receipt", "validation-report"],
        f"s2 read_refs cannot be safely resealed: {roles!r}",
    )
    typed_roles = [str(role) for role in roles]
    s2_obj["payload"]["read_refs"] = [
        file_ref(role, replacements[role]) for role in typed_roles
    ]
    save(s2_path, s2_obj)

    s3_path = root / "artifacts/s3.json"
    s3_obj = load(s3_path)
    s3_obj["payload"]["decision"] = (
        "ACCEPT_1K_EVIDENCE" if validation_pass else "REJECT_1K_EVIDENCE"
    )
    s3_obj["payload"]["read_refs"] = [file_ref("s2", s2_path)]
    save(s3_path, s3_obj)

    for path in (run_path, validation_path, s2_path, s3_path):
        assert_canonical_json(path)

    refreshed_s2 = load(s2_path)
    refs = refreshed_s2["payload"]["read_refs"]
    check(
        refs[1] == file_ref("run-report", run_path),
        "resealed run-report reference differs",
    )
    check(
        refs[3] == file_ref("validation-report", validation_path),
        "resealed validation-report reference differs",
    )
    check(
        load(s3_path)["payload"]["read_refs"] == [file_ref("s2", s2_path)],
        "resealed s3 reference differs",
    )


def main() -> int:
    failures: list[str] = []
    expected = {
        "success": "verdict=PASS",
        "failure-cleanup": "verdict=FAIL",
        "failure-observer": "verdict=FAIL",
        "failure-runtime": "verdict=FAIL",
        "failure-validation": "verdict=FAIL",
    }
    with tempfile.TemporaryDirectory(prefix="m8-v3-fixtures-") as temp:
        fixture_root = Path(temp) / "fixtures"
        second_fixture_root = Path(temp) / "fixtures-second"
        subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--output-root",
                str(fixture_root),
            ],
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--output-root",
                str(second_fixture_root),
            ],
            check=True,
        )
        generated = tree_snapshot(fixture_root)
        check(
            generated == tree_snapshot(second_fixture_root),
            "repeated fixture generation differs",
        )
        committed = tree_snapshot(COMMITTED_FIXTURES)
        if generated != committed:
            changed = sorted(
                path
                for path in set(generated) | set(committed)
                if generated.get(path) != committed.get(path)
            )
            failures.append(
                "committed fixtures differ from deterministic generation: "
                + ", ".join(changed)
            )
        for fixture_tree, label in (
            (fixture_root, "fixture"),
            (COMMITTED_FIXTURES, "committed fixture"),
        ):
            for name, marker in expected.items():
                result = run(fixture_tree / name)
                ok = result.returncode == 0 and marker in result.stdout
                print(("PASS" if ok else "FAIL") + f" {label} {name}")
                if not ok:
                    failures.append(
                        f"{label} {name}: {result.stdout}{result.stderr}"
                    )

        def prepare_boundary_only(root: Path, empty: bool = False) -> None:
            ledger = root / "events/network.jsonl"
            ledger.write_bytes(
                b"" if empty else ledger.read_bytes().rstrip(b"\n")
            )

        def critical_mutation(root: Path, empty: bool) -> None:
            prepare_boundary_only(root, empty)
            reseal_observer_chain(root)

        def replace_network_ledger(root: Path, data: bytes) -> None:
            (root / "events/network.jsonl").write_bytes(data)
            reseal_observer_chain(root)

        def mutate_event_sequence(root: Path) -> None:
            replace_network_ledger(
                root,
                b'{"detail":"none","kind":"observer-start",'
                b'"sequence":1,"status":"PASS"}\n'
                b'{"detail":"none","kind":"observer-stop",'
                b'"sequence":2,"status":"PASS"}\n',
            )

        def mutate_noncanonical_event(root: Path) -> None:
            replace_network_ledger(
                root,
                b'{"status":"PASS","sequence":0,"kind":"observer-start",'
                b'"detail":"none"}\n'
                b'{"detail":"none","kind":"observer-stop",'
                b'"sequence":1,"status":"PASS"}\n',
            )

        junction_ok, junction_detail = junction_regression(
            fixture_root / "success",
            fixture_root / "mutations",
        )
        print(("PASS" if junction_ok else "FAIL") + " containment directory-junction")
        if not junction_ok:
            failures.append(f"containment directory-junction: {junction_detail}")

        s3_reject_target = fixture_root / "variants" / "ready-s2-s3-reject"
        shutil.copytree(fixture_root / "success", s3_reject_target)
        s3_reject_expectation = s3_reject_target / "expectation.json"
        s3_reject_expectation_obj = load(s3_reject_expectation)
        s3_reject_expectation_obj["graph"] = "ready-s2-s3-reject"
        save(s3_reject_expectation, s3_reject_expectation_obj)
        s3_reject_path = s3_reject_target / "artifacts/s3.json"
        s3_reject = load(s3_reject_path)
        s3_reject["payload"]["decision"] = "REJECT_1K_EVIDENCE"
        s3_reject["payload"]["allowed_next_action"] = "stop"
        save(s3_reject_path, s3_reject)
        s3_reject_result = run(s3_reject_target)
        s3_reject_ok = (
            s3_reject_result.returncode == 0
            and "verdict=PASS" in s3_reject_result.stdout
        )
        print(
            ("PASS" if s3_reject_ok else "FAIL")
            + " valid ready-s2-s3-reject"
        )
        if not s3_reject_ok:
            failures.append(
                "valid ready-s2-s3-reject: "
                f"{s3_reject_result.stdout}{s3_reject_result.stderr}"
            )

        def semantic_json_mutation(
            relative: str,
            change: Callable[[dict], object],
        ) -> Callable[[Path], None]:
            mutation = mutate_json(relative, change)

            def apply(root: Path) -> None:
                mutation(root)
                reseal_artifact_refs(root)

            return apply

        def mutate_s2_and_reseal_s3(
            root: Path,
            change: Callable[[dict], object],
        ) -> None:
            s2_path = root / "artifacts/s2.json"
            s3_path = root / "artifacts/s3.json"
            s2 = load(s2_path)
            change(s2)
            save(s2_path, s2)
            s3 = load(s3_path)
            s3["payload"]["read_refs"] = [artifact_ref("s2", s2_path)]
            save(s3_path, s3)
            assert_canonical_json(s2_path)
            assert_canonical_json(s3_path)

        cases = [
            MutationSpec(
                "target-bytes",
                lambda root: (root / "input/chunks.jsonl").write_bytes(
                    b"tampered\n"
                ),
                expected_failures=("FAIL manifest: digest input/chunks.jsonl",),
            ),
            MutationSpec(
                "ref-role",
                mutate_json(
                    "artifacts/input-manifest.json",
                    lambda o: o["payload"]["identity_ref"].__setitem__(
                        "role", "run-report"
                    ),
                ),
                expected_failures=("FAIL identity: ref role",),
            ),
            MutationSpec(
                "ref-schema",
                mutate_json(
                    "artifacts/input-manifest.json",
                    lambda o: o["payload"]["identity_ref"].__setitem__(
                        "schema_id", "sa.m8.minimal.run-report.v3"
                    ),
                ),
                expected_failures=("FAIL identity: ref schema id",),
            ),
            MutationSpec(
                "logical-name",
                semantic_json_mutation(
                    "artifacts/identity.json",
                    lambda o: o.__setitem__(
                        "logical_name", "minimal-1k/wrong/identity.json"
                    ),
                ),
                semantic=True,
                expected_failures=("FAIL identity: logical name",),
            ),
            MutationSpec(
                "ref-digest",
                mutate_json(
                    "artifacts/input-manifest.json",
                    lambda o: o["payload"]["identity_ref"].__setitem__(
                        "sha256", "f" * 64
                    ),
                ),
                expected_failures=("FAIL identity: ref digest",),
            ),
            MutationSpec(
                "member-count",
                semantic_json_mutation(
                    "artifacts/input-manifest.json",
                    lambda o: o["payload"]["members"][0].__setitem__(
                        "record_count", 99
                    ),
                ),
                semantic=True,
                expected_failures=("FAIL manifest: records input/chunks.jsonl",),
            ),
            MutationSpec(
                "protocol-digest",
                semantic_json_mutation(
                    "artifacts/identity.json",
                    lambda o: o["payload"].__setitem__(
                        "protocol_sha256", "f" * 64
                    ),
                ),
                semantic=True,
                expected_failures=("FAIL identity: protocol digest bytes",),
            ),
            MutationSpec(
                "gate-actor",
                semantic_json_mutation(
                    "artifacts/s2.json",
                    lambda o: o["payload"].__setitem__("actor_role", "owner"),
                ),
                semantic=True,
                expected_failures=("FAIL s2: gate actor mapping",),
            ),
            MutationSpec(
                "s0-read-ref",
                semantic_json_mutation(
                    "artifacts/s0.json",
                    lambda o: o["payload"]["read_refs"].append(
                        {
                            "logical_name": "minimal-1k/invalid/s0.json",
                            "role": "s0",
                            "schema_id": "sa.m8.minimal.decision-record.v3",
                            "sha256": "0" * 64,
                            "byte_count": 1,
                        }
                    ),
                ),
                semantic=True,
                expected_failures=("FAIL s0: predecessor refs must be empty",),
            ),
            MutationSpec(
                "s1-with-rejected-s0",
                semantic_json_mutation(
                    "artifacts/s0.json",
                    lambda o: (
                        o["payload"].__setitem__(
                            "decision", "PROTOCOL_REJECTED"
                        ),
                        o["payload"].__setitem__("allowed_next_action", "stop"),
                    ),
                ),
                semantic=True,
                expected_failures=("FAIL s1: predecessor authority",),
            ),
            MutationSpec(
                "gate-decision-action",
                semantic_json_mutation(
                    "artifacts/s2.json",
                    lambda o: (
                        o["payload"].__setitem__("decision", "DRY_RUN_FAILED"),
                        o["payload"].__setitem__(
                            "allowed_next_action", "request-s3"
                        ),
                    ),
                ),
                semantic=True,
                expected_failures=(
                    "FAIL s2: decision/action mapping",
                    "FAIL s2: evidence authority",
                ),
            ),
            MutationSpec(
                "s2-missing-authority",
                lambda root: mutate_s2_and_reseal_s3(
                    root,
                    lambda o: o["payload"]["read_refs"].pop(),
                ),
                semantic=True,
                expected_failures=("FAIL s2: authority refs",),
            ),
            MutationSpec(
                "observer-summary",
                semantic_json_mutation(
                    "artifacts/run-report.json",
                    lambda o: o["payload"]["observers"]["network"].__setitem__(
                        "event_count", 99
                    ),
                ),
                semantic=True,
                expected_failures=(
                    "FAIL observer network: count",
                    "FAIL validation: observer check",
                    "FAIL validation: verdict",
                    "FAIL s2: evidence authority",
                    "FAIL s3: evidence authority",
                ),
            ),
            MutationSpec(
                "event-sequence",
                mutate_event_sequence,
                semantic=True,
                expected_failures=("FAIL observer network: sequence",),
            ),
            MutationSpec(
                "noncanonical-event",
                mutate_noncanonical_event,
                semantic=True,
                expected_failures=(
                    "FAIL observer network: invalid JSONL JSONL line is not canonical JSON",
                ),
            ),
            MutationSpec(
                "missing-final-lf",
                lambda root: critical_mutation(root, False),
                semantic=True,
                expected_failures=(
                    "FAIL observer network: JSONL must end with LF",
                ),
            ),
            MutationSpec(
                "empty-observer",
                lambda root: critical_mutation(root, True),
                semantic=True,
                expected_failures=(
                    "FAIL observer network: JSONL must be non-empty",
                    "FAIL observer network: JSONL must end with LF",
                    "FAIL observer network: byte_count type",
                    "FAIL observer network: event_count type",
                    "FAIL observer network: lifecycle",
                ),
            ),
            MutationSpec(
                "noncanonical-input",
                make_noncanonical_input,
                semantic=True,
                expected_failures=(
                    "FAIL manifest: invalid JSONL input/chunks.jsonl: "
                    "JSONL line is not canonical JSON",
                ),
            ),
            MutationSpec(
                "failure-as-success",
                semantic_json_mutation(
                    "artifacts/s2.json",
                    lambda o: (
                        o["payload"].__setitem__("decision", "EVIDENCE_READY"),
                        o["payload"].__setitem__(
                            "allowed_next_action", "request-s3"
                        ),
                    ),
                ),
                source="failure-cleanup",
                semantic=True,
                expected_failures=("FAIL s2: evidence authority",),
            ),
            MutationSpec(
                "missing-artifact",
                lambda root: (root / "artifacts/s3.json").rename(
                    root / "s3.missing"
                ),
                expected_failures=("FAIL graph inventory mismatch:",),
            ),
            MutationSpec(
                "unknown-artifact",
                lambda root: (root / "artifacts/unknown.json").write_text(
                    "{}\n", encoding="utf-8"
                ),
                expected_failures=("FAIL graph inventory mismatch:",),
            ),
            MutationSpec(
                "path-escape",
                mutate_json(
                    "artifacts/input-manifest.json",
                    lambda o: o["payload"]["members"][0].__setitem__(
                        "path", "../escape.jsonl"
                    ),
                ),
                expected_failures=(
                    "FAIL unsafe relative path: ../escape.jsonl",
                ),
            ),
        ]
        for spec in cases:
            source = fixture_root / spec.source
            target = fixture_root / "mutations" / spec.name
            shutil.copytree(source, target)
            expectation = target / "expectation.json"
            expectation_obj = load(expectation)
            expectation_obj["graph"] = spec.name
            save(expectation, expectation_obj)
            spec.mutation(target)
            result = run(target)
            ok = mutation_result(spec, result)
            print(("PASS" if ok else "FAIL") + f" negative {spec.name}")
            if not ok:
                failures.append(
                    f"negative {spec.name}: {result.stdout}{result.stderr}"
                )

        critical_specs = {
            spec.name: spec
            for spec in cases
            if spec.name in {
                "missing-final-lf",
                "empty-observer",
                "noncanonical-event",
                "noncanonical-input",
            }
        }
        for critical_name in sorted(critical_specs):
            spec = critical_specs[critical_name]
            target = fixture_root / "causal" / critical_name
            shutil.copytree(fixture_root / spec.source, target)
            expectation_path = target / "expectation.json"
            expectation_obj = load(expectation_path)
            expectation_obj["graph"] = critical_name
            save(expectation_path, expectation_obj)
            spec.mutation(target)
            causal_result = run(target)
            causal_lines = fail_lines(causal_result)
            causal_ok = (
                exact_failure(causal_result, spec.expected_failures)
                and (
                    critical_name == "empty-observer"
                    or not forbidden_causal_failure(causal_lines)
                )
            )
            print(("PASS" if causal_ok else "FAIL") + f" causal {critical_name}")
            if not causal_ok:
                failures.append(
                    f"causal {critical_name}: "
                    f"{causal_result.stdout}{causal_result.stderr}"
                )

        variant_root = Path(temp) / "validator-variants"
        variant_root.mkdir()
        variant_specs = (
            (
                "final-lf-disabled",
                b'            final_lf_valid = data.endswith(b"\\n")\n',
                b"            final_lf_valid = bool(data)\n",
                False,
                [
                    "FAIL validation: observer check",
                    "FAIL validation: verdict",
                    "FAIL s2: evidence authority",
                ],
            ),
            (
                "nonempty-disabled",
                b"            nonempty_valid = bool(data)\n",
                b"            nonempty_valid = True\n",
                True,
                [
                    "FAIL observer network: JSONL must end with LF",
                    "FAIL observer network: byte_count type",
                    "FAIL observer network: event_count type",
                    "FAIL observer network: lifecycle",
                ],
            ),
        )
        sensitivity_records: list[dict[str, object]] = []
        for variant_name, source_line, replacement_line, empty, expected_variant in variant_specs:
            target = fixture_root / "mutations" / f"sensitivity-{variant_name}"
            shutil.copytree(fixture_root / "success", target)
            expectation_path = target / "expectation.json"
            expectation_obj = load(expectation_path)
            expectation_obj["graph"] = f"sensitivity-{variant_name}"
            save(expectation_path, expectation_obj)
            prepare_boundary_only(target, empty)
            reseal_observer_chain(target)

            variant_path = variant_root / f"{variant_name}.py"
            record = build_validator_variant(
                variant_path,
                variant_name=variant_name,
                source_line=source_line,
                replacement_line=replacement_line,
            )
            production_result = run(target)
            variant_result = run(target, variant_path)
            production_lines = fail_lines(production_result)
            variant_lines = fail_lines(variant_result)
            target_diagnostic = (
                "FAIL observer network: JSONL must be non-empty"
                if empty
                else "FAIL observer network: JSONL must end with LF"
            )
            production_ok = (
                production_result.returncode != 0
                and target_diagnostic in production_lines
                and (
                    empty
                    or not forbidden_causal_failure(production_lines)
                )
            )
            variant_ok = (
                variant_lines == expected_variant
                and variant_result.returncode == (0 if not expected_variant else 1)
                and target_diagnostic not in variant_lines
                and (
                    empty
                    or not forbidden_causal_failure(variant_lines)
                )
            )
            record.update(
                {
                    "production_returncode": production_result.returncode,
                    "production_failures": production_lines,
                    "variant_returncode": variant_result.returncode,
                    "variant_failures": variant_lines,
                }
            )
            sensitivity_records.append(record)
            ok = production_ok and variant_ok
            print(("PASS" if ok else "FAIL") + f" sensitivity {variant_name}")
            if not ok:
                failures.append(
                    f"sensitivity {variant_name}: {json.dumps(record, sort_keys=True)}"
                )

    if failures:
        print("\n".join(failures))
        return 1
    print(
        f"ALL PASS: {len(expected)} persistent graphs + "
        f"{len(cases)} fail-closed mutations + "
        f"{len(sensitivity_records)} sensitivity proofs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
