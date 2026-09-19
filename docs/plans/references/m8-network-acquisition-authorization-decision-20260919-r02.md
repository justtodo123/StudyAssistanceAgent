# M8 Network-Acquisition Authorization Decision r02

record_type: M8_NETWORK_ACQUISITION_AUTHORIZATION_DECISION
authorization_decision_id: m8-network-acquisition-authorization-decision-20260919-r02
decision: NETWORK_ACQUISITION_AUTHORIZATION_REJECTED_FAILED_CLOSED
decision_timestamp_utc: 2026-09-19T09:02:24Z
owner_identity: StudyAssistanceAgent Network-Acquisition Authorization Owner
owner_role: network-acquisition-authorization-owner
cycle_id: m8-network-acquisition-authority-remediation-20260919-r02

## Decision basis

The independently persisted Scope Review record exists at
`docs/plans/references/m8-network-acquisition-authority-remediation-independent-review-20260919-r02.md`.
It records `NETWORK_ACQUISITION_SCOPE_APPROVED`, no unresolved Scope Review blocker, and no execution.
This authorization decision is independent of the Builder self-check and Scope Review conclusion.

The authorization object is locked to the reviewed fixed-object chain below. Branch head and worktree
state are not authorization inputs.

## Exact reviewed-object binding

- dispatch manifest path: `docs/plans/references/external-artifacts/m8-network-acquisition-authority-remediation-review-dispatch-20260919-r02.json`
- dispatch manifest bytes: `5149`
- dispatch manifest SHA-256: `47202952dc611bb5b5dd9a0f2210891defe7ad8b56fdfe6c1eea3f0e17d6faf6`
- dispatch manifest Git blob: `05988762b8458918b077b5450c847775785c5bc5`
- dispatch commit: `7c2a231b42c940cb99e830f083ccd087ee42538d`
- dispatch parent: `ec6de9390da8801f4949d43d24f3449e8506cc67`
- dispatch tree: `48b65e335ce1437ae5fef3e97143cdac38c6aa03`
- dispatch commit object size: `314`
- dispatch-material commit: `ec6de9390da8801f4949d43d24f3449e8506cc67`
- dispatch-material parent: `0153653244a5a6aafc804715b094229fd617a9af`
- dispatch-material tree: `cf93bdd97fcf606d1d429aa03d561a2ccf12fe40`
- dispatch-material commit object size: `309`
- exact review-target commit: `20d60cd06733c2f42a2ac36434a9d1a41e2eef8d`
- review-target parent / candidate-binding commit: `68b568d097808200ccf55c5904906882f0e1d8f8`
- review-target tree: `8e49fc6c540b9b851c616703f4a290f7e54ecf57`
- review-target commit object size: `316`
- payload commit: `44e6cff5535f37405b277a893bc59e9bbb4781c9`
- payload-binding commit: `bbb131c8e0816c3fec28e0e49787ea60f8101724`
- candidate-envelope commit: `1e4beeeec0690a4c72868625556af68913410bd7`
- candidate-binding commit: `68b568d097808200ccf55c5904906882f0e1d8f8`
- candidate digest semantics: `authority-payload-sha256`
- candidate digest: `f2992204cff95bf56c85601f44cf47ec03f0655aa71fe4690f199fd864da8a1e`
- candidate payload Git blob: `a5b0e2f92bc16092738f57bf2329394d1694fe90`
- candidate-envelope digest: `0ebe9bf8a335e3f6bcde7e6791311370e2104cd80361de3dda1757f5b6bf5332`
- candidate-envelope Git blob: `c4478c841b74d3aec8038677686f5d6fdad0a2d5`
- candidate-binding SHA-256: `479d6bf79592d5f1527012c86795313f866714d5ab0c881db9d5dc5c2876f4d4`
- candidate-binding Git blob: `ec82b25d3ec69ab8f6e6e78ff57652c03ed3b3db`
- Scope Review record path: `docs/plans/references/m8-network-acquisition-authority-remediation-independent-review-20260919-r02.md`
- Scope Review record bytes: `8413`
- Scope Review record SHA-256: `c26ae1911d1eb32748d9ce1d36fe17a7d1124d134fc9fe41042cb88862911c5d`
- Scope Review record Git blob if persisted unchanged: `f51fc0fbb34783fd0cd34c541edf8059bfa2a067`
- Scope Review decision: `NETWORK_ACQUISITION_SCOPE_APPROVED`
- historical r01 failure bytes: `1610`
- historical r01 failure SHA-256: `303fcfec5a30e18543a10b94e692bacdd766369fc7c086a2f19d8ca69d8be252`
- historical r01 failure Git blob: `6aed5b3f636e247efbbfb7b47149a1e7792fc968`

The fixed payload, payload binding, candidate envelope, candidate binding, review-target, dispatch
material, and dispatch facts recompute consistently with the Scope Review. The historical r01 failure
record remains unchanged. The pre-decision state remains `BLOCKED / NOT_STARTED`; every declared
execution authorization flag remains false, and no acquisition or M8 execution evidence is present.

## Blocking findings

Authorization fails closed for the following concrete reasons:

1. The reviewed payload does not declare any allowed package name. It contains only
   `limits.max_dependency_packages: 0` and provenance field names; it does not contain a finite package
   allowlist.
2. The reviewed payload does not declare any allowed package version.
3. The reviewed payload does not declare any exact wheel tag or exact wheel filename/artifact identity.
   `cp313`, `win_amd64`, and `cp313-win_amd64` identify the runtime, not an authorized artifact.
4. The reviewed payload does not declare exact initial URL paths or project/version/file URL closure.
   Host-only `pypi.org` and redirect-host rules are insufficient for an acquisition authorization.
5. The exact downloader candidate is explicitly not validated for the current candidate:
   `observer_binding.candidate_downloader_validation.candidate_exact_path_validated_by_prior_validator`
   is `false`.
6. Real collector authority and collector coverage receipts are absent:
   `observer_binding.full_s1_observer_authority` is `false`,
   `observer_binding.real_collector_authorized` is `false`, and
   `observer_binding.real_collector_coverage_receipts` is
   `REQUIRED_BEFORE_ANY_ACQUISITION_AUTHORIZATION`.
7. The frozen payload authorizes only policy preparation/review. Its `allowed_actions` are
   `prepare-and-review-authority-only`, `run-hermetic-builder-self-check`, and
   `request-independent-scope-review`; granting network or download authority would exceed the reviewed
   scope.
8. Because package, version, exact tag, artifact, and URL/path scope are absent, a positive owner record
   would require the executor to choose them or would require modifying/replacing reviewed material.
   Both are prohibited.

Affected object: authority payload at commit
`44e6cff5535f37405b277a893bc59e9bbb4781c9`, SHA-256
`f2992204cff95bf56c85601f44cf47ec03f0655aa71fe4690f199fd864da8a1e`, Git blob
`a5b0e2f92bc16092738f57bf2329394d1694fe90`. The blocking fields are `allowed_actions`,
`source_policy`, `runtime_authority`, `observer_binding`, `wheel_policy`, and the absent finite
package/version/artifact/URL allowlists.

## Approved actions

None.

## Denied actions and stage flags

- preparation: false
- identity creation: false
- formal venv creation: false
- backend selection: false
- collector creation: false
- network access: false
- package index access: false
- PyPI access: false
- metadata acquisition: false
- wheel download: false
- wheelhouse creation: false
- resolver execution: false
- installation: false
- S1: false
- S1-B: false
- S2: false
- S3: false
- M8 execution: false

Additional authorization flags:

- acquisition_authorized: false
- network_access_authorized: false
- pypi_access_authorized: false
- wheel_download_authorized: false
- wheelhouse_creation_authorized: false
- resolver_authorized: false
- installation_authorized: false
- formal_venv_authorized: false
- formal_identity_authorized: false
- real_collector_authorized: false
- backend_selection_authorized: false
- s1_retry_authorized: false
- s1_b_authorized: false
- s2_authorized: false
- s3_authorized: false

## Network, source, package, identity, tool, root, and backend scope

No operational scope is authorized.

- allowed domains: none
- allowed URL/path ranges: none
- allowed protocols: none for execution
- package/index sources: none
- package names: none
- package versions: none
- exact tags: none
- artifact types: none
- identity: none authorized
- downloader/tool: none authorized; the reviewed curl identity remains candidate-only
- preparation root: no root creation or use authorized
- backend: none authorized
- cycle applicability: decision applies only to
  `m8-network-acquisition-authority-remediation-20260919-r02`
- validity boundary: rejection is effective immediately and remains in force unless a new, independently
  reviewed, fully concrete candidate receives a separate positive authorization decision

The reviewed host, TLS, timeout, byte, and write policies remain unexercised policy facts. They do not
form an executable network allowance.

## Limits

Authorized operational limits are all zero because no operation is approved:

- network requests: `0`
- metadata requests: `0`
- wheel downloads: `0`
- downloaded files: `0`
- downloaded bytes: `0`
- single-file bytes: `0`
- concurrency: `0`
- retries: `0`
- redirects: `0`
- resolver expansion: `0`
- dependency packages: `0`
- execution seconds: `0`

The nonzero limits in the reviewed candidate are policy ceilings only and are not activated by this
rejection.

## Failure, stop, revocation, and failed-close policy

- Stop before preparation-root creation, identity/venv creation, collector creation, network access,
  package-index access, metadata acquisition, download, resolver, installation, backend selection, or
  any M8 stage.
- Any attempted action listed above is unauthorized and must stop immediately without retry.
- Do not convert this rejection into retry authority.
- Do not infer authority from the Scope Review, Builder self-check, candidate policy ceilings, branch
  head, worktree files, or prior records.
- Do not modify the reviewed candidate, binding, dispatch, Scope Review, or historical r01 failure.
- Candidate/binding/review/dispatch drift, an unexpected true flag, status drift, prior execution,
  ambiguous source scope, missing exact package/version/tag/artifact/URL scope, absent current downloader
  validation, or absent collector coverage keeps the cycle failed closed.
- Revocation conditions are not applicable to a positive grant because no permission is granted; any
  purported downstream permission derived from this record is void.

## State transition

- pre-decision m8_status: `BLOCKED / NOT_STARTED`
- pre-decision authorization flags: all false
- post-decision m8_status: `BLOCKED / NOT_STARTED`
- post-decision authorization flags: all false
- state transition: no execution-state transition; an independent failed-closed authorization decision
  is recorded

## Authorization record Git binding

- Git file path: `docs/plans/references/m8-network-acquisition-authorization-decision-20260919-r02.md`
- file size: to be computed from the exact persisted bytes
- SHA-256: to be computed from the exact persisted bytes
- Git blob: to be computed from the exact persisted bytes
- binding commit: not created by this review; a later additive commit may bind this record without
  changing its bytes
- parent: not created by this review
- tree: not created by this review
- binding commit object size: not created by this review

A record cannot contain its own future commit OID, parent, tree, or commit object size. This record is
complete as a failed-closed decision without those future values. Any later Git binding must be additive,
must bind these exact bytes, and must not change this decision or authorize execution.

## Allowed next action

Create a new, independently named remediation candidate and one-way binding chain that explicitly fixes
all of the following before requesting a new Scope Review and a new Owner authorization decision:

- finite exact package-name allowlist;
- exact version allowlist;
- exact wheel filename and complete Python/ABI/platform tag allowlist;
- exact initial metadata URL paths and permitted artifact URL/path closure;
- independently verified current downloader path/version/SHA-256/TLS identity;
- real collector authority and immutable coverage/lifecycle receipts;
- finite limits and stop rules bound directly to those exact artifacts.

No network, download, resolver, installation, backend, collector, preparation, identity, S1, S1-B, S2,
S3, or M8 action is an allowed next action.
