"""Verify the factual P2 measurement materials without issuing P2."""
import hashlib, json, subprocess, sys
from pathlib import Path
R=Path(r"D:\Git Demo\StudyAssistanceAgent\docs\plans\references")
M=R/'m8-draft010-p2-materials-20260914.md'; P=R/'m8-active-execution-protocol-draft-0.10.md'; I=R/'external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1.json'; P1=R/'external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1.json'
bad=[]
def ck(s,c,d=''):
 print(('PASS ' if c else 'FAIL ')+s+((' :: '+d) if not c else '')); bad.append(s) if not c else None
t=M.read_text(encoding='utf8'); p=P.read_bytes(); ih=hashlib.sha256(I.read_bytes()).hexdigest(); r=json.loads(P1.read_text(encoding='utf8'))['payload']
ck('材料存在',M.exists()); ck('材料状态为 P2 blocked 且未给出通过结论', '状态：`P2_BLOCKED_ON_WORKSPACE_VOLUME / FINDING_RECORDED / NOT_AUTHORIZED`' in t and '不得把本材料或这次实测改写为 `P2 AUTHORIZED`、`P2 PASS`' in t); ck('材料不授权', '不产生 `repository-binding`' in t); ck('协议摘要正确', hashlib.sha256(p).hexdigest().startswith('b5bc5088')); ck('identity 摘要引用正确', r['payload']['identity_ref']['sha256']==ih); ck('P1 仅 identity 操作',r['scope']['operations']==['identity']); ck('目标为 D 工作区','D:/Git Demo/StudyAssistanceAgent' in t); ck('D 目标失败事实',"directory exposes unexpected streams: [':sguard:$DATA']" in t); ck('C 对照通过事实','C:/Users/Public' in t and '结果退出码 `0`' in t); ck('未生成 P2 binding','未生成 P2 binding record' in t); ck('不把 C 对照作为绕过','不能绕过当前工作区目标卷的阻断' in t); print('ALL PASS' if not bad else f'{len(bad)} FAIL'); sys.exit(bool(bad))
