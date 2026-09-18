# M8 Network Acquisition Observer Remediation Candidate — r04

- cycle: `m8-s1-network-acquisition-cycle-20260918-r01`
- remediation_of: `97f8c94074635a123b1f11ebf3cc1751d7c9febf`
- prior_review: `m8-minimal-1k-v3-s1-network-acquisition-independent-review-r03.md`
- status: `REMEDIATION_CANDIDATE_NOT_REVIEWED`
- acquisition: `NOT_AUTHORIZED`

## Remediation

The write observer now enforces the declared persistent relative allowlist. It accepts only:

- `authority.json`
- `inventory.json`
- `provenance.json`
- the four declared `events/*.jsonl` paths
- `wheels/*.whl`
- `wheels/*.whl.partial`

Unknown paths such as `random.txt`, `events/random.bin`, `wheels/not-a-wheel.txt`, and `secret/unknown.json` fail closed with `M8ACQ_E017_FILE_TYPE_DENIED`.

The authority candidate was regenerated as canonical `sa-json-c14n-v1` bytes and implementation/test bindings were refreshed.

## Verification

- observer test: `PASS: 21 network-acquisition observer fail-closed controls`
- network access: none
- download/wheelhouse/resolver/installation/formal environment: none
- S1/S1-B/S2/S3/backend selection: not executed

This remediation candidate requires a new independent read-only review. It does not authorize acquisition or any M8 execution stage.
