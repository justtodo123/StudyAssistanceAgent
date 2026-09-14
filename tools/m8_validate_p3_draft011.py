import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'docs/plans/references'
A=R/'external-artifacts/text-audits/p3-audit-20260914-external-reviewer-01.json'
G=R/'external-gates/p3/p3-m8-active-execution-draft011-940ecec4-r01.json'
P2=R/'external-gates/p2/p2-m8-active-execution-draft011-940ecec4-r01.json'
RP=R/'external-artifacts/binding/sa-m8-active-draft011-20260914-940ecec4-repository.json'
P=R/'m8-active-execution-protocol-draft-0.11.md'
EXPECTED_IDS=['c-01','c-02','c-03','c-04','c-05','c-06','c-07','c-08','c-09','c-10','c-11','c-12','c-13','l-02']
bad=[]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_bytes())
def canonical(p): return p.read_bytes()==(json.dumps(load(p),ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def ck(name,value):
 print(('PASS ' if value else 'FAIL ')+name)
 if not value: bad.append(name)
for p in (A,G):
 ck(p.name+' canonical',canonical(p)); ck(p.name+' LF',p.read_bytes().endswith(b'\n') and b'\r' not in p.read_bytes())
a=load(A); g=load(G)['payload']; p2=load(P2)['payload']; rp=load(RP)['payload']
aref={'logical_name':A.relative_to(R).as_posix(),'schema_id':'sa.m8.text-audit.v1','sha256':sha(A)}
bref={'logical_name':RP.relative_to(R).as_posix(),'schema_id':'sa.m8.repository-binding.v1','sha256':sha(RP)}
ck('frozen protocol digest',sha(P)=='92e28958eb3e5d938e8646704fa22a297430bfede3d53f04ba941181c9b8d40d')
ck('frozen P2 digest',sha(P2)=='7b5efd98b844559d93f67203ee94906555a60e2cb9296d5ac7e5d8a9e73c66a8')
ck('frozen repository binding digest',sha(RP)=='91af7708a8d73ffe99e185d1cfec8efba8f09ad04768408f2e3bbfc7785bc602')
ck('audit schema/name',a['schema_id']=='sa.m8.text-audit.v1.payload' and a['logical_name']==A.relative_to(R).as_posix())
ck('audit rejected findings',a['payload']['verdict']=='REJECTED' and a['payload']['finding_ids']==EXPECTED_IDS)
ck('audit protocol identity',a['payload']['audited_protocol_path']==str(P.relative_to(ROOT)).replace('\\','/') and a['payload']['audited_protocol_sha256']==sha(P))
ck('audit binding identity',a['payload']['binding_ref']==bref and a['payload']['object_bindings']==[{'object_role':'protocol','logical_name':str(P.relative_to(ROOT)).replace('\\','/'),'sha256':sha(P)},{'object_role':'repository-binding','logical_name':bref['logical_name'],'sha256':bref['sha256']}])
ck('P3 rejection mapping',g['gate_id']=='P3' and g['decision']=='REJECTED' and g['allowed_next_action']=='stop')
ck('P3 actor mapping',g['actor']=={'name':'external-reviewer-01','role':'independent-reviewer'} and g['independence']['required'] is True and g['independence']['satisfied'] is True and g['scope']['operations']==['review'])
ck('P3 unique P2 predecessor',g['predecessors']==[{'expected_decision':'AUTHORIZED','expected_next_action':'request-p3','gate_id':'P2','record_id':p2['record_id'],'record_sha256':sha(P2)}])
ck('P3 payload refs',g['payload']=={'binding_ref':bref,'gate_id':'P3','text_audit_ref':aref})
ck('P3 exact read closure',g['scope']['read_refs']==[{'logical_name':P2.relative_to(R).as_posix(),'schema_id':'sa.m8.external-gate-record.v1','sha256':sha(P2)},bref,aref])
ck('three binding refs equal',g['payload']['binding_ref']==a['payload']['binding_ref']==p2['payload']['binding_ref'])
ck('no P4',not list((R/'external-gates/p4').glob('*draft011*.json')) if (R/'external-gates/p4').exists() else True)
print('ALL PASS' if not bad else f'{len(bad)} FAIL')
sys.exit(bool(bad))
