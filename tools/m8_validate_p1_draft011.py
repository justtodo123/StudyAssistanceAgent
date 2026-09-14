import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "docs" / "plans" / "references"
PROTOCOL = REFS / "m8-active-execution-protocol-draft-0.11.md"
P0 = REFS / "external-gates" / "p0" / "p0-m8-active-execution-draft011-20260914-r01.json"
IDENTITY = REFS / "external-artifacts" / "identity" / "sa-m8-active-draft011-20260914-940ecec4.json"
P1 = REFS / "external-gates" / "p1" / "p1-m8-active-execution-draft011-940ecec4-r01.json"
EXPECTED_PROTOCOL_SHA = "92e28958eb3e5d938e8646704fa22a297430bfede3d53f04ba941181c9b8d40d"
failures = []


def check(label, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + label + ((" :: " + detail) if detail and not condition else ""))
    if not condition:
        failures.append(label)


def canonical_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_canonical(path):
    raw = path.read_bytes()
    value = json.loads(raw)
    check(f"canonical {path.name}", raw == canonical_bytes(value))
    check(f"UTF-8 no BOM {path.name}", not raw.startswith(b"\xef\xbb\xbf"))
    check(f"LF ending {path.name}", raw.endswith(b"\n") and not raw.endswith(b"\n\n") and b"\r" not in raw)
    return value, raw


protocol_raw = PROTOCOL.read_bytes()
p0, p0_raw = load_canonical(P0)
identity, identity_raw = load_canonical(IDENTITY)
p1, p1_raw = load_canonical(P1)
p0_payload = p0["payload"]
i = identity["payload"]
g = p1["payload"]
q = g["payload"]
expected_history = [{"id": f"sa.m8.admission-evidence.v{n}", "ordinal": n - 1} for n in range(1, 14)]

check("protocol digest frozen", hashlib.sha256(protocol_raw).hexdigest() == EXPECTED_PROTOCOL_SHA)
check("P0 accepted", p0_payload["decision"] == "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY" and p0_payload["allowed_next_action"] == "request-p1")
check("identity envelope", identity["schema_id"] == "sa.m8.experiment-identity.v1.payload" and identity["schema_version"] == 1 and identity["canonicalization_id"] == "sa-json-c14n-v1")
check("identity logical name", identity["logical_name"] == IDENTITY.relative_to(REFS).as_posix())
check("new draft011 experiment", i["experiment_id"] == "sa-m8-active-draft011-20260914-940ecec4" and "draft010" not in i["experiment_id"])
check("identity protocol binding", i["reviewed_protocol_path"] == PROTOCOL.relative_to(ROOT).as_posix() and i["reviewed_protocol_sha256"] == EXPECTED_PROTOCOL_SHA)
check("identity nonce HEX64", re.fullmatch(r"[0-9a-f]{64}", i["identity_nonce"]) is not None)
check("identity history objects", i["forbidden_history_ids"] == expected_history)
check("P1 envelope", p1["schema_id"] == "sa.m8.external-gate-record.v1" and p1["schema_version"] == 1 and p1["canonicalization_id"] == "sa-json-c14n-v1")
check("P1 logical name", p1["logical_name"] == P1.relative_to(REFS).as_posix())
check("P1 actor mapping", g["gate_id"] == "P1" and g["actor"] == {"name": "justtodo123", "role": "owner"})
check("P1 independence mapping", g["independence"]["required"] is False and g["independence"]["satisfied"] is False)
check("P1 decision/action", g["decision"] == "AUTHORIZED" and g["allowed_next_action"] == "request-p2")
check("P1 operation only", g["scope"]["operations"] == ["identity"] and g["scope"]["workloads"] == [] and g["scope"]["write_targets"] == [])
check("P1 no network/write", g["scope"]["allow_network"] is False and g["scope"]["allow_production_write"] is False)
check("P1 protocol binding", g["reviewed_protocol_path"] == PROTOCOL.relative_to(ROOT).as_posix() and g["reviewed_protocol_sha256"] == EXPECTED_PROTOCOL_SHA)
check("P1 closed payload", set(q) == {"gate_id", "identity_ref", "forbidden_history_ids"} and q["gate_id"] == "P1")
check("P1 history equals identity", q["forbidden_history_ids"] == expected_history == i["forbidden_history_ids"])
check("identity REF", q["identity_ref"] == {"logical_name": identity["logical_name"], "schema_id": identity["schema_id"], "sha256": hashlib.sha256(identity_raw).hexdigest()})
expected_predecessor = {"expected_decision": p0_payload["decision"], "expected_next_action": p0_payload["allowed_next_action"], "gate_id": "P0", "record_id": p0_payload["record_id"], "record_sha256": hashlib.sha256(p0_raw).hexdigest()}
check("exact P0 predecessor", g["predecessors"] == [expected_predecessor])
check("P0 read REF", g["scope"]["read_refs"] == [{"logical_name": p0["logical_name"], "schema_id": p0["schema_id"], "sha256": hashlib.sha256(p0_raw).hexdigest()}])
check("reason/basis bounds", 1 <= len(g["reason"]) <= 4096 and 1 <= len(g["independence"]["basis"]) <= 1024)
check("one draft011 identity", list((REFS / "external-artifacts" / "identity").glob("*draft011*.json")) == [IDENTITY])
draft011_gates = list((REFS / "external-gates").rglob("*draft011*.json"))
p2_gates = list((REFS / "external-gates" / "p2").glob("*draft011*.json"))
check("P0/P1 remain unique through P2", sum(path == P0 for path in draft011_gates) == 1 and sum(path == P1 for path in draft011_gates) == 1)
check("successor lifecycle at most P2", len(p2_gates) <= 1 and all("/p0/" in path.as_posix() or "/p1/" in path.as_posix() or "/p2/" in path.as_posix() for path in draft011_gates))

print("ALL PASS" if not failures else f"{len(failures)} FAIL")
sys.exit(bool(failures))
