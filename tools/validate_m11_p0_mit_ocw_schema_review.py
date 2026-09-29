from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform"))
from app.m11_mit_ocw_schema_review import MitOcwSchemaReviewError, validate_mit_ocw_schema_result

MANIFESTS = ROOT / "data/manifests"

def load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text(encoding="utf-8"))

def main() -> int:
    try:
        result = validate_mit_ocw_schema_result(load("m11-p0-mit-ocw-schema-review-result-v1.json"), authority=load("m11-p0-mit-ocw-schema-review-authority-v1.json"), packet=load("m11-p0-mit-ocw-owner-decision-input-packet-v1.json"), materialization=load("m11-p0-mit-ocw-candidate-materialization-v1.json"), digest_evidence=load("m11-p0-digest-evidence-v1.json"), receipt_batch=load("m11-p0-acquisition-26-receipts-v1.json"), gate0_result=load("m11-p0-formal-gate0-26-result-v1.json"))
    except (OSError, TypeError, json.JSONDecodeError, MitOcwSchemaReviewError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(f"valid: {result['asset_count']} exact MIT candidates; {result['pending_cell_count']} schema cells PENDING; packet total {result['packet_pending_cell_count']}; no closure or escalation")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
