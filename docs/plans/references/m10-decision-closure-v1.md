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

## 2. 批准记录

| 批次 | Decision | 裁定 | 批准人 | 批准时间 | 批准引用 |
| --- | --- | --- | --- | --- | --- |
| ① | `M10-AUTHORITY` | — | — | — | — |
| ① | `M10-WRITE-AUTHORIZATION` | — | — | — | — |

批准为空，十一项 Decision 全部保持 `OPEN`，M10 保持 `BLOCKED / NOT_STARTED`。Agent 不得自行批准。
