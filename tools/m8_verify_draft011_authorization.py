"""Verify the draft-0.11 authorization record without creating draft-0.11."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(r'D:\Git Demo\StudyAssistanceAgent'); R=ROOT/'docs/plans/references'; A=R/'m8-active-execution-protocol-draft-0.11-authorization-20260914.md'; P=R/'m8-draft011-revision-proposal-20260914.md'; bad=[]
def ck(s,c,d=''):
 print(('PASS ' if c else 'FAIL ')+s+((' :: '+d) if not c else '')); bad.append(s) if not c else None
b=A.read_bytes();t=b.decode('utf8');p=P.read_text(encoding='utf8')
ck('authorization exists',A.exists());ck('UTF-8 no BOM',not b.startswith(b'\xef\xbb\xbf'));ck('LF only',b'\r\n' not in b);ck('one terminal LF',b.endswith(b'\n') and not b.endswith(b'\n\n'));ck('owner decision quoted','批准 A+B+C 作为一次 draft-0.11 协议修订' in t);ck('authorization state closed','AUTHORIZED_FOR_PROTOCOL_REVISION / NOT_A_GATE / NOT_EXECUTION_AUTHORIZED' in t);ck('post-revision state only','DRAFTED / PENDING_INDEPENDENT_P0_REVIEW / UNBOUND / NOT_EXECUTION_AUTHORIZED' in t);ck('A mapping all 11 gates',all('| '+g+' |' in t for g in ['P0','P1','P2','P3','P4','P5','P6','P7','P7A','P8','P9']));ck('P0 drafting party field','drafting_party_name:ASCII[1,128]' in t);ck('P8 literal','admission_scope:"protocol-p8-decision-only"' in t);ck('text audit schema','schema_id:sa.m8.text-audit.v1' in t);ck('text audit logical name','external-artifacts/text-audits/<record_id>.json' in t);ck('package member','text_audit_member:PACKAGE_MEMBER_REF' in t);ck('9/19 preserved','`gate_members` 恰为 9' in t and '`input_members` 恰为 19' in t);ck('six boundaries',all('边界'+x in t for x in ['一','二','三','四','五','六']));ck('M8 blocked','M8: BLOCKED / NOT_STARTED' in t);ck('proposal remains proposal','PROPOSAL_ONLY / NOT_AN_AUTHORIZATION / NOT_A_REVISION' in p);p11=R/'m8-active-execution-protocol-draft-0.11.md'
if p11.exists():
 p11t=p11.read_text(encoding='utf8')
 ck('authorized draft011 protocol bytes may now exist','文档版本：`draft-0.11`' in p11t)
 ck('draft011 stops pending independent P0','不预置 P0/P3 结论' in p11t)
else:
 ck('pre-execution state permits no protocol bytes',True)
ck('no draft011 gates/artifacts',not any((R/'external-gates').rglob('*draft011*')) and not any((R/'external-artifacts').rglob('*draft011*')))
expected=[('m8-active-execution-protocol-draft-0.10.md','b5bc5088'),('external-artifacts/binding/sa-m8-active-draft010-20260914-5d10f2a1-repository.json','65cc34a0'),('external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1-r02.json','519d7837'),('external-gates/p2/p2-m8-active-execution-draft010-5d10f2a1-r01.json','1d758007')]
for rel,prefix in expected: ck('frozen digest '+Path(rel).name,hashlib.sha256((R/rel).read_bytes()).hexdigest().startswith(prefix))
records=list((R/'external-gates').rglob('*.json'))+list((R/'external-artifacts').rglob('*.json'));n=0
for q in records:
 try:
  x=json.loads(q.read_text(encoding='utf8'))['payload']
  if x.get('reviewed_protocol_sha256','').startswith('b5bc5088'): n+=1
 except Exception: pass
ck('seven exact draft010 bindings',n==7,str(n));ck('frozen objects absent from diff',subprocess.run(['git','diff','--quiet','--','docs/plans/references/m8-active-execution-protocol-draft-0.10.md','docs/plans/references/external-artifacts/binding','docs/plans/references/external-gates/p1','docs/plans/references/external-gates/p2'],cwd=ROOT).returncode==0);print('ALL PASS' if not bad else f'{len(bad)} FAIL');sys.exit(bool(bad))