"""Validate owner-authorized RFC revision/provenance/parser decisions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_rfc_technical_evidence_review import (  # noqa: E402
    RfcTechnicalEvidenceReviewError,
    validate_rfc_technical_result,
)

MANIFESTS = ROOT / "data/manifests"


def main() -> int:
    try:
        result = json.loads((MANIFESTS / "m11-p0-rfc-technical-evidence-review-result-v1.json").read_text(encoding="utf-8"))
        authority = json.loads((MANIFESTS / "m11-p0-rfc-technical-evidence-review-authority-v1.json").read_text(encoding="utf-8"))
        schema_result = json.loads((MANIFESTS / "m11-p0-rfc-schema-review-result-v1.json").read_text(encoding="utf-8"))
        validated = validate_rfc_technical_result(result, authority=authority, schema_result=schema_result)
    except (OSError, TypeError, json.JSONDecodeError, RfcTechnicalEvidenceReviewError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        f"valid: {validated['verified_cell_count']} VERIFIED + "
        f"{validated['not_applicable_cell_count']} NOT_APPLICABLE; "
        f"{validated['pending_cell_count']} PENDING; no successor; this validator does not execute repository-wide Gate 0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
