from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_iana_evidence_closure_packet import (  # noqa: E402
    IanaEvidenceClosurePacketError,
    validate_iana_evidence_closure_packet,
)

PACKET = ROOT / "data/manifests/m11-p0-iana-evidence-closure-packet-v1.json"
DIGEST_EVIDENCE = ROOT / "data/manifests/m11-p0-digest-evidence-v1.json"
RECEIPT_BATCH = ROOT / "data/manifests/m11-p0-acquisition-26-receipts-v1.json"


def main() -> int:
    try:
        validated = validate_iana_evidence_closure_packet(
            json.loads(PACKET.read_text(encoding="utf-8")),
            digest_evidence=json.loads(DIGEST_EVIDENCE.read_text(encoding="utf-8")),
            receipt_batch=json.loads(RECEIPT_BATCH.read_text(encoding="utf-8")),
        )
    except (OSError, TypeError, json.JSONDecodeError, IanaEvidenceClosurePacketError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        f"valid: {len(validated['batch_records'])} IANA owner decision-input records; "
        "24 statuses remain PENDING; authority not issued; current heads unchanged; "
        "historical Formal Gate0 remains BLOCKED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
