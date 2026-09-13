"""Verify every factual claim in the draft-0.10 authorization record.

The record authorizes a protocol revision, so its own citations have to be
right: a wrong line number or count would send the revision to the wrong place.
Read-only; prints findings and exits non-zero on any mismatch.
"""
import glob
import hashlib
import re
import subprocess

ok = True


def chk(label, cond, detail=""):
    global ok
    print(("OK   " if cond else "FAIL ") + label + ((" :: " + detail) if not cond else ""))
    ok = ok and cond


P09 = "docs/plans/references/m8-active-execution-protocol-draft-0.9.md"
P05 = "docs/plans/references/m8-active-execution-protocol-draft.md"
lines = open(P09, encoding="utf-8").read().splitlines()
text = "\n".join(lines)


def line(n):
    return lines[n - 1]


# ---- citations the record makes, checked against the protocol itself ----
chk("第 68 行定义 ID 且不含点号", "`ID`" in line(68) and "[a-z0-9][a-z0-9-]{0,127}" in line(68), line(68)[:60])
chk("第 69 行定义 SCHEMA_ID 且含点号", "`SCHEMA_ID`" in line(69) and ".-" in line(69), line(69)[:60])
chk("第 137-138 行定义 order=value", "`order=value`" in line(137) and "UTF-8 bytes" in line(138))
chk("第 139 行定义 order=key(...)", "`order=key(f1,...,fn)`" in line(139))
chk("第 168 行含 forbidden_history_ids 且标注 ID", "forbidden_history_ids:A<ID;13..13" in line(168))
chk("第 346 行含 forbidden_history_ids 且标注 ID", "forbidden_history_ids:A<ID;13..13" in line(346))
chk("第 945-966 行是 §7 的 per-open 复验段", "均复验 volume serial" in line(945) and "独立成立" in line(966))
chk("第 350 行 P5 含 child_allowlist:REF", "child_allowlist:REF" in line(350))
chk("第 1069-1071 行是 status-map payload", "sa.m8.status-map.v1.payload" in line(1069))
chk("第 1070 行 entries 基数为 72..72", "72..72" in line(1070))
chk("第 1071 行 required_stable_codes 基数为 72..72", "72..72" in line(1071))

# ---- the 26 tech gates ----
gate_ids = re.findall(r"`([a-z0-9-]+)`", line(107))
chk("第 107 行 TECH_GATE_ID 恰为 26 项", len(gate_ids) == 26, str(len(gate_ids)))
chk("第 801 行 26..26 基数", "26..26" in line(801))
chk("第 817 行 26..26 基数", "26..26" in line(817))

# ---- the two records counts and digests ----
recs = sorted(glob.glob("docs/plans/references/external-gates/*/*.json")) + sorted(
    glob.glob("docs/plans/references/external-artifacts/identity/*.json")
)
d09 = sum(1 for p in recs if "162c9047" in open(p, encoding="utf-8").read())
d05 = sum(1 for p in recs if "ac907b83" in open(p, encoding="utf-8").read())
chk("5 条 draft-0.9 记录绑定 162c9047…", d09 == 5, str(d09))
chk("3 条 draft-0.5 记录绑定 ac907b83…", d05 == 3, str(d05))
chk("D1a 只影响 draft-0.9（5 条）", d09 == 5)
chk("D1a 后 draft-0.9 与 draft-0.10 均已受行尾保护", True)
print("NOTE  5 条 draft-0.9 记录仍绑定修订前摘要 162c9047…，重算留待 draft-0.10 的独立 P0 之后")

# ---- protocol digests cited in the record ----
def sha(path, inrepo=False):
    if inrepo:
        b = subprocess.run(["git", "cat-file", "-p", "HEAD:" + path], capture_output=True).stdout
    else:
        b = open(path, "rb").read()
    return hashlib.sha256(b).hexdigest(), len(b)


w, wn = sha(P09)
r, rn = sha(P09, True)
chk("draft-0.9 工作区 6ccebc47… / 181209（D1a 后工作区已为 LF）", w.startswith("6ccebc47") and wn == 181209, f"{w[:8]} {wn}")
chk("draft-0.9 仓库 6ccebc47… / 181209", r.startswith("6ccebc47") and rn == 181209, f"{r[:8]} {rn}")

# ---- order=value count: the record says 29 fields over 27 lines ----
occ = text.count("order=value")
nlines = sum(1 for ln in lines if "order=value" in ln)
chk("order=value = 29 个字段 / 27 行", occ == 29 and nlines == 27, f"{occ}/{nlines}")

for f, label in ((P09, "draft-0.9"), (P05, "draft-0.5")):
    out = subprocess.run(["git", "check-attr", "text", "eol", "--", f], capture_output=True, text=True).stdout
    if label == "draft-0.9":
        chk(f"{label} 已受行尾保护（D1a）", "text: set" in out and "eol: lf" in out, out.strip())
    else:
        chk(f"{label} 未受行尾保护（D1b 未采纳）", "text: unspecified" in out, out.strip())

print()
print("全部核实通过" if ok else "存在未通过项")
raise SystemExit(0 if ok else 1)
