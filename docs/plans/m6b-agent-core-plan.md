# M6b Agent 只读预览（工具调用决策层）执行计划

> 版本：v2.0
> 制定日期：2026-08-21
> 当前状态：设计草案已形成；`BLOCKED / NOT_STARTED`，未获准开工
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)；最终状态权威为 [`docs/PLAN.md`](../PLAN.md)
> 适用范围：provider-neutral 原生工具调用、只读工具预览、独立入口与安全预算
> 后续阶段：M6b 与 M7 均以 M6a 退出证据为共同必要前置，并各自需要专属保护基线、决策和批准；彼此不互为前置；M8/M9/M10 依赖见 PLAN；M10 实现完整自主 Runner
> 招聘价值：证明结构化 tool-use、权限边界和可观测预览链路，不宣称已有完整 ReAct Runner

## 0. 准入状态与强制设定

M6a 完成是必要前置，但不会自动批准 M6b。M6a 退出证据、保护基线和下列 M6b 专属运行设定全部闭合并由
用户/项目负责人批准前，本计划持续为 `BLOCKED / NOT_STARTED`。任何 provider、endpoint、预算或配置示例都
只是获准后的拟议内容。

### 0.1 前置证据

| Prerequisite ID | 当前状态 | 准入所需证据 |
| --- | --- | --- |
| `M6B-M6A-EXIT` | `OPEN` | M6a 契约、Source identity、快照切换、兼容和隐私退出证据 |
| `M6B-PROTECTED-BASELINE` | `OPEN` | 当前 revision 上 API/OpenAPI/SSE、旧会话恢复、`platform/tests/` 40 项与默认 90 题质量门禁真实通过；`collect-only` 不算通过 |

### 0.2 强制决策

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M6B-PROVIDER` | `OPEN` | 首个 provider/model、原生 tool-call/finish reason 能力、文本 JSON fallback 是否允许及独立计量规则 |
| `M6B-ENDPOINT-AUTH` | `OPEN` | preview 入口、base URL/endpoint、认证变量、secret/TLS/proxy 边界和 provider 不可用语义 |
| `M6B-TIMEOUT-BUDGETS` | `OPEN` | 总 deadline、模型/工具 timeout、最大 turn/call/token/cost/result bytes 的具体默认值、覆盖范围及拒绝行为 |
| `M6B-RETRY` | `OPEN` | 可重试错误、次数、backoff/jitter、取消行为，以及已完成工具调用不得重复执行的规则 |
| `M6B-CONCURRENCY` | `OPEN` | 单 preview/进程并发、parallel tool call、结果顺序、取消传播、rate limit 与过载响应 |
| `M6B-TRACE` | `OPEN` | trace 字段、参数 hash/脱敏、存储、访问、保留与删除，并继承 M6a 三层可见性 |
| `M6B-P95` | `OPEN` | workload、冷/热条件、并发、硬件、样本数、p95 指标及是否作为阻断阈值 |
| `M6B-FAILURE-SEMANTICS` | `OPEN` | 默认关闭、preview 专用结构化失败、熔断/终止；失败绝不创建或修改正式 session |

每项必须满足统一决策完成标准；`TBD`、未选 provider 列表、没有 workload 的 p95 或“实现时调参”都保持 `OPEN`。

### 0.3 全量准入检查与批准

- [ ] M6a 退出与保护基线证据全部有效；
- [ ] 八项 M6b 强制决策全部为 `RESOLVED` 并有证据、责任人和日期；
- [ ] 已确认 M6b 隔离、默认关闭、只读且不接管 `study-sessions`；
- [ ] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表状态一致；
- [ ] 用户或项目负责人完成批准记录。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | — |
| approved_at | — |
| approval_reference | — |
| plan_revision | — |
| decision_set_version | — |

批准记录为空，因此当前不得添加 provider 依赖、preview endpoint/runtime flag、外部服务或生产执行路径，也不得以
CI、README 或发布说明声称只读 preview 已交付。允许的工作仅限设定澄清、契约/评测方案、只读调查和另行批准的
可丢弃实验。获准后才可实施第 4 节子阶段和第 5 节测试。

## 1. 背景与阶段定位

M6a 固化 Source/存储职责/Tool/Runner 契约，并保持学习状态机为正式路径。M6b 在此基础上验证模型
能通过 provider-native 的结构化工具调用选择只读能力，但只提供隔离的 preview 入口。它不创建或修改
正式学习会话，不提交答案，不写掌握度或复习历史，也不通过配置替换状态机。

“原生 Function Calling”指 provider/API 返回的结构化 tool-call block；提示模型输出 JSON 文本不是同一协议。
若供应商不支持原生调用，可实现显式命名的 `TextJsonFallbackAdapter`，但必须单独计量、标记和验收，不能
把 fallback 结果描述为原生工具调用。

### 1.1 阶段目标

1. 建立 provider-neutral 的 `LLMClient`/model-turn 边界和原生 provider adapter。
2. 提供 ToolRegistry、JSON Schema 参数校验、权限检查和只读 allowlist。
3. 完成受限的 model turn → validate → authorize → execute → append result 预览往返。
4. 记录可审计的 agent trace，同时保持 domain trace 与正式学习状态隔离。
5. 在没有 LLM 时保证正式状态机离线工作；preview 本身返回明确的未配置/不可用状态，不无条件接管。

### 1.2 非目标

- 不实现完整 ReAct/开放式自主循环，不持久化或要求原始 Thought 文本；
- 不实现 `ReActRunner`，不新增 `SA_RUNNER=react`，不改正式 Runner 选择逻辑；
- 不接管 `/api/v1/study-sessions`、工作台或任何正式学习闭环；
- 不暴露 ReviewLog、掌握度、会话状态、Source 注册/删除等写工具；
- 不把 Agent 失败自动回退为状态机，也不在失败后重复执行领域副作用；
- 不实现 checkpoint/resume、exactly-once/idempotent 写入，这些属于 M10；
- 不用提示词 JSON 解析冒充 provider-native tool call；
- 不做多模型路由、语义缓存或 MCP 对外化。

## 2. 开工门禁与契约复用

M6b 只有在以下 M6a 证据全部通过后才能开工：Source/Tool/Runner contract tests、旧会话恢复、路径隐私、
现有 API/OpenAPI 兼容、SSE contract、受保护的 `platform/tests/` 40 项，以及默认 OS/DS/CO 90 题的完整
离线质量门禁。collect-only 只用于计数，不能替代这些通过证据。

M6b 必须直接复用 M6a 的 `ToolContext`、`ToolResult`、Source identity、授权和 trace 契约；provider adapter
只负责把 `call_id` 与 provider block 映射到既有工具结果，不得再定义平行的领域 result envelope。用户响应、
模型/工具可见限量结果和 audit trace 继续使用 M6a 的三层可见性；`agent_trace` 与状态机 `domain_trace` 分离，
不得记录知识正文、用户答案、密钥或宿主机绝对路径。

## 3. 核心契约

### 3.1 Provider-neutral model turn

在领域 Tool 协议和供应商 SDK 之间增加适配层，至少表达：

- `ModelTurn`：消息/工具调用 block、`finish_reason`、usage、延迟和可选 cost 元数据；
- `ToolCall`：`call_id`、规范化工具名、结构化 arguments、provider 元数据；
- `ToolExecutionResult`：provider 层对既有 M6a `ToolResult` 的 `call_id` 关联视图，不复制领域成功/错误 envelope；
- `LLMClient`：请求工具描述、接收结构化 turn、取消和超时，不把某一供应商类型泄露到领域层。

原始 Thought 不是必须字段，不进入持久化 agent trace。trace 只保留决策结果、工具名、参数摘要/哈希、call_id、
结果状态、guard 触发、usage、latency 和 fallback 标识；不得记录用户答案、知识正文、密钥或完整敏感参数。

### 3.2 ToolRegistry 与授权

ToolRegistry 负责注册、发现、描述序列化和按名称查找；工具描述采用实际 provider adapter 能消费的 schema。
每个工具携带 read-only/idempotent/side-effect 能力元数据。preview 只允许：

- `retrieve/search`：检索知识片段和出处；
- `quiz preview`：生成不写状态的题目预览；
- `review-due`：读取待复习列表。

`ReviewLogTool`、会话创建/答案提交、掌握度写入等即使未来在总注册表中存在，也必须被 preview allowlist 拒绝。
`ToolContext` 携带权限、source namespace、learner scope、correlation ID、取消信号和预算。

### 3.3 独立预览入口

新增独立 preview service/endpoint 或 CLI（实现时在 M6a API 兼容边界内定名），默认关闭；启用后返回预览答案、
来源、结构化 tool trace、终止原因和 usage 摘要。它不复用正式 `study-sessions` 写入入口，不创建 session，
不写 `learning_state.sqlite3`。未配置、不可用或执行失败时返回 preview 专用结构化结果，不创建正式 session
作为回退。

## 4. 子阶段

### M6b-1：工具注册与只读目录

任务：

- 实现 `ToolRegistry`：`register`、`get`、`list_tools`、provider schema 描述导出；
- 将 Retrieve/Quiz-preview/Review-due 注册为只读工具；
- 对写工具做显式 allowlist/deny test；
- 测试名称冲突、未知工具、schema 缺失、权限拒绝和结构化错误。

退出条件：preview 获得的工具集合可审计，任何写工具不能通过参数或名称绕过授权。

### M6b-2：原生 provider adapter

任务：

- 实现 provider-neutral `LLMClient`、`ModelTurn`、`ToolCall`、`ToolExecutionResult`；
- 请求使用 provider 原生工具描述字段，读取结构化 tool-call block；
- 校验 `call_id`、工具名、arguments JSON Schema 和结果关联；
- 对不支持原生工具调用的 provider 实现独立的 `TextJsonFallbackAdapter`（可选），并在 trace/指标中标记；
- mock provider 可离线运行，真实 provider smoke 只能是非阻塞/显式配置测试。

退出条件：原生 block、参数错误、未知工具、超时和 provider 错误均有稳定的结构化结果；文本 fallback 不被
统计为原生 tool-call 成功。

### M6b-3：受限只读预览编排

每轮只允许如下流程：

```text
model turn
  → 读取结构化 tool call
  → schema validate
  → authorize read-only tool
  → execute with ToolContext
  → append ToolExecutionResult
  → 返回下一轮或确定性终止
```

预览可以有有限的工具往返，但不把它命名为开放式 ReAct，不要求 Final Answer 必须落到复习记录。需要
模型综合结果时，只返回无副作用的预览回答；所有领域状态变化仍由正式状态机处理。

### M6b-4：安全、预算与隐私

至少实现并测试：

- 总 deadline、模型调用超时、工具执行超时和取消传播；
- 最大 model turns、tool calls、单次/总 token 与 cost budget；
- 最大 tool-result bytes/tokens，超限时结构化截断或终止；
- 规范化 `tool_name + arguments` 调用指纹的重复熔断；
- 未知工具、写工具、越权 source/learner scope 立即拒绝；
- 所有 guard 以确定性终止原因写入 agent trace；日志沿用既有敏感信息过滤规则。

这些是 preview 的边界，不等同于 M10 的完整自主 Runner 护栏；checkpoint、恢复和写副作用仍后移。

### M6b-5：离线评测与文档收口

三层验收：

1. **协议一致性**：mock provider 验证原生工具 schema、tool-call block、call_id、结果回传和错误映射；
2. **离线 scripted tasks**：验证工具选择、参数合法率、只读任务成功率、终止、重复/越权拒绝、延迟与预算；
3. **真实 provider smoke**：仅在显式配置 key 时运行，不阻塞离线 CI，不记录原始内容。

同步 `platform/README.md`、`docs/PLAN.md`、`docs/plans/README.md` 和 `docs/interview/README.md`（实施阶段再更新）。
明确写出 M6b 是只读 preview，完整自主 Runner 和 Agent 评测属于 M10。

## 5. 测试策略与验收门禁

新增测试建议放在 `tests/M6b/`，不修改 M0–M5 和 M6a 存量测试：

```text
test_tool_registry.py       注册、schema、allowlist 和写工具拒绝
test_provider_adapter.py     native block、call_id、参数/错误映射、显式 text fallback
test_preview_service.py      独立入口、只读往返、trace 和不写状态
test_safety_budget.py        deadline、超时、调用/结果/token/cost/重复预算
test_api_compatibility.py   正式 study-sessions/工作台不变
```

验收顺序：

```text
tests/M6b/
  → tests/M6a/
  → tests/M0_M2/ + tests/regression/ + platform/tests/
  → 默认 OS/DS/CO 90 题离线 RAG 评测
  → 可选真实 provider smoke → 文档/隐私检查
```

必须证明：preview 不创建/修改 study session，不提交答案，不写 review log；正式学习无 LLM 仍可运行；默认
三课 Recall@3 不退化。不得把 collection-only 结果写成测试通过。

## 6. 代码结构与配置规划

```text
platform/app/
  tool_registry.py
  llm_client.py              # provider-neutral model turn 与 adapter 边界
  preview_agent.py           # 受限只读预览编排，不是 ReActRunner
  preview_service.py         # 独立入口与结果模型

tests/M6b/
  test_tool_registry.py
  test_provider_adapter.py
  test_preview_service.py
  test_safety_budget.py
  test_api_compatibility.py
```

配置必须使用 preview 专用命名空间，例如 `SA_AGENT_PREVIEW_ENABLED`、`SA_PREVIEW_MAX_TURNS`、
`SA_PREVIEW_DEADLINE_SECONDS`、`SA_PREVIEW_TOOL_RESULT_LIMIT`；不得引入 `SA_RUNNER=react`，不得让 preview
开关替换正式状态机。无 LLM key 时，正式学习路径照常降级；preview 返回受控的不可用结果。

## 7. 风险、拟定方向与后续归属（不得替代强制决策）

| 风险 | M6b 决策 | 后续 |
| --- | --- | --- |
| JSON 文本被误称 Function Calling | 原生 block 优先，text fallback 单独命名/计量 | M10 统一 provider 评测 |
| Agent 绕过只读边界 | ToolContext + allowlist + schema/权限校验 | M10 才增加写工具 |
| 失败造成重复副作用 | preview 禁止写入，不做状态机 fallback | M10 checkpoint/幂等/恢复 |
| 循环失控或成本不可控 | preview turns/calls/deadline/token/cost/result 预算 | M10 完整 Runner 护栏 |
| trace 泄露学习内容 | 只记录摘要/哈希和安全元数据 | 持续复用 observability 过滤 |

M10 的完整范围：可选自主 Runner、正式执行路径接入、写工具授权、checkpoint/resume、幂等副作用、失败恢复、
Agent 任务评测、知识包 manifest 和 MCP 最小实现。M6b 完成不代表这些能力已实现。

## 8. 分支、提交与下一步

```text
feature/m6b-readonly-preview
```

建议提交：provider-neutral 契约、ToolRegistry/allowlist、原生 adapter、preview service、安全预算、测试、文档。
不自动 push、不改写历史。M6b 与 M7 均以 M6a 退出证据为共同必要前置，并在各自决策、专属保护基线和批准闭合后独立推进，彼此不互为前置；M8/M9 依赖 M7，M10 依赖 M7–M9。
