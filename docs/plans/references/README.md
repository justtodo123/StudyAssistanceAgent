# 计划辅助调查（plans/references/）

> **本目录只辅助决策，不是最终支撑来源。**
> 最终计划依据只有 [`docs/PLAN.md`](../../PLAN.md)。
> 这里的分析、对照、建议都不能当开工许可、验收门禁或技术选型真源。
> 若与 PLAN 冲突，以 PLAN 为准。

## 用途

- 对照外部要求、招聘 JD、参考架构，核对本仓库事实
- 讨论阶段顺序、可吸收项、应推迟项
- 供维护 `docs/PLAN.md` 时查阅；通过后再由 PLAN 授权去写 `m*-plan.md`

## 当前文件

| 文件 | 说明 | 地位 |
| --- | --- | --- |
| [`agent-alignment-analysis.md`](agent-alignment-analysis.md) | 对照 Agent 招聘要求与仓库现状 | 辅助调查 |
| [`stage-advancement-analysis.md`](stage-advancement-analysis.md) | M6–M10 推进顺序与招聘项映射 | 辅助调查 |
| [`recruitment-driven-feasibility.md`](recruitment-driven-feasibility.md) | 以招聘要求为唯一标准的可行性分析与阶段更新建议 | 辅助调查 |
| [`m8-v7-authorization-20260908.md`](m8-v7-authorization-20260908.md) | V7 仅-smoke 待签范围记录；执行尝试已 `INVALID` | 不是 M8 准入或 v8 授权 |
| [V8 authorization](m8-v8-authorization-20260908.md) | 历史授权 | 已消费并失效；执行已 `INVALID` |
| [V9 authorization](m8-v9-authorization-20260909.md) | 未授权记录 | `PRE_FREEZE_STATIC_AUDIT_FAILED`；不可复用 |
| [V10 authorization](m8-v10-authorization-20260909.md) | 未授权记录 | `PRE_SOURCE_GOVERNANCE_INVALID`；不可复用 |
| [V11 authorization](m8-v11-authorization-20260909.md) | 历史阶段 1 授权 | 已消费；`PRE_SOURCE_PROVENANCE_INVALID` |
| [V12 authorization](m8-v12-authorization-20260909.md) | 阶段 1 授权 | 已消费；V12 已因独立审计 `FAIL` 封口 |
| [V12 independent static audit (FAIL)](m8-v12-independent-static-audit-fail-20260909.md) | 现行独立静态审计报告 | 最终 `FAIL`；四项机械门禁缺陷；V12 不可复用 |
| [V12 independent static audit (historical)](m8-v12-independent-static-audit-20260909.md) | 历史审计记录 | 初判 `PASS` 已失效，仅作历史追溯 |
| [V12 disposition](m8-v12-disposition-20260909.md) | 永久处置 | `INDEPENDENT_STATIC_AUDIT_FAILED`；不可复用 |
| [M8 eleven-round governance review](m8-eleven-rounds-governance-review.md) | V1–V11 辅助治理复盘 | 仅供辅助判断；不是计划依据或授权 |

以上记录都不是 M8 准入。V8–V12 不得授权其对应身份或后继；V12 独立静态审计最终为 `FAIL`，其授权仅覆盖已
完成的阶段 1，从未覆盖独立审计 `PASS`、preflight 或执行。任何后继实验须由负责人另行书面授权。

招聘对照原文：[`docs/interview/StudyAssistanceAgent_requirement.md`](../../interview/StudyAssistanceAgent_requirement.md)。
该原文同样不是计划依据。
