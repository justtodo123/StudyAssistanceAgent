"""Independently validate the draft-0.9 P0 gate record, identity and P1 record.

This validator re-derives everything from the files themselves and from the
protocol text; it does not import the build script. It checks the schema fields
declared in the protocol, the P0->P1 predecessor edge, the bound protocol digest,
the canonical JSON form, and the identity/forbidden-history disjointness.
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

P0 = REF / "external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json"
P1 = REF / "external-gates/p1" / next(
    p.name for p in (REF / "external-gates/p1").glob("*draft09*.json")
)
IDENTITY = REF / "external-artifacts/identity" / next(
    p.name for p in (REF / "external-artifacts/identity").glob("*draft09*.json")
)

# --- type regexes from protocol 2.1 -----------------------------------------
RE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
RE_SCHEMA_ID = re.compile(r"^[a-z0-9][a-z0-9.-]{0,127}$")
RE_HEX64 = re.compile(r"^[0-9a-f]{64}$")
RE_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
RE_GATE = re.compile(r"^(P0|P1|P2|P3|P4|P5|P6|P7|P7A|P8|P9)$")

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

results: list[tuple[str, bool, str]] = []


def ck(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


protocol_sha = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
p0, p1, ident = load(P0), load(P1), load(IDENTITY)

# ------------------------------------------------------ canonical JSON form --
for label, path in (("P0", P0), ("P1", P1), ("identity", IDENTITY)):
    raw = path.read_bytes()
    ok = raw == (canon(json.loads(raw.decode("utf-8"))) + "\n").encode("utf-8")
    ck(f"{label}: file is sa-json-c14n-v1 canonical (sorted keys, no spaces)", ok)
    ck(f"{label}: no BOM and LF-terminated", raw[:3] != b"\xef\xbb\xbf" and raw.endswith(b"\n"))

# ---------------------------------------------------------- envelope shape --
for label, obj, schema in (
    ("P0", p0, "sa.m8.external-gate-record.v1"),
    ("P1", p1, "sa.m8.external-gate-record.v1"),
    ("identity", ident, "sa.m8.experiment-identity.v1.payload"),
):
    ck(f"{label}: envelope keys exact",
       set(obj) == {"canonicalization_id", "logical_name", "payload",
                    "schema_id", "schema_version"},
       str(sorted(obj)))
    ck(f"{label}: schema_id == {schema}", obj["schema_id"] == schema)
    ck(f"{label}: schema_version == 1", obj["schema_version"] == 1)
    ck(f"{label}: canonicalization_id == sa-json-c14n-v1",
       obj["canonicalization_id"] == "sa-json-c14n-v1")

# ------------------------------------------------------- protocol binding ---
for label, obj in (("P0", p0), ("P1", p1), ("identity", ident)):
    ck(f"{label}: reviewed_protocol_path is draft-0.9",
       obj["payload"]["reviewed_protocol_path"] == PROTOCOL_RELPATH)
    ck(f"{label}: reviewed_protocol_sha256 == actual draft-0.9 digest",
       obj["payload"]["reviewed_protocol_sha256"] == protocol_sha,
       obj["payload"]["reviewed_protocol_sha256"])

# ------------------------------------------------------------------- P0 ------
p0p = p0["payload"]
ck("P0: gate_id == P0", p0p["gate_id"] == "P0")
ck("P0: has no predecessor", p0p["predecessors"] == [])
ck("P0: payload.gate_id == P0", p0p["payload"]["gate_id"] == "P0")
ck("P0: review_kind exact",
   p0p["payload"]["review_kind"] == "P0_TECHNICAL_SCOPE_REVIEW")
ck("P0: finding_ids is empty array",
   p0p["payload"]["finding_ids"] == [])
ck("P0: decision == P0_NOT_ACCEPTED (gate NOT discharged)",
   p0p["decision"] == "P0_NOT_ACCEPTED", p0p["decision"])
ck("P0: allowed_next_action == stop (must not auto-advance to P1)",
   p0p["allowed_next_action"] == "stop", p0p["allowed_next_action"])
ck("P0: independence.required is True (protocol requires it at P0)",
   p0p["independence"]["required"] is True)
ck("P0: independence.satisfied is FALSE (same actor drafted and reviewed)",
   p0p["independence"]["satisfied"] is False,
   str(p0p["independence"]["satisfied"]))
ck("P0: independence basis discloses pending human reviewer",
   "SUBSTANTIVE INDEPENDENCE IS NOT ESTABLISHED" in p0p["independence"]["basis"]
   and "pending a human reviewer" in p0p["independence"]["basis"])
ck("P0: operations == [review]", p0p["scope"]["operations"] == ["review"])
ck("P0: write_targets empty (P0-P3 have none)",
   p0p["scope"]["write_targets"] == [])
ck("P0: workloads empty (P0-P3)", p0p["scope"]["workloads"] == [])
ck("P0: allow_network false", p0p["scope"]["allow_network"] is False)
ck("P0: allow_production_write false",
   p0p["scope"]["allow_production_write"] is False)
ck("P0: record_id matches ID grammar",
   bool(RE_ID.match(p0p["record_id"])), p0p["record_id"])
ck("P0: timestamp matches TS grammar",
   bool(RE_TS.match(p0p["timestamp"])), p0p["timestamp"])
ck("P0: actor role == independent-reviewer (only enum member for a P0 review)",
   p0p["actor"]["role"] == "independent-reviewer")
ck("P0: actor name is labelled mechanical, not passed off as the human reviewer",
   "mechanical" in p0p["actor"]["name"]
   and p0p["actor"]["name"] != "m8-independent-reviewer-01",
   p0p["actor"]["name"])
ck("P0: decision in GATE_DECISION enum", p0p["decision"] in GATE_DECISIONS)
ck("P0: next action in NEXT_ACTION enum",
   p0p["allowed_next_action"] in NEXT_ACTIONS)
ck("P0: logical_name follows external-gates/p0/<record_id>.json",
   p0["logical_name"] == f"external-gates/p0/{p0p['record_id']}.json")

# ---------------------------------------------------------------- identity ---
ip = ident["payload"]
ck("identity: experiment_id matches ID grammar",
   bool(RE_ID.match(ip["experiment_id"])), ip["experiment_id"])
ck("identity: nonce is HEX64", bool(RE_HEX64.match(ip["identity_nonce"])))
ck("identity: created_at matches TS", bool(RE_TS.match(ip["created_at"])))
ck("identity: exactly 13 forbidden history ids",
   len(ip["forbidden_history_ids"]) == 13)
# The existing draft-0.5 records order these as v1..v13 in *numeric* order, not
# lexicographic order (lexicographic would put v10 before v2). This validator
# therefore checks the numeric order actually used in-repo, and reports the
# ordering convention rather than forcing sorted().
def natural_key(s: str):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", s)]

ck("identity: forbidden ids are unique",
   len(set(ip["forbidden_history_ids"])) == 13)
ck("identity: forbidden ids are in numeric v-order (matches draft-0.5 precedent)",
   ip["forbidden_history_ids"] == sorted(ip["forbidden_history_ids"], key=natural_key),
   str(ip["forbidden_history_ids"][:3]))
ck("identity: forbidden ids use the exact same literals as draft-0.5 record",
   ip["forbidden_history_ids"]
   == [f"sa.m8.admission-evidence.v{i}" for i in range(1, 14)])
ck("identity: experiment_id does not collide with forbidden history",
   ip["experiment_id"] not in ip["forbidden_history_ids"])

# ------------------------------------------------------------------- P1 ------
p1p = p1["payload"]
ck("P1: gate_id == P1", p1p["gate_id"] == "P1")
ck("P1: payload.gate_id == P1", p1p["payload"]["gate_id"] == "P1")
ck("P1: exactly one predecessor (P0->P1 edge)",
   len(p1p["predecessors"]) == 1)
pred = p1p["predecessors"][0]
ck("P1: predecessor gate_id == P0", pred["gate_id"] == "P0")
ck("P1: predecessor record_id equals P0 record_id",
   pred["record_id"] == p0p["record_id"], pred["record_id"])
ck("P1: predecessor record_sha256 equals P0 file digest",
   pred["record_sha256"] == hashlib.sha256(P0.read_bytes()).hexdigest())
ck("P1: predecessor expected_decision is the accepted-only decision",
   pred["expected_decision"] == "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY")
ck("P1: predecessor expected_next_action is request-p1",
   pred["expected_next_action"] == "request-p1")
ck("P1: predecessor edge is NOT satisfied by the actual P0 record",
   pred["expected_decision"] != p0p["decision"],
   f"expected={pred['expected_decision']} actual={p0p['decision']}")
ck("P1: decision == NOT_AUTHORIZED (predecessor P0 not accepted)",
   p1p["decision"] == "NOT_AUTHORIZED", p1p["decision"])
ck("P1: allowed_next_action == stop",
   p1p["allowed_next_action"] == "stop", p1p["allowed_next_action"])
ck("P1: reason states P1 is not authorized",
   "P1 IS NOT AUTHORIZED" in p1p["reason"])
ck("P1: reason states it grants nothing",
   "This record grants nothing" in p1p["reason"])
ck("P1: independence required=false (owner-only step, not the blocker)",
   p1p["independence"]["required"] is False)
ck("P1: independence.satisfied is False",
   p1p["independence"]["satisfied"] is False)
ck("P1: independence basis names the P0 rejection as the reason",
   "P0_NOT_ACCEPTED" in p1p["independence"]["basis"])
ck("P1: operations == [identity]", p1p["scope"]["operations"] == ["identity"])
ck("P1: write_targets empty (P1 admin artifact is not a TARGET)",
   p1p["scope"]["write_targets"] == [])
ck("P1: identity_ref.sha256 equals actual identity file digest",
   p1p["payload"]["identity_ref"]["sha256"]
   == hashlib.sha256(IDENTITY.read_bytes()).hexdigest())
ck("P1: identity_ref.logical_name equals identity artifact logical name",
   p1p["payload"]["identity_ref"]["logical_name"] == ident["logical_name"])
ck("P1: identity_ref.schema_id matches identity envelope schema",
   p1p["payload"]["identity_ref"]["schema_id"]
   == "sa.m8.experiment-identity.v1.payload")
ck("P1: read_refs contains exactly the P0 record ref",
   len(p1p["scope"]["read_refs"]) == 1
   and p1p["scope"]["read_refs"][0]["logical_name"] == p0["logical_name"])
ck("P1: read_refs sha256 equals P0 digest",
   p1p["scope"]["read_refs"][0]["sha256"]
   == hashlib.sha256(P0.read_bytes()).hexdigest())
fhi = p1p["payload"]["forbidden_history_ids"]
ck("P1: forbidden_history_ids matches identity's list byte-for-byte",
   fhi == ip["forbidden_history_ids"])
ck("P1: record_id matches ID grammar", bool(RE_ID.match(p1p["record_id"])))
ck("P1: timestamp matches TS", bool(RE_TS.match(p1p["timestamp"])))
ck("P1: actor role == owner", p1p["actor"]["role"] == "owner")
ck("P1: decision in GATE_DECISION enum", p1p["decision"] in GATE_DECISIONS)
ck("P1: next action in NEXT_ACTION enum",
   p1p["allowed_next_action"] in NEXT_ACTIONS)
ck("P1: logical_name follows external-gates/p1/<record_id>.json",
   p1["logical_name"] == f"external-gates/p1/{p1p['record_id']}.json")

# ------------------------------------------------------- disclosure checks --
ck("DISCLOSURE: P0 reason states the gate is not discharged",
   "THE DRAFT-0.9 P0 GATE IS NOT DISCHARGED" in p0p["reason"])
ck("DISCLOSURE: P0 reason preserves technical findings without accepting",
   "they are NOT an " in p0p["reason"])
ck("DISCLOSURE: P0 independence basis warns against treating it as accepted",
   "Do NOT treat this record as an accepted P0" in p0p["independence"]["basis"])
ck("CHAIN: no gate in this material set claims execution authority",
   p0p["decision"] == "P0_NOT_ACCEPTED"
   and p1p["decision"] == "NOT_AUTHORIZED")

# ------------------------------------------------------------------ report --
print("=" * 78)
print("P1 materials validation (draft-0.9)")
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
