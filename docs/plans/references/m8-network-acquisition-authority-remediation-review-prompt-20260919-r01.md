# M8 Network-Acquisition Remediation Independent Review Prompt r01

你是独立 scope Reviewer，不是 Builder 或 Owner。请对 remediation candidate 执行只读、fail-closed 审查。

cycle_id: m8-network-acquisition-authority-remediation-20260919-r01
candidate_version: remediation-candidate-20260919-r01
self_check_version: remediation-builder-self-check-20260919-r01
candidate: docs/plans/references/external-artifacts/m8-network-acquisition-authority-remediation-candidate-20260919-r01.json
builder_self_check: docs/plans/references/m8-network-acquisition-authority-remediation-builder-self-check-20260919-r01.md
review_request: docs/plans/references/m8-network-acquisition-authority-remediation-review-request-20260919-r01.md
candidate_sha256: fadfbdf6e1e68cc76afd8ff467eee7a8528e876b93c81d23153c5e0e58649880
authority_digest: 7eda05780f6960823a17bae743790107a0a8a9ce4c37c51c2dc0b63f6906f600
payload_commit: RECORDED_AFTER_PAYLOAD_COMMIT
binding_record: docs/plans/references/external-artifacts/m8-network-acquisition-authority-remediation-git-binding-20260919-r01.json

从 Git 实际对象重新计算每个声明文件的原始字节、size、SHA-256、Git blob，并核验 payload commit 的 parent、tree、commit object size 及 additive binding record。核验 candidate 是否严格满足 sa-json-c14n-v1；所有策略、limits、provenance 字段、路径、版本、digest 和 false authorization flags 是否闭合；核验 r02/r06 失败证据只读保留。任何占位符、漂移、遗漏、越界、隐式默认、非有限数字、重复/未知字段、能力夸大或自引用绑定均 fail closed。

禁止联网、访问 PyPI、下载 wheel、创建 wheelhouse/root、运行 resolver/installation、创建正式 venv/identity、执行 S1/S1-B/S2/S3、选择 backend、运行 collector、修改任何对象或伪造 acquisition evidence。

Reviewer 只能返回：REMEDIATION_CANDIDATE_READY_FOR_INDEPENDENT_REVIEW 或 REMEDIATION_CANDIDATE_BLOCKED。前者不等于通过、不等于 Owner 决策，也不授权任何执行。

acquisition_authorized: false
network_access_authorized: false
wheel_download_authorized: false
wheelhouse_creation_authorized: false
resolver_authorized: false
installation_authorized: false
formal_venv_authorized: false
formal_identity_authorized: false
real_collector_authorized: false
s1_retry_authorized: false
s1_b_authorized: false
s2_authorized: false
s3_authorized: false
backend_selection_authorized: false
m8_status: BLOCKED / NOT_STARTED
