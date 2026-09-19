# M8 Network-Acquisition Cycle Builder Adversarial Self-Check — 2026-09-19 r03

- record_type: `M8_NETWORK_ACQUISITION_CYCLE_BUILDER_ADVERSARIAL_SELF_CHECK`
- builder_role: `builder`
- cycle_id: `m8-network-acquisition-authority-20260919-r02`
- cycle_type: `NETWORK_ACQUISITION_CYCLE`
- branch: `docs/m8-network-acquisition-cycle-r02`
- original_review_object: `3c58b4b598f72d88917681336bac0167af4b9c5f`
- original_parent: `2c92f61708b46d79d92f84eb7b0106bf38d6166c`
- remediation_candidate: `external-artifacts/m8-network-acquisition-authority-candidate-20260919-r03.json`
- result: `BUILDER_REMEDIATION_PENDING_GIT_BINDING`
- acquisition_status: `NOT_AUTHORIZED`
- m8_status: `BLOCKED / NOT_STARTED`

> 本记录仅是 Builder 自动对抗性检查，不是独立 Reviewer 或 Owner 决定，不得输出或替代
> `NETWORK_ACQUISITION_SCOPE_ACCEPTED`、`OWNER_AUTHORIZED` 或任何执行授权。

## r02 对抗性结论

原 r02 候选和自检无法作为可审查的完整 authority freeze，已 fail-closed。历史文件保持不变，缺陷仅通过
additive r03 材料修复。

| check_id | r02 result | evidence / remediation |
| --- | --- | --- |
| actual-parent-cycle | FAIL_CLOSED | r02 把同一提交才新增的 policy-only decision 描述为旧周期不可变历史；r03 明确实际父周期为 `m8-s1-network-acquisition-cycle-20260918-r01`，并把该 decision 标为 `created_in_commit: 3c58b4b...`。 |
| dangling-observer-binding | FAIL_CLOSED | r02 指向提交中不存在的 r09；r03 改为已提交 r08，并绑定其 Git blob 与 SHA-256。 |
| canonical-json | FAIL_CLOSED | r02 缺 `canonicalization_id` 且键未排序；r03 使用 `sa-json-c14n-v1`：UTF-8、无 BOM、紧凑排序键、无 CR、恰好一个终止 LF。 |
| source-policy | REMEDIATED | r03 冻结官方 PyPI 严格模式、HTTPS GET、TLS/Schannel、无代理/认证/镜像/额外 index、redirect limit 3、retry 1、connect 15 秒、request total 300 秒。 |
| runtime-authority | REMEDIATED | r03 冻结 CPython 3.13.3、`cp313/cp313/win_amd64`、AMD64、Windows build、`D:\\Python\\python.exe`、`-I -S`、UTF-8/UTC/no-site/no-bytecode policy。 |
| downloader-identity | REMEDIATED_AS_CANDIDATE_ONLY | r03 记录本地 curl 路径、SHA-256、大小、版本、Schannel 与 feature 列表；身份仍明确为候选，未经 Owner 授权。 |
| process-policy | REMEDIATED | r03 冻结 exact executable、单一 child、无 shell、仅零退出码成功及 stdout/stderr evidence policy。 |
| wheel-only-policy | REMEDIATED | wheel only；sdist/source archive/VCS/editable/build/build isolation/setup.py/candidate-code execution 均拒绝。 |
| write-boundary | REMEDIATED | r03 冻结新 root、精确 persistent allowlist、forbidden roots、Windows path safety、partial→verify→atomic rename、existing target deny。 |
| provenance-schema | REMEDIATED | r03 冻结 package/version/file/tags/URL/redirect/status/size/digest/timestamp/downloader/TLS/cycle/authority digest 等字段；候选未伪造真实 acquisition provenance。 |
| limits | REMEDIATED | r03 冻结 concurrency 1、metadata 4 MiB、single wheel 512 MiB、total 2 GiB、files 256，并声明任何超限 fail-closed。 |
| observer-scope | DISCLOSED_BLOCKER | r08 仅是 declared-event policy validator；不是 real collector，无 lifecycle ledger、coverage receipts、no-follow containment、rename-race/process-identity/PID-reuse/evidence-sealing authority。r03 未提升其权限。 |
| resolver-isolation | PASS | untracked resolver 与测试被排除在本周期 remediation 之外；未运行。静态审计发现 runtime contract、host-path disclosure/TOCTOU、ZIP symlink、dist-info/RECORD、canonical JSON、output overwrite 等 blocker。 |
| authorization-flags | PASS | r03 包含完整 false set：network/acquisition/wheelhouse/resolver/install/formal identity/venv/S1 retry/S1-B/S2/S3/backend 均未授权。 |
| forbidden-execution | PASS | 未联网、未访问 PyPI、未下载 wheel、未创建 wheelhouse、未运行 resolver、未安装、未创建正式环境、未执行 S1/S2/S3、未选 backend。 |
| historical-immutability | PASS | r02、旧候选、旧 Reviewer/Owner/Builder 记录均未修改；r03 是 additive remediation。 |
| git-object-freeze | PENDING | 候选必须先进入 additive commit，随后由新的 binding record 绑定 candidate blob/SHA-256、commit/parent/tree/path；不能自绑定。 |
| independent-review | NOT_PERFORMED | Builder 不冒充独立 Reviewer；只能在 Git binding 与 hermetic matrix 完成后发出 review request。 |

## r03 预期绑定

以下旧对象绑定来自已提交 Git 对象，仅为 reference-only：

- observer authority r08:
  - Git blob: `5eb536f994343aacc669e0e38e70a5fa048af103`
  - SHA-256: `e882a712187a4a9e759234b6acab8c4ced8188addafd7cfe2bd6613f080c9c99`
- observer module:
  - Git blob: `97c005710b62a76221cc8669bd399254398967ce`
  - SHA-256: `841dc1e98d09c673045b96c0949930b7cca1829db758598c6d82706178869c1a`
- observer test:
  - Git blob: `1a859ee1355d4d76ffc52fe5cbad281c9ee47a6a`
  - SHA-256: `c300095adee7001986cab5474b1afab211eb03541594201d086a8fdb97c2e78c`

候选自身的 SHA-256 和 Git blob 必须由下一条 additive binding record 在提交后记录。

## 当前处置

Builder-scope 内容缺陷已通过 r03 candidate 修复，但 Git-object freeze 尚未完成，因此当前不是独立审查入口。

- independent_scope_review_required: `true`
- independent_scope_review_status: `NOT_STARTED`
- owner_acquisition_decision_status: `NOT_REACHED`
- independent_acquisition_review_status: `NOT_YET_REQUIRED`
- real_collector_authorized: `false`
- acquisition_authorized: `false`
- network_access_authorized: `false`
- wheel_download_authorized: `false`
- wheelhouse_creation_authorized: `false`
- resolver_authorized: `false`
- installation_authorized: `false`
- formal_venv_authorized: `false`
- formal_identity_authorized: `false`
- s1_retry_authorized: `false`
- s1_b_authorized: `false`
- s2_authorized: `false`
- s3_authorized: `false`
- backend_selection_authorized: `false`
- allowed_next_action: `commit-r03-remediation-then-create-additive-git-binding`

`BUILDER_REMEDIATION_PENDING_GIT_BINDING`
