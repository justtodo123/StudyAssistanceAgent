#!/usr/bin/env python3
"""Generate persistent, micro synthetic artifact graphs for M8 v3 S0 review.

These fixtures test the graph validator itself. They are not a 1K dry-run,
do not use LanceDB, and confer no S1/S2 authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/plans/references/fixtures/m8-minimal-1k-v3"
PROTOCOL = ROOT / "docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md"
CANON = "sa-json-c14n-v1"
SCHEMA_VERSION = 3


def canonical(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


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


def event(kind: str, sequence: int, status: str = "PASS", detail: str = "none") -> dict:
    return {"detail": detail, "kind": kind, "sequence": sequence, "status": status}


def graph(name: str, failure: str | None) -> None:
    exp = f"sa-m8-v3-fixture-{name}"
    graph_dir = OUT / name
    evidence = graph_dir / "artifacts"
    event_dir = graph_dir / "events"
    protocol_sha = digest(PROTOCOL.read_bytes()) if PROTOCOL.exists() else "0" * 64

    identity = envelope(exp, "identity", "sa.m8.minimal.experiment-identity.v3", {
        "backends": ["sqlite-linear-exact", "lancedb-embedded-exact-flat"],
        "chunk_count": 1000,
        "dimension": 512,
        "dtype": "float32",
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
    for filename, records, body in [
        ("chunks.jsonl", 2, b'{"chunk_id":"fixture-000"}\n{"chunk_id":"fixture-001"}\n'),
        ("queries.jsonl", 2, b'{"query_id":"fixture-q00"}\n{"query_id":"fixture-q01"}\n'),
        ("gold.jsonl", 2, b'{"query_id":"fixture-q00","gold":["fixture-000"]}\n{"query_id":"fixture-q01","gold":[]}\n'),
    ]:
        target = graph_dir / "input" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        members.append({"byte_count": len(body), "path": f"input/{filename}", "record_count": records, "sha256": digest(body)})
    vectors = b"M8-V3-FIXTURE-VECTORS-NOT-REAL-1K\n"
    (graph_dir / "input/vectors.bin").write_bytes(vectors)
    members.append({"byte_count": len(vectors), "path": "input/vectors.bin", "record_count": 2, "sha256": digest(vectors)})

    manifest = envelope(exp, "input-manifest", "sa.m8.minimal.input-manifest.v3", {
        "experiment_id": exp,
        "identity_ref": ref_for("identity", identity),
        "members": sorted(members, key=lambda item: item["path"]),
        "synthetic_fixture_only": True,
    })
    write_json(evidence / "input-manifest.json", manifest)

    event_sets = {
        "network": [event("observer-start", 0), event("observer-stop", 1)],
        "write": [event("observer-start", 0), event("allowed-write", 1), event("observer-stop", 2)],
        "process": [event("observer-start", 0), event("child-count", 1, detail="0"), event("observer-stop", 2)],
        "redaction": [event("observer-start", 0), event("utf8-scan", 1), event("observer-stop", 2)],
    }
    if failure == "observer":
        event_sets["network"].insert(1, event("outbound-connection", 1, "FAIL", "fixture-denied"))
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
    run = envelope(exp, "run-report", "sa.m8.minimal.run-report.v3", {
        "backend_results": [
            {"backend": "sqlite-linear-exact", "mode": "linear-exact", "status": runtime_status},
            {"backend": "lancedb-embedded-exact-flat", "mode": "embedded-exact-flat-no-ann", "status": runtime_status},
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

    gates = {}
    s0 = envelope(exp, "s0", "sa.m8.minimal.decision-record.v3", {
        "actor_role": "independent-reviewer", "allowed_next_action": "request-s1",
        "decision": "PROTOCOL_ACCEPTED", "experiment_id": exp, "gate_id": "S0", "read_refs": []})
    write_json(evidence / "s0.json", s0); gates["s0"] = s0
    s1 = envelope(exp, "s1", "sa.m8.minimal.decision-record.v3", {
        "actor_role": "owner", "allowed_next_action": "run-s2", "decision": "DRY_RUN_AUTHORIZED",
        "experiment_id": exp, "gate_id": "S1", "read_refs": [ref_for("s0", s0)]})
    write_json(evidence / "s1.json", s1); gates["s1"] = s1
    if validation_status == "PASS" and cleanup_status == "CLEANED":
        s2_decision, s2_action = "EVIDENCE_READY", "request-s3"
    else:
        s2_decision, s2_action = "DRY_RUN_FAILED", "stop"
    s2 = envelope(exp, "s2", "sa.m8.minimal.decision-record.v3", {
        "actor_role": "executor", "allowed_next_action": s2_action, "decision": s2_decision,
        "experiment_id": exp, "gate_id": "S2", "read_refs": [ref_for("s1", s1), ref_for("run-report", run), ref_for("cleanup-receipt", cleanup), ref_for("validation-report", validation)]})
    write_json(evidence / "s2.json", s2); gates["s2"] = s2
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
    OUT.mkdir(parents=True, exist_ok=True)
    for name, failure in [
        ("success", None),
        ("failure-cleanup", "cleanup"),
        ("failure-observer", "observer"),
        ("failure-runtime", "runtime"),
        ("failure-validation", "validation"),
    ]:
        graph(name, failure)
    print(OUT)


if __name__ == "__main__":
    main()
