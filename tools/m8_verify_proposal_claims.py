"""Verify every factual claim made in m8-protocol-revision-proposal-20260913.md."""
import glob
import hashlib
import json
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
# The proposal was written before D1a was applied, when the working copy was
# CRLF (162c9047..., 182575 bytes) and the repository LF (6ccebc47..., 181209
# bytes). D1a pinned the protocol to LF, so those two now agree. What the
# proposal asserted about draft-0.5 must still hold, since D1b was declined.
chk("draft-0.9 工作区摘要 = 6ccebc47…（D1a 后工作区已为 LF）", w.startswith("6ccebc47"), w[:16])
chk("draft-0.9 仓库摘要 = 6ccebc47…", r.startswith("6ccebc47"), r[:16])
chk("draft-0.9 工作区 181209 bytes", wn == 181209, str(wn))
chk("draft-0.9 仓库 181209 bytes", rn == 181209, str(rn))
chk("draft-0.9 工作区字节 == 仓库字节（D1a 的直接目的）", wn == rn, f"{wn} vs {rn}")

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
P10 = "docs/plans/references/m8-active-execution-protocol-draft-0.10.md"
for f, label in ((P09, "draft-0.9"), (P10, "draft-0.10"), (P05, "draft-0.5")):
    out = subprocess.run(["git", "check-attr", "text", "eol", "--", f], capture_output=True, text=True).stdout
    if label == "draft-0.5":
        # D1b was declined: draft-0.5 is frozen history and stays as it is.
        chk(f"{label} 协议仍未受保护（D1b 已否决，属预期）", "text: unspecified" in out, out.strip())
    else:
        # D1a pinned these; they are the live chain root.
        chk(f"{label} 协议已由 D1a 锁定为 LF", "eol: lf" in out, out.strip())

print()
print("全部核实通过" if ok else "存在未通过项")
raise SystemExit(0 if ok else 1)
