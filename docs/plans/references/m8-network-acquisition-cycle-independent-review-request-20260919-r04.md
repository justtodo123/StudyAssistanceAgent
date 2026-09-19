# M8 Network-Acquisition Cycle Independent Scope Review Request — 2026-09-19 r04

- record_type: `M8_NETWORK_ACQUISITION_CYCLE_INDEPENDENT_SCOPE_REVIEW_REQUEST`
- cycle_id: `m8-network-acquisition-authority-20260919-r02`
- cycle_type: `NETWORK_ACQUISITION_CYCLE`
- reviewer_role: `independent-scope-reviewer`
- reviewer_id: `NOT_YET_DESIGNATED`
- independence_required: `true`
- request_status: `PENDING_INDEPENDENT_REVIEW`

## Review objects

- remediation commit: `d15f620ee292aceb4c3f2bb0ff359a9a5a76d631`
- remediation parent: `6705afb2b83effa21e78c3b0172f5b9250ba6d1b`
- remediation tree: `c6bdc2433cf2e054098807e20fa390cacd51be5e`
- authority candidate:
  `external-artifacts/m8-network-acquisition-authority-candidate-20260919-r04.json`
- candidate Git binding:
  `external-artifacts/m8-network-acquisition-git-binding-20260919-r04.json`
- Builder remediation self-check:
  `m8-network-acquisition-cycle-builder-self-check-20260919-r05.md`
- Builder final self-check:
  `m8-network-acquisition-cycle-builder-self-check-20260919-r06.md`
- immutable predecessor candidate/self-check commit:
  `6705afb2b83effa21e78c3b0172f5b9250ba6d1b`
- original r02 package commit:
  `3c58b4b598f72d88917681336bac0167af4b9c5f`
- reference-only policy validator:
  `external-artifacts/m8-minimal-1k-v3-s1-network-acquisition-observer-authority-20260918-r08.json`

## Required review

Reviewer 必须独立核验：

1. r04 JSON 是否严格满足 `sa-json-c14n-v1` 与其 strict document schema；
2. candidate SHA-256、Git blob、size、commit、parent、tree、path 是否与 r04 binding 一致；
3. r02/r03 缺陷是否通过 additive r04/r05 诚实披露，而非改写历史；
4. source、逐跳 redirect、TLS、proxy/auth/mirror/index、retry/timeout/concurrency 是否 fail-closed；
5. runtime executable/tags/OS/architecture/startup 与 downloader candidate identity 是否完整；
6. curl config/environment/option/header/stdin/output/write-out/wall-clock schema 是否闭合；
7. wheel-only、preparation root、persistent allowlist、Windows path safety、partial/atomic publication 与 limits 是否闭合；
8. provenance required fields 是否完整且没有伪造 acquisition evidence；
9. r08 是否仅是旧 exact-path 的 declared-event policy validator，且与当前 downloader path 的 mismatch 已显式披露；
10. real collector、coverage receipts 和 exact current-candidate validation 是否仍明确缺失且未被授权；
11. 所有 execution/authorization flags 是否为 false；
12. resolver、临时文件、`tools/README.md` 与无关历史草稿是否未进入 review object；
13. Builder 是否仅输出 `READY_FOR_INDEPENDENT_SCOPE_REVIEW`，没有代替 Reviewer 或 Owner 作决定。

## Reviewer prohibitions

不得联网、访问 PyPI、下载或复制 wheel、创建 wheelhouse、运行 resolver/installer、创建正式 venv/identity、
执行 S1/S1-B/S2/S3、选择 backend、修改任何对象或伪造 acquisition evidence。

## Allowed decision values

独立 Reviewer 只能输出以下之一：

- `NETWORK_ACQUISITION_SCOPE_ACCEPTED`
- `NETWORK_ACQUISITION_SCOPE_REJECTED_FAILED_CLOSED`
- `RETURN_FOR_SCOPE_REMEDIATION`

接受仅表示进入 Owner acquisition decision gate，不授权联网或下载。

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
