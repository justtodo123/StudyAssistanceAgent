import copy, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'docs/plans/references'
P=R/'m8-minimal-1k-dry-run-protocol-v1.md'
S=R/'schemas/m8-minimal-1k-artifacts-v1.schema.json'
bad=[]
def ck(name,ok):
 print(('PASS ' if ok else 'FAIL ')+name)
 if not ok: bad.append(name)
def canonical(o): return (json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def validate_envelope(o):
 return set(o)=={'canonicalization_id','logical_name','payload','schema_id','schema_version'} and o['canonicalization_id']=='sa-json-c14n-v1' and o['schema_version']==1 and o['schema_id'] in json.loads(S.read_text(encoding='utf-8'))['properties']['schema_id']['enum'] and isinstance(o['payload'],dict)
def valid_identity(o):
 p=o['payload']; required={'experiment_id','protocol_sha256','repository_commit','python_version','seed','chunk_count','dimension','dtype','normalization','backends','query_counts','top_k','measured_run_network','temporary_root_policy','dependency_versions','created_at','owner_actor','nonce'}
 return validate_envelope(o) and o['schema_id']=='sa.m8.minimal.experiment-identity.v1' and set(p)==required and p['chunk_count']==1000 and p['dimension']==512 and p['dtype']=='float32' and p['normalization']=='l2' and p['backends']==['sqlite-linear-exact','lancedb-embedded-exact-flat'] and p['top_k']==[1,3,5] and p['measured_run_network'] is False and re.fullmatch(r'[0-9a-f]{64}',p['nonce']) is not None
proto=P.read_bytes(); text=proto.decode('utf-8'); ck('protocol UTF8 LF',not proto.startswith(b'\xef\xbb\xbf') and b'\r' not in proto and proto.endswith(b'\n') and not proto.endswith(b'\n\n')); ck('protocol limited backends','不包含 Qdrant' in text and 'lancedb-embedded-exact-flat' in text and 'sqlite-linear-exact' in text); ck('protocol excludes 10K execution','禁止自动准备或运行 10K' in text); ck('protocol old-chain separation','不是 `draft-0.11` 的修订或 P4' in text); ck('schema canonical',S.read_bytes()==canonical(json.loads(S.read_bytes())))
base={'canonicalization_id':'sa-json-c14n-v1','logical_name':'external-artifacts/minimal/identity/example.json','payload':{'experiment_id':'example-1k','protocol_sha256':hashlib.sha256(proto).hexdigest(),'repository_commit':'0'*40,'python_version':'3.11.9','seed':20260914,'chunk_count':1000,'dimension':512,'dtype':'float32','normalization':'l2','backends':['sqlite-linear-exact','lancedb-embedded-exact-flat'],'query_counts':{'exact':25,'perturbed':25,'metadata-filter':25,'wrong-owner-no-hit':25},'top_k':[1,3,5],'measured_run_network':False,'temporary_root_policy':'isolated-disposable','dependency_versions':{'lancedb':'frozen-at-s1'},'created_at':'2026-09-14T00:00:00Z','owner_actor':'justtodo123','nonce':'0'*64},'schema_id':'sa.m8.minimal.experiment-identity.v1','schema_version':1}
ck('positive complete identity',valid_identity(base)); x=copy.deepcopy(base); x['payload']['chunk_count']=10000; ck('negative rejects 10K',not valid_identity(x)); x=copy.deepcopy(base); x['payload']['backends'].append('qdrant'); ck('negative rejects extra backend',not valid_identity(x)); x=copy.deepcopy(base); x['payload']['measured_run_network']=True; ck('negative rejects measured network',not valid_identity(x)); x=copy.deepcopy(base); x['payload']['future_gate']='preset'; ck('negative rejects extra field',not valid_identity(x)); ck('canonical roundtrip',json.loads(canonical(base))==base)
print('ALL PASS' if not bad else f'{len(bad)} FAIL');sys.exit(bool(bad))
