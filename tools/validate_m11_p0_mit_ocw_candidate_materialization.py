"""Validate the metadata-only MIT OCW candidate materialization checkpoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_mit_ocw_candidate_materialization import (  # noqa: E402
    MitOcwCandidateMaterializationError,
    validate_mit_ocw_candidate_materialization,
)

MANIFEST = ROOT / "data/manifests/m11-p0-mit-ocw-candidate-materialization-v1.json"


def main() -> int:
    try:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        validated = validate_mit_ocw_candidate_materialization(payload)
    except (OSError, TypeError, json.JSONDecodeError, MitOcwCandidateMaterializationError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        "valid: 18 MIT candidate artifacts; 93 candidate chunks; 2 rejections; "
        "0 approved chunks; does not count toward 3K"
    )
    assert validated["publication_authorized"] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
