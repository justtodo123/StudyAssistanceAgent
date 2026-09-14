# 学习计划与项目执行计划（plans/）

> 本目录同时存放个人复习计划、项目工程执行计划，以及辅助分析和限定范围的历史治理记录。
> 三者定位不同，文件名和内容必须明确区分。

## 目录用途

### 个人复习计划

由 `review-plan` Skill 或 `/api/v1/review-plan` API 自动生成，按课程和目标日期安排每日学习任务。

- 命名：`{plan_name}-plan.md`
- 内容：按天分列学习任务、难度、时间估算和优先级

### 项目工程执行计划

用于拆解项目里程碑，安排代码、测试、文档、知识库和 Git 分支推进，不替代 `docs/PLAN.md` 的总路线图。

- **最终计划依据**：[`docs/PLAN.md`](../PLAN.md)（定位、里程碑、退出方向）
- 已完成：M3 / M4 / M5（MVP 最小实现）
- 当前阶段：M6a 与 M6b 均为 `ADMITTED / COMPLETE`；M6b 默认关闭的只读 preview 已完成全部 closeout 门禁与证据同步
- M6a：契约先行的兼容骨架，明确逻辑 Source 身份、快照失效/清理、Search/QA 传播边界和状态机唯一权威；
  M6b：前置、八项决策、保护基线与独立批准均已闭合，获批的独立只读原生工具调用预览已实现；
  完整自主 Runner 属于 M10
- M6b 与 M7 都以 M6a 退出证据为共同必要前置，彼此不互为前置；M7 已取得基础设施 scope admission、
  独立生产开工授权与 2026-09-06 独立人工完成批准，当前为 `ADMITTED / COMPLETE`。M8/M9/M10 的事实型
  M7 退出前置已满足；M8 八项 Decision 已 `RESOLVED`，但 M8–M12 仍须分别闭合剩余前置、阶段 Decision 与批准，
  当前均保持阻断；`draft-0.10` 曾完成 P0/P1/P2 并到达 `BINDING_FROZEN`，但 2026-09-14 独立 P3 文本审计
  因三项阻断缺陷判定 `REJECTED / stop`，不得 `request-p4`。
- 不把 `references/` 中的分析或历史治理记录当作执行计划、阶段批准或验收真源
- 跨阶段运行时契约见 [`docs/standards/runtime-contracts.md`](../standards/runtime-contracts.md)
- M6a–M12 准入政策见 [`docs/standards/stage-admission-gates.md`](../standards/stage-admission-gates.md)，机器登记见
  [`stage-admission-gates.json`](../standards/stage-admission-gates.json)；计划或登记表不能单独批准阶段

### 辅助与历史治理记录（`references/`）

[`references/`](references/) 同时存放两类材料：非正式分析/事实调查，以及不具阶段权威、但可证明其限定历史事实的
协议、授权、审计、处置和治理记录。

- 分析与建议只辅助判断，不是最终支撑来源
- 历史治理记录只在其明确范围内证明既往事实，不能扩张、续用或组合成新授权
- 最终阶段状态和路线图以 [`docs/PLAN.md`](../PLAN.md) 为准，准入政策以 standards 中的正式门禁为准
- 本目录不能单独或组合产生 Decision resolution、后端选择、M8 admission、建根、source authoring、preflight 或执行授权
- 任务拆解、分支和验收门禁应写入正式计划；与 PLAN 或正式政策冲突时，以正式权威为准

## 当前计划

M6a 与 M6b 均为 `ADMITTED / COMPLETE`。M7 基础设施范围的实现、冻结技术证据与 correctness 收口已完成，
并于 2026-09-06 在 `m7-infrastructure-only-v1` 范围内取得独立人工完成批准，现为
`ADMITTED / COMPLETE`；技术证据本身不产生该批准。M8/M9/M10 的事实型 M7 退出前置已满足；M8 八项 Decision
已 `RESOLVED`，但 `draft-0.10` 独立 P3 已 `REJECTED / stop`，不得 `request-p4`；M8–M12 均因剩余前置、
阶段 Decision 或批准未闭合而保持 `BLOCKED / NOT_STARTED`。最终状态以
[`docs/PLAN.md`](../PLAN.md) 为准。

| 文件 | 类型 | 状态 |
| --- | --- | --- |
| `m3-engineering-execution-plan.md` | 项目工程执行计划 | M3d 收口与最终回归完成，已合并到 `master`（2026-08-18） |
| `m4-knowledge-base-scale-plan.md` | 项目工程执行计划 | 三门课程各补齐至 20 篇，已进入 `master`（2026-08-18） |
| `m5-agent-session-delivery-plan.md` | 项目工程执行计划 | M5 已收口，作为 MVP 冻结（2026-08-18） |
| `m6a-harness-skeleton-plan.md` | 项目工程执行计划 | M6a-4 收口完成；`ADMITTED / COMPLETE` |
| `m6b-agent-core-plan.md` | 项目工程执行计划 | 默认关闭只读 preview 已完成 closeout；`ADMITTED / COMPLETE` |
| `m7-source-lifecycle-plan.md` | 阶段执行计划 | 基础设施范围 `ADMITTED / COMPLETE`；独立完成批准日期为 2026-09-06；Network 不在 scope 内，下游阶段不自动获批 |
| `m7-p0-corpus-governance-report.md` | P0 语料治理报告 | 82 篇文档级 mapping 已建立；Network 31 篇来源/许可未闭合，停止等待人工复核，不因 M7 完成而关闭 |
| `data-expansion-runbook.md` | 未来参考运行手册 | `DRAFT / NON-AUTHORITATIVE`；不批准数据扩展，不关闭 P0 或下游门禁 |
| `m8-specialized-storage-plan.md` | 阶段准入准备计划 | `BLOCKED / NOT_STARTED`；八项 Decision 已 `RESOLVED`；100K capacity 后端实证与 admission 未授权 |
| `m9-goal-driven-planning-plan.md` | 阶段准入准备计划 | M9 目标驱动计划、mastery 与偏差；`BLOCKED / NOT_STARTED` |
| `m10-autonomous-runner-plan.md` | 阶段准入准备计划 | M10 自主 Runner、写副作用、长任务恢复与 Harness；`BLOCKED / NOT_STARTED` |
| `m11-data-scaling-plan.md` | 阶段准入准备计划 | 10K 高质量真实 approved chunks；`BLOCKED / NOT_STARTED` |
| `m12-cloud-deployment-plan.md` | 阶段准入准备计划 | 可选云端单用户部署，本地离线仍默认；`BLOCKED / NOT_STARTED` |

## 辅助与历史治理记录

| 文件 | 类型 | 状态 |
| --- | --- | --- |
| [`references/agent-alignment-analysis.md`](references/agent-alignment-analysis.md) | Agent 招聘对齐事实调查 | 辅助决策；最终依据是 PLAN.md |
| [`references/stage-advancement-analysis.md`](references/stage-advancement-analysis.md) | M6–M10 推进分析 | 辅助决策；最终依据是 PLAN.md |
| [`references/recruitment-driven-feasibility.md`](references/recruitment-driven-feasibility.md) | 招聘驱动可行性分析 | 辅助决策；结论已反映在 PLAN.md 的 M6a/M6b 拆分中 |
| [`references/m8-m12-scope-decision-v1.md`](references/m8-m12-scope-decision-v1.md) | M8–M12 规模化范围决策 | `APPROVED / SCOPE_FROZEN`；不等于阶段 admission |
| [`references/m8-decision-closure-v1.md`](references/m8-decision-closure-v1.md) | M8 八项 Decision 批准记录 | `APPROVED / EIGHT_DECISIONS_RESOLVED`；不选择后端或授权实现 |
| [`references/m8-active-execution-protocol-draft-0.10.md`](references/m8-active-execution-protocol-draft-0.10.md) | M8 active execution protocol `draft-0.10` | 曾到达 `BINDING_FROZEN`；独立 P3 文本审计 `REJECTED / stop`；不得 `request-p4`，从未执行 |
| [`references/m8-draft010-p3-independent-text-audit-20260914.md`](references/m8-draft010-p3-independent-text-audit-20260914.md) | `draft-0.10` 独立 P3 文本审计 | `REJECTED / stop`（`FAILED / RETURNED`）；三项阻断缺陷；不得 `request-p4` |
| [`references/m8-draft011-revision-proposal-20260914.md`](references/m8-draft011-revision-proposal-20260914.md) | `draft-0.11` successor 修订提案 | `PROPOSAL_ONLY / NOT_AN_AUTHORIZATION / NOT_A_REVISION`；提案本身不推进任何 gate |
| [`references/m8-active-execution-protocol-draft-0.11-authorization-20260914.md`](references/m8-active-execution-protocol-draft-0.11-authorization-20260914.md) | `draft-0.11` 修订授权 | `AUTHORIZED_FOR_PROTOCOL_REVISION / NOT_A_GATE / NOT_EXECUTION_AUTHORIZED`；M8 仍阻断 |
| [`references/m8-active-execution-protocol-draft-0.11.md`](references/m8-active-execution-protocol-draft-0.11.md) | `draft-0.11` protocol blob | `P3 REJECTED / stop`；14 项阻断 finding；仍未授权建根或执行 |
| [`references/m8-draft011-revision-implementation-20260914.md`](references/m8-draft011-revision-implementation-20260914.md) | `draft-0.11` 实施说明 | 精确字节摘要、差异范围、冻结边界与未执行事项 |
| [`references/external-gates/p0/p0-m8-active-execution-draft011-20260914-r01.json`](references/external-gates/p0/p0-m8-active-execution-draft011-20260914-r01.json) | `draft-0.11` P0 | `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / request-p1`；独立 reviewer `justtodo123` |
| [`references/external-artifacts/identity/sa-m8-active-draft011-20260914-940ecec4.json`](references/external-artifacts/identity/sa-m8-active-draft011-20260914-940ecec4.json) | `draft-0.11` identity | 全新 canonical identity；绑定 `92e28958…d40d`；不构成 P2 或执行授权 |
| [`references/external-gates/p1/p1-m8-active-execution-draft011-940ecec4-r01.json`](references/external-gates/p1/p1-m8-active-execution-draft011-940ecec4-r01.json) | `draft-0.11` P1 | `AUTHORIZED / request-p2`；仅授权 identity，M8 仍 `BLOCKED / NOT_STARTED` |
| [`references/m8-draft011-p2-parent-environment-authorization-20260914.md`](references/m8-draft011-p2-parent-environment-authorization-20260914.md) | `draft-0.11` P2 parent 环境准备授权 | 只允许全新 C: parent 的创建与双次只读复验；不是 P2 或执行授权 |
| [`references/m8-draft011-p2-parent-validation-20260914.md`](references/m8-draft011-p2-parent-validation-20260914.md) | `draft-0.11` P2 parent 复验结果 | 新 C: parent 双次只读结果逐字段一致且目录为空；P2 仍未签发 |
| [`references/m8-draft011-p2-decision-materials-20260914.md`](references/m8-draft011-p2-decision-materials-20260914.md) | `draft-0.11` P2 owner 裁定材料 | owner 已接受精确候选；材料本身不是 gate |
| [`references/external-artifacts/binding/sa-m8-active-draft011-20260914-940ecec4-repository.json`](references/external-artifacts/binding/sa-m8-active-draft011-20260914-940ecec4-repository.json) | `draft-0.11` repository binding | clean commit、全新 parent、identity 和五种 publication purpose 已冻结 |
| [`references/external-gates/p2/p2-m8-active-execution-draft011-940ecec4-r01.json`](references/external-gates/p2/p2-m8-active-execution-draft011-940ecec4-r01.json) | `draft-0.11` P2 | `AUTHORIZED / request-p3`；仅 binding，M8 仍 `BLOCKED / NOT_STARTED` |
| [`references/m8-active-execution-protocol-draft.md`](references/m8-active-execution-protocol-draft.md) | 历史 M8 active execution protocol `draft-0.5` | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED` |
| [`references/m8-active-execution-protocol-draft-0.5-authorization-20260912.md`](references/m8-active-execution-protocol-draft-0.5-authorization-20260912.md) | `draft-0.5` 修订授权记录 | 已授权并消费的历史文本修订；不解除执行、建根或后端选择禁令 |
| [`references/m8-active-execution-protocol-draft-0.5-review-20260913.md`](references/m8-active-execution-protocol-draft-0.5-review-20260913.md) | `draft-0.5` P0 技术审查 | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`；只接受技术文字 |
| [`references/m8-active-execution-protocol-draft-0.5-returned.md`](references/m8-active-execution-protocol-draft-0.5-returned.md) | 被审的 `draft-0.5` 原文 | 171830 bytes；`ac907b83…b9fbc9`；不得 binding 或授权 |
| [`references/m8-active-execution-protocol-draft-0.4-authorization-20260912.md`](references/m8-active-execution-protocol-draft-0.4-authorization-20260912.md) | `draft-0.4` 修订授权记录 | 已消费文本修订；不解除执行、建根或后端选择禁令 |
| [`references/m8-active-execution-protocol-draft-0.4-review-20260912.md`](references/m8-active-execution-protocol-draft-0.4-review-20260912.md) | `draft-0.4` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`；3 项新增阻断缺陷 |
| [`references/m8-active-execution-protocol-draft-0.4-returned.md`](references/m8-active-execution-protocol-draft-0.4-returned.md) | 被退回的 `draft-0.4` 原文 | 历史追溯；不得 binding 或授权 |
| [`references/m8-active-execution-protocol-draft-0.3-review-20260912.md`](references/m8-active-execution-protocol-draft-0.3-review-20260912.md) | `draft-0.3` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED` |
| [`references/m8-active-execution-protocol-draft-0.3-returned.md`](references/m8-active-execution-protocol-draft-0.3-returned.md) | 被退回的 `draft-0.3` 原文 | 历史追溯；不得 binding 或授权 |
| [`references/m8-active-execution-protocol-draft-0.2-review-20260911.md`](references/m8-active-execution-protocol-draft-0.2-review-20260911.md) | `draft-0.2` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED` |
| [`references/m8-active-execution-protocol-draft-0.2-returned.md`](references/m8-active-execution-protocol-draft-0.2-returned.md) | 被退回的 `draft-0.2` 原文 | 历史追溯；不得 binding 或授权 |
| [`references/m8-active-execution-protocol-draft-0.1-review-20260911.md`](references/m8-active-execution-protocol-draft-0.1-review-20260911.md) | `draft-0.1` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED` |
| [`references/m8-active-execution-protocol-draft-0.1-returned.md`](references/m8-active-execution-protocol-draft-0.1-returned.md) | 被退回的 `draft-0.1` 原文 | 历史追溯；不得 binding 或授权 |
| [`references/m8-v7-admission-protocol.md`](references/m8-v7-admission-protocol.md) | V7 静态冻结协议 | 历史前置产物；执行尝试已 `INVALID` |
| [`references/m8-v8-admission-protocol.md`](references/m8-v8-admission-protocol.md) | V8 历史冻结协议 | 历史前置产物；执行根已 `INVALID` |
| [`references/m8-v9-admission-protocol.md`](references/m8-v9-admission-protocol.md) | V9 历史失败协议 | `PRE_FREEZE_STATIC_AUDIT_FAILED`；不可复用 |
| [`references/m8-v10-admission-protocol.md`](references/m8-v10-admission-protocol.md) | V10 历史失败协议 | `PRE_SOURCE_GOVERNANCE_INVALID`；不可复用 |
| [`references/m8-v11-admission-protocol.md`](references/m8-v11-admission-protocol.md) | V11 历史失败协议 | `PRE_SOURCE_PROVENANCE_INVALID`；不可复用 |
| [`references/m8-v12-admission-protocol.md`](references/m8-v12-admission-protocol.md) | V12 历史失败协议 | `INDEPENDENT_STATIC_AUDIT_FAILED`；不可复用 |
| [`references/m8-v13-admission-protocol.md`](references/m8-v13-admission-protocol.md) | V13 历史未绑定草案 | 已由处置记录停止；不得 binding 或执行 |
| [`references/m8-v13-scale-fit-assessment-20260910.md`](references/m8-v13-scale-fit-assessment-20260910.md) | V13 对 100K 新目标适配评估 | `NOT_FIT_AS_COMPLETE_M8_EVIDENCE_PROTOCOL` |
| [`references/m8-v13-disposition-20260910.md`](references/m8-v13-disposition-20260910.md) | V13 草案处置 | `SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED` |
| [`references/m8-v7-authorization-20260908.md`](references/m8-v7-authorization-20260908.md) | V7 仅-smoke 待签范围记录 | V7 已 `INVALID`；不是 M8 准入或 v8 授权 |
| [V8 authorization](references/m8-v8-authorization-20260908.md) | 历史授权 | 已消费并失效；V8 `INVALID` |
| [V9 authorization](references/m8-v9-authorization-20260909.md) | 未授权记录 | `PRE_FREEZE_STATIC_AUDIT_FAILED`；不可复用 |
| [V10 authorization](references/m8-v10-authorization-20260909.md) | 未授权记录 | `PRE_SOURCE_GOVERNANCE_INVALID`；不可复用 |
| [V11 authorization](references/m8-v11-authorization-20260909.md) | 历史阶段 1 授权 | 已消费；`PRE_SOURCE_PROVENANCE_INVALID` |
| [V12 authorization](references/m8-v12-authorization-20260909.md) | 阶段 1 授权 | 已消费；V12 已因独立审计 `FAIL` 封口 |
| [V12 independent static audit (FAIL)](references/m8-v12-independent-static-audit-fail-20260909.md) | 现行独立静态审计报告 | 最终 `FAIL`；四项机械门禁缺陷；V12 不可复用 |
| [V12 independent static audit (historical)](references/m8-v12-independent-static-audit-20260909.md) | 历史审计记录 | 初判 `PASS` 已失效，仅作历史追溯 |
| [V12 disposition](references/m8-v12-disposition-20260909.md) | 永久处置 | `INDEPENDENT_STATIC_AUDIT_FAILED`；不可复用 |
| [V13 protocol text audit](references/m8-v13-protocol-text-audit-20260910.md) | 协议文本审计 | `PASS_AFTER_REVISION / DRAFT_NOT_AUTHORIZED`；不是未来独立静态审计或执行授权 |
| [M8 eleven-round governance review](references/m8-eleven-rounds-governance-review.md) | V1–V11 辅助治理复盘 | 仅供辅助判断；不是计划依据或授权 |

V8–V11 记录均不得授权其对应身份或后继。V12 独立静态审计已 `FAIL`，现以 `INDEPENDENT_STATIC_AUDIT_FAILED`
永久封口且不可复用，不得进入 preflight 或 harness。V13 协议文本审计的历史
`PASS_AFTER_REVISION / DRAFT_NOT_AUTHORIZED` 只评价当时文本设计，从未产生 binding、建根或执行授权；V13 已
`SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`，不得恢复、修订、binding 或执行。任何后续 M8
实证必须使用全新协议身份并重新完成分阶段书面授权。
`draft-0.5` 的历史 P0 只接受技术文字，且从未产生 binding 或执行授权。后续 `draft-0.10` 曾完成 P0/P1/P2 并到达
`BINDING_FROZEN`，但 2026-09-14 独立 P3 因三项阻断缺陷判定 `REJECTED / stop`（`FAILED / RETURNED`）。该冻结链
不得 `request-p4`，未创建 machine P3 gate，也未授权建根、依赖、输入、benchmark、发布、后端选择或 M8 admission。
如需修订，必须形成新的协议版本并重新完成 P0/P1/P2；不得就地修改冻结的 `draft-0.10` 或 binding。

> 后续由 `review-plan` Skill 生成的个人复习计划，继续使用 `{plan_name}-plan.md` 命名，避免与项目执行计划、调查材料混淆。
