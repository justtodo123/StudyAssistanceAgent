# M8 Network-Acquisition Cycle Independent Scope Review Request — 2026-09-19 r06

- record_type: `M8_NETWORK_ACQUISITION_CYCLE_INDEPENDENT_SCOPE_REVIEW_REQUEST`
- cycle_id: `m8-network-acquisition-authority-20260919-r02`
- cycle_type: `NETWORK_ACQUISITION_CYCLE`
- branch: `docs/m8-network-acquisition-cycle-r02`
- reviewer_role: `independent-scope-reviewer`
- reviewer_id: `NOT_YET_DESIGNATED`
- independence_required: `true`
- request_status: `PENDING_INDEPENDENT_REVIEW`

## Frozen review objects

- additive binding: `docs/plans/references/external-artifacts/m8-network-acquisition-git-binding-20260919-r06.json`
- additive binding commit: `106f6adaa1e54b3dd382529b9144da9358c5aba1`
- additive binding parent: `7fc2bcfa1209eec7d86744fd3f9439a85e8168d5`
- additive binding tree: `fda9be2847d069cb1a8f851c96b4a886075383e3`
- additive binding size: `2084`
- additive binding SHA-256: `2b951ec91d05f54c2e306cfe40ca99d824efa79241fe3653830f7925b13feaca`
- additive binding Git blob: `7ed31dee47d74049961f136ab69b1e1cdfb05d7e`
- predecessor binding: `docs/plans/references/external-artifacts/m8-network-acquisition-git-binding-20260919-r05.json`
- predecessor binding commit: `7fc2bcfa1209eec7d86744fd3f9439a85e8168d5`
- authority candidate: `docs/plans/references/external-artifacts/m8-network-acquisition-authority-candidate-20260919-r04.json`
- current observer: `tools/m8_observe_network_acquisition_v2.py`
- current observer tests: `tools/m8_test_observe_network_acquisition_v2.py`
- Builder self-check: `docs/plans/references/m8-network-acquisition-cycle-builder-self-check-20260919-r08.md`

The r06 binding corrects the r05 transitional `allowed_next_action` to
`independent-read-only-scope-review`. It remains additive, Builder-only evidence, and grants no
execution or acquisition authority. The r05 binding remains immutable history and is superseded only
for current-transition wording.

## Required independent review

Reviewer 必须独立、只读地核验：

1. r04 candidate and r06 binding canonical bytes satisfy `sa-json-c14n-v1`;
2. candidate, observer, test, and r08 self-check SHA-256, Git blob, size, path, commit, parent,
   and tree bindings match the already frozen objects;
3. the r06 binding's predecessor reference and transition state are truthful, and r05 is
   preserved as immutable history;
4. additive history preserves r02/r03/r04/r05/r06/r07/r08 and does not rewrite historical records;
5. official PyPI source, exact URL closure, per-hop redirect hosts, HTTPS/TLS, proxy/auth/mirror/
   extra-index denial, retry/timeout/concurrency, and redirect limits are fail-closed;
6. runtime identity, exact downloader path/identity, command-line contract, empty ambient environment,
   shell denial, and candidate schema validation are complete for the declared review scope;
7. wheel-only policy, preparation root, persistent allowlist, Windows path safety, partial/atomic
   publication, redaction, provenance, and hard limits are closed without bypass;
8. v2 remains hermetic declared-event and candidate-schema validation only, with no real collector,
   lifecycle/coverage receipts, or acquisition execution capability claimed;
9. all acquisition, network, download, wheelhouse, resolver, installation, formal environment/
   identity, collector, backend, S1, S1-B, S2, and S3 authorization flags remain false;
10. the Builder has not issued an independent Reviewer or Owner decision.

## Reviewer prohibitions

不得联网、访问 PyPI、下载或复制 wheel、创建 wheelhouse、运行 resolver/installer、创建正式 venv/identity、
执行 S1/S1-B/S2/S3、选择 backend、修改任何对象或伪造 acquisition evidence。

## Allowed decision values

独立 Reviewer 只能输出以下之一：

- `NETWORK_ACQUISITION_SCOPE_ACCEPTED`
- `NETWORK_ACQUISITION_SCOPE_REJECTED_FAILED_CLOSED`
- `RETURN_FOR_SCOPE_REMEDIATION`

接受仅表示进入 Owner acquisition decision gate，不授权联网、下载、wheelhouse、resolver、安装或 M8 执行。

- acquisition_authorized: `false`
- network_access_authorized: `false`
- wheel_download_authorized: `false`
- wheelhouse_creation_authorized: `false`
- resolver_authorized: `false`
- installation_authorized: `false`
- formal_venv_authorized: `false`
- formal_identity_authorized: `false`
- real_collector_authorized: `false`
- s1_retry_authorized: `false`
- s1_b_authorized: `false`
- s2_authorized: `false`
- s3_authorized: `false`
- backend_selection_authorized: `false`
- m8_status: `BLOCKED / NOT_STARTED`
- allowed_next_action: `independent-read-only-scope-review`

`READY_FOR_INDEPENDENT_SCOPE_REVIEW`
