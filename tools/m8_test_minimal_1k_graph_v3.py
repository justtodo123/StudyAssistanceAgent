#!/usr/bin/env python3
"""Run persistent positive/failure fixtures and fail-closed mutations for M8 v3."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/plans/references/fixtures/m8-minimal-1k-v3"
GENERATOR = ROOT / "tools/m8_generate_minimal_1k_v3_fixtures.py"
VALIDATOR = ROOT / "tools/m8_validate_minimal_1k_graph_v3.py"


def run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(VALIDATOR), str(path)], text=True, capture_output=True, check=False)


def load(path: Path) -> dict:
    return json.loads(path.read_bytes())


def save(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")


def mutate_json(relative: str, change):
    def apply(root: Path) -> None:
        path = root / relative
        obj = load(path)
        change(obj)
        save(path, obj)
    return apply


def main() -> int:
    subprocess.run([sys.executable, str(GENERATOR)], check=True)
    failures: list[str] = []
    expected = {
        "success": "verdict=PASS",
        "failure-cleanup": "verdict=FAIL",
        "failure-observer": "verdict=FAIL",
        "failure-runtime": "verdict=FAIL",
        "failure-validation": "verdict=FAIL",
    }
    for name, marker in expected.items():
        result = run(FIXTURES / name)
        ok = result.returncode == 0 and marker in result.stdout
        print(("PASS" if ok else "FAIL") + f" fixture {name}")
        if not ok:
            failures.append(f"fixture {name}: {result.stdout}{result.stderr}")

    cases = [
        ("target-bytes", lambda root: (root / "input/chunks.jsonl").write_bytes(b"tampered\n")),
        ("ref-role", mutate_json("artifacts/input-manifest.json", lambda o: o["payload"]["identity_ref"].__setitem__("role", "run-report"))),
        ("ref-schema", mutate_json("artifacts/input-manifest.json", lambda o: o["payload"]["identity_ref"].__setitem__("schema_id", "sa.m8.minimal.run-report.v3"))),
        ("logical-name", mutate_json("artifacts/identity.json", lambda o: o.__setitem__("logical_name", "minimal-1k/wrong/identity.json"))),
        ("ref-digest", mutate_json("artifacts/input-manifest.json", lambda o: o["payload"]["identity_ref"].__setitem__("sha256", "f" * 64))),
        ("member-count", mutate_json("artifacts/input-manifest.json", lambda o: o["payload"]["members"][0].__setitem__("record_count", 99))),
        ("protocol-digest", mutate_json("artifacts/identity.json", lambda o: o["payload"].__setitem__("protocol_sha256", "f" * 64))),
        ("gate-actor", mutate_json("artifacts/s2.json", lambda o: o["payload"].__setitem__("actor_role", "owner"))),
        ("s0-read-ref", mutate_json("artifacts/s0.json", lambda o: o["payload"]["read_refs"].append({"logical_name":"minimal-1k/invalid/s0.json","role":"s0","schema_id":"sa.m8.minimal.decision-record.v3","sha256":"0" * 64,"byte_count":1}))),
        ("s1-with-rejected-s0", mutate_json("artifacts/s0.json", lambda o: (o["payload"].__setitem__("decision", "PROTOCOL_REJECTED"), o["payload"].__setitem__("allowed_next_action", "stop")))),
        ("gate-decision-action", mutate_json("artifacts/s2.json", lambda o: (o["payload"].__setitem__("decision", "DRY_RUN_FAILED"), o["payload"].__setitem__("allowed_next_action", "request-s3")))),
        ("s2-missing-authority", mutate_json("artifacts/s2.json", lambda o: o["payload"]["read_refs"].pop())),
        ("observer-summary", mutate_json("artifacts/run-report.json", lambda o: o["payload"]["observers"]["network"].__setitem__("event_count", 99))),
        ("event-sequence", lambda root: (root / "events/network.jsonl").write_bytes(b'{"detail":"none","kind":"observer-start","sequence":1,"status":"PASS"}\n{"detail":"none","kind":"observer-stop","sequence":2,"status":"PASS"}\n')),
        ("noncanonical-event", lambda root: (root / "events/network.jsonl").write_bytes(b'{"status":"PASS","sequence":0,"kind":"observer-start","detail":"none"}\n{"detail":"none","kind":"observer-stop","sequence":1,"status":"PASS"}\n')),
        ("missing-final-lf", lambda root: (root / "events/network.jsonl").write_bytes((root / "events/network.jsonl").read_bytes().rstrip(b"\n"))),
        ("empty-observer", lambda root: (root / "events/network.jsonl").write_bytes(b"")),
        ("noncanonical-input", lambda root: (root / "input/chunks.jsonl").write_bytes(b'{"chunk_id": "m8-v3-00000", "owner_id":"owner-00","source_id":"source-00","text":"synthetic chunk 00000"}\n{"chunk_id":"m8-v3-00001","owner_id":"owner-00","source_id":"source-00","text":"synthetic chunk 00001"}\n')),
        ("failure-as-success", mutate_json("artifacts/s2.json", lambda o: (o["payload"].__setitem__("decision", "EVIDENCE_READY"), o["payload"].__setitem__("allowed_next_action", "request-s3")))),
        ("missing-artifact", lambda root: (root / "artifacts/s3.json").rename(root / "s3.missing")),
        ("unknown-artifact", lambda root: (root / "artifacts/unknown.json").write_text("{}\n", encoding="utf-8")),
        ("path-escape", mutate_json("artifacts/input-manifest.json", lambda o: o["payload"]["members"][0].__setitem__("path", "../escape.jsonl"))),
    ]
    with tempfile.TemporaryDirectory(prefix="m8-v3-negative-") as temp:
        temp_root = Path(temp)
        for name, mutation in cases:
            source = FIXTURES / ("failure-cleanup" if name == "failure-as-success" else "success")
            target = temp_root / name
            shutil.copytree(source, target)
            mutation(target)
            result = run(target)
            ok = result.returncode != 0
            print(("PASS" if ok else "FAIL") + f" negative {name}")
            if not ok:
                failures.append(f"negative {name} was accepted: {result.stdout}")

    if failures:
        print("\n".join(failures))
        return 1
    print(f"ALL PASS: {len(expected)} persistent graphs + {len(cases)} fail-closed mutations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
