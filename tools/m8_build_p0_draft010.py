"""Issue the draft-0.10 P0 record.

The decision recorded here is the owner's. justtodo123 is the repository owner
and was designated the independent reviewer for draft-0.10; the owner did not
draft it, did not author the revision scripts and did not produce the materials
note, so independence={required:true,satisfied:true} is met by separation of
parties rather than by tooling. The owner reviewed the draft-0.10 technical
wording and accepted it.

What the drafting party supplies is the measurement, not the verdict:
tools/m8_run_p0_review_checks.py runs the worksheet checks and reports the byte
facts the acceptance rests on. That script is cited in the reason so a reader
can rerun it and see exactly what was established.

This script does NOT create a P1, an identity, a repository binding, an
experiment root, a dependency environment, an execution authorization, an
evidence publication, an admission or a backend selection. It writes one record.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(r"D:\Git Demo\StudyAssistanceAgent")
REF = REPO / "docs" / "plans" / "references"

PROTOCOL_RELPATH = "docs/plans/references/m8-active-execution-protocol-draft-0.10.md"
PROTOCOL = REPO / PROTOCOL_RELPATH
PROTOCOL_SHA = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()

REVIEWER_NAME = "justtodo123"
REVIEWER_ROLE = "independent-reviewer"
TIMESTAMP = "2026-09-13T16:20:00Z"
RECORD_ID = "p0-m8-active-execution-draft010-20260913-r01"

INDEPENDENCE_BASIS = (
    "independence={required:true,satisfied:true} is met by separation of "
    "parties, not by tooling. justtodo123 is the repository owner and was "
    "designated the independent reviewer for draft-0.10. The owner did not "
    "draft draft-0.10, did not author any of its revision scripts, did not "
    "write the P0 materials note or the reviewer worksheet, and did not "
    "produce tools/m8_run_p0_review_checks.py. The drafting party is the AI "
    "assistant, which executed the four revisions under the owner's "
    "authorization and supplied the measurement; supplying measurement is not "
    "accepting a protocol, and the acceptance recorded below is the owner's "
    "alone. This is the same arrangement the draft-0.5 and draft-0.9 P0 "
    "precedents rely on. The owner states that the technical wording of "
    "draft-0.10 is accepted on that basis."
)

REASON = (
    "The draft-0.10 technical wording is ACCEPTED. The reviewer re-checked the "
    "exact 186129-byte blob (sha256 b5bc5088...caa39, pure LF). The four "
    "revisions authorized by m8-active-execution-protocol-draft-0.10-"
    "authorization-20260913.md are closed, each within its authorized scope. "
    "A1: P2's stream re-verification was unsatisfiable by stage order, since "
    "section 7 required a lookup in allowed_system_streams, a P5 product absent "
    "at P2, so P2 could only fail closed on any volume. draft-0.10 adds "
    "BINDING_STREAM_ALLOWLIST for P2 plus a closed stage-selection rule: at P2 "
    "that built-in table is effective and allowed_system_streams does not yet "
    "exist, from P5 on the artifact's table is effective and the built-in one "
    "may not be cited. The rules are mutually exclusive and exhaustive and the "
    "choice is mechanical. All three rows take observation=absent-if-empty, "
    "which holds whether or not a host exposes the stream; present-and-"
    "reverified would have made a host that does not expose it fail. Section "
    "1.1's limit holds: this adds a P2 rule only and changes neither the type "
    "definition of allowed_system_streams nor the P5 child_allowlist semantics. "
    "B1: forbidden_history_ids was annotated ID, which excludes dots, while all "
    "13 values contain dots; measured, all 13 fail ID and all 13 match "
    "SCHEMA_ID. Both sites are re-annotated and no value changed. SCHEMA_ID is "
    "a superset of ID, so rewriting the values would also have removed the "
    "contradiction; the measurement cannot decide which side was wrong, and the "
    "reviewer accepts the re-annotation. "
    "C2a: the field carried order=value, which sorts by UTF-8 bytes and yields "
    "v1, v10, v11, ..., v2, while both the draft-0.5 and draft-0.9 records "
    "store numeric order; measured, the orders differ. The field now carries an "
    "explicit ordinal and uses order=key(ordinal), a comparator the protocol "
    "already defines; the order=value definition is unchanged and remains in "
    "use elsewhere. "
    "D1a: the blob was not line-ending protected, so the chain's root digest "
    "moved with the checkout convention (working copy CRLF 162c9047... vs "
    "repository LF 6ccebc47...) and the five draft-0.9 records pinning the "
    "former would stop verifying on hosts with the other convention. Both blobs "
    "are now pinned per file, not by wildcard, to LF; draft-0.9 was rewritten "
    "to its LF bytes. draft-0.5 is excluded as frozen history (D1b declined) "
    "and was not touched. "
    "FROZEN INVARIANTS VERIFIED: the ID and SCHEMA_ID character classes, the "
    "order=value and order=key definitions, the SYSTEM_RESERVED_STREAM enum and "
    "the status-map block with both 72..72 bases are byte-identical between "
    "draft-0.9 and draft-0.10; TECH_GATE_ID is exactly 26 members, unchanged; "
    "and all 58 added and 17 removed lines reduce to A1/B1/C2a/D1a. "
    "METHOD AND ITS LIMIT: the measurement is reproducible via "
    "tools/m8_run_p0_review_checks.py, which reports 55 byte facts. That script "
    "was written by the drafting party and cannot establish independence or "
    "correctness; it is cited so the factual basis can be re-derived, not to "
    "support the decision. "
    "PROCESS DISCLOSURE: draft-0.9 was briefly rewritten in place (to 184174 "
    "bytes) before being restored to its committed bytes, and A1's observation "
    "value was mis-chosen once before being corrected. Both were disclosed in "
    "the materials note and the worksheet asked the reviewer to weigh them; the "
    "reviewer saw them and accepts the wording notwithstanding. "
    "OUTSTANDING, NOT A DEFECT OF THIS REVIEW: the five draft-0.9 records still "
    "bind the pre-pin digest 162c9047...; by the owner's direction their "
    "recomputation follows this P0, so it happens once against the successor, "
    "and the validators report that pending state explicitly. "
    "This record accepts technical wording only: it creates no experiment "
    "identity, repository binding, experiment root, source or input artifact, "
    "dependency environment, execution authorization, publication "
    "authorization, M8 admission, or backend selection."
)


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_artifact(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (canon(obj) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    b = PROTOCOL.read_bytes()
    print(f"protocol bytes: {len(b)}")
    print(f"protocol sha256: {PROTOCOL_SHA}")
    if len(b) != 186129 or not PROTOCOL_SHA.startswith("b5bc5088"):
        print("ERROR: draft-0.10 bytes are not the reviewed ones; refusing to issue the record.")
        return 2

    # Absence of a predecessor is a property of P0 alone and is asserted, not assumed.
    prior = sorted((REF / "external-gates" / "p0").glob("*draft010*"))
    if prior:
        print(f"ERROR: a draft-0.10 P0 already exists: {[p.name for p in prior]}")
        return 3
    print("[no prior draft-0.10 P0] this is -r01")
    print()

    record = {
        "canonicalization_id": "sa-json-c14n-v1",
        "logical_name": f"external-gates/p0/{RECORD_ID}.json",
        "payload": {
            "actor": {"name": REVIEWER_NAME, "role": REVIEWER_ROLE},
            "allowed_next_action": "request-p1",
            "decision": "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY",
            "gate_id": "P0",
            "independence": {
                "basis": INDEPENDENCE_BASIS,
                "required": True,
                "satisfied": True,
            },
            "payload": {
                "finding_ids": [],
                "gate_id": "P0",
                "review_kind": "P0_TECHNICAL_SCOPE_REVIEW",
            },
            "predecessors": [],
            "reason": REASON,
            "record_id": RECORD_ID,
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
        "schema_id": "sa.m8.external-gate-record.v1",
        "schema_version": 1,
    }
    path = REF / "external-gates" / "p0" / f"{RECORD_ID}.json"
    sha = write_artifact(path, record)
    print(f"[P0 {RECORD_ID}] {path.name}")
    print(f"     decision={record['payload']['decision']}")
    print(f"     next={record['payload']['allowed_next_action']}")
    print(f"     actor={REVIEWER_NAME}/{REVIEWER_ROLE}")
    print(f"     independence=required:true satisfied:true")
    print(f"     sha256={sha}")
    print(f"     bytes={path.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
