"""Validate the metadata-only RFC exact-three candidate checkpoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_rfc_candidate_materialization import (  # noqa: E402
    RfcCandidateMaterializationError,
    validate_rfc_candidate_materialization,
)

MANIFEST = ROOT / "data/manifests/m11-p0-rfc-candidate-materialization-v1.json"


def main() -> int:
    try:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        validated = validate_rfc_candidate_materialization(payload)
    except (OSError, TypeError, json.JSONDecodeError, RfcCandidateMaterializationError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        "valid: 3 RFC candidate artifacts; 3 candidate chunks; 0 rejected; "
        "0 approved chunks; does not count toward 3K"
    )
    assert validated["publication_authorized"] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
