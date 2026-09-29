"""Validate the owner-authorized IANA exact-three evidence result."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/'platform') not in sys.path: sys.path.insert(0,str(ROOT/'platform'))
from app.m11_iana_evidence_review import IanaEvidenceReviewError, validate_iana_evidence_review_result
M=ROOT/'data/manifests'
def load(name): return json.loads((M/name).read_text(encoding='utf-8'))
def main():
 try:
  a=load('m11-p0-iana-evidence-review-authority-v1.json')
  result=validate_iana_evidence_review_result(load('m11-p0-iana-evidence-review-result-v1.json'), application=load('m11-p0-iana-evidence-review-application-v1.json'), authority=a, packet=load('m11-p0-iana-evidence-closure-packet-v1.json'), census=load('m11-p0-iana-evidence-census-v1.json'), disposition=load('m11-p0-iana-owner-disposition-v1.json'), digest_evidence=load('m11-p0-digest-evidence-v1.json'), receipt_batch=load('m11-p0-acquisition-26-receipts-v1.json'), predecessor_slice=load('m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json'), formal_gate0_result=load('m11-p0-formal-gate0-26-result-v1.json'))
 except (OSError, KeyError, TypeError, json.JSONDecodeError, IanaEvidenceReviewError) as exc:
  print(f'invalid: {exc}'); return 1
 print(f"valid: {result['asset_count']} exact-three IANA assets; 24 evidence cells remain PENDING; XML UNRESOLVED; TXT FAIL_CLOSED; current heads unchanged")
 return 0
if __name__=='__main__': raise SystemExit(main())
