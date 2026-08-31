# 阶段准入门禁

> 适用阶段：M6a、M6b、M7、M8、M9、M10
> 状态权威：[`docs/PLAN.md`](../PLAN.md)
> 机器可读登记：[`stage-admission-gates.json`](stage-admission-gates.json)

## 1. 目的

M6a–M10 涉及 Source 身份、索引生命周期、外部模型、专业存储、学习计划和写副作用。
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
当前为 `ADMITTED / COMPLETE`。M7 的十二项强制决策、专属保护基线和人工批准已闭合，当前为
`ADMITTED / NOT_STARTED`；批准范围只包含 M7 基础设施，`implementation_start=NOT_AUTHORIZED`，因此尚未开始生产实施。
Network 文档晋升/语料治理闭环、M8 专业存储和 Milvus 后端选择均明确排除。M8–M10 仍为
`BLOCKED / NOT_STARTED`。M6a-P0 crawler 本身只构成前置证据，不单独批准阶段。

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
`NOT_STARTED` 进入 `IN_PROGRESS`，不改变准入结论。

Agent 不得自行批准准入或生产开工。任何强制决策、前置证据或兼容不变量发生实质变化后，准入必须改为
`REVOKED`；在重新澄清和批准前不得继续生产实施。

## 5. 阻断或未获生产开工授权期间允许与禁止的工作

`BLOCKED`、`REVOKED`，或已登记 `implementation_start=NOT_AUTHORIZED` 时仅允许：

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

上游阶段仅 `ADMITTED` 不等于已退出。下游 prerequisite 只有在上游生产实现、退出测试和所需 benchmark
形成真实证据后才能改为 `SATISFIED`；因此 M7 准入本身不能满足 `M8-M7-EXIT`。

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

JSON 登记表保存状态、Decision ID、值/证据引用、前置证据、批准记录，以及可选的批准范围和生产开工门禁；
详细理由留在对应阶段计划。任何状态变更必须在同一变更中同步阶段计划、登记表和 `docs/PLAN.md`，
并通过文档一致性回归。批准记录为空时，阶段必须保持 `BLOCKED`；存在未完成的开工授权时，交付必须保持
`NOT_STARTED`。
