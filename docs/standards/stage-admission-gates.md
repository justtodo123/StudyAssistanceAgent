# 阶段准入门禁

> 适用阶段：M6a、M6b、M7、M8、M9、M10、M11、M12
> 状态权威：[`docs/PLAN.md`](../PLAN.md)
> 机器可读登记：[`stage-admission-gates.json`](stage-admission-gates.json)

## 1. 目的

M6a–M12 涉及 Source 身份、索引生命周期、外部模型、专业存储、学习计划、写副作用、真实数据规模化和可选云部署。
在这些设定未澄清前直接实现，会把待决定事项固化为不兼容的代码、数据或部署依赖。
因此，本规则把“设定澄清完成、CI 一致性门禁通过并取得人工批准”设为生产实施前的准入门禁。该门禁降低误实施风险，但仓库内可修改的文档和 CI 检查本身不是外部不可篡改的安全边界；如需强化不可绕过性，应另行配置分支保护、CODEOWNERS 和必需检查。

计划文件存在、设计草案形成或前序调查完成，都不等于阶段已经获准开工。
`docs/PLAN.md` 是最终状态权威；JSON 登记表和阶段计划不能单独批准阶段。

## 2. 三类独立状态

| 维度 | 状态 | 含义 |
| --- | --- | --- |
| 决策 | `OPEN` | 强制设定尚无完整、可验证的结论 |
| 决策 | `RESOLVED` | 已记录选定值、行为、影响、证据、责任人和日期 |
| 准入 | `BLOCKED` | 禁止进入生产实现 |
| 准入 | `ADMITTED` | 全部准入条件已满足并经用户/项目负责人批准 |
| 准入 | `REVOKED` | 已批准条件失效，必须停止实施并重新审批 |
| 交付 | `NOT_STARTED` | 尚未实施生产能力 |
| 交付 | `IN_PROGRESS` | 已获准并正在实施 |
| 交付 | `COMPLETE` | 已满足阶段退出条件 |
| 开工授权 | `NOT_AUTHORIZED` | 已准入范围尚未获得独立生产开工授权 |
| 开工授权 | `AUTHORIZED` | 用户/项目负责人已明确允许已准入范围进入生产实施 |

准入、交付和开工授权彼此独立。`ADMITTED / NOT_STARTED` 是合法状态：它表示治理范围已获准，
但没有生产能力正在交付。阶段若登记 `implementation_start`，只有状态为 `AUTHORIZED` 且授权记录完整时，
才能把交付改为 `IN_PROGRESS`；`NOT_AUTHORIZED` 必须继续保持 `NOT_STARTED`。

M6a 的强制决策、前置证据与负责人批准已闭合，当前为 `ADMITTED / COMPLETE`：已获准实施，
M6a-1 协议契约与 M6a-2 默认 `knowledge-pack` 兼容适配的自动化门禁已通过，M6a-3 与 M6a-4 已完成。
M6b 的前置证据、八项决策、保护基线与独立批准也已闭合；获批的默认关闭只读 preview 已完成全部 closeout 门禁，
当前为 `ADMITTED / COMPLETE`。M7 的十二项强制决策、专属保护基线和基础设施范围准入已闭合，
`implementation_start=AUTHORIZED`；技术退出证据完成后，justtodo123 于 2026-09-06 另行明确批准
`M7 COMPLETE`，因此当前为 `ADMITTED / COMPLETE`。该完成批准沿用 `m7-infrastructure-only-v1`，不扩大原
scope：Network 文档晋升/语料治理闭环、任何 corpus 自动批准、M8 专业存储和 Milvus 后端选择仍明确排除。
M8–M12 仍为 `BLOCKED / NOT_STARTED`。M8 的八项 Decision 已于 2026-09-10 逐项批准并 `RESOLVED`，但这只关闭
评测政策、规模层、指标类别和 hard-gate 原则；后端选择、阶段 admission、开工授权以及任何 active execution protocol
仍未闭合。未来实证必须在看到结果前由全新、独立协议冻结具体 corpus、seed、query/gold、环境、候选、样本数、容差、
数值门槛和报告字段，历史 V1–V13 数值或方法不能替代该冻结。M9/M10 的 M7-exit 前置已满足但仍等待阶段专属
Decision 与上游退出；M11/M12 是新登记的拟议阶段，全部 Decision、前置和批准保持开放。M6a-P0 crawler 本身只构成
前置证据，不单独批准阶段。

## 3. 决策完成标准

强制决策只有同时记录以下信息才能标记 `RESOLVED`：

1. 稳定 Decision ID；
2. 明确选定值或政策，而不是候选项列表；
3. 默认值、允许覆盖和适用范围；
4. 输入校验、拒绝和失败行为；
5. 对 M0–M5 兼容性的影响；
6. 安全、隐私和数据保留影响（适用时）；
7. 可量化验收阈值及 workload（适用时）；
8. 可追溯证据；
9. 决策责任人和日期。

涉及删除、撤销或不可逆数据处置的决策，还必须明确：
- 逻辑不可见、物理清理、审计保留和 hard-delete receipt 的边界；
- last-good、缓存、索引、出处和并发运行在删除期间的可见性；
- 清理失败、重试、幂等重放和 receipt 未完成时的 fail-closed 行为。

`TBD`、空值、“稍后决定”、“实现时决定”或未选择的多个方案都必须保持 `OPEN`。
调查材料和 `collect-only` 结果不能替代真实的设计结论或测试通过证据。

## 4. 准入和撤销

阶段只有同时满足以下条件才可改为 `ADMITTED`：

- 所有强制决策均为 `RESOLVED`；
- 所有前序阶段和保护基线有真实通过证据；
- 已确认本文件第 6 节的继承不变量；
- 阶段计划、JSON 登记表与 `docs/PLAN.md` 一致；
- 用户或项目负责人填写批准人、批准时间、批准引用、计划修订和决策集版本。

阶段可登记 `approval_scope` 来缩小并明确批准边界。scope 必须有稳定 `scope_id`、非空 `included` 和
`excluded`；它不能替代强制决策、前置证据、五项批准字段或退出证据，也不能把被排除的数据、后端或下游阶段
隐式提升为已批准。阶段可另登记 `implementation_start` 作为生产开工门禁；它只控制交付从
`NOT_STARTED` 进入 `IN_PROGRESS`，不改变准入结论。交付改为 `COMPLETE` 时，必须在技术退出证据之外登记独立的
`completion_approval`，至少记录批准人、日期、批准引用、适用 scope 和证据；该记录不得覆盖原准入批准，也不得
扩大既有 `approval_scope`。测试或 benchmark 全绿本身不能自动生成完成批准。

本字段引入前已经关闭的历史阶段仅有 `M6a` 和 `M6b`。它们可按迁移例外保持既有 `COMPLETE` 事实，但不补造、
不追溯推定 `completion_approval`，且该例外不可转移到 `M7` 或任何后续阶段；`M7` 及以后所有 `COMPLETE` 阶段都必须
具有完整且与批准 scope 一致的独立完成批准。

Agent 不得自行批准准入或生产开工。任何强制决策、前置证据或兼容不变量发生实质变化后，准入必须改为
`REVOKED`；在重新澄清和批准前不得继续生产实施。

## 5. 阻断或未获生产开工授权期间允许与禁止的工作

`BLOCKED`、`REVOKED`，或已登记 `implementation_start=NOT_AUTHORIZED` 时仅允许（本条不限制已登记为 `AUTHORIZED` 的 M7-1 范围）：

- 设定澄清、契约和计划文档；
- 只读代码调查；
- 测试与 benchmark 方案设计；
- 记录既有前置证据；
- 经单独批准、可丢弃且不进入生产树的研究实验。

M7 的一次性准入前实验使用 `sa.source.admission-baseline.v1`：只对既有 M6a 静态 Source/检索边界运行仓库外、纯合成、
可丢弃的 current-state reference。现行 M6a combined hard max 为 2,000 chunks，因此 3k reference 必须记录为
`UNAVAILABLE_PRE_ADMISSION_CAPACITY_LIMIT`，不得通过提高限制或绕过生产 builder 伪造通过。若可执行的 1k reference 与全部
继承门禁通过，该精确容量差距可作为 M7 待解决项进入人工准入候选，不替代获准后必须同时通过 1k/3k 的
`sa.source.benchmark.v1`，也不授权 Agent 批准阶段或编写 M7 生产代码。

此时禁止：

- 创建该阶段的生产模块、适配器或正式数据迁移；
- 添加用于激活该能力的运行时开关；
- 修改数据库 schema，添加依赖、外部服务、worker 或部署配置；
- 接入正式 API、学习状态机或其他生产执行路径；
- 增加声称该能力已经交付的 CI、README、面试或发布说明；
- 开始依赖该阶段完成状态的后续阶段。

上游阶段仅 `ADMITTED` 不等于已退出。下游 prerequisite 只有在上游生产实现、退出测试、所需 benchmark
和独立完成批准形成真实证据后才能改为 `SATISFIED`。M7 准入本身不能满足 `M8-M7-EXIT`；2026-09-06 的独立
`M7 COMPLETE` 批准已使 M8/M9/M10 的 M7-exit 事实前置满足，但不会自动批准任何下游阶段。

## 6. 继承且不可削弱的不变量

- M0–M5 API/OpenAPI 和正式学习闭环保持兼容；
- `StudySessionService` 继续独占当前正式状态转换、答案评估和领域写入；
- 旧 SQLite session 可恢复，`learning_state.sqlite3` 与 review-history 兼容行为不回退；
- 默认 OS/DS/CO 90 题保持不变，Network 仍是显式扩展集；
- API、模型/工具可见结果、日志和 trace 不泄露宿主机绝对路径；
- 默认离线路径不强制依赖外部 LLM、向量模型或新服务；
- M6b 始终是隔离、默认关闭的只读 preview，不接管 `study-sessions`；
- 自主执行与写工具只有在 M10 获准并实现后才能启用，状态机仍为正式默认。

## 7. 登记和维护

JSON 登记表保存状态、Decision ID、值/证据引用、前置证据、准入批准记录，以及可选的批准范围、生产开工门禁、
独立完成批准记录和准入过渡留痕；详细理由留在对应阶段计划。任何状态变更必须在同一变更中同步阶段计划、登记表和
`docs/PLAN.md`，并通过文档一致性回归。准入批准记录为空时，阶段必须保持 `BLOCKED`；存在未完成的开工授权时，
交付必须保持 `NOT_STARTED`；交付为 `COMPLETE` 时必须存在完整 `completion_approval`。

阶段可以登记可选的 `admission_history`：一个**追加式**数组，每条记录 `from` / `to` / `at` / `reason` /
`reference`，用于留痕本节要求的准入过渡（例如强制决策实质变更导致的撤销与重新准入）。它只追加、不改写既有条目，
且**不替代** `admission_status`——当前权威状态始终由 `admission_status` 表达，登记该字段不改变交付、开工授权或
任何门禁结论。`reference` 必须是仓库内可移植路径。
