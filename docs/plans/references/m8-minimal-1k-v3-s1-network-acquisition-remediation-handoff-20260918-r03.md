# M8 Network Acquisition Observer Remediation Candidate — r03

- cycle: `m8-s1-network-acquisition-cycle-20260918-r01`
- remediation_of: `1b0e448687374db4cb6efd1404a09aed5e761c23`
- prior_review: `m8-minimal-1k-v3-s1-network-acquisition-independent-review-r02.md`
- status: `REMEDIATION_CANDIDATE_NOT_REVIEWED`
- acquisition: `NOT_AUTHORIZED`

## Remediations

1. Reject every path component containing parent-like `..` text, not only the exact component `..`.
2. Reject Windows alternate data stream syntax containing `:` in non-anchor components.
3. Reject trailing dot/space components.
4. Reject Windows reserved device names, including `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9` and `LPT1`–`LPT9`, including extension forms.
5. Add hermetic regression fixtures for the reported parent-like segment, alternate data stream, `NUL`, and `CON` forms.
6. Rebuild the observer authority artifact using canonical `sa-json-c14n-v1` bytes and bind the updated implementation/test digests.

## Verification

- observer test: `PASS: 21 network-acquisition observer fail-closed controls`
- r04 authority canonical byte comparison: `True`
- network access: none
- download/wheelhouse/resolver/installation/formal environment: none
- S1/S1-B/S2/S3/backend selection: not executed

This remediation candidate requires a new independent read-only review. It does not authorize acquisition or any M8 execution stage.
