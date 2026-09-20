# M9 目标驱动学习计划 — 决策设计草案（非授权）

> 状态：设计草案；八项 Decision 仍为 `OPEN`，本文件只提供准入前的人审设计输入，不产生任何 `RESOLVED`、
> 准入、开工或批准。最终结论以 `docs/PLAN.md`、`docs/plans/m9-goal-driven-planning-plan.md` 与
> `docs/standards/stage-admission-gates.json` 为准。

## 0. 设计原则（贯穿八项决策）

1. **Planner 只提建议，不写权威**：`StudySessionService` 与领域仓储继续独占正式状态转换、答案评估与
   mastery 写入。Planner 输出的是 Plan 文档，采纳与否由既有学习闭环与用户显式决定。
2. **确定性优先，LLM 可选**：无外部 AI、无网络、无专业后端时，确定性目录/规则路径必须可运行且结果可复现；
   外部 AI 只是同一 schema 的增强 adapter，不是正确性的来源。
3. **输入有界，不随 chunk 总量线性膨胀**：Planner 输入只含 Goal、约束、topic graph、Source 摘要、版本、
   授权 scope 与 mastery snapshot；原始 chunk 正文只经受限检索按需获取。
4. **身份稳定，删除可追踪**：PlanTask 引用稳定 topic/source identity；引用 chunk 时绑定 revision/generation；
   stale/deleted/越权 Source 零进入。

## 1. `M9-PLANNER-INPUT-SCHEMA`

- **版本化请求体**：`schema_version`、`goal`（自由文本 + 可选的显式目标课程/范围）、`target_date`、
  `constraints`（每日可用学时、必须覆盖的 topic、禁止 topic）、`user_level`、`mastery_snapshot`、
  `authorized_source_scope`（稳定 source identity 集合）、`topic_graph_ref`。
- **校验与拒绝**：goal 非空且长度有界；target_date 为合法未来日期；每日学时在既定区间；authorized scope
  必须与 Source registry 的 owner/revision/generation 一致，stale/deleted/未发布 Source 一律拒绝。
- **默认值**：无 target_date 时按现有 review-plan 语义回退 14 天；无 user_level 时回退默认等级。
- **允许覆盖**：只能收紧（更少 source、更短 horizon、更严约束），不能放宽到越权 Source。

## 2. `M9-PLAN-SCHEMA`

- **对象**：`Plan`（版本化根）、`PlanRevision`（不可变历史）、`PlanTask`（可执行单元）、`ProgressEvent`
  （完成/跳过/过期/偏差）。
- **身份**：`plan_id`、`revision_id`（单调递增）、`task_id`（稳定，与 topic/source identity 绑定，索引重建
  不得无故改变）。
- **状态转换**：Plan 由 Planner 生成 → 用户/闭环采纳为 active → ProgressEvent 驱动偏差 → 触发 replan 生成
  新 PlanRevision。旧 revision 只读保留。
- **可重放**：给定相同 input + snapshot，确定性路径产出相同 PlanRevision（相同 seed 与排序规则）。

## 3. `M9-MASTERY-SCHEMA`

- **量表**：离散等级（如 0–4 或 入门/熟练/掌握）而非连续浮点为主，避免与检索相似度混用。
- **字段**：`level`、`confidence`、`evidence`（来源会话/答题/复习记录引用）、`updated_at`、`decay` 规则。
- **来源**：只由 `StudySessionService`/领域仓储写入；Planner 只能读 snapshot。
- **缺失与迁移**：旧 SQLite 无 mastery 时按默认等级冷启动；schema 升级必须向前兼容（新增字段有默认值，
  不破坏既有记录）。

## 4. `M9-MASTERY-AUTHORITY`

- **唯一写入口**：`StudySessionService` + 领域仓储。Planner 的 mastery 建议进入隔离的 `suggestion` 通道，
  由闭环决定是否采纳；绝不直接回写权威 mastery。
- **冲突处理**：Planner 建议与权威不一致时，权威为准并记录偏差；建议只作审计材料。
- **验证**：任何把 Planner 建议写成权威状态的路径都在测试中 fail closed。

## 5. `M9-EXECUTION-DEVIATION`

- **事件类型**：`completed`、`skipped`、`overdue`、`replanned`。
- **偏差指标**：完成率、跳过率、逾期天数、与目标日期的漂移。
- **重规划触发**：跳过/逾期累计超过阈值，或目标日期/约束变化，触发生成新 PlanRevision。
- **版本关系**：新 revision 明确 `parent_revision_id`，形成不可变前向链；并发事件按时间戳 + 幂等键合并。

## 6. `M9-EXTERNAL-AI`

- **provider/model**：显式 opt-in；默认关闭。
- **发送字段最小披露**：仅 goal、约束、topic 摘要、mastery 摘要与授权 scope 标识，不送原始 chunk 正文、
  用户数据、绝对路径、凭据。
- **隐私/保留**：不落 provider 侧日志/trace；本地只留脱敏审计。
- **timeout/cost**：硬超时、token/成本预算；失败即回退确定性路径，不产生半成品 Plan。
- **确定性 fallback**：无 LLM 时产出规则化 Plan，schema 与正确性要求不变。

## 7. `M9-EVALUATION`

- **维度**：计划有效性（先修关系不违反）、source grounding（PlanTask 只引用授权/未删除 Source）、遵循度
  （计划可被闭环执行）、偏差处理、可重放性、延迟、成本。
- **workload**：固定任务集（覆盖不同课程/等级/约束），比较确定性路径与可选 AI 路径。
- **阈值**：先修关系违反 = 0；stale/deleted Source 进入 = 0；确定性路径可重放 = 100%；输入规模不随 chunk
  总量线性增长必须可证明。

## 8. `M9-COMPATIBILITY`

- **既有 API**：`/api/v1/review-plan`、`/api/v1/study-sessions` 保持不变；M9 是增量扩展，不破坏现有响应。
- **旧 SQLite 数据**：可恢复、可迁移、不回写历史记录。
- **默认工作台与 M0–M5**：学习闭环不退化；90 题评测不退化。
- **回滚**：M9 关闭或撤销时，回退到确定性 review-plan 路径。

## 采纳顺序建议

先冻结 `PLANNER-INPUT-SCHEMA` → `PLAN-SCHEMA` → `MASTERY-SCHEMA`/`MASTERY-AUTHORITY`，再
`EXECUTION-DEVIATION` → `COMPATIBILITY`，最后 `EXTERNAL-AI` 与 `EVALUATION`。顺序不构成准入或开工授权。
