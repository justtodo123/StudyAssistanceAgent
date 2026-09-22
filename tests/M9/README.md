# M9 目标驱动学习计划测试

验证确定性 Planner 的完整链路：Goal + 约束 + 四个只读投影（**复习历史** / **mastery** / 授权 **Source 摘要** /
**先修关系 topic graph**）→ 版本化、可重放的分日计划，以及采纳 / 进度事件 / 偏差触发的版本化重规划。
四个投影都是纯读（不写领域状态、不构建 chunk 索引、不读原始 chunk 正文），
且都以**活对象**注入，使计划身份与排序随答题 / 复习状态刷新。
`test_plan_grounding.py` 覆盖其后的**受限检索接缝**：Planner 按需取回有界 grounding 证据，
并在接缝上独立交叉校验用户源可用性。`test_day_distribution.py` 覆盖分日的**每日容量**不变量
（窗口是起点、容量才是硬约束）。

`test_plan_ai_adapter.py` / `test_plan_ai_benchmark.py` 覆盖 **`m9.external-ai`（默认关闭）**：可选外部 AI
排序路径，以及冻结工作负载上确定性与 AI 两条路径的比较。自 v1.5 起 `test_plan_ai_benchmark.py` 还承载
**冻结预算矩阵**（证明预算被**强制执行**，而非测量性能）；真实 provider 读数在
`test_plan_ai_provider_smoke.py`，显式 opt-in、**非门禁**、本次未运行。

`test_mastery_write_authority.py` 是 **M9 退出条件的证据**，不是能力：它把「正式 mastery 只有一个写入权威」
从当前事实钉成可测不变量。**它不新增写路径** —— 恰恰相反，`m9.mastery-write` 之所以在 `approval_scope.excluded`
里，就是为了禁止 M9 成为第二套 mastery 权威（M9 计划 §1/§2）。

## 文件

| 文件 | 覆盖 |
|------|------|
| `test_goal_planner.py` | 确定性生成、版本、计划身份、输入有界与只读守卫 |
| `test_day_distribution.py` | **每日容量是硬约束**：任何一天的任务分钟数不得超出当日容量（唯一例外是「单条任务本身就装不下」且该天**恰好只装一个**任务）、追加的天与窗口内的天同受容量约束且日期连续、窗口够用时不追加、`total_days`/`total_hours` 与逐日明细自洽、`total_minutes` 的构成口径、空任务集仍是 1 个空天、分日确定性 |
| `test_plan_lifecycle.py` | 采纳、进度事件、重规划与 revision 前向链 |
| `test_deviation_signals.py` | 跳过 + 逾期偏差信号、阈值触发与 `parent_revision_id` |
| `test_deviation_consumption.py` | 未消费阈值、`deviation_ledger` 消费台账与重复调用幂等 |
| `test_mastery_projection.py` | 跨会话答题聚合、知识条目 file 路径映射（三分支，与 `_log_review` 同序）、不可映射排除、真只读守卫、有界输入、计划身份派生输入摘要、存量计划兼容 |
| `test_source_summary_projection.py` | 「可用」规则 7 态 × 有无 generation 矩阵、隐藏态排除、恰好一次 bulk 读、只读守卫、懒装配不建库、principal 守卫、有界输入、与 Planner 的接缝 |
| `test_topic_graph_projection.py` | frontmatter 行内列表解析（含块状形式被静默丢弃的陷阱）、同目录兄弟边解析与嵌套目录不跨目录连边、丢弃规则、环与环下游诊断、零写入与每条目恰好解析一次、空图等价于无图的逐字节不变量、真图拓扑序与 `violations` 三种成因、置顶闭包交互、60 条语料数据完整性 |
| `test_plan_grounding.py` | 受限检索接缝：四类预算各自生效与放宽被拒、stale/deleted/未发布/未就绪/禁用/待删源在接缝上被丢弃（真 registry + 真投影端到端）、无 principal 与投影不可用时的 fail-closed、畸形 provenance、真只读守卫、证据有界 |
| `test_plan_identity.py` | 计划身份按 principal 分隔（带标签段、7 例参数化、`goal` 伪造 `\|principal=` 段不碰撞）与反 churn 逐字节护栏（对合成任务对比旧公式，不依赖语料）、进度事件不跨 principal 污染、`summary` 落记录、replan 还原 principal 与源范围、principal 不出现在任何读取路径、源码级单点剥离护栏 |
| `test_review_history_projection.py` | 复习历史活投影：只返回成员资格（不交 payload）、刻意不缓存、恰好一次批量读、无写面（import 级 AST 扫描 + 连接级 `total_changes` 审计 + 库快照比对）、**构造 Planner 之后落的复习必须可见**（旧代码下必失败的缺陷证明）、快照参数仍冻结、`plan_id` 随复习变化、`main.py` 装配护栏 |
| `test_plan_ai_adapter.py` | 外部 AI 排序路径（默认关闭）：最小披露的**字段级**白名单（prompt 里没有路径 / chunk 正文 / `principal_id` / per-file mastery）、预算只允许收紧与非正数被拒、每一类失败收敛为 `order=None` + 稳定原因码、关闭时与无 adapter 逐字节相同（含 `plan_id`）、失败不落库（写入口全 fail + 连接级审计 + 库快照比对）、先修闸门与必选置顶**非空转**（同 adapter 同提案：注入图被拒、不注入图被采纳；置顶断言传递闭包块是前缀）、**单轮 output 预算**（驱动**真实桥** `build_anthropic_proposer` 证明默认预算能走到 provider 且传给 `create_turn` 的是单轮值、单轮 ≤ 累积 ≤ 客户端硬上限、单轮 > 累积被拒、`SA_PLAN_AI_MAX_TURN_OUTPUT_TOKENS` 真被读且只能收紧） |
| `test_plan_ai_benchmark.py` | 冻结工作负载上两条路径的比较（`m9_benchmark`，1K 语料）：语料**只读复用** M7 生成器且 chunk 数**量出来**（10 vs 1000，源真的发布过且可检索）、输入有界（两种规模下 prompt 字节数与条目数逐字相同）、两条路径先修违反均为 0、确定性可重放、合法相邻对换被采纳而非法对换被拒（两条臂都非空转）、报告独占创建 + 双摘要。**另含 v1.5 冻结预算矩阵**（6 场景 × 稳定原因码）：驱动**真实** `build_anthropic_proposer(client_factory=…)` 接缝（用 `proposer=` 注入会绕过 `_run_blocking`，那样断言 deadline 是假证据），断言 `prompt` 预算在调用 provider **之前**返回（provider 调用数为 0）、`cost` 预算在收到**合法**置换时仍丢弃它、`deadline` 被强制；并钉住两处价目表常量不漂移、`_estimate_cost` 在冻结表上可复现、stub 延迟分布上界绑在冻结 `deadline_seconds` 之下。报告 `m9-plan-ai-evaluation-v2` 含机器可读的 `enforced_locally` / `not_enforced_locally` |
| `test_plan_ai_provider_smoke.py` | **真实 provider** 读数（`online` + `M9_PROVIDER_SMOKE` skip 门控，**非门禁**）：复用 `test_plan_ai_benchmark.py` 的 `_WORKLOAD`（import，不重新声明，防两臂漂到不同 workload），5 workload × 2 轮 = 10 个固定 case，走生产 `build_anthropic_proposer`（默认 `client_factory=AnthropicLLMClient`）；**只记脱敏字段**（无 prompt 正文、无 provider 原文、无路径、无异常文本）；花费上限默认 $1.00、**事后累加**（故最坏为 cap + 单次调用，报告里写明）、报告先落盘再断言（判红也保留读数）。**本次未运行**，真实 provider 延迟 / 成本 / 失败模式**仍未验证** |
| `test_mastery_write_authority.py` | M9 退出条件「正式 mastery 只有一个写入权威」的**结构性证据**：动态枚举 `platform/app/` 全部源文件（当前 60 个）后断言写 `study_sessions`/`answer_attempts` 的模块**恰好**是 `learning_store.py`、M9 模块连**导入**写权威都做不到（AST 闭包断言，非子串匹配）、mastery 派生只有一处定义；含检测器正反对照与「表名确实是 store 建的表」的上游契约钉桩 |

## 十二条关键约定

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
- **只读输入必须是活对象，不能是构造时求值的快照**：`main.py` 原先把
  `review_history=_learning_store.all_reviews()` 传给 Planner，那是**构造时求值一次**的快照，于是同一进程内
  新记录的复习永不反映到计划上——`reviewed` 标志、排序优先级，以及经 `_derived_digest` 参与 `plan_id` 的
  身份全部停在进程启动时刻；而紧邻的 mastery 投影刻意传活对象（注释原文「使计划身份与排序随答题状态刷新」），
  两条同源只读输入一个冻结一个实时。现由 `ReviewHistoryProjection` 补齐，形状对齐既有三个只读投影，
  每轮 `generate` 只重读一次（生成途中落库的新复习不能让不同任务看到两个快照）；未注入投影时回落到构造时的
  快照，故既有调用方行为逐字节不变。**该守卫必须钉在 `main.py` 的装配上**——本目录其余用例直接构造
  `GoalPlannerService`，把装配改回快照它们仍然全绿，而缺陷原本就长在装配上。

- **`hours_per_day` 是每日容量（预算），`target_date` 是视野而非硬期限**：容量是**硬约束**，视野不是
  ——计划**允许超过窗口**（`review_plan.py` 的「剩余任务追加到最后一天（如果超出天数）」是唯一的正面声明，
  M9 逐字继承），但**不允许**任何一天超出 `hours_per_day × 60`（唯一声明的每日上界是 `+ 10` 分钟复习缓冲）。
  已证实缺陷的回归：排不完的任务曾被一次性倾倒进一个不设上限的「第 `total_days + 1` 天」——默认请求下
  该天 114 个任务 / 3890 分钟，而当日可用仅 110 分钟（最高超出 92 倍）。现为**逐天追加**，追加的天受
  同一容量约束。**残留**：`and day_tasks` 守卫保证每天第一个任务必被放入，故单条任务超容量时该天仍会
  超出——保证是「每天**至多一个**任务造成超出」，不是「绝不超出」，`test_day_distribution.py` 把它钉成
  可见事实。**与 `review_plan.py` 刻意分叉**：该服务有同一处缺陷，但 `platform/tests/test_review_plan.py`
  的 `actual_days <= max_days + 1` 明确容忍它且该套件按约定冻结不动，故修正只落在 `goal_planner.py`。
- **外部 AI 路径默认关闭，且「最小披露」是结构性的**：载荷由 `PlanAIRequest` / `PlanAITaskSummary`
  两个冻结 dataclass 定义，`PlanAITaskSummary` **没有 `file` 字段**，`task_id` 是 `sha256(file)[:16]`
  （不透明、不含路径），mastery 只送**聚合计数**，`principal_id` 根本不在载荷里——故「不送路径」不是靠
  渲染时过滤，而是类型上就没有那个字段可送。**AI 只提出排序，采纳由既有确定性校验器裁决**：置换校验在
  Planner 侧**再做一遍**（adapter 是可注入接缝，只在接缝一侧校验等于没校验），先修违反即整体回退，
  必选主题置顶由确定性侧**重新施加**。任何超时 / 超预算 / 非法输出都返回**入参本身**（逐字回退），
  不落库、不改 `revision_id`，故不产生半成品计划。**不新增公开路由**：该路径经既有
  `POST /api/v1/plans` 可达。Planner **不 import** adapter 模块（鸭子类型），以保持其源码级护栏
  （不含 `llm_client` / `content` / `split_headings` 字样）成立。
- **1K 比较是窄口径证据，不是容量声明**：`test_plan_ai_benchmark.py` 只跑 **1K**（M7 生成器，
  `sources=1, documents=100, units=10`），证明的是**输入有界**——送往 AI 的 prompt 不随语料规模增长。
  M9 既不存储也不索引 1K chunks，故这不是容量通过。**10K/100K 逐字记为 M8（`BLOCKED`）/ M11（拟议）
  依赖**；CI 里 AI 路径由**确定性 stub** 驱动，真实 provider 的延迟 / 成本 / 失败模式**未在 CI 验证**。
- **v1.5 解冻的是「预算被强制执行」，不是性能**：`M9-EVALUATION` 的延迟/成本维度自 plan_revision v1.5 起
  为冻结评测，范围**仅限 M9 外部 AI 路径**（不是全项目评测声明）。CI 臂（门禁）证明四件事——`prompt`
  预算在调用 provider **之前**返回、`answer` 预算收到回复即判、`cost` 预算是**硬上限**（合法置换照样丢弃）、
  `deadline` 由 `_run_blocking` 强制。**但 stub 下没有任何性能读数**：延迟是桥接开销，成本由脚本化 usage
  算出。另有三项预算**不在本地执行**（`max_input_tokens` 本地无 tokenizer、`model_timeout_seconds` 与
  `max_output_tokens` 仅 provider 侧），报告里的 `not_enforced_locally` 是这条的机器可读证据；
  `deadline` 守卫**放弃线程而非取消它**。
- **output token 预算是两个字段，不是一个**：`max_output_tokens` 是**累积**预算、只送 provider；
  `max_turn_output_tokens` 是**单轮**预算，它才是传给 `create_turn` 的 `max_tokens`，而 `llm_client`
  硬拒大于 `MAX_TURN_OUTPUT_TOKENS`(1024) 的值，故这道闸门**在本地**。已证实缺陷的回归：累积值曾被
  直接当单轮值传下去，于是**默认配置下**每次调用都在发出任何 HTTP 请求之前抛 `ValueError`，被回退路径
  收敛成 `provider_unavailable`——整条外部 AI 路径静默失效，而既有测试全绿（它们一律经 `proposer=`
  注入，绕过那个调用点）。故 `test_plan_ai_adapter.py` 的「单轮 output 预算」节**驱动真实桥**
  （`build_anthropic_proposer`），并有一条配置层用例钉住 `SA_PLAN_AI_MAX_TURN_OUTPUT_TOKENS` 真的被读、
  且只能收紧。
- **真实 provider 读数必须显式 opt-in，且不得成为门禁**：`test_plan_ai_provider_smoke.py` 的 skip 门控是
  **承重**的——本目录在 CI 阶段测试步骤内，而该步骤**不排除** `online` 标记，故「默认不跑」完全靠
  `M9_PROVIDER_SMOKE` 未设时的 `pytest.skip`。该文件**绝不**触碰 workflow：
  `tests/regression/test_ci_contract.py` 明文禁止 `ANTHROPIC_API_KEY` / `SA_PLAN_AI_TOKEN` /
  `SA_PLAN_AI_ENABLED` 出现在其中。**任何门禁、退出条件与登记表都不得依赖它**。
- **mastery 写入只有一个权威，且这条不变量靠动态枚举守住**：权威是 `StudySessionService` + 领域仓储，
  唯一写 `study_sessions`/`answer_attempts` 的模块是 `learning_store.py`。既有测试只**逐模块**证明
  「我没写」；`test_mastery_write_authority.py` 补的是**闭包**——扫描面是 `platform/app/` 下**全部**
  `*.py`（动态枚举，当前 60 个），所以「新加一个写者」无处可藏，不需要谁记得更新名单。
  M9 的 8 个模块与写权威**导入不可达**（AST 判定，不是子串匹配——注释里提一句不算）。
  **`m9.mastery-write` 仍在 `approval_scope.excluded`**：M9 计划 §1/§2 明令 Planner 不得成为第二套
  mastery 权威，本文件只证明**不存在第二套权威**，不证明 M9 获得写能力。

## 命令

```bash
./platform/.venv/Scripts/python -m pytest tests/M9 -v
./platform/.venv/Scripts/python -m pytest tests/M9 -m m9 -q
./platform/.venv/Scripts/python -m pytest tests/M9 -m m9_benchmark -q   # 冻结 1K 比较 + 预算矩阵（已排除在阶段步骤外）

# 真实 provider 读数：显式 opt-in、会花真钱、非门禁（默认 skip）
SA_PLAN_AI_TOKEN=... M9_PROVIDER_SMOKE=1 \
M9_PROVIDER_SMOKE_RUN_ID=<id> M9_PROVIDER_SMOKE_REPORT=/path/m9-plan-ai-provider-smoke-<id>.json \
./platform/.venv/Scripts/python -m pytest tests/M9/test_plan_ai_provider_smoke.py -q -m online
```

自 2026-09-21 起本套件已纳入 `.github/workflows/offline-ci.yml` 的阶段测试步骤；`m9_benchmark` 另有独立
CI 步骤（含报告独占创建与上传）。真实 provider 臂**不在 CI 内**，且不得被加进去。
