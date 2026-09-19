# 辅助与历史治理记录（plans/references/）

> 本目录不具阶段权威，不能产生新授权。
> 最终阶段状态和路线图以 [`docs/PLAN.md`](../../PLAN.md) 为准，正式准入政策以 `docs/standards/` 为准。
> 若本目录材料与上述权威冲突，以正式权威为准。

## 用途与证据边界

本目录同时存放两类材料：

1. **非正式分析与事实调查**：用于对照外部要求、讨论阶段顺序和辅助维护正式计划；不是最终支撑来源。
2. **限定范围的历史治理记录**：协议、授权、审计、处置和治理复盘可证明其明确记载的既往事实，但不具当前阶段
   权威，不得扩张、续用或组合成新的批准。

历史材料或未批准草案不能关闭 Decision、选择后端、批准阶段 admission，或授权建根、source authoring、preflight、
执行与生产实现。经负责人明确批准的范围/Decision 记录只能证明其所载政策已批准；阶段状态仍以 PLAN 和机器门禁
为准。正式任务拆解只在 PLAN 授权后写入对应 `m*-plan.md`。

## 当前文件

S1 prerequisite freeze 的 candidate closure 由目标 commit 内的 canonical oracle manifest 唯一声明并机械展开。
Code-fixed bootstrap 防止 manifest 省略自身、aggregate 或 freeze authority chain；fixture graph/member 数仍可作为
展开规则的结构事实，但最终排序路径、数量、总字节与 closure digest 均从声明推导，不再以旧 29 + 90 = 119
组合作为独立权威。Gating closure 排除 historical reviewer、worksheet、external gate/artifact 和既有 review-freeze；
旧 88/88 与 77/77 校验只能从显式 full commit 的八对象闭包隔离重放，并明确为 non-gating evidence；shallow
repository 被拒绝。所选 commit 中的 validator bytes 是调用者明确选择并执行的代码，仍具有调用用户的 OS 权限；外部临时树、
`python -I`、环境清理、bounded I/O/timeout、Windows kill-on-close Job Object 与 process cleanup 不是 OS sandbox，且
Windows process launch 到 Job assignment 之间仍有短暂非原子窗口。四个 declared template 都必须是
`sa-json-c14n-v1` bytes；实例化规则为 strict parse、结构化替换、canonical serialize，不得直接文本替换 placeholder。
本索引与以上声明均不产生任何 gate 或执行授权。

| 文件 | 说明 | 地位 |
| --- | --- | --- |
| [`agent-alignment-analysis.md`](agent-alignment-analysis.md) | 对照 Agent 招聘要求与仓库现状 | 辅助调查 |
| [`stage-advancement-analysis.md`](stage-advancement-analysis.md) | M6–M10 推进顺序与招聘项映射 | 辅助调查 |
| [`recruitment-driven-feasibility.md`](recruitment-driven-feasibility.md) | 以招聘要求为唯一标准的可行性分析与阶段更新建议 | 辅助调查 |
| [`m8-m12-scope-decision-v1.md`](m8-m12-scope-decision-v1.md) | M8–M12 规模化范围决策 | `APPROVED / SCOPE_FROZEN`；不等于阶段 admission |
| [`m8-decision-closure-v1.md`](m8-decision-closure-v1.md) | M8 八项 Decision 批准记录 | `APPROVED / EIGHT_DECISIONS_RESOLVED`；不选择后端或授权实现 |
| [`m8-minimal-1k-v3-s1-prereq-oracle-manifest.json`](m8-minimal-1k-v3-s1-prereq-oracle-manifest.json) | v3 S1 prerequisite oracle 声明 | target-commit-bound canonical manifest；声明封闭 gating closure、四个模板与独立 non-gating historical replay；不产生授权 |
| [`external-artifacts/m8-minimal-1k-v3-s1-owner-decision-20260918.json`](external-artifacts/m8-minimal-1k-v3-s1-owner-decision-20260918.json) | v3 S1 Owner 决策记录 | `S1_AUTHORIZED / prepare-s1-environment`；不授权 S2/S3、backend execution 或 admission |
| [`external-artifacts/m8-minimal-1k-v3-s1-failure-20260918-r01.json`](external-artifacts/m8-minimal-1k-v3-s1-failure-20260918-r01.json) | v3 S1-A fail-closed 并行失败记录 | `S1_A_FAILED / request-owner-environment-resolution`；缺少唯一精确离线依赖闭包及完整 frozen config/inventory；S2 保持 `NOT_AUTHORIZED` |
| [`m8-minimal-1k-v3-s1-wheelhouse-preparation-authorization-20260918-r01.md`](m8-minimal-1k-v3-s1-wheelhouse-preparation-authorization-20260918-r01.md) | v3 S1 wheelhouse 准备 Owner 拒绝记录 | `WHEELHOUSE_PREPARATION_REJECTED / request-owner-environment-resolution`；无完整本地离线闭包且无获取缺失 wheel 的权限；不授权 wheelhouse、S1 retry、S1-B、S2 或 S3 |
| [`m8-minimal-1k-v3-s1-environment-resolution-20260918-r01.md`](m8-minimal-1k-v3-s1-environment-resolution-20260918-r01.md) | v3 S1 environment-resolution Owner 三选一决策 | `ENVIRONMENT_RESOLUTION_REMAINS_FAILED_CLOSED / stop`；无完整本地闭包、网络 acquisition authority 或外部 wheelhouse import authority |
| [`m8-minimal-1k-v3-s1-network-acquisition-cycle-initiation-20260918-r01.md`](m8-minimal-1k-v3-s1-network-acquisition-cycle-initiation-20260918-r01.md) | v3 S1 network-acquisition 新周期启动候选 | 新 cycle 仅允许准备并审查官方 PyPI 严格模式 authority；不恢复旧链、不授权下载、resolver、S1/S2/S3 或 backend selection |
| [`m8-owner-policy-only-scope-decision-20260919.md`](m8-owner-policy-only-scope-decision-20260919.md) | M8 Owner policy-only scope decision | `POLICY_ONLY_SCOPE_ACCEPTED`; accepts only the declared-event-only policy validator; full S1 observer authority, real collector, acquisition, S1/S2/S3, backend selection, and M8 execution remain unauthorized; `BLOCKED / NOT_STARTED` |
| [`m8-network-acquisition-cycle-initiation-20260919-r02.md`](m8-network-acquisition-cycle-initiation-20260919-r02.md) | New M8 network-acquisition cycle Owner initiation | `NETWORK_ACQUISITION_CYCLE_INITIATED`; new branch and identity, authority preparation/review only; all acquisition and execution permissions remain false |
| [`external-artifacts/m8-network-acquisition-authority-candidate-20260919-r02.json`](external-artifacts/m8-network-acquisition-authority-candidate-20260919-r02.json) | New-cycle network-acquisition authority candidate | Additive `CANDIDATE_NOT_REVIEWED`; freezes official-PyPI source, CPython 3.13.3 runtime, write/provenance/limit boundaries; does not authorize network or acquisition |
| [`m8-network-acquisition-cycle-builder-self-check-20260919-r02.md`](m8-network-acquisition-cycle-builder-self-check-20260919-r02.md) | New-cycle Builder scope self-check | Scope preparation checks pass; independent review remains pending; no acquisition or M8 stage executed |
| [`m8-network-acquisition-cycle-independent-review-request-20260919-r02.md`](m8-network-acquisition-cycle-independent-review-request-20260919-r02.md) | New-cycle independent scope-review request | Requests read-only independent review; reviewer is not yet designated; no authority is granted |
| [`external-artifacts/m8-network-acquisition-authority-candidate-20260919-r03.json`](external-artifacts/m8-network-acquisition-authority-candidate-20260919-r03.json) | New-cycle network-acquisition authority remediation candidate | Additive canonical v10 candidate; later Builder audit found a missing runtime executable and other closure gaps, so it remains immutable but is superseded by r04 |
| [`m8-network-acquisition-cycle-builder-self-check-20260919-r03.md`](m8-network-acquisition-cycle-builder-self-check-20260919-r03.md) | New-cycle Builder adversarial remediation check | r02 fails closed and r03 awaited Git binding; later r05 audit identifies additional r03 blockers; no independent review or authority is claimed |
| [`external-artifacts/m8-network-acquisition-authority-candidate-20260919-r04.json`](external-artifacts/m8-network-acquisition-authority-candidate-20260919-r04.json) | New-cycle second authority remediation candidate | Additively restores the runtime executable, closes downloader command/environment and strict schema gaps, and discloses the r08 exact-path mismatch; all execution permissions remain false |
| [`m8-network-acquisition-cycle-builder-self-check-20260919-r05.md`](m8-network-acquisition-cycle-builder-self-check-20260919-r05.md) | New-cycle second Builder adversarial check | Fails r03 and its uncommitted review package closed, records r04 remediation, and leaves Git-object binding pending |
| [`external-artifacts/m8-network-acquisition-git-binding-20260919-r04.json`](external-artifacts/m8-network-acquisition-git-binding-20260919-r04.json) | New-cycle r04 Git-object binding | Freezes r04 candidate/r05 self-check blob, SHA-256, size, commit, parent and tree; Builder-only evidence, no acquisition authority |
| [`m8-network-acquisition-cycle-builder-self-check-20260919-r06.md`](m8-network-acquisition-cycle-builder-self-check-20260919-r06.md) | New-cycle Builder final self-check | Full hermetic matrix passes for independent scope review while current-candidate collector/validator remains an explicitly disclosed authorization blocker |
| [`m8-network-acquisition-cycle-independent-review-request-20260919-r04.md`](m8-network-acquisition-cycle-independent-review-request-20260919-r04.md) | Corrected independent scope-review package | Binds r04 candidate/binding/Builder records for read-only independent review; does not grant acquisition authority |
| [`m8-network-acquisition-cycle-independent-review-prompt-20260919-r04.md`](m8-network-acquisition-cycle-independent-review-prompt-20260919-r04.md) | Corrected independent scope-review prompt | Prepared but not dispatchable: subsequent r07 Builder audit returned the package for current-candidate validator remediation |
| [`m8-network-acquisition-cycle-builder-self-check-20260919-r07.md`](m8-network-acquisition-cycle-builder-self-check-20260919-r07.md) | Post-package Builder adversarial check | Additively supersedes r06 readiness after independent static audit found current downloader/root/schema and test-conformance blockers; review remains not started |
| [`../tools/m8_observe_network_acquisition_v2.py`](../tools/m8_observe_network_acquisition_v2.py) | Additive current-candidate hermetic observer/schema validator | Binds current r04 curl/root and strict candidate checks; declared-event only, no real collector or acquisition authorization |
| [`../tools/m8_test_observe_network_acquisition_v2.py`](../tools/m8_test_observe_network_acquisition_v2.py) | Additive v2 observer regression script | Covers canonical URL, current path/root, strict document schema and downloader/environment fail-closed controls |
| [`external-artifacts/m8-network-acquisition-git-binding-20260919-r05.json`](external-artifacts/m8-network-acquisition-git-binding-20260919-r05.json) | Additive r05 Git-object binding | `GIT_OBJECTS_FROZEN_BUILDER_ONLY`; freezes observer package bytes and grants no acquisition authority |
| [`m8-network-acquisition-cycle-builder-self-check-20260919-r08.md`](m8-network-acquisition-cycle-builder-self-check-20260919-r08.md) | Additive r08 Builder self-check | Validator remediation implemented; real collector remains blocked; Builder-only and no acquisition authority |
| [`m8-network-acquisition-cycle-independent-review-request-20260919-r05.md`](m8-network-acquisition-cycle-independent-review-request-20260919-r05.md) | Historical additive r05 independent scope-review request | Superseded by r06 transition-wording correction; never grants acquisition authority |
| [`m8-network-acquisition-cycle-independent-review-prompt-20260919-r05.md`](m8-network-acquisition-cycle-independent-review-prompt-20260919-r05.md) | Historical additive r05 independent scope-review prompt | Superseded by r06 transition-wording correction; not dispatched and not authority-granting |
| [`external-artifacts/m8-network-acquisition-git-binding-20260919-r06.json`](external-artifacts/m8-network-acquisition-git-binding-20260919-r06.json) | Additive r06 Git-object binding candidate | Corrects the current transition to `independent-read-only-scope-review`; Builder-only candidate, no acquisition authority |
| [`m8-network-acquisition-cycle-independent-review-request-20260919-r06.md`](m8-network-acquisition-cycle-independent-review-request-20260919-r06.md) | Additive r06 independent scope-review request | Points to r06 binding candidate for read-only independent review; does not grant acquisition authority |
| [`m8-network-acquisition-cycle-independent-review-prompt-20260919-r06.md`](m8-network-acquisition-cycle-independent-review-prompt-20260919-r06.md) | Additive r06 independent scope-review prompt | Prepared for a separately designated Reviewer; not dispatched and not authority-granting |
| [`external-artifacts/m8-network-acquisition-authority-remediation-candidate-20260919-r01.json`](external-artifacts/m8-network-acquisition-authority-remediation-candidate-20260919-r01.json) | New independent remediation candidate r01 | Canonical two-layer payload; pending independent read-only review; all acquisition and execution permissions remain false |
| [`m8-network-acquisition-authority-remediation-builder-self-check-20260919-r01.md`](m8-network-acquisition-authority-remediation-builder-self-check-20260919-r01.md) | Remediation Builder self-check r01 | Construction facts only; Git binding is recorded separately; no independent verdict or authority |
| [`m8-network-acquisition-authority-remediation-review-request-20260919-r01.md`](m8-network-acquisition-authority-remediation-review-request-20260919-r01.md) | Remediation independent review request r01 | Requests a new read-only review; does not grant acquisition authority |
| [`m8-network-acquisition-authority-remediation-review-prompt-20260919-r01.md`](m8-network-acquisition-authority-remediation-review-prompt-20260919-r01.md) | Remediation independent review prompt r01 | Reviewer instructions; only the two fail-closed review conclusions are permitted |
| [`external-artifacts/m8-network-acquisition-authority-remediation-git-binding-20260919-r01.json`](external-artifacts/m8-network-acquisition-authority-remediation-git-binding-20260919-r01.json) | Remediation additive Git-object binding r01 | Binds the four-material payload commit; non-self-referential and non-authorizing |
| [`m8-network-acquisition-authority-remediation-independent-review-failure-20260919-r01.md`](m8-network-acquisition-authority-remediation-independent-review-failure-20260919-r01.md) | Immutable r01 independent-review failure record | Records the concrete failed-closed binding defect and verified historical objects; no authority |
| [`m8-network-acquisition-authority-remediation-binding-design-20260919-r02.md`](m8-network-acquisition-authority-remediation-binding-design-20260919-r02.md) | Independent remediation r02 binding design | Defines the one-way non-self-referential Git DAG and all-false execution boundary |
| [`external-artifacts/m8-network-acquisition-authority-remediation-payload-20260919-r02.json`](external-artifacts/m8-network-acquisition-authority-remediation-payload-20260919-r02.json) | Remediation r02 canonical authority payload | Freezes policy bytes only; pending independent review and grants no acquisition authority |
| [`external-artifacts/m8-network-acquisition-authority-remediation-payload-binding-20260919-r02.json`](external-artifacts/m8-network-acquisition-authority-remediation-payload-binding-20260919-r02.json) | Remediation r02 payload binding | Directly freezes design and payload Git/file facts; non-authorizing |
| [`external-artifacts/m8-network-acquisition-authority-remediation-candidate-20260919-r02.json`](external-artifacts/m8-network-acquisition-authority-remediation-candidate-20260919-r02.json) | Remediation r02 candidate envelope | Directly binds concrete payload and payload-binding facts; independent review remains pending |
| [`external-artifacts/m8-network-acquisition-authority-remediation-candidate-binding-20260919-r02.json`](external-artifacts/m8-network-acquisition-authority-remediation-candidate-binding-20260919-r02.json) | Remediation r02 candidate binding | Directly freezes the candidate-envelope Git/file facts; non-authorizing |
| [`m8-network-acquisition-authority-remediation-builder-self-check-20260919-r02.md`](m8-network-acquisition-authority-remediation-builder-self-check-20260919-r02.md) | Remediation r02 Builder self-check | Construction and staged-binding checks only; not an independent verdict or execution authority |
| [`m8-network-acquisition-authority-remediation-review-request-20260919-r02.md`](m8-network-acquisition-authority-remediation-review-request-20260919-r02.md) | Remediation r02 independent scope-review request | Directly binds the exact review target and preceding Git/file facts; non-authorizing |
| [`m8-network-acquisition-authority-remediation-review-prompt-20260919-r02.md`](m8-network-acquisition-authority-remediation-review-prompt-20260919-r02.md) | Remediation r02 independent scope-review prompt | Exact read-only review instructions; no acquisition or execution authority |
| [`external-artifacts/m8-network-acquisition-authority-remediation-review-dispatch-20260919-r02.json`](external-artifacts/m8-network-acquisition-authority-remediation-review-dispatch-20260919-r02.json) | Remediation r02 final review dispatch manifest | Final binding root for independent review; non-authorizing |
| [`m8-network-acquisition-authority-remediation-independent-review-20260919-r02.md`](m8-network-acquisition-authority-remediation-independent-review-20260919-r02.md) | Remediation r02 independent scope review | `NETWORK_ACQUISITION_SCOPE_APPROVED`; scope approval only, no acquisition or execution authority |
| [`m8-network-acquisition-authorization-decision-20260919-r02.md`](m8-network-acquisition-authorization-decision-20260919-r02.md) | Remediation r02 independent Owner authorization decision | `NETWORK_ACQUISITION_AUTHORIZATION_REJECTED_FAILED_CLOSED`; all acquisition and execution permissions remain false |
| [`external-artifacts/m8-network-acquisition-authorization-decision-binding-20260919-r02.json`](external-artifacts/m8-network-acquisition-authorization-decision-binding-20260919-r02.json) | Remediation r02 additive authorization-decision Git binding | Binds the exact failed-closed decision bytes and commit facts; binding-only, no acquisition or execution authority |
| [`external-artifacts/m8-network-acquisition-authorization-decision-binding-correction-20260919-r02.json`](external-artifacts/m8-network-acquisition-authorization-decision-binding-correction-20260919-r02.json) | Remediation r02 additive correction to authorization-decision commit tree fact | Corrects the exact decision-commit tree OID; binding-only, no acquisition or execution authority |
| [`m8-network-acquisition-authority-remediation-evidence-inventory-20260919-r03.md`](m8-network-acquisition-authority-remediation-evidence-inventory-20260919-r03.md) | Remediation r03 evidence inventory | Records evidence insufficiency while preserving r02 Owner rejection and binding-only correction history; no execution authority |
| [`m8-network-acquisition-authority-remediation-binding-design-20260919-r03.md`](m8-network-acquisition-authority-remediation-binding-design-20260919-r03.md) | Remediation r03 blocked binding design | Defines the one-way blocked candidate chain, all-false authorization boundary, and zero operational limits |
| [`external-artifacts/m8-network-acquisition-authority-remediation-payload-20260919-r03.json`](external-artifacts/m8-network-acquisition-authority-remediation-payload-20260919-r03.json) | Remediation r03 canonical blocked payload | `AUTHORIZATION_REMEDIATION_CANDIDATE_BLOCKED`; no exact package/artifact/URL or unsupported receipt is claimed |
| [`external-artifacts/m8-network-acquisition-authority-remediation-payload-binding-20260919-r03.json`](external-artifacts/m8-network-acquisition-authority-remediation-payload-binding-20260919-r03.json) | Remediation r03 payload binding | Freezes design, inventory, and blocked payload facts without authority |
| [`external-artifacts/m8-network-acquisition-authority-remediation-candidate-20260919-r03.json`](external-artifacts/m8-network-acquisition-authority-remediation-candidate-20260919-r03.json) | Remediation r03 blocked candidate envelope | Directly binds the r03 blocked payload package for read-only review only |
| [`external-artifacts/m8-network-acquisition-authority-remediation-candidate-binding-20260919-r03.json`](external-artifacts/m8-network-acquisition-authority-remediation-candidate-binding-20260919-r03.json) | Remediation r03 candidate binding | Freezes the blocked candidate envelope and its predecessors; no acquisition authority |
| [`m8-network-acquisition-authority-remediation-builder-self-check-20260919-r03.md`](m8-network-acquisition-authority-remediation-builder-self-check-20260919-r03.md) | Remediation r03 Builder self-check | Confirms the one-way chain and records evidence-insufficiency block; not an independent decision |
| [`m8-minimal-1k-v3-s1-network-acquisition-authority-20260918-r01.json`](external-artifacts/m8-minimal-1k-v3-s1-network-acquisition-authority-20260918-r01.json) | v3 S1 network-acquisition 来源与 runtime authority 候选 | 冻结 CPython 3.13.3、官方 PyPI host、写入边界、限额和 provenance 字段；observer 尚未实例化，不授权联网或下载 |
| [`external-artifacts/m8-minimal-1k-v3-s1-network-acquisition-observer-authority-20260918-r06.json`](external-artifacts/m8-minimal-1k-v3-s1-network-acquisition-observer-authority-20260918-r06.json) | v3 S1 network-acquisition observer authority 候选 r06 | 仅绑定 hermetic declared-event validator 与测试字节；显式不具真实 collector 能力，不授权 acquisition 或 M8 执行 |
| [`external-artifacts/m8-minimal-1k-v3-s1-network-acquisition-observer-authority-20260918-r07.json`](external-artifacts/m8-minimal-1k-v3-s1-network-acquisition-observer-authority-20260918-r07.json) | v3 S1 network-acquisition observer authority 候选 r07 | additive；绑定最新 observer/test 字节并记录 redirect、redaction、process 与 Windows path remediation；仍不授权 acquisition 或 M8 执行 |
| [`external-artifacts/m8-minimal-1k-v3-s1-network-acquisition-observer-authority-20260918-r08.json`](external-artifacts/m8-minimal-1k-v3-s1-network-acquisition-observer-authority-20260918-r08.json) | v3 S1 network-acquisition observer authority 候选 r08 | additive；绑定 LF-only observer/test 字节并记录完整 hermetic matrix；真实 collector conformance 仍阻断，不授权 acquisition 或 M8 执行 |
| [`m8-minimal-1k-v3-s1-network-acquisition-remediation-handoff-20260918-r05.md`](m8-minimal-1k-v3-s1-network-acquisition-remediation-handoff-20260918-r05.md) | v3 S1 network-acquisition Builder remediation r05 | additive、未独立审查；记录 closed schema/canonicalization 加固与非授权边界 |
| [`m8-minimal-1k-v3-s1-network-acquisition-builder-self-check-20260918-r01.md`](m8-minimal-1k-v3-s1-network-acquisition-builder-self-check-20260918-r01.md) | v3 S1 network-acquisition Builder 对抗自查 r01 | `FAILED_CLOSED`；declared-event validator 检查通过，但真实 collector conformance 仍阻断；不是独立 Reviewer 结论 |
| [`m8-minimal-1k-v3-s1-network-acquisition-builder-self-check-20260919-r02.md`](m8-minimal-1k-v3-s1-network-acquisition-builder-self-check-20260919-r02.md) | v3 S1 network-acquisition Builder 对抗自查 r02 | `FAILED_CLOSED`；最新 declared-event matrix 通过，但真实 collector conformance 与 checkout line-ending binding 仍阻断；不是独立 Reviewer 结论 |
| [`m8-minimal-1k-v3-s1-network-acquisition-builder-self-check-20260919-r03.md`](m8-minimal-1k-v3-s1-network-acquisition-builder-self-check-20260919-r03.md) | v3 S1 network-acquisition Builder 对抗自查 r03 | `FAILED_CLOSED`；LF binding 已通过，但真实 collector conformance 仍阻断；不是独立 Reviewer 结论 |
| [`m8-minimal-1k-v3-generator-spec.md`](m8-minimal-1k-v3-generator-spec.md) | 最小 1K v3 S1 受控输入生成规格 | 受限前置规格；不构成 binding、执行、后端选择或阶段 admission |
| [`m8-minimal-1k-v3-observer-spec.md`](m8-minimal-1k-v3-observer-spec.md) | 最小 1K v3 S1 环境观察规格 | 受限前置规格；不构成 binding、执行、后端选择或阶段 admission |
| [`schemas/m8-minimal-1k-observer-config-v3.schema.json`](schemas/m8-minimal-1k-observer-config-v3.schema.json) | v3 closed observer config schema | 绑定 synthetic implementation、四 component、collector 参数、error registry 与 redaction registry；不产生授权 |
| [`schemas/m8-minimal-1k-redaction-registry-v3.schema.json`](schemas/m8-minimal-1k-redaction-registry-v3.schema.json) | v3 digest-only redaction registry schema | closed matcher/binary policy 契约；不存 plaintext needle，不产生授权 |
| [`schemas/m8-minimal-1k-s1-config-v3.schema.json`](schemas/m8-minimal-1k-s1-config-v3.schema.json) | v3 S1 config 校验 schema | 受限机器可读前置契约；不产生授权 |
| [`schemas/m8-minimal-1k-s1-gate-v3.schema.json`](schemas/m8-minimal-1k-s1-gate-v3.schema.json) | v3 S1 gate 校验 schema | 受限机器可读前置契约；不产生授权 |
| [`templates/m8-minimal-1k-observer-config-v3.json`](templates/m8-minimal-1k-observer-config-v3.json) | v3 observer config 空白模板 | non-authorizing、non-instance；必须由未来完整 config 替代 |
| [`templates/m8-minimal-1k-redaction-registry-v3.json`](templates/m8-minimal-1k-redaction-registry-v3.json) | v3 redaction registry 空白模板 | non-authorizing、non-instance；空 pattern/allowlist 不可用于 S1 |
| [`templates/m8-minimal-1k-s1-config-v3.json`](templates/m8-minimal-1k-s1-config-v3.json) | v3 S1 config 空白模板 | non-authorizing、non-instance；不含真实机器身份或 root |
| [`templates/m8-minimal-1k-s1-gate-v3.json`](templates/m8-minimal-1k-s1-gate-v3.json) | v3 S1 gate 空白模板 | non-authorizing、non-instance；不预填成功 decision/action |
| [`templates/`](templates/) | 其余 v3 受控模板与 fixture | 仅供对应前置规格使用；不构成任何阶段证据或授权 |
| [`m8-active-execution-protocol-draft.md`](m8-active-execution-protocol-draft.md) | M8 active execution protocol `draft-0.5` | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED` |
| [`m8-active-execution-protocol-draft-0.5-authorization-20260912.md`](m8-active-execution-protocol-draft-0.5-authorization-20260912.md) | `draft-0.5` 修订授权 | 已授权并已消费的文本修订；不解除任何执行禁令 |
| [`m8-active-execution-protocol-draft-0.5-review-20260913.md`](m8-active-execution-protocol-draft-0.5-review-20260913.md) | `draft-0.5` P0 技术审查 | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`；不产生执行、准入或后端权限 |
| [`m8-active-execution-protocol-draft-0.5-returned.md`](m8-active-execution-protocol-draft-0.5-returned.md) | 被审的 `draft-0.5` 原文（171830 bytes） | 历史追溯；被审字节 `ac907b83…b9fbc9`；不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.6.md`](m8-active-execution-protocol-draft-0.6.md) | `draft-0.6` 正文（174214 bytes） | **`UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`**；未授权先修订，不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.6-authorization-20260913.md`](m8-active-execution-protocol-draft-0.6-authorization-20260913.md) | `draft-0.6` 修订**事后补正**记录 | `RETROACTIVE_CORRECTION / NOT_A_PRIOR_AUTHORIZATION`；**不是**授权，不赋予正当性 |
| [`m8-active-execution-protocol-draft-0.6-review-20260913.md`](m8-active-execution-protocol-draft-0.6-review-20260913.md) | `draft-0.6` P0 技术审查（AI 机械核验） | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`；5 项残留阻断缺陷；`AI_ASSISTED_MECHANICAL_REVIEW`，非人类独立审查 |
| [`m8-active-execution-protocol-draft-0.7.md`](m8-active-execution-protocol-draft-0.7.md) | `draft-0.7` 正文（175826 bytes） | **`UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`**；未授权先修订，不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.7-authorization-20260913.md`](m8-active-execution-protocol-draft-0.7-authorization-20260913.md) | `draft-0.7` 修订**事后补正**记录 | `RETROACTIVE_CORRECTION / NOT_A_PRIOR_AUTHORIZATION`；**不是**授权，不赋予正当性 |
| [`m8-active-execution-protocol-draft-0.7-review-20260913.md`](m8-active-execution-protocol-draft-0.7-review-20260913.md) | `draft-0.7` P0 技术审查（AI 机械核验） | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`；3 项残留阻断缺陷；`AI_ASSISTED_MECHANICAL_REVIEW`，非人类独立审查 |
| [`m8-active-execution-protocol-draft-0.8.md`](m8-active-execution-protocol-draft-0.8.md) | `draft-0.8` 正文（180033 bytes） | **`UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`**；未授权先修订，不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.8-authorization-20260913.md`](m8-active-execution-protocol-draft-0.8-authorization-20260913.md) | `draft-0.8` 修订**事后补正**记录 | `RETROACTIVE_CORRECTION / NOT_A_PRIOR_AUTHORIZATION`；**不是**授权，不赋予正当性 |
| [`m8-active-execution-protocol-draft-0.8-review-20260913.md`](m8-active-execution-protocol-draft-0.8-review-20260913.md) | `draft-0.8` P0 技术审查（AI 机械核验） | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`；3 项残留阻断 + 2 项非阻断；`AI_ASSISTED_MECHANICAL_REVIEW` |
| [`m8-active-execution-protocol-draft-0.9.md`](m8-active-execution-protocol-draft-0.9.md) | `draft-0.9` 正文（181209 bytes，纯 LF） | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`；不得 binding 或执行；2026-09-13 依 D1a 改为 LF 后摘要由 `162c9047…` 变为 `6ccebc47…`；5 条旧记录已以 `-r03` 并行重算，旧字节未动 |
| [`m8-active-execution-protocol-draft-0.10.md`](m8-active-execution-protocol-draft-0.10.md) | `draft-0.10` 正文（186129 bytes，纯 LF） | 曾到达 `P2_AUTHORIZED / BINDING_FROZEN`；2026-09-14 独立 P3 文本审计为 `REJECTED / stop`，不得 `request-p4`；`NEVER_EXECUTED` |
| [`external-gates/p0/p0-m8-active-execution-draft010-20260913-r01.json`](external-gates/p0/p0-m8-active-execution-draft010-20260913-r01.json) | `draft-0.10` P0 门禁记录（机器可读） | **`P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`** / `request-p1`；由未参与起草的独立 reviewer `justtodo123` 接受；仅技术文字，不产生执行权限 |
| [`external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1.json`](external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1.json) | `draft-0.10` P1 初版记录（历史，字节未动） | **格式无效**：`forbidden_history_ids` 沿用字符串数组且 nonce 为 32 hex；由 `-r02` 纠正，不得作为 P2 前驱 |
| [`external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1-r02.json`](external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1-r02.json) | `draft-0.10` P1 `-r02`（机器可读） | **`AUTHORIZED`** / `request-p2`；owner `justtodo123`；精确采用 13 个 `{id,ordinal}` 对象与 HEX64 nonce；仅授权 identity |
| [`m8-draft010-p1-schema-defect-20260914.md`](m8-draft010-p1-schema-defect-20260914.md) | `draft-0.10` P1/identity schema 缺陷记录 | `P1_ARTIFACT_SCHEMA_INVALID / CORRECTION_REQUIRED / P2_BLOCKED`；记录初版两项 schema 违规及 `-r02` 并行纠正 |
| [`m8-draft010-p2-materials-20260914.md`](m8-draft010-p2-materials-20260914.md) | `draft-0.10` P2 目标卷实测材料 | `P2_BLOCKED_ON_WORKSPACE_VOLUME / FINDING_RECORDED / NOT_AUTHORIZED`；D: 工作区目标暴露 `:sguard:$DATA`，C: 对照通过；不构成 P2 授权或 binding |
| [`m8-draft010-p2-parent-environment-authorization-20260914.md`](m8-draft010-p2-parent-environment-authorization-20260914.md) | `draft-0.10` P2 parent 环境选择与目录创建授权 | `AUTHORIZED_FOR_PARENT_PREPARATION / NOT_P2_AUTHORIZED`；唯一候选路径 `C:\M8-Parents\sa-m8-active-draft010-20260914-5d10f2a1`；仅授权目录创建、只读复验和 binding 候选准备 |
| [`m8-draft010-p2-parent-validation-20260914.md`](m8-draft010-p2-parent-validation-20260914.md) | `draft-0.10` C: 专用 parent 复验结果 | `PARENT_CANDIDATE_VALIDATED / P2_ISSUED`；NTFS、no-follow、relative walk、stream/ID/ACL 复验均通过；生成 P2 前后两次物理复验逐字段一致，目录为空 |
| [`external-artifacts/binding/sa-m8-active-draft010-20260914-5d10f2a1-parent.json`](external-artifacts/binding/sa-m8-active-draft010-20260914-5d10f2a1-parent.json) | `draft-0.10` parent-binding | 绑定 C: 专用 parent 的 volume/file ID、ACL、组件链与 open 不变量；canonical JSON |
| [`external-artifacts/binding/sa-m8-active-draft010-20260914-5d10f2a1-repository.json`](external-artifacts/binding/sa-m8-active-draft010-20260914-5d10f2a1-repository.json) | `draft-0.10` repository-binding | 冻结干净提交 `9e7e9f7…`、有效 identity `-r02`、experiment parent 与五种 publication purpose |
| [`external-gates/p2/p2-m8-active-execution-draft010-5d10f2a1-r01.json`](external-gates/p2/p2-m8-active-execution-draft010-5d10f2a1-r01.json) | `draft-0.10` P2 门禁记录 | **`AUTHORIZED` / `request-p3`**；owner `justtodo123`；仅冻结 binding，不授权 experiment root、依赖、执行、发布或准入 |
| [`m8-draft010-p3-independent-text-audit-20260914.md`](m8-draft010-p3-independent-text-audit-20260914.md) | `draft-0.10` 独立 P3 文本审计记录 | **`REJECTED / stop`（`FAILED / RETURNED`）**；三项阻断缺陷；不得 `request-p4`，未创建 machine P3 gate |
| [`external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1.json`](external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1.json) | `draft-0.10` 初版 identity（历史，字节未动） | **格式无效**：字符串数组 + 32 hex nonce；由 `-r02` 纠正，不得继续引用 |
| [`external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1-r02.json`](external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1-r02.json) | `draft-0.10` identity `-r02`（机器可读） | 有效：13 个 `{id,ordinal}` 对象、ordinal 0..12、HEX64 nonce；供 P1 `-r02` 与后续 P2 引用 |
| [`m8-active-execution-protocol-draft-0.9-authorization-20260913.md`](m8-active-execution-protocol-draft-0.9-authorization-20260913.md) | `draft-0.9` 修订授权 | 已发起并消费的文本修订；不产生执行、准入或后端权限 |
| [`m8-active-execution-protocol-draft-0.9-review-20260913.md`](m8-active-execution-protocol-draft-0.9-review-20260913.md) | `draft-0.9` P0 技术审查（AI 机械核验） | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`；A/B/C/D 全闭合；`AI_ASSISTED_MECHANICAL_REVIEW`，非人类独立审查 |
| [`m8-draft09-p1-materials-20260913.md`](m8-draft09-p1-materials-20260913.md) | `draft-0.9` P0/identity/P1 材料说明 | `MATERIALS_PREPARED / P0_PENDING_INDEPENDENT_REVIEW / NOT_AUTHORIZED`；**不构成任何授权** |
| [`m8-draft09-p0-r02-reviewer-worksheet-20260913.md`](m8-draft09-p0-r02-reviewer-worksheet-20260913.md) | `draft-0.9` P0 `-r02` 独立复核工作单 | `REVIEW_WORKSHEET`；**不是门禁记录、不预置结论、不构成授权**；供未参与本轮起草与核验的 reviewer 使用 |
| [`m8-draft05-unauthorized-artifacts-20260913.md`](m8-draft05-unauthorized-artifacts-20260913.md) | `draft-0.5` 未授权实验目录取证与处置 | `UNAUTHORIZED_ARTIFACTS_FOUND / CLEANUP_COMPLETE`；E 盘 7 个空目录（0 文件）与 `NEVER_EXECUTED` 冲突，已授权删除并复验无残留 |
| [`m8-draft09-p2-sguard-blocker-20260913.md`](m8-draft09-p2-sguard-blocker-20260913.md) | `draft-0.9` P2 阻断事实（工作区卷 `sguard`） | `P2_BLOCKED_ON_WORKSPACE_VOLUME`；实测 `D:` 卷目录稳定暴露 `:sguard:$DATA`，`C:` 卷目录（6 个）均通过复验；**不构成授权**；含 2026-09-13 范围更正 |
| [`m8-protocol-revision-proposal-20260913.md`](m8-protocol-revision-proposal-20260913.md) | 协议修订提案（四项遗留缺陷 A/B/C/D） | `PROPOSAL_ONLY / NOT_AN_AUTHORIZATION`；**非授权**，未经独立审查与批准前不得据以改动协议 |
| [`m8-draft011-revision-proposal-20260914.md`](m8-draft011-revision-proposal-20260914.md) | `draft-0.11` successor 修订提案（三项 P3 阻断） | `PROPOSAL_ONLY / NOT_AN_AUTHORIZATION / NOT_A_REVISION`；提案本身不创建或授权协议，不推进任何 gate |
| [`m8-active-execution-protocol-draft-0.11-authorization-20260914.md`](m8-active-execution-protocol-draft-0.11-authorization-20260914.md) | `draft-0.11` 协议修订授权记录 | `AUTHORIZED_FOR_PROTOCOL_REVISION / NOT_A_GATE / NOT_EXECUTION_AUTHORIZED`；owner 批准 A+B+C 一次性修订及六项边界 |
| [`m8-active-execution-protocol-draft-0.11.md`](m8-active-execution-protocol-draft-0.11.md) | `draft-0.11` protocol blob（191290 bytes，纯 LF） | `P3_REJECTED / stop / NEVER_EXECUTED`；SHA-256 `92e28958…d40d`；14 项阻断 finding |
| [`m8-draft011-revision-implementation-20260914.md`](m8-draft011-revision-implementation-20260914.md) | `draft-0.11` 修订实施说明 | 记录 60 行新增/10 行删除、精确字节摘要、冻结边界与未执行事项；不构成 P0/P3 结论 |
| [`m8-draft011-p0-materials-20260914.md`](m8-draft011-p0-materials-20260914.md) | `draft-0.11` P0 独立审查材料 | `MATERIALS_PREPARED / P0_REVIEW_COMPLETED / NOT_A_GATE`；reviewer `justtodo123` 与 drafting party `ai-assistant` 分离 |
| [`m8-draft011-p0-reviewer-worksheet-20260914.md`](m8-draft011-p0-reviewer-worksheet-20260914.md) | `draft-0.11` P0 reviewer 工作单 | `REVIEW_WORKSHEET / NOT_A_GATE`；独立裁定另以 canonical P0 记录落盘 |
| [`external-gates/p0/p0-m8-active-execution-draft011-20260914-r01.json`](external-gates/p0/p0-m8-active-execution-draft011-20260914-r01.json) | `draft-0.11` P0 门禁记录 | **`P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / request-p1`**；独立 reviewer `justtodo123`；仅接受技术文字 |
| [`external-artifacts/identity/sa-m8-active-draft011-20260914-940ecec4.json`](external-artifacts/identity/sa-m8-active-draft011-20260914-940ecec4.json) | `draft-0.11` 全新 experiment identity | 有效 canonical JSON；HEX64 nonce；13 个 `{id,ordinal}`；绑定 protocol SHA `92e28958…d40d` |
| [`external-gates/p1/p1-m8-active-execution-draft011-940ecec4-r01.json`](external-gates/p1/p1-m8-active-execution-draft011-940ecec4-r01.json) | `draft-0.11` P1 门禁记录 | **`AUTHORIZED / request-p2`**；owner `justtodo123`；仅授权 identity，不授权 binding、建根或执行 |
| [`m8-draft011-p2-parent-environment-authorization-20260914.md`](m8-draft011-p2-parent-environment-authorization-20260914.md) | `draft-0.11` P2 parent 环境准备授权 | `AUTHORIZED_FOR_PARENT_PREPARATION / NOT_P2_AUTHORIZED`；仅允许创建并双次只读复验全新 C: 专用 parent |
| [`m8-draft011-p2-parent-validation-20260914.md`](m8-draft011-p2-parent-validation-20260914.md) | `draft-0.11` C: 专用 parent 双次复验 | `PARENT_CANDIDATE_VALIDATED / P2_NOT_YET_ISSUED`；两次输出相同、目录为空；不是 binding 或 P2 gate |
| [`m8-draft011-p2-decision-materials-20260914.md`](m8-draft011-p2-decision-materials-20260914.md) | `draft-0.11` P2 owner 裁定材料 | owner 已接受其中精确 commit 与候选摘要；材料本身仍不是 gate |
| [`external-artifacts/binding/sa-m8-active-draft011-20260914-940ecec4-parent.json`](external-artifacts/binding/sa-m8-active-draft011-20260914-940ecec4-parent.json) | `draft-0.11` parent-binding | 全新 C: parent 的 canonical 物理身份与打开不变量；SHA-256 `3b237c6d…ff9f` |
| [`external-artifacts/binding/sa-m8-active-draft011-20260914-940ecec4-repository.json`](external-artifacts/binding/sa-m8-active-draft011-20260914-940ecec4-repository.json) | `draft-0.11` repository-binding | 冻结 clean commit `9e80d7e…d128`、identity、protocol 和五种 publication purpose；SHA-256 `91af7708…c602` |
| [`external-gates/p2/p2-m8-active-execution-draft011-940ecec4-r01.json`](external-gates/p2/p2-m8-active-execution-draft011-940ecec4-r01.json) | `draft-0.11` P2 门禁记录 | **`AUTHORIZED / request-p3`**；owner `justtodo123`；仅授权 binding，不授权建根或执行 |
| [`m8-draft011-p3-independent-audit-materials-20260914.md`](m8-draft011-p3-independent-audit-materials-20260914.md) | `draft-0.11` P3 独立审计材料 | `P3_MATERIALS_READY / INDEPENDENT_REVIEWER_REQUIRED / NOT_A_GATE`；不预置 findings 或 verdict |
| [`m8-draft011-p3-reviewer-worksheet-20260914.md`](m8-draft011-p3-reviewer-worksheet-20260914.md) | `draft-0.11` P3 reviewer 工作单 | `REVIEW_WORKSHEET / NOT_A_GATE / VERDICT_BLANK`；须由不同于 `ai-assistant` 和 `justtodo123` 的主体填写 |
| [`m8-draft011-p3-reviewer-designation-20260914.md`](m8-draft011-p3-reviewer-designation-20260914.md) | `draft-0.11` P3 reviewer 指定 | `external-reviewer-01`；指定记录仍为 `NOT_A_GATE`；最终裁定另行落盘 |
| [`m8-draft011-p3-independent-audit-20260914.md`](m8-draft011-p3-independent-audit-20260914.md) | `draft-0.11` P3 独立审计记录 | `REJECTED / stop`；14 项阻断 finding；不得 `request-p4` |
| [`m8-minimal-dry-run-route-decision-20260914.md`](m8-minimal-dry-run-route-decision-20260914.md) | M8 分层 dry-run 治理路线变更决定 | owner 批准起草最小安全协议；只覆盖 SQLite/LanceDB 1K；尚未授权执行 |
| [`m8-minimal-1k-dry-run-protocol-v1.md`](m8-minimal-1k-dry-run-protocol-v1.md) | M8 1K 最小安全 dry-run 协议 v1 | `DRAFT_FOR_S0_REVIEW`；SQLite oracle + LanceDB candidate；不授权执行 |
| [`schemas/m8-minimal-1k-artifacts-v1.schema.json`](schemas/m8-minimal-1k-artifacts-v1.schema.json) | 最小 1K artifact envelope schema | 只枚举 identity、input、run、validation、cleanup 与 decision 六类 artifact |
| [`m8-minimal-1k-s0-review-materials-20260914.md`](m8-minimal-1k-s0-review-materials-20260914.md) | 最小 1K 协议 S0 审查材料 | `INDEPENDENT_REVIEW_REQUIRED`；冻结 protocol/schema/validator 摘要；不预置裁定 |
| [`m8-minimal-1k-s0-reviewer-worksheet-20260914.md`](m8-minimal-1k-s0-reviewer-worksheet-20260914.md) | S0 reviewer 空白工作单 | `VERDICT_BLANK / NOT_A_DECISION` |
| [`m8-minimal-1k-s0-independent-audit-20260914.md`](m8-minimal-1k-s0-independent-audit-20260914.md) | 最小 1K 协议独立 S0 审计 | `PROTOCOL_REJECTED / stop`；8 项 finding；S1 未授权 |
| [`m8-minimal-1k-protocol-v2-authorization-20260914.md`](m8-minimal-1k-protocol-v2-authorization-20260914.md) | 最小协议 v2 修订授权 | 只授权闭合 `m8-s0-001`～`008`；不接受 S0、不授权执行 |
| [`m8-minimal-1k-dry-run-protocol-v2.md`](m8-minimal-1k-dry-run-protocol-v2.md) | 最小 1K dry-run 协议 v2 | `DRAFT_FOR_INDEPENDENT_S0`；闭合 workload、observer 和 evidence lifecycle |
| [`schemas/m8-minimal-1k-artifacts-v2.schema.json`](schemas/m8-minimal-1k-artifacts-v2.schema.json) | v2 六类 closed artifact schema | 以 `oneOf` 按 schema ID 关闭 payload、logical name、REF、actor 与 primitive fields |
| [`m8-minimal-1k-v2-s0-review-materials-20260914.md`](m8-minimal-1k-v2-s0-review-materials-20260914.md) | v2 独立 S0 审查材料 | 冻结 object commit 与三个摘要；不预置 reviewer/verdict |
| [`m8-minimal-1k-v2-s0-reviewer-worksheet-20260914.md`](m8-minimal-1k-v2-s0-reviewer-worksheet-20260914.md) | v2 S0 reviewer 空白工作单 | `VERDICT_BLANK / NOT_A_DECISION` |
| [`m8-minimal-1k-v2-s0-independent-audit-20260914.md`](m8-minimal-1k-v2-s0-independent-audit-20260914.md) | v2 独立 S0 技术审查 | `PROTOCOL_REJECTED / stop`；13 项 finding；S1 未授权 |
| [`m8-minimal-1k-v3-implementation-validation-authorization-20260914.md`](m8-minimal-1k-v3-implementation-validation-authorization-20260914.md) | 最小协议 v3 实现级验证路线决定与起草授权 | owner 选择协议安全边界 + 真实目录 graph validator；只授权起草与 fixture 验证，不授权 S1 或 1K 执行 |
| [`m8-minimal-1k-dry-run-protocol-v3.md`](m8-minimal-1k-dry-run-protocol-v3.md) | M8 1K 最小安全 dry-run 协议 v3 | `DRAFT_FOR_INDEPENDENT_S0`；JSON Schema 负责局部结构，graph validator 负责真实目录跨对象约束；不授权执行 |
| [`schemas/m8-minimal-1k-artifacts-v3.schema.json`](schemas/m8-minimal-1k-artifacts-v3.schema.json) | v3 单文件 envelope/REF/member/observer summary schema | 只定义局部字段形状与枚举，不声称解析引用目标 bytes |
| [`fixtures/m8-minimal-1k-v3/`](fixtures/m8-minimal-1k-v3/) | v3 validator 微型持久 fixture 集 | 5 个测试图；只验证 validator，不是 1K evidence，不产生 S1/S2 权限 |
| [`m8-minimal-1k-v3-s0-review-materials-20260914.md`](m8-minimal-1k-v3-s0-review-materials-20260914.md) | v3 独立 S0 审查材料 | 冻结 object commit、五个对象摘要与 fixture-tree-v1；不预置 reviewer 或 verdict |
| [`m8-minimal-1k-v3-s0-reviewer-worksheet-20260914.md`](m8-minimal-1k-v3-s0-reviewer-worksheet-20260914.md) | v3 独立 S0 reviewer 工作单 | `VERDICT_BLANK / NOT_A_DECISION`；由独立 reviewer 自行填写 |
| [`m8-minimal-1k-v3-s0-independent-audit-20260915.md`](m8-minimal-1k-v3-s0-independent-audit-20260915.md) | v3 独立 S0 审查裁定 | `PROTOCOL_REJECTED / stop`；fixture-tree 摘要不匹配，JSONL canonicalization 未机械强制 |
| [`m8-minimal-1k-v3-fixture-tree-correction-20260915-r01.md`](m8-minimal-1k-v3-fixture-tree-correction-20260915-r01.md) | v3 fixture-tree 摘要并行更正记录 | 两条独立读取路径证明 reviewer tree 与 reviewed commit 一致；旧材料摘要记录错误，旧拒绝不改写 |
| [`m8-minimal-1k-v3-s0-review-materials-20260915-r01.md`](m8-minimal-1k-v3-s0-review-materials-20260915-r01.md) | v3 JSONL 修订后独立 S0 复审材料 r01 | reviewed object `1ccefe1...`；5 个持久图 + 20 个 fail-closed mutation；不授权 S1 |
| [`m8-minimal-1k-v3-s0-reviewer-worksheet-20260915-r01.md`](m8-minimal-1k-v3-s0-reviewer-worksheet-20260915-r01.md) | v3 独立 S0 复审工作单 r01 | `VERDICT_BLANK / NOT_A_DECISION`；聚焦两个 v3 finding 与新增 fail-open |
| [`m8-minimal-1k-v3-s0-rereview-audit-20260915-r01.md`](m8-minimal-1k-v3-s0-rereview-audit-20260915-r01.md) | v3 独立 S0 复审裁定 r01 | `PROTOCOL_REJECTED / stop`；fixture-tree 已关闭，observer ledger 缺少最终 LF 仍可被接受 |
| [`m8-minimal-1k-v3-s0-review-materials-20260915-r02.md`](m8-minimal-1k-v3-s0-review-materials-20260915-r02.md) | v3 独立 S0 复审材料 r02 | 修复 observer ledger 非空与最终 LF；reviewed object `df78c11...`；不授权 S1 |
| [`m8-minimal-1k-v3-s0-reviewer-worksheet-20260915-r02.md`](m8-minimal-1k-v3-s0-reviewer-worksheet-20260915-r02.md) | v3 独立 S0 复审工作单 r02 | `VERDICT_BLANK / NOT_A_DECISION`；聚焦 r01 observer finding 与回归验证 |
| [`m8-minimal-1k-v3-s0-rereview-audit-20260915-r02.md`](m8-minimal-1k-v3-s0-rereview-audit-20260915-r02.md) | v3 独立 S0 复审裁定 r02 | `PROTOCOL_REJECTED / stop`；validator 摘要冻结错误，新增 harness mutation 未同步证据链 |
| [`m8-reviewer-fixer-two-stage-decision-20260915.md`](m8-reviewer-fixer-two-stage-decision-20260915.md) | M8 Reviewer-Fixer 双阶段审查模式决定 | 下一轮起 Reviewer A 可批量修复并自查但不得终审；Reviewer B 只读独立裁定；不签发 S1 |
| [`external-artifacts/m8-minimal-1k-v3-review-freeze-20260915.json`](external-artifacts/m8-minimal-1k-v3-review-freeze-20260915.json) | v3 Reviewer-Fixer canonical Git-object freeze | 冻结 candidate `8c7f598...` 的 99 个 Git objects 与 90-file fixture-tree；`NOT_REQUESTED` 不是工作区一致性声明；不构成 gate |
| [`m8-minimal-1k-v3-reviewer-fixer-remediation-20260915.md`](m8-minimal-1k-v3-reviewer-fixer-remediation-20260915.md) | v3 Reviewer A 修复、自查与重放记录 | `reviewer-fixer / remediation author` 交接记录；不是独立 S0 decision，不得签署 `PROTOCOL_ACCEPTED` |
| [`m8-minimal-1k-v3-s0-review-materials-20260915-r03.md`](m8-minimal-1k-v3-s0-review-materials-20260915-r03.md) | v3 Reviewer B 独立 S0 终审材料 r03 | reviewed object `8c7f598...`；要求从 Git objects 只读复算并裁定 r02 两项 finding；不预置 verdict，不授权 S1 |
| [`m8-minimal-1k-v3-s0-reviewer-worksheet-20260915-r03.md`](m8-minimal-1k-v3-s0-reviewer-worksheet-20260915-r03.md) | v3 Reviewer B 独立 S0 空白工作单 r03 | `VERDICT_BLANK / NOT_A_DECISION`；覆盖 package boundary、5 graphs、22 mutations、2 sensitivity proofs 与 r02 dispositions |
| [`external-artifacts/text-audits/p3-audit-20260914-external-reviewer-01.json`](external-artifacts/text-audits/p3-audit-20260914-external-reviewer-01.json) | canonical P3 text-audit | `REJECTED`；14 个 finding ID；绑定冻结 protocol 与 repository binding |
| [`external-gates/p3/p3-m8-active-execution-draft011-940ecec4-r01.json`](external-gates/p3/p3-m8-active-execution-draft011-940ecec4-r01.json) | canonical P3 gate | `REJECTED / stop`；actor `external-reviewer-01`；不得 P4 |
| [`m8-active-execution-protocol-draft-0.10-authorization-20260913.md`](m8-active-execution-protocol-draft-0.10-authorization-20260913.md) | `draft-0.10` 修订授权（A1/B1/C2a/D1a） | `AUTHORIZED / DRAFTED / P0_ACCEPTED / P1_AUTHORIZED`；只授权文本修订，P1 另行由 owner 授权创建 identity；不产生执行权限 |
| [`m8-draft010-p0-materials-20260913.md`](m8-draft010-p0-materials-20260913.md) | `draft-0.10` P0 材料说明 | `MATERIALS_PREPARED / P0_PENDING_INDEPENDENT_REVIEW / NOT_AUTHORIZED`；**不预置结论、不构成任何授权**；由起草方编写，受众为被指定的独立 reviewer `justtodo123` |
| [`m8-draft010-p0-reviewer-worksheet-20260913.md`](m8-draft010-p0-reviewer-worksheet-20260913.md) | `draft-0.10` P0 独立复核工作单 | `REVIEW_WORKSHEET`；**不是门禁记录、不预置结论、不构成授权**；含留空裁定表，供 reviewer 逐项自测后自行裁定；结果已由独立 reviewer 另行记录 |
| [`external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json`](external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json) | `draft-0.9` P0 门禁记录 `-r02`（机器可读） | **`P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`**；由未参与起草与核验的独立 reviewer 接受；仅技术文字 |
| [`external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json`](external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json) | `draft-0.9` P1 门禁记录 `-r02`（机器可读） | **`AUTHORIZED`**；前驱为 P0 `-r02`；仅授权创建 identity |
| [`external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json`](external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json) | `draft-0.9` experiment identity（机器可读） | 已授权创建（P1 `-r02`）；不构成 binding 或执行授权 |
| [`external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json`](external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json) | `draft-0.9` P0 门禁记录 `-r01`（历史，字节未动） | **`P0_NOT_ACCEPTED`**；`independence.satisfied=false`，同一主体不能自证独立性 |
| [`external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json`](external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json) | `draft-0.9` P1 门禁记录（旧，历史，字节未动） | **`NOT_AUTHORIZED`**；其前驱为 `-r01`；已被 `-r02` 取代但未删除 |
| [`m8-active-execution-protocol-draft-0.4-authorization-20260912.md`](m8-active-execution-protocol-draft-0.4-authorization-20260912.md) | `draft-0.4` 修订授权 | 已消费文本修订；不解除任何执行禁令 |
| [`m8-active-execution-protocol-draft-0.4-review-20260912.md`](m8-active-execution-protocol-draft-0.4-review-20260912.md) | `draft-0.4` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`；3 项新增阻断缺陷 |
| [`m8-active-execution-protocol-draft-0.4-returned.md`](m8-active-execution-protocol-draft-0.4-returned.md) | 被退回的 `draft-0.4` 原文 | 历史追溯；不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.3-review-20260912.md`](m8-active-execution-protocol-draft-0.3-review-20260912.md) | `draft-0.3` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED` |
| [`m8-active-execution-protocol-draft-0.3-returned.md`](m8-active-execution-protocol-draft-0.3-returned.md) | 被退回的 `draft-0.3` 原文 | 历史追溯；不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.2-review-20260911.md`](m8-active-execution-protocol-draft-0.2-review-20260911.md) | `draft-0.2` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED` |
| [`m8-active-execution-protocol-draft-0.2-returned.md`](m8-active-execution-protocol-draft-0.2-returned.md) | 被退回的 `draft-0.2` 原文 | 历史追溯；不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.1-review-20260911.md`](m8-active-execution-protocol-draft-0.1-review-20260911.md) | `draft-0.1` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED` |
| [`m8-active-execution-protocol-draft-0.1-returned.md`](m8-active-execution-protocol-draft-0.1-returned.md) | 被退回的 `draft-0.1` 原文 | 历史追溯；不得 binding 或授权 |
| [`m8-v7-admission-protocol.md`](m8-v7-admission-protocol.md) | V7 静态冻结协议 | 历史前置产物；执行尝试已 `INVALID` |
| [`m8-v8-admission-protocol.md`](m8-v8-admission-protocol.md) | V8 历史冻结协议 | 历史前置产物；执行根已 `INVALID` |
| [`m8-v9-admission-protocol.md`](m8-v9-admission-protocol.md) | V9 历史失败协议 | `PRE_FREEZE_STATIC_AUDIT_FAILED`；不可复用 |
| [`m8-v10-admission-protocol.md`](m8-v10-admission-protocol.md) | V10 历史失败协议 | `PRE_SOURCE_GOVERNANCE_INVALID`；不可复用 |
| [`m8-v11-admission-protocol.md`](m8-v11-admission-protocol.md) | V11 历史失败协议 | `PRE_SOURCE_PROVENANCE_INVALID`；不可复用 |
| [`m8-v12-admission-protocol.md`](m8-v12-admission-protocol.md) | V12 历史失败协议 | `INDEPENDENT_STATIC_AUDIT_FAILED`；不可复用 |
| [`m8-v13-admission-protocol.md`](m8-v13-admission-protocol.md) | V13 历史未绑定草案 | 已停止；不得 binding、建根或执行 |
| [`m8-v13-scale-fit-assessment-20260910.md`](m8-v13-scale-fit-assessment-20260910.md) | V13 对 100K 新目标适配评估 | `NOT_FIT_AS_COMPLETE_M8_EVIDENCE_PROTOCOL` |
| [`m8-v13-disposition-20260910.md`](m8-v13-disposition-20260910.md) | V13 草案处置 | `SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED` |
| [`m8-v7-authorization-20260908.md`](m8-v7-authorization-20260908.md) | V7 仅-smoke 待签范围记录；执行尝试已 `INVALID` | 不是 M8 准入或 v8 授权 |
| [V8 authorization](m8-v8-authorization-20260908.md) | 历史授权 | 已消费并失效；执行已 `INVALID` |
| [V9 authorization](m8-v9-authorization-20260909.md) | 未授权记录 | `PRE_FREEZE_STATIC_AUDIT_FAILED`；不可复用 |
| [V10 authorization](m8-v10-authorization-20260909.md) | 未授权记录 | `PRE_SOURCE_GOVERNANCE_INVALID`；不可复用 |
| [V11 authorization](m8-v11-authorization-20260909.md) | 历史阶段 1 授权 | 已消费；`PRE_SOURCE_PROVENANCE_INVALID` |
| [V12 authorization](m8-v12-authorization-20260909.md) | 阶段 1 授权 | 已消费；V12 已因独立审计 `FAIL` 封口 |
| [V12 independent static audit (FAIL)](m8-v12-independent-static-audit-fail-20260909.md) | 现行独立静态审计报告 | 最终 `FAIL`；四项机械门禁缺陷；V12 不可复用 |
| [V12 independent static audit (historical)](m8-v12-independent-static-audit-20260909.md) | 历史审计记录 | 初判 `PASS` 已失效，仅作历史追溯 |
| [V12 disposition](m8-v12-disposition-20260909.md) | 永久处置 | `INDEPENDENT_STATIC_AUDIT_FAILED`；不可复用 |
| [V13 protocol text audit](m8-v13-protocol-text-audit-20260910.md) | V13 协议文本设计审计 | `PASS_AFTER_REVISION / DRAFT_NOT_AUTHORIZED`；不构成执行或独立静态审计授权 |
| [M8 eleven-round governance review](m8-eleven-rounds-governance-review.md) | V1–V11 辅助治理复盘 | 仅供辅助判断；不是计划依据或授权 |

以上历史记录只在表中限定范围内具有事实证据效力，均不是当前 M8 准入。V8–V12 不得授权其对应身份或后继；
V12 独立静态审计最终为 `FAIL`，其授权仅覆盖已完成的阶段 1，从未覆盖独立审计 `PASS`、preflight 或执行。V13
历史协议文本审计的 `PASS_AFTER_REVISION / DRAFT_NOT_AUTHORIZED` 从未产生 repository binding、建根、source
freeze、独立静态审计 PASS 或执行授权；V13 已由处置记录永久标记为
`SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`，不得恢复、修订、binding、建根、授权或执行。
后续 M8 实证只能使用全新协议身份并重新取得分阶段书面授权。
2026-09-11 active execution protocol `draft-0.1` 与 `draft-0.2` 经 P0 技术审查先后退回；2026-09-12 `draft-0.3`
也经独立 P0 技术审查退回（12 项 schema/状态/证据闭合缺陷），其精确字节已封存为
[`m8-active-execution-protocol-draft-0.3-returned.md`](m8-active-execution-protocol-draft-0.3-returned.md)，只作历史追溯。
2026-09-12 负责人主动发起 `draft-0.4` 修订，并以独立记录
[`m8-active-execution-protocol-draft-0.4-authorization-20260912.md`](m8-active-execution-protocol-draft-0.4-authorization-20260912.md)
明确授权仅进行文本修订；该版本随后于同日经独立 P0 技术审查退回（3 项新增 schema/状态/证据闭合缺陷），当前状态为
`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED / UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`。该授权只解除“不得创建
`draft-0.4`”这一针对未经发起修订的禁令，不创建 experiment/protocol
执行身份，不建立 binding，不得据此创建实验根、安装依赖、生成输入、执行 benchmark、改变 M8 registry、准入 M8
或选择 LanceDB/任何后端。`draft-0.4` 已退回；2026-09-12 负责人另行主动发起 `draft-0.5` 定点修订，仅处理该 3 项
阻断缺陷，2026-09-13 经未参与起草的 independent reviewer 完成 P0 技术审查并取得
`PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`（4 项缺陷全部机械闭合，72 行映射表逐字节未变），审查记录见
[`m8-active-execution-protocol-draft-0.5-review-20260913.md`](m8-active-execution-protocol-draft-0.5-review-20260913.md)，
被审精确字节见
[`m8-active-execution-protocol-draft-0.5-returned.md`](m8-active-execution-protocol-draft-0.5-returned.md)。该 P0 接受
只表示技术文字被接受：`draft-0.5` 仍为未绑定、未授权、从未执行的历史 protocol blob，不产生任何执行权限，也不自动
产生 `draft-0.6`；后续修订仍须负责人另行发起。后续 `draft-0.10` 曾完成 P0/P1/P2 并到达 `BINDING_FROZEN`，但
2026-09-14 独立 P3 因 gate-specific role/独立性、P8 `admission_scope` 与 P3 `text_audit_ref` artifact schema 三项
阻断缺陷判定 `REJECTED / stop`（`FAILED / RETURNED`）。该链不得 `request-p4`；未创建 machine P3 gate，也未授权
建根、依赖、输入、benchmark、发布、后端选择或 M8 admission。任何修订须形成新协议版本并重新完成 P0/P1/P2，
不得就地修改冻结的 `draft-0.10` 或 repository binding。
2026-09-13 另发现并记载一项**未授权制品事实**：在推进 `draft-0.9` P2 前期工作时，于 `E:` 卷发现
`E:\sa-m8-active-draft05-parent` 与 `E:\sa-m8-active-draft05-evidence\`（含 package / normal-receipt /
nonpublication-receipt / abort-receipt / failure-receipt 五个子目录），共 **7 个目录、0 个文件**，创建时间为
2026-09-13 13:20:13。既有记录将 `draft-0.5` 记为 `UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`，与磁盘上存在实体
目录结构**不一致**；仓库内**无任何文件引用**这两个路径，也不存在创建脚本或对应授权记录，据现有证据判断为
**未经负责人事先发起而创建**。全部目录为空，故未产生任何证据工件，也不构成执行；它只是目录骨架被创建这一事实。
取证与处置记录见
[`m8-draft05-unauthorized-artifacts-20260913.md`](m8-draft05-unauthorized-artifacts-20260913.md)（`file_id` 已由
`tools/m8_parent_binding_validator.py` 以 read-only 方式核实，与未跟踪文件 `.p2-parent-identities-run.json` 逐字段相等）。
处置原则为**先记录、后清理**：该组目录曾构成 `residual-zero` 意义上需清除的残留。**清理已于 2026-09-13 完成**：
经负责人明确授权，7 个空目录按“先子后父”顺序以 `rmdir` 删除（不使用强制参数），删除后复验 `E:` 卷仅剩
`System Volume Information`、无 `sa-m8-active-draft05*` 残留，且删除前文件数为 `0`，无数据丢失。本次发现**不使**任何
既有记录失效，也**不改变** `draft-0.5` 的 `UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED` 地位；清理也不抹除
“曾未经授权创建目录”这一已发生事实。
2026-09-13 补充记载：`draft-0.6`、`draft-0.7`、`draft-0.8` 三版正文（174214 / 175826 / 180033 bytes）在形成时
**均无事先授权，也无授权、审查或 returned 字节记录落盘**，属未经负责人事先发起的自行续版，其缺陷清单只能从
修订脚本头注释推定。三版均经事后补正定为 **`UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`**，正文只作历史追溯，
不得 binding、授权或执行；对应补正记录为
[`draft-0.6`](m8-active-execution-protocol-draft-0.6-authorization-20260913.md) /
[`draft-0.7`](m8-active-execution-protocol-draft-0.7-authorization-20260913.md) /
[`draft-0.8`](m8-active-execution-protocol-draft-0.8-authorization-20260913.md)，均为
`RETROACTIVE_CORRECTION / NOT_A_PRIOR_AUTHORIZATION`，**不是**授权、不赋予正当性、不免除审查。三者对应的 P0 技术审查记录已由独立进程 `tools/m8_draft_reviewer.py` 机械核验并填定，结论均为
`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`（分别 5 / 3 / 3 项残留阻断缺陷）；该审查标记为
`AI_ASSISTED_MECHANICAL_REVIEW`，**非人类独立 reviewer 审查**，不构成技术认可。
2026-09-13 负责人另行主动发起 `draft-0.9` 定点修订，处理 `draft-0.8` 的三项推定阻断缺陷（A scope 固化、B `stream_scope`
标量、C `stream_query_source` 来源冲突）及两项装饰/不可达清理（D），授权记录见
[`m8-active-execution-protocol-draft-0.9-authorization-20260913.md`](m8-active-execution-protocol-draft-0.9-authorization-20260913.md)；
该版于 2026-09-13 经独立进程 `tools/m8_draft_reviewer.py` 机械核验后取得
`PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`（A/B/C 三项阻断缺陷与 D 项两处清理全部闭合，整条链的保留
不变量成立，72 行表逐字节未变），审查记录见
[`m8-active-execution-protocol-draft-0.9-review-20260913.md`](m8-active-execution-protocol-draft-0.9-review-20260913.md)；
该审查标记为 `AI_ASSISTED_MECHANICAL_REVIEW`，**非人类独立 reviewer 审查**，不构成技术认可之外任何授权，
也不自动产生 `draft-0.10`。
2026-09-13 另为 `draft-0.9` 准备 P0/identity/P1 机器可读材料，说明见
[`m8-draft09-p1-materials-20260913.md`](m8-draft09-p1-materials-20260913.md)。该材料集**不包含任何已成立的门禁**：
draft-0.9 的 P0 技术文字机械核验虽可复现，但核验者与起草者为同一主体，**实质性独立性未成立**，故 P0 记录以
`P0_NOT_ACCEPTED` / `independence.satisfied=false` / `allowed_next_action=stop` 落盘，其唯一后继 P1 随之落为
`NOT_AUTHORIZED` / `stop`；identity 工件已备好但未激活。该材料集曾在首次落盘时误以
`P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY` / `satisfied=true` / P1 `AUTHORIZED` 形式记为已成立，经独立性审阅
认定属**不可验证的自我证明**，已按“待复核”语义整改（experiment identity 字节未变，仍为 `5ba25bd8…`）。P0 门禁
须由**未参与本轮起草与审查的审查者**另行建立（可另发 `-r02`），在此之前 P1 不得重新签发。该材料不产生 identity
激活、binding、建根、依赖获取、source 生成、preflight、执行、证据发布、M8 准入或后端选择中的任何一项。
为降低上述独立复核的成本，已形成一份 `-r02` 复核工作单
[`m8-draft09-p0-r02-reviewer-worksheet-20260913.md`](m8-draft09-p0-r02-reviewer-worksheet-20260913.md)：它列出待审对象
的精确字节与双口径摘要（登记值 `162c9047…` 对应**工作区 CRLF**；仓库 LF 归一化为 `6ccebc47…`，差 1366 字节
恰为 1366 个 CRLF）、逐项可复跑的核验清单及其已核实行号，并显式声明本工作单由起草方编写、**不是独立证据**，
不预置结论。复核者对 draft-0.9 技术文字是否闭合、行尾登记惯例是否可接受、以及是否接受该 P0 的判断，
只能由其签署的 `-r02` 记录承载。
2026-09-13 后续：由**未参与 draft-0.9 起草、未编写其修订脚本、未产出 `-r01` 机械核验**的独立 reviewer
（`justtodo123`，仓库负责人）复核后签发
[`p0-m8-active-execution-draft09-20260913-r02.json`](external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json)，
decision 为 `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`，`independence={required:true,satisfied:true}` 由**主体分离**
满足（与 draft-0.5 先例同构）。其唯一后继
[`p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json`](external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json)
随之取得 `AUTHORIZED / request-p2`；identity 工件（字节仍为 `5ba25bd8…`）已获授权创建。
但**P2（binding）未能生成**：准备 P2 材料时实测发现，工作区所在的 `D:` 卷上的目录暴露 `:sguard:$DATA`
系统保留流（以 `NtQueryInformationFile(FileStreamInformation)` 于三个不同层级目录分别检出，连续 8 次复跑均为 FAIL），
而按 §7 与 §2.1 的规则，未列入 allowlist 的 named stream 一律 fail closed，因此 **`D:` 卷无法通过 P2**。
**该表述曾于初次落盘时被扩大为"本机不存在任何可通过 P2 的卷"，已同日更正**：对 `C:` 卷 6 个目录复跑
（`C:/Windows`、`C:/Users`、`C:/Program Files`、`C:/ProgramData`、`C:/Windows/System32`、`C:/Users/Public`）
全部 PASS，`C:/Windows` 连续 8 次稳定通过；`D:` 卷同样 8 次全部 FAIL。三卷均为 NTFS，故差异是
**卷级挂载/安全组件监视差异**（本机装有 `Kingsoft` 与 `Tencent` 组件），不是文件系统或 OS 全局特性。
但**范围更正不等于解除阻断**：关键约束在于 `allowed_system_streams` 属 `sa.m8.child-allowlist.v1.payload`、即 **P5** 的产物，
P2 时该 allowlist **尚不存在**，故 P2 校验只能 fail closed；这是链的前置关系，不是可绕过的技术障碍。
即使改用 `C:` 卷，该前置关系依然存在。因此 **P2 未生成**，`draft-0.9` 链停在 P1 `AUTHORIZED / request-p2`，Sguard 阻断评估见
[`m8-draft09-p2-sguard-blocker-20260913.md`](m8-draft09-p2-sguard-blocker-20260913.md)。该发现不使任何既有记录失效，
也不授权任何后续动作；如何处置（协议修订 / 换卷或换机 / 由负责人定 P2 是否可先行冻结）应另行决定。
**推进方式为并行落盘，非就地改写**：`-r01`、旧 P1 与 identity 三者字节均**未变动**，旧 P1 保持 `NOT_AUTHORIZED`
并靠 `record_id` 的 `-r01`/`-r02` 后缀与新版区分。两版共存的 `record_id` 版本化做法是本次为保全历史而采用，
协议本身未规定多版本共存方式，已记入材料说明 §7 建议后续修订澄清。该接受**仅限技术文字**：不授权 binding、
建根、依赖获取、source 生成、preflight、执行、证据发布、M8 准入或后端选择；链上下一道门为 P2（binding），
M8 仍为 `BLOCKED / NOT_STARTED`。

### 协议修订提案（四项遗留缺陷）

[`m8-protocol-revision-proposal-20260913.md`](m8-protocol-revision-proposal-20260913.md) 将四处遗留缺陷合并为一份待裁定的
提案，状态为 `PROPOSAL_ONLY / NOT_AN_AUTHORIZATION`：

- **A（阻断级）**：P2 在任何卷上都必然 fail closed——§7 要求查 `allowed_system_streams`，而该表属 P5 产物，
  P2 时不存在。这是阶段顺序矛盾，换卷无法解除。
- **B**：`forbidden_history_ids` 标注为 `ID`（不允许点号），但 13 个取值均含点号；修法不唯一（改标注或改取值），
  需按协议本意裁定。
- **C**：`order=value` 规定按 UTF-8 bytes 排序，与实际记录采用的数字序不一致；两侧必有一侧与文本不符。
- **D（结构级，起草提案时新发现）**：**协议本体未受行尾保护**（`text: unspecified`），
  工作区摘要 `162c9047…`（CRLF，182575 bytes）与仓库摘要 `6ccebc47…`（LF，181209 bytes）不同，
  而全部 5 条 draft-0.9 记录绑定的都是**前者**。在 LF 检出环境（Linux、或 `autocrlf=false`）下，
  协议摘要会变为 `6ccebc47…`，**这 5 条记录会全部失效**。
  `draft-0.5` 协议同样未受保护（工作区 `ac907b83…` / 仓库 `4ab35a66…`，差 1280 = CRLF 数），
  其 3 条记录也绑定工作区摘要——即**当前全部 8 条外部门禁记录的摘要都只在 Windows + `autocrlf=true` 下成立**。
  提案因此给出 D1a（只锁 `draft-0.9`，失效 5 条）与 D1b（两份都锁，失效 8 条）两个选项。这与已修复的门禁 JSON 缺陷同源，
  但影响面更大——它是整条链的摘要根。

提案建议四项合并为一次修订（每改一次协议都要重走一遍 P0/P1；分批做会重复付费），
并建议 **D 优先定案**，因为它决定协议在哪个行尾口径上被固定。

### `draft-0.10` 修订授权

负责人于 2026-09-13 明确指示推进 M8，据此形成
[`m8-active-execution-protocol-draft-0.10-authorization-20260913.md`](m8-active-execution-protocol-draft-0.10-authorization-20260913.md)，
批准提案的四项方案：

| 缺陷 | 方案 | 要点 |
| --- | --- | --- |
| A（P2 阻断） | **A1** | 为 P2 的 `parent-binding` 定义独立、闭合、可机械复验的最小 sguard 容许规则；**不**前移 P5 allowlist，**不**豁免 P2 复验 |
| B（类型标注） | **B1** | 第 168/346 行的标注 `ID` → `SCHEMA_ID`；只动标注，不动取值 |
| C（排序冲突） | **C2a** | 第 168/346 行改为 `order=key(ordinal)` 的 object 数组；**不改** `order=value` 定义（29 个字段在用） |
| D（行尾） | **D1a** | **只**锁定 `draft-0.9`/`draft-0.10` 为 LF 并重算其 5 条记录；**否决 D1b**（会重算已冻结的 `draft-0.5` 记录） |

历史修订授权记录状态为 `AUTHORIZED / DRAFTED / PENDING_P0_REVIEW`，并明确声明：它**只**授权文本修订，
**不**产生执行权限、**不**解除任何执行禁令、**不**预告 P0 会通过；`draft-0.10` 的 P0 仍须由未参与起草者
独立审查。其全部引用（行号、基数、摘要、记录计数）由 `tools/m8_verify_authorization_claims.py`（22 项）逐项核验。

### 合并时暴露并修复的行尾缺陷

将本分支合回 `master` 后，两套校验器立即报出 6 项失败，全部指向 "file is sa-json-c14n-v1 canonical"
与摘要不匹配。根因**不是合并改坏了记录**，而是**从来没有任何规则锁定门禁记录的行尾**：

- `git cat-file -p HEAD:<path>` 显示三个受影响的记录在**仓库内仍为纯 LF**（3719 / 3016 / 1001 字节），
  `git status` 干净——提交内容始终正确；
- 但 `core.autocrlf=true` 使 `checkout` 把它们写成 CRLF（各多 1 字节）；
- `.gitattributes` 当时只为 `docs/reference/document-mapping.json` 锁定了 LF，**未覆盖门禁记录与 identity 工件**；
- 因此同一份记录在不同平台/不同检出状态下会得到**不同字节**，而它们的摘要被写死在兄弟记录里。
  `draft-0.5` 的记录此次未报错，只是因为那次 checkout **碰巧**没有重写它们。

修复：把既有的 LF 锁定规则扩展到 `docs/plans/references/external-gates/**/*.json` 与
`docs/plans/references/external-artifacts/**/*.json`，与 `sa-json-c14n-v1` 对 canonical JSON 的要求一致。
验证方式是**在一个全新克隆中重建并复跑**，而非仅在本机确认：全新克隆中 8 个门禁记录的磁盘字节
逐一等于仓库字节，165 项检查（88 + 77）全数通过。

该缺陷的意义在于：门禁记录的"字节"是其证据力的载体，任何使其随环境漂移的因素都与治理前提相悖。
修复只改 `.gitattributes`，**未改动任何记录内容、摘要或门禁状态**。

招聘对照原文：[`docs/interview/StudyAssistanceAgent_requirement.md`](../../interview/StudyAssistanceAgent_requirement.md)。
该原文同样不是计划依据。
