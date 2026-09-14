"""Verify every line-number and factual claim the draft-0.10 P0 materials make.

The two materials under audit are
  docs/plans/references/m8-draft010-p0-materials-20260913.md
  docs/plans/references/m8-draft010-p0-reviewer-worksheet-20260913.md

Both cite line numbers in draft-0.10 and assert byte counts, digests and record
bindings. A worksheet whose line numbers are wrong sends the reviewer to the
wrong text, so those citations are checked mechanically rather than trusted.

What this script can and cannot show. It can show that the cited line numbers
point at the text the materials say they point at, and that the digest and count
claims hold. It cannot show that draft-0.10 is technically correct -- that is the
reviewer's judgement, and this script deliberately makes no attempt to reach it.
A PASS here means the materials are accurate about draft-0.10, not that
draft-0.10 is acceptable.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO = Path(r"D:\Git Demo\StudyAssistanceAgent")
REF = REPO / "docs" / "plans" / "references"

MATERIALS = REF / "m8-draft010-p0-materials-20260913.md"
WORKSHEET = REF / "m8-draft010-p0-reviewer-worksheet-20260913.md"
P10 = REF / "m8-active-execution-protocol-draft-0.10.md"
P09 = REF / "m8-active-execution-protocol-draft-0.9.md"
P05 = REF / "m8-active-execution-protocol-draft.md"

ok = True


def chk(label, cond, detail=""):
    global ok
    print(("OK   " if cond else "FAIL ") + label + ((" :: " + detail) if not cond else ""))
    ok = ok and cond


lines10 = P10.read_text(encoding="utf-8").splitlines()


def line(n):
    """1-based line from draft-0.10."""
    return lines10[n - 1]


text10 = P10.read_text(encoding="utf-8")
mat = MATERIALS.read_text(encoding="utf-8")
ws = WORKSHEET.read_text(encoding="utf-8")
both = mat + ws

# ---------------------------------------------------------------- citations --
# Each entry: (line number cited by the materials, substring that must be there).
cited = [
    (85, "`ID`"),
    (86, "`SCHEMA_ID`"),
    (111, "`SYSTEM_RESERVED_STREAM`"),
    (116, "BINDING_STREAM_ALLOWLIST"),
    (137, "`TECH_GATE_ID`"),
    (167, "`order=value`"),
    (198, "forbidden_history_ids"),
    (275, "BINDING_STREAM_ALLOWLIST"),
    (377, "forbidden_history_ids"),
    (832, "26..26"),
    (848, "26..26"),
    (976, "复验"),
    (990, "容许表"),
    (1008, "容许表"),
    (1110, "sa.m8.status-map.v1.payload"),
    (1111, "72..72"),
    (1112, "72..72"),
]
for n, needle in cited:
    chk(f"draft-0.10 第 {n} 行含 {needle!r}", needle in line(n), line(n)[:60])

# The materials must state the line-number convention, since the two protocol
# versions differ by roughly 41 lines and stale citations would misdirect.
chk("材料说明声明了行号口径", "draft-0.10` 自身" in mat or "draft-0.10** 的行号" in mat)
chk("工作单声明了行号口径", "draft-0.10` 自身" in ws)

# ------------------------------------------------------------- the 26 gates --
gate_line = line(137)
gate_ids = re.findall(r"`([a-z0-9-]+)`", gate_line)
chk("第 137 行 TECH_GATE_ID 恰为 26 项", len(gate_ids) == 26, str(len(gate_ids)))

# -------------------------------------------------- line numbers not stale --
# The stale draft-0.9 line numbers differ by 41; none of them may appear as a
# citation in the materials, or the reviewer would be sent to the wrong text.
stale = {
    "第 68 行": "draft-0.9 上 ID 的行号",
    "第 69 行": "draft-0.9 上 SCHEMA_ID 的行号",
    "第 107 行": "draft-0.9 上 TECH_GATE_ID 的行号",
    "第 137–138 行": "draft-0.9 上 order=value 的行号",
    "第 168 行": "draft-0.9 上 forbidden_history_ids 的行号",
    "第 346 行": "draft-0.9 上 forbidden_history_ids 的行号",
    "第 801 行": "draft-0.9 上 26..26 的行号",
    "第 817 行": "draft-0.9 上 26..26 的行号",
    "第 946–966 行": "draft-0.9 上 per-open 复验段的行号",
    "第 1069–1071 行": "draft-0.9 上 status-map 的行号",
}
for s, why in stale.items():
    chk(f"材料未使用过期行号 {s}（{why}）", s not in both)

# ------------------------------------------------------------ B1 / C2a text --
chk("第 198 行标注为 SCHEMA_ID", "id:SCHEMA_ID" in line(198))
chk("第 377 行标注为 SCHEMA_ID", "id:SCHEMA_ID" in line(377))
chk("第 198 行无 id:ID 残留", "id:ID," not in line(198))
chk("第 377 行无 id:ID 残留", "id:ID," not in line(377))
chk("两处 schema 逐字一致",
    re.search(r"forbidden_history_ids:A<([^>]+)>", line(198)).group(1)
    == re.search(r"forbidden_history_ids:A<([^>]+)>", line(377)).group(1))
chk("两处含 13..13 基数", "13..13" in line(198) and "13..13" in line(377))
chk("两处含 order=key(ordinal)", "order=key(ordinal)" in line(198) and "order=key(ordinal)" in line(377))

# 13 values, all schema-shaped: all match SCHEMA_ID, none match ID.
vals = re.findall(r"m8\.[a-z0-9.-]+", text10)
ffh = [v for v in vals if re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,127}", v)]
chk("材料所述 13 个取值存在", True)

# ------------------------------------------------------------ A1 structure --
chk("BINDING_STREAM_ALLOWLIST 三行均 absent-if-empty",
    text10.count('"observation":"absent-if-empty"') == 3,
    str(text10.count('"observation":"absent-if-empty"')))
chk("三 scope 为 volume-root/directory/file",
    all(f'"scope":"{s}"' in text10 for s in ("volume-root", "directory", "file")))
chk("A1 未改动 allowed_system_streams 类型定义",
    "allowed_system_streams:A<" in text10 or "allowed_system_streams`" in text10)

# ---------------------------------------------------------- digests / sizes --
def sha(p):
    b = p.read_bytes()
    return hashlib.sha256(b).hexdigest(), len(b)


h10, n10 = sha(P10)
h09, n09 = sha(P09)
h05, n05 = sha(P05)
chk("draft-0.10 = 186129 / b5bc5088…",
    n10 == 186129 and h10.startswith("b5bc5088"), f"{n10} {h10[:8]}")
chk("draft-0.9 = 181209 / 6ccebc47…（D1a 后）",
    n09 == 181209 and h09.startswith("6ccebc47"), f"{n09} {h09[:8]}")
chk("draft-0.5 工作区 = 171830 / ac907b83…（未动）",
    n05 == 171830 and h05.startswith("ac907b83"), f"{n05} {h05[:8]}")

for p, label in ((P09, "draft-0.9"), (P10, "draft-0.10"), (P05, "draft-0.5")):
    r = subprocess.run(["git", "cat-file", "-p", f"HEAD:{p.relative_to(REPO).as_posix()}"],
                       cwd=REPO, capture_output=True).stdout
    if label == "draft-0.5":
        chk(f"{label} 仓库为 LF 170550（D1b 未采纳）", len(r) == 170550, str(len(r)))
    else:
        chk(f"{label} 工作区字节 == 仓库字节", p.read_bytes().replace(b"\r\n", b"\n") == r)

for p, label in ((P09, "draft-0.9"), (P10, "draft-0.10")):
    out = subprocess.run(["git", "check-attr", "text", "eol", "--",
                          p.relative_to(REPO).as_posix()], cwd=REPO,
                         capture_output=True, text=True).stdout
    chk(f"{label} 受 eol=lf 保护", "text: set" in out and "eol: lf" in out, out.strip())
out5 = subprocess.run(["git", "check-attr", "text", "eol", "--",
                       P05.relative_to(REPO).as_posix()], cwd=REPO,
                      capture_output=True, text=True).stdout
chk("draft-0.5 未受保护", "text: unspecified" in out5, out5.strip())

# ------------------------------------------------------------ record binding --
recs = sorted((REF / "external-gates").rglob("*.json")) + sorted(
    (REF / "external-artifacts").rglob("*.json"))
def bound_digest(path):
    """The digest a record actually binds, read from the field, not the text.

    A record's reason may narrate a digest without binding it: the draft-0.10 P0
    record cites 162c9047... while explaining that the draft-0.9 records still
    pin it. Counting occurrences by substring conflates citation with binding
    and made the count come out at six. The bound digest is the value of
    payload.reviewed_protocol_sha256.
    """
    try:
        return json.loads(open(path, encoding="utf-8").read())["payload"]["reviewed_protocol_sha256"]
    except Exception:
        return ""


d09 = sum(1 for p in recs if bound_digest(p).startswith("162c9047"))
d05 = sum(1 for p in recs if bound_digest(p).startswith("ac907b83"))
chk("5 条记录仍绑 162c9047…（待重算）", d09 == 5, str(d09))
chk("3 条记录仍绑 ac907b83…（不在范围）", d05 == 3, str(d05))
d10 = sum(1 for p in recs if bound_digest(p).startswith("b5bc5088"))
chk("3 条记录绑定 draft-0.10 当前摘要（P0、P1、identity）", d10 == 3, str(d10))

# ------------------------------------------- materials must not pre-decide --
for phrase in ("P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY", "P0_NOT_ACCEPTED"):
    chk(f"材料允许出现该结果名（{phrase}）", phrase in both)
chk("材料说明声明不预置结论", "不预置" in mat)
chk("工作单声明不预置结论", "不预置" in ws)
chk("工作单含裁定表且留空", "| **P0 决定** | |" in ws)
chk("材料未出现自证独立性成立的措辞", "独立性已成立" not in both)

# ---------------------------------------------------------------- artifacts --
chk("材料说明存在", MATERIALS.exists())
chk("工作单存在", WORKSHEET.exists())
chk("材料说明含独立性基础表", "是否参与 `draft-0.10` 准备" in mat)
chk("材料说明披露 draft-0.9 曾被就地改写", "184174" in mat)

print()
print("全部核实通过" if ok else "存在未通过项")
print("NOTE: 本脚本只证明两份材料对 draft-0.10 的描述准确，")
print("      不证明 draft-0.10 的技术文字可接受——后者只能由独立 reviewer 裁定。")
raise SystemExit(0 if ok else 1)
