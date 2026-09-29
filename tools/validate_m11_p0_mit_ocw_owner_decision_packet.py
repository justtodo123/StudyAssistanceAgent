from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLATFORM=ROOT/'platform'
if str(PLATFORM) not in sys.path: sys.path.insert(0,str(PLATFORM))
from app.m11_mit_ocw_owner_decision_packet import MitOcwOwnerDecisionPacketError, validate_mit_ocw_owner_decision_packet
PACKET=ROOT/'data/manifests/m11-p0-mit-ocw-owner-decision-input-packet-v1.json'
MATERIALIZATION=ROOT/'data/manifests/m11-p0-mit-ocw-candidate-materialization-v1.json'
DIGEST=ROOT/'data/manifests/m11-p0-digest-evidence-v1.json'
RECEIPTS=ROOT/'data/manifests/m11-p0-acquisition-26-receipts-v1.json'
GATE0=ROOT/'data/manifests/m11-p0-formal-gate0-26-result-v1.json'
def main()->int:
    try:
        value=validate_mit_ocw_owner_decision_packet(json.loads(PACKET.read_text(encoding="utf-8")),materialization=json.loads(MATERIALIZATION.read_text(encoding="utf-8")),digest_evidence=json.loads(DIGEST.read_text(encoding="utf-8")),receipt_batch=json.loads(RECEIPTS.read_text(encoding="utf-8")),gate0_result=json.loads(GATE0.read_text(encoding="utf-8")))
    except (OSError,TypeError,json.JSONDecodeError,MitOcwOwnerDecisionPacketError) as exc:
        print(f'invalid: {exc}'); return 1
    print(f"valid: {value['asset_count']} MIT OCW owner decision-input records; 160 statuses remain PENDING; 18 candidate-validated/2 pipeline-rejected; authority not issued; historical Gate0 remains BLOCKED")
    return 0
if __name__=='__main__': raise SystemExit(main())
