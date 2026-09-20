# M9 目标驱动学习计划准备计划

> 当前状态：`ADMITTED / IN_PROGRESS`；确定性 Planner 先行（只生成计划，不做采纳/进度/重规划/外部 AI）
> 前置：M7 用户源生命周期与 M8 存储契约退出证据
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)

## 1. 范围与非目标

M9 规划基于 Goal、目标日期、用户等级、掌握度与授权 Source scope 生成版本化学习计划，按正式学习事件跟踪完成、
跳过、偏差和重规划。Planner 只能提出计划和建议，不成为第二套 mastery 或会话状态权威。

本阶段不实现写工具自主循环、checkpoint/EffectLedger 或 MCP；这些属于 M10。计划文件存在不批准外部 AI 接入、
新 API、schema migration 或正式状态路径修改。

### 1.1 10K/100K 规模感知边界

M9 必须在 M8 的 100K capacity 能力上保持输入有界，但不把 100K chunks 全量送入 Planner：

- Planner 输入只允许 Goal、约束、课程/topic graph、Source 摘要、版本、授权 scope 和 mastery snapshot；
- 原始 chunk 正文只能通过受限检索按需获取，受 top-k、token、来源数、时间和成本预算控制；
- 禁止为生成计划扫描、拼接或注入全部 10K/100K chunks；
- stale、deleted、未发布或越权 Source 不得进入目录摘要、计划 grounding 或后续检索；
- PlanTask 优先引用稳定 topic/source identity；引用 chunk 时必须绑定 revision/generation，索引重建不得无故改变计划身份；
- embedding profile 或 SQLite/LanceDB 数据面切换不得改变 mastery 和计划状态语义；
- 无专业后端、无网络或无外部 AI 时，确定性目录/规则路径仍须可运行。

本节不批准 100K 真实数据、外部 AI 或专业后端；真实 10K 数据属于拟议 M11，云端 profile 属于拟议 M12。

## 2. 前置证据与继承不变量

| Prerequisite ID | 当前状态 | 准入所需证据 |
| --- | --- | --- |
| `M9-M7-EXIT` | `SATISFIED` | M7 Source lifecycle、scope/isolation、revision/delete、离线 fallback 与独立完成批准；证据见 `docs/PLAN.md`、M7 计划与 `docs/baselines.md` |
| `M9-M8-EXIT` | `SATISFIED` | 明确维持当前 SQLite/BM25 后端作为 M9 数据面基线（100K 专业化存储容量验证暂缓）；证据见 `docs/PLAN.md` 与 `docs/plans/m8-specialized-storage-plan.md` |

`StudySessionService` 与领域仓储继续掌握正式状态转换、答案评估和 mastery 写入。现有 review-plan 与
study-sessions API 保持兼容；旧 SQLite 状态可恢复；无外部 LLM 时仍有确定性路径；授权 Source 内容和用户数据
不得越界进入 provider、日志或 trace。

## 3. 强制决策

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M9-PLANNER-INPUT-SCHEMA` | `RESOLVED` | 自由文本 Goal + 可选结构化约束；Planner 只读权威仓储获取 mastery；输入有界、不随 chunk 总量线性膨胀 |
| `M9-PLAN-SCHEMA` | `RESOLVED` | 版本化 Plan/PlanRevision/PlanTask/ProgressEvent；task 按 topic 粒度稳定标识；显式采纳、不自动激活；确定性可重放 |
| `M9-MASTERY-SCHEMA` | `RESOLVED` | 粗粒度两段式（topic 的 attempt/correct/last_mastered 计数）；暂不引入连续浮点等级、置信度与时间衰减 |
| `M9-MASTERY-AUTHORITY` | `RESOLVED` | `StudySessionService`/领域仓储唯一写；Planner 建议隔离；先粗粒度 mastery；采纳由 SessionService 记录 |
| `M9-EXECUTION-DEVIATION` | `RESOLVED` | completed/skipped/overdue/replanned 事件；跳过+逾期≥3 或目标/约束变化触发重规划；parent_revision 前向链；复用 review_scheduler 的 days_overdue |
| `M9-EXTERNAL-AI` | `RESOLVED` | 默认关闭、显式 opt-in；最小披露（不送 chunk 正文/用户数据/路径/凭据）；硬超时+成本预算；确定性 fallback |
| `M9-EVALUATION` | `RESOLVED` | 先修违反=0、stale/deleted Source 进入=0、确定性可重放=100%、输入有界可证明；遵循度先定性，延迟/成本暂缓 |
| `M9-COMPATIBILITY` | `RESOLVED` | review-plan/study-session API 不变；SQLite 可恢复可迁移不回写历史；90 题不退化；关闭时回退确定性 review-plan |

所有决策都需明确默认、覆盖、输入校验、失败、隐私/兼容影响、适用阈值、证据、责任人和日期。外部模型可以生成
自由文本不等于计划 schema 已闭合；没有确定性 fallback 的候选方案保持 `OPEN`。

八项决策的设计草案（非授权、不产生 `RESOLVED`）见
[`references/m9-decision-design-draft.md`](references/m9-decision-design-draft.md)。

## 4. 准入检查与批准记录

- [x] M7/M8 数据、scope、revision 和存储契约退出证据有效；
- [x] 八项强制决策全部 `RESOLVED`，schema 与 authority 不冲突；
- [ ] 外部 AI 最小披露、失败和无 LLM fallback 可验证；
- [ ] evaluation workload、样本、阈值和人工评审口径冻结；
- [ ] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表一致；
- [ ] 用户或项目负责人完成批准。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-09-20 |
| approval_reference | User instruction: 批准 M9 确定性 Planner 先行（只生成计划，不做采纳/进度/重规划/外部 AI） |
| plan_revision | v1.0 |
| decision_set_version | m9-decision-set-v1 |

批准范围 `m9-deterministic-planner-v1`：仅 `m9.goal-plan-generation`；排除采纳、进度事件、重规划、外部 AI、
mastery 写入。`M9-M7-EXIT` 与 `M9-M8-EXIT` 均已满足，八项强制决策全部 `RESOLVED`；`ADMITTED / IN_PROGRESS`
仅覆盖确定性计划生成。

## 5. 获准后的拟实施顺序

1. 先冻结 planner input、plan、mastery 和 progress event schema；
2. 以确定性规则生成最小计划并验证现有 API/SQLite 兼容；
3. 接入只读 mastery snapshot、topic graph 和授权 Source 摘要，不复制领域写入，并验证输入规模不随 chunk 总量线性增长；
4. 接入按需受限检索，冻结 top-k/token/source/time 预算和 stale/deleted Source 拒绝行为；
5. 实现偏差事件与版本化重规划，再增加可选外部 AI adapter；
6. 在冻结任务集上比较确定性与 AI 路径，并在 1K/10K/100K capacity 元数据规模下验证计划延迟与输入预算，达标后才扩大 rollout。

拟新增 `tests/M9/` 覆盖 schema、authority、deviation/replan、provider privacy/failure、fallback 和兼容；评测必须验证
source grounding 与先修关系，而非只检查 JSON 可解析。退出条件包括正式 mastery 只有一个写入权威、计划可重放、
Planner 输入不随 chunk 总量线性膨胀、stale/deleted Source 零进入、默认学习闭环与 90 题不退化、无 LLM 路径可
运行，以及冻结评测达标。

## 6. 撤销与后续边界

mastery 定义、Source scope、计划 schema、provider 隐私政策或 evaluation workload 变化时必须 `REVOKED`。
M10 必须等待 M9 的真实退出证据，不能把 planner 建议误作自主写入授权。
