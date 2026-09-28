"""Validate owner-authorized RFC content-quality decisions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_rfc_content_quality_review import (  # noqa: E402
    RfcContentQualityReviewError,
    validate_rfc_content_quality_result,
)

MANIFESTS = ROOT / "data/manifests"


def _load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))


def main() -> int:
    try:
        validated = validate_rfc_content_quality_result(
            _load("m11-p0-rfc-content-quality-review-result-v1.json"),
            authority=_load("m11-p0-rfc-content-quality-review-authority-v1.json"),
            sampling_result=_load("m11-p0-rfc-content-quality-sampling-result-v1.json"),
            technical_result=_load("m11-p0-rfc-technical-evidence-review-result-v1.json"),
            schema_result=_load("m11-p0-rfc-schema-review-result-v1.json"),
        )
    except (OSError, TypeError, json.JSONDecodeError, RfcContentQualityReviewError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        f"valid: {validated['verified_cell_count']} VERIFIED + "
        f"{validated['not_applicable_cell_count']} NOT_APPLICABLE; "
        f"{validated['pending_cell_count']} legal-policy cells remain PENDING; "
        "no successor; Gate 0 unexecuted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
