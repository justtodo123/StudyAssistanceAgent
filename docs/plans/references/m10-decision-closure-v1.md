# M10 决策闭合记录 v1（提案）

> 状态：**提案（非授权）**。M10 十一项 Decision 在 `stage-admission-gates.json` 中**仍为 `OPEN`**；
> 本文件逐批记录 owner 的裁定与批准。**批准前不得据此修改登记表**，也不得创建任何生产物件
> （无写工具、无 MCP server、无 schema migration、无执行开关）。
>
> 设计输入见 [`m10-decision-design-draft.md`](m10-decision-design-draft.md)；本文件是它的**闭合面**——
> 把草案内容落成可直接写进登记表 `value` 的令牌串与十项必备内容。

## 0. 用法与推进方式

- **分批推进**（owner 2026-09-22 裁定）：① `AUTHORITY` + `WRITE-AUTHORIZATION`；② `CHECKPOINT` +
  `IDEMPOTENCY` + `EFFECT-LEDGER` + `RECOVERY`；③ `OFFLINE-DEFAULT` + `MANIFEST` + `EVALUATION` +
  `MCP` + `ROLLOUT`。
- 每批在本文件追加一节，并在 §批准记录 追加一行。
- **只有 owner 批准过的批次**，其 Decision 才可由 `OPEN` 改为 `RESOLVED`。本文件本身**不产生** `RESOLVED`。
- 未列入本文件的内容不构成承诺；与 `docs/PLAN.md` 或 M10 计划冲突时以后者为准。

## 1. 批次 ①：`M10-AUTHORITY` 与 `M10-WRITE-AUTHORIZATION`

### 1.1 `M10-AUTHORITY`

**拟定 `value`**（可直接落登记表）：

```text
STATE_MACHINE_IS_THE_FORMAL_DEFAULT__RUNNER_OWNS_ONLY_JOB_CHECKPOINT_LEDGER_STATE__NO_DIRECT_SQL_OR_NATIVE_BACKEND_ACCESS__DOMAIN_SERVICE_REJECTS_CONFLICTING_EFFECTS
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 正式学习状态（session / answer / mastery / review）的唯一权威仍是 `StudySessionService`（`platform/app/study_session.py:86`）与领域仓储 `SqliteLearningStore`（`platform/app/learning_store.py:106`）。Runner 自有状态**仅限** job / checkpoint / effect ledger，且按存储裁定放在**独立 SQLite 文件**。Runner 与模型不得直接执行 LanceDB / Qdrant / SQLite 原生命令，只能调用受授权领域服务。 |
| **权威的准确表述（必须写准）** | `learning_store.py` 的写者**不止**状态机：`save()` `:137`、`save_review()` `:277`、`save_plan()` `:385`、`save_progress_event()` `:450`，分别由 `StudySessionService` / `ReviewSchedulerService` / `PlanLifecycleService` 调用。故唯一性在**领域服务层**成立，**不是**「全仓唯一写者」。写成后者即为事实错误。 |
| **默认与覆盖** | 默认：Runner 关闭（`SA_RUNNER` 未设）时**不存在**自主执行路径。覆盖只能收紧（更小 scope、更少工具、更低预算），不能放宽到未授权 scope。 |
| **校验与失败** | 源码级闭包断言，**动态枚举** `platform/app/` 全部源文件（沿用 `tests/M9/test_mastery_write_authority.py` 的动态枚举纪律，不写死名单）：(a) 写 `study_sessions` / `answer_attempts` 的模块**恰好**是 `learning_store.py`；(b) Runner 侧模块**不 import `sqlite3`**；(c) Runner 侧模块不引用 store 的写方法名。非空性：断言扫描集合 > 0。冲突时由**领域服务**拒绝，Runner 记 `failed` + 稳定原因码，**不盲目重试**。 |
| **隐私** | Runner 自有库不得留存超出领域记录已有的用户内容；ledger / checkpoint 不得写宿主路径或凭据。 |
| **兼容** | 旧 SQLite 学习状态库**完全不被 Runner 触碰**——物理分离使其可机械验证；不 bump `SCHEMA_VERSION`；状态机路径与 M0–M5 API 不变。 |
| **量化阈值** | 越权写入 = 0；Runner 侧模块对 `sqlite3` 的直接引用 = 0；`platform/app/` 中写 `study_sessions`/`answer_attempts` 的模块数 = 1。 |
| **证据** | 源码级断言 + 运行期用例（拟 `tests/M10/test_authority_boundary.py`）；关闭时响应逐字节相同（沿用 M9「默认关闭是恒等操作」的形态）。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 1.2 `M10-WRITE-AUTHORIZATION`

**拟定 `value`**：

```text
SEPARATE_WRITE_ALLOWLIST_DISJOINT_FROM_PREVIEW__CAPABILITY_AND_SCOPE_REQUIRED_DENY_BY_DEFAULT__CONFIRMATION_TOKEN_BOUND_TO_JOB_TOOL_ARG_DIGEST__REVOCATION_INVALIDATES_PENDING__APPEND_ONLY_AUDIT
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 写工具走**独立** allowlist（暂名 `RUNNER_WRITE_TOOL_ALLOWLIST`），与 `PREVIEW_TOOL_ALLOWLIST`（`platform/app/tool_registry.py:21`）**断言不相交**。注册期三项校验：在写 allowlist 内 + `capability=WRITE` + `side_effect != NONE`，与只读侧的四项校验（`tool_registry.py:223-237`）同形。**执行期二次校验**，照 `tool_registry.py:194-209`，不只靠注册期。 |
| **作用域** | 每个写工具声明所需 capability 与 scope（learner / course / source scope）。`ToolContext.permissions` 显式携带写能力；**缺失即拒绝**（fail closed），与 `tools/common.py` 的读检查同形态。 |
| **显式确认** | 任何改动正式学习状态的写必须持有绑定 `(job_id, tool_name, 参数摘要)` 的确认令牌；**同令牌配不同参数即拒绝**——直接复用 `source_delete.py:821` `_assert_idempotent` 的 `REQUEST_CONFLICT` 形态。 |
| **撤销** | 撤销记录使未决授权失效；已撤销的授权**不得**再 apply，未决副作用必须在撤销后停止。 |
| **不可变审计** | 每次授权写一条**追加式**记录（actor / scope / 参数摘要 / 裁定 / 时间戳），只增不改不删。 |
| **默认与覆盖** | 默认拒绝（缺 capability 即拒，不降级、不静默回退到只读）。scope 只能收紧。 |
| **校验与失败** | 越权 ⇒ `TOOL_PERMISSION_DENIED`（按 2026-09-22 的错误码裁定，M10 **真实返回**该码）；令牌参数不匹配 ⇒ 稳定冲突码。两类失败都**不**产生副作用。 |
| **隐私** | 审计记录只留参数**摘要**，不留参数原文、宿主路径或凭据。 |
| **兼容** | M6b 的只读 preview 面**不改**；`ToolCapability` / `SideEffect` 枚举**只增不改**（既有成员语义不变）。 |
| **量化阈值** | 越权写入尝试 = 0；令牌参数不匹配的重放 = 0；写 allowlist ∩ 只读 allowlist = ∅（结构性断言）；每次授权恰有一条审计记录。 |
| **证据** | 拟 `tests/M10/test_write_authorization.py`；注册期与执行期两侧的拒绝用例 + 令牌重放用例 + 审计追加性用例。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 1.3 本批**不做**什么

- 不创建任何写工具、不改 `tool_registry.py`、不新增路由或开关。
- 不创建独立 SQLite 文件、不定义其 schema（那属于批次 ② 的 `M10-CHECKPOINT`）。
- 不修改 M6b 已交付并冻结的只读 preview 行为。
- 不产生 `RESOLVED`：登记表在本批获 owner 批准**之后**才可更新。

## 2. 批次 ②：`M10-CHECKPOINT`、`M10-IDEMPOTENCY`、`M10-EFFECT-LEDGER`、`M10-RECOVERY`

四项彼此耦合（副作用语义四件套），故同批裁定。全部以 §3 的**独立 SQLite 文件**存储裁定为前提。

### 2.1 `M10-CHECKPOINT`

**拟定 `value`**：

```text
SEPARATE_SQLITE_FILE_FOR_RUNNER_STATE__JOB_AND_CHECKPOINT_RECORDS__ONE_CHECKPOINT_PER_EFFECT_BOUNDARY_NO_TIME_BASED__RESUME_REVALIDATES_AUTHORIZATION_AND_DELETION__CANCEL_IS_TERMINAL_NO_FURTHER_EFFECTS
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | job 与 checkpoint 落在**独立 SQLite 文件**（2026-09-22 存储裁定），完全不碰 `learning_store.py`。对象：`job`（identity / scope / input manifest digest / 资源预算 / progress / terminal state）与 `checkpoint`（`job_id` / 单调 `seq` / `stage` / `input_digest` / `state_digest` / 时间戳）。 |
| **该库自己的版本机制** | 独立库仍需版本机制。取 `source_registry.py:438-444` 的 **meta 表 family + 数值版本、不匹配即拒** 范式——它是**新库**，不存在需要升级的老库，故 `source_delete.py` 那条 `ALTER TABLE` 迁移路径在本阶段**不适用**。 |
| **边界与频率** | **每个副作用边界至多一次** checkpoint：propose 前 / authorize 后 / apply 前 / apply 后。**不做**基于时间的 checkpoint——那会破坏可重放性（`M9-PLAN-SCHEMA` 的同一纪律）。 |
| **resume 校验** | 从 checkpoint 恢复必须**重新**校验授权与删除状态，照 `source_delete.py:851` `_resume_barrier` 的「从持久化 intent 恢复」形态；**不得**因恢复而跳过授权/删除复核。 |
| **取消** | cancel 是 job 行上的**终态请求**；已取消的 job **不得**再 apply 任何副作用。 |
| **保留** | 与 job 保留期一致；不得留存超出领域记录已有的用户内容。 |
| **隐私** | checkpoint 不写宿主路径、凭据或用户内容原文；只留摘要与标识。 |
| **兼容** | 学习状态库**完全不被触碰**（物理分离使其可机械验证）；不 bump `SCHEMA_VERSION`；旧 session/plan 可读。 |
| **量化阈值** | 恢复导致重复副作用 = 0；恢复跳过授权复核 = 0；每个副作用边界**恰好**一条 checkpoint（结构性断言）。 |
| **证据** | 拟 `tests/M10/test_checkpoint.py`；含「恢复时授权已撤销则拒绝」与「恢复时 source 已删除则拒绝」两个 fail-closed 用例。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 2.2 `M10-IDEMPOTENCY`

**拟定 `value`**：

```text
KEY_DERIVED_FROM_JOB_TOOL_ARG_DIGEST_SCOPE__UNIQUE_CONSTRAINT__SAME_KEY_DIFFERENT_ARGS_IS_A_STABLE_CONFLICT__REPLAY_RETURNS_RECORDED_RESULT__RETENTION_NOT_SHORTER_THAN_JOB_RETENTION
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | `idempotency_key = sha256(job_id \| tool_name \| 参数摘要 \| scope_id)`，落在**唯一约束**上。 |
| **冲突** | 同一键配**不同**参数 ⇒ 稳定冲突码，副作用**不**应用——复用 `source_delete.py:821` `_assert_idempotent` 的 `SOURCE_DELETE_REQUEST_CONFLICT` 语义。 |
| **重放** | 返回**已记录的结果**，不重新执行。 |
| **并发** | 唯一约束 + 事务保证重复收敛为一次应用。**单 worker 裁定下**无需处理跨 worker 并发（那属 M12）。 |
| **保留** | **不短于** job 保留期——短于重放窗口会二次应用。 |
| **隐私** | 键与记录只含参数**摘要**，不含参数原文、路径或凭据。 |
| **兼容** | 幂等键是**新增**面，不改既有 `save` / `save_review` / `save_plan` / `save_progress_event` 的语义。 |
| **量化阈值** | 重复副作用 = 0（在冻结 crash 矩阵与并发用例上）；同键不同参数的冲突码稳定。 |
| **证据** | 拟 `tests/M10/test_idempotency.py`。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 2.3 `M10-EFFECT-LEDGER`

**拟定 `value`**：

```text
PROPOSED_AUTHORIZED_PENDING_APPLIED_FAILED_COMPENSATED__OUTBOX_RECONCILE_REQUIRED_NOT_OPTIONAL__PENDING_PERSISTED_BEFORE_DOMAIN_WRITE__APPEND_ONLY__DECLARES_ACTUAL_GUARANTEE_NEVER_EXACTLY_ONCE
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 六态：`proposed` / `authorized` / `pending` / `applied` / `failed` / `compensated`。 |
| **事务边界（本批最要害的一条）** | 存储裁定取独立库 ⇒ **跨库事务不可用**，故 outbox + reconcile 是**必需项而非可选优化**。台账行必须在领域写入**之前**持久化为 `pending`；否则崩溃窗口内会出现「已 apply 但无台账行」，而这正是本项阈值要抓的缺陷。 |
| **reconcile** | `pending` 超阈值与领域状态对账；**reconcile 自身必须幂等**，否则对账会制造重复副作用。 |
| **审计** | 追加式；保留期内不删除。 |
| **诚实声明（强制）** | 台账**不得**宣称 exactly-once（M10 计划 §1 同款要求）。报告须写明**实际**保证（at-least-once + 幂等应用，或每键 at-most-once）并给出该保证的**证据用例名**。 |
| **隐私** | 台账不写宿主路径、凭据或用户内容原文。 |
| **兼容** | 独立库新增面；不改学习状态库 schema。 |
| **量化阈值** | `applied` 而无台账行 = 0；台账 `applied` 而领域无对应效果 = 0（由 reconcile 检查）。 |
| **证据** | 拟 `tests/M10/test_effect_ledger.py`；含 reconcile 幂等用例与「先落 pending 再写领域」的顺序用例。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 2.4 `M10-RECOVERY`

**拟定 `value`**：

```text
FROZEN_SINGLE_PROCESS_CRASH_MATRIX_TEN_POINTS__EACH_POINT_HAS_EXPECTED_TERMINAL_STATE__UNCOMPENSABLE_FAILURES_ARE_NON_RETRYABLE_AND_NEED_HUMAN_INTERVENTION__POISON_EFFECT_STOPS_THE_JOB
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 冻结 crash/recovery matrix，**逐点枚举**，每点有期望终态、是否允许重放、是否需补偿。 |
| **矩阵（10 点，单进程口径）** | ① propose 前；② propose 后 / authorize 前；③ authorize 后 / apply 前；④ apply 事务中途；⑤ apply 后 / 台账 commit 前；⑥ 台账 commit 后 / job checkpoint 前；⑦ checkpoint 写入中途；⑧ cancel 处理中途；⑨ 任一步骤磁盘不足；⑩ provider 中途超时。 |
| **口径来源** | worker 拓扑裁定为**维持单 worker**，故矩阵**只需覆盖单进程** crash；「未来云端 worker 重试」是 **M12 的输入**，不是本阶段要求（M10 计划 §1.1 已同步改口径）。 |
| **不可补偿失败** | 无法补偿的副作用 ⇒ job 进入**不可重试**终态并要求**人工介入**；**必须**留痕，**绝不**静默重试。 |
| **poison effect** | 同一 effect 连续失败达阈值（默认 3）后标记 poison，job 停止而非无限重试。 |
| **隐私** | 恢复路径不得把宿主路径/凭据写进任何记录。 |
| **兼容** | 恢复不得重复发布 generation、不得重复写领域状态、不得跳过授权/删除复核（M10 计划 §1.1）。 |
| **量化阈值** | 矩阵每点「重复副作用 = 0」且「半发布 generation = 0」；矩阵覆盖 = **100%**（10/10 点各有用例）。 |
| **证据** | 拟 `tests/M10/test_recovery.py`；10 点各一用例 + 不可补偿失败与 poison 两个终态用例。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 2.5 本批**不做**什么

- 不创建独立 SQLite 文件、不写其 schema、不写任何 checkpoint/ledger 代码。
- 不改 `learning_store.py`（该库无迁移机制，本批不引入迁移机制——独立库不需要它）。
- 不新增路由、开关或生产物件；不建 `tests/M10/`。
- 不产生 `RESOLVED`：登记表在本批获 owner 批准**之后**才可更新。

## 3. 批次 ③：`M10-OFFLINE-DEFAULT`、`M10-MANIFEST`、`M10-EVALUATION`、`M10-MCP`、`M10-ROLLOUT`

### 3.1 `M10-OFFLINE-DEFAULT`

**拟定 `value`**：

```text
STATE_MACHINE_IS_THE_FORMAL_DEFAULT__NO_AUTONOMOUS_PATH_WITHOUT_LLM__NO_SILENT_FALLBACK_TO_A_WEAKER_WRITE_PATH__RUNNER_FAILURES_ARE_ISOLATED_AND_LEAVE_STATE_BYTE_IDENTICAL__DISABLED_IS_IDENTITY
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 正式默认是状态机。`SA_RUNNER` 未设或为假时，`/api/v1/study-sessions` 行为与接入前**逐字节相同**（含 `session_id` 派生）——沿用 M9 已冻结的「默认关闭是恒等操作」纪律。 |
| **无 LLM** | 无外部 AI 时**不存在**自主路径；**不得**静默降级成一条能力更弱的**写**路径。回退只能回到状态机。 |
| **隔离** | Runner 失败（超时、provider 错误、崩溃）**不得**污染 session/plan 状态；失败收敛为稳定终止原因码，且不产生半成品。 |
| **隐私** | 关闭路径不读 provider key、不构造 provider 客户端（照 M9「未设 `SA_PLAN_AI_ENABLED` 时不构造 proposer，连 token 都不读」）。 |
| **兼容** | M0–M5 API/OpenAPI、默认 90 题、旧 SQLite session 恢复均不变。 |
| **量化阈值** | 关闭时响应逐字节相同；Runner 各类失败后库状态与失败前逐字节相同（沿用 M6b 的 `iterdump` 摘要 + `PRAGMA data_version` + `total_changes` 机械证明）。 |
| **证据** | 拟 `tests/M10/test_offline_default.py`。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 3.2 `M10-MANIFEST`

**拟定 `value`**：

```text
KNOWLEDGE_PACK_MANIFEST_IDENTITY_VERSION_INTEGRITY_CAPABILITY_PROVENANCE_COMPAT_SIGNATURE__BYTE_REPRODUCIBLE_DIGEST_WITH_FROZEN_CANONICALIZATION__BINDS_TO_M7_GENERATION_IDENTITY__MUST_NOT_CHANGE_MASTERY_OR_PLAN_SEMANTICS
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | manifest 定义 knowledge-pack 的 identity / 版本 / 完整性 / 能力 / 来源 / 兼容 / 签名政策。 |
| **字节稳定性（本批最要害的一条）** | digest 必须**可复现**。本仓已为此付过代价——`.gitattributes` 为 `document-mapping.json`、M8 gate 记录等**逐条** pin `text eol=lf`，因为 CRLF checkout 会改变校验方读到的字节。manifest 若进 digest，**必须**先冻结换行与序列化规范（可复用 `sa-json-c14n-v1`：UTF-8 无 BOM、LF、canonical JSON）。 |
| **与既有身份的关系** | **必须**绑定 M7 的 generation 身份，**不得**另造一套并行 source identity。 |
| **兼容** | manifest 变化**不得**改变 mastery 与计划状态语义（M9 计划 §1.1 的同一约束）；不得因 manifest 变更 churn 既有 `plan_id`。 |
| **隐私** | manifest 不含用户内容原文、宿主路径或凭据。 |
| **量化阈值** | 同一输入两次生成 digest 逐字节相同；manifest 变更后旧 session/plan 仍可读。 |
| **证据** | 拟 `tests/M10/test_manifest.py`；含 digest 复现用例与「manifest 变更不改变 mastery/plan 语义」用例。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 3.3 `M10-EVALUATION`

**拟定 `value`**：

```text
FROZEN_AGENT_TASK_SET__TWO_ARMS_DETERMINISTIC_STUB_GATING_REAL_PROVIDER_OPT_IN_NON_GATING__EVERY_GATE_NAMES_ITS_LOCAL_EXECUTION_POINT__ZERO_TOLERANCE_THRESHOLDS__SCOPE_LIMITED_TO_THE_M10_AUTONOMOUS_PATH
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 维度：任务成功率、工具/参数合法率、**越权率**、终止原因分布、恢复成功率、cost、p95、发布阈值。 |
| **两臂（沿用 M9 已冻结的分工）** | arm A 确定性 stub、**CI 门禁**；arm B 真实 provider、显式 opt-in、**非门禁**，任何退出条件与登记表**不得**依赖它。 |
| **原则 3 的强制适用** | 每个被写成门禁的指标**必须**给出**本地执行点**。给不出执行点的只能进报告，**不得**进门禁——M9 的 `max_output_tokens` 就是这么被纠正的（M9 计划 §4.4）。 |
| **阈值（owner 2026-09-22 裁定：0 容忍组）** | 越权率 = 0；重复副作用 = 0；半发布 generation = 0；crash 矩阵覆盖 = 100%；状态机默认路径可回滚且旧 session 可恢复；默认 90 题不退化。 |
| **范围限制** | 本评测**只覆盖 M10 自主路径**，**不是**全项目评测口径冻结；遵循度类指标仍为**定性**，无数值阈值。 |
| **隐私** | 报告只记脱敏字段（无 prompt 正文、无 provider 原文、无宿主路径、无异常文本）——照 `tests/M9/test_plan_ai_provider_smoke.py` 的既有形态。 |
| **证据** | 冻结任务集文件 + 报告（含机器可读的 `enforced_locally` / `not_enforced_locally`，沿用 M9 报告形态）+ 用例名清单。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 3.4 `M10-MCP`

**拟定 `value`**：

```text
MINIMAL_SURFACE_NO_WRITE_TOOLS_IN_FIRST_RELEASE__STDIO_ONLY_NO_LISTENER__TOKEN_AT_LEAST_32_BYTES_FAIL_CLOSED__CONSUMES_TOOL_PERMISSION_DENIED_AND_BUDGET_EXCEEDED__NO_NATIVE_BACKEND_CAPABILITY_EXPOSED
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 首个发布**不含写工具**；工具集是 `PREVIEW_TOOL_ALLOWLIST` 的子集或等价只读集。传输取**本地 stdio only**，不监听端口（与 local-first 默认一致，不新开网络面）。 |
| **认证** | token ≥32 UTF-8 字节、缺失即 fail closed，沿用 `config.py:140-143` 的 preview 形态。 |
| **错误码（owner 2026-09-22 裁定）** | **消费** `runtime-contracts.md:71-72` 的两个预留码 `TOOL_PERMISSION_DENIED` / `BUDGET_EXCEEDED`，使契约表与实现对齐。**边界**：只要求 M10 自己的面消费；M6b preview 的既有 `terminated` 表达**不改写**（已交付且已冻结，改它属另一个决定）。 |
| **conformance** | 不得暴露 LanceDB / Qdrant / SQLite 原生能力；错误码稳定且不泄露路径或凭据。 |
| **隐私** | 响应与日志不含宿主路径、凭据、用户内容原文。 |
| **兼容** | 默认不注册（照 `/api/v1/agent-preview` 的条件注册形态）；M6b 面不变。 |
| **量化阈值** | conformance 用例全绿；未授权工具调用 = 0；响应中宿主路径出现 = 0。 |
| **证据** | 拟 `tests/M10/test_mcp_conformance.py`。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 3.5 `M10-ROLLOUT`

**拟定 `value`**：

```text
DEFAULT_OFF__KILL_SWITCH_CHECKED_AT_EVERY_EFFECT_BOUNDARY_NOT_ONLY_AT_JOB_START__SINGLE_WORKER_TOPOLOGY_MAINTAINED__DISABLING_LEAVES_ALL_EXISTING_DATA_READABLE_AND_THE_STATE_MACHINE_FUNCTIONAL
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 默认关闭；启用条件、环境/用户范围、观测字段、kill switch、回滚、迁移兼容均须逐项定义。 |
| **kill switch（本批最要害的一条）** | **在每个副作用边界**检查，**不只在 job 开始时检查一次**——否则长任务无法被叫停，而 M10 的核心场景正是长任务。 |
| **并发前提（owner 2026-09-22 裁定）** | 维持**单 worker**，`worker_topology.py:40/64` 的 `enforce_single_worker_topology` 继续生效；多 worker 与云端 worker 重试**留给 M12**。 |
| **回滚** | 关闭 Runner 后，全部既有 session / plan / review 数据仍可读，状态机路径功能完整。 |
| **隐私** | 观测字段不含宿主路径、凭据或用户内容原文。 |
| **兼容** | 不 bump `SCHEMA_VERSION`；独立库的存在不影响学习状态库的可读性。 |
| **量化阈值** | kill switch 在矩阵**每个边界点**生效（用例覆盖 100%）；关闭后回归套件全绿。 |
| **证据** | 拟 `tests/M10/test_rollout.py`。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 3.6 本批**不做**什么

- 不创建 MCP server、不新增路由/开关、不建 `tests/M10/`、不写任何生产物件。
- 不修改 `docs/standards/runtime-contracts.md`——消费两个预留码是**实现时**的动作，本批只裁定口径。
- 不产生 `RESOLVED`：登记表在本批获 owner 批准**之后**才可更新。

## 4. 批准记录

| 批次 | Decision | 裁定 | 批准人 | 批准时间 | 批准引用 |
| --- | --- | --- | --- | --- | --- |
| ① | `M10-AUTHORITY` | `RESOLVED` | justtodo123 | 2026-09-22 | 见下「批次 ① 批准依据」 |
| ① | `M10-WRITE-AUTHORIZATION` | `RESOLVED` | justtodo123 | 2026-09-22 | 见下「批次 ① 批准依据」 |
| ② | `M10-CHECKPOINT` | 已起草，待批准 | — | — | — |
| ② | `M10-IDEMPOTENCY` | 已起草，待批准 | — | — | — |
| ② | `M10-EFFECT-LEDGER` | 已起草，待批准 | — | — | — |
| ② | `M10-RECOVERY` | 已起草，待批准 | — | — | — |
| ③ | `M10-OFFLINE-DEFAULT` | 已起草，待批准 | — | — | — |
| ③ | `M10-MANIFEST` | 已起草，待批准 | — | — | — |
| ③ | `M10-EVALUATION` | 已起草，待批准 | — | — | — |
| ③ | `M10-MCP` | 已起草，待批准 | — | — | — |
| ③ | `M10-ROLLOUT` | 已起草，待批准 | — | — | — |

### 批次 ① 批准依据

| 批准字段 | 值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-09-22 |
| approval_reference | User instruction: 「按顺序进行即可」——回应「要请你看批次 ① …确认后我把它标为已批准、把登记表两项转 `RESOLVED`，再写批次 ②」。按本仓既有惯例（M9 的 `approval_reference` 同样逐字引用原话并说明解读），本句读作**批准批次 ① 按草案原文成立，并按 ①→②→③ 顺序继续**；未提出修改，故 §1.1 / §1.2 的 `value` 与十项必备内容逐字生效 |

**本批批准做什么**：把 `M10-AUTHORITY` 与 `M10-WRITE-AUTHORIZATION` 在登记表中由 `OPEN` 改为 `RESOLVED`，
`value` 取 §1.1 / §1.2 的令牌串，`evidence` 指向本文件与设计草案。

**本批批准不做什么**（逐条，防止被后读高估）：

- **不批准 M10 准入**：`admission_status` 仍 `BLOCKED`、`approval` 五字段仍为空；十一项决策尚有九项 `OPEN`。
- **不授权开工**：不创建写工具、不改 `tool_registry.py`、不新增路由/开关、不建 `tests/M10/`。
- **不创建独立 SQLite 文件、不定义其 schema**——那属于批次 ② 的 `M10-CHECKPOINT`。
- **不改写 M6b** 已交付并冻结的只读 preview 行为。
- **不触发 §4 撤销、不写 `admission_history`**：M10 从未准入，不存在可撤销的准入；`from`/`to` 会是
  `BLOCKED → BLOCKED`。

**其余九项 Decision 仍为 `OPEN`**（`M10-CHECKPOINT` / `M10-IDEMPOTENCY` / `M10-EFFECT-LEDGER` /
`M10-RECOVERY` / `M10-OFFLINE-DEFAULT` / `M10-MANIFEST` / `M10-EVALUATION` / `M10-MCP` / `M10-ROLLOUT`），
M10 保持 `BLOCKED / NOT_STARTED`。Agent 不得自行批准。

**批次 ②③ 已起草但未批准**（见 §2 / §3）。它们的 `value` 与十项必备内容**只是提案**，在 §4 批准记录
填入 owner 的批准引用之前，登记表中对应九项**必须**保持 `OPEN`、`value` 为 `null`、`evidence` 为空。
