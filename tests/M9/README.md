# M9 目标驱动学习计划测试

验证确定性 Planner 的完整链路：Goal + 约束 + 只读复习与三个只读投影（**mastery** / 授权 **Source 摘要** /
**先修关系 topic graph**）→ 版本化、可重放的分日计划，以及采纳 / 进度事件 / 偏差触发的版本化重规划。
三个投影都是纯读（不写领域状态、不构建 chunk 索引、不读原始 chunk 正文，不引入外部 AI）。
`test_plan_grounding.py` 覆盖其后的**受限检索接缝**：Planner 按需取回有界 grounding 证据，
并在接缝上独立交叉校验用户源可用性。

## 文件

| 文件 | 覆盖 |
|------|------|
| `test_goal_planner.py` | 确定性生成、版本、计划身份、输入有界与只读守卫 |
| `test_plan_lifecycle.py` | 采纳、进度事件、重规划与 revision 前向链 |
| `test_deviation_signals.py` | 跳过 + 逾期偏差信号、阈值触发与 `parent_revision_id` |
| `test_deviation_consumption.py` | 未消费阈值、`deviation_ledger` 消费台账与重复调用幂等 |
| `test_mastery_projection.py` | 跨会话答题聚合、知识条目 file 路径映射（三分支，与 `_log_review` 同序）、不可映射排除、真只读守卫、有界输入、计划身份派生输入摘要、存量计划兼容 |
| `test_source_summary_projection.py` | 「可用」规则 7 态 × 有无 generation 矩阵、隐藏态排除、恰好一次 bulk 读、只读守卫、懒装配不建库、principal 守卫、有界输入、与 Planner 的接缝 |
| `test_topic_graph_projection.py` | frontmatter 行内列表解析（含块状形式被静默丢弃的陷阱）、同目录兄弟边解析与嵌套目录不跨目录连边、丢弃规则、环与环下游诊断、零写入与每条目恰好解析一次、空图等价于无图的逐字节不变量、真图拓扑序与 `violations` 三种成因、置顶闭包交互、60 条语料数据完整性 |
| `test_plan_grounding.py` | 受限检索接缝：四类预算各自生效与放宽被拒、stale/deleted/未发布/未就绪/禁用/待删源在接缝上被丢弃（真 registry + 真投影端到端）、无 principal 与投影不可用时的 fail-closed、畸形 provenance、真只读守卫、证据有界 |
| `test_plan_identity.py` | 计划身份按 principal 分隔（带标签段、7 例参数化、`goal` 伪造 `\|principal=` 段不碰撞）与反 churn 逐字节护栏（对合成任务对比旧公式，不依赖语料）、进度事件不跨 principal 污染、`summary` 落记录、replan 还原 principal 与源范围、principal 不出现在任何读取路径、源码级单点剥离护栏 |

## 六条关键约定

- **聚合身份是知识条目的 file 路径**，不是 `study_sessions.topic` 那样的自由文本。解析顺序与
  `StudySessionService._log_review` 一致（检索出处 → 出题出处 → `knowledge/{course}/{topic}.md` 回退）；
  不可映射或条目不存在的会话被**排除而非猜测**。
- **计划身份含派生输入摘要**：`plan_id` 覆盖 goal / 目标日期 / 课程 / 每日学时 / 约束，以及最终任务列表的
  `task_id`/`reviewed`/mastery 序列。因此复习或 mastery 状态变化会得到**新的** `plan_id`；旧计划记录只读保留，
  仍可 `GET` / `adopt` / `progress` / `replan`，只是不再被重新生成命中。
- **Source 摘要里的集合叫 `usable`，不叫 `authorized`**：规则是「已发布 generation 且状态为 READY / DEGRADED」，
  规范来源是 `source_offline.py` 内联的同一判断。它**严格小于** M7 的
  `IsolationSnapshot.authorized_source_ids`（后者含 REGISTERED / SYNCING / DISABLED）。未发布、未就绪、
  禁用、待删、已删的源都不进入摘要；隐藏态由 `list_sources` 的 WHERE 子句构造性排除，
  因此投影**无法报告**被排除的计数——该证据由本目录的测试提供。
- **先修边解析为「同目录兄弟文件」**：`prerequisites: [a]` 指 `knowledge/{course}/a.md`，**不**按课程解析。
  `knowledge/interview/co/` 是嵌套目录且全树有多个 basename 撞名，按课程解析会把先修静默连到面经条目上。
  **只支持行内方括号形式**——块状 YAML 会被解析器静默丢成空列表，故数据完整性用例按**原始文件**断言。
  计划侧 `summary.prerequisites.violations` 只从**最终顺序**算出，因此「同一 `plan_id` ⇒ 相同 `summary`」
  这条不变量结构上成立；`unorderable()` 是**图级**环诊断，刻意不进计划 `summary`。
- **grounding 不进计划身份、也不进 `summary`**：证据依赖索引 generation，折进 `plan_id` 会让每次
  reindex 都 churn 身份，折进 `summary` 会破坏「同一 `plan_id` ⇒ 相同 `summary`」。它是**已装配、
  生产休眠**的服务层只读接缝——principal 按设计是内部边界，公共请求体不接受 caller-selected
  `principal_id`，故不经 HTTP 路由，`STALE_DELETED_SOURCE_ENTRY_ZERO` 只在**接缝**上取证。
  预算按 **UTF-8 字节**计不按 token 计（本仓无本地 tokenizer，沿用 M6b 的 `max_prompt_bytes` 口径）；
  `timeout_seconds` 是**事后截止检查**，不是硬中断（`recall` 无取消通道）。
- **principal 进身份键与记录 payload，但不进响应体**：`_plan_id` 追加一段**带标签**的 principal
  （`...|principal={id}`）且**仅在非 None 时**追加——`event_id` 是 `(plan_id, task_id, event)` 的哈希、
  不含 principal 成分，不同 principal 撞同一 `plan_id` 会让后者的 `completed` 被 `INSERT OR IGNORE`
  静默去重、把前者的任务标成完成；只在非 None 时追加则 `principal_id=None` 的身份**逐字节不变**，
  既有计划 id 不 churn。principal 是**内部记录键**，`get` / `adopt` / `replan` 的每个返回点都过单点
  函数 `_public_plan`，故「不进响应体」是结构保证而非逐点过滤；`GoalPlanRequest` / `GoalPlanResponse`
  都没有该字段，因此也不进 OpenAPI schema。

## 命令

```bash
./platform/.venv/Scripts/python -m pytest tests/M9 -v
./platform/.venv/Scripts/python -m pytest tests/M9 -m m9 -q
```

自 2026-09-21 起本套件已纳入 `.github/workflows/offline-ci.yml` 的阶段测试步骤。
