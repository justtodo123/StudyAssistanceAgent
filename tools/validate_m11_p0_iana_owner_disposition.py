from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_iana_owner_disposition import (  # noqa: E402
    IanaOwnerDispositionError,
    validate_iana_owner_disposition,
)

DISPOSITION = ROOT / "data/manifests/m11-p0-iana-owner-disposition-v1.json"
PACKET = ROOT / "data/manifests/m11-p0-iana-evidence-closure-packet-v1.json"
CENSUS = ROOT / "data/manifests/m11-p0-iana-evidence-census-v1.json"
DIGEST_EVIDENCE = ROOT / "data/manifests/m11-p0-digest-evidence-v1.json"
RECEIPT_BATCH = ROOT / "data/manifests/m11-p0-acquisition-26-receipts-v1.json"


def main() -> int:
    try:
        validated = validate_iana_owner_disposition(
            json.loads(DISPOSITION.read_text(encoding="utf-8")),
            packet=json.loads(PACKET.read_text(encoding="utf-8")),
            census=json.loads(CENSUS.read_text(encoding="utf-8")),
            digest_evidence=json.loads(DIGEST_EVIDENCE.read_text(encoding="utf-8")),
            receipt_batch=json.loads(RECEIPT_BATCH.read_text(encoding="utf-8")),
        )
    except (OSError, TypeError, json.JSONDecodeError, IanaOwnerDispositionError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        f"valid: owner disposition for {len(validated['records'])} IANA assets; XML UNRESOLVED; "
        "TXT FAIL_CLOSED; 3 schema cells applicable/PENDING; all escalation false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
