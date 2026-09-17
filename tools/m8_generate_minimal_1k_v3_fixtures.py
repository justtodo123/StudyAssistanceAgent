#!/usr/bin/env python3
"""Generate persistent, micro synthetic artifact graphs for M8 v3 S0 review.

These fixtures test the graph validator itself. They are not a 1K dry-run,
do not use LanceDB, and confer no S1/S2 authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/plans/references/fixtures/m8-minimal-1k-v3"
PROTOCOL = ROOT / "docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md"
CANON = "sa-json-c14n-v1"
SCHEMA_VERSION = 3


def _absolute_lexical(path: Path) -> Path:
    """Return an absolute path without following a caller-supplied link."""
    return Path(os.path.abspath(os.fspath(path)))


def _has_reparse_point(file_stat: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(file_stat, "st_file_attributes", 0) & reparse_flag)


def _inspect_output_path(path: Path) -> Path:
    """Reject links/reparse points in every existing output-path component."""
    absolute = _absolute_lexical(path)
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current /= part
        try:
            file_stat = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise ValueError(f"output path cannot be inspected: {exc}") from exc
        if stat.S_ISLNK(file_stat.st_mode) or _has_reparse_point(file_stat):
            raise ValueError(
                f"output path contains a symlink or reparse point: {current}"
            )
    return absolute


def canonical(obj: object) -> bytes:
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


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def envelope(experiment_id: str, role: str, schema_id: str, payload: dict) -> dict:
    return {
        "canonicalization_id": CANON,
        "logical_name": f"minimal-1k/{experiment_id}/{role}.json",
        "payload": payload,
        "schema_id": schema_id,
        "schema_version": SCHEMA_VERSION,
    }


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(obj))


def ref_for(role: str, obj: dict) -> dict:
    data = canonical(obj)
    return {
        "logical_name": obj["logical_name"],
        "role": role,
        "schema_id": obj["schema_id"],
        "sha256": digest(data),
        "byte_count": len(data),
    }


def event(
    observer: str,
    kind: str,
    sequence: int,
    status: str = "PASS",
    *,
    code: str = "none",
    phase: str | None = None,
) -> dict:
    digest_text = digest(b"fixture-observer-detail")
    if observer == "network":
        if kind in {"observer-start", "observer-stop"}:
            detail = {
                "api_ids": ["fixture-network-api"],
                "code": code,
                "phase": (
                    "observer-bootstrap"
                    if kind == "observer-start"
                    else "observer-finalize"
                ),
                "root_process_identity": digest_text,
            }
        else:
            detail = {
                "address_family": "ipv4",
                "code": code,
                "local_endpoint_digest": digest_text,
                "phase": phase or "measured",
                "process_identity_digest": digest_text,
                "protocol": "tcp",
                "remote_endpoint_digest": digest_text,
            }
    elif observer == "write":
        if kind in {"observer-start", "observer-stop"}:
            detail = {
                "allowed_root_set_sha256": digest_text,
                "api_ids": ["fixture-write-api"],
                "code": code,
                "phase": (
                    "observer-bootstrap"
                    if kind == "observer-start"
                    else "observer-finalize"
                ),
                "root_process_identity": digest_text,
            }
        else:
            detail = {
                "code": code,
                "operation": "create",
                "path_digest": digest_text,
                "phase": "measured",
                "process_identity_digest": digest_text,
                "root_id": "temporary-root",
            }
    elif observer == "process":
        if kind in {"observer-start", "observer-stop"}:
            detail = {
                "api_ids": ["fixture-process-api"],
                "code": code,
                "phase": (
                    "observer-bootstrap"
                    if kind == "observer-start"
                    else "observer-finalize"
                ),
                "root_process_identity": digest_text,
            }
        elif kind == "child-count":
            detail = {
                "code": code,
                "count": 0,
                "phase": phase or "measured",
                "tree_digest": digest_text,
            }
        else:
            detail = {
                "code": code,
                "executable_digest": digest_text,
                "parent_identity_digest": digest_text,
                "phase": "measured",
                "process_identity_digest": digest_text,
            }
    elif observer == "redaction":
        if kind in {"observer-start", "observer-stop"}:
            detail = {
                "code": code,
                "phase": (
                    "observer-bootstrap"
                    if kind == "observer-start"
                    else "observer-finalize"
                ),
                "registry_sha256": digest_text,
                "scanned_set_sha256": digest_text,
            }
        elif kind == "utf8-scan":
            detail = {
                "byte_count": 0,
                "code": code,
                "path": "artifacts/fixture.json",
                "phase": "redaction-and-seal",
                "sha256": digest_text,
            }
        else:
            detail = {
                "code": code,
                "match_count": 1,
                "path": "artifacts/fixture.json",
                "pattern_id": "fixture-pattern",
                "phase": "redaction-and-seal",
            }
    else:
        raise ValueError(f"unknown observer: {observer}")
    return {
        "detail": detail,
        "kind": kind,
        "sequence": sequence,
        "status": status,
    }


def graph(
    output_root: Path,
    name: str,
    failure: str | None,
    protocol_bytes: bytes,
) -> None:
    exp = f"sa-m8-v3-fixture-{name}"
    graph_dir = output_root / name
    evidence = graph_dir / "artifacts"
    event_dir = graph_dir / "events"
    protocol_sha = digest(protocol_bytes)

    identity = envelope(exp, "identity", "sa.m8.minimal.experiment-identity.v3", {
        "backends": ["sqlite-linear-exact", "lancedb-embedded-exact-flat"],
        "chunk_count": 1000,
        "dimension": 512,
        "dtype": "float32",
        "byte_order": "little-endian",
        "experiment_id": exp,
        "generator_algorithm": "sa-m8-synthetic-unit-v3",
        "normalization": "l2",
        "protocol_sha256": protocol_sha,
        "seed": 20260914,
        "synthetic_only": True,
        "top_k": [1, 3, 5],
    })
    write_json(evidence / "identity.json", identity)

    members = []
    fixture_inputs = [
        (
            "chunks.jsonl",
            2,
            canonical({"chunk_id": "fixture-000"})
            + canonical({"chunk_id": "fixture-001"}),
        ),
        (
            "queries.jsonl",
            2,
            canonical({"query_id": "fixture-q00"})
            + canonical({"query_id": "fixture-q01"}),
        ),
        (
            "gold.jsonl",
            2,
            canonical(
                {"gold": ["fixture-000"], "query_id": "fixture-q00"}
            )
            + canonical({"gold": [], "query_id": "fixture-q01"}),
        ),
    ]
    for filename, records, body in fixture_inputs:
        target = graph_dir / "input" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        members.append(
            {
                "byte_count": len(body),
                "path": f"input/{filename}",
                "record_count": records,
                "sha256": digest(body),
            }
        )
    vectors = b"M8-V3-FIXTURE-VECTORS-NOT-REAL-1K\n"
    (graph_dir / "input/vectors.bin").write_bytes(vectors)
    members.append(
        {
            "byte_count": len(vectors),
            "path": "input/vectors.bin",
            "record_count": 2,
            "sha256": digest(vectors),
        }
    )

    manifest = envelope(exp, "input-manifest", "sa.m8.minimal.input-manifest.v3", {
        "experiment_id": exp,
        "identity_ref": ref_for("identity", identity),
        "members": sorted(members, key=lambda item: item["path"]),
        "synthetic_fixture_only": True,
    })
    write_json(evidence / "input-manifest.json", manifest)

    event_sets = {
        "network": [
            event("network", "observer-start", 0),
            event("network", "observer-stop", 1),
        ],
        "write": [
            event("write", "observer-start", 0),
            event("write", "allowed-write", 1),
            event("write", "observer-stop", 2),
        ],
        "process": [
            event("process", "observer-start", 0),
            *[
                event("process", "child-count", index + 1, phase=phase)
                for index, phase in enumerate(
                    (
                        "observer-bootstrap",
                        "acquisition",
                        "measured",
                        "redaction-and-seal",
                        "cleanup",
                        "observer-finalize",
                    )
                )
            ],
            event("process", "observer-stop", 7),
        ],
        "redaction": [
            event("redaction", "observer-start", 0),
            event("redaction", "utf8-scan", 1),
            event("redaction", "observer-stop", 2),
        ],
    }
    if failure == "observer":
        event_sets["network"].insert(
            1,
            event(
                "network",
                "outbound-connection",
                1,
                "FAIL",
                code="network-measured-outbound-observed",
                phase="measured",
            ),
        )
        event_sets["network"][-1]["sequence"] = 2
    observer_summaries = {}
    for observer, events in event_sets.items():
        target = event_dir / f"{observer}.jsonl"
        body = b"".join(canonical(item) for item in events)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        observer_summaries[observer] = {
            "byte_count": len(body),
            "event_count": len(events),
            "path": f"events/{observer}.jsonl",
            "sha256": digest(body),
            "status": "FAIL" if any(item["status"] == "FAIL" for item in events) else "PASS",
        }

    runtime_status = "FAIL" if failure == "runtime" else "PASS"
    fixture_per_query = [
        {
            "query_id": "fixture-q00",
            "top_k": {
                "1": ["fixture-000"],
                "3": ["fixture-000"],
                "5": ["fixture-000"],
            },
        },
        {
            "query_id": "fixture-q01",
            "top_k": {"1": [], "3": [], "5": []},
        },
    ]
    run = envelope(exp, "run-report", "sa.m8.minimal.run-report.v3", {
        "backend_results": [
            {
                "backend": "sqlite-linear-exact",
                "input_manifest_sha256": (
                    "f" * 64
                    if failure == "validation"
                    else digest(canonical(manifest))
                ),
                "mode": "linear-exact",
                "per_query": fixture_per_query,
                "status": runtime_status,
            },
            {
                "backend": "lancedb-embedded-exact-flat",
                "input_manifest_sha256": digest(canonical(manifest)),
                "mode": "embedded-exact-flat-no-ann",
                "per_query": fixture_per_query,
                "status": runtime_status,
            },
        ],
        "experiment_id": exp,
        "input_manifest_ref": ref_for("input-manifest", manifest),
        "observers": observer_summaries,
        "runtime_errors": ["fixture-runtime-failure"] if failure == "runtime" else [],
        "status": runtime_status,
    })
    write_json(evidence / "run-report.json", run)

    cleanup_status = "FAIL" if failure == "cleanup" else "CLEANED"
    cleanup = envelope(exp, "cleanup-receipt", "sa.m8.minimal.cleanup-receipt.v3", {
        "after_count": 1 if failure == "cleanup" else 0,
        "experiment_id": exp,
        "failure_code": "FIXTURE_DESCENDANT_REMAINS" if failure == "cleanup" else "none",
        "status": cleanup_status,
        "temporary_root_exists": failure == "cleanup",
    })
    write_json(evidence / "cleanup-receipt.json", cleanup)

    validation_status = "FAIL" if failure in {"cleanup", "observer", "runtime", "validation"} else "PASS"
    checks = {
        "cleanup": cleanup_status == "CLEANED",
        "observer": all(value["status"] == "PASS" for value in observer_summaries.values()),
        "runtime": runtime_status == "PASS",
        "same_input": True,
    }
    if failure == "validation":
        checks["same_input"] = False
    validation = envelope(exp, "validation-report", "sa.m8.minimal.validation-report.v3", {
        "checks": checks,
        "cleanup_receipt_ref": ref_for("cleanup-receipt", cleanup),
        "experiment_id": exp,
        "run_report_ref": ref_for("run-report", run),
        "verdict": validation_status,
    })
    write_json(evidence / "validation-report.json", validation)

    s0 = envelope(exp, "s0", "sa.m8.minimal.decision-record.v3", {
        "actor_role": "independent-reviewer", "allowed_next_action": "request-s1",
        "decision": "PROTOCOL_ACCEPTED", "experiment_id": exp, "gate_id": "S0", "read_refs": []})
    write_json(evidence / "s0.json", s0)
    s1 = envelope(exp, "s1", "sa.m8.minimal.decision-record.v3", {
        "actor_role": "owner", "allowed_next_action": "run-s2", "decision": "DRY_RUN_AUTHORIZED",
        "experiment_id": exp, "gate_id": "S1", "read_refs": [ref_for("s0", s0)]})
    write_json(evidence / "s1.json", s1)
    if validation_status == "PASS" and cleanup_status == "CLEANED":
        s2_decision, s2_action = "EVIDENCE_READY", "request-s3"
    else:
        s2_decision, s2_action = "DRY_RUN_FAILED", "stop"
    s2 = envelope(exp, "s2", "sa.m8.minimal.decision-record.v3", {
        "actor_role": "executor",
        "allowed_next_action": s2_action,
        "decision": s2_decision,
        "experiment_id": exp,
        "gate_id": "S2",
        "read_refs": [
            ref_for("s1", s1),
            ref_for("run-report", run),
            ref_for("cleanup-receipt", cleanup),
            ref_for("validation-report", validation),
        ],
    })
    write_json(evidence / "s2.json", s2)
    s3_decision = "ACCEPT_1K_EVIDENCE" if s2_decision == "EVIDENCE_READY" else "REJECT_1K_EVIDENCE"
    s3 = envelope(exp, "s3", "sa.m8.minimal.decision-record.v3", {
        "actor_role": "independent-reviewer", "allowed_next_action": "stop", "decision": s3_decision,
        "experiment_id": exp, "gate_id": "S3", "read_refs": [ref_for("s2", s2)]})
    write_json(evidence / "s3.json", s3)

    expectation = {
        "fixture_kind": "validator-micro-fixture-not-real-1k",
        "graph": name,
        "intended_outcome": "PASS" if failure is None else "VALID_FAILURE_GRAPH",
        "represented_failure": failure or "none",
    }
    write_json(graph_dir / "expectation.json", expectation)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--replace-tracked",
        action="store_true",
        help="explicitly regenerate the committed fixture tree",
    )
    args = parser.parse_args()
    try:
        output_root = _inspect_output_path(args.output_root)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        protocol_bytes = PROTOCOL.read_bytes()
    except OSError as exc:
        parser.error(f"protocol is unreadable: {exc}")
    if output_root == DEFAULT_OUT and not args.replace_tracked:
        parser.error(
            "default output root is tracked; use --replace-tracked explicitly"
        )
    if output_root != DEFAULT_OUT:
        if output_root.exists():
            if output_root.is_symlink() or not output_root.is_dir():
                parser.error("output root must be an absent or empty directory")
            if any(output_root.iterdir()):
                parser.error("output root must be absent or empty")
        output_root.mkdir(parents=True, exist_ok=True)
        target_root = output_root
        temporary_root = None
    else:
        if output_root.exists() and (
            output_root.is_symlink() or not output_root.is_dir()
        ):
            parser.error("tracked output root must be a regular directory")
        temporary_root = Path(
            tempfile.mkdtemp(prefix="m8-v3-fixtures-", dir=ROOT.parent)
        )
        target_root = temporary_root / DEFAULT_OUT.name
        target_root.mkdir(parents=True, exist_ok=True)
    try:
        for name, failure in [
            ("success", None),
            ("failure-cleanup", "cleanup"),
            ("failure-observer", "observer"),
            ("failure-runtime", "runtime"),
            ("failure-validation", "validation"),
        ]:
            graph(target_root, name, failure, protocol_bytes)
        if temporary_root is not None:
            expected = {
                path.relative_to(target_root).as_posix(): path
                for path in target_root.rglob("*")
                if path.is_file() and not path.is_symlink()
            }
            unexpected_staged = [
                path
                for path in target_root.rglob("*")
                if path.is_symlink() or (not path.is_file() and not path.is_dir())
            ]
            if unexpected_staged:
                raise RuntimeError("staged fixture tree contains non-regular members")
            if output_root.exists():
                existing = {
                    path.relative_to(output_root).as_posix(): path
                    for path in output_root.rglob("*")
                    if path.is_file() and not path.is_symlink()
                }
                non_regular = [
                    path
                    for path in output_root.rglob("*")
                    if path.is_symlink()
                    or (not path.is_file() and not path.is_dir())
                ]
                if non_regular:
                    parser.error(
                        "tracked fixture tree contains non-regular members"
                    )
                unexpected = sorted(
                    set(existing) - set(expected),
                    key=lambda path: path.encode("utf-8"),
                )
                if unexpected:
                    parser.error(
                        "tracked fixture tree contains unexpected members: "
                        + ", ".join(unexpected)
                    )
            publish_root = temporary_root / "published"
            shutil.copytree(target_root, publish_root)
            backup_root = temporary_root / "previous"
            if output_root.exists():
                output_root.replace(backup_root)
            try:
                publish_root.replace(output_root)
            except OSError:
                if backup_root.exists() and not output_root.exists():
                    backup_root.replace(output_root)
                raise
            if backup_root.exists():
                shutil.rmtree(backup_root)
    finally:
        if temporary_root is not None:
            shutil.rmtree(temporary_root)
    print(output_root)


if __name__ == "__main__":
    main()
