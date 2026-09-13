"""Issue the draft-0.9 P0 -r02 record and rebuild P1 on top of it.

Background. The draft-0.9 P0 -r01 record is P0_NOT_ACCEPTED because the actor
that drafted the revision also performed its mechanical verification, so
independence={required:true,satisfied:true} could not be met. The protocol does
not repair that by editing -r01: the state machine expects a P0 issued by a
reviewer who did not participate in the drafting round. That reviewer is the
repository owner acting as independent reviewer, and this script emits the
result of that review.

What this script does NOT do:
  * it does not rewrite -r01 or its dependent P1; both stay as history;
  * it does not touch the experiment identity, which is an input, not an
    output, and keeps its existing bytes;
  * it creates no repository binding, experiment root, dependency, source,
    input, preflight, execution, publication, admission or backend authority.

Only P0 -r02 and the P1 that binds it are (re)written.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(r"D:\Git Demo\StudyAssistanceAgent")
REF = REPO / "docs" / "plans" / "references"

PROTOCOL_RELPATH = "docs/plans/references/m8-active-execution-protocol-draft-0.9.md"
PROTOCOL = REPO / PROTOCOL_RELPATH
PROTOCOL_SHA = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()

# The reviewer's own decision and identity, supplied by that reviewer.
REVIEWER_NAME = "justtodo123"
REVIEWER_ROLE = "independent-reviewer"
REVIEWER_BASIS = (
    "independence={required:true,satisfied:true} is met by separation of "
    "parties, not by tooling: justtodo123 is the repository owner and did not "
    "draft draft-0.9, did not author any of its revision scripts, and did not "
    "produce the mechanical verification recorded in -r01. The owner acting as "
    "the independent reviewer is the same arrangement the draft-0.5 P0 "
    "precedent relies on; the reviewer identity differs from -r01's mechanical "
    "self-review actor (m8-mechanical-self-review-draft09-01), which is "
    "retained as history and is not superseded in its own right. The -r01 "
    "findings are treated as advisory input only; the accepting decision below "
    "is the reviewer's, and the reviewer states that the technical wording of "
    "draft-0.9 is accepted on that basis."
)

# The material set is one authoring act. -r02 is a distinct act with its own
# timestamp, deliberately later than -r01 (2026-09-13T13:20:50Z).
TIMESTAMP = "2026-09-13T14:05:00Z"


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_artifact(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (canon(obj) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def envelope(logical_name: str, schema_id: str, payload: dict) -> dict:
    return {
        "canonicalization_id": "sa-json-c14n-v1",
        "logical_name": logical_name,
        "payload": payload,
        "schema_id": schema_id,
        "schema_version": 1,
    }


def ref(logical_name: str, schema_id: str, sha256: str) -> dict:
    return {"logical_name": logical_name, "schema_id": schema_id, "sha256": sha256}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    print(f"protocol bytes: {len(PROTOCOL.read_bytes())}")
    print(f"protocol sha256: {PROTOCOL_SHA}")
    print()

    # ------------------------------------------------- locate prior records --
    r01_path = REF / "external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json"
    if not r01_path.exists():
        print(f"ERROR: -r01 not found at {r01_path}")
        return 2
    r01 = load(r01_path)
    r01_payload = r01["payload"]
    if r01_payload["record_id"] != "p0-m8-active-execution-draft09-20260913-r01":
        print("ERROR: unexpected -r01 record_id")
        return 2
    if r01_payload["decision"] != "P0_NOT_ACCEPTED":
        print(
            "ERROR: -r01 is no longer P0_NOT_ACCEPTED; refusing to overwrite the "
            "history of an accepted P0."
        )
        return 2
    r01_file_sha = hashlib.sha256(r01_path.read_bytes()).hexdigest()
    print(f"[r01 kept as history] {r01_path.name}")
    print(f"     decision={r01_payload['decision']} sha256={r01_file_sha}")

    # The identity is reused verbatim; it is not a product of this run.
    identities = sorted(
        p for p in (REF / "external-artifacts" / "identity").glob("*draft09*.json")
    )
    if len(identities) != 1:
        print(f"ERROR: expected exactly one draft-0.9 identity, found {len(identities)}")
        for p in identities:
            print("   ", p.name)
        return 3
    identity_path = identities[0]
    identity_sha = hashlib.sha256(identity_path.read_bytes()).hexdigest()
    identity = load(identity_path)
    experiment_id = identity["payload"]["experiment_id"]
    print(f"[identity reused] {identity_path.name}")
    print(f"     experiment_id={experiment_id} sha256={identity_sha}")
    print()

    # -------------------------------------------------------------- P0 -r02 --
    r02_record_id = "p0-m8-active-execution-draft09-20260913-r02"
    r02_logical = f"external-gates/p0/{r02_record_id}.json"
    r02 = envelope(
        r02_logical,
        "sa.m8.external-gate-record.v1",
        {
            "actor": {"name": REVIEWER_NAME, "role": REVIEWER_ROLE},
            "allowed_next_action": "request-p1",
            "decision": "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY",
            "gate_id": "P0",
            "independence": {
                "basis": REVIEWER_BASIS,
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
                "The draft-0.9 technical wording is ACCEPTED. The reviewer "
                "re-checked the exact 182575-byte draft-0.9 blob (sha256 "
                "162c9047ddeaceda59d7da79f8dfbf45234a89e2b00fd271e72473bbc6cca5b4) "
                "and accepts the technical scope wording: the draft-0.8 defects "
                "A (per-open STREAM_SCOPE, profile no longer carries "
                "opens_volume_root, walk freezes the volume-root identity up "
                "front), B (stream_scope_per_open replaces the scalar "
                "derived-from-profile field) and C (stream_query_source admits "
                "only opened-file-handle) are closed; the cleanups D-1 "
                "(decorative allowed_system_streams_closed removed from the "
                "schema) and D-2 (unreachable stream_reverify=not-applicable "
                "enum member removed, the stream_reverify field itself retained "
                "as the constant \"required\") are closed; the retained "
                "invariants of the chain hold; and the 72-row status map is "
                "byte-identical to the draft-0.5 baseline. This acceptance "
                "supersedes -r01's P0_NOT_ACCEPTED for the purpose of advancing "
                "the chain, because -r01 was rejected for want of independence "
                "rather than for any technical defect; -r01 is retained as "
                "history and its findings are not repudiated. NOTE ON THE "
                "REGISTERED DIGEST: the accepting review used the working-tree "
                "bytes (sha256 162c9047..., 182575 bytes, CRLF). The repository "
                "blob normalized to LF is 181209 bytes with sha256 "
                "6ccebc477dd54df4415998c8c03ffff3215d523cf2a42af128a8ff6a36e244a9, "
                "and the 1366-byte difference is exactly the 1366 CRLF pairs; "
                "the two are byte-identical apart from line endings. The "
                "working-tree digest is the registered one, consistent with the "
                "draft-0.5 precedent. This record accepts technical wording "
                "only: it creates no experiment identity, repository binding, "
                "experiment root, source or input artifact, dependency "
                "environment, execution authorization, evidence publication "
                "authorization, M8 admission, or backend selection. It does not "
                "supersede, close or delete -r01; both records stand, -r02 as "
                "the accepted P0 for draft-0.9 and -r01 as the record of why an "
                "accepted P0 could not be produced by the drafting actor."
            ),
            "record_id": r02_record_id,
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
            "timestamp": TIMESTAMP,
        },
    )
    r02_path = REF / "external-gates" / "p0" / f"{r02_record_id}.json"
    r02_sha = write_artifact(r02_path, r02)
    print(f"[P0 -r02] {r02_path.name}")
    print(f"     decision={r02['payload']['decision']}")
    print(f"     actor={REVIEWER_NAME}/{REVIEWER_ROLE}")
    print(f"     sha256={r02_sha}")
    print()

    # ------------------------------------------------------------------ P1 --
    # Issue a NEW P1 that binds the accepted -r02 instead of the rejected -r01.
    #
    # The prior P1 is NOT overwritten. It is an already-committed gate record
    # whose decision was NOT_AUTHORIZED; rewriting it in place would make one
    # record_id mean two different things across two commits and would destroy
    # the evidence of why the chain was blocked. Instead the new record takes a
    # distinct -r02 suffix of its own, so the -r02 P0 and the P1 that consumes
    # it share the same revision marker and downstream readers can tell the two
    # P1s apart by record_id alone.
    p1_suffix = experiment_id.split("draft09-")[1]
    prior_p1_path = (
        REF / "external-gates/p1"
        / f"p1-m8-active-execution-active-draft09-{p1_suffix}.json"
    )
    prior_p1 = load(prior_p1_path)
    prior_p1_decision = prior_p1["payload"]["decision"]
    if prior_p1_decision != "NOT_AUTHORIZED":
        print(
            f"ERROR: the prior P1 is {prior_p1_decision}, not NOT_AUTHORIZED; "
            "refusing to issue a parallel record over an authorized chain."
        )
        return 4
    prior_p1_sha = hashlib.sha256(prior_p1_path.read_bytes()).hexdigest()
    forbidden_ids = prior_p1["payload"]["payload"]["forbidden_history_ids"]
    print(f"[P1 prior kept as history] {prior_p1_path.name}")
    print(f"     decision={prior_p1_decision} sha256={prior_p1_sha}")
    print()

    p1_record_id = (
        f"p1-m8-active-execution-active-draft09-{p1_suffix}-r02"
    )
    p1_logical = f"external-gates/p1/{p1_record_id}.json"
    p1_path = REF / "external-gates" / "p1" / f"{p1_record_id}.json"
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
                    "P1 is an owner-only identity authorization step; the "
                    "protocol requires no independent review at this gate."
                ),
                "required": False,
                "satisfied": False,
            },
            "payload": {
                "forbidden_history_ids": forbidden_ids,
                "gate_id": "P1",
                "identity_ref": ref(
                    identity["logical_name"],
                    "sa.m8.experiment-identity.v1.payload",
                    identity_sha,
                ),
            },
            "predecessors": [
                {
                    "expected_decision": "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY",
                    "expected_next_action": "request-p1",
                    "gate_id": "P0",
                    "record_id": r02_record_id,
                    "record_sha256": r02_sha,
                }
            ],
            "reason": (
                "P1 is authorized to create exactly one new experiment identity "
                f"artifact ({experiment_id}) disjoint from the thirteen "
                "forbidden historical experiment IDs. The predecessor edge is "
                "satisfied by P0 -r02 "
                f"({r02_record_id}), which accepted the draft-0.9 technical "
                "wording and authorizes request-p1. This record supersedes the "
                "earlier P1 for draft-0.9, which was NOT_AUTHORIZED because its "
                "predecessor there was the P0_NOT_ACCEPTED -r01; that earlier P1 "
                "is retained unchanged as history under its own record_id and is "
                "not deleted or rewritten. This record authorizes identity "
                "creation only; it does not authorize repository binding, "
                "experiment-root creation, dependency acquisition or "
                "installation, source/corpus/query/gold generation, preflight, "
                "benchmark execution, evidence publication, M8 admission, "
                "backend selection, or production implementation."
            ),
            "record_id": p1_record_id,
            "reviewed_protocol_path": PROTOCOL_RELPATH,
            "reviewed_protocol_sha256": PROTOCOL_SHA,
            "scope": {
                "allow_network": False,
                "allow_production_write": False,
                "operations": ["identity"],
                "read_refs": [
                    ref(r02_logical, "sa.m8.external-gate-record.v1", r02_sha)
                ],
                "workloads": [],
                "write_targets": [],
            },
            "timestamp": TIMESTAMP,
        },
    )
    p1_sha = write_artifact(p1_path, p1)
    print(f"[P1 rebuilt] {p1_path.name}")
    print(f"     decision={p1['payload']['decision']}")
    print(f"     predecessor={r02_record_id} sha256={r02_sha}")
    print(f"     sha256={p1_sha}")
    print()

    # ---------------------------------------------------- reproducibility ----
    print("verification:")
    ok = True
    for path, expected, label in (
        (r02_path, r02_sha, "P0 -r02"),
        (p1_path, p1_sha, "P1 -r02"),
        (identity_path, identity_sha, "identity (unchanged)"),
        (r01_path, r01_file_sha, "P0 -r01 (unchanged history)"),
        (prior_p1_path, prior_p1_sha, "P1 prior (unchanged history)"),
    ):
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        match = actual == expected
        ok &= match
        print(f"  {'OK  ' if match else 'FAIL'} {label}: {actual}")
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
