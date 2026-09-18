# M8 S1 Network Acquisition Observer Builder Adversarial Self-Check — 2026-09-19 r03

- record_type: `M8_BUILDER_ADVERSARIAL_SELF_CHECK`
- builder_role: `builder`
- cycle_id: `m8-s1-network-acquisition-cycle-20260918-r01`
- candidate: `m8-minimal-1k-v3-s1-network-acquisition-observer-authority-20260918-r08.json`
- status: `SELF_CHECK_INCOMPLETE_FAILED_CLOSED`
- acquisition_status: `NOT_AUTHORIZED`
- m8: `BLOCKED_NOT_STARTED`

> This is a Builder record, not an independent Reviewer decision. It cannot issue
> `ENVIRONMENT_AUTHORITY_REVIEW_ACCEPTED` or authorize acquisition or M8 execution.

## Matrix

| check_id | status | evidence |
| --- | --- | --- |
| canonical-json | PASS | Candidate and validator use compact sorted UTF-8 JSON with exactly one final LF; NaN, Infinity, and unpaired surrogates are rejected. |
| sha-256 | PASS | r08 binds observer `841dc1e98d09c673045b96c0949930b7cca1829db758598c6d82706178869c1a`; test `c300095adee7001986cab5474b1afab211eb03541594201d086a8fdb97c2e78c`. |
| git-blob-oid | PASS | r08 binds observer `97c005710b62a76221cc8669bd399254398967ce`; test `1a859ee1355d4d76ffc52fe5cbad281c9ee47a6a`. |
| observer-implementation-binding | PASS | Additive r08 binds LF-only working-tree source bytes and retains the declared-event-only role. |
| test-implementation-binding | PASS | Additive r08 binds LF-only hermetic test bytes. |
| network-policy | PASS | Closed fields; HTTPS GET; initial `pypi.org`; redirects `pypi.org`/`files.pythonhosted.org`; TLS required; proxy/authentication/certificate bypass denied; redirect limit 3; final URL is bound to the chain. |
| runtime-authority | PASS | No runtime or acquisition authority was expanded. |
| write-root | PASS | Only lexical paths under the preparation root pass declared-event validation. |
| forbidden-roots | PASS | Repository, external source directory, and pip cache roots fail closed. |
| windows-special-paths | PASS | Parent-like components, ADS, reserved names, `CONIN$`/`CONOUT$`, forbidden characters including `(`, control characters, trailing dot/space, UNC, alternate drive, mixed/duplicate separators, and overlong components fail closed. |
| persistent-relative-allowlist | PASS | Only seven evidence files and direct `wheels/*.whl` or `wheels/*.whl.partial` paths pass. |
| kind-path-consistency | PASS | Evidence, wheel, and partial kinds match only their declared path classes. |
| file-size-limits | PASS | Strict non-boolean integer and frozen maximum are enforced. |
| total-size-limits | PASS | Aggregate size is bounded and cannot be less than file size. |
| file-count-limits | PASS | Strict count range `1..256` is enforced. |
| redaction-policy | PASS | SHA-256 binds bytes; decoded attested content is scanned, including `Authorization=`; supplied text must match decoded bytes. |
| process-policy | PASS | Exact string curl path; one strict integer process; shell disabled. |
| stable-error-codes | PASS | Registry contains exactly 21 unique stable codes. |
| execution-boundary | PASS | No network, PyPI, download/copy, wheelhouse, formal environment, pip, resolver, installation, dependency import, M8 stage, database, backend, or external-source access occurred. |
| historical-record-immutability | PASS | r08 and this record are additive; historical candidates, reviews, handoffs, failures, freezes, and decisions were not edited. |
| normal-hermetic-test | PASS | Required PASS line emitted. |
| optimized-hermetic-test | PASS | Required PASS line emitted under `python -O` without assertion-dependent correctness. |
| isolated-compilation | PASS | Both modules compile under isolated Python. |
| diff-whitespace | PASS | `.gitattributes` now pins both digest-bound Python sources to LF; `git ls-files --eol` reports `i/lf w/lf`, and strict `git diff --check` passes. |
| real-collector-conformance | BLOCKED | Candidate validates declared events only; it does not implement real network/write/process collectors, lifecycle ledgers, coverage receipts, Windows no-follow containment, rename-race handling, process identity/PID reuse protection, or complete evidence sealing. |

## Disposition

The implementation-level declared-event matrix passes after the additive LF-bound r08 remediation,
but the candidate remains blocked as the full S1 observer authority because real-collector
conformance is absent. This Builder record does not authorize acquisition or M8 execution and
is not an independent Reviewer decision.

- s1_b: `NOT_AUTHORIZED`
- s1_retry: `NOT_AUTHORIZED`
- s2: `NOT_AUTHORIZED`
- s3: `NOT_AUTHORIZED`
- backend_selection: `NOT_AUTHORIZED`
- independent_review_performed: `false`
- allowed_next_action: `independent-read-only-scope-review-or-separate-real-collector-remediation`

`BUILDER_ADVERSARIAL_SELF_CHECK_FAILED_CLOSED`
