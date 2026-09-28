"""Validate owner-authorized RFC legal-policy decisions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_rfc_legal_policy_review import (  # noqa: E402
    RfcLegalPolicyReviewError,
    validate_rfc_legal_policy_result,
)

MANIFESTS = ROOT / "data/manifests"


def _load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))


def main() -> int:
    try:
        validated = validate_rfc_legal_policy_result(
            _load("m11-p0-rfc-legal-policy-review-result-v1.json"),
            authority=_load("m11-p0-rfc-legal-policy-review-authority-v1.json"),
            census=_load("m11-p0-rfc-legal-policy-census-v1.json"),
            content_quality_result=_load("m11-p0-rfc-content-quality-review-result-v1.json"),
        )
    except (OSError, TypeError, json.JSONDecodeError, RfcLegalPolicyReviewError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        f"valid: {validated['verified_cell_count']} VERIFIED + "
        f"{validated['not_applicable_cell_count']} NOT_APPLICABLE; 0 PENDING; "
        "evidence complete; no successor; Gate 0 unexecuted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
