# M10 自主 Runner 与 Harness 对外准备计划

> 当前状态：`ADMITTED / IN_PROGRESS`（2026-09-22 获批，范围 `m10-autonomous-runner-v1`，plan_revision v1.0；
> `implementation_start` 已 `AUTHORIZED`，见 §4.1）
> 前置：M7、M8、M9 全部退出证据（三项均已 `SATISFIED`）
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)

## 1. 范围与非目标

M10 才规划可选自主 Runner、受授权写工具、checkpoint/resume、幂等副作用、恢复、Agent 任务评测、knowledge-pack
manifest 和 MCP 最小对外面。状态机继续作为正式默认与无 LLM fallback，自主 Runner 不因 M6b preview 或计划文件
存在而启用。

本阶段不承诺分布式 exactly-once；通过能力授权、幂等键、EffectLedger、事务边界、reconcile 和补偿定义可验证的
副作用语义。设定未闭合前不得添加自主执行开关、写工具、MCP server、schema migration 或发布配置。

### 1.1 10K/100K 长任务边界

M10 必须支持 M8 100K capacity 和拟议 M11 10K 真实数据带来的长任务，但不把向量数据库变成模型可直接操作的工具：

- ingestion、parser、embedding、index build/rebuild、incremental sync、evaluation 必须作为有界异步 job；
- job 必须有稳定 identity、scope、input manifest digest、resource budget、progress、checkpoint、cancel 和 terminal state；
- checkpoint/resume 不得重复发布 generation、重复写领域状态或跳过授权/删除复核；
- EffectLedger 记录 proposed/authorized/pending/applied/failed/compensated，批量子任务必须使用幂等键；
- Runner 和模型不得直接执行 LanceDB/Qdrant/SQLite 原生命令，只能调用受授权领域服务；
- index candidate 构建不得阻塞正式学习会话；只有完整校验和原子发布后才可见；
- 本地进程退出、断电、磁盘不足、取消必须进入冻结 crash/recovery matrix；**未来云端 worker 重试**在
  2026-09-22 的 worker 拓扑裁定（维持单 worker，多 worker 留给 M12，见
  [`references/m10-decision-design-draft.md`](references/m10-decision-design-draft.md) §11）下**只作为 M12 的
  输入**，不构成本阶段的矩阵要求；
- 资源预算至少覆盖 wall-clock、CPU、RSS、磁盘临时空间、并发、外部 AI token/cost（若启用）和保留期。

本节不批准 M11 数据扩展、M12 云部署、后台 worker 或任何生产长任务。

## 2. 前置证据与继承不变量

| Prerequisite ID | 当前状态 | 准入所需证据 |
| --- | --- | --- |
| `M10-M7-EXIT` | `SATISFIED` | M7 Source lifecycle/delete/isolation/fallback 与独立完成批准；证据见 `docs/PLAN.md`、M7 计划与 `docs/baselines.md` |
| `M10-M8-EXIT` | `SATISFIED` | 2026-09-22 owner 批准的**维持现状结论**（见 §2.1）：M10 数据面维持当前 SQLite registry + linear cosine + 默认 BM25，100K 专业化存储容量验证保持待命参考；证据见 `docs/PLAN.md`、本节与 [`m8-specialized-storage-plan.md`](m8-specialized-storage-plan.md) |
| `M10-M9-EXIT` | `SATISFIED` | plan/mastery authority、deviation/replan、外部 AI fallback 和评测退出证据；证据见 `docs/PLAN.md` 与 [`m9-goal-driven-planning-plan.md`](m9-goal-driven-planning-plan.md) §4.5（2026-09-22 收口时同步） |

正式默认仍是 `StudySessionService` 状态机；旧 SQLite session 可恢复；M0–M5 API/OpenAPI、默认 90 题与离线路径
保持兼容；M6b 只读 preview 不能作为写权限、checkpoint 或副作用幂等已实现的证据。

### 2.1 `M10-M8-EXIT` 维持现状结论（2026-09-22 owner 裁定）

`M10-M8-EXIT` 的准入所需证据原文即含「**或批准的维持现状结论**」分支，本节兑现该分支——与 M9 的
`M9-M8-EXIT` 走同一条路径（M9 计划 §2 记「明确维持当前 SQLite/BM25 后端作为 M9 数据面基线」）。

| 裁定字段 | 值 |
| --- | --- |
| decided_by | justtodo123 |
| decided_at | 2026-09-22 |
| decision_reference | User instruction: 在「`M10-M8-EXIT` 怎么处理」的三选一裁定中选择「走维持现状结论分支」——与 M9 的 `M9-M8-EXIT` 同一分支，维持当前 SQLite/BM25 为 M10 数据面，100K 专业化存储保持待命参考；只需 owner 裁定 + 一份证据记录，不新建协议、不做实验、不冻结 digest |
| data_plane | 维持当前 SQLite registry（唯一控制面）+ SQLite linear cosine + 默认 BM25 |
| deferred | 100K 专业化存储容量验证（LanceDB / Qdrant）保持**待命参考**，不阻塞 M10 |

**结论的依据**（三条，均可追溯）：

1. **M10 不需要 100K 数据面**：M10 的范围是自主 Runner 与写副作用治理——authority、写授权、checkpoint、
   幂等、EffectLedger、恢复、评测、manifest/MCP、rollout（§3 十一项），没有任何一项依赖专业向量后端。
2. **M8 侧已由 owner 亲手封存**：`references/m8-owner-policy-only-scope-decision-20260919.md` 记
   `POLICY_ONLY_SCOPE_ACCEPTED`、`allowed_next_action: record-policy-only-scope-and-stop`，network /
   wheel_download / resolver / installation / s1 / s2 / s3 / backend_selection 逐项 `authorized: false`；
   M8 计划抬头亦记「100K 专业化存储容量验证…转为待命参考，不阻塞当前学习闭环」。
3. **重启 M8 的边际产出有历史证据**：`references/m8-eleven-rounds-governance-review.md` 记 V1–V12 全部未
   通过准入，失败性质由数值/结果逐层下移到流程纪律与源码完整性；其后 `draft-0.10` 与 `draft-0.11` 的独立
   P3 均 `REJECTED / stop`，minimal-1k v3 的 s0/s1 又经多轮 r01–r09。再开一轮的期望产出是**再下探一层
   约束**，不是 M10 所需的任何前置。

**本裁定做什么**：把 `M10-M8-EXIT` 由 `OPEN` 改为 `SATISFIED`，并在登记表写入上述证据路径。

**本裁定不做什么**（逐条，防止被后读高估）：

- **不构成 M10 的准入批准**：`admission_status` 仍为 `BLOCKED`、`approval` 五个字段仍为空；M10 仍需
  §3 全部十一项强制决策 `RESOLVED` 与 owner 的独立准入批准（§4）。
- **不批准 M8 的任何执行**：不选择后端、不建 `tests/M8/`、不做 100K 实证、不触碰 Network / Milvus；
  M8 保持 `BLOCKED / NOT_STARTED`，其 §9 的剩余准入项**不因本裁定减少**。
- **不产生任何容量证据**：这是**维持现状**，不是「容量已验证」；10K 真实数据仍属拟议 M11。
- **不改写历史**：不修改 `references/` 下的任何治理记录，也不改变 M7 / M9 的既有结论。
- **不触发 §4 撤销、不写 `admission_history`**：§4 的撤销前提是**已准入阶段**的强制决策、前置证据或
  兼容不变量发生实质变化，而 M10 从未准入（`admission_status` 恒为 `BLOCKED`、`approval` 从未填写），
  故不存在可撤销的准入；`admission_history` 的 `from` / `to` 语义是准入状态，本次为 `BLOCKED → BLOCKED`，
  写入会造成语义错配，且会被 `test_admission_history_records_are_well_formed` 的 `from != to` 断言判红。

## 3. 强制决策

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M10-AUTHORITY` | `RESOLVED` | `StudySessionService`、可选 Runner、repository 和 tool 的唯一权威边界、冲突处理与状态机默认规则（2026-09-22 闭合批次 ①，`value` 见登记表与 [`references/m10-decision-closure-v1.md`](references/m10-decision-closure-v1.md) §1.1） |
| `M10-WRITE-AUTHORIZATION` | `RESOLVED` | 写 capability、用户/learner/source scope、显式确认、拒绝/撤销语义和不可变审计字段（2026-09-22 闭合批次 ①，`value` 见登记表与 [`references/m10-decision-closure-v1.md`](references/m10-decision-closure-v1.md) §1.2） |
| `M10-CHECKPOINT` | `RESOLVED` | checkpoint schema/version、边界、频率、存储、加密/保留、取消、兼容和 resume 校验 |
| `M10-IDEMPOTENCY` | `RESOLVED` | idempotency key 派生、作用域、唯一约束、保留、重放、并发、冲突和结果复用 |
| `M10-EFFECT-LEDGER` | `RESOLVED` | proposed/authorized/pending/applied/failed/compensated 状态、事务边界、outbox/reconcile 和审计 |
| `M10-RECOVERY` | `RESOLVED` | retry/resume/compensation、poison effect、人工介入、进程 crash-point matrix 和不可补偿失败 |
| `M10-EVALUATION` | `RESOLVED` | Agent 任务集、成功率、工具/参数合法率、越权率、终止、恢复、cost、p95 和发布阈值 |
| `M10-MCP` | `RESOLVED` | protocol/transport、tool/resource surface、认证、schema/error mapping、写限制和 conformance |
| `M10-MANIFEST` | `RESOLVED` | knowledge-pack manifest identity、版本、完整性、能力、来源、兼容和签名/校验政策 |
| `M10-OFFLINE-DEFAULT` | `RESOLVED` | 状态机正式默认、无 LLM fallback、自主路径不可用/失败时的隔离和不得重复副作用 |
| `M10-ROLLOUT` | `RESOLVED` | 自主 Runner 默认关闭、启用条件、环境/用户范围、观测、kill switch、回滚和迁移兼容 |

每项必须记录明确政策、默认与覆盖、校验/失败、兼容/隐私、量化阈值、证据、责任人和日期。笼统的
“exactly-once”、未定义 crash point 的恢复宣称或仅有 happy-path demo 都不能闭合决策。

十一项决策的设计草案（**非授权、不产生 `RESOLVED`**）见
[`references/m10-decision-design-draft.md`](references/m10-decision-design-draft.md)：§0.1 逐条登记起草时核实的
仓库事实；§末记录 owner 于 2026-09-22 对四项开放点的**裁定**——存储机制取**独立 SQLite 文件**、预留错误码由
M10 **消费**、**维持单 worker**（多 worker 留给 M12）、评测取 **0 容忍组**。四项裁定**只关闭草案内的开放点**，
**不产生任何 `RESOLVED`**，十一项决策仍需逐项闭合并经 owner 单独批准。

决策的**闭合面**（可直接落登记表 `value` 的令牌串与十项必备内容）见
[`references/m10-decision-closure-v1.md`](references/m10-decision-closure-v1.md)：分批推进，批次 ①
（`M10-AUTHORITY` + `M10-WRITE-AUTHORIZATION`）**已于 2026-09-22 获 owner 批准并转 `RESOLVED`**；批次 ②
（`CHECKPOINT` / `IDEMPOTENCY` / `EFFECT-LEDGER` / `RECOVERY`）与批次 ③（`OFFLINE-DEFAULT` / `MANIFEST` /
`EVALUATION` / `MCP` / `ROLLOUT`）**已起草但未批准**，对应九项在登记表中仍 `OPEN`。本文件与闭合记录都
**不产生** `RESOLVED`，登记表在 owner 逐批批准后才可更新。

## 4. 准入检查与批准记录

- [x] M7–M9 退出证据全部真实有效（`M10-M8-EXIT` 以 §2.1 的维持现状结论兑现，不是容量证据）；
- [x] 十一项强制决策全部 `RESOLVED`（2026-09-22 闭合批次 ① 两项 + ②③ 九项），authority、authorization、
  ledger 和 recovery 一致——四项相互引用的约束已交叉核对（独立 SQLite 文件 ⇒ 无跨库事务 ⇒ outbox/reconcile
  必需 ⇒ 台账行先落 `pending`；单 worker ⇒ crash 矩阵只需单进程）；
- [x] 写副作用 crash-point、越权和重放测试方案可执行（方案见
  [`references/m10-test-plan-v1.md`](references/m10-test-plan-v1.md)：10 点 crash matrix 的注入方式与断言、
  越权矩阵、重放/冲突、台账与 reconcile、零写入的机械证明形态、恒等操作与隔离，以及每条用例的非空转与
  变异要求）；
- [x] Agent 评测任务集、样本、硬件/provider、成本与发布阈值冻结（**阈值**已由 `M10-EVALUATION` 冻结为 0 容忍组，
  两臂分工沿用 M9；**任务集形状**见 [`references/m10-test-plan-v1.md`](references/m10-test-plan-v1.md) §10——
  冻结的是**任务类别 × 期望终态 × 越权探针**，**刻意不冻结具体语料**：Runner 尚不存在，此时冻结语料是把未验证的
  假设写成事实；实施时物化为机器可读文件并钉住摘要）；
- [x] MCP/manifest 的认证、兼容和 conformance 边界明确（`M10-MCP` 与 `M10-MANIFEST` 已 `RESOLVED`，含
  stdio-only、token ≥32 字节、首个发布不含写工具，以及 manifest digest 的 canonicalization 前置）；
- [x] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表一致（由
  `test_stage_plans_track_registry_prerequisites`、`test_stage_plans_track_registry_decision_status` 与
  `test_plan_milestone_table_matches_registry` 逐项机械校验）；
- [x] 用户或项目负责人完成批准（2026-09-22，见 §4.1）。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-09-22 |
| approval_reference | User instruction: 「允许执行」（原文与解读见 §4.1） |
| plan_revision | v1.0 |
| decision_set_version | m10-decision-set-v1 |

**准入检查表六项已全部勾选。** 第 3、4 两项由准备物
[`references/m10-test-plan-v1.md`](references/m10-test-plan-v1.md) 关闭——它给出可执行的测试方案与冻结的
评测任务集**形状**，但**不创建 `tests/M10/`**、不写生产物件、不产生性能声明。

三项前置（`M10-M7-EXIT` / `M10-M8-EXIT` / `M10-M9-EXIT`）自 2026-09-22 起均已 `SATISFIED`。

### 4.1 准入与生产开工批准（2026-09-22）

| 批准字段 | 值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-09-22 |
| approval_reference | User instruction: 「允许执行」——回应「下一步：M10 准入 + 开工批准。批了之后 M10 转 `ADMITTED / IN_PROGRESS`，我按计划 §5 从『冻结 authority/capability/EffectLedger schema，先实现拒绝路径』开始写代码」。按本仓既有惯例逐字引用原话并说明解读：本次用「执行」（而非上次推送用的「推送」），故读作**批准 M10 准入与生产开工**，而非仅批准推送 |
| plan_revision | v1.0 |
| decision_set_version | m10-decision-set-v1 |
| approval_scope | `m10-autonomous-runner-v1` |
| implementation_start | `AUTHORIZED`（2026-09-22，同一指令；见登记表） |

**批准范围 `m10-autonomous-runner-v1`**：

- `included`（11 项，与 §3 的十一项强制决策一一对应）：`m10.authority`、`m10.write-authorization`、
  `m10.checkpoint`、`m10.idempotency`、`m10.effect-ledger`、`m10.recovery`、`m10.evaluation`、
  `m10.manifest`、`m10.mcp`、`m10.offline-default`、`m10.rollout`；
- `excluded`（5 项）：`m11.data-scaling`、`m12.cloud-deployment`、`m10.multi-worker-topology`、
  `m8.backend-selection`、`m10.real-10k-100k-data`。

**本批准做什么**：把 `admission_status` 改为 `ADMITTED`、`delivery_status` 改为 `IN_PROGRESS`，
`implementation_start` 改为 `AUTHORIZED`（按
[`stage-admission-gates.md`](../standards/stage-admission-gates.md) §4，交付进入 `IN_PROGRESS` 需开工门禁已授权）。

**本批准不做什么**（逐条，防止被后读高估）：

- **不批准任何被排除项**：M11 数据扩展、M12 云部署、多 worker 拓扑、M8 后端选择、10K/100K 真实数据
  仍全部未获批——`approval_scope` 只用于**缩小**边界，不得把被排除的下游阶段隐式提升为已批准。
- **不产生 `completion_approval`**：`COMPLETE` 需要技术退出证据之外的**独立**完成批准，本阶段远未到；
  登记表中 `completion_approval` 必须保持不存在。
- **不改变十一项决策值**、不改 `approval_scope` 之外任何字段、不写 `admission_history`（本次为
  `BLOCKED → ADMITTED`，是**准入状态过渡**——按 §4 的留痕要求，过渡本身由本节与登记表批准字段承担；
  M9 的 `admission_history` 记录对应的是**决策值实质变更**，本次没有决策值变更）。
- **不豁免 §6 继承不变量**：M0–M5 API/OpenAPI 与正式学习闭环保持兼容、`StudySessionService` 继续独占正式
  状态转换与领域写入、默认 90 题不变、默认离线路径不强制依赖外部 LLM、M6b 仍是隔离且默认关闭的只读 preview、
  **状态机仍为正式默认**。
- **不授权跳过 §5 顺序**：实施按 §5 的七步推进，且必须遵守
  [`references/m10-test-plan-v1.md`](references/m10-test-plan-v1.md) 的方案与变异要求。

## 5. 获准后的拟实施顺序

1. 冻结 authority、capability 和 EffectLedger schema，先实现拒绝路径；
2. 为单一受控写工具实现 idempotency、checkpoint 和逐 crash point 恢复；
3. 建立通用异步 job envelope、资源预算、进度、取消和 terminal state，并先用无生产发布的合成长任务验证；
4. 为 ingestion/embedding/reindex 定义 manifest-bound checkpoint 与 generation publication 门禁；
5. 建立 reconcile/人工介入和不可补偿失败处理，再扩大写工具集合；
6. 接入默认关闭的可选 Runner，并保持状态机路径与数据兼容；
7. 在冻结 Agent 任务集达标后，分阶段交付 manifest 和最小 MCP surface。

拟新增 `tests/M10/` 覆盖 authorization、checkpoint、idempotency、effect ledger、recovery、offline default、rollout、
manifest/MCP conformance；真实 provider 或 transport smoke 必须显式启用且不阻断默认离线 CI。退出条件包括零越权、
重放不重复副作用、10K/100K 合成长任务在取消/崩溃/磁盘不足下不产生半发布 generation、crash matrix 达标、
状态机默认可回滚、旧 session 恢复、默认 90 题不退化及任务评测达到批准阈值。

## 6. 撤销与发布边界

写 capability、ledger/checkpoint schema、provider/MCP 协议、任务集或发布阈值实质变化时必须改为 `REVOKED`，停止
自主实施并重新批准。只有 `ADMITTED` 后实现且退出条件真实通过，才能把 M10 标为 `COMPLETE` 或对外宣称能力已交付。
