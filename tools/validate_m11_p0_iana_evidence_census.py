from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_iana_evidence_census import (  # noqa: E402
    IanaEvidenceCensusError,
    validate_iana_evidence_census,
)

MANIFEST = ROOT / "data/manifests/m11-p0-iana-evidence-census-v1.json"
DIGEST_EVIDENCE = ROOT / "data/manifests/m11-p0-digest-evidence-v1.json"
RECEIPT_BATCH = ROOT / "data/manifests/m11-p0-acquisition-26-receipts-v1.json"


def main() -> int:
    try:
        validated = validate_iana_evidence_census(
            json.loads(MANIFEST.read_text(encoding="utf-8")),
            digest_evidence=json.loads(DIGEST_EVIDENCE.read_text(encoding="utf-8")),
            receipt_batch=json.loads(RECEIPT_BATCH.read_text(encoding="utf-8")),
        )
    except (OSError, TypeError, json.JSONDecodeError, IanaEvidenceCensusError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        f"valid: {validated['sample_size']} IANA census records; CC0 and robots observations "
        "captured; XML date conflict remains UNRESOLVED; 24 cells remain PENDING; no authority"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
