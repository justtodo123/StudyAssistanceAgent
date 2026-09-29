from __future__ import annotations
import copy, json
from pathlib import Path
import pytest
from app.m11_mit_ocw_owner_decision_packet import MitOcwOwnerDecisionPacketError, validate_mit_ocw_owner_decision_packet
pytestmark=pytest.mark.m11
ROOT=Path(__file__).resolve().parents[2]
FILES={k:ROOT/f'data/manifests/{v}' for k,v in {'packet':'m11-p0-mit-ocw-owner-decision-input-packet-v1.json','materialization':'m11-p0-mit-ocw-candidate-materialization-v1.json','digest':'m11-p0-digest-evidence-v1.json','receipts':'m11-p0-acquisition-26-receipts-v1.json','gate0':'m11-p0-formal-gate0-26-result-v1.json'}.items()}
def load(k): return json.loads(FILES[k].read_text(encoding='utf-8'))
def validate(p=None, **deps):
    args={k:load(k) for k in ('materialization','digest','receipts','gate0')}; args.update(deps)
    return validate_mit_ocw_owner_decision_packet(load('packet') if p is None else p, materialization=args['materialization'], digest_evidence=args['digest'], receipt_batch=args['receipts'], gate0_result=args['gate0'])
def test_exact_twenty_partition_and_all_pending():
    p=validate(); assert p['asset_count']==20; assert len(p['batch_records'])==20; assert p['validated_candidate_count']==18; assert p['pipeline_rejected_count']==2
    assert p['pipeline_rejections']=={'digital_answers':{'status':'REJECTED','reason':'SOURCE_PARSE_FAILED'},'information_worksheet':{'status':'REJECTED','reason':'INVALID_CANDIDATE_INPUT'}}
    assert sum(len(v) for v in p['proposed_statuses'].values())==160
    assert all(s=='PENDING' for v in p['proposed_statuses'].values() for s in v.values())
def test_packet_is_nonexecuting_and_historical_gate0_only():
    p=validate(); assert p['metadata_only'] is True and p['authority_issued'] is False; assert p['formal_gate0_executed'] is False; assert p['historical_gate0_reference']['status']=='BLOCKED'
@pytest.mark.parametrize('mutation',[
 lambda p:p.__setitem__('authority_issued',True), lambda p:p.__setitem__('publication_authorized',True), lambda p:p.__setitem__('candidate_approval_granted',True), lambda p:p['proposed_statuses']['digital_answers'].__setitem__('parser','FAILED'), lambda p:p['batch_records'].pop(), lambda p:p['batch_records'][0].__setitem__('receipt_digest','0'*64), lambda p:p['pipeline_rejections']['digital_answers'].__setitem__('reason','HUMAN_REVIEW_REJECT'), lambda p:p.__setitem__('owner_verdict','ACCEPT')])
def test_mutations_fail_closed(mutation):
    p=copy.deepcopy(load('packet')); mutation(p)
    with pytest.raises(MitOcwOwnerDecisionPacketError): validate(p)
@pytest.mark.parametrize('dependency', ['materialization','digest','receipts','gate0'])
def test_dependency_mutations_fail_closed(dependency):
    p=load('packet'); deps={k:load(k) for k in ('materialization','digest','receipts','gate0')}
    if dependency=='materialization': deps[dependency]['candidate_chunk_count']+=1
    elif dependency=='digest': deps[dependency]['assets'][0]['sha256']='f'*64
    elif dependency=='receipts': deps[dependency]['receipts'][0]['revision']='f'*64
    else: deps[dependency]['status']='READY'
    with pytest.raises(MitOcwOwnerDecisionPacketError): validate(p,**deps)
def test_detached_copy_and_no_host_paths():
    before=FILES['packet'].read_bytes(); p=validate(); p['proposed_statuses']['beta_answers']['license']='changed'; assert load('packet')['proposed_statuses']['beta_answers']['license']=='PENDING'; assert FILES['packet'].read_bytes()==before
    text=FILES['packet'].read_text(encoding="utf-8"); assert 'D:/' not in text and 'D:\\' not in text and '"body"' not in text
