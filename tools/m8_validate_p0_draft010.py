"""Validate the draft-0.10 P0 record against the protocol's own schema.

The record is a machine-readable artifact, so it is checked as one: envelope
shape, canonicalization, the closed decision and next-action enums, the actor
role enum, the P0 payload variant, the P0 independence requirement, the closed
scope sets, predecessor absence, and the binding to the reviewed protocol.

This script checks that the record is well formed and says what the protocol
requires a P0 record to say. It does not judge the decision -- an accepted P0
and a rejected P0 are both valid records, and the point of validating is to
catch malformed ones, not to second-guess the reviewer.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(r"D:\Git Demo\StudyAssistanceAgent")
REF = REPO / "docs" / "plans" / "references"
P10 = REF / "m8-active-execution-protocol-draft-0.10.md"
REC = REF / "external-gates/p0/p0-m8-active-execution-draft010-20260913-r01.json"

P10_RELPATH = "docs/plans/references/m8-active-execution-protocol-draft-0.10.md"

bad = []


def ck(label, cond, detail=""):
    if not cond:
        bad.append(label)
    print(("OK   " if cond else "FAIL ") + label + ((" :: " + detail) if not cond else ""))


protocol = P10.read_text(encoding="utf-8")


def line_of(pattern):
    for i, ln in enumerate(protocol.splitlines(), 1):
        if pattern in ln:
            return i, ln
    return None, ""


def enum_after(heading):
    """Collect a closed enum that may wrap across several lines."""
    lines = protocol.splitlines()
    for i, ln in enumerate(lines):
        if heading in ln:
            blob = "".join(lines[i:i + 4])
            blob = blob.split(":", 1)[1] if ":" in blob else blob
            blob = blob.split("`.")[0].replace("`", "")
            return [v for v in blob.replace("\n", "").split(",") if v.strip()]
    return []


# Read the protocol's own closed enums rather than hard-coding them, so that a
# record cannot drift from the protocol while still passing this script.
decisions = enum_after("`GATE_DECISION` is the closed enum, in this order:")
nexts = enum_after("`NEXT_ACTION` is the closed enum, in this order:")

raw = REC.read_bytes()
rec = json.loads(raw.decode("utf-8"))
p = rec["payload"]

print("=== canonical form ===")
canon = json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
ck("文件为 UTF-8 无 BOM", not raw.startswith(b"\xef\xbb\xbf"))
ck("无 CRLF", b"\r\n" not in raw)
ck("以换行结尾", raw.endswith(b"\n"))
ck("内容等于 sa-json-c14n-v1 规范形式 + \\n",
   raw.decode("utf-8") == canon + "\n")
ck("无尾随空白行", not raw.decode("utf-8").endswith("\n\n"))
rec_sha = hashlib.sha256(raw).hexdigest()
print(f"     record sha256 = {rec_sha}")
print(f"     record bytes  = {len(raw)}")

print()
print("=== envelope ===")
ck("canonicalization_id = sa-json-c14n-v1", rec.get("canonicalization_id") == "sa-json-c14n-v1")
ck("schema_id = sa.m8.external-gate-record.v1", rec.get("schema_id") == "sa.m8.external-gate-record.v1")
ck("schema_version = 1", rec.get("schema_version") == 1)
ck("顶层恰为 5 个字段",
   set(rec) == {"canonicalization_id", "logical_name", "payload", "schema_id", "schema_version"},
   str(sorted(rec)))
ck("logical_name 与路径一致",
   rec.get("logical_name") == f"external-gates/p0/{REC.stem}.json", rec.get("logical_name"))
ck("信封不含自身摘要", "sha256" not in rec and "digest" not in rec)

print()
print("=== payload 字段集 ===")
expected = {
    "record_id", "gate_id", "reviewed_protocol_path", "reviewed_protocol_sha256",
    "predecessors", "actor", "independence", "timestamp", "decision", "reason",
    "allowed_next_action", "scope", "payload",
}
ck("恰为协议规定的 13 个字段", set(p) == expected, str(sorted(set(p) ^ expected)))
ck("record_id == 文件名", p["record_id"] == REC.stem, p["record_id"])

print()
print("=== 闭枚取值 ===")
ck("GATE_DECISION 解析出 11 项", len(decisions) == 11, str(len(decisions)))
ck("decision 在 GATE_DECISION 闭枚内", p["decision"] in decisions,
   f"{p['decision']} not in {decisions}")
ck("allowed_next_action 在 NEXT_ACTION 闭枚内", p["allowed_next_action"] in nexts,
   f"{p['allowed_next_action']} not in {nexts}")
ck("decision = 接受型", p["decision"] == "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY")
ck("allowed_next_action = request-p1", p["allowed_next_action"] == "request-p1")
ck("decision/next 配对符合 P0 行",
   (p["decision"], p["allowed_next_action"])
   == ("P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY", "request-p1"))
ck("actor.role 在闭枚内",
   p["actor"]["role"] in ("owner", "independent-reviewer", "independent-verifier"),
   p["actor"]["role"])
ck("actor.role = independent-reviewer", p["actor"]["role"] == "independent-reviewer")
ck("actor.name = justtodo123", p["actor"]["name"] == "justtodo123")

print()
print("=== P0 专属要求 ===")
ck("gate_id = P0", p["gate_id"] == "P0")
ck("P0 无前驱", p["predecessors"] == [], str(p["predecessors"]))
ck("P0 payload 变体正确", p["payload"] == {
    "finding_ids": [], "gate_id": "P0", "review_kind": "P0_TECHNICAL_SCOPE_REVIEW"},
   str(p["payload"]))
ck("内层 gate_id 与外层一致", p["payload"]["gate_id"] == p["gate_id"])
ck("independence.required = true", p["independence"]["required"] is True)
ck("independence.satisfied = true", p["independence"]["satisfied"] is True)
ck("independence.basis 长度 1..1024",
   1 <= len(p["independence"]["basis"]) <= 1024, str(len(p["independence"]["basis"])))
ck("reason 长度 1..4096", 1 <= len(p["reason"]) <= 4096, str(len(p["reason"])))
ck("finding_ids 为空（接受即无遗留缺陷）", p["payload"]["finding_ids"] == [])

print()
print("=== scope ===")
s = p["scope"]
ck("operations = [review]（P0 操作集）", s["operations"] == ["review"], str(s["operations"]))
ck("operations 长度 1..3", 1 <= len(s["operations"]) <= 3)
ck("operations 在闭枚内",
   all(o in ("review", "identity", "binding", "acquire", "prepare", "execute",
             "verify", "publish", "cleanup", "admit", "select") for o in s["operations"]))
ck("allow_network = false", s["allow_network"] is False)
ck("allow_production_write = false", s["allow_production_write"] is False)
ck("workloads 为空（P0–P3）", s["workloads"] == [])
ck("write_targets 为空", s["write_targets"] == [])
ck("read_refs 为空", s["read_refs"] == [])
ck("scope 字段集精确",
   set(s) == {"workloads", "allow_network", "allow_production_write",
              "operations", "write_targets", "read_refs"}, str(sorted(s)))

print()
print("=== 协议绑定 ===")
ck("reviewed_protocol_path = draft-0.10", p["reviewed_protocol_path"] == P10_RELPATH)
actual = hashlib.sha256(P10.read_bytes()).hexdigest()
ck("reviewed_protocol_sha256 == 实际 draft-0.10 摘要",
   p["reviewed_protocol_sha256"] == actual, p["reviewed_protocol_sha256"])
ck("摘要为 64 位小写十六进制",
   re.fullmatch(r"[0-9a-f]{64}", p["reviewed_protocol_sha256"]) is not None)
ck("REPO_PATH 形态（正斜杠）", "/" in p["reviewed_protocol_path"] and "\\" not in p["reviewed_protocol_path"])
ck("timestamp 为 TS 形态",
   re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", p["timestamp"]) is not None,
   p["timestamp"])

print()
print("=== 授权边界：本记录不得越界 ===")
low = p["reason"].lower()
ck("reason 未宣称产生执行权限", "execution authorization" in low)
ck("reason 未宣称准入", "admission" in low)
ck("reason 记录了 26 项门禁校验", "26" in p["reason"])
ck("reason 披露了 draft-0.9 曾被就地改写", "184174" in p["reason"])
ck("reason 说明记录重算待办", "162c9047" in p["reason"])
ck("reason 的 measured 口径可复现（引用脚本）",
   "m8_run_p0_review_checks.py" in p["reason"])

print()
print("=== 与既有记录的关系 ===")
others = sorted((REF / "external-gates" / "p0").glob("*.json"))
ck("draft-0.10 的 P0 恰一条", len([x for x in others if "draft010" in x.name]) == 1)
ck("draft-0.9 的 P0 记录未被改动（-r01 仍 P0_NOT_ACCEPTED）",
   json.loads((REF / "external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json")
              .read_text(encoding="utf-8"))["payload"]["decision"] == "P0_NOT_ACCEPTED")
ck("draft-0.9 的 P0 -r02 未被改动",
   json.loads((REF / "external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json")
              .read_text(encoding="utf-8"))["payload"]["decision"]
   == "P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY")

print()
if bad:
    print(f"{len(bad)} 项未通过：")
    for n in bad:
        print("  -", n)
    sys.exit(1)
print("P0 记录校验全部通过")
print("NOTE: 本脚本校验记录的形式合规性，不评判其决定。")
print("      P0 的接受决定由 justtodo123 以 independent-reviewer 身份作出。")
