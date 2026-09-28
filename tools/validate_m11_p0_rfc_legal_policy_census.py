"""Validate the metadata-only RFC legal-policy census."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_rfc_legal_policy_census import (  # noqa: E402
    RfcLegalPolicyCensusError,
    validate_rfc_legal_policy_census,
)

MANIFEST = ROOT / "data/manifests/m11-p0-rfc-legal-policy-census-v1.json"


def main() -> int:
    try:
        validated = validate_rfc_legal_policy_census(json.loads(MANIFEST.read_text(encoding="utf-8")))
    except (OSError, TypeError, json.JSONDecodeError, RfcLegalPolicyCensusError) as exc:
        print(f"invalid: {exc}")
        return 1
    families = {item["notice_family"] for item in validated["records"]}
    print(
        f"valid: {validated['sample_size']} RFC legal notice records; "
        f"families={','.join(sorted(families))}; 9 legal-policy cells remain PENDING; "
        "no network; no authority; Gate 0 unexecuted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
