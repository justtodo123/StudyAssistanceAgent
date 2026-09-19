# M8 Network-Acquisition Remediation Independent Review Request r01

record_type: M8_NETWORK_ACQUISITION_REMEDIATION_INDEPENDENT_SCOPE_REVIEW_REQUEST
cycle_id: m8-network-acquisition-authority-remediation-20260919-r01
cycle_type: NETWORK_ACQUISITION_CYCLE
candidate_version: remediation-candidate-20260919-r01
self_check_version: remediation-builder-self-check-20260919-r01
candidate: docs/plans/references/external-artifacts/m8-network-acquisition-authority-remediation-candidate-20260919-r01.json
builder_self_check: docs/plans/references/m8-network-acquisition-authority-remediation-builder-self-check-20260919-r01.md
review_prompt: docs/plans/references/m8-network-acquisition-authority-remediation-review-prompt-20260919-r01.md
reviewer_role: independent-scope-reviewer
reviewer_id: NOT_YET_DESIGNATED
independence_required: true
request_status: PENDING_INDEPENDENT_REVIEW
candidate_sha256: fadfbdf6e1e68cc76afd8ff467eee7a8528e876b93c81d23153c5e0e58649880
authority_digest: 7eda05780f6960823a17bae743790107a0a8a9ce4c37c51c2dc0b63f6906f600
payload_commit: RECORDED_AFTER_PAYLOAD_COMMIT
binding_record: docs/plans/references/external-artifacts/m8-network-acquisition-authority-remediation-git-binding-20260919-r01.json

## Required read-only checks

Reviewer must independently read bytes from Git and verify canonicalization, candidate schema, complete frozen source/runtime/downloader/write/provenance/limit policies, exact paths and versions, candidate SHA-256/blob, payload commit parent/tree/object size, and additive binding-record facts. Reviewer must confirm historical r02/r06 evidence remains unchanged and that the two-layer model has no self-referential claim.

Reviewer must reject any placeholder, unknown field, missing required field, non-numeric or unbounded limit, digest/path/version drift, stale binding, policy bypass, or authority escalation. Builder self-check is evidence of construction only and is not an independent review or Owner decision.

## Prohibitions

Do not access the network or PyPI; download/copy wheels; create a wheelhouse or preparation root; run pip, resolver or installer; create formal venv/identity; execute S1, S1-B, S2 or S3; select a backend; run a collector; modify any historical object; or fabricate acquisition evidence.

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
allowed_next_action: independent-read-only-remediation-review
