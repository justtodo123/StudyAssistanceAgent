# 学习计划与项目执行计划（plans/）

> 本目录同时存放个人复习计划、项目工程执行计划，以及辅助计划决策的调查材料。
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
  M7 退出前置已满足，但 M8–M10 仍须分别闭合自身前置、决策与批准，当前均保持阻断
- 不把 `references/` 中的分析当作执行计划或验收真源
- 跨阶段运行时契约见 [`docs/standards/runtime-contracts.md`](../standards/runtime-contracts.md)
- M6a–M10 准入政策见 [`docs/standards/stage-admission-gates.md`](../standards/stage-admission-gates.md)，机器登记见
  [`stage-admission-gates.json`](../standards/stage-admission-gates.json)；计划或登记表不能单独批准阶段

### 计划辅助调查（`references/`）

[`references/`](references/) 用来存储**辅助计划决策的分析与事实调查**。

- 只辅助判断，**不是最终支撑来源**
- 最终支撑计划依据是 [`docs/PLAN.md`](../PLAN.md)
- 不写任务拆解、分支、验收门禁；那些要么写在 PLAN，要么在 PLAN 授权后另写 `m*-plan.md`
- 与 PLAN 冲突时，忽略本目录结论

## 当前计划

M6a 与 M6b 均为 `ADMITTED / COMPLETE`。M7 基础设施范围的实现、冻结技术证据与 correctness 收口已完成，
并于 2026-09-06 在 `m7-infrastructure-only-v1` 范围内取得独立人工完成批准，现为
`ADMITTED / COMPLETE`；技术证据本身不产生该批准。M8/M9/M10 的事实型 M7 退出前置已满足，但 M8–M10
仍因自身前置、强制决策与批准未闭合而保持 `BLOCKED / NOT_STARTED`。最终状态以 [`docs/PLAN.md`](../PLAN.md) 为准。

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
| `m8-specialized-storage-plan.md` | 阶段准入准备计划 | `BLOCKED / NOT_STARTED`；V7–V12 不可复用；V12 独立静态审计 `FAIL` |
| `m8-v7-admission-protocol.md` | V7 静态冻结协议 | 独立静态审阅曾 `PASS`；执行尝试已 `INVALID`，不得恢复或重试同一 ID |
| `m8-v8-admission-protocol.md` | V8 历史冻结协议 | 协议文本独立静态审阅曾 `PASS`；执行根已 `INVALID`，不得继续或复用 |
| `m8-v9-admission-protocol.md` | V9 历史失败协议 | `PRE_FREEZE_STATIC_AUDIT_FAILED`；身份与根永久冻结且不可复用 |
| `m8-v10-admission-protocol.md` | V10 历史失败协议 | `PRE_SOURCE_GOVERNANCE_INVALID`；身份与根不可复用，`NOT_AUTHORIZED` |
| `m8-v11-admission-protocol.md` | V11 历史失败协议 | `PRE_SOURCE_PROVENANCE_INVALID`；身份、根与 source 不可复用 |
| `m8-v12-admission-protocol.md` | V12 历史失败协议 | `INDEPENDENT_STATIC_AUDIT_FAILED`；身份、根与 source 不可复用 |
| `m9-goal-driven-planning-plan.md` | 阶段准入准备计划 | M9 目标驱动计划、mastery 与偏差；`BLOCKED / NOT_STARTED` |
| `m10-autonomous-runner-plan.md` | 阶段准入准备计划 | M10 自主 Runner、写副作用与 Harness；`BLOCKED / NOT_STARTED` |

## 计划辅助调查

| 文件 | 类型 | 状态 |
| --- | --- | --- |
| [`references/agent-alignment-analysis.md`](references/agent-alignment-analysis.md) | Agent 招聘对齐事实调查 | 辅助决策；最终依据是 PLAN.md |
| [`references/stage-advancement-analysis.md`](references/stage-advancement-analysis.md) | M6–M10 推进分析 | 辅助决策；最终依据是 PLAN.md |
| [`references/recruitment-driven-feasibility.md`](references/recruitment-driven-feasibility.md) | 招聘驱动可行性分析 | 辅助决策；结论已反映在 PLAN.md 的 M6a/M6b 拆分中 |
| [`references/m8-v7-authorization-20260908.md`](references/m8-v7-authorization-20260908.md) | V7 仅-smoke 待签范围记录 | V7 已 `INVALID`；不是 M8 准入或 v8 授权 |
| [V8 authorization](references/m8-v8-authorization-20260908.md) | 历史授权 | 已消费并失效；V8 `INVALID` |
| [V9 authorization](references/m8-v9-authorization-20260909.md) | 未授权记录 | `PRE_FREEZE_STATIC_AUDIT_FAILED`；不可复用 |
| [V10 authorization](references/m8-v10-authorization-20260909.md) | 未授权记录 | `PRE_SOURCE_GOVERNANCE_INVALID`；不可复用 |
| [V11 authorization](references/m8-v11-authorization-20260909.md) | 历史阶段 1 授权 | 已消费；`PRE_SOURCE_PROVENANCE_INVALID` |
| [V12 authorization](references/m8-v12-authorization-20260909.md) | 阶段 1 授权 | 已消费；V12 已因独立审计 `FAIL` 封口 |
| [V12 independent static audit (FAIL)](references/m8-v12-independent-static-audit-fail-20260909.md) | 现行独立静态审计报告 | 最终 `FAIL`；四项机械门禁缺陷；V12 不可复用 |
| [V12 independent static audit (historical)](references/m8-v12-independent-static-audit-20260909.md) | 历史审计记录 | 初判 `PASS` 已失效，仅作历史追溯 |
| [V12 disposition](references/m8-v12-disposition-20260909.md) | 永久处置 | `INDEPENDENT_STATIC_AUDIT_FAILED`；不可复用 |
| [M8 eleven-round governance review](references/m8-eleven-rounds-governance-review.md) | V1–V11 辅助治理复盘 | 仅供辅助判断；不是计划依据或授权 |

V8–V11 记录均不得授权其对应身份或后继。V12 独立静态审计已 `FAIL`，现以 `INDEPENDENT_STATIC_AUDIT_FAILED` 永久封口且不可复用，不得进入 preflight 或 harness；任何后继实验必须使用全新 V13 身份并取得新的书面授权。

> 后续由 `review-plan` Skill 生成的个人复习计划，继续使用 `{plan_name}-plan.md` 命名，避免与项目执行计划、调查材料混淆。
