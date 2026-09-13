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
                        ("0.8", review_08, "0.7")):
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

        print("  [residual defects still present]")
        for n, ok in residual:
            print(("    PRESENT " if ok else "    ABSENT  ") + n)

        blocking = [n for n, ok in residual if ok and "blocking" in n]
        all_fixed = all(ok for _, ok in fixed)
        ident_ok = all(ok for _, ok in identity)

        if not ident_ok:
            verdict = "INVALID"
        elif all_fixed and not blocking:
            verdict = "PASS"
        elif all_fixed and blocking:
            verdict = "RETURNED_FOR_REVISION"
        else:
            verdict = "RETURNED_FOR_REVISION"
        verdicts[v] = verdict

    print("\n" + "=" * 76)
    for v in ("0.6", "0.7", "0.8"):
        print(f"draft-{v}: {verdicts[v]}")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
