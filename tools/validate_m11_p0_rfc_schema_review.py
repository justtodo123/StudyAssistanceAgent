"""Validate the owner-authorized RFC exact-three schema N/A decision."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_rfc_schema_review import (  # noqa: E402
    RfcSchemaReviewError,
    validate_rfc_schema_review_result,
)

MANIFESTS = ROOT / "data/manifests"


def main() -> int:
    try:
        result = json.loads((MANIFESTS / "m11-p0-rfc-schema-review-result-v1.json").read_text(encoding="utf-8"))
        authority = json.loads((MANIFESTS / "m11-p0-rfc-schema-review-authority-v1.json").read_text(encoding="utf-8"))
        validated = validate_rfc_schema_review_result(result, authority=authority)
    except (OSError, TypeError, json.JSONDecodeError, RfcSchemaReviewError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        f"valid: {validated['closed_cell_count']} RFC schema cells NOT_APPLICABLE; "
        f"{validated['pending_cell_count']} cells remain PENDING; no successor; Gate 0 unexecuted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
