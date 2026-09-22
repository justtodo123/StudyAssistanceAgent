# M10 写副作用测试方案 v1（准备物，非授权）

> 状态：**准入准备物**。本文件关闭 M10 计划 §4 准入检查表的「写副作用 crash-point、越权和重放测试方案
> 可执行」一项。它**不**批准 M10 准入或开工，**不**创建 `tests/M10/`，**不**写任何生产物件。
> 权威决策见 [`m10-decision-closure-v1.md`](m10-decision-closure-v1.md)；本文只回答「**怎么测**」。

## 0. 本文覆盖什么、不覆盖什么

| 决策 | 本文给出的可执行方案 |
| --- | --- |
| `M10-RECOVERY` | §2 的 10 点 crash matrix：每点如何注入、断言什么 |
| `M10-WRITE-AUTHORIZATION` | §3 的越权矩阵：注册期 / 执行期 / 令牌 / 撤销 |
| `M10-IDEMPOTENCY` | §4 的重放与冲突 |
| `M10-EFFECT-LEDGER` | §5 的台账与 reconcile |
| `M10-AUTHORITY` | §6 的边界与零写入机械证明 |
| `M10-OFFLINE-DEFAULT` | §7 的恒等操作与隔离 |

**不覆盖**：`M10-EVALUATION` 的 Agent 任务集与两臂读数（见 §8）、`M10-MCP` / `M10-MANIFEST` 的 conformance
（各自决策已指定边界，实施时另立用例）。

## 1. 测试树、marker 与前置约束

- 新增 `tests/M10/`，`pytestmark = pytest.mark.m10`；**不修改**任何存量阶段测试。
- 测试树**现在不创建**：本文件是方案，不是测试。M10 获准入后按 M10 计划 §5 顺序落地。
- 所有用例使用 `tmp_path` 下的独立 SQLite 文件；**绝不触碰** `platform/.cache/learning_state.sqlite3`。
- 默认离线：不联网、不构造 provider 客户端。需要真实 provider 的用例必须 `online` + skip 门控且**非门禁**。
- 每条断言必须能**失败**：新增用例都要过 §9 的变异要求。

## 2. crash-point matrix 的行使方式（10 点）

矩阵来自 `M10-RECOVERY`。注入手段统一为**故障钩子**：在 `_run_bounded` 式的受控接缝上，按点注入一次
异常或进程终止信号。**不**用 `sleep` 竞态，**不**依赖时序——每点必须是确定性的。

| # | crash point | 注入方式 | 断言 |
| --- | --- | --- | --- |
| 1 | propose 前 | 在 propose 入口抛 `_InjectedCrash` | 无台账行、无领域写入、job 可重跑 |
| 2 | propose 后 / authorize 前 | 在 authorize 入口抛 | 台账停在 `proposed`，无领域写入 |
| 3 | authorize 后 / apply 前 | 在 apply 入口抛 | 台账停在 `authorized`；**恢复时若授权已撤销则拒绝** |
| 4 | apply 事务中途 | 在领域写入的事务内抛 | 领域状态**原子回滚**，无半写 |
| 5 | apply 后 / 台账 commit 前 | 在台账 commit 前抛 | 由 reconcile 收敛为 `applied`，**不重复 apply** |
| 6 | 台账 commit 后 / job checkpoint 前 | 在 checkpoint 写入前抛 | 由台账恢复，重跑**不重复副作用** |
| 7 | checkpoint 写入中途 | 写一半后抛 | 上一 checkpoint 仍有效，job 从它恢复 |
| 8 | cancel 处理中途 | 在 cancel 落库后、清理前抛 | 终态为 `cancelled`，**不再 apply 任何副作用** |
| 9 | 任一步骤磁盘不足 | 让写入抛 `OSError(ENOSPC)` | fail closed，**无半发布 generation** |
| 10 | provider 中途超时 | stub provider 挂住至超时 | 回退，无半成品，原因码稳定 |

**每点两条断言**：`重复副作用 == 0` 与 `半发布 generation == 0`。矩阵覆盖必须 **10/10**——缺任一点，
`M10-EVALUATION` 的「矩阵覆盖 = 100%」阈值即不成立。

**不可补偿失败与 poison**：另立两个用例——① 补偿本身失败时 job 进**不可重试**终态并要求人工介入，且**留痕**；
② 同一 effect 连续失败达阈值（默认 3）后标记 poison 且 job **停止**，不无限重试。

## 3. 越权矩阵（`M10-WRITE-AUTHORIZATION`）

| 层 | 用例 | 断言 |
| --- | --- | --- |
| 注册期 | 把不在写 allowlist 的工具注册 | `ToolRegistryError`；**且写 allowlist 与 `PREVIEW_TOOL_ALLOWLIST` 断言不相交** |
| 注册期 | 注册 `capability=READ` 或 `side_effect=NONE` 的「写」工具 | 拒绝，与只读侧四项校验同形 |
| 执行期 | `ToolContext.permissions` 缺写能力 | 拒绝，**副作用为 0**；返回 `TOOL_PERMISSION_DENIED` |
| 令牌 | 同令牌配**不同参数**重放 | 稳定冲突码，**副作用为 0** |
| 令牌 | 无令牌 / 令牌绑定到别的 `(job, tool)` | 拒绝 |
| 撤销 | 授权后撤销，再 apply | 拒绝；未决副作用停止 |
| 审计 | 每次授权 | 恰有一条追加式记录；记录只含**参数摘要**，不含原文/路径/凭据 |

**零写入的机械证明**（沿用 M6b 已交付的形态，不重新发明）：`iterdump()` 全文摘要 + 三表行数 +
`PRAGMA data_version` + 连接级 `total_changes`，并把 store 的写方法 monkeypatch 成 `pytest.fail`。

## 4. 重放与冲突（`M10-IDEMPOTENCY`）

- 同键重放 → 返回**已记录结果**，且领域写入计数**不增**（用连接级 `total_changes` 证明）。
- 同键不同参数 → 稳定冲突码，副作用 0。
- 并发：两个线程同键并发 → **恰好一次**应用（唯一约束 + 事务）。
- 保留期：键的保留不短于 job 保留期——用例断言保留窗口内重放仍被去重。
- **非空转**：断言重放路径确实被走到（例如记录 provider/工具调用次数为 1），否则「没重复」可能只是「没执行」。

## 5. 台账与 reconcile（`M10-EFFECT-LEDGER`）

- 六态跃迁合法性：非法跃迁被拒。
- **顺序**：台账行必须在领域写入**之前**落 `pending`——用例注入「领域写入成功但台账未提交」的崩溃点（矩阵第 5 点），
  断言 reconcile 能收敛，而不是留下「已 apply 无台账行」。
- reconcile **幂等**：连续跑两次 reconcile，结果逐字节相同、副作用计数不增。
- 阈值：`applied` 无台账行 = 0；台账 `applied` 但领域无对应效果 = 0。
- **诚实声明**：报告须写明实际保证（at-least-once + 幂等应用 / 每键 at-most-once），并给出证据用例名；
  **不得**出现 `exactly-once` 字样——用一个源码级断言扫报告与台账模块，钉住这一点。

## 6. 权威边界与零写入（`M10-AUTHORITY`）

- 源码级**动态枚举** `platform/app/` 全部源文件（沿用 `tests/M9/test_mastery_write_authority.py` 的纪律，
  不写死名单；带非空性断言）：写 `study_sessions` / `answer_attempts` 的模块**恰好**是 `learning_store.py`。
- Runner 侧模块**不 import `learning_store`**，也不引用其写方法名（`save` / `save_review` / `save_plan` /
  `save_progress_event`）。**注意口径**：`M10-CHECKPOINT` 已裁定 runner 状态放**独立 SQLite 文件**，故
  `effect_ledger.py` **必然** import `sqlite3`——它打开的是**自己的**库。因此本项的判据是「不触碰**领域**库」，
  **不是**「不用 `sqlite3`」；写成后者会是一条错的守卫，并会因不成立而被削弱。
- 冲突：领域服务拒绝 Runner 提议时，job 记 `failed` + 稳定原因码，**不盲目重试**（断言重试计数为 0）。
- 物理分离：Runner 自有库与学习状态库是**两个文件**——断言路径不同，且学习状态库在整套 M10 用例后
  逐字节未变。

## 7. 恒等操作与隔离（`M10-OFFLINE-DEFAULT`）

- `SA_RUNNER` 未设 / 为假时，`/api/v1/study-sessions` 的响应与接入前**逐字节相同**（含 `session_id` 派生）。
- 未设开关时**不读** provider key、**不构造** provider 客户端（照 M9「连 token 都不读」的形态）。
- Runner 各类失败（超时 / provider 错误 / 崩溃）后，库状态与失败前**逐字节相同**（§3 的机械证明形态）。
- 无 LLM 时**不存在**自主写路径——断言不存在「降级成更弱写路径」的分支。

## 8. 与 `M10-EVALUATION` 的接缝

- 本方案的用例名清单是评测报告里 `enforced_locally` 字段的证据来源：**每个被写成门禁的指标都必须指到一个
  本地执行点**；指不出的只能进报告、**不得**进门禁（M9 `max_output_tokens` 的教训）。
- 两臂沿用 M9 已冻结的分工：arm A 确定性 stub、CI 门禁；arm B 真实 provider、显式 opt-in、**非门禁**。
- 冻结的 Agent 任务集见 §10。

## 9. 非空转与变异要求（对每条新用例）

- 每条用例都要能**失败**：实施时逐条做变异（关掉被断言的行为），记录「恰好 N 项判红」。
- **无法用判红表达的结果必须写明**：M7 的解析上界修正中，移除上界不会让测试判红，而是让测试**挂起**——
  因为死循环正是没有 `except` 能捕获的东西（M7 计划 §7.1）。M10 若有同类（例如 kill switch 的检查点），
  必须同样如实记录，而不是假装覆盖了。
- 非空性断言：任何「全部 X 都满足 Y」的断言都要先断言扫描集合**非空**，否则集合为空时平凡成立。

## 10. 冻结的 Agent 评测任务集（`M10-EVALUATION`）

**冻结的是任务形状与判据，不是具体语料。** M10 的自主 Runner 尚不存在，此时冻结一份具体语料是把未验证的
假设写成事实；因此本版冻结的是**任务类别 × 期望终态 × 越权探针**，实施时再物化为机器可读文件并钉住其摘要。

| 任务类别 | 期望终态 | 越权探针 | 恢复探针 |
| --- | --- | --- | --- |
| 只读检索（无写） | `completed` | 请求写工具 → 拒绝 | 无 |
| 单次受控写（有确认令牌） | `completed` + 一条 `applied` 台账 | 缺令牌 / 令牌错参 → 拒绝 | 矩阵第 3、4 点 |
| 多步写（≥2 次 effect） | `completed` + 逐 effect 台账 | 中途撤销授权 → 未决项停止 | 矩阵第 5、6 点 |
| 被拒绝的写（scope 外） | `failed` + `TOOL_PERMISSION_DENIED` | — | 无 |
| 长任务 + 取消 | `cancelled` | 取消后仍尝试 apply → 拒绝 | 矩阵第 8 点 |
| 崩溃后恢复 | `completed` 且**无重复副作用** | — | 矩阵第 1–7 点 |
| provider 不可用 | 回退确定性路径，`provider_unavailable` | — | 矩阵第 10 点 |

**硬件 / provider / 成本口径**：arm A 不联网、无成本；arm B 的 provider、模型、成本上限与延迟读数口径
**沿用 M9 已冻结的形态**（`online` + skip 门控、花费上限、只记脱敏字段、非门禁），不重新发明。

**阈值**：`M10-EVALUATION` 的 0 容忍组——越权率 = 0、重复副作用 = 0、半发布 generation = 0、矩阵覆盖 = 100%、
状态机默认路径可回滚且旧 session 可恢复、默认 90 题不退化。

## 11. 本方案**不**做什么

- 不创建 `tests/M10/`、不写任何生产代码或 schema。
- 不批准 M10 准入或开工；不改变任何 `RESOLVED` 决策值。
- 不冻结具体语料（理由见 §10）；不产生任何性能或容量声明。
