"""Verify every factual claim made in m8-protocol-revision-proposal-20260913.md."""
import glob
import hashlib
import subprocess

ok = True


def chk(label, cond, detail=""):
    global ok
    print(("OK   " if cond else "FAIL ") + label + ((" :: " + detail) if not cond else ""))
    ok = ok and cond


def sha(path, inrepo=False):
    if inrepo:
        b = subprocess.run(["git", "cat-file", "-p", "HEAD:" + path], capture_output=True).stdout
    else:
        b = open(path, "rb").read()
    return hashlib.sha256(b).hexdigest(), len(b)


P09 = "docs/plans/references/m8-active-execution-protocol-draft-0.9.md"
P05 = "docs/plans/references/m8-active-execution-protocol-draft.md"

w, wn = sha(P09)
r, rn = sha(P09, True)
chk("draft-0.9 工作区摘要 = 162c9047…", w.startswith("162c9047"), w[:16])
chk("draft-0.9 仓库摘要 = 6ccebc47…", r.startswith("6ccebc47"), r[:16])
chk("draft-0.9 工作区 182575 bytes", wn == 182575, str(wn))
chk("draft-0.9 仓库 181209 bytes", rn == 181209, str(rn))
chk("draft-0.9 差值 = 1366 = CR 数", wn - rn == 1366, str(wn - rn))

w5, wn5 = sha(P05)
r5, rn5 = sha(P05, True)
chk("draft-0.5 工作区摘要 = ac907b83…", w5.startswith("ac907b83"), w5[:16])
chk("draft-0.5 仓库摘要 = 4ab35a66…", r5.startswith("4ab35a66"), r5[:16])
chk("draft-0.5 工作区 171830 bytes", wn5 == 171830, str(wn5))
chk("draft-0.5 仓库 170550 bytes", rn5 == 170550, str(rn5))
chk("draft-0.5 差值 = 1280 = CR 数", wn5 - rn5 == 1280, str(wn5 - rn5))

recs = sorted(glob.glob("docs/plans/references/external-gates/*/*.json")) + sorted(
    glob.glob("docs/plans/references/external-artifacts/identity/*.json")
)
d09 = sum(1 for p in recs if "162c9047" in open(p, encoding="utf-8").read())
d05 = sum(1 for p in recs if "ac907b83" in open(p, encoding="utf-8").read())
chk("绑定 162c9047 的记录 = 5 条", d09 == 5, str(d09))
chk("绑定 ac907b83 的记录 = 3 条", d05 == 3, str(d05))
chk("合计 8 条", d09 + d05 == 8, str(d09 + d05))

text = open(P09, encoding="utf-8").read()
# Two different counts are easy to confuse: lines that mention the comparator
# versus individual field annotations. The proposal cites the latter.
occurrences = text.count("order=value")
lines = sum(1 for ln in text.splitlines() if "order=value" in ln)
chk("order=value 出现 29 次（= 29 个字段标注）", occurrences == 29, str(occurrences))
chk("order=value 分布于 27 行", lines == 27, str(lines))

# 协议文本的行尾保护状态
for f, label in ((P09, "draft-0.9"), (P05, "draft-0.5")):
    out = subprocess.run(["git", "check-attr", "text", "eol", "--", f], capture_output=True, text=True).stdout
    chk(f"{label} 协议未受行尾保护（text: unspecified）", "text: unspecified" in out, out.strip())

print()
print("全部核实通过" if ok else "存在未通过项")
raise SystemExit(0 if ok else 1)
