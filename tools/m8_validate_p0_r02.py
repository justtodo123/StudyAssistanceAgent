"""Independently validate the draft-0.9 P0 -r02 record and its rebuilt P1.

This validator re-derives everything from the files and the protocol text. It
does not import the build script. It also checks the history-preservation
property that matters here: -r01 and the prior P1 must be untouched, and the
chain must advance through -r02 rather than by rewriting the rejected records.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(r"D:\Git Demo\StudyAssistanceAgent")
REF = REPO / "docs" / "plans" / "references"

PROTOCOL_RELPATH = "docs/plans/references/m8-active-execution-protocol-draft-0.9.md"
PROTOCOL = REPO / PROTOCOL_RELPATH

R01 = REF / "external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json"
R02 = REF / "external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json"
P1_OLD = REF / "external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json"
P1_NEW = (
    REF / "external-gates/p1"
    / "p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json"
)
IDENTITY = REF / "external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json"

# Digests of the records as they were committed before -r02 was issued. If any
# of these drift, history was mutated and the whole exercise is void.
R01_EXPECTED_SHA = "772a76ad6fc861dcd589a2fd4dbaed0be9ed604fc5069d0cb829da355ab16c6c"
P1_OLD_EXPECTED_SHA = "a17742af1246b6c46f001cc4a0ff2c3792dd86adaa47d770c235501f53cd0da8"
IDENTITY_EXPECTED_SHA = "5ba25bd8a7fb50d635a4b0b396f00876464028d189b61860f1961cb0913ebe1f"

RE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
RE_HEX64 = re.compile(r"^[0-9a-f]{64}$")
RE_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

GATE_DECISIONS = {
    "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY", "P0_NOT_ACCEPTED",
    "AUTHORIZED", "NOT_AUTHORIZED", "VERIFIED", "REJECTED",
    "PUBLICATION_REFUSED", "ADMITTED", "NOT_ADMITTED",
    "SELECT_LANCEDB_EXACT_FLAT", "SELECT_SQLITE_NO_CHANGE",
}
NEXT_ACTIONS = {
    "none", "request-p1", "request-p2", "request-p3", "request-p4",
    "request-p5", "request-p6", "run-l0", "request-p7a", "write-package",
    "run-nonpublication-cleanup", "run-abort-cleanup", "request-p8",
    "request-p9", "stop",
}
ACTOR_ROLES = {"owner", "independent-reviewer", "independent-verifier"}

results: list[tuple[str, bool, str]] = []


def ck(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


protocol_sha = sha(PROTOCOL)
for label, path in (("P0 -r01", R01), ("P0 -r02", R02), ("P1 prior", P1_OLD),
                    ("P1 -r02", P1_NEW), ("identity", IDENTITY)):
    ck(f"{label}: exists", path.exists())
if not all(p.exists() for p in (R01, R02, P1_OLD, P1_NEW, IDENTITY)):
    for n, ok, d in results:
        if not ok:
            print("MISSING:", n)
    sys.exit(1)

r01, r02, p1o, p1n, ident = (load(p) for p in (R01, R02, P1_OLD, P1_NEW, IDENTITY))

# ------------------------------------------------- history preservation ----
ck("HISTORY: P0 -r01 bytes unchanged since it was committed",
   sha(R01) == R01_EXPECTED_SHA, sha(R01))
ck("HISTORY: P0 -r01 still records P0_NOT_ACCEPTED",
   r01["payload"]["decision"] == "P0_NOT_ACCEPTED")
ck("HISTORY: P1 prior bytes unchanged since it was committed",
   sha(P1_OLD) == P1_OLD_EXPECTED_SHA, sha(P1_OLD))
ck("HISTORY: P1 prior still records NOT_AUTHORIZED",
   p1o["payload"]["decision"] == "NOT_AUTHORIZED")
ck("HISTORY: identity bytes unchanged",
   sha(IDENTITY) == IDENTITY_EXPECTED_SHA, sha(IDENTITY))
ck("HISTORY: P0 -r01 and P0 -r02 are distinct records",
   r01["payload"]["record_id"] != r02["payload"]["record_id"])
ck("HISTORY: P1 prior and P1 -r02 are distinct records",
   p1o["payload"]["record_id"] != p1n["payload"]["record_id"])

# ------------------------------------------------------ canonical form -----
for label, path in (("P0 -r02", R02), ("P1 -r02", P1_NEW)):
    raw = path.read_bytes()
    ck(f"{label}: file is sa-json-c14n-v1 canonical",
       raw == (canon(json.loads(raw.decode("utf-8"))) + "\n").encode("utf-8"))
    ck(f"{label}: no BOM and LF-terminated",
       raw[:3] != b"\xef\xbb\xbf" and raw.endswith(b"\n"))

# ------------------------------------------------------- protocol binding --
for label, obj in (("P0 -r02", r02), ("P1 -r02", p1n)):
    pl = obj["payload"]
    ck(f"{label}: reviewed_protocol_path is draft-0.9",
       pl["reviewed_protocol_path"] == PROTOCOL_RELPATH)
    ck(f"{label}: reviewed_protocol_sha256 == actual protocol digest",
       pl["reviewed_protocol_sha256"] == protocol_sha)
    ck(f"{label}: record_id matches ID grammar",
       bool(RE_ID.match(pl["record_id"])), pl["record_id"])
    ck(f"{label}: timestamp matches TS grammar",
       bool(RE_TS.match(pl["timestamp"])), pl["timestamp"])
    ck(f"{label}: actor role in protocol enum",
       pl["actor"]["role"] in ACTOR_ROLES, pl["actor"]["role"])
    ck(f"{label}: decision in GATE_DECISION enum",
       pl["decision"] in GATE_DECISIONS, pl["decision"])
    ck(f"{label}: next action in NEXT_ACTION enum",
       pl["allowed_next_action"] in NEXT_ACTIONS, pl["allowed_next_action"])
    ck(f"{label}: logical_name follows external-gates/<gate>/<record_id>.json",
       obj["logical_name"].endswith(f"/{pl['record_id']}.json"), obj["logical_name"])

# --------------------------------------------------------- P0 -r02 shape ---
r2 = r02["payload"]
ck("P0 -r02: gate_id == P0", r2["gate_id"] == "P0")
ck("P0 -r02: has no predecessor", r2["predecessors"] == [])
ck("P0 -r02: decision accepted-only",
   r2["decision"] == "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY")
ck("P0 -r02: allowed_next_action == request-p1",
   r2["allowed_next_action"] == "request-p1")
ck("P0 -r02: independence required+satisfied (P0 requires true/true)",
   r2["independence"]["required"] is True
   and r2["independence"]["satisfied"] is True)
ck("P0 -r02: actor name is the reviewer-supplied identity",
   r2["actor"]["name"] == "justtodo123", r2["actor"]["name"])
ck("P0 -r02: actor role is independent-reviewer (state machine requirement)",
   r2["actor"]["role"] == "independent-reviewer")
ck("P0 -r02: independence basis states separation of parties, not tooling",
   "separation of parties" in r2["independence"]["basis"])
ck("P0 -r02: independence basis states the reviewer did not draft",
   "did not draft draft-0.9" in r2["independence"]["basis"])
ck("P0 -r02: reason discloses the working-tree vs repository digest split",
   "162c9047" in r2["reason"] and "6ccebc47" in r2["reason"])
ck("P0 -r02: reason explains the 1366-byte difference is CRLF",
   "1366" in r2["reason"] and "CRLF" in r2["reason"])
ck("P0 -r02: reason states -r01 is retained as history",
   "-r01 is retained as history" in r2["reason"])
ck("P0 -r02: reason records that D-2 keeps the stream_reverify field",
   'the stream_reverify field itself retained' in r2["reason"])
ck("P0 -r02: review_kind is the technical scope review",
   r2["payload"]["review_kind"] == "P0_TECHNICAL_SCOPE_REVIEW")
ck("P0 -r02: finding_ids empty (accepted)",
   r2["payload"]["finding_ids"] == [])
ck("P0 -r02: operations == [review]", r2["scope"]["operations"] == ["review"])
ck("P0 -r02: write_targets empty (P0-P3)", r2["scope"]["write_targets"] == [])
ck("P0 -r02: workloads empty (P0-P3)", r2["scope"]["workloads"] == [])
ck("P0 -r02: allow_network false", r2["scope"]["allow_network"] is False)
ck("P0 -r02: allow_production_write false",
   r2["scope"]["allow_production_write"] is False)

# ---------------------------------------------------------- P1 -r02 shape --
p1 = p1n["payload"]
ck("P1 -r02: gate_id == P1", p1["gate_id"] == "P1")
ck("P1 -r02: exactly one predecessor", len(p1["predecessors"]) == 1)
pred = p1["predecessors"][0]
ck("P1 -r02: predecessor gate_id == P0", pred["gate_id"] == "P0")
ck("P1 -r02: predecessor record_id == P0 -r02 record_id",
   pred["record_id"] == r2["record_id"], pred["record_id"])
ck("P1 -r02: predecessor record_sha256 == actual -r02 file digest",
   pred["record_sha256"] == sha(R02))
ck("P1 -r02: predecessor expected_decision == -r02 actual decision",
   pred["expected_decision"] == r2["decision"])
ck("P1 -r02: predecessor expected_next_action == -r02 actual action",
   pred["expected_next_action"] == r2["allowed_next_action"])
ck("P1 -r02: predecessor edge IS satisfied", pred["record_sha256"] == sha(R02)
   and pred["expected_decision"] == r2["decision"])
ck("P1 -r02: decision == AUTHORIZED", p1["decision"] == "AUTHORIZED")
ck("P1 -r02: allowed_next_action == request-p2",
   p1["allowed_next_action"] == "request-p2")
ck("P1 -r02: independence required=false,satisfied=false (owner-only step)",
   p1["independence"]["required"] is False
   and p1["independence"]["satisfied"] is False)
ck("P1 -r02: actor role == owner", p1["actor"]["role"] == "owner")
ck("P1 -r02: operations == [identity]", p1["scope"]["operations"] == ["identity"])
ck("P1 -r02: write_targets empty (P1 admin artifact is not a TARGET)",
   p1["scope"]["write_targets"] == [])
ck("P1 -r02: identity_ref.sha256 == actual identity digest",
   p1["payload"]["identity_ref"]["sha256"] == sha(IDENTITY))
ck("P1 -r02: identity_ref.logical_name == identity logical_name",
   p1["payload"]["identity_ref"]["logical_name"] == ident["logical_name"])
ck("P1 -r02: read_refs contains exactly the -r02 P0 ref",
   len(p1["scope"]["read_refs"]) == 1
   and p1["scope"]["read_refs"][0]["logical_name"] == r02["logical_name"])
ck("P1 -r02: read_refs sha256 == -r02 digest",
   p1["scope"]["read_refs"][0]["sha256"] == sha(R02))
ck("P1 -r02: read_refs does NOT reference the rejected -r01",
   all("r01" not in r["logical_name"] for r in p1["scope"]["read_refs"]))
ck("P1 -r02: forbidden_history_ids matches identity list",
   p1["payload"]["forbidden_history_ids"] == ident["payload"]["forbidden_history_ids"])
ck("P1 -r02: reason states it supersedes the NOT_AUTHORIZED prior P1",
   "supersedes the earlier P1" in p1["reason"])
ck("P1 -r02: reason states the prior P1 is retained as history",
   "retained unchanged as history" in p1["reason"])
ck("P1 -r02: reason grants identity only, not execution",
   "authorizes identity creation only" in p1["reason"])

# ------------------------------------------------------ record_id pairing --
ck("PAIRING: P1 -r02 carries the same -r02 suffix as P0 -r02",
   p1["record_id"].endswith("-r02") and r2["record_id"].endswith("-r02"))

# ------------------------------------------------ no authority in the set --
ck("CHAIN: no record in this set claims execution authority",
   r2["decision"] == "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY"
   and p1["decision"] == "AUTHORIZED"
   and p1["allowed_next_action"] == "request-p2")

# ------------------------------------------------------------------ report -
print("=" * 78)
print("P0 -r02 / P1 -r02 validation (draft-0.9)")
print("=" * 78)
for name, ok, detail in results:
    line = ("OK   " if ok else "FAIL ") + name
    if detail and not ok:
        line += f"   [{detail}]"
    print(line)

bad = [n for n, ok, _ in results if not ok]
print()
print(f"checks: {len(results)}  passed: {len(results) - len(bad)}  failed: {len(bad)}")
if bad:
    print("FAILED:")
    for n in bad:
        print("  -", n)
    sys.exit(1)
print("ALL CHECKS PASS")
