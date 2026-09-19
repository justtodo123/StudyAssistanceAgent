# M8 Network-Acquisition Remediation Builder Self-Check r01

record_type: M8_NETWORK_ACQUISITION_REMEDIATION_BUILDER_SELF_CHECK
cycle_id: m8-network-acquisition-authority-remediation-20260919-r01
candidate_version: remediation-candidate-20260919-r01
self_check_version: remediation-builder-self-check-20260919-r01
candidate_path: docs/plans/references/external-artifacts/m8-network-acquisition-authority-remediation-candidate-20260919-r01.json
candidate_bytes: 12972
candidate_sha256: fadfbdf6e1e68cc76afd8ff467eee7a8528e876b93c81d23153c5e0e58649880
authority_digest: 7eda05780f6960823a17bae743790107a0a8a9ce4c37c51c2dc0b63f6906f600
candidate_git_blob: RECORDED_AFTER_PAYLOAD_COMMIT

result: BUILDER_CHECK_COMPLETE_INDEPENDENT_REVIEW_REQUIRED

checks:
  canonicalization: PASS — sa-json-c14n-v1, sorted keys, compact separators, UTF-8, no BOM, no CR, exactly one final LF
  candidate_schema: PASS — candidate v11 required root and nested fields are present; unknown-field policy is fail-closed
  source_policy: PASS — HTTPS official PyPI hosts, GET, TLS Schannel, proxy/auth/mirror/extra-index/certificate bypass denied
  runtime_policy: PASS — exact CPython identity, UTF-8 evidence, UTC timestamps, no bytecode/site/user-site
  downloader_policy: PASS — absolute curl identity, shell false, empty environment, bounded command contract
  write_boundary: PASS — root, path safety, allowlist, partial/atomic and existing-target policies are explicit
  provenance_schema: PASS — package/version/tag/source/index/downloader/TLS/time/status/artifact/dependency/failure/binding fields required
  acquisition_limits: PASS — numeric package, attempt, byte, file, timeout, retry, concurrency, redirect and resolver bounds
  execution_boundary: PASS — all execution and authorization flags remain false
  historical_immutability: PASS — prior r02/r06 evidence is referenced read-only and not edited or reused
  git_binding: PENDING — payload and additive binding records must be independently recomputed from Git objects

network_access: NOT_AUTHORIZED / NOT_PERFORMED
pypi_access: NOT_AUTHORIZED / NOT_PERFORMED
wheel_download: NOT_AUTHORIZED / NOT_PERFORMED
wheelhouse_creation: NOT_AUTHORIZED / NOT_PERFORMED
resolver: NOT_AUTHORIZED / NOT_PERFORMED
installation: NOT_AUTHORIZED / NOT_PERFORMED
formal_venv: NOT_AUTHORIZED / NOT_PERFORMED
formal_identity: NOT_AUTHORIZED / NOT_PERFORMED
s1_retry: NOT_AUTHORIZED / NOT_PERFORMED
s1_b: NOT_AUTHORIZED / NOT_PERFORMED
s2: NOT_AUTHORIZED / NOT_PERFORMED
s3: NOT_AUTHORIZED / NOT_PERFORMED
backend_selection: NOT_AUTHORIZED / NOT_PERFORMED
real_collector: NOT_AUTHORIZED / NOT_PERFORMED
preparation_root: NOT_CREATED
m8_status: BLOCKED / NOT_STARTED
allowed_next_action: create-independent-remediation-candidate
independent_reviewer_decision: NOT_ISSUED_BY_BUILDER
