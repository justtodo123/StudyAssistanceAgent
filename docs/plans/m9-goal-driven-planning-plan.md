# M9 目标驱动学习计划准备计划

> 当前状态：`ADMITTED / IN_PROGRESS`；确定性 Planner + 计划生命周期（生成/采纳/进度/重规划 + 跳过/逾期偏差信号；可选外部 AI 路径默认关闭；mastery 写入除外）
> 前置：M7 用户源生命周期与 M8 存储契约退出证据
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)

## 1. 范围与非目标

M9 规划基于 Goal、目标日期、用户等级、掌握度与授权 Source scope 生成版本化学习计划，按正式学习事件跟踪完成、
跳过、偏差和重规划。Planner 只能提出计划和建议，不成为第二套 mastery 或会话状态权威。

本阶段不实现写工具自主循环、checkpoint/EffectLedger 或 MCP；这些属于 M10。计划文件存在本身不批准新 API、
schema migration 或正式状态路径修改；可选外部 AI 接入的批准见 §4 的 v1.4 记录（默认关闭、窄口径）。

### 1.1 10K/100K 规模感知边界

M9 必须在 M8 的 100K capacity 能力上保持输入有界，但不把 100K chunks 全量送入 Planner：

- Planner 输入只允许 Goal、约束、课程/topic graph、Source 摘要、版本、授权 scope 和 mastery snapshot；
- 原始 chunk 正文只能通过受限检索按需获取，受 top-k、token、来源数、时间和成本预算控制；
- 禁止为生成计划扫描、拼接或注入全部 10K/100K chunks；
- stale、deleted、未发布或越权 Source 不得进入目录摘要、计划 grounding 或后续检索；
- PlanTask 优先引用稳定 topic/source identity；引用 chunk 时必须绑定 revision/generation，索引重建不得无故改变计划身份；
- embedding profile 或 SQLite/LanceDB 数据面切换不得改变 mastery 和计划状态语义；
- 无专业后端、无网络或无外部 AI 时，确定性目录/规则路径仍须可运行。

本节不批准 100K 真实数据或专业后端；真实 10K 数据属于拟议 M11，云端 profile 属于拟议 M12。可选外部 AI 的
批准见 §4 的 v1.4 记录（默认关闭、窄口径），且**不改变本节的输入有界约束**——AI 路径的输入与确定性路径同样有界。

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
| `M9-EXECUTION-DEVIATION` | `RESOLVED` | completed/skipped/overdue/replanned 事件；**未消费的**跳过+逾期≥3 或目标/约束变化触发重规划；触发时按 revision 追加消费台账；parent_revision 前向链；复用 review_scheduler 的 days_overdue |
| `M9-EXTERNAL-AI` | `RESOLVED` | 默认关闭、显式 opt-in；最小披露（不送 chunk 正文/用户数据/路径/凭据）；硬超时+成本预算；确定性 fallback |
| `M9-EVALUATION` | `RESOLVED` | 先修违反=0、stale/deleted Source 进入=0、确定性可重放=100%、输入有界可证明；遵循度先定性；延迟/成本已由 v1.5 解冻为**冻结评测**，但**范围仅限 M9 外部 AI 路径**（不是全项目评测声明）：CI 侧冻结**预算被强制执行**（确定性 stub，门禁），真实 provider 读数为显式 opt-in 且**非门禁** |
| `M9-COMPATIBILITY` | `RESOLVED` | review-plan/study-session API 不变；SQLite 可恢复可迁移不回写历史；90 题不退化；关闭时回退确定性 review-plan |

所有决策都需明确默认、覆盖、输入校验、失败、隐私/兼容影响、适用阈值、证据、责任人和日期。外部模型可以生成
自由文本不等于计划 schema 已闭合；没有确定性 fallback 的候选方案保持 `OPEN`。

八项决策的设计草案（非授权、不产生 `RESOLVED`）见
[`references/m9-decision-design-draft.md`](references/m9-decision-design-draft.md)。

## 4. 准入检查与批准记录

- [x] M7/M8 数据、scope、revision 和存储契约退出证据有效；
- [x] 八项强制决策全部 `RESOLVED`，schema 与 authority 不冲突；
- [x] 外部 AI 最小披露、失败和无 LLM fallback 可验证（v1.4 窄口径兑现：`tests/M9/test_plan_ai_adapter.py`
  逐字段断言载荷白名单、每一类失败收敛为回退、关闭时与无 adapter 逐字节相同；**注意**这只覆盖 1K 与
  stub provider，真实 provider 的延迟/成本/失败模式仍未验证）；
- [x] evaluation workload、样本与阈值口径冻结——**范围仅限 M9 外部 AI 路径**（v1.5，见 §4.3）；
  遵循度的人工评审口径**仍未**冻结（保持定性），故这不是全项目评测口径冻结；
- [ ] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表一致；
- [ ] 用户或项目负责人完成批准。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-09-22 |
| approval_reference | User instruction: 解冻 M9-EVALUATION 的延迟/成本维度（选项 1）；经裁定证据取两臂——CI 冻结预算执行用确定性 stub 且为门禁，真实 provider 读数为显式 opt-in、由 owner 自行运行且非门禁；评测 workload 冻结但限定在 M9 外部 AI 路径，不作全项目评测声明；本次不启动 M9 收口 |
| plan_revision | v1.5 |
| decision_set_version | m9-decision-set-v1 |

**批准历史**（`approval` 字段只承载当前批准，故历史在此保留；登记表侧的历史见 `admission_history`）：

| plan_revision | 批准引用 |
| --- | --- |
| v1.1 | （v1.2 之前的准入批准，原文未单独留存；其条件已由 v1.2 的实质变更取代，见 `admission_history`） |
| v1.2 | User instruction: 批准 M9 偏差触发语义由累计改为未消费（消费台账按 revision 追加，仅在阈值真正触发时消费，纯目标/约束变化不消费）；外部 AI 与 mastery 写入仍在范围外 |
| v1.3 | User instruction: 授权 M9 步骤 4（按需受限检索 + stale/deleted Source 拒绝），拆为 4a（受限检索接缝与预算）与 4b（principal 内部接缝与计划身份往返保真）；principal_id 保持内部接缝、不开公开请求字段；4a 为纯只读 accessor；范围扩张不写 admission_history；外部 AI 与 mastery 写入仍在范围外 |
| v1.4 | User instruction: 快速推进授权扩张范围到步骤 6；经裁定取窄口径（外部 AI + 仅 1K）——把 m9.external-ai 从 excluded 移入 included，在冻结任务集上比较确定性与 AI 路径，容量只在 1K 跑；不动 M9-EVALUATION（延迟/成本保持 deferred），故不需要 REVOKED；10K/100K 逐字记为 M8/M11 依赖、不触碰；mastery 写入仍在范围外 |
| v1.5 | User instruction: 解冻 M9-EVALUATION 的延迟/成本维度（选项 1）；经裁定证据取两臂——CI 冻结预算执行用确定性 stub 且为门禁，真实 provider 读数为显式 opt-in、由 owner 自行运行且非门禁；评测 workload 冻结但限定在 M9 外部 AI 路径，不作全项目评测声明；本次不启动 M9 收口 |

**v1.5 批准的具体依据**（供审计；不得拔高为「评测已完成」「延迟/成本已验证」「M9 退出条件达标」或
「M9 完成」）：owner 在候选项中选择**解冻 `M9-EVALUATION` 的延迟/成本维度**（这是唯一能真正解开 M9 收口的
动作）。随后三项裁定逐字为——证据口径取**两臂**（「两者都要：CI 冻结预算执行 + 本地标注真实读数」）；
workload 冻结范围取**「冻结，但限定在 M9 外部 AI 路径」**；arm B 执行取**「只建 harness，读数由你自己跑」**；
收口取**「不启动，只做解冻」**。故本批准**只解冻评测口径**：它**不**授予 M9 收口、**不**产生真实 provider
读数（arm B 本次未运行）、**不**作任何全项目评测声明、**不**冻结遵循度数值阈值。本变更**必然触发 §4 撤销**
（理由见 §4.3），与 v1.3 / v1.4 相反——那两次都在论证「为何不触发」。

**v1.4 批准的具体依据**（供审计；不得拔高为「步骤 6 已完成」或「评测 workload 已冻结」）：owner 的
指令原文为「快速推进授权扩张范围到步骤 6（含外部 AI 接入与 1K/10K/100K 容量验证，后者触及 M8 尚阻断的
数据面）」；因完整口径不可准入（理由见 §4.2），owner 在二选一裁定中选择**窄口径「外部 AI + 仅 1K」**，
其选项描述为「把 `m9.external-ai` 从 `excluded` 移入 `included`，冻结任务集上做确定性 vs AI 路径比较，
容量只在 1K 跑。不动 `M9-EVALUATION`（延迟/成本保持 deferred），故不需要 `REVOKED`，一次批准即可实施。
10K/100K 逐字记为 M8/M11 依赖，不触碰」。本批准**仅覆盖该窄口径**。

批准范围 `m9-plan-lifecycle-v1`：含 `m9.goal-plan-generation`、`m9.plan-adoption`、`m9.progress-event`、
`m9.replanning`、`m9.bounded-grounding-retrieval`、`m9.plan-identity-fidelity`、`m9.external-ai`；
**排除项只剩 mastery 写入**。
`M9-M7-EXIT` 与 `M9-M8-EXIT` 均已满足，八项强制决策全部
`RESOLVED`；`ADMITTED / IN_PROGRESS` 覆盖确定性计划生成与计划生命周期。

### 4.1 v1.3 范围扩张为何不触发 §4 撤销

`approval_scope` 按 [`stage-admission-gates.md`](../standards/stage-admission-gates.md) §4 只用于**缩小**边界，
故步骤 4 此前不在 `included` 内，本次属**显式范围扩张**，需要新的 owner 批准记录（v1.3）。

**不需要 `REVOKED` 过渡**：§4 要求撤销的前提是「强制决策、前置证据或兼容不变量发生实质变化」，本次三者均未变——

- `M9-EVALUATION` 早已携带 `STALE_DELETED_SOURCE_ENTRY_ZERO`（步骤 4 是**兑现**该判据，不是改判据）；
- `M9-PLANNER-INPUT-SCHEMA` 与本计划 §1.1 早已允许「原始 chunk 正文只经受限检索按需获取，受 top-k、
  token、来源数、时间和成本预算控制」；
- `M9-COMPATIBILITY` 的继承不变量不变（未改 review-plan / study-sessions API，未 bump `SCHEMA_VERSION`）。

**未登记 `admission_history` 条目**：该字段的 `from` / `to` 语义是准入状态
（`BLOCKED` / `ADMITTED` / `REVOKED`），而本次准入状态未变（`ADMITTED` → `ADMITTED`）；写入会造成语义错配。
范围扩张的留痕改由批准字段、本表与 §5.1 承担。

批准范围沿用 `m9-plan-lifecycle-v1`，但 `M9-EXECUTION-DEVIATION` 的触发语义在 v1.2 由「累计偏差 ≥ 3」
改为「未消费偏差 ≥ 3」。这是对已 `RESOLVED` 强制决策的**实质变更**，按
[`stage-admission-gates.md`](../standards/stage-admission-gates.md) §4「任何强制决策、前置证据或兼容不变量
发生实质变化后，准入必须改为 `REVOKED`；在重新澄清和批准前不得继续生产实施」。owner 于 2026-09-21 裁定
**严格按 §4 执行**：撤销过渡必须留痕，不接受把已 `RESOLVED` 的决策值原地改写。

过渡以登记表的追加式 `admission_history` 留痕，**live 字段保持 `ADMITTED / IN_PROGRESS`**：

| 过渡 | 时间 | 依据 |
| --- | --- | --- |
| `ADMITTED`（v1.1 批准）→ `REVOKED` | 2026-09-21 | `M9-EXECUTION-DEVIATION` 决策值在 v1.2 实质变更，v1.1 批准条件失效 |
| `REVOKED` → `ADMITTED`（v1.2 批准） | 2026-09-21 | owner 记录 v1.2 批准（批准人、批准时间、批准引用、计划修订、决策集版本五项齐全）后重新准入 |

没有把阶段真实翻转为 `REVOKED / NOT_STARTED`：那会让 [`tests/M9/`](../../tests/M9/) 成为「未开工阶段的生产面」
而与 `tests/regression/test_governance_contract.py` 的既有生产面检查冲突，并需要放宽该检查——即削弱一道真实的
门禁。owner 的重新批准与决策变更同时发生，阶段从未处于「停止实施」的运行状态，因此 `admission_history` 记录
§4 要求留痕的判定序列，`admission_status` 继续表达当前权威状态。

已知覆盖缺口（**已于步骤 4d 关闭**）：`admission_history[].reference` 此前未纳入
`tests/regression/test_governance_contract.py` 的 `_registry_references` 白名单枚举，因此该字段只受「必须是
仓库内可移植路径」的人工约束。现已折进同一白名单——`§7` 已明文要求该字段是可移植仓库路径，故复用既有校验器
即可，不另写一套。详见下方「准入留痕字段覆盖（步骤 4d）」。

### 4.2 v1.4 范围扩张为何不触发 §4 撤销

§4.1 的三条理由**专属于步骤 4**，不能照搬到外部 AI；本节给出 v1.4 自己的理由。

**完整口径不可准入**（owner 原始指令含 1K/10K/100K 容量验证）。三条独立理由：

1. [`stage-admission-gates.md`](../standards/stage-admission-gates.md) 记录 M6a 合并硬上限为 2,000 chunks，
   且 §5 明文禁止「通过提高限制或绕过生产 builder 伪造通过」——10K/100K 会直接撞上该上限；
2. 1K/10K/100K 分级是 **M8 自己的强制决策 `M8-BENCHMARK`**，而 M8 为 `BLOCKED / NOT_STARTED`、
   `approval_scope: null`、`implementation_start: null`；10K 真实数据属拟议 M11（同为 `BLOCKED`）；
3. §4 禁止 `approval_scope` 把被排除的数据、后端或下游阶段**隐式提升**为已批准。

另有决策冲突：原指令要求验证延迟与成本，而 `M9-EVALUATION` 的 `RESOLVED` 值以
`ADHERENCE_QUALITATIVE_FIRST_LATENCY_COST_DEFERRED` 结尾——解除该暂缓属对已 `RESOLVED` 决策的**实质变更**，
按 §4 会强制 `REVOKED`。owner 遂裁定取**窄口径**，**不动** `M9-EVALUATION`。

**窄口径为何仍不需要 `REVOKED`**：§4 的撤销前提是「强制决策、前置证据或兼容不变量发生实质变化」，本次三者均未变——

- `M9-EXTERNAL-AI` 早已 `RESOLVED`，且其值（默认关闭 / 最小披露 / 硬超时+成本预算 / 确定性 fallback）
  正是本次要实现的内容——本次是**兑现**它，不是改判据；
- `M9-EVALUATION` **原值不动**，延迟/成本维度仍 `DEFERRED`；
- `M9-COMPATIBILITY` 的继承不变量不变（未改 review-plan / study-sessions API，未 bump `SCHEMA_VERSION`，
  默认关闭时确定性路径逐字节可运行）。

**未登记 `admission_history` 条目**：与 §4.1 同理——`from` / `to` 的语义是准入状态，本次为
`ADMITTED` → `ADMITTED`，写入会造成语义错配（且会被
`test_admission_history_records_are_well_formed` 的 `from != to` 断言判红）。留痕由批准字段、批准历史表与本节承担。

**本次明确不做**（逐字记为后续阶段依赖，不触碰）：10K/100K 容量验证（M8 / M11）、`M9-EVALUATION` 的
延迟/成本维度解冻、评测 workload 的整体冻结、mastery 写入。

### 4.3 v1.5 决策值变更为何**触发** §4 撤销

本节是 §4.1 / §4.2 的**镜像**：那两节论证「为何不触发」，本节论证「为何必然触发」。§4.2 末段早已逐字
预言本次——「解除该暂缓属对已 `RESOLVED` 决策的**实质变更**，按 §4 会强制 `REVOKED`」。v1.5 做的正是
解除该暂缓，故这是 M9 **第一次真正触发** §4 的变更。

`M9-EVALUATION` 的 `RESOLVED` 值由 `..._ADHERENCE_QUALITATIVE_FIRST_LATENCY_COST_DEFERRED` 改为
`..._ADHERENCE_QUALITATIVE_FIRST__LATENCY_COST_FROZEN_M9_EXTERNAL_AI_PATH_ONLY__
DETERMINISTIC_STUB_BUDGET_ENFORCEMENT_CI_GATING__REAL_PROVIDER_READING_OPT_IN_NON_GATING`。前五段逐字
保留；新增三段分别承载范围限定（只限 M9 外部 AI 路径）、CI 臂证明的对象（**预算被强制执行**，而非
性能被测量）与 arm B 的地位（opt-in、非门禁）。按
[`stage-admission-gates.md`](../standards/stage-admission-gates.md) §4，这要求撤销过渡留痕：

| 过渡 | 时间 | 依据 |
| --- | --- | --- |
| `ADMITTED`（v1.4 批准）→ `REVOKED` | 2026-09-22 | `M9-EVALUATION` 决策值在 v1.5 实质变更（延迟/成本维度解冻为冻结评测），v1.4 批准条件失效 |
| `REVOKED` → `ADMITTED`（v1.5 批准） | 2026-09-22 | owner 记录 v1.5 批准（五项批准字段齐全）后重新准入 |

**live 字段仍保持 `ADMITTED / IN_PROGRESS`**，与 §4.1 同理（这是该机制**第二次**使用）：把阶段真实翻转为
`REVOKED / NOT_STARTED` 会让 [`tests/M9/`](../../tests/M9/) 成为「未开工阶段的生产面」，与
`test_unstarted_stages_do_not_add_future_production_surfaces` 冲突，必须放宽该检查才能通过——即削弱一道真实
门禁。owner 的重新批准与决策变更同时发生，阶段从未处于「停止实施」的运行状态，故 `admission_history`
记录 §4 要求留痕的判定序列，`admission_status` 继续表达当前权威状态。

**未变项**（逐条核对，防止把本次读成范围扩张）：`approval_scope` 与 `scope_id`（仍 `m9-plan-lifecycle-v1`）、
`implementation_start`（仍 `AUTHORIZED`）、其余七项强制决策、以及 `M9-EXTERNAL-AI`——后者**刻意不动**，
因为本次是**兑现**其既有的 `HARD_TIMEOUT_COST_BUDGET__DETERMINISTIC_FALLBACK`，改它会是第二次实质变更、
第二次 §4 过渡。

**本次明确不做**（逐字清单）：10K/100K 容量验证（M8 `BLOCKED` / M11 拟议）；任何**全项目**评测声明
（本次口径只覆盖 M9 外部 AI 路径）；遵循度的**数值**阈值（保持定性）；把 arm B 用作门禁或退出证据
（它是 opt-in、非门禁、本次未运行）；mastery 写入（`m9.mastery-write` 仍在 `excluded`）；M9 收口
（`COMPLETE` 需要 §4 要求的独立 `completion_approval`，本次**不申请**）。

**冻结口径的诚实边界**（写入本节以免被后读高估）：CI 臂用确定性 stub 驱动**真实**的
`build_anthropic_proposer(client_factory=…)` 接缝，证明的是**预算被强制执行**——其中 `prompt` 预算在调用
provider 之前返回（provider 调用数为 0），`cost` 预算在收到**合法**置换时仍丢弃它（硬上限而非告警阈值）。
但 stub 下**没有任何性能读数**：延迟是桥接开销，成本由脚本化 usage 算出。真实 provider 的延迟 / 成本 /
失败模式**仍未验证**，只能由 arm B 读，且必须由人显式启动。另有三项预算**不在本地执行**：
`max_input_tokens`（本地无 tokenizer，故用字节预算）、`model_timeout_seconds` 与 `max_output_tokens`
（均传给 provider）；`deadline_seconds` 的守卫**放弃线程而非取消它**。

### 4.4 v1.5 之后的两处实现修正为何**不**触发 §4 撤销

本节与 §4.3 成对：§4.3 论证 v1.5 **必然触发**，本节论证紧随其后的两处缺陷修正**不触发**。
判据是同一把尺子——§4 看的是**强制决策的实质变化**，不是代码变动本身。

**修正一：外部 AI 路径的单轮 output 预算。** `PlanAILimits.max_output_tokens`（累积，2048）曾被直接
当作 `create_turn` 的 `max_tokens` 传下去，而 `llm_client.create_turn` 硬拒大于
`MAX_TURN_OUTPUT_TOKENS`（1024）的值。于是**默认配置下**每次调用都在发出任何 HTTP 请求之前抛
`ValueError`，被回退路径收敛成 `provider_unavailable`——整条外部 AI 路径静默失效，而既有测试全绿
（它们一律经 `proposer=` 注入，绕过该调用点）。现拆成两个字段：累积值只送 provider，单轮值在本地执行。

**修正二：分日的每日容量。** `_distribute` 把 `total_days`（请求窗口）当成硬截断，排不完的任务被一次性
倾倒进一个不设上限的「第 `total_days + 1` 天」——实测默认请求下该天 114 个任务 / 3890 分钟，而当日
可用容量 110 分钟。现改为**逐天追加**，追加的天受同一容量约束。

**为何两者都不触发 §4：**

1. **`M9-EXTERNAL-AI` 的决策值不含任何数字**——`OPT_IN_DISABLED_BY_DEFAULT__MINIMAL_DISCLOSURE_
   NO_CHUNK_BODY_USER_DATA_PATHS_CREDENTIALS__HARD_TIMEOUT_COST_BUDGET__DETERMINISTIC_FALLBACK`。
   2048 / 1024 是**实现常量**，不是判据。修正一是把既有的 `HARD_TIMEOUT_COST_BUDGET` 从句面条款
   变成**真正生效**的条款（修正前该子句根本没有执行点），属**兑现**而非**改判据**。
2. **`M9-EVALUATION` 的 v1.5 值不动**，`approval_scope` / `implementation_start` / 其余七项决策均不动。
3. **两个冻结摘要逐字节不变**：`_workload_digest` 只哈希 `_WORKLOAD`（name/goal/course/required/
   excluded），`_budget_scenario_digest` 只哈希 `_BUDGET_SCENARIOS`（各 limits 字典只含
   `max_prompt_bytes` / `max_answer_bytes` / `deadline_seconds`）。修正后重算，两者与 v1.5 记录值
   逐字节相同，故 1K 与预算矩阵的历史读数**继续可比**。
4. **`plan_id` 不受分日修正影响**：`_plan_id` 哈希的是请求字段与**派生输入摘要**（按最终顺序的
   `task_id`/`reviewed`/mastery 序列），不含天数、分组或 `total_minutes`。突变探针证实：把 `_distribute`
   换成「只产出一个空天」的桩，`plan_id` 逐字节不变。故计划身份这一兼容不变量未被触碰。

**确实变化且必须记录的两处可观行为**（属**在既有声明内的行为纠正**，不是判据变更）：

- 装不进窗口的计划 `total_days` 变大（默认请求 15 → 52，`os`/1 小时 15 → 19）。**超出窗口本就是声明允许的**
  ——`review_plan.py` 的「剩余任务追加到最后一天（如果超出天数）」是唯一的正面声明，M9 逐字继承；
  违反声明的是**每日容量**（`review-plan` 技能：「每天学习时间不超过 `hours_per_day × 60 + 10` 分钟」）。
- `total_days` 现在回报**真实**天数而非请求窗口值，`total_days` 与逐日明细自此自洽。
- **与 `review_plan.py` 刻意分叉**：该服务有同一处缺陷，但 `platform/tests/test_review_plan.py` 的
  `actual_days <= max_days + 1` 明确容忍它，且该套件按仓库约定**冻结不动**。故修正只落在
  `goal_planner.py`，两个服务在这一点上**有意不一致**，不得被读成遗漏。
- **本修正不消除的残留**：`and day_tasks` 守卫保证每天第一个任务必被放入，故单条任务时长超过当日容量时
  （`hours_per_day=0.5` 下容量 20 分钟而进阶任务 50 分钟）该天仍会超出。保证是「**每天至多一个**任务
  造成超出」，不是「绝不超出」——`tests/M9/test_day_distribution.py` 把它钉成可见事实。

**本次明确不做**（与 §4.3 同）：不 bump `plan_revision`、不新增 `approval_reference`、不新增
`admission_history` 记录（§4 的两条触发条件——决策值变化与批准条件失效——均未发生）、不新增公开路由、
不申请 M9 收口。

## 5. 获准后的拟实施顺序

1. 先冻结 planner input、plan、mastery 和 progress event schema；
2. 以确定性规则生成最小计划并验证现有 API/SQLite 兼容；
3. 接入只读 mastery snapshot、topic graph 和授权 Source 摘要，不复制领域写入，并验证输入规模不随 chunk 总量线性增长；
4. 接入按需受限检索，冻结 top-k/token/source/time 预算和 stale/deleted Source 拒绝行为；
5. 实现偏差事件与版本化重规划，再增加可选外部 AI adapter；
6. 在冻结任务集上比较确定性与 AI 路径，并在 1K capacity 规模下验证输入预算，达标后才扩大 rollout。
   **延迟/成本维度已由 v1.5 解冻并冻结在 M9 外部 AI 路径范围内**（见 §4.3）：CI 侧冻结预算执行，
   真实 provider 读数走显式 opt-in。**10K/100K 仍不在范围内**：那是 M8（`BLOCKED`）/ M11 依赖。

拟新增 `tests/M9/` 覆盖 schema、authority、deviation/replan、provider privacy/failure、fallback 和兼容；评测必须验证
source grounding 与先修关系，而非只检查 JSON 可解析。退出条件包括正式 mastery 只有一个写入权威、计划可重放、
Planner 输入不随 chunk 总量线性膨胀、stale/deleted Source 零进入、默认学习闭环与 90 题不退化、无 LLM 路径可
运行，以及冻结评测达标。

**退出条件的挣得情况**（截至 2026-09-22，v1.5）：**在各自声明的范围内**，七项条件已全部挣得——正式
mastery 只有一个写入权威（`tests/M9/test_mastery_write_authority.py`，见 §5.1）、计划可重放、Planner 输入
不随 chunk 总量线性膨胀（1K 规模已证）、stale/deleted Source 零进入、默认学习闭环与 90 题不退化、无 LLM
路径可运行，以及**冻结评测达标**（`M9-EVALUATION` 的延迟/成本维度已由 v1.5 解冻，冻结口径见 §4.3）。

**但这不等于「M9 退出条件已全部挣得」可以读成「M9 完成」**，三处限定必须一起读：

1. 冻结评测的**范围**是 M9 外部 AI 路径，**不是**全项目评测；遵循度仍是定性，无数值阈值；
2. 真实 provider 的延迟 / 成本 / 失败模式被**刻意**排除在门禁判据之外，且**仍未验证**（arm B 本次未运行）；
3. `COMPLETE` 需要 §4 要求的**独立 `completion_approval`**，本次**不申请**。是否作退出就绪声明是
   **另一个决定**，不得从 v1.5 推定。

### 5.1 实现进度

| 步骤 | 状态 | 证据 |
| --- | --- | --- |
| 1 冻结 planner input / plan / mastery / progress event schema | 已完成 | `tests/M9/test_goal_planner.py`；mastery schema 已落到只读投影 `MasteryProjectionService.mastery_by_file()`（attempt / correct / last_mastered），见 `tests/M9/test_mastery_projection.py` |
| 2 确定性规则生成最小计划 + 验证 API/SQLite 兼容 | 已完成 | `tests/M9/test_goal_planner.py`、`tests/M9/test_plan_lifecycle.py` |
| 3 只读 mastery snapshot / topic graph / Source 摘要 | 已完成 | mastery 投影：`platform/app/mastery_projection.py`、`tests/M9/test_mastery_projection.py`；授权 Source 摘要：`platform/app/source_summary_projection.py`、`tests/M9/test_source_summary_projection.py`；topic graph（先修关系）：`platform/app/topic_graph_projection.py`、`tests/M9/test_topic_graph_projection.py`。三者均已接入确定性 Planner |
| 4a 受限检索接缝与四类预算（`m9.bounded-grounding-retrieval`） | 已完成 | `platform/app/plan_grounding.py`、`tests/M9/test_plan_grounding.py`；装配于 `main.py` |
| 4b principal 内部接缝与计划身份往返保真（`m9.plan-identity-fidelity`） | 已完成 | `tests/M9/test_plan_identity.py`；`platform/app/goal_planner.py` 的身份键与 `platform/app/plan_lifecycle.py` 的往返保真 |
| 4c 复习历史活投影（`m9.review-history-projection`）——步骤 3 已记录残留的修复，**非**范围扩张 | 已完成 | `platform/app/review_history_projection.py`、`tests/M9/test_review_history_projection.py`；装配于 `main.py` |
| 4d 准入留痕字段覆盖（`m9.admission-history-reference-coverage`）——关闭 §4 已记录缺口，**纯治理测试硬化、非能力** | 已完成 | `tests/regression/test_governance_contract.py` 的 `_registry_references` 与 `test_admission_history_records_are_well_formed` |
| 5 偏差事件与版本化重规划 | 已完成 | `tests/M9/test_deviation_signals.py`：跳过+逾期 ≥ 3、目标/约束变化、parent 前向链、确定性重放；`tests/M9/test_deviation_consumption.py`：未消费阈值、消费台账、重复调用幂等 |
| 6 可选外部 AI adapter 与冻结任务集比较（`m9.external-ai`，**窄口径**） | 已完成（**窄口径**） | v1.4 批准（见 §4.2）；实现见 `platform/app/plan_ai_adapter.py`、`tests/M9/test_plan_ai_adapter.py`；冻结任务集比较见 `tests/M9/test_plan_ai_benchmark.py`。**步骤 6 整体未闭合**：10K/100K 容量验证逐字记为 M8（`BLOCKED`）/ M11（拟议）依赖，本次不触碰 |
| 6+ 评测口径冻结：`M9-EVALUATION` 延迟/成本维度解冻（**治理变更，非新能力**） | 已完成 | v1.5 批准（见 §4.3，**触发 §4 撤销过渡**）；CI 臂见 `tests/M9/test_plan_ai_benchmark.py`（冻结预算矩阵，驱动真实 `client_factory=` 接缝，`-m m9_benchmark`）；opt-in 真实读数见 `tests/M9/test_plan_ai_provider_smoke.py`（`online` + skip 门控，**本次未运行**、非门禁）。**范围仅限 M9 外部 AI 路径**；真实 provider 性能仍未验证 |
| **退出条件证据**：唯一写权威（**非步骤、非能力、非范围扩张**） | 已交付 | `tests/M9/test_mastery_write_authority.py`：动态枚举 `platform/app/` 全部源文件（当前 60 个）后断言写 `study_sessions`/`answer_attempts` 的模块**恰好**是 `learning_store.py`，且 M9 的 8 个模块与写权威**导入不可达**（AST 闭包断言）。**它不新增任何写路径**——`m9.mastery-write` 仍在 `excluded`，本增量只把 §1/§2 的继承不变量从当前事实钉成可测不变量，故**不改 `plan_revision`、不写 `admission_history`** |

**步骤 6 窄口径的实现约定（含一处跨阶段只读耦合，逐字登记）**：

- **跨阶段只读耦合（M9 → M7）**：`tests/M9/test_plan_ai_benchmark.py` 只读复用 M7 的
  `tools/run_m7_benchmark.py` 的 `build_corpus` 与 `publish_sources`（`sources=1, documents=100, units=10`
  = 1000 chunks），以及其 `_install_unit_parser`（用后**恢复**，避免全局替换泄漏到同进程其他测试）。
  M7 已 `ADMITTED / COMPLETE` 且 `m7.1k-3k-benchmark-implementation` 本在其批准范围内，故该复用不需要
  新批准；**本增量不修改 M7 的任何生产文件**，只在测试进程内调用其生成器。语料物化到临时目录、
  **不落任何二进制、不持久化、不触碰 M8 数据面**。
- **不新增公开路由**：AI 路径经既有 `POST /api/v1/plans` 可达，故 `PUBLIC_API_PATHS` 与路由 docstring
  均不改（`tests/TEST_PLAN.md` §5.2 记录：后续阶段新增默认公开路由没有合法登记渠道）。
- **AI 产出完整替代计划，但采纳权在确定性侧**：`plan_id` 由**最终任务序**重算，故两条路径的身份天然
  不同——这正是 §7 要求比较的两个对象。校验器保证 AI 计划**不会更差**：置换成员、先修序、必选置顶
  在 AI 提出之后**重新施加**。
- **Planner 不 import adapter**：`goal_planner._ai_order` 按鸭子类型取 `task_id` / `topic` / `difficulty` /
  `tags`，使 Planner 的源码级护栏（不得出现 `llm_client` / `content` / `split_headings`）**结构上**成立，
  而不是靠措辞回避。
- **默认关闭是恒等操作**：未设 `SA_PLAN_AI_ENABLED` 时不构造 proposer（连 token 都不读），
  `generate()` 输出与接入前**逐字节相同**（含 `plan_id`）；CI 不设该 env。

偏差信号实现约定：逾期复用 `ReviewSchedulerService.overdue_by_file()` 的 `days_overdue`（只读复习历史，
不构建 chunk 索引，保持 Planner 输入有界）；偏差按 task_id 去重后计数，跳过与逾期不重复计入同一任务；
`replan` 记录 `replan_reason` 以便审计重规划由何触发。Plan 记录自描述（回显 `course` / `hours_per_day` /
`constraints`），重规划据此保真还原范围；旧 revision 只读保留，`revision_id` 与 `parent_revision_id`
构成前向链。`persist_generated` 幂等：同一 plan_id 重复生成不重置已存计划状态。plan_id 现在包含
**派生输入摘要**，因此该幂等性成立的前提是「派生输入未变」——复习/mastery 状态变化会得到新的 plan_id，
旧计划记录不被覆盖、不被回填，只是不再被重新生成命中（详见下文「计划身份修复」）。

消费约定（v1.2 语义）：偏差触发条件不是「累计 ≥ 3」而是「**未消费** ≥ 3」——未消费 = 当前偏差
task_id 集合减去台账里已消费的并集。台账键 `deviation_ledger` 落在 `plans.payload`（无 DDL），
**追加式**，每个产生的 revision 恰好一条，条目含 `revision_id` / `trigger` / `consumed_task_ids`
（`sorted` 以保证 payload 字节稳定，重放可比对）；消费只在偏差阈值**真正**被满足时发生，
纯目标/约束变化的重规划写空集，因此不会吞掉未达阈值的 1~2 个偏差；未触发的 `replan` 调用
**不写盘**，所以也不消费任何东西——这是结构保证而非额外分支判断。

关于决策文本里的 `replanned` 事件：它**不在** `progress_events` 词表内（词表仍只有 `completed` /
`skipped` / `overdue`），而是由台账条目落地——每个产生的 revision 恰好一条台账记录，
`trigger` 字段即该次重规划的原因。`M9-EXECUTION-DEVIATION` 的值仍保留 `REPLANNED_EVENTS` 记号，
指的是这条落地路径，不是 `progress_events` 里的一行。

刻意的取舍：消费是单调的，已消费的偏差任务即使后来再次逾期也不再触发（宁可漏报「复发偏差」，
也不产内容相同的幻影 revision），`tests/M9/test_deviation_consumption.py` 用测试钉住这条取舍。
残留上限：偏差不进入 `generate()`，因此偏差触发的重规划内容仍与上一个 revision 逐字节相同，
本语义只能把幻影 revision 限制为「每批新偏差最多一个」，不能归零；已膨胀的存量 revision 链
不会回填修复（append-only），只是停止增长。整条 record 的字节级重放仍做不到（`generated_at` /
`created_at` / `updated_at` 取 `datetime.now()`，逾期投影依赖 `datetime.now().date()`）；
保证的是决策确定性 + 内容确定性 + 台账字节稳定。

升级行为：改造前的旧库没有 `deviation_ledger` 键，缺键即空集，因此首次重规划会按「累计」语义
多产生一个 revision，写入台账后即收敛到新语义；不需要回填迁移。

mastery 只读投影实现约定：投影在 `platform/app/mastery_projection.py`（`MasteryProjectionService`），
与 `ReviewSchedulerService.overdue_by_file()` 同形——纯读、不写 mastery、不写会话状态、不构建 chunk
索引、不读 chunk 正文；权威写入仍是 `StudySessionService` / 领域仓储（`M9-MASTERY-AUTHORITY` 未变）。
聚合身份是**知识条目的 file 路径**，不是 `study_sessions.topic` 那样的自由文本。解析**三分支**，
逐字对齐 `StudySessionService._log_review`：`sources[0].file` → `questions[0].question.source_file`
→ 回退 `knowledge/{course}/{topic}.md`。中间分支不是可选项：漏掉它会让「无检索出处但有出题出处」的会话
把 mastery 记到与复习历史**不同**的文件上，正是「不猜」要防的失效模式；两者不能共享代码（`_log_review`
必须**记录**不可映射的回退，投影必须**丢弃**它），故等价性由 `test_resolution_matches_log_review_rule`
按三种输入形态钉住。三个分支的候选键都要过 `entry_exists` 校验：`sources[0].file` 可能是 `extra://…`
这类非知识库标识，回退键由自由文本 topic 拼出（须挡住 `../` 越界与非法后缀）。不可映射或条目不存在的
会话**排除而非补 0**。输入有界：一次 join 聚合语句（跨界只有两个短出处字符串，不读整份 payload）+
每个去重候选键一次 stat。数据面新增 `SqliteLearningStore.aggregate_attempts_by_session()`（跨会话读取，
既有 `list_answer_attempts` 只按单会话读）。Planner 侧：`GoalPlanTask` 增补带默认值的
`mastery_attempts` / `mastery_correct` / `mastery_last_mastered`；`_stable_order` 在 `reviewed` 之后、
难度优先级之前插入一档粗粒度 `_mastery_rank`（0 无证据 / 1 有尝试未答对 / 2 已答对）；`summary.mastery`
给出三档计数。依赖注入为**活对象且可空**：未注入时全部任务落在桶 0，排序与接入前逐字节一致。

授权 Source 摘要实现约定：投影在 `platform/app/source_summary_projection.py`，与 `mastery_projection.py` 同形
——纯读、不写 Source 生命周期、不写会话状态、不构建 chunk 索引、不读 chunk 正文；权威写入仍是
`SourceLifecycleService` / 领域仓储。步骤 3 的第三个投影（topic graph）随后已交付，见下文「先修关系实现约定」。

(a) **「可用」规则**：`is_usable_for_retrieval(record)` = `published_generation is not None and state in
{READY, DEGRADED}`，逐字对齐 `source_offline.py` 的离线取快照前置判断（那是规范来源）。该规则在
`source_offline.py` 内**联**、没有可 import 的谓词，本次选择在新模块内定义并**记录这份重复**，而不改 M7
生产文件——两处若分歧以 `source_offline.py` 为准。规则矩阵（7 态 × 有无 generation = 14 例）由
`tests/M9/test_source_summary_projection.py` 钉住。其中 `DEGRADED + 无 generation` 是**唯一**能由生命周期自然
到达的 DEGRADED 形态（`transition_source` 只在 `target_state is READY` 时接受 revision，带 generation 的
DEGRADED 只经 `begin_sync_run` 的过期租约回收产生），因此「DEGRADED ≠ 可用」是实测结论而非猜测。

(b) **`usable` ≠ M7 的 `authorized_source_ids`**：后者等于「`list_sources` 减去隐藏态」，**包含** REGISTERED /
SYNCING / DISABLED；本投影的集合严格更小。故输出字段一律叫 `usable`，不叫 `authorized`——混用会让
「已注册但未发布」的源被当成可检索源。

(c) **摘要今天不影响任何计划内容**：registry 只能存 `user-<uuid7>`（`SourceRecord.__post_init__` 校验
`source_type == "user_registered"`），知识包 id `knowledge-pack` 不在 `source_records` 里，而 `PlanTask.file`
恒为 `knowledge/{rel}`——两个命名空间之间**没有映射**；且本仓 checkout 下 `platform/.cache/` 没有
`source_registry.sqlite3`，懒守卫因此恒返回空表，计数在实践中结构性为 0。本增量交付的是**规则层证据 +
步骤 4 的输入接缝**，不是「计划内容因此变干净了」：它证明 `usable` 规则在 Source 会进入的那条边界上正确
排除了未发布 / 未就绪 / 禁用 / 待删 / 已删，而**不是**端到端的检索隔离。

(d) **无公开 scope 选择通道**（残留）：`GoalPlanRequest` **未**新增 `principal_id`，`generate()` 只多了一个
可选关键字参数，`main.py` 的既有路由不传它——即「已装配但生产休眠」，与 `LazyUserSourceSearch` 已接入
`MultiRecallService` 而无任何路由传 principal 的既有形态一致。之所以不开该通道：`event_id =
sha256(f"{plan_id}|{task_id}|{event}")[:16]` 配 `INSERT OR IGNORE`，而 `_plan_id` 不含 principal，两个 principal
生成同一 Goal 会撞同一 `plan_id` 与同一行计划，B 的 `completed` 与 A 的字节相同而被静默去重、把 A 的任务
标成完成；且 `_response_to_record` **没有 `summary` 键**、`_plan_to_request` 只还原 5 个字段，principal 一旦
进入计划路径，`replan` 会以无 principal 重新生成、源范围静默改变，违反上一增量写进本节的不变量「Plan 记录
自描述…重规划据此保真还原范围」。该通道与检索预算一起延后到步骤 4 处理。

(e) **只读边界**：本模块只声称**领域级**只读（不写生命周期、不写会话、不构建 chunk 索引、不读正文），
**不**声称文件系统零变更——`SqliteSourceRegistry._configure` 对每条连接都执行 `PRAGMA journal_mode=WAL`，
`_initialize_or_validate` 会 `mkdir` 且可能建表。因此懒装配把 `is_file()` 守卫放在构造**之前**
（`SqliteSourceRegistry.__init__` 会建库），测试用「构造即失败」的 monkeypatch 钉住它，并断言
`platform/.cache/source_registry.sqlite3` 在整套测试后仍未被创建。

(f) **不得改用整数计数捷径**（残留陷阱）：`count_non_deleted_sources` 是第二个 bulk 读，其 WHERE 为
`state != DELETED`，**包含** `DELETE_PENDING`；测试用 monkeypatch 让它一旦被调用即失败。另有残留：隐藏态由
`list_sources` 的 WHERE 构造性排除，故投影**无法报告**被排除的计数——凭空补一个 0 会把「没读」伪装成
「读了且为空」，证据改由测试提供。该用例的 `DELETE_PENDING` / `DELETED` 必须用**直接 SQL** 种入（经服务层
种用例是空转的），且它钉的是 M7 既有 WHERE 子句，**不是**本增量新增的证据。

`M9-EVALUATION` **未**因此有进展：其 `STALE_DELETED_SOURCE_ENTRY_ZERO` 是**检索路径**判据，本增量只到规则层。
接缝语义：`summary["sources"] = {"usable": N}` 只在「传了 principal 且注入了投影」时出现——键的出现取决于
**输入**而非结果，否则「键不存在」会同时意味着「没传 principal」和「传了但一个可用源都没有」，调用方无法
区分。未传 principal 时 `summary` 与接入前逐字节一致；`_plan_id` / `_derived_digest` 未改动，故目录变化
不 churn 计划身份（与「摘要只覆盖本计划范围内任务」同一原则）。本次**未新增任何公开路由**，
`PUBLIC_API_PATHS` 与路由 docstring 均未改动。

先修关系（topic graph）实现约定：投影在 `platform/app/topic_graph_projection.py`（`TopicGraphProjection`），与
`mastery_projection.py` 同形——纯读、不写知识库、不写会话状态、不构建 chunk 索引、不读 chunk 正文；权威写入仍是
知识条目自身（frontmatter 由人工维护）。**不需要走 §4 的 `REVOKED` 过渡**：§1.1 已把「课程/topic graph」明确列为
Planner 允许的输入之一，且 `M9-PLANNER-INPUT-SCHEMA` 只要求「输入有界、不随 chunk 总量线性膨胀」——本投影只读
frontmatter 一行，满足该约束，决策值未变。

(a) **数据载体**：条目 frontmatter 新增 `prerequisites:`，值是**与依赖条目同目录的兄弟文件 stem**（不含 `.md`、
不含路径分隔符）。**刻意不做跨目录/跨课程解析**：`knowledge/interview/co/` 是嵌套目录，全树有 4 个 basename 撞名
（`cache-mapping`、`heap-priority-queue`、`sorting`、`stack-queue`），而 `GoalPlanRequest.course` 默认 `None` 覆盖全部
课程——按课程解析会把 `co` 的先修**确定性地**连到 `interview/co` 的同名文件上，且因为是确定性的，不会有任何
flaky 测试来暴露它。同目录解析无歧义。**丢弃而非补**：目标不存在、自环、越界 stem、`_templates`/`_inbox`、无
`title` 的文件一律丢弃该边，不猜测——与 `mastery_projection` 的「不可映射则排除」同一纪律。边由人工拟定、owner
审 diff，**不**从 tags 共现或 README 顺序推导。

(b) **只支持行内方括号形式**（残留陷阱）：`markdown_parser._YAML_FIELD_RE` 不匹配块状 YAML（后续行写 `- a`），
故块状形式会被**静默**解析成空列表——不报错、不告警。`tests/M9/test_topic_graph_projection.py` 因此按**原始文件**
断言 60 条只用行内形式，并逐条断言「声明的 stem 数 == 解析出的边数」，拼错一个词即失败。
`parse_frontmatter` 只对 `tags` 与 `prerequisites` 做列表解码，其余键一律保留为字符串——刻意不「看到方括号就当
列表」，那会改变既有消费方对未知键的取值形态；`tags` 行为逐字节不变。

(c) **`unorderable()` ≠ 精确 SCC**：它返回 Kahn 剩余集 = **参与环 ∪ 环下游**，故不叫 `cyclic`——与
`source_summary_projection` 把集合叫 `usable` 而不叫 `authorized` 同一纪律。它是**图级**诊断，与 Planner 侧按本计划
任务集算出的强制释放集**不同名同义**，调用方不要混用。`graph()` 的键是全部在场条目（无边者为空集），边已与在场
条目求交（指向不存在条目的先修在本投影里不存在，而不是留一个悬空引用）。

(d) **Planner 接入**：构造函数的可空活对象依赖 `topic_graph` **追加在参数末尾**——插在 `source_summary` 之前会
静默重绑位置参数调用方。`_graph()` 未注入时返回 `{}`，与 `_mastery()`/`_source_scope()` 同形：依赖缺省是守卫，
不是错误。`generate()` 里**整轮只读一次**图（生成途中图若变化，排序与违反计数会基于不同快照）。排序改为
**Kahn 拓扑排序 + 确定性堆**，堆键是既有的 4 元组 `(reviewed, mastery 桶, 难度优先级, file)`；必须用 `heapq`
而不是队列（队列会让输出依赖邻接表插入顺序），且 `file` 唯一故堆元组全序、`heapq` 永不比较 `GoalPlanTask` 对象。
三处要害：

1. **入度必须与本计划任务集求交**（`_present_edges`）：先修若被 `excluded_topics` 移除，它在任务集里就不存在，
   该边在本计划内也不存在。用原始计数会让入度永远 > 0，把「先修缺失」**伪装成「环」**，再被强制释放机制吞掉。
   求交同时确立了「用户显式排除优先于图边」这一优先级裁定。
2. **空图显式短路**：`if not graph: return sorted(tasks, key=_order_key)`。把「逐字节相同」从「Kahn 在空图上恰好
   退化」升级为可指认的性质，并让 `None` 与 `{}` 走同一条路径、不会各自漂移。
3. **环上节点按堆键顺序强制释放并继续**，保证输出是全序且确定性；Planner 不静默修复环——环本身由图投影的
   `unorderable()` 报告，计划侧只保证终止与可重放。

(e) **置顶语义（owner 裁定：先修优先）**：必选主题 ∪ 其**传递**先修闭包构成置顶块。闭包必须传递——块对先修
封闭 ⇒ 没有边从块外进入 ⇒ 整块前移不可能违反任何边；一级闭包会让「先修的先修」留在块外，静默破坏全局序。
块内**必须再跑一次拓扑排序**：朴素按用户优先级排是错的（required `[B(0), A(1)]` 而 A 是 B 的先修时会产出
`[B, A]`）。内层 Kahn 的键用 `(用户优先级, 入参下标)`，**不是 `file`**——今日靠 `sorted` 的稳定性处理同名必选主题，
改用 `file` 会在那一刻偏离。闭包遍历带 `seen`，否则环上死循环。

**本增量修掉一处实现缺陷（由新增用例发现）**：块内短路分支原先的门是「闭包没新增节点」
（`len(pinned) == len(user_rank)`），这是错的——必选主题**互为先修**时闭包恰好只含这两个节点，但块内**存在**边，
走 `sorted` 就产出 `[B, A]` 并违反那条边。门已改为 **`not edges`**（无先修边，含未注入图）；无先修边时 `pinned`
恒等于必选主题集且内层 Kahn 的键退化为 `(用户优先级, 入参下标)`，与 `sorted` 的稳定排序结果逐字符相同，故该短路
纯属可指认的优化，不改变接入前的行为。`test_pin_required_respects_prerequisites_inside_the_block` 钉住修复后的语义，
`test_unrelated_required_topics_keep_the_user_rank_order` 钉住短路被跳过时块内顺序仍与接入前一致。

(f) **`summary["prerequisites"] = {"edges": N, "violations": M}`**，仅在注入图时出现（键的出现取决于**输入**，
与 `summary["sources"]` 同一规则），未注入时 `summary` 逐字节不变。`N` = 本计划任务集内的先修边数；`M` = **最终
顺序违反的边数**（依赖任务排在先修之前）。`violations` 刻意定义为「最终顺序违反的边数」而**不是**「置顶块冲突数」：
它只从最终顺序算出，所以「同一 `plan_id` ⇒ 相同 `summary`」这条不变量**结构上**成立（顺序相同则违反集相同），
不需要把图折进 `_derived_digest`；它同时把环、被排除的先修、置顶冲突三种成因统一成一个可测量的数，直接度量
`M9-EVALUATION` 的「先修违反=0」。**`unorderable` 刻意不进 `summary`**：它是图级诊断，放进来会让两个顺序相同但
环剩余集不同的计划共用 `plan_id` 却带不同 `summary`，削弱上述不变量。

(g) **内容**：`knowledge/{os,ds,co}/` 各 20 条共 60 条新增 `prerequisites:`，一次到位；每条同时按
`knowledge/README.md` 的「更新驱动」约定 bump `updated`。诚实记录副作用：`updated` 属于 `_safe_metadata` 白名单，
因而**会**改变 `_fingerprint_chunks` 的输入面，触发一次索引 generation 变化（`EXPECTED_DEFAULT_PACK_REVISION` 未设
环境变量故无门禁）。检索结果**不受影响**：`markdown_pack.py` 在切块前用 `_FRONTMATTER_RE.sub("", text)` 剥掉整个
frontmatter 块，`document_id` = `sha256(source_id + logical_uri)` 也不含 frontmatter。实测 90 题离线 BM25
Recall@5 = 0.989、Recall@3 = 0.978，与改动前基线逐位相同。`network/`（candidate 语料，不在默认包）与
`interview/` 不在本次范围，无图。

(h) **显式残留（不夸大）**：① 不给 `GoalPlanTask` 加先修字段——关系只经最终顺序可观察，加字段还须同步改
`_response_to_record` 的逐字段列举（已知静默丢字段陷阱）与 `_derived_digest`；② 不实现跨目录/跨课程先修；
③ `unorderable` 是图级诊断，不进计划 `summary`；④ 「先修违反=0」只对**计划任务集内的边**成立，被显式排除的
先修不计违反；⑤ 期考复盘类条目不声明先修（它们是复习产物，不是有先修关系的知识主题），因此图**不会**把复盘条目
推到末尾——注入图后它们因无入度而可能比接入前更早出现，这是本增量未解决的一处排序退化；⑥ 步骤 4（检索路径
隔离）与评测 workload 仍需 owner 另行扩范围授权，本增量不触碰。

(i) **命名空间提示**：此处的 `prerequisites`（知识条目 frontmatter）与
`docs/standards/stage-admission-gates.json` 中 per-stage 的 `prerequisites` 同词不同义，文档中显式记一笔避免日后
grep 混用。本次**未新增任何公开路由**，`PUBLIC_API_PATHS` 与路由 docstring 均未改动；**未 bump
`SCHEMA_VERSION`**（记录 schema 未变）。`tests/M9` 自本次起 125 → 187 项。

受限检索接缝（grounding）实现约定：模块在 `platform/app/plan_grounding.py`
（`PlanGroundingService`），与三个只读投影同形——纯读、不写 Source 生命周期、不写会话状态、
不写计划状态、不构建 chunk 索引。**不新建检索实现**：复用 `MultiRecallService.recall`，只在外面
加四类预算与一道独立的交叉校验。

(a) **问题定性（本增量最重要的一条）**：M7 **已经**在检索路径端到端强制了 stale/deleted 拒绝——
可用性谓词在 `source_offline.py` 内联、generation 绑定贯穿 index 校验 / search / hydrate / hit 过滤、
隐藏态由 `list_sources` 的 WHERE 构造性排除、principal 作用域结果绕过外层结果缓存、末道
`ensure_user_provenance` fail-closed。因此 `M9-EVALUATION` 的 `STALE_DELETED_SOURCE_ENTRY_ZERO`
缺的**不是实现**，而是 **Planner 根本没接上检索路径**——计划此前只由目录 / frontmatter / mastery
生成，没有 grounded 检索这一步，故该判据在端到端上无证据可测。本增量补的是这条接缝与它的证据。

(b) **预算按 UTF-8 字节计，不按 token 计**：本仓没有本地 tokenizer。M6b 对同类问题用的是
`max_prompt_bytes` / `max_answer_bytes`（`preview_agent.py`）。凭空写一个「token 数」是估算冒充计量，
故 §5 步骤 4 里的「token 预算」由 `max_evidence_bytes` 兑现，**不改**该步骤的意图，只改计量单位。

(c) **`timeout_seconds` 是事后截止检查，不是硬中断**：`recall` 是同步调用且没有取消通道，一次已经
卡住的召回无法被抢占。该预算约束的是 Planner **接受**多少证据，不是检索路径**做**多少工作；
超时即返回**空证据**并标注 `truncated=("timeout",)`，不返回部分结果。

(d) **fail-closed 交叉校验**：召回后，任何 `user://{source_id}/…` chunk 的 `source_id` 不在
`summaries(principal_id)` 的可用集合内即丢弃。可用集合在三种「不确定」下都收敛到**空集**——
未注入投影、无 principal、控制面抛异常——因此这三种情况都**丢弃全部用户源**，而不是放行。
畸形 `user://` 的 `source_id` 必然不在集合内，同样被丢弃，不会被误当作默认包。默认知识包不是
生命周期门控对象，不受该校验约束。

(e) **预算只能收紧**：`GROUNDING_BUDGET_CEILING` 即字段默认值，任何维度超过上限即抛
`GroundingBudgetError` 且**不触达检索路径**；裁剪顺序固定为 `top_k` → 来源数 → 字节，保证同一
输入 + 同一预算下可重放。

(f) **grounding 刻意不进计划身份、也不进 `summary`**：其结果依赖索引 generation，折进 `plan_id`
会让每次 reindex 都 churn 计划身份（违反 §1.1「索引重建不得无故改变计划身份」）；折进 `summary`
会让同一 `plan_id` 因 reindex 得到不同 `summary`，破坏「同一 `plan_id` ⇒ 相同 `summary`」这条
结构性不变量——`unorderable` 被排除在 `summary` 外正是同一纪律。§1.1 的原文恰好支持这一拆分：
「PlanTask 优先引用稳定 topic/source identity；引用 chunk 时必须绑定 revision/generation」。

(g) **不新增任何公开路由**：`PUBLIC_API_PATHS` 与路由 docstring 均未改动，
`test_openapi_public_paths_remain_exact` 保持绿。`tests/TEST_PLAN.md` §5.2 记录的「新增默认公开
路由无合法登记渠道」这一缺口**本次不触碰**——按 §5.2 自己给出的规避方式，把能力留在服务层接缝上。
**未 bump `SCHEMA_VERSION`**（记录 schema 未变）。

(h) **已装配、生产休眠（如实记录）**：`main.py` 构造了 `_plan_grounding` 并注入 `_source_summary`，
但**没有任何路由把 principal 传进来**——principal 按设计是内部边界（与 M7 公共 Search/QA 不接受
caller-selected `principal_id` 一致），与 `_user_source_search` 同一形态。它刻意**不**注入
`_goal_planner`：按 (f)，注入也不会改变计划内容。

(i) **`STALE_DELETED_SOURCE_ENTRY_ZERO` 的证明边界**：本增量在**服务层接缝**上证明它——
`tests/M9/test_plan_grounding.py` 用**真 registry + 真生命周期转移 + 真投影**覆盖未发布 / 同步中 /
禁用 / 待删 / 已删五种形态，而非 mock 状态字符串。它**不**经 HTTP 路由（见 (h)），因此**不是**
「公共 API 上的端到端隔离」；M7 内层路径的自身证据仍留在 `tests/M7/`，本增量不重复也不替代它。
该守卫做过变异检查：把可用性判断改成空操作会让 32 项中的 10 项失败，故不是空转。

(j) **仍未闭合**：评测 workload 冻结（§5 步骤 6）与外部 AI 仍在 `m9-plan-lifecycle-v1` 之外，
`M9-EVALUATION` 的 `ADHERENCE_QUALITATIVE_FIRST` 与延迟 / 成本维度仍暂缓；本增量不使 M9 达到退出条件。

> **v1.4 更新**（不修改上述历史记录）：外部 AI 已由 §4.2 的窄口径纳入 `included`；
> **评测 workload 冻结与延迟 / 成本暂缓两条仍然成立**。
> **v1.5 更新**（不修改上述历史记录）：延迟 / 成本暂缓已由 §4.3 解冻，故「延迟 / 成本暂缓」**不再成立**；
> 「评测 workload 冻结」**仅在该范围内**成立，**不是**全项目评测口径冻结。本条取代 §4.3 之前的表述。
`tests/M9` 自本次起 187 → 219 项；步骤 4b 再追加 26 项，共 245 项。

计划身份修复：`_plan_id` 原先只哈希 `goal|target|course|required|excluded`，而任务顺序与 `summary`
的 reviewed 计数依赖复习状态、分日依赖 `hours_per_day`。两处碰撞均已实测证实：同一 `plan_id`
（`e0a2a24d83470a9e`）下任务顺序与 `summary.reviewed` 由 0 变 10；同一 `plan_id`（`3c3bc9f6a24005bd`）
下 `total_days` 15 vs 2、首日任务 1 vs 11。修复后身份 = 请求字段（含 `hours_per_day`）+ **派生输入摘要**
（按最终顺序排列的 `task_id`/`reviewed`/mastery 序列，见 `_derived_digest`）。摘要只覆盖本计划范围内的
任务，故范围外条目的状态变化不会无谓 churn `plan_id`。刻意**不含生成日期**：它只影响分日日期锚点，
含它会让正在采纳中的计划每天被孤立——残留是旧计划的日期锚定在生成时刻。**未 bump `SCHEMA_VERSION`**：
记录 schema 未变（纯增量带默认值字段），只有身份派生方式变了。迁移语义：旧 `plan_id` 仍可
`GET`/`adopt`/`progress`/`replan`（主键查找，读时不重算），只是不再匹配新生成的 id；**不回填、不改写**；
`replan` 不改写身份（保留 parent revision 链与已采纳状态）。副作用须诚实记录：状态变化后同一内容可能
同时存在于旧（已采纳）与新两个 id 下——不要靠「让 replan 重算身份」来消除它，那会打断 revision 链并
孤立进度事件。同时修掉 `_response_to_record` 对任务**逐字段列举**导致的静默丢字段：新增的 mastery 字段
若不加进该列举会从 `plan["tasks"]` 消失，而 `plan["revisions"]` 用 `model_dump()` 会保留，两处表示不一致。

> **2026-09-22 修订**：上段引用的 `total_days` 15 vs 2 是**每日容量缺陷**下的读数（窗口 14 天 + 一个
> 不设上限的溢出天）。该缺陷已修（见 §4.4），同一请求现为 `19 vs 2`。原句保留以记录当时的实测值——
> 「两个 `plan_id` 相撞」这一**结论**不受影响，且 `plan_id` 本身不随分日变化（把 `_distribute` 换成
> 只产出一个空天的桩，`plan_id` 逐字节不变）。

mastery 字段**只落 payload**，不给 `plan_tasks` 表加列（该表只写不读，且仓库无 `ALTER TABLE`/`user_version`
迁移机制，`CREATE TABLE IF NOT EXISTS` 对既有库不会补列）。本次**未新增任何公开路由**：能力经既有
`POST /api/v1/plans` 与 `replan` 可达，`PUBLIC_API_PATHS` 未改动。`tests/M9` 自本次起纳入
`.github/workflows/offline-ci.yml` 的阶段命令。同阶段测试修复：`tests/M9/test_goal_planner.py::test_planner_does_not_write_state`
此前是**空转**的（构造了 Spy 却从未注入，`spy.saves == 0` 恒真），已改为真 store + 写入口全 fail +
连接级 `total_changes` 审计 + 库快照比对的真守卫，用例名保留。**当时记录的残留已由步骤 4c 修复**：
`main.py` 原先在 import 时把 `all_reviews()` 冻结成快照，故 `reviewed` 在进程生命周期内不更新，而紧邻的
mastery 投影是实时的——两条同源只读输入一个冻结一个实时。详见下方「复习历史活投影（步骤 4c）」。

计划身份往返保真（步骤 4b）实现约定：

(a) **两处已证实缺陷**（步骤 3 记录、本增量修复）：① `_plan_id` 的身份键不含 principal，而 `event_id`
是 `(plan_id, task_id, event)` 的哈希、同样不含 principal 成分 → 两个 principal 生成同一 Goal 会撞同一
`plan_id`，后者的 `completed` 被 `INSERT OR IGNORE` 静默去重，把前者的任务标成完成；②
`_response_to_record` 没有 `summary` 键，`_plan_to_request` 只还原 5 个请求字段 → principal 一旦进入计划
路径，`replan` 会以「无 principal」重新生成，源范围静默改变。

(b) **修法（身份）**：`_plan_id` 追加一段**带标签**的 principal（`...|principal={id}`），且**仅在非 None
时追加**。两条理由：只有非 None 才追加，`principal_id=None` 的身份才与接入前**逐字节相同**，既有计划 id
不 churn（沿用「未注入时逐字节一致」的纪律）；用带标签的段而非裸值，是因为 `goal` 是自由文本、可含 `|`，
裸追加会让「goal 结尾恰好拼出 `|principal=p`」的请求与「goal 去掉该后缀 + principal=p」撞同一键——
`test_goal_text_cannot_forge_a_principal_segment` 钉住这一点。反 churn 护栏用**合成任务列表**直接调
`_plan_id` 并对比逐字复刻的旧公式，故不依赖知识库语料（语料一变就会变成误报源，而不是守卫）。

(c) **修法（往返）**：`_response_to_record` 补 `summary` 键，消除 `plan["tasks"]` 与 `plan["revisions"]`
两处表示不一致；principal 落 payload 供还原，`replan` 以 `plan.get(PRINCIPAL_RECORD_KEY)` 取回并传给
`generate`。证据是 `summary["sources"]` 键——它只在「有 principal 且注入了投影」时出现，故重规划后它
仍在，即证明 principal 被还原（去掉还原会让该用例 `KeyError: 'sources'`）。

(d) **principal 不进响应体，且这是结构保证**：`get` / `adopt` / `replan` 的每个返回点都过单点函数
`_public_plan`（按 `INTERNAL_RECORD_KEYS` 剥离），而不是各写一遍过滤——后者漏一处就静默泄露。落盘仍用
完整记录；`main.py` 不直接读计划 store，故不存在绕过路径。源码级用例
`test_service_returns_go_through_public_plan` 扫公开方法里的每一处 `return`，且扫描集合由
`_public_methods()` **动态枚举**类上所有非下划线开头的可调用属性——初版写成硬编码
`("get", "adopt", "replan")`，新增一个 `def summarize(self): return plan` 即可绕过，已改。
`test_public_method_scan_covers_the_routes` 防止扫描集合被改空而让前者空转。

(e) **未新增公开路由、未改请求体**：principal 仍是内部接缝，`GoalPlanRequest` / `GoalPlanResponse` 都
没有该字段，因此它也不进 OpenAPI schema。能力经既有 `POST /api/v1/plans` 与 `replan` 可达，
`PUBLIC_API_PATHS` 与路由 docstring 均未改动。

(f) **未 bump `SCHEMA_VERSION`**：记录 schema 未变——payload 是 JSON blob，无 DDL、无新列。

(g) **迁移语义（诚实残留）**：非 None principal 下的**旧 id 不再匹配新生成结果**；旧记录仍可
`GET` / `adopt` / `progress` / `replan`（主键查找，读时不重算），**不回填、不改写**。
`principal_id=None` 的既有计划 id 逐字节不变，不受影响。

(h) **同阶段测试的断言有意反转**：`tests/M9/test_source_summary_projection.py` 的
`test_principal_does_not_change_plan_identity_or_tasks` 原断言 `anonymous.plan_id == scoped.plan_id`，
那正是步骤 3 记录的立场，也正是本增量证伪的。该断言**有意反转**并改名为
`test_principal_does_not_change_tasks_or_days`，内容侧不变量（任务、分日、除 `sources` 外的 `summary`）
全部保留，身份断言迁至 `tests/M9/test_plan_identity.py`。这不是「把存量测试改绿」：被删掉的是一条已被
证伪的断言，替代它的断言更强（见 (b) 的 7 例参数化分隔用例）。

(i) **变异验证**：关掉剥离 → 2 项失败；去掉身份里的 principal 段 → 10 项失败；去掉 replan 的 principal
还原 → 1 项失败；去掉 `summary` 落记录 → 4 项失败。四道守卫都不是空转。

(j) **仍未闭合**：与 4a 同——评测 workload 冻结（§5 步骤 6）与外部 AI 仍在 `m9-plan-lifecycle-v1` 之外，
本增量不使 M9 达到退出条件。`tests/M9` 自本次起 219 → 245 项。

> **v1.4 更新**（不修改上述历史记录）：外部 AI 已由 §4.2 的窄口径纳入 `included`；
> **评测 workload 冻结仍然成立**。
> **v1.5 更新**（不修改上述历史记录）：评测 workload 冻结**仅在该范围内**成立（见 §4.3），
> 且延迟 / 成本维度已解冻，故本条不再表述为「全项目评测口径冻结」。

复习历史活投影（步骤 4c）实现约定：

(a) **这不是范围扩张**：步骤 3 交付时已把「`main.py` 仍在 import 时把 `all_reviews()` 冻结成快照」逐字
记为残留，本增量只是把它修掉。批准字段（`approval_scope` / `approval_reference` / `plan_revision`）与
`admission_history` 均**未改动**——能力 id `m9.review-history-projection` 是既有 `m9-plan-lifecycle-v1`
范围内的实现项，不是新边界。

(b) **缺陷定性**：Planner 本身没错，错在**装配**。`main.py` 传的是
`review_history=_learning_store.all_reviews()`——构造时求值一次的快照，于是同一进程内新记录的复习永不
反映到计划上：`reviewed` 标志、排序优先级，以及经 `_derived_digest` 参与 `plan_id` 的身份全部停在进程
启动时刻。紧邻的 mastery 投影刻意传活对象（注释原文「使计划身份与排序随答题状态刷新」），两条同源只读
输入一个实时一个冻结。

(c) **修法**：新增 `ReviewHistoryProjection`（形状对齐 `mastery_projection` / `source_summary_projection` /
`topic_graph_projection`），`main.py` 注入活对象；`GoalPlannerService._reviews()` 每轮重读投影，未注入时
回落到构造时的快照，故既有调用方行为逐字节不变。投影**只返回成员资格**（`frozenset[str]`）——Planner 只用
`file in reviewed`，从不读 review payload，把 payload 交出去会凭空给出一条调用方并不需要、也无从审计的
读取路径。

(d) **整轮只读一次**：`generate` 开头取一次 `reviews = self._reviews()` 再传给 `_build_tasks`，与 `mastery`
同形。否则生成途中若有新复习落库，不同任务会看到两个快照，排序与派生摘要就基于不一致的输入。

(e) **变异验证**：把 `main.py` 装配改回冻结快照 → **恰好 1 项**失败（`test_main_wires_a_live_review_history_projection`，
即装配护栏本身）；把 `_reviews()` 改回恒读快照 → 4 项失败。两道守卫都不是空转。

(f) **装配护栏单独存在是必要的**：本文件其余用例直接构造 `GoalPlannerService`，因此**不覆盖 `main.py` 的
装配**——把装配改回快照，它们仍然全绿。缺陷原本就长在装配上，故守卫必须钉在装配上，否则「修好了」这句话
没有证据。

(g) **迁移语义（诚实残留）**：进程内新记录的复习**现在会改变 `plan_id`**（`reviewed` 参与
`_derived_digest`）。这与既有 docstring「复习/mastery 状态变化后会得到新的 plan_id」一致，只是此前该承诺
在复习这一侧**不成立**（mastery 侧成立）。旧 `plan_id` 仍可 `GET` / `adopt` / `progress` / `replan`
（主键查找，读时不重算），**不回填、不改写**。未 bump `SCHEMA_VERSION`：记录 schema 未变。

(h) **未新增公开路由**：纯装配改动，`PUBLIC_API_PATHS` 与路由 docstring 均未改动。

(i) **仍未闭合**：与 4a / 4b 同——评测 workload 冻结（§5 步骤 6）与外部 AI 仍在 `m9-plan-lifecycle-v1`
之外，本增量不使 M9 达到退出条件。`tests/M9` 自本次起 245 → 263 项。

> **v1.4 更新**（不修改上述历史记录）：外部 AI 已由 §4.2 的窄口径纳入 `included`；
> **评测 workload 冻结仍然成立**。
> **v1.5 更新**（不修改上述历史记录）：评测 workload 冻结**仅在该范围内**成立（见 §4.3），
> 且延迟 / 成本维度已解冻，故本条不再表述为「全项目评测口径冻结」。

准入留痕字段覆盖（步骤 4d）实现约定：

(a) **这是关闭一条已记录缺口，不是范围扩张**：缺口原文逐字记在本文件 §4（「`admission_history[].reference`
尚未纳入 `_registry_references` 白名单枚举」）。本次只是把它关掉，故批准字段、`approval_scope` 与
`admission_history` 内容**均未改动**，也**未新增任何能力、路由或字段**。

(b) **修法：折进既有白名单，不另写校验器**。`stage-admission-gates.md` §7 已明文要求该字段「必须是仓库内
可移植路径」，与 `approval_reference` / `authorization_reference` 同一条规则，故只需让 `_registry_references`
多 yield 一段——复用一个校验器胜过并行维护两套。未新增测试文件，改动落在既有
`tests/regression/test_governance_contract.py`（这正是缺口原文所说的「补入枚举需改存量测试」）。

(c) **补了非空性护栏**：`admission_history` 目前**只有 M9 登记**。若哪天被清空，新增的那段 yield 就变成空转，
而 `test_registry_references_use_closed_portable_allowlist` 仍会**全绿**。故
`test_admission_history_records_are_well_formed` 先断言 `records` 非空，再逐条断言键集恰为
`from` / `to` / `at` / `reason` / `reference`（§7 的五键）、`from` / `to` 属
`{BLOCKED, ADMITTED, REVOKED}` 且不相等。键集断言是**本次新增的覆盖**，不在缺口原文范围内——原文只说
`reference`；记在此处以免日后被当成「本来就有的」。它同样只紧不松：§7 已枚举这五个字段。

(d) **变异验证**：把 `admission_history[0].reference` 换成宿主绝对路径 → `test_registry_references_use_closed_portable_allowlist`
**恰好 1 项**失败（`assert_local_markdown_target` 报 `absolute reference`）；把
`admission_history` 整个删掉 → 那条 allowlist 用例**仍然全绿**，只有
`test_admission_history_records_are_well_formed` 变红。后者正是 (c) 存在的理由，两次变异都实测过。
（注：变异用的宿主路径**不逐字写进本文件**——`tests/regression/test_path_privacy.py` 会扫描治理文档并拒绝
宿主绝对路径，初版本节照抄了报错原文，导致该用例失败。护栏是对的，改的是文档。）

(e) **仍未闭合**：与 4a / 4b / 4c 同——评测 workload 冻结（§5 步骤 6）与外部 AI 仍在
`m9-plan-lifecycle-v1` 之外，本增量不使 M9 达到退出条件。本增量**不改 `tests/M9` 计数**（263 项不变），
`tests/regression` 由 15 → 16 项。

> **v1.4 更新**（不修改上述历史记录）：外部 AI 已由 §4.2 的窄口径纳入 `included`；
> **评测 workload 冻结仍然成立**。
> **v1.5 更新**（不修改上述历史记录）：评测 workload 冻结**仅在该范围内**成立（见 §4.3），
> 且延迟 / 成本维度已解冻，故本条不再表述为「全项目评测口径冻结」。

跨阶段登记（owner 已追认）：M9 的 5 条公开路由已补登到 `tests/M6a/test_closeout_contracts.py` 的
`PUBLIC_API_PATHS`，逐项为 `/api/v1/plans`、`/api/v1/plans/{plan_id}`、`/api/v1/plans/{plan_id}/adopt`、
`/api/v1/plans/{plan_id}/progress`、`/api/v1/plans/{plan_id}/replan`。改动纯追加（8 行 = 5 条路由 + 3 行注释，
0 删除），未改动任何既有断言，`test_openapi_public_paths_remain_exact` 仍同时断言子集与「无未登记路径」。

这是 owner 于 2026-09-21 **追认**的一次性迁移例外。诚实记录两点：

1. 它**不满足** `tests/TEST_PLAN.md` §5.2 唯一例外的字面前提——§5.2 允许改存量测试的条件是「已冻结的公开契约
   与安全/隐私不变量直接冲突」，而本次是公开面**扩张**，不是隐私冲突。该追认属 owner 作为唯一权威对例外机制的
   一次性扩展，不是「规则本就允许」。
2. 之所以不选回退：M6a 的 `test_openapi_public_paths_remain_exact` 断言的是默认公开面的**精确集合**，回退会使
   `.github/workflows/offline-ci.yml` 永久变红（该测试在 CI 中运行且无 `continue-on-error`），而仓库规则中不存在
   「已知基线失败」这一记录类别可供登记；同时回退会摧毁该断言的信号——在已失败于 5 条已知路径之后，后续第 6 条
   未登记路由会淹没在噪声里。§5.2 的规则缺口已记录在 `tests/TEST_PLAN.md`。

顺带更正一处过期表述：`docs/plans/m6b-agent-core-plan.md` §0.1.1 的继承不变量「默认路由集合不变」在 M9 之后已不
再字面成立（新增 5 条默认开启路由，属**追加式**变更，未删除或改动任何既有路由）。该行是 M6b 阶段的历史记录，
不予改写；当前事实以本段为准。

另更正一处事实错误：登记提交 `f03d205` 的正文声称「This is the only edit to a prior stage's test file」，
该说法不成立——已核实 `5eae89e`（2026-09-11，M6a 冻结后 16 天）改过同一个 M6a 文件，`ee73dd2`（2026-09-06，M7）
改过 `tests/M6b/test_preview_service.py`。历史提交正文无法追溯改写，故在此更正。这也意味着 §5.2 的红线在 M9 之前
已被越过两次且均无记录，M9 的登记是这几例中唯一有记录的一次。

## 6. 撤销与后续边界

mastery 定义、Source scope、计划 schema、provider 隐私政策，或 **M9 外部 AI 评测 workload / 阈值**变化时
必须 `REVOKED`；当前冻结口径见 §4.3。M10 必须等待 M9 的真实退出证据，不能把 planner 建议误作自主写入授权。
