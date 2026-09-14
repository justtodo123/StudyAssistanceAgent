"""Validate draft-0.11 A+B+C text and fail-closed acceptance matrix.

The validator supports pre-review, post-P0 and post-P1 lifecycle states. Positive
and negative cases exercise closed predicates implemented below from the protocol
text; frozen unrelated sections are compared to draft-0.10 byte-for-byte.
"""
import hashlib,re,sys
from pathlib import Path
R=Path(r'D:\Git Demo\StudyAssistanceAgent\docs\plans\references'); P10=R/'m8-active-execution-protocol-draft-0.10.md'; P11=R/'m8-active-execution-protocol-draft-0.11.md'; t10=P10.read_text(encoding='utf8'); t=P11.read_text(encoding='utf8'); bad=[]
def ck(s,c,d=''): print(('PASS ' if c else 'FAIL ')+s+((' :: '+d) if not c else '')); bad.append(s) if not c else None
# A closed mapping
MAP={'P0':('independent-reviewer',True,True,['review']),'P1':('owner',False,False,['identity']),'P2':('owner',False,False,['binding']),'P3':('independent-reviewer',True,True,['review']),'P4':('owner',False,False,['acquire','prepare']),'P5':('independent-reviewer',True,True,['review']),'P6':('owner',False,False,['execute']),'P7':('independent-verifier',True,True,['verify']),'P7A':('owner',False,False,['cleanup','publish']),'P8':('owner',False,False,['admit']),'P9':('owner',False,False,['select'])}
def gate_ok(g,role,req,sat,ops): return MAP.get(g)==(role,req,sat,ops)
for g,v in MAP.items(): ck('A positive '+g,gate_ok(g,*v))
ck('A negative wrong role',not gate_ok('P3','owner',True,True,['review']));ck('A negative flag mismatch',not gate_ok('P7','independent-verifier',True,False,['verify']));ck('A negative wrong ops',not gate_ok('P4','owner',False,False,['prepare','acquire']));ck('A mapping present in text',all(g+'=' in t for g in ['P0/P3/P5','P7','P1','P2','P4','P6','P7A','P8','P9']));ck('A P0 drafting field','drafting_party_name:ASCII[1,128]' in t)
def independent_ok(g,actor,drafter,owners): return actor!=drafter if g=='P0' else g in ('P3','P5','P7') and actor not in owners
ck('A nonoverlap positive P0',independent_ok('P0','reviewer-a','drafter-a',[]));ck('A nonoverlap negative P0',not independent_ok('P0','same','same',[]));ck('A nonoverlap positive P3',independent_ok('P3','reviewer-a','drafter-a',['owner-a']));ck('A nonoverlap negative owner',not independent_ok('P3','owner-a','drafter-a',['owner-a']))
# B closed literal
def p8_ok(scope,ops,writes): return scope=='protocol-p8-decision-only' and ops==['admit'] and writes==[]
ck('B positive literal',p8_ok('protocol-p8-decision-only',['admit'],[]));ck('B negative other scope',not p8_ok('m8-project-admission',['admit'],[]));ck('B negative write target',not p8_ok('protocol-p8-decision-only',['admit'],['x']));ck('B old free text absent','admission_scope:UTF8[1,1024]' not in t);ck('B literal in P8 row','admission_scope:"protocol-p8-decision-only"' in t)
# C artifact predicate
def audit_ok(a):
 try:
  roles=[x['object_role'] for x in a['object_bindings']]
  return set(a)=={'audit_id','audited_protocol_path','audited_protocol_sha256','binding_ref','verdict','finding_ids','object_bindings'} and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,127}',a['audit_id']) and roles==['protocol','repository-binding'] and a['binding_ref']['schema_id']=='sa.m8.repository-binding.v1' and ((a['verdict']=='VERIFIED' and a['finding_ids']==[]) or (a['verdict']=='REJECTED' and len(a['finding_ids'])>0))
 except Exception:return False
base={'audit_id':'audit-one','audited_protocol_path':'docs/p.md','audited_protocol_sha256':'0'*64,'binding_ref':{'schema_id':'sa.m8.repository-binding.v1'},'verdict':'VERIFIED','finding_ids':[],'object_bindings':[{'object_role':'protocol'},{'object_role':'repository-binding'}]}
ck('C positive verified',audit_ok(base));q={**base,'verdict':'REJECTED','finding_ids':['f1']};ck('C positive rejected',audit_ok(q));q={**base,'verdict':'VERIFIED','finding_ids':['f1']};ck('C negative verified findings',not audit_ok(q));q={**base,'object_bindings':[{'object_role':'repository-binding'},{'object_role':'protocol'}]};ck('C negative role order',not audit_ok(q));q={**base,'binding_ref':{'schema_id':'wrong'}};ck('C negative binding schema',not audit_ok(q));ck('C schema and logical binding in text','sa.m8.text-audit.v1.payload' in t and 'external-artifacts/text-audits/<audit_id>.json' in t);ck('C P3 exact three refs','read_refs` must contain exactly three REFs' in t);ck('C verdict mappings','VERIFIED/request-p4' in t and 'REJECTED/stop' in t);ck('C package scalar','text_audit_member:PACKAGE_MEMBER_REF' in t);ck('C 9/19 preserved','`gate_members` 仍恰为 9' in t and '`input_members` 仍恰为 19' in t)
# frozen anchored definitions
def line(t,needle): return next(x for x in t.splitlines() if needle in x)
for name,needle in [('ID','- `ID`：'),('SCHEMA_ID','- `SCHEMA_ID`：'),('TECH_GATE_ID','- `TECH_GATE_ID`：'),('order=value','- `order=value`：'),('order=key','- `order=key('),('binding allowlist','- `BINDING_STREAM_ALLOWLIST`：')]: ck('frozen '+name,line(t,needle)==line(t10,needle))
def block(text,start,end): return text.split(start,1)[1].split(end,1)[0]
ck('frozen status map section',block(t,'`sa.m8.status-map.v1.payload` exact fields：','## 9. Lifecycle')==block(t10,'`sa.m8.status-map.v1.payload` exact fields：','## 9. Lifecycle'))
ck('frozen gate order','P0→P1→P2→P3→P4→P5→P6→P7→P7A→P8→P9' in t)
ck('version header draft011','文档版本：`draft-0.11`' in t);b=P11.read_bytes();ck('LF only',b'\r\n' not in b);ck('one terminal LF',b.endswith(b'\n') and not b.endswith(b'\n\n'));gates=list((R/'external-gates').rglob('*draft011*.json')); artifacts=list((R/'external-artifacts').rglob('*draft011*'))
p0=[q for q in gates if '/p0/' in q.as_posix()];p1=[q for q in gates if '/p1/' in q.as_posix()];later=[q for q in gates if q not in p0+p1]
ck('successor gate lifecycle',len(p0)<=1 and len(p1)<=1 and not later and (not p1 or len(p0)==1),str([q.as_posix() for q in gates]))
ck('successor artifact lifecycle',(not artifacts and not p1) or (len(artifacts)==1 and len(p1)==1 and '/identity/' in artifacts[0].as_posix()),str([q.as_posix() for q in artifacts]))
print('ALL PASS' if not bad else f'{len(bad)} FAIL');sys.exit(bool(bad))