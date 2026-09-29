"""Validate RFC exact-three ACCEPT successor without executing Gate 0."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_rfc_exact_three_successor import (  # noqa: E402
    RfcExactThreeSuccessorError,
    validate_rfc_exact_three_successor,
)

M = ROOT / "data/manifests"


def _load(name: str) -> dict:
    return json.loads((M / name).read_text(encoding="utf-8"))


def main() -> int:
    try:
        result = validate_rfc_exact_three_successor(
            authority=_load("m11-p0-rfc-exact-three-accept-authority-v1.json"),
            result=_load("m11-p0-rfc-exact-three-accept-result-v1.json"),
            legal_result=_load("m11-p0-rfc-legal-policy-review-result-v1.json"),
            successor_wrapper=_load("m11-p0-human-review-rfc-exact-three-accept-3-v1.json"),
            official_reviews=_load("m11-p0-human-review-official-observation-defer-26-v1.json")["records"],
            exact_six_reviews=_load("m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json")["records"],
            mit_reviews=_load("m11-p0-human-review-mit-ocw-evidence-defer-20-v1.json")["records"],
        )
    except (OSError, TypeError, json.JSONDecodeError, RfcExactThreeSuccessorError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        f"valid: {result['asset_count']} RFC current heads ACCEPT_FOR_PROMOTION_REVIEW; "
        "IANA/MIT remain DEFER; this validator does not execute repository-wide Gate 0; promotion/publication false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
