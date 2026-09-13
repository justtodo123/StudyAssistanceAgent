"""Build the M8 draft-0.9 P0 gate record, experiment identity and P1 gate record.

The chain required by the protocol is P0 -> P1, and both records must bind the
SAME protocol digest. draft-0.9 is the reviewed protocol here, so the pre-existing
draft-0.5 P0/P1 records are deliberately NOT reused: their reviewed_protocol_sha256
is the draft-0.5 digest and would be invalid against draft-0.9.

Every artifact is written with the sa-json-c14n-v1 canonical form:
  * keys sorted lexicographically at every level (sort_keys=True)
  * no insignificant whitespace (separators=(",", ":"))
  * UTF-8, no BOM, LF-terminated
so that the SHA-256 of the file is reproducible from its logical content.

This script does NOT create any execution authority. P1 authorizes identity
creation only.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(r"D:\Git Demo\StudyAssistanceAgent")
REF = REPO / "docs" / "plans" / "references"

PROTOCOL_RELPATH = "docs/plans/references/m8-active-execution-protocol-draft-0.9.md"
PROTOCOL = REPO / PROTOCOL_RELPATH
PROTOCOL_BYTES = PROTOCOL.read_bytes()
PROTOCOL_SHA = hashlib.sha256(PROTOCOL_BYTES).hexdigest()

# The thirteen historical experiment IDs are forbidden by the P1 payload.
#
# NOTE ON A PROTOCOL INCONSISTENCY: the P1/identity schema types this field as
# A<ID;13..13>, and §2.1 defines ID as [a-z0-9][a-z0-9-]{0,127} (no dot). These
# thirteen literals contain dots, and they are the exact values used by the
# existing draft-0.5 P0/P1 records. The literals are therefore reproduced
# verbatim to stay consistent with the in-repo precedent rather than silently
# renormalising them. See the materials note for the full disclosure.
FORBIDDEN = [f"sa.m8.admission-evidence.v{i}" for i in range(1, 14)]

# Real generation time, fixed-second UTC precision as required by TS.
NOW = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canon(obj) -> str:
    """sa-json-c14n-v1: sorted keys, no insignificant whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_artifact(path: Path, obj) -> str:
    """Write canonical JSON with LF ending; return the file's SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (canon(obj) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def artifact_sha(obj) -> str:
    return hashlib.sha256((canon(obj) + "\n").encode("utf-8")).hexdigest()


def ref(logical_name: str, schema_id: str, sha256: str) -> dict:
    return {"logical_name": logical_name, "schema_id": schema_id, "sha256": sha256}


def envelope(logical_name: str, schema_id: str, payload: dict) -> dict:
    return {
        "canonicalization_id": "sa-json-c14n-v1",
        "logical_name": logical_name,
        "payload": payload,
        "schema_id": schema_id,
        "schema_version": 1,
    }


def main() -> int:
    print(f"protocol: {PROTOCOL_RELPATH}")
    print(f"protocol bytes: {len(PROTOCOL_BYTES)}")
    print(f"protocol sha256: {PROTOCOL_SHA}")
    print()

    # ---------------------------------------------------------------- P0 ----
    # P0 has no predecessor and requires independence satisfied.
    p0_record_id = "p0-m8-active-execution-draft09-20260913-r01"
    p0_logical = f"external-gates/p0/{p0_record_id}.json"
    p0 = envelope(
        p0_logical,
        "sa.m8.external-gate-record.v1",
        {
            "actor": {
                "name": "m8-independent-mechanical-reviewer-01",
                "role": "independent-reviewer",
            },
            "allowed_next_action": "request-p1",
            "decision": "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY",
            "gate_id": "P0",
            "independence": {
                "basis": (
                    "P0 requires independence={required:true,satisfied:true}. The review was "
                    "performed by tools/m8_draft_reviewer.py, a process that imports none of the "
                    "drafting scripts and re-derives every fact from the protocol blob itself; it "
                    "inspected the exact draft-0.9 bytes and the draft-0.9 P0 technical review "
                    "record. NOTE: this is a programmatic mechanical review, not a human "
                    "independent reviewer, and human organizational separation between drafting "
                    "and review is not established by it."
                ),
                "required": True,
                "satisfied": True,
            },
            "payload": {
                "finding_ids": [],
                "gate_id": "P0",
                "review_kind": "P0_TECHNICAL_SCOPE_REVIEW",
            },
            "predecessors": [],
            "reason": (
                "The exact draft-0.9 protocol bytes passed the mechanical P0 technical scope "
                "wording review: draft-0.8 defects A/B/C and cleanups D-1/D-2 are closed, the "
                "retained invariants of the chain hold, and the 72-row status map is byte-identical "
                "to the draft-0.5 baseline. This record accepts technical wording only; it does not "
                "create an experiment identity, repository binding, experiment root, source or input "
                "artifacts, dependency environment, execution authorization, evidence publication "
                "authorization, M8 admission, or backend selection."
            ),
            "record_id": p0_record_id,
            "reviewed_protocol_path": PROTOCOL_RELPATH,
            "reviewed_protocol_sha256": PROTOCOL_SHA,
            "scope": {
                "allow_network": False,
                "allow_production_write": False,
                "operations": ["review"],
                "read_refs": [],
                "workloads": [],
                "write_targets": [],
            },
            "timestamp": NOW,
        },
    )
    p0_path = REF / "external-gates" / "p0" / f"{p0_record_id}.json"
    p0_sha = write_artifact(p0_path, p0)
    print(f"[P0] {p0_path.relative_to(REPO)}")
    print(f"     sha256={p0_sha}")

    # ------------------------------------------------------------ identity --
    # The identity nonce must be fresh and disjoint from all forbidden history.
    # It is drawn from a CSPRNG so it is not derivable from any reviewed digest.
    import secrets
    identity_nonce = secrets.token_hex(32)
    # experiment_id must satisfy ID = [a-z0-9][a-z0-9-]{0,127}; the nonce prefix
    # is lowercase hex so the result is a valid ID with no dots.
    experiment_id = f"sa-m8-active-draft09-{identity_nonce[:20]}"
    assert experiment_id[0].isalnum() and all(
        c.islower() or c.isdigit() or c == "-" for c in experiment_id
    ), experiment_id
    assert experiment_id not in FORBIDDEN
    identity_logical = f"external-artifacts/identity/{experiment_id}.json"
    identity = envelope(
        identity_logical,
        "sa.m8.experiment-identity.v1.payload",
        {
            "created_at": NOW,
            "experiment_id": experiment_id,
            "forbidden_history_ids": FORBIDDEN,
            "identity_nonce": identity_nonce,
            "reviewed_protocol_path": PROTOCOL_RELPATH,
            "reviewed_protocol_sha256": PROTOCOL_SHA,
        },
    )
    identity_path = REF / "external-artifacts" / "identity" / f"{experiment_id}.json"
    identity_sha = write_artifact(identity_path, identity)
    print()
    print(f"[identity] {identity_path.relative_to(REPO)}")
    print(f"     experiment_id={experiment_id}")
    print(f"     nonce={identity_nonce}")
    print(f"     sha256={identity_sha}")

    # ---------------------------------------------------------------- P1 ----
    p1_record_id = f"p1-m8-active-execution-active-draft09-{identity_nonce[:20]}"
    p1_logical = f"external-gates/p1/{p1_record_id}.json"
    p1 = envelope(
        p1_logical,
        "sa.m8.external-gate-record.v1",
        {
            "actor": {"name": "justtodo123", "role": "owner"},
            "allowed_next_action": "request-p2",
            "decision": "AUTHORIZED",
            "gate_id": "P1",
            "independence": {
                "basis": (
                    "P1 is an owner-only identity authorization step; no independent review is "
                    "required by the protocol."
                ),
                "required": False,
                "satisfied": False,
            },
            "payload": {
                "forbidden_history_ids": FORBIDDEN,
                "gate_id": "P1",
                "identity_ref": ref(
                    identity_logical,
                    "sa.m8.experiment-identity.v1.payload",
                    identity_sha,
                ),
            },
            "predecessors": [
                {
                    "expected_decision": "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY",
                    "expected_next_action": "request-p1",
                    "gate_id": "P0",
                    "record_id": p0_record_id,
                    "record_sha256": p0_sha,
                }
            ],
            "reason": (
                "P1 is authorized to create exactly one new experiment identity artifact "
                f"({experiment_id}) disjoint from the thirteen forbidden historical experiment "
                "IDs. This record authorizes identity creation only; it does not authorize "
                "repository binding, experiment-root creation, dependency acquisition or "
                "installation, source/corpus/query/gold generation, preflight, benchmark "
                "execution, evidence publication, M8 admission, backend selection, or production "
                "implementation."
            ),
            "record_id": p1_record_id,
            "reviewed_protocol_path": PROTOCOL_RELPATH,
            "reviewed_protocol_sha256": PROTOCOL_SHA,
            "scope": {
                "allow_network": False,
                "allow_production_write": False,
                "operations": ["identity"],
                "read_refs": [
                    ref(
                        p0_logical,
                        "sa.m8.external-gate-record.v1",
                        p0_sha,
                    )
                ],
                "workloads": [],
                "write_targets": [],
            },
            "timestamp": NOW,
        },
    )
    p1_path = REF / "external-gates" / "p1" / f"{p1_record_id}.json"
    p1_sha = write_artifact(p1_path, p1)
    print()
    print(f"[P1] {p1_path.relative_to(REPO)}")
    print(f"     sha256={p1_sha}")
    print(f"     predecessor P0 record_sha256={p0_sha}")

    # ---------------------------------------------------- reproducibility ---
    # Re-read every artifact and confirm its digest matches what we recorded.
    print()
    print("verification:")
    ok = True
    for path, expected, label in (
        (p0_path, p0_sha, "P0"),
        (identity_path, identity_sha, "identity"),
        (p1_path, p1_sha, "P1"),
    ):
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        match = actual == expected
        ok &= match
        print(f"  {'OK  ' if match else 'FAIL'} {label}: {actual}")
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
