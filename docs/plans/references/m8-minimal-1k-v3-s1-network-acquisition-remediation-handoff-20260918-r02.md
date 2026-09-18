# M8 Network Acquisition Observer Remediation Candidate — r03

- cycle: `m8-s1-network-acquisition-cycle-20260918-r01`
- remediation_of: `91b3032`
- prior_review: `m8-minimal-1k-v3-s1-network-acquisition-independent-review-20260918-r01.md`
- status: `REMEDIATION_CANDIDATE_NOT_REVIEWED`
- acquisition: `NOT_AUTHORIZED`

## Remediations

1. Rebuilt observer authority JSON as canonical `sa-json-c14n-v1` bytes: sorted keys, compact separators, UTF-8, no BOM, no CR, exactly one final LF.
2. Added fail-closed rejection for any lexical `..` path segment before preparation-root checks.
3. Added a hermetic regression fixture covering traversal from the preparation root to an outside path.

## Verification

- observer test: `PASS: 21 network-acquisition observer fail-closed controls`
- observer authority canonical byte comparison: `True`
- network access: none
- download/wheelhouse/resolver/installation/formal environment: none
- S1/S1-B/S2/S3/backend selection: not executed

## New candidate materials

- `docs/plans/references/external-artifacts/m8-minimal-1k-v3-s1-network-acquisition-observer-authority-20260918-r03.json`
- updated observer implementation and hermetic test

This remediation candidate requires a new independent read-only review. It does not authorize acquisition or any M8 execution stage.
