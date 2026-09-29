from __future__ import annotations
import copy, json
from pathlib import Path
import pytest
from app.m11_iana_evidence_review import IanaEvidenceReviewError, validate_iana_evidence_review_result
ROOT=Path(__file__).resolve().parents[2]; M=ROOT/'data/manifests'
def load(n): return json.loads((M/n).read_text(encoding='utf-8'))
def args():
 return dict(result=load('m11-p0-iana-evidence-review-result-v1.json'), application=load('m11-p0-iana-evidence-review-application-v1.json'), authority=load('m11-p0-iana-evidence-review-authority-v1.json'), packet=load('m11-p0-iana-evidence-closure-packet-v1.json'), census=load('m11-p0-iana-evidence-census-v1.json'), disposition=load('m11-p0-iana-owner-disposition-v1.json'), digest_evidence=load('m11-p0-digest-evidence-v1.json'), receipt_batch=load('m11-p0-acquisition-26-receipts-v1.json'), predecessor_slice=load('m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json'), formal_gate0_result=load('m11-p0-formal-gate0-26-result-v1.json'))
def validate(a): return validate_iana_evidence_review_result(a['result'], application=a['application'], authority=a['authority'], packet=a['packet'], census=a['census'], disposition=a['disposition'], digest_evidence=a['digest_evidence'], receipt_batch=a['receipt_batch'], predecessor_slice=a['predecessor_slice'], formal_gate0_result=a['formal_gate0_result'])
def test_exact_three_result_is_valid():
 r=validate(args()); assert r['asset_count']==3 and r['pending_cell_count']==24; assert r['current_heads']['iana']=='3 DEFER'
 assert all(c['status']=='PENDING' for x in r['records'] for c in x['evidence'].values())
@pytest.mark.parametrize('mutation', [lambda a:a['result']['records'][1]['evidence']['schema'].__setitem__('status','VERIFIED'),lambda a:a['result'].__setitem__('current_heads',{'rfc':'3 ACCEPT','iana':'3 ACCEPT','mit_ocw':'20 DEFER'}),lambda a:a['result'].__setitem__('publication_authorized',True),lambda a:a['authority'].__setitem__('operation','gate0'),lambda a:a['application'].__setitem__('asset_count',4),lambda a:a['result']['records'][0].__setitem__('candidate_digest','f'*64),lambda a:a['disposition']['records'][1].__setitem__('xml_conflict_status','RESOLVED'),lambda a:a['predecessor_slice']['records'][0].__setitem__('review_id','forged-predecessor'),lambda a:a['formal_gate0_result'].__setitem__('status','PASS')])
def test_mutations_fail_closed(mutation):
 a=args(); mutation(a)
 with pytest.raises(IanaEvidenceReviewError): validate(a)
def test_parent_inputs_and_result_are_immutable():
 a=args(); before=copy.deepcopy(a); out=validate(a); out['records'][0]['evidence']['schema']['status']='VERIFIED'; assert a==before


def test_predecessor_seals_are_immutable():
    a = args()
    forged = copy.deepcopy(a["predecessor_slice"])
    forged["records"][0]["comment"] = "same identity, changed content"
    a["predecessor_slice"] = forged
    with pytest.raises(IanaEvidenceReviewError): validate(a)

@pytest.mark.parametrize('signed_at', ['2026-09-29T00:59:59Z', '2026-10-13T01:00:00Z'])
def test_result_rejects_authority_window_boundaries(signed_at):
 a=args(); a['result']['signed_at']=signed_at
 with pytest.raises(IanaEvidenceReviewError, match='IANA_REVIEW_RESULT_SIGNER_INVALID'): validate(a)

def test_result_accepts_issued_at_boundary():
 a=args(); a['result']['signed_at']=a['authority']['issued_at']
 assert validate(a)['signed_at']==a['authority']['issued_at']


@pytest.mark.parametrize("target, value", [
    (("application", "submitted_at"), "2026-09-29T00:59:59Z"),
    (("application", "submitted_at"), "2026-10-13T01:00:00Z"),
    (("result", "signed_at"), "2026-09-29T00:59:59Z"),
    (("result", "signed_at"), "2026-10-13T01:00:00Z"),
])
def test_application_and_result_timestamps_must_be_within_authority(target, value):
    a = args(); a[target[0]][target[1]] = value
    with pytest.raises(IanaEvidenceReviewError): validate(a)


def test_authority_issuer_and_recursive_privacy_are_bound():
    a = args(); a["authority"]["issued_by"] = "other-owner"
    with pytest.raises(IanaEvidenceReviewError): validate(a)
    for container, mutation in (
        ("application", lambda payload: payload.__setitem__("reviewer_comment", "forbidden")),
        ("application", lambda payload: payload.__setitem__("packet_manifest", r"C:\\host\\secret.json")),
        ("result", lambda payload: payload["records"][0]["evidence"]["schema"]["refs"].append(r"\\\\host\\secret")),
        ("result", lambda payload: payload["records"][0]["evidence"]["schema"].__setitem__("comment", "/home/owner/secret")),
    ):
        a = args(); mutation(a[container])
        with pytest.raises(IanaEvidenceReviewError): validate(a)
