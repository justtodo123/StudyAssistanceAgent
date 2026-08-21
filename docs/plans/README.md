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
- 当前前置：M6a-P0 crawler 已收口；M6a/M6b 已完成设计、尚未开工
- M6a：契约先行的兼容骨架；M6b：独立只读原生工具调用预览；完整自主 Runner 属于 M10
- 不把 `references/` 中的分析当作执行计划或验收真源
- 跨阶段运行时契约见 [`docs/standards/runtime-contracts.md`](../standards/runtime-contracts.md)

### 计划辅助调查（`references/`）

[`references/`](references/) 用来存储**辅助计划决策的分析与事实调查**。

- 只辅助判断，**不是最终支撑来源**
- 最终支撑计划依据是 [`docs/PLAN.md`](../PLAN.md)
- 不写任务拆解、分支、验收门禁；那些要么写在 PLAN，要么在 PLAN 授权后另写 `m*-plan.md`
- 与 PLAN 冲突时，忽略本目录结论

## 当前计划

| 文件 | 类型 | 状态 |
| --- | --- | --- |
| `m3-engineering-execution-plan.md` | 项目工程执行计划 | M3d 收口与最终回归完成，已合并到 `master`（2026-08-18） |
| `m4-knowledge-base-scale-plan.md` | 项目工程执行计划 | 三门课程各补齐至 20 篇，已进入 `master`（2026-08-18） |
| `m5-agent-session-delivery-plan.md` | 项目工程执行计划 | M5 已收口，作为 MVP 冻结（2026-08-18） |
| `m6a-harness-skeleton-plan.md` | 项目工程执行计划 | M6a 契约与兼容骨架；前置 crawler P0 已收口；设计完成，未开工 |
| `m6b-agent-core-plan.md` | 项目工程执行计划 | M6b 独立只读原生工具调用预览；设计完成，未开工（完整自主 Runner 后移 M10） |

## 计划辅助调查

| 文件 | 类型 | 状态 |
| --- | --- | --- |
| [`references/agent-alignment-analysis.md`](references/agent-alignment-analysis.md) | Agent 招聘对齐事实调查 | 辅助决策；最终依据是 PLAN.md |
| [`references/stage-advancement-analysis.md`](references/stage-advancement-analysis.md) | M6–M10 推进分析 | 辅助决策；最终依据是 PLAN.md |
| [`references/recruitment-driven-feasibility.md`](references/recruitment-driven-feasibility.md) | 招聘驱动可行性分析 | 辅助决策；结论已反映在 PLAN.md 的 M6a/M6b 拆分中 |

> 后续由 `review-plan` Skill 生成的个人复习计划，继续使用 `{plan_name}-plan.md` 命名，避免与项目执行计划、调查材料混淆。
