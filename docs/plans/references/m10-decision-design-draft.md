# M10 自主 Runner 与 Harness 对外 — 决策设计草案（非授权）

> 状态：设计草案；十一项 Decision 仍为 `OPEN`，本文件只提供准入前的人审设计输入，**不产生任何 `RESOLVED`、
> 准入、开工或批准**。最终结论以 `docs/PLAN.md`、`docs/plans/m10-autonomous-runner-plan.md` 与
> `docs/standards/stage-admission-gates.json` 为准。
>
> 本文件**不**批准、也不创建任何生产物件：无自主执行开关、无写工具、无 MCP server、无 schema migration、
> 无发布配置（M10 计划 §1）。

## 0. 设计原则（贯穿十一项决策）

1. **状态机是正式默认，Runner 是可选执行器**：`StudySessionService` 与领域仓储继续独占正式状态转换、
   答案评估与 mastery 写入。Runner 不拥有任何领域状态，只拥有**自己的** job / checkpoint / ledger 记录。
2. **写权限默认拒绝，且与只读面物理隔离**：M6b 的 `PREVIEW_TOOL_ALLOWLIST` 是只读 allowlist；写工具必须走
   **另一个** allowlist，且两者不相交。缺权限 ⇒ 拒绝，不 ⇒ 降级。
3. **每个限制必须有本地执行点**：M9 的教训是 `max_output_tokens` 曾被当作预算宣传却**没有任何运行期执行点**。
   本草案对每一项限制都标注「本地执行点在哪」，标不出来的就不写成门禁。
4. **默认关闭是恒等操作**：Runner 关闭时，`/api/v1/study-sessions` 的响应与接入前**逐字节相同**——沿用 M9
   已冻结的同一纪律（`tests/M9/test_plan_ai_adapter.py` 的「关闭时与无 adapter 逐字节相同」）。
5. **不宣称 exactly-once**：只定义**可验证**的副作用语义（幂等键 + 台账 + 事务边界 + reconcile + 补偿），
   并在报告里写明实际保证是 at-least-once 还是 at-most-once，不写「exactly-once」。

## 0.1 现状基线（起草时已核实，均带证据）

起草不能凭印象。以下是本次核对过的仓库事实，决策必须在这些约束上落地：

| 事实 | 证据 | 对决策的影响 |
| --- | --- | --- |
| 会话状态机权威 | `platform/app/study_session.py:86`（类）、`:34-39`（六个状态常量）、`:184`（`submit_answer`）、`:400`（`_log_review`） | `M10-AUTHORITY` 的边界基准 |
| 持久化层的写者**不止**状态机 | `learning_store.py:137` `save()`、`:277` `save_review()`、`:385` `save_plan()`、`:450` `save_progress_event()` | 「唯一权威」须限定为**领域**权威，不能写成「全仓唯一写者」 |
| `learning_store.py` **没有迁移机制** | 只有 `CREATE TABLE IF NOT EXISTS`（`learning_store.py:17-85`），全仓 **0 处** `PRAGMA user_version`、该文件 **0 处** `ALTER TABLE` | `M10-CHECKPOINT` 必须**先决定**迁移机制，不能默认「加张表就行」 |
| 但其它 store **有**版本化迁移先例 | `source_registry.py:438-444`（meta 表存 family+数值版本，不匹配即拒）、`source_delete.py:355` + `:1246-1332`（数值版本 + `ALTER TABLE` 路径）、`vector_store.py:326-329`（一次性 `ALTER`） | 迁移机制有**三份现成范式**可择一，不必发明 |
| 只读 allowlist 与四项注册校验 | `tool_registry.py:21`（`PREVIEW_TOOL_ALLOWLIST`）、`:223-237`（名字在 allowlist + `capability=READ` + `side_effect=NONE` + `idempotent`） | `M10-WRITE-AUTHORIZATION` 的直接模板 |
| 执行期二次授权 | `tool_registry.py:194-209`（`authorize` + 结果 `SideEffect != NONE` 拒绝）、`protocols.py:309-314` | 写路径同样需要执行期检查，不能只靠注册期 |
| 只读预算**每条都有本地执行点** | `preview_agent.py:31-52`（`PreviewLimits`）；执行点见 `:162-163`、`:224-229`、`:236`、`:252-253`、`:365-368` | 写路径预算应照此办理 |
| M9 预算**部分没有执行点**（且已诚实记录） | `plan_ai_adapter.py:102-123`；`max_output_tokens` / `max_input_tokens` 无运行期执行点（`:25-33`、`:109-112`） | 原则 3 的来源；M10 不得重犯 |
| 单轮输出硬上限 | `llm_client.py:13`（`MAX_TURN_OUTPUT_TOKENS = 1024`）、`:169-170`（发请求前硬拒） | `M10-EVALUATION` 的成本/预算口径须绑定真实闸门 |
| Preview 默认关闭且启用需 token | `config.py:136`（`SA_AGENT_PREVIEW_ENABLED`，`_strict_bool` 默认 `False`）、`:140-143`（token ≥32 字节，否则启动 fail closed） | `M10-ROLLOUT` / `M10-MCP` 的开关模板 |
| 零写入是**机械证明**的 | `tests/M6b/test_preview_read_only.py:274-334`：`iterdump` 摘要 + 三表行数 + `PRAGMA data_version` + `total_changes`，并把写方法 monkeypatch 成 `pytest.fail` | `M10-WRITE-AUTHORIZATION` 的证据标准 |
| **没有** job / EffectLedger / outbox / 补偿 / crash matrix | 全仓 `platform/app` 代码 0 命中；仅出现在 M10/M12 规划文档 | 这五类是**从零建设**，不是「接入既有」 |
| M7 **有**真实的 checkpoint/resume，但只在 Source 生命周期 | `source_registry.py:332-334`（`checkpoint_stage`/`checkpoint_digest`/`input_digest`）、`user_source_sync.py:565`/`:595`、`source_delete.py:851`/`:874`（resume barrier） | `M10-CHECKPOINT`/`M10-RECOVERY` 有**可复用范式**，但不可直接套用 |
| 单 worker 守卫已存在 | `worker_topology.py:40`（`ServiceLock`）、`:64`（`enforce_single_worker_topology`，拒绝多 worker） | `M10-ROLLOUT` 的并发前提；与「未来云端 worker」直接冲突，须显式裁定 |
| 两个错误码是**预留但未被消费** | `docs/standards/runtime-contracts.md:71-72` 标 `TOOL_PERMISSION_DENIED` / `BUDGET_EXCEEDED` 为预留；M6b preview 实际用 `terminated` envelope + 内部原因码 | `M10-MCP` 必须裁定：**消费**它们还是**修订契约**——不得让契约表继续悬空 |

## 1. `M10-AUTHORITY`

- **权威边界**：正式学习状态（session / answer / mastery / review）的唯一权威仍是 `StudySessionService` +
  领域仓储。Runner 与模型**不得**直接执行 LanceDB/Qdrant/SQLite 原生命令，只能调用受授权领域服务
  （M10 计划 §1.1）。Runner 自有状态仅限 job / checkpoint / effect ledger 三类记录。
- **冲突处理**：Runner 提议的副作用若与领域状态机当前状态冲突（例如 session 已 `completed`），由**领域服务**
  拒绝；Runner 记 `failed` 并附稳定原因码，**不盲目重试**。权威永远优先，不因 Runner 提议而回退。
- **校验**：源码级闭包断言——动态枚举 `platform/app/` 全部源文件（沿用
  `tests/M9/test_mastery_write_authority.py` 的**动态枚举**纪律，不写死名单），断言 Runner 侧模块
  **不 import `sqlite3`**、**不引用 store 的写方法**、且写 `study_sessions`/`answer_attempts` 的模块仍恰好是
  `learning_store.py`。非空性：断言扫描集合 > 0。
- **默认**：Runner 关闭；`SA_RUNNER` 未设时不存在自主执行路径。
- **阈值**：越权写入 = 0；Runner 模块对 `sqlite3` 的直接引用 = 0。

## 2. `M10-WRITE-AUTHORIZATION`

- **能力模型**：复用既有 `ToolCapability` / `SideEffect` 枚举，新增**独立**的写 allowlist
  （暂名 `RUNNER_WRITE_TOOL_ALLOWLIST`），与 `PREVIEW_TOOL_ALLOWLIST` **断言不相交**。写工具注册须通过
  「在写 allowlist 内 + `capability=WRITE` + `side_effect != NONE`」三项，与只读侧的四项校验同形。
- **作用域**：每个写工具声明所需 capability 与 scope（learner / course / source scope）。`ToolContext.permissions`
  显式携带写能力；**缺失即拒绝**（fail closed），与 `tools/common.py` 的读检查同一形态。执行期二次校验，
  不只在注册期。
- **显式确认**：任何改动正式学习状态的写，必须持有一个绑定 `(job_id, tool_name, 参数摘要)` 的确认令牌。
  **同一令牌配不同参数即拒绝**——直接复用 `source_delete.py:821` `_assert_idempotent` 的
  `REQUEST_CONFLICT` 形态。
- **撤销**：撤销记录使未决授权失效；已撤销的授权**不得**再 apply，且未决副作用必须在撤销后停止。
- **不可变审计**：每次授权写一条追加式记录（actor / scope / 参数摘要 / 裁定 / 时间戳），只增不改不删。
- **阈值**：冻结评测中越权写入尝试 = 0；确认令牌参数不匹配的重放 = 0。

## 3. `M10-CHECKPOINT`

- **先决问题（已由 owner 裁定，见 §末裁定记录）**：`learning_store.py` **没有**迁移机制，而 checkpoint 需要新表，
  故存储与迁移机制必须先定。**裁定取 (c)：新建独立 SQLite 文件**承载 job / checkpoint / ledger，完全不碰学习
  状态库。理由：它让「Runner 自有状态」与「领域权威状态」在**物理上**分开，使 `M10-AUTHORITY` 的边界可被机械
  检查，也避免动到无迁移机制的库。
- **该裁定的已知代价（必须一并承担，不得后读时当作意外）**：跨库事务不可用。因此台账的
  「状态跃迁与领域写入同事务」**不可行**，outbox + reconcile 从 §5 的可选项变成**必需项**；且
  「恢复一致性」必须靠 reconcile 收敛，不能靠事务回滚。另需为这个新库自己定义版本机制（(a) 或 (b) 的范式
  仍适用于**它**，只是不再适用于 `learning_store.py`）。
- **对象**：`job`（identity / scope / input manifest digest / 资源预算 / progress / terminal state）与
  `checkpoint`（`job_id` / 单调 `seq` / `stage` / `input_digest` / `state_digest` / 时间戳）。
- **边界与频率**：**每个副作用边界至多一次** checkpoint（propose 前 / authorize 后 / apply 前 / apply 后）。
  **不做**基于时间的 checkpoint——那会破坏可重放性。
- **resume 校验**：从 checkpoint 恢复必须**重新**校验授权与删除状态，沿用 `source_delete.py:851`
  `_resume_barrier` 的「从持久化 intent 恢复」纪律；不得因恢复而跳过授权/删除复核（M10 计划 §1.1）。
- **保留**：与 job 保留期一致；不得留存超出领域记录已有的用户内容。
- **取消**：cancel 是 job 行上的终态请求；已取消的 job 不得再 apply 任何副作用。
- **阈值**：冻结 crash 矩阵中「恢复导致重复副作用」= 0；「恢复跳过授权复核」= 0。

## 4. `M10-IDEMPOTENCY`

- **键派生**：`idempotency_key = sha256(job_id | tool_name | 参数摘要 | scope_id)`，落在唯一约束上。
- **作用域**：按 (job, tool, 参数) 唯一。
- **冲突**：同一键配**不同**参数 ⇒ 稳定错误码（如 `IDEMPOTENCY_CONFLICT`），副作用**不**应用——与
  `SOURCE_DELETE_REQUEST_CONFLICT` 同一语义。
- **重放**：返回**已记录的结果**，不重新执行。
- **并发**：唯一约束 + 事务保证并发重复收敛为一次应用。
- **保留**：≥ job 保留期，否则重放窗口内会二次应用。
- **阈值**：重复副作用 = 0（在冻结 crash 矩阵与并发用例上）。

## 5. `M10-EFFECT-LEDGER`

- **状态**：`proposed` / `authorized` / `pending` / `applied` / `failed` / `compensated`（M10 计划 §1.1）。
- **事务边界**：§3 已裁定采用**独立 SQLite 文件**，跨库事务不可用，故 outbox + reconcile 是**必需项**而非
  可选优化：台账状态跃迁与领域写入不在同一事务内，一致性由 reconcile 收敛。台账行必须在领域写入**之前**
  持久化为 `pending`，否则崩溃窗口内会出现「已 apply 但无台账行」。
- **outbox / reconcile**：`pending` 超过阈值的条目与领域状态对账；**reconcile 自身必须幂等**。
- **审计**：追加式，保留期内不删除。
- **诚实声明（强制）**：台账**不得**宣称 exactly-once。报告须写明实际保证（如「at-least-once + 幂等应用」
  或「每键 at-most-once」），并给出该保证的**证据用例名**。
- **阈值**：`applied` 无台账行 = 0；台账 `applied` 但领域无对应效果 = 0（由 reconcile 检查）。

## 6. `M10-RECOVERY`

- **crash-point matrix（必须逐点枚举，不接受「未定义 crash point 的恢复宣称」）**。至少覆盖：

  | # | crash point | 期望终态 | 允许重放 | 需补偿 |
  | --- | --- | --- | --- | --- |
  | 1 | propose 前 | 无副作用 | 是 | 否 |
  | 2 | propose 后 / authorize 前 | 无副作用 | 是 | 否 |
  | 3 | authorize 后 / apply 前 | 未决授权可撤销 | 是（须重校验） | 否 |
  | 4 | apply 事务中途 | 原子回滚 | 是 | 否 |
  | 5 | apply 后 / 台账 commit 前 | 由 reconcile 收敛 | 幂等重放 | 否 |
  | 6 | 台账 commit 后 / job checkpoint 前 | 由台账恢复 | 是 | 否 |
  | 7 | checkpoint 写入中途 | 上一 checkpoint 有效 | 是 | 否 |
  | 8 | cancel 处理中途 | 终态为 cancelled | 否 | 视已 apply 项 |
  | 9 | 任一步骤磁盘不足 | fail closed，无半发布 generation | 否（修复后另行） | 否 |
  | 10 | provider 中途超时 | 回退，无半成品 | 是 | 否 |

- **不可补偿失败**：无法补偿的副作用 ⇒ job 进入**不可重试**终态并要求人工介入，**必须**留痕，绝不静默重试。
- **poison effect**：同一 effect 连续失败达阈值（默认 3）后标记 poison，job 停止而非无限重试。
- **阈值**：矩阵每点「重复副作用 = 0」且「半发布 generation = 0」；矩阵覆盖率 = 100%（10/10 点各有用例）。

## 7. `M10-EVALUATION`

- **维度**：任务成功率、工具/参数合法率、**越权率**、终止原因分布、恢复成功率、cost、p95、发布阈值。
- **两臂（沿用 M9 已冻结的分工，不重新发明）**：arm A 确定性 stub、**CI 门禁**；arm B 真实 provider、
  显式 opt-in、**非门禁**、任何退出条件与登记表**不得**依赖它。
- **原则 3 的强制适用**：每个被写成门禁的指标都必须给出**本地执行点**。给不出执行点的指标只能进报告，
  **不得**进门禁——M9 的 `max_output_tokens` 就是这么被纠正的（M9 计划 §4.4）。
- **阈值（owner 已裁定取 0 容忍组）**：越权率 = 0；重复副作用 = 0；半发布 generation = 0；
  crash 矩阵覆盖 = 100%；状态机默认路径可回滚且旧 session 可恢复；默认 90 题不退化。与 M9 的
  「先修违反 = 0 / stale Source 进入 = 0」同一纪律。**注意**：0 容忍组里每一项都必须先能**本地执行**，
  否则按原则 3 只能进报告、不得进门禁。
- **范围限制**：本评测**只覆盖 M10 自主路径**，不是全项目评测口径冻结；遵循度类指标仍为定性。
- **证据**：冻结任务集文件、报告（含机器可读的 `enforced_locally` / `not_enforced_locally`，沿用 M9 报告形态）、
  用例名清单。

## 8. `M10-MCP`

- **最小面**：首个发布**不含写工具**；工具集是 `PREVIEW_TOOL_ALLOWLIST` 的子集或等价的只读集。
- **传输**：本地 **stdio only**，不监听端口——与 local-first 默认一致，也避免新开网络面。
- **认证**：token ≥32 UTF-8 字节、缺失即 fail closed，沿用 `config.py:140-143` 的 preview 形态。
- **schema / 错误映射（owner 已裁定：M10 消费它们）**：`runtime-contracts.md:71-72` 两个**预留但未被消费**的
  错误码（`TOOL_PERMISSION_DENIED` / `BUDGET_EXCEEDED`）由 M10 的写路径与 MCP 面**真实返回**，使契约表与
  实现对齐。**边界**：本裁定只要求 M10 自己的面消费它们；M6b preview 的既有表达（`terminated` envelope +
  内部原因码）**不因此改写**——它是已交付且已冻结的行为，改它属另一个决定。
- **conformance**：不得暴露 LanceDB/Qdrant/SQLite 原生能力；错误码稳定且不泄露路径/凭据。
- **阈值**：conformance 用例全绿；未授权工具调用 = 0；响应中宿主路径出现 = 0。

## 9. `M10-MANIFEST`

- **身份**：knowledge-pack manifest 的 identity / 版本 / 完整性 / 能力 / 来源 / 兼容 / 签名政策。
- **字节稳定性**：manifest digest 必须**可复现**。本仓已有为此付出的代价——`.gitattributes` 为
  `document-mapping.json`、M8 gate 记录等逐条 pin `text eol=lf`，因为 CRLF checkout 会改变校验方读到的字节。
  manifest 若进 digest，**必须**先冻结换行与序列化规范（可复用 `sa-json-c14n-v1`）。
- **兼容**：manifest 变化**不得**改变 mastery 与计划状态语义（M9 计划 §1.1 的同一约束）。
- **与既有身份的关系**：必须绑定 M7 的 generation 身份，不得另造一套并行的 source identity。
- **阈值**：同一输入两次生成 manifest digest 逐字节相同；manifest 变更后旧 session/plan 仍可读。

## 10. `M10-OFFLINE-DEFAULT`

- **正式默认**：状态机。`SA_RUNNER` 未设或为假时，`/api/v1/study-sessions` 的行为与接入前**逐字节相同**
  （原则 4）。
- **无 LLM**：无外部 AI 时**不存在**自主路径；**不得**静默降级成一条能力更弱的**写**路径。回退只能回到状态机。
- **隔离**：Runner 失败（超时、provider 错误、崩溃）**不得**污染 session/plan 状态；失败必须收敛为稳定的
  终止原因码，且不产生半成品。
- **阈值**：关闭时响应逐字节相同（含 `session_id` 派生）；Runner 各类失败后库状态与失败前逐字节相同
  （沿用 M6b 的 `iterdump` 摘要 + `data_version` + `total_changes` 机械证明）。

## 11. `M10-ROLLOUT`

- **默认**：关闭。启用条件、环境/用户范围、观测字段、kill switch、回滚、迁移兼容。
- **kill switch**：**在每个副作用边界**检查，不只在 job 开始时检查一次——否则长任务无法被叫停。
- **并发前提（owner 已裁定：维持单 worker）**：`worker_topology.py:40/64` 的 `enforce_single_worker_topology`
  继续生效，M10 **不**放宽它；多 worker 与云端 worker 重试**留给 M12**。直接后果：crash 矩阵只需覆盖**单进程**
  crash（§6 的 10 点即按此口径），幂等与台账无需处理跨 worker 并发。**同时更新 M10 计划 §1.1 的口径**——
  该节「未来云端 worker 重试必须进入冻结 crash/recovery matrix」一句在本裁定下**只作为 M12 的输入**，
  不构成本阶段的矩阵要求。
- **回滚**：关闭 Runner 后，全部既有 session/plan/review 数据仍可读，状态机路径功能完整。
- **阈值**：kill switch 在矩阵每个边界点生效（用例覆盖 100%）；关闭后回归套件全绿。

## 采纳顺序建议

先 `AUTHORITY` → `WRITE-AUTHORIZATION`（边界与权限是其余九项的前提），再 `CHECKPOINT`（含迁移机制裁定）
→ `IDEMPOTENCY` → `EFFECT-LEDGER` → `RECOVERY`（副作用语义四件套，彼此耦合），随后 `OFFLINE-DEFAULT`
与 `MANIFEST`（兼容性前提），最后 `EVALUATION` → `MCP` → `ROLLOUT`。

顺序**不构成**准入或开工授权。十一项全部 `RESOLVED` 且 owner 填写批准记录之前，M10 保持
`BLOCKED / NOT_STARTED`。

## owner 裁定记录（2026-09-22）

起草时列出的四项开放点已由 owner 逐项裁定。裁定**只关闭草案内的开放点**，**不**使任何一项 Decision 变成
`RESOLVED`——十一项仍需完整的政策/默认/覆盖/校验/失败/隐私/阈值/证据/责任人/日期，并经 owner 单独批准。

| 开放点 | 裁定 | 落地位置 |
| --- | --- | --- |
| 存储与迁移机制 | 新建**独立 SQLite 文件**承载 job / checkpoint / ledger，不碰学习状态库 | §3、§5 |
| 两个预留错误码 | M10 **消费** `TOOL_PERMISSION_DENIED` / `BUDGET_EXCEEDED`（不改写 M6b 既有表达） | §8 |
| worker 拓扑 | **维持单 worker**，多 worker 与云端重试留给 M12 | §11 |
| 评测数值阈值 | 接受 **0 容忍组**（越权 0 / 重复副作用 0 / 半发布 generation 0 / 矩阵覆盖 100% / 90 题不退化） | §7 |

| 裁定字段 | 值 |
| --- | --- |
| decided_by | justtodo123 |
| decided_at | 2026-09-22 |
| decision_reference | User instruction: 就本草案末尾四项开放点逐项裁定，四项均取草案给出的推荐项——存储机制取「独立 SQLite 文件」、预留错误码取「M10 消费它们」、worker 拓扑取「维持单 worker」、评测阈值取「0 容忍组」 |

**这四项裁定不做什么**（防止被后读高估）：不产生任何 `RESOLVED`；不改变 `stage-admission-gates.json`（十一项
仍 `OPEN`）；不批准 M10 准入或开工；不创建任何生产物件（无写工具、无 MCP server、无 schema migration、
无执行开关）；M10 保持 `BLOCKED / NOT_STARTED`。
