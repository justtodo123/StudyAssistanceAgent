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

| 文件 | 说明 | 地位 |
| --- | --- | --- |
| [`agent-alignment-analysis.md`](agent-alignment-analysis.md) | 对照 Agent 招聘要求与仓库现状 | 辅助调查 |
| [`stage-advancement-analysis.md`](stage-advancement-analysis.md) | M6–M10 推进顺序与招聘项映射 | 辅助调查 |
| [`recruitment-driven-feasibility.md`](recruitment-driven-feasibility.md) | 以招聘要求为唯一标准的可行性分析与阶段更新建议 | 辅助调查 |
| [`m8-m12-scope-decision-v1.md`](m8-m12-scope-decision-v1.md) | M8–M12 规模化范围决策 | `APPROVED / SCOPE_FROZEN`；不等于阶段 admission |
| [`m8-decision-closure-v1.md`](m8-decision-closure-v1.md) | M8 八项 Decision 批准记录 | `APPROVED / EIGHT_DECISIONS_RESOLVED`；不选择后端或授权实现 |
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
| [`m8-active-execution-protocol-draft-0.10.md`](m8-active-execution-protocol-draft-0.10.md) | `draft-0.10` 正文（186129 bytes，纯 LF） | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`；依授权记录落地 A1/B1/C2a/D1a 四项文本修订；**P0 已由独立 reviewer 接受（仅技术文字）**，仍不得 binding 或执行 |
| [`external-gates/p0/p0-m8-active-execution-draft010-20260913-r01.json`](external-gates/p0/p0-m8-active-execution-draft010-20260913-r01.json) | `draft-0.10` P0 门禁记录（机器可读） | **`P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`** / `request-p1`；由未参与起草的独立 reviewer `justtodo123` 接受；仅技术文字，不产生执行权限 |
| [`external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1.json`](external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1.json) | `draft-0.10` P1 门禁记录（机器可读） | **`AUTHORIZED`** / `request-p2`；owner `justtodo123`；仅授权创建一个新的 experiment identity，不授权 binding、依赖、执行、发布或准入 |
| [`m8-draft010-p2-materials-20260914.md`](m8-draft010-p2-materials-20260914.md) | `draft-0.10` P2 目标卷实测材料 | `P2_BLOCKED_ON_WORKSPACE_VOLUME / FINDING_RECORDED / NOT_AUTHORIZED`；D: 工作区目标暴露 `:sguard:$DATA`，C: 对照通过；不构成 P2 授权或 binding |
| [`external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1.json`](external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1.json) | `draft-0.10` experiment identity（机器可读） | 由 P1 授权创建；绑定 `draft-0.10` 当前摘要；不构成 repository binding 或执行授权 |
| [`m8-active-execution-protocol-draft-0.9-authorization-20260913.md`](m8-active-execution-protocol-draft-0.9-authorization-20260913.md) | `draft-0.9` 修订授权 | 已发起并消费的文本修订；不产生执行、准入或后端权限 |
| [`m8-active-execution-protocol-draft-0.9-review-20260913.md`](m8-active-execution-protocol-draft-0.9-review-20260913.md) | `draft-0.9` P0 技术审查（AI 机械核验） | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`；A/B/C/D 全闭合；`AI_ASSISTED_MECHANICAL_REVIEW`，非人类独立审查 |
| [`m8-draft09-p1-materials-20260913.md`](m8-draft09-p1-materials-20260913.md) | `draft-0.9` P0/identity/P1 材料说明 | `MATERIALS_PREPARED / P0_PENDING_INDEPENDENT_REVIEW / NOT_AUTHORIZED`；**不构成任何授权** |
| [`m8-draft09-p0-r02-reviewer-worksheet-20260913.md`](m8-draft09-p0-r02-reviewer-worksheet-20260913.md) | `draft-0.9` P0 `-r02` 独立复核工作单 | `REVIEW_WORKSHEET`；**不是门禁记录、不预置结论、不构成授权**；供未参与本轮起草与核验的 reviewer 使用 |
| [`m8-draft05-unauthorized-artifacts-20260913.md`](m8-draft05-unauthorized-artifacts-20260913.md) | `draft-0.5` 未授权实验目录取证与处置 | `UNAUTHORIZED_ARTIFACTS_FOUND / CLEANUP_COMPLETE`；E 盘 7 个空目录（0 文件）与 `NEVER_EXECUTED` 冲突，已授权删除并复验无残留 |
| [`m8-draft09-p2-sguard-blocker-20260913.md`](m8-draft09-p2-sguard-blocker-20260913.md) | `draft-0.9` P2 阻断事实（工作区卷 `sguard`） | `P2_BLOCKED_ON_WORKSPACE_VOLUME`；实测 `D:` 卷目录稳定暴露 `:sguard:$DATA`，`C:` 卷目录（6 个）均通过复验；**不构成授权**；含 2026-09-13 范围更正 |
| [`m8-protocol-revision-proposal-20260913.md`](m8-protocol-revision-proposal-20260913.md) | 协议修订提案（四项遗留缺陷 A/B/C/D） | `PROPOSAL_ONLY / NOT_AN_AUTHORIZATION`；**非授权**，未经独立审查与批准前不得据以改动协议 |
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
只表示技术文字被接受：`draft-0.5` 仍为未绑定、未授权、从未执行的 protocol blob，不产生任何执行权限，也不自动
产生 `draft-0.6`；后续修订仍须负责人另行发起。
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
