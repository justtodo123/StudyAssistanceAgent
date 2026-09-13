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

IMPORTANT — P0 INDEPENDENCE IS NOT ESTABLISHED:
The drafting and the mechanical review of draft-0.9 were performed by the same
actor. The protocol gating chain treats P0 as the single gate that explicitly
requires independence={required:true,satisfied:true}, so recording satisfied=true
here would be an unverifiable self-attestation. The P0 record is therefore
emitted with independence.satisfied=false, decision=P0_NOT_ACCEPTED and
allowed_next_action=stop, and P1 is emitted as NOT_AUTHORIZED. This is the
honest state: the technical wording passed, but the P0 gate has NOT been
discharged and must be re-established by a reviewer who did not participate in
this round.
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
#
# The timestamp is fixed at the moment the material set was first formed: the
# P0/identity/P1 records describe one single authoring act, and re-running this
# script to correct a field must NOT silently restamp the material set (that
# would make the bytes non-reproducible and would alter artifacts that are not
# the subject of the correction). Pass --restamp to deliberately issue a new
# material set with a fresh timestamp.
_STAMPED = "2026-09-13T13:20:50Z"
NOW = (
    _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "--restamp" in sys.argv
    else _STAMPED
)


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
    # P0 has no predecessor. The protocol requires independence true/true here,
    # but that requirement is NOT met: the same actor drafted and reviewed. The
    # record is therefore emitted as a PENDING-REVIEW, NOT-ACCEPTED P0.
    #
    # The id keeps the -r01 suffix; this is the first (and so far only) record
    # for draft-0.9, and it is explicitly marked as not discharged so that a
    # future independent reviewer can issue -r02 without ambiguity.
    p0_record_id = "p0-m8-active-execution-draft09-20260913-r01"
    p0_logical = f"external-gates/p0/{p0_record_id}.json"
    p0 = envelope(
        p0_logical,
        "sa.m8.external-gate-record.v1",
        {
            # The role stays independent-reviewer because the protocol's role
            # enum has no "self-review" member and this record is a P0 review
            # attempt. The name is deliberately NOT the human reviewer identity
            # used by earlier drafts: it is labelled mechanical so it cannot be
            # mistaken for the human independent reviewer that P0 requires.
            "actor": {
                "name": "m8-mechanical-self-review-draft09-01",
                "role": "independent-reviewer",
            },
            "allowed_next_action": "stop",
            "decision": "P0_NOT_ACCEPTED",
            "gate_id": "P0",
            "independence": {
                "basis": (
                    "P0 requires independence={required:true,satisfied:true}. The mechanical "
                    "verification is reproducible: tools/m8_draft_reviewer.py imports none of the "
                    "drafting scripts and re-derives every fact from the protocol blob itself, and "
                    "it inspected the exact draft-0.9 bytes. HOWEVER, SUBSTANTIVE INDEPENDENCE IS "
                    "NOT ESTABLISHED: the drafting and the review were performed by the same "
                    "actor, and the protocol provides no mechanism by which the same actor can "
                    "satisfy its own independence requirement. The reviewer state is recorded as "
                    "declared-but-unverified and satisfied=false, so the draft-0.9 P0 gate remains "
                    "undischarged pending a human reviewer who did not participate in this round. "
                    "Do NOT treat this record as an accepted P0."
                ),
                "required": True,
                "satisfied": False,
            },
            "payload": {
                "finding_ids": [],
                "gate_id": "P0",
                "review_kind": "P0_TECHNICAL_SCOPE_REVIEW",
            },
            "predecessors": [],
            "reason": (
                "THE DRAFT-0.9 P0 GATE IS NOT DISCHARGED. The exact draft-0.9 protocol bytes did "
                "pass the mechanical technical scope wording checks (draft-0.8 defects A/B/C and "
                "cleanups D-1/D-2 are closed, the retained invariants of the chain hold, and the "
                "72-row status map is byte-identical to the draft-0.5 baseline), and those findings "
                "are reproducible. The record is nonetheless issued as P0_NOT_ACCEPTED because "
                "independence={required:true,satisfied:true} is NOT met: the same actor drafted "
                "and mechanically reviewed this revision, and a mechanical self-review cannot "
                "discharge the protocol's independence requirement. The technical wording "
                "findings are preserved for the benefit of the next reviewer; they are NOT an "
                "acceptance, and the P0 gate must be re-established by a reviewer who did not "
                "participate in this round. This record creates no experiment identity, repository "
                "binding, experiment root, source or input artifacts, dependency environment, "
                "execution authorization, evidence publication authorization, M8 admission, or "
                "backend selection."
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
    #
    # IMPORTANT: the identity is NOT a product of this run. It is an input. If a
    # draft-0.9 identity already exists in the repository it is REUSED verbatim,
    # because re-minting it would orphan the previously published artifact and
    # create a second, unrelated experiment identity. A new identity is minted
    # only when no draft-0.9 identity exists yet (or --new-identity is passed).
    import secrets
    existing_identities = sorted(
        p for p in (REF / "external-artifacts" / "identity").glob("*draft09*.json")
    )
    mint_new = "--new-identity" in sys.argv or not existing_identities
    if not mint_new:
        if len(existing_identities) > 1:
            print("ERROR: multiple draft-0.9 identities exist; refusing to guess:")
            for p in existing_identities:
                print("   ", p.name)
            return 2
        identity_path = existing_identities[0]
        identity_existing = json.loads(identity_path.read_text(encoding="utf-8"))
        experiment_id = identity_existing["payload"]["experiment_id"]
        identity_nonce = identity_existing["payload"]["identity_nonce"]
        print(f"[identity] reusing existing: {identity_path.name}")
        print(f"     experiment_id={experiment_id}")
        print()
    else:
        identity_nonce = secrets.token_hex(32)
        # experiment_id must satisfy ID = [a-z0-9][a-z0-9-]{0,127}; the nonce
        # prefix is lowercase hex so the result is a valid ID with no dots.
        experiment_id = f"sa-m8-active-draft09-{identity_nonce[:20]}"
    assert experiment_id[0].isalnum() and all(
        c.islower() or c.isdigit() or c == "-" for c in experiment_id
    ), experiment_id
    assert experiment_id not in FORBIDDEN
    identity_logical = f"external-artifacts/identity/{experiment_id}.json"
    # When reusing, rebuild the artifact from its own payload so the canonical
    # bytes are re-derived rather than trusted; a mismatch means the on-disk
    # identity was hand-edited and is reported instead of silently overwritten.
    if not mint_new:
        expected_existing = envelope(
            identity_logical,
            "sa.m8.experiment-identity.v1.payload",
            identity_existing["payload"],
        )
        # The reused identity keeps its original created_at: it records when
        # the identity came into being, which is not the time of this run.
        if canon(expected_existing) + "\n" != canon(identity_existing) + "\n":
            print("ERROR: existing identity is not in canonical form; refusing to proceed")
            return 3
    identity = envelope(
        identity_logical,
        "sa.m8.experiment-identity.v1.payload",
        {
            "created_at": (
                identity_existing["payload"]["created_at"] if not mint_new else NOW
            ),
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
            "allowed_next_action": "stop",
            "decision": "NOT_AUTHORIZED",
            "gate_id": "P1",
            "independence": {
                "basis": (
                    "P1 is an owner-only identity authorization step, so the protocol requires "
                    "no independent review at this gate; independence is not the reason this "
                    "record is withheld. The identity is NOT AUTHORIZED because its sole "
                    "predecessor, the draft-0.9 P0 record, is P0_NOT_ACCEPTED: the P0 gate is "
                    "undischarged and therefore cannot authorize a request-p1. P1 may only be "
                    "issued once a P0 for draft-0.9 has been accepted by a reviewer who did not "
                    "participate in drafting or in this round of review."
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
                "P1 IS NOT AUTHORIZED. The identity artifact "
                f"({experiment_id}) is prepared and disjoint from the thirteen forbidden "
                "historical experiment IDs, but its predecessor P0 record is P0_NOT_ACCEPTED "
                "with satisfied=false independence, so the P0->P1 edge is not satisfied and no "
                "request-p1 may be granted. This record grants nothing: not identity activation, "
                "not repository binding, not experiment-root creation, not dependency acquisition "
                "or installation, not source/corpus/query/gold generation, not preflight, not "
                "benchmark execution, not evidence publication, not M8 admission, not backend "
                "selection, and not production implementation. P1 may be re-issued only after a "
                "P0 for draft-0.9 is accepted by a reviewer who did not participate in drafting "
                "or in this round of review."
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
    print("     decision=NOT_AUTHORIZED (predecessor P0 is P0_NOT_ACCEPTED)")

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
