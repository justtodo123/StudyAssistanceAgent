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

招聘对照原文：[`docs/interview/StudyAssistanceAgent_requirement.md`](../../interview/StudyAssistanceAgent_requirement.md)。
该原文同样不是计划依据。
