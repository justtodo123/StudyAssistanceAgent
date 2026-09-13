"""Independent P0 technical reviewer for M8 active-execution-protocol drafts 0.6/0.7/0.8.

This program performs a MECHANICAL P0 technical review of the three protocol
drafts that were produced without prior authorization. It is deliberately
independent of the drafting scripts (apply_draft0X_revision.py): it does not
import them, and it re-derives every fact from the protocol blobs themselves.

Review model
------------
For each reviewed draft the program answers two questions:

  FIXED  - is the defect set that this draft CLAIMS to repair actually repaired?
  RESIDUAL - does this draft still exhibit the defect set that the NEXT draft
             was written to repair (i.e. is it not the last word)?

A draft is PASS only if FIXED is fully satisfied AND no residual defect of the
`blocking` class remains. A draft that repairs its own claimed defects but still
carries blocking residuals is RETURNED_FOR_REVISION - which is exactly the
situation of draft-0.6 and draft-0.7 in this repository.

The program produces NO execution authority of any kind.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

REF = Path(r"D:\Git Demo\StudyAssistanceAgent\docs\plans\references")

EXPECTED_BYTES = {"0.5": 171830, "0.6": 174214, "0.7": 175826,
                  "0.8": 180033, "0.9": 182575}

# The 0.9 review is a tip-of-chain review: it verifies that every repair the
# draft claims actually holds and that the retained invariants of the whole
# chain survive. It is deliberately NOT phrased as a residual hunt because no
# successor draft exists to define a residual set.


def blob(v: str) -> Path:
    if v == "0.5":
        return REF / "m8-active-execution-protocol-draft.md"
    return REF / f"m8-active-execution-protocol-draft-{v}.md"


def read(v: str) -> str:
    return blob(v).read_bytes().decode("utf-8")


def norm(t: str) -> str:
    return t.replace("\r\n", "\n")


def digest(v: str) -> str:
    return hashlib.sha256(blob(v).read_bytes()).hexdigest()


# ------------------------------------------------------------ status map -----
STATUS_MAP_RE = re.compile(
    r"`sa\.m8\.status-map\.v1\.payload` exact fields：(?P<body>.*?)(?=\n`sa\.m8\.|\Z)",
    re.S,
)
STATUS_ROW_RE = re.compile(
    r"^\|\s*`(?P<dom>backend|ntstatus|protocol|watchdog)`\s*"
    r"\|\s*`(?P<ph>preflight|runtime|cleanup)`\s*"
    r"\|\s*`(?P<raw>[A-Z0-9_]+)`\s*"
    r"\|\s*`(?P<code>[A-Z0-9_]+)`\s*\|\s*$"
)


def status_map_rows(v: str) -> list[str]:
    m = STATUS_MAP_RE.search(read(v))
    seg = m.group("body") if m else ""
    return [l.strip() for l in seg.split("\n") if STATUS_ROW_RE.match(l.strip())]


def diff_lines(a: str, b: str) -> tuple[int, int]:
    import difflib
    la, lb = norm(read(a)).split("\n"), norm(read(b)).split("\n")
    sm = difflib.SequenceMatcher(None, la, lb)
    hunks = changed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            hunks += 1
            changed += (i2 - i1) + (j2 - j1)
    return hunks, changed


def has(t: str, s: str) -> bool:
    return s in t


# ---------------------------------------------------------------- review -----
def review_06() -> tuple[list[tuple[str, bool]], list[tuple[str, bool]]]:
    t = read("0.6")
    fixed = [
        ("0.5 defect R1 repaired: SYSTEM_RESERVED_STREAM enum defined",
         has(t, "SYSTEM_RESERVED_STREAM")),
        ("0.5 defect R2 repaired: allowed_system_streams field present",
         has(t, "allowed_system_streams")),
        ("0.5 defect R1/R2 repaired: sguard handled as a named system stream",
         has(t, "sguard")),
        ("0.5 defect R1/R2 repaired: section 7 separates unnamed vs reserved",
         has(t, "SYSTEM_RESERVED_STREAM") and has(t, "§7")),
    ]
    # draft-0.7 was written to repair these in 0.6 => they are 0.6 residuals.
    residual = [
        ("RESIDUAL (blocking): SYSTEM_RESERVED_STREAM is defined outside §2.2 "
         "(type placement defect)", "闭合枚举" in t and not has(t, "- `STREAM_SCOPE`")),
        ("RESIDUAL (blocking): no STREAM_SCOPE enum, so volume/device root has "
         "no stream decision domain", not has(t, "STREAM_SCOPE")),
        ("RESIDUAL (blocking): allowlist cardinality is still the free range "
         "0..2 rather than the derived constant",
         has(t, "};0..2;") or not has(t, "};3..3")),
        ("RESIDUAL (blocking): interposition ADS carve-out absent",
         not has(t, "is not an alternate data stream for the")),
        ("RESIDUAL (blocking): FileStreamInformation not in information_class",
         not has(t, "FileStreamInformation")),
    ]
    return fixed, residual


def review_07() -> tuple[list[tuple[str, bool]], list[tuple[str, bool]]]:
    t = read("0.7")
    fixed = [
        ("0.6 defect B1 repaired: STREAM_SCOPE enum introduced with volume-root",
         has(t, "STREAM_SCOPE") and has(t, "volume-root")),
        ("0.6 defect B1 repaired: SYSTEM_RESERVED_STREAM defined exactly once",
         t.count("`SYSTEM_RESERVED_STREAM`：闭合枚举") == 1),
        ("0.6 defect B3 repaired: allowlist cardinality is 3..3",
         has(t, "};3..3")),
        ("0.6 defect B4 repaired: FileStreamInformation present",
         has(t, "FileStreamInformation")),
        ("0.6 defect B4 repaired: query-streams mapping split out",
         has(t, "query-streams")),
    ]
    # draft-0.8 was written to repair these in 0.7 => they are 0.7 residuals.
    residual = [
        ("RESIDUAL (blocking): volume-root scope is decided from "
         "authoritative_handle_source, which does not carry that meaning",
         not has(t, "opens_volume_root")),
        ("RESIDUAL (blocking): allowed_system_streams.observation is declared "
         "but never consumed", not has(t, "并按该行的 `observation` 判定")),
        ("RESIDUAL (blocking): per-operation stream re-verification is not "
         "representable (no stream_reverify field)",
         not has(t, "stream_reverify")),
    ]
    return fixed, residual


def body_only(v: str) -> str:
    """Protocol body with the '> ' revision-changelog header lines removed.

    Revision prose must never satisfy or violate a schema assertion, so every
    field-level check below runs against this view.
    """
    return "\n".join(l for l in norm(read(v)).split("\n") if not l.startswith(">"))


def review_08() -> tuple[list[tuple[str, bool]], list[tuple[str, bool]]]:
    t = read("0.8")
    fixed = [
        ("0.7 defect B1 repaired: opens_volume_root introduced",
         has(t, "opens_volume_root")),
        ("0.7 defect B2 repaired: observation consumed in section 7",
         has(t, "observation") and has(t, "并按该行的")),
        ("0.7 defect B3 repaired: stream_reverify/stream_scope/"
         "stream_query_source present",
         all(has(t, k) for k in ("stream_reverify", "stream_scope",
                                 "stream_query_source"))),
    ]
    # draft-0.9 was written to repair these in 0.8 => they are 0.8 residuals.
    residual = [
        ("RESIDUAL (blocking): scope is frozen as a profile constant although "
         "parent-walk opens both the volume root and ordinary directories",
         not has(t, "per-open")),
        ("RESIDUAL (blocking): stream_scope is a single scalar "
         "(derived-from-profile), not per-open",
         has(t, 'stream_scope:oneOf[literal["derived-from-profile"]')),
        ("RESIDUAL (blocking): stream_query_source.handle_source still admits "
         "root-directory-handle",
         has(t, 'handle_source:enum[root-directory-handle,opened-file-handle]')),
        ("RESIDUAL (non-blocking): decorative allowed_system_streams_closed "
         "flag present", has(t, "allowed_system_streams_closed")),
        ("RESIDUAL (non-blocking): unreachable stream_reverify=not-applicable "
         "member present", has(t, "stream_reverify:enum[required,not-applicable]")),
    ]
    return fixed, residual


def review_09() -> tuple[list[tuple[str, bool]], list[tuple[str, bool]]]:
    t = body_only("0.9")
    fixed = [
        ("0.8 defect A repaired: STREAM_SCOPE is per-open, decided by the "
         "object each open actually obtains",
         has(t, "per-open") and has(t, "`STREAM_SCOPE` 是 **per-open** 的")),
        ("0.8 defect A repaired: profile no longer carries opens_volume_root",
         not has(t, "opens_volume_root")),
        ("0.8 defect A repaired: walk freezes the volume-root identity up front",
         has(t, "必须先打开并冻结起始卷根 handle")),
        ("0.8 defect B repaired: stream_scope_per_open replaces the scalar "
         "derived-from-profile field",
         has(t, 'stream_scope_per_open:"required"')
         and not has(t, 'stream_scope:oneOf[literal["derived-from-profile"]')),
        ("0.8 defect C repaired: stream_query_source admits only "
         "opened-file-handle",
         bool(re.search(
             r'stream_query_source:oneOf\[literal\["not-applicable"\],'
             r'\{information_class:"FileStreamInformation",api:"NtQueryInformationFile",'
             r'handle_source:"opened-file-handle"\}\]', t))),
        ("0.8 defect D repaired: decorative allowed_system_streams_closed gone "
         "from schema",
         not has(t, "allowed_system_streams_closed")),
        ("0.8 defect D repaired: unreachable stream_reverify enum gone",
         not has(t, "stream_reverify:enum[")
         and has(t, 'stream_reverify:"required"')),
    ]
    # Nothing downstream has repaired 0.9 yet, so there is no residual class to
    # check; instead the retained invariants of the whole chain are re-verified.
    residual = [
        ("RETAINED: scope enum remains three-valued",
         has(t, "`STREAM_SCOPE`：`enum[file,directory,volume-root]`")),
        ("RETAINED: SYSTEM_RESERVED_STREAM defined exactly once",
         t.count("`SYSTEM_RESERVED_STREAM`：闭合枚举") == 1),
        ("RETAINED: allowlist cardinality is the derived 3..3 constant",
         has(t, "};3..3;order=key(scope);unique=key(scope)>")),
        ("RETAINED: observation is consumed in section 7",
         has(t, "并按该行的 `observation` 判定")),
        ("RETAINED: FileStreamInformation query is the stream source",
         has(t, 'information_class:"FileStreamInformation"')),
        ("RETAINED: interposition ADS carve-out kept",
         has(t, "is not an alternate data stream for the")),
        ("RETAINED: volume-root identity compared over four FILE_IDENTITY "
         "fields via FileIdInformation",
         has(t, "`NtQueryInformationFile(FileIdInformation)`")),
    ]
    return fixed, residual


def main() -> int:
    print("=" * 76)
    print("M8 draft reviewer - mechanical P0 technical review")
    print("reviewer: independent process tools/m8_draft_reviewer.py")
    print("=" * 76)

    baseline_rows = status_map_rows("0.5")
    baseline_block = "\n".join(baseline_rows)

    verdicts: dict[str, str] = {}
    for v, fn, prev in (("0.6", review_06, "0.5"),
                        ("0.7", review_07, "0.6"),
                        ("0.8", review_08, "0.7"),
                        ("0.9", review_09, "0.8")):
        fixed, residual = fn()
        raw = blob(v).read_bytes()
        rows = status_map_rows(v)
        hunks, lines = diff_lines(prev, v)

        identity = [
            (f"byte count == {EXPECTED_BYTES[v]}", len(raw) == EXPECTED_BYTES[v]),
            ("no BOM", raw[:3] != b"\xef\xbb\xbf"),
            ("UTF-8 decodable", True),
            (f"status-map rows == baseline {len(baseline_rows)}", len(rows) == len(baseline_rows)),
            ("status-map rows byte-identical to draft-0.5",
             "\n".join(rows) == baseline_block),
        ]

        print(f"\n--- draft-{v} ---")
        print(f"  bytes={len(raw)} sha256={digest(v)}")
        print(f"  diff vs draft-{prev}: {hunks} hunks / {lines} lines\n")

        print("  [identity & frozen invariants]")
        for n, ok in identity:
            print(("    OK   " if ok else "    FAIL ") + n)

        print("  [claimed repairs]")
        for n, ok in fixed:
            print(("    OK   " if ok else "    FAIL ") + n)

        label = ("[retained invariants (must all hold)]" if v == "0.9"
                 else "[residual defects still present]")
        print("  " + label)
        for n, ok in residual:
            if v == "0.9":
                print(("    HOLDS   " if ok else "    BROKEN  ") + n)
            else:
                print(("    PRESENT " if ok else "    ABSENT  ") + n)

        blocking = [n for n, ok in residual if ok and "blocking" in n]
        all_fixed = all(ok for _, ok in fixed)
        ident_ok = all(ok for _, ok in identity)

        if not ident_ok:
            verdict = "INVALID"
        elif v == "0.9":
            # 0.9 is the tip of the chain: it is PASS only if every claimed
            # repair holds AND every retained invariant still holds.
            retained_ok = all(ok for _, ok in residual)
            verdict = ("PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY"
                       if all_fixed and retained_ok else "NEEDS_ATTENTION")
        elif all_fixed and not blocking:
            verdict = "PASS"
        else:
            verdict = "RETURNED_FOR_REVISION"
        verdicts[v] = verdict

    print("\n" + "=" * 76)
    for v in ("0.6", "0.7", "0.8", "0.9"):
        print(f"draft-{v}: {verdicts[v]}")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
