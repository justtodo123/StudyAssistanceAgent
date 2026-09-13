"""Run the worksheet's checks 2.1-2.8 and print the results the P0 record cites.

This is the measurement pass behind the draft-0.10 P0 record: the reviewer's
decision is the reviewer's, but the facts the decision rests on have to be
reproducible by anyone. Each block below corresponds to a numbered item in
m8-draft010-p0-reviewer-worksheet-20260913.md and prints the measured values
rather than a verdict.

Scope note. This script does not decide anything. It reports what the bytes say.
A reader who disagrees with the P0 decision can rerun it and see exactly what
was and was not established.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO = Path(r"D:\Git Demo\StudyAssistanceAgent")
REF = REPO / "docs" / "plans" / "references"
P09 = REF / "m8-active-execution-protocol-draft-0.9.md"
P10 = REF / "m8-active-execution-protocol-draft-0.10.md"

ok = True


def chk(label, cond, detail=""):
    global ok
    print(("OK   " if cond else "FAIL ") + label + ((" :: " + detail) if not cond else ""))
    ok = ok and cond


def read(p):
    return p.read_text(encoding="utf-8")


t09, t10 = read(P09), read(P10)

print("=== 1. 被审字节 ===")
b10 = P10.read_bytes()
h10 = hashlib.sha256(b10).hexdigest()
chk("draft-0.10 = 186129 bytes", len(b10) == 186129, str(len(b10)))
chk("draft-0.10 sha256 = b5bc5088…", h10.startswith("b5bc5088"), h10)
chk("draft-0.10 为纯 LF", b"\r\n" not in b10)
repo10 = subprocess.run(["git", "cat-file", "-p",
                         "HEAD:docs/plans/references/m8-active-execution-protocol-draft-0.10.md"],
                        cwd=REPO, capture_output=True).stdout
chk("draft-0.10 工作区字节 == 仓库字节", b10 == repo10)

print()
print("=== 2.2 改动范围：逐行归属 ===")
# Everything the diff adds or removes must map to A1/B1/C2a/D1a; nothing else.
diff_run = subprocess.run(["git", "diff", "--no-index", "--unified=0",
                          P09.relative_to(REPO).as_posix(),
                          P10.relative_to(REPO).as_posix()],
                         cwd=REPO, capture_output=True)
# git diff --no-index exits 1 when the files differ, so the exit code is not an
# error here; decode UTF-8 explicitly rather than letting the console codepage
# (GBK) decide, which would mangle the Chinese lines this diff is full of.
d = diff_run.stdout.decode("utf-8", errors="replace")
added = [l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]
removed = [l[1:] for l in d.splitlines() if l.startswith("-") and not l.startswith("---")]
print(f"新增 {len(added)} 行 / 删除 {len(removed)} 行")
# No added line may touch the frozen status map or the 72 bases.
frozen_hits = [l for l in added + removed if "72..72" in l and "STATUS_MAP" in l]
chk("无改动触及 status-map 的 72 基数", not frozen_hits, str(frozen_hits[:2]))
# No added line may redefine ID / SCHEMA_ID / order=value / order=key.
redef = [l for l in added
         if re.match(r"^- `(ID|SCHEMA_ID|order=value|order=key)", l.strip())]
chk("无改动重新定义 ID/SCHEMA_ID/order 定义", not redef, str(redef[:2]))
gate_def = [l for l in added if l.strip().startswith("- `TECH_GATE_ID`：")]
chk("无改动重新定义 TECH_GATE_ID 枚举", not gate_def)

print()
print("=== 2.3.1 A1 前提：allowed_system_streams 属 P5 产物 ===")
chk("allowed_system_streams 定义在 child-allowlist payload 内",
    "sa.m8.child-allowlist.v1.payload.allowed_system_streams" in t10)
chk("P5 门禁表含 child_allowlist:REF",
    re.search(r"\| P5 \|[^\n]*child_allowlist:REF", t10) is not None)
chk("P2 门禁表不含 child_allowlist",
    re.search(r"\| P2 \|[^\n]*child_allowlist", t10) is None)

print()
print("=== 2.3.2-2.3.5 A1 结构 ===")
chk("BINDING_STREAM_ALLOWLIST 定义存在", "- `BINDING_STREAM_ALLOWLIST`" in t10)
chk("基数 3..3", "};3..3;order=key(scope);unique=key(scope)>" in t10)
chk("三 scope 齐全", all(f'"scope":"{s}"' in t10 for s in ("volume-root", "directory", "file")))
chk("三行均为 absent-if-empty", t10.count('"observation":"absent-if-empty"') == 3)
chk("阶段选择规则含（一）P2", "（一）当本次操作属于 **P2**" in t10)
chk("阶段选择规则含（二）P5 及其后", "（二）当本次操作属于 **P5 及其后**" in t10)
chk("声明互斥且穷尽", "互斥且穷尽" in t10)
chk("明确 P5 的 allowlist 类型定义未被改动",
    "也不改变 `allowed_system_streams` 的类型定义" in t10)

print()
print("=== 2.4 B1 ===")
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
SC = re.compile(r"^[a-z0-9][a-z0-9.-]{0,127}$")
p1 = json.loads((REF / "external-gates/p1"
                 / "p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json")
                .read_text(encoding="utf-8"))
ffh = p1["payload"]["payload"]["forbidden_history_ids"]
vals = [x["id"] if isinstance(x, dict) else x for x in ffh]
chk("记录内 13 项", len(vals) == 13, str(len(vals)))
chk("13 项全部不匹配 ID", not any(ID.match(v) for v in vals))
chk("13 项全部匹配 SCHEMA_ID", all(SC.match(v) for v in vals))
chk("13 项全部含点号", all("." in v for v in vals))
chk("draft-0.10 两处标注均为 SCHEMA_ID",
    t10.count("id:SCHEMA_ID,ordinal:INT[0,12]") == 2,
    str(t10.count("id:SCHEMA_ID,ordinal:INT[0,12]")))
# Only forbidden_history_ids may be checked here. A bare "id:ID" substring also
# matches predicate_id:ID, sample_id:ID and dozens of unrelated fields, which is
# why this matches the element schema of this field alone.
chk("forbidden_history_ids 元素内无 id:ID",
    not re.search(r"forbidden_history_ids:A<\{id:ID,", t10))
chk("forbidden_history_ids 两处均带 ordinal 要素",
    len(re.findall(r"forbidden_history_ids:A<\{id:SCHEMA_ID,ordinal:INT\[0,12\]\}", t10)) == 2,
    str(len(re.findall(r"forbidden_history_ids:A<\{id:SCHEMA_ID,ordinal:INT\[0,12\]\}", t10))))
chk("ID/SCHEMA_ID 定义逐字未变",
    re.search(r"- `ID`：([^\n]+)", t09).group(1) == re.search(r"- `ID`：([^\n]+)", t10).group(1)
    and re.search(r"- `SCHEMA_ID`：([^\n]+)", t09).group(1)
    == re.search(r"- `SCHEMA_ID`：([^\n]+)", t10).group(1))

print()
print("=== 2.5 C2a ===")
by_bytes = sorted(vals, key=lambda s: s.encode("utf-8"))
by_num = sorted(vals, key=lambda s: int(s.rsplit(".v", 1)[1]))
chk("记录内实际为数字序", vals == by_num)
chk("order=value(UTF-8 bytes) 与数字序冲突", by_bytes != by_num)
print("      记录首三项:", vals[:3])
print("      bytes 序首三项:", by_bytes[:3])
chk("draft-0.10 含 order=key(ordinal)", t10.count("order=key(ordinal)") >= 2)
chk("order=value 定义逐字未变",
    re.search(r"- `order=value`：([^\n]+)", t09).group(1)
    == re.search(r"- `order=value`：([^\n]+)", t10).group(1))
chk("order=value 仍在使用（未被替换掉）", t10.count("order=value") >= 25,
    str(t10.count("order=value")))

print()
print("=== 2.6 D1a ===")
for p, label in ((P09, "draft-0.9"), (P10, "draft-0.10")):
    out = subprocess.run(["git", "check-attr", "text", "eol", "--",
                          p.relative_to(REPO).as_posix()], cwd=REPO,
                         capture_output=True).stdout.decode("utf-8", errors="replace")
    chk(f"{label} text: set / eol: lf", "text: set" in out and "eol: lf" in out, out.strip())
b09 = P09.read_bytes()
chk("draft-0.9 = 181209 / 6ccebc47…",
    len(b09) == 181209 and hashlib.sha256(b09).hexdigest().startswith("6ccebc47"),
    f"{len(b09)} {hashlib.sha256(b09).hexdigest()[:8]}")
repo09 = subprocess.run(["git", "cat-file", "-p",
                         "HEAD:docs/plans/references/m8-active-execution-protocol-draft-0.9.md"],
                        cwd=REPO, capture_output=True).stdout
chk("draft-0.9 工作区 == 仓库", b09 == repo09)
P05 = REF / "m8-active-execution-protocol-draft.md"
b05 = P05.read_bytes()
chk("draft-0.5 未被触及 171830 / ac907b83…",
    len(b05) == 171830 and hashlib.sha256(b05).hexdigest().startswith("ac907b83"),
    f"{len(b05)}")
out5 = subprocess.run(["git", "check-attr", "text", "eol", "--",
                       P05.relative_to(REPO).as_posix()], cwd=REPO,
                      capture_output=True).stdout.decode("utf-8", errors="replace")
chk("draft-0.5 仍不受行尾保护（D1b 未采纳）", "text: unspecified" in out5)

print()
print("=== 2.7 冻结不变量 ===")


def seg(t, pat, flags=0):
    m = re.search(pat, t, flags)
    return m.group(1) if m else None


pairs = [
    ("ID 定义", r"- `ID`：([^\n]+)"),
    ("SCHEMA_ID 定义", r"- `SCHEMA_ID`：([^\n]+)"),
    ("order=value 定义", r"- `order=value`：([^\n]+)"),
    ("order=key 定义", r"- `order=key\(([^\n]+)"),
    ("SYSTEM_RESERVED_STREAM 定义", r"- `SYSTEM_RESERVED_STREAM`：([^\n]+)"),
    ("status-map payload", r"`sa\.m8\.status-map\.v1\.payload` exact fields：(.*?)\n\n"),
    ("26 基数", r"(gates:A<TECH_GATE_RESULT;26\.\.26[^\n]*)"),
]
for label, pat in pairs:
    chk(f"冻结项未变：{label}", seg(t09, pat, re.S) == seg(t10, pat, re.S))
g09 = re.findall(r"`([a-z0-9-]+)`", seg(t09, r"`TECH_GATE_ID`：([^\n]+)"))
g10 = re.findall(r"`([a-z0-9-]+)`", seg(t10, r"`TECH_GATE_ID`：([^\n]+)"))
chk("TECH_GATE_ID 恰 26 项且逐字未变", len(g10) == 26 and g09 == g10, str(len(g10)))
chk("status-map 两项 72 基数在位", seg(t10, r"`sa\.m8\.status-map\.v1\.payload` exact fields：(.*?)\n\n", re.S).count("72..72") == 2)

print()
print("=== 2.8 记录绑定 ===")
recs = sorted((REF / "external-gates").rglob("*.json")) + sorted((REF / "external-artifacts").rglob("*.json"))
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


d09 = [p.name for p in recs if bound_digest(p).startswith("162c9047")]
d05 = [p.name for p in recs if bound_digest(p).startswith("ac907b83")]
chk("5 条记录仍绑 162c9047…（待重算）", len(d09) == 5, str(len(d09)))
chk("3 条记录仍绑 ac907b83…（不在范围）", len(d05) == 3, str(len(d05)))

print()
print("实测完成" if ok else "存在未通过项")
print("NOTE: 本脚本报告字节事实，不作 P0 裁定。裁定见 P0 记录本身。")
raise SystemExit(0 if ok else 1)
