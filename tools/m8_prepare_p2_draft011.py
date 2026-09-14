"""Prepare and validate draft-0.11 P2 binding candidates without issuing P2.

The command reads the committed P0/P1/identity and a fresh parent measurement,
then writes candidate-only JSON outside the repository. It never writes a
canonical binding artifact or gate under docs/plans/references.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "docs" / "plans" / "references"
BASE = "sa-m8-active-draft011-20260914-940ecec4"
PROTOCOL_REL = "docs/plans/references/m8-active-execution-protocol-draft-0.11.md"
IDENTITY_REL = f"external-artifacts/identity/{BASE}.json"
P1_REL = "external-gates/p1/p1-m8-active-execution-draft011-940ecec4-r01.json"
PARENT_LOGICAL = f"external-artifacts/binding/{BASE}-parent.json"
REPOSITORY_LOGICAL = f"external-artifacts/binding/{BASE}-repository.json"
EXPECTED_PROTOCOL_SHA = "92e28958eb3e5d938e8646704fa22a297430bfede3d53f04ba941181c9b8d40d"
EXPECTED_IDENTITY_SHA = "44fabea20f36165151b3e5c6bf140efdf348929399b33aa1d478a6cfec6c58a2"
EXPECTED_P1_SHA = "d60057e5ec81dad67a5706574db8bf51cc6a6fdda03f385a8621421371ad13f6"
PURPOSES = ["package", "normal-receipt", "nonpublication-receipt", "abort-receipt", "failure-receipt"]
failures = []


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check(label, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + label + ((" :: " + detail) if detail and not condition else ""))
    if not condition:
        failures.append(label)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


parser = argparse.ArgumentParser()
parser.add_argument("measurement", type=Path)
parser.add_argument("output_dir", type=Path)
args = parser.parse_args()
status = git("status", "--porcelain")
check("repository clean", not status, status)
commit = git("rev-parse", "HEAD")
protocol_bytes = (ROOT / PROTOCOL_REL).read_bytes()
identity_path = REFS / IDENTITY_REL
p1_path = REFS / P1_REL
identity_bytes = identity_path.read_bytes()
p1_bytes = p1_path.read_bytes()
identity = json.loads(identity_bytes)
p1 = json.loads(p1_bytes)
measurement_doc = json.loads(args.measurement.read_text(encoding="utf-8"))
measurement = measurement_doc[f"C:/M8-Parents/{BASE}"]
check("protocol digest", digest(protocol_bytes) == EXPECTED_PROTOCOL_SHA)
check("identity digest", digest(identity_bytes) == EXPECTED_IDENTITY_SHA)
check("P1 digest", digest(p1_bytes) == EXPECTED_P1_SHA)
check("P1 authorizes request-p2", p1["payload"]["decision"] == "AUTHORIZED" and p1["payload"]["allowed_next_action"] == "request-p2")
check("measurement components", measurement["components"] == ["M8-Parents", BASE])
check("measurement open invariants", measurement["opened_by"] == "NtCreateFile" and measurement["walk"] == "volume-root-component-walk" and measurement["root_directory_relative"] is True and measurement["share_mask"] == "read-write-delete" and measurement["no_follow"] is True)
check("measurement identity shapes", all(re.fullmatch(r"[0-9a-f]{16}", value["volume_serial"]) and re.fullmatch(r"[0-9a-f]{32}", value["file_id"]) and re.fullmatch(r"[0-9a-f]{64}", value["acl_sha256"]) and value["filesystem"] in {"ntfs", "refs"} for value in [measurement["volume_root"], measurement["parent"]]))
check("measurement same volume", measurement["volume_root"]["volume_serial"] == measurement["parent"]["volume_serial"])
parent = {"canonicalization_id": "sa-json-c14n-v1", "logical_name": PARENT_LOGICAL, "payload": measurement, "schema_id": "sa.m8.parent-binding.v1", "schema_version": 1}
parent_bytes = canonical(parent)
parent_ref = {"logical_name": PARENT_LOGICAL, "schema_id": "sa.m8.parent-binding.v1", "sha256": digest(parent_bytes)}
repository = {
    "canonicalization_id": "sa-json-c14n-v1",
    "logical_name": REPOSITORY_LOGICAL,
    "payload": {
        "experiment_parent_binding": parent_ref,
        "identity_ref": {"logical_name": IDENTITY_REL, "schema_id": identity["schema_id"], "sha256": digest(identity_bytes)},
        "oid_algorithm": "sha1",
        "publication_parent_bindings": [{"binding_ref": parent_ref, "purpose": purpose} for purpose in PURPOSES],
        "repository_commit": commit,
        "repository_dirty": False,
        "reviewed_protocol_path": PROTOCOL_REL,
        "reviewed_protocol_sha256": digest(protocol_bytes),
    },
    "schema_id": "sa.m8.repository-binding.v1",
    "schema_version": 1,
}
repository_bytes = canonical(repository)
check("parent candidate canonical", json.loads(parent_bytes) == parent)
check("repository candidate canonical", json.loads(repository_bytes) == repository)
check("five publication purposes", [row["purpose"] for row in repository["payload"]["publication_parent_bindings"]] == PURPOSES)
check("no repository binding artifact", not (REFS / REPOSITORY_LOGICAL).exists())
check("no parent binding artifact", not (REFS / PARENT_LOGICAL).exists())
check("no draft011 P2 gate", not list((REFS / "external-gates" / "p2").glob("*draft011*.json")))
if failures:
    print(f"{len(failures)} FAIL")
    sys.exit(1)
args.output_dir.mkdir(parents=True, exist_ok=True)
(args.output_dir / "parent-binding-candidate.json").write_bytes(parent_bytes)
(args.output_dir / "repository-binding-candidate.json").write_bytes(repository_bytes)
manifest = {"candidate_only": True, "identity_sha256": digest(identity_bytes), "p1_sha256": digest(p1_bytes), "parent_binding_sha256": digest(parent_bytes), "protocol_sha256": digest(protocol_bytes), "repository_binding_sha256": digest(repository_bytes), "repository_commit": commit, "repository_dirty": False}
(args.output_dir / "candidate-manifest.json").write_bytes(canonical(manifest))
print("ALL PASS")
print(json.dumps(manifest, indent=2))
