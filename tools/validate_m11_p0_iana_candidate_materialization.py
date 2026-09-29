"""Validate the IANA exact-three materialization checkpoint."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_iana_candidate_materialization import (  # noqa: E402
    IanaCandidateMaterializationError,
    validate_iana_candidate_materialization,
)

MANIFEST = ROOT / "data/manifests/m11-p0-iana-candidate-materialization-v1.json"

def main() -> int:
    try:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        validate_iana_candidate_materialization(payload)
    except (OSError, TypeError, json.JSONDecodeError, IanaCandidateMaterializationError) as exc:
        print(f"invalid: {exc}")
        return 1
    print("valid: 3 IANA candidates; 3 chunks; 0 rejects; 0 approved; historical Gate0 remains BLOCKED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
