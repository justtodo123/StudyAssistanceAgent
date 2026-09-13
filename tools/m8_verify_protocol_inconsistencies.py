"""Mechanically re-verify the two protocol inconsistencies recorded in
docs/plans/references/m8-draft09-p1-materials-20260913.md section 4.

Read-only. It parses the protocol blob for the ID / SCHEMA_ID definitions and
the order=value definition, then checks the actual gate records against them.
It prints findings; it does not modify anything.

What this proves, and what it does not
--------------------------------------
It proves that both inconsistencies exist: the thirteen values do not match
``ID``, both records store them in numeric order, and that order differs from
the one ``order=value`` prescribes.

It does *not* determine which side is wrong, and it is not a bug report about
the values. ``SCHEMA_ID``'s character class is a strict superset of ``ID``'s
(it differs only by allowing the dot), so retyping the field and rewriting the
values are both sufficient to remove inconsistency 1; likewise, inconsistency 2
is removed either by re-sorting the records or by changing the comparator.
Only the protocol author can say which was intended, so this script stops at
demonstrating the contradiction.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / "docs/plans/references/m8-active-execution-protocol-draft-0.9.md"
P1_R02 = (
    ROOT
    / "docs/plans/references/external-gates/p1"
    / "p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json"
)
P1_D05 = (
    ROOT
    / "docs/plans/references/external-gates/p1"
    / "p1-m8-active-execution-active-draft05-955334f23b2a5c98.json"
)

failures: list[str] = []
checks = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if ok:
        print(f"OK   {label}")
    else:
        print(f"FAIL {label}{(' :: ' + detail) if detail else ''}")
        failures.append(label)


def read_protocol() -> str:
    # Normalise line endings so the patterns below are platform independent.
    return PROTOCOL.read_text(encoding="utf-8").replace("\r\n", "\n")


def extract_definition(text: str, name: str) -> str | None:
    """Return the character class in the type definition, plus any trailing
    constraint text (SCHEMA_ID carries an extra 'no .. and no trailing .' rule)."""
    m = re.search(
        rf"^- `{re.escape(name)}`：ASCII\[1,128\]，匹配 `([^`]+)`(.*)$", text, re.M
    )
    return m.group(1) if m else None


def extract_trailing(text: str, name: str) -> str:
    m = re.search(
        rf"^- `{re.escape(name)}`：ASCII\[1,128\]，匹配 `[^`]+`(.*)$", text, re.M
    )
    return m.group(1) if m else ""


def main() -> int:
    text = read_protocol()

    id_def = extract_definition(text, "ID")
    schema_def = extract_definition(text, "SCHEMA_ID")

    check("protocol defines ID", id_def is not None, str(id_def))
    check("protocol defines SCHEMA_ID", schema_def is not None, str(schema_def))
    if id_def is None or schema_def is None:
        return finish()

    # Python regexes mirror the protocol's own character classes.
    id_re = re.compile(r"^" + id_def.replace("{0,127}", "{0,127}") + r"$")
    schema_re = re.compile(r"^" + schema_def + r"$")

    check("ID forbids the dot", not id_re.match("sa.m8.admission-evidence.v1"))
    check(
        "SCHEMA_ID allows the dot",
        bool(schema_re.match("sa.m8.admission-evidence.v1")),
    )

    # ---- Finding 1: the field is annotated ID but the values are SCHEMA_ID ----
    payload = json.loads(P1_R02.read_text(encoding="utf-8"))["payload"]["payload"]
    ids = payload["forbidden_history_ids"]
    check("P1 -r02 carries 13 forbidden_history_ids", len(ids) == 13, str(len(ids)))
    check(
        "none of the 13 values match ID (matches the recorded defect)",
        not any(id_re.match(x) for x in ids),
    )
    check(
        "all 13 values match SCHEMA_ID",
        all(schema_re.match(x) for x in ids),
    )
    # SCHEMA_ID carries a trailing rule beyond the character class; the values
    # must satisfy it too, or the retyping would be wrong for a second reason.
    trailing = extract_trailing(text, "SCHEMA_ID")
    check("SCHEMA_ID declares an extra constraint", ".." in trailing, trailing[:40])
    check(
        "no value contains '..' or ends with '.'",
        all(".." not in x and not x.endswith(".") for x in ids),
    )
    check(
        "the protocol annotates the field with ID, not SCHEMA_ID",
        "forbidden_history_ids:A<ID;13..13" in text,
    )

    # ---- Finding 2: order=value by UTF-8 bytes contradicts the stored order ----
    # The definition wraps onto a second line that indents with two spaces.
    order_def = re.search(r"^- `order=value`：(.*(?:\n  [^\n]*)*)", text, re.M)
    check("protocol defines order=value", order_def is not None)
    if order_def:
        body = order_def.group(1)
        check(
            "order=value sorts these types by UTF-8 bytes",
            "按 UTF-8 bytes" in body and "SCHEMA_ID" in body,
            body.replace("\n", " ")[:90],
        )

    # Values are ASCII, so UTF-8 byte order equals code-point order.
    lexical = sorted(ids)
    check(
        "the stored order is not the order the protocol prescribes",
        ids != lexical,
        f"prescribed starts {lexical[:3]}",
    )
    numeric = sorted(ids, key=lambda s: int(s.rsplit(".v", 1)[1]))
    check("the stored order is numeric order", ids == numeric)

    # Same stored order in the retained draft-0.5 record.
    d05 = json.loads(P1_D05.read_text(encoding="utf-8"))["payload"]["payload"]
    d05_ids = d05["forbidden_history_ids"]
    check("the draft-0.5 record uses the same numeric order", d05_ids == numeric)
    check("both records are therefore inconsistent with the protocol", d05_ids != sorted(d05_ids))

    return finish()


def finish() -> int:
    print()
    print(f"checks: {checks}  failed: {len(failures)}")
    if failures:
        print("FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
