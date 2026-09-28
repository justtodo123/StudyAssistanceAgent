"""Validate the non-executing RFC exact-three closure packet."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_rfc_evidence_closure_packet import (  # noqa: E402
    RfcEvidenceClosurePacketError,
    validate_rfc_evidence_closure_packet,
)

PACKET = ROOT / "data/manifests/m11-p0-rfc-evidence-closure-packet-draft-v1.json"


def main() -> int:
    try:
        payload = json.loads(PACKET.read_text(encoding="utf-8"))
        validate_rfc_evidence_closure_packet(payload)
    except (OSError, TypeError, json.JSONDecodeError, RfcEvidenceClosurePacketError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        "valid: RFC exact-three non-executing packet; 24 evidence statuses remain PENDING; "
        "authority not issued; Gate 0 remains unexecuted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
