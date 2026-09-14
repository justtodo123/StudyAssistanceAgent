"""Validate the draft-0.10 P1 and the five LF-recomputed draft-0.9 records.

Checks only structural facts: canonical JSON, current protocol digests, unique
parallel filenames, predecessor/reference hashes, and preservation of old bytes.
It does not authorize P2 or judge any technical outcome.
"""
import hashlib, json, subprocess, sys
from pathlib import Path
R=Path(r"D:\Git Demo\StudyAssistanceAgent\docs\plans\references")
ROOT=R.parent.parent.parent
D09='6ccebc477dd54df4415998c8c03ffff3215d523cf2a42af128a8ff6a36e244a9'
D10='b5bc5088486079971eba28efe5cd2d7ed90c73a1359a87d9bca4722c473caa39'
bad=[]
def ck(s,c,d=''):
 print(('PASS ' if c else 'FAIL ')+s+((' :: '+d) if not c else '')); bad.append(s) if not c else None
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(p):
 b=p.read_bytes(); return b== (json.dumps(load(p),ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def gitbytes(rel): return subprocess.run(['git','cat-file','-p','HEAD:'+rel],cwd=ROOT,capture_output=True).stdout
print('=== canonical / historical bytes ===')
for p in [R/'external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json',R/'external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json',R/'external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json',R/'external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json',R/'external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json']:
 rel=p.relative_to(ROOT).as_posix(); ck('旧记录 '+p.name+' 字节未变',p.read_bytes()==gitbytes(rel)); ck('旧记录 '+p.name+' canonical',canon(p))
print('=== recomputed draft-0.9 chain ===')
p0a=R/'external-gates/p0/p0-m8-active-execution-draft09-20260913-r03-rejected.json'; p0b=R/'external-gates/p0/p0-m8-active-execution-draft09-20260913-r03-accepted.json'; iid=R/'external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543-r03.json'; p1a=R/'external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r03.json'
for p in [p0a,p0b,iid,p1a]: ck(p.name+' canonical',canon(p)); ck(p.name+' LF digest',load(p)['payload'].get('reviewed_protocol_sha256')==D09 if 'payload' in load(p) and 'reviewed_protocol_sha256' in load(p)['payload'] else load(p)['payload']['reviewed_protocol_sha256']==D09)
for p in [p0a,p0b]: ck(p.name+' logical_name matches',load(p)['logical_name']=='external-gates/p0/'+p.name); ck(p.name+' unique record_id',load(p)['payload']['record_id']==p.stem)
for p0 in [p0a,p0b]:
 x=load(p0); assert x['payload']['record_id'] in ('p0-m8-active-execution-draft09-20260913-r03-rejected','p0-m8-active-execution-draft09-20260913-r03-accepted')
px=load(p1a)['payload']; ck('recomputed P1 predecessor references accepted P0',px['predecessors'][0]['record_id']==load(p0b)['payload']['record_id'] and px['predecessors'][0]['record_sha256']==sha(p0b)); ck('recomputed P1 references recomputed identity',px['payload']['identity_ref']['sha256']==sha(iid)); ck('recomputed identity path matches',px['payload']['identity_ref']['logical_name']=='external-artifacts/identity/'+iid.name)
print('=== draft-0.10 P1 ===')
p10=R/'external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1.json'; i10=R/'external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1.json'; p0=R/'external-gates/p0/p0-m8-active-execution-draft010-20260913-r01.json'; x=load(p10)['payload']; y=load(i10)['payload']; ck('P1 canonical',canon(p10)); ck('P1 AUTHORIZED/request-p2',x['decision']=='AUTHORIZED' and x['allowed_next_action']=='request-p2'); ck('P1 owner',x['actor']=={'name':'justtodo123','role':'owner'}); ck('P1 protocol digest',x['reviewed_protocol_sha256']==D10); ck('P1 predecessor P0 hash',x['predecessors'][0]['record_sha256']==sha(p0)); ck('P1 identity hash',x['payload']['identity_ref']['sha256']==sha(i10)); ck('identity protocol digest',y['reviewed_protocol_sha256']==D10); ck('identity path matches',x['payload']['identity_ref']['logical_name']=='external-artifacts/identity/'+i10.name); ck('P1 only identity operation',x['scope']['operations']==['identity']); ck('P1 no network/write',x['scope']['allow_network'] is False and x['scope']['allow_production_write'] is False)
print('=== result ==='); print('ALL PASS' if not bad else f'{len(bad)} FAIL'); sys.exit(bool(bad))
