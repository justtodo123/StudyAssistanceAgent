# M6b Agent 只读预览（工具调用决策层）执行计划

> 版本：v2.1
> 决策集：`m6b-decision-set-v1`
> 制定日期：2026-08-21
> 决策冻结日期：2026-08-27
> 当前状态：默认关闭的只读 Agent Preview 已完成全部 closeout 门禁与证据同步；`ADMITTED / COMPLETE`
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)；最终状态权威为
> [`docs/PLAN.md`](../PLAN.md)
> 适用范围：provider-neutral 原生工具调用、只读工具预览、独立入口与安全预算
> 后续阶段：M6b 与 M7 均以 M6a 退出证据为共同必要前置，并各自需要专属保护基线、决策和批准；
> 彼此不互为前置；M10 才实现完整自主 Runner
> 批准边界：justtodo123 于 2026-08-27 仅批准 M6b 默认关闭的只读 Agent Preview；不包含 M7

## 0. 准入状态与强制设定

M6a 完成是必要前置，但不会自动批准 M6b。`M6B-M6A-EXIT`、八项 M6b 专属决策和
`M6B-PROTECTED-BASELINE` 已依次闭合；justtodo123 随后按受保护候选身份独立批准 M6b。当前为
`ADMITTED / COMPLETE`：获批范围、阶段隔离、隐私/零写入、离线 benchmark、文档、治理与完整回归门禁均已通过。

### 0.1 前置证据

| Prerequisite ID | 当前状态 | 证据与边界 |
| --- | --- | --- |
| `M6B-M6A-EXIT` | `SATISFIED` | M6a 契约、Source identity、快照切换、兼容、隐私和 M6a-4 收口证据；映射见 §0.1.1。只满足共同前置，不批准 M6b |
| `M6B-PROTECTED-BASELINE` | `SATISFIED` | [`baselines.md`](../baselines.md) 的 2026-08-27 当前候选树复测；candidate evidence digest 为 `a8e33b5345b12c5e10da5294b49e699cf838fcb4cb17550d0879186fe3fe0d2c`。仅满足保护基线，不批准 M6b |

#### 0.1.1 M6a 退出证据映射

| M6a 已交付边界 | M6b 继承约束 | 退出证据 |
| --- | --- | --- |
| Source 与 Tool 协议 | 直接复用 `SourceIdentity`、`SourceChunk`、`ToolSpec`、`ToolContext`、`ToolResult`，不定义平行领域 envelope | [`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md)、`platform/app/protocols.py`、`tests/M6a/test_protocols.py` |
| 工具授权与校验 | 复用 `authorize`、`validate_arguments`、`error_result`、`result_with_data`；preview 仍须执行本地 schema 和权限检查 | `platform/app/tools/common.py`、`tests/M6a/test_tool_adapters.py` |
| 只读工具 | 只复用 `RetrieveTool`、工具名为 `quiz_preview` 的 `QuizTool`、`ReviewDueTool` | `platform/app/tools/`、`tests/M6a/test_tool_adapters.py` |
| Source scope | preview 检索使用 `DEFAULT_PLUS_EXTRAS`；正式 `StudySessionService` 继续固定 `DEFAULT_ONLY` | `platform/app/combined_snapshot.py`、`platform/app/preview_service.py`、`tests/M6b/test_preview_read_only.py` |
| 正式状态权威 | `StudySessionService` 继续独占正式状态转换、答案评估、持久化和 review-log | `platform/app/study_session.py`、`tests/M6a/test_closeout_contracts.py` |
| API/OpenAPI 与隐私 | 默认路由集合不变；响应、日志和 trace 不得泄露宿主绝对路径 | `tests/M6a/test_closeout_contracts.py`、`tests/regression/test_path_privacy.py` |
| 单 worker 拓扑 | 保持单 service process / 单 Uvicorn worker，不新增后台 preview worker | `platform/app/worker_topology.py`、[`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md) |
| M6a 收口 | M6a 阶段、回归、平台测试和默认 90 题质量已作为退出证据完成 | [`baselines.md`](../baselines.md#m6a-4-收口复测--2026-08-26当前-checkoutparent-b9bb31b) |

`M6B-M6A-EXIT=SATISFIED` 不满足 M6b 专属保护基线，也不产生准入批准。

### 0.2 强制决策总表

| Decision ID | 状态 | 冻结摘要 |
| --- | --- | --- |
| `M6B-PROVIDER` | `RESOLVED` | 官方 Python `anthropic` SDK + Messages API + `claude-opus-5`；原生 strict tool use；项目自有有限 manual loop |
| `M6B-ENDPOINT-AUTH` | `RESOLVED` | 启动前显式开关才注册 `POST /api/v1/agent-preview`；Bearer token；仅服务端 Anthropic key |
| `M6B-TIMEOUT-BUDGETS` | `RESOLVED` | 45 s 总 deadline、4 turns、3 calls、token/cost/result/answer 硬预算；覆盖只能收紧 |
| `M6B-RETRY` | `RESOLVED` | SDK 零自动重试；项目最多一次、仅瞬时 provider 错误；已完成工具永不重放 |
| `M6B-CONCURRENCY` | `RESOLVED` | 单进程最多 2 个 active preview；250 ms 等待；每 turn 1 个工具；过载 429 |
| `M6B-TRACE` | `RESOLVED` | 请求内存中的 allowlist 元数据 trace；响应后丢弃；正文、凭据、路径和原始异常禁止进入 |
| `M6B-P95` | `RESOLVED` | scripted fake provider + BM25 warm workload；20 warm-up + 200 samples；并发 2；p95 ≤ 1,000 ms |
| `M6B-FAILURE-SEMANTICS` | `RESOLVED` | 默认无路由；前置 HTTP 错误与 loop 内稳定 termination envelope 分离；所有路径零领域写入 |

各决策均按以下共同元数据冻结：

- 决策集：`m6b-decision-set-v1`；计划修订：`v2.1`；
- 决策记录责任人：`justtodo123`；记录日期：2026-08-27；
- 证据类型：本文选定政策、M6a 既有契约、生产实现、M6b 阶段测试与 blocking offline benchmark；
- 当前含义：决策已冻结且阶段已独立获准；只允许实施本批准记录精确覆盖的 M6b 默认关闭只读 preview；
- 变更规则：任何实质政策变化都须重新打开对应决策；若阶段已准入，则按统一政策改为 `REVOKED`。

### 0.3 全量准入检查与批准

- [x] `M6B-M6A-EXIT` 已映射并标记为 `SATISFIED`；
- [x] `M6B-PROTECTED-BASELINE` 在当前候选树真实通过并留存 digest；
- [x] 八项 M6b 强制决策为 `RESOLVED`，选定值、失败行为、兼容/隐私和验收条件见 §3；
- [x] 设计确认 M6b 隔离、默认关闭、只读且不接管 `study-sessions`；
- [x] [`docs/PLAN.md`](../PLAN.md)、本计划、baseline 与 JSON 登记表已按实测同步；
- [x] 用户或项目负责人完成**独立的 M6b 准入批准**。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | `justtodo123` |
| approved_at | `2026-08-27` |
| approval_reference | 本节（§0.3）记录的用户明确批准 |
| plan_revision | `v2.1` |
| decision_set_version | `m6b-decision-set-v1` |
| protected_parent_head | `65fa55af051ba4751464752edba9255f076496f1` |
| candidate_tree_digest | `a8e33b5345b12c5e10da5294b49e699cf838fcb4cb17550d0879186fe3fe0d2c` |
| scope | M6b 默认关闭的只读 Agent Preview；明确不包含 M7 |

批准允许在上述精确范围内实施 M6b，但不证明能力已经交付。只有阶段隔离测试、回归、隐私/零写入和阻断性离线
benchmark 全部通过并追加收口证据后，才能将交付状态改为 `COMPLETE`。在本计划批准时，M7 保持
`BLOCKED / NOT_STARTED`；其后续状态以阶段准入登记表为准。

## 1. 背景与阶段定位

M6a 固化 Source/存储职责/Tool/Runner 契约，并保持学习状态机为正式路径。M6b 在此基础上验证模型能通过
provider-native 的结构化工具调用选择只读能力，但只提供隔离、默认关闭的 preview 入口。它不创建或修改正式学习会话，
不提交答案，不写掌握度或复习历史，也不通过配置替换状态机。

“原生工具调用”只指 provider/API 返回的结构化 `tool_use` block 以及随后关联的 `tool_result`。提示模型输出 JSON 文本
不是同一协议，M6b 不提供 text-JSON fallback，也不将 provider refusal 当作 fallback 成功。

### 1.1 阶段目标

1. 建立 provider-neutral 的 `LLMClient` / `ModelTurn` / `ToolCall` / `ToolExecutionResult` 边界；
2. 提供 ToolRegistry、strict JSON Schema、本地参数校验、权限检查和只读 allowlist；
3. 完成受限的 model turn → validate → authorize → execute → append result 往返；
4. 记录仅含安全元数据的临时 `agent_trace`，与领域 `tool_trace` / `domain_trace` 分离；
5. 默认关闭且默认离线；无 provider 配置不影响正式状态机、Search、QA、SSE 或学习会话。

### 1.2 非目标

- 不实现 `ReActRunner`、开放式自主循环、`SA_RUNNER=react` 或原始 Thought 持久化；
- 不接管 `/api/v1/study-sessions`、工作台或任何正式学习闭环；
- 不暴露 ReviewLog、会话创建/答案提交、掌握度、Source 注册/删除等写工具；
- 不把 Agent 失败回退为状态机，也不在失败后执行领域副作用；
- 不实现 checkpoint/resume、durable queue、exactly-once 或幂等写入；
- 不使用 OpenAI-compatible shim、SDK Tool Runner、Managed Agents、Claude Agent SDK、MCP 或服务端代码执行；
- 不做多模型路由、用户可选 provider/base URL、语义缓存或第二 worker；
- 不用文本 JSON 冒充 provider-native tool call。

## 2. 契约与隔离架构

### 2.1 Provider-neutral model turn

领域层只依赖项目自有类型：

- `ModelTurn`：结构化文本/工具调用 block、标准化 stop reason、usage 和延迟；
- `ToolCall`：`call_id`、规范化工具名、结构化 arguments 和最小 provider 元数据；
- `ToolExecutionResult`：以 `call_id` 关联现有 M6a `ToolResult`，不复制领域成功/错误 envelope；
- `LLMClient`：接收消息和工具 schema，返回标准化 model turn，支持 deadline/cancellation。

Anthropic SDK 类型只存在于 adapter 内，不进入工具、领域服务、API 模型或持久化模型。

### 2.2 ToolRegistry 与授权

ToolRegistry 负责注册、按名称查找、schema 导出和重复名拒绝。注册与执行时都要求工具同时满足：

```text
capability = READ
side_effect = NONE
idempotent = true
name in explicit preview allowlist
```

M6b 只允许复用：

- `RetrieveTool`：preview scope 为 `DEFAULT_PLUS_EXTRAS`；
- `QuizTool`：对外工具名为 `quiz_preview`，只生成状态无关的题目预览；
- `ReviewDueTool`：只读查询待复习条目。

任何当前或未来写工具即使出现在全局目录，也不能自动进入 preview。provider strict schema 是第一层约束，本地
`validate_arguments` 与 `authorize` 仍是不可跳过的第二层约束。

### 2.3 独立预览服务

获准后的入口固定为 `POST /api/v1/agent-preview`。仅当进程启动前显式设置
`SA_AGENT_PREVIEW_ENABLED=true` 才注册路由；默认 app 和默认 OpenAPI 不包含该路径。Preview 只在单次请求内保存 transcript
和 trace，不创建 session/run/checkpoint，不写 SQLite，不调用 `StateMachineRunner`。

## 3. 已冻结的八项强制决策

### 3.1 `M6B-PROVIDER`（`RESOLVED`）

**选定政策**

- 官方 Python `anthropic` SDK，第一方 Anthropic Messages API，精确模型 ID `claude-opus-5`；
- 原生 strict `tool_use` / `tool_result`；provider 返回的结构化 block 是唯一 native tool-call 计量来源；
- 项目自有、有界 manual loop，经 provider-neutral `LLMClient` 归一化 turn、call、usage 和 stop reason；
- 每次 turn 使用 adaptive thinking、low effort、`max_tokens=1024`、`tool_choice=auto`，禁用 parallel tool use；
- 不发送旧式 `budget_tokens`，不增加 temperature/top-p 等采样参数；
- 不实现 text-JSON fallback 或 refusal fallback；文本 JSON 永不计为 native tool call。

**固定与覆盖**

- provider、endpoint、模型和 loop 形态在 M6b 不开放环境覆盖；后续改变必须重开本决策；
- SDK 版本须在实施时设置兼容下限与上限并由离线协议测试锁定；版本选择不允许改变上述协议语义。

**失败、兼容与隐私**

- provider typed exceptions 和 stop reasons 归一化为 §3.8 的稳定 termination reason；原始异常不外泄；
- Anthropic SDK 类型不进入领域层，保持正式状态机和既有 QA provider 配置不变；
- 功能所需 prompt 与受限工具结果会发送给 Anthropic，文档不得把它描述成“数据不离开本机”。

**验收**

- fake provider 覆盖 final-only、原生工具 block、call-id、usage、所有 stop reason 与错误映射；
- 网络被禁止时默认测试全通过；真实 Anthropic 仅显式、非阻断 smoke。

### 3.2 `M6B-ENDPOINT-AUTH`（`RESOLVED`）

**选定政策**

- 独立入口：`POST /api/v1/agent-preview`；只在启动前 `SA_AGENT_PREVIEW_ENABLED=true` 时注册；
- 启用时 `SA_AGENT_PREVIEW_TOKEN` 必填且 UTF-8 长度不少于 32 字符；无效配置在应用启动校验时失败；
- 请求使用 `Authorization: Bearer <token>`，服务端以常量时间比较；
- provider 凭据只接受服务端 `ANTHROPIC_API_KEY`，不接受请求体/header 中的 provider key；
- 固定 Anthropic 官方 HTTPS endpoint，不提供 preview base URL 覆盖，不允许关闭 TLS 校验。

**失败语义**

- 默认关闭：路由和 OpenAPI 中均不存在；
- 启用后 inbound auth 失败：401；通过 inbound auth 但缺 provider key：结构化 503；
- token/key/proxy 凭据不能出现在响应、trace、日志、OpenAPI example 或 provider 异常中。

**兼容与验收**

- 默认 M6a OpenAPI 路由集合保持完全不变；正式 Search/QA/SSE/session 不依赖 preview token 或 Anthropic key；
- 测试覆盖 route absence、启动配置、Bearer 解析、常量时间比较、provider key 缺失和 secret canary。

### 3.3 `M6B-TIMEOUT-BUDGETS`（`RESOLVED`）

所有数值是默认值与硬上限；环境变量只能降低，不能提高。解析失败、非有限值、负值、零值不适用或超过硬上限均
在启动配置校验时失败，不能静默回退为更宽松值。

| 预算 | 默认/硬上限 |
| --- | ---: |
| 请求总 deadline（含 semaphore、token count、model、tool、retry wait） | 45 s |
| 单次 model timeout | `min(20 s, remaining)` |
| 单次 token-count timeout | `min(3 s, remaining)` |
| 单工具 timeout | `min(2 s, remaining)` |
| 最大 model turns | 4 |
| 最大 tool calls | 3 |
| 每 turn 最大 tool calls | 1 |
| 累计 provider input tokens | 12,000 |
| 累计 provider output tokens | 4,096 |
| 每 turn output tokens | 1,024 |
| 估算费用 | USD 0.20 |
| UTF-8 prompt | 8 KiB |
| 单项模型可见工具结果 | 12 KiB |
| 累计模型可见工具结果 | 24 KiB |
| 最终 answer | 8 KiB |

**预算执行**

- 每次 provider request 前，在独立 3 s 上限内调用 token count，并用冻结的 `claude-opus-5` 价格表预留下一 turn 的
  1,024 output tokens；未知价格、无法计数或预计超限时 fail closed；
- usage 以 provider 返回值累计；不得把 retry 或最后一个 turn 从累计中排除；
- 工具结果只能按已定义结构做确定性、安全裁剪并标记原始/返回字节数；不能安全裁剪时以 result budget 终止；
- deadline/cancellation 到达后不得开始新 model、tool、retry 或后台 continuation；已经提交的非协作同步工具无法被 Python
  安全强杀，其工作槽必须保留至自然返回或抛错，晚到结果仅用于资源清理，不得写回 conversation 或触发后续工作。

**验收**

逐一测试边界值、环境收紧、启动拒绝、token/cost 预留、UTF-8 字节口径、结构裁剪、deadline 和 cancellation。

### 3.4 `M6B-RETRY`（`RESOLVED`）

**选定政策**

- Anthropic SDK `max_retries=0`；项目对每个 model request 最多执行 1 次 retry；
- 仅重试：连接失败、未获得任何可用响应前的 timeout、HTTP 408/409/429/5xx（含 529）；
- 不重试：其他 4xx、provider refusal、预算、schema、认证/授权、工具失败、取消或 deadline；
- full jitter 200–500 ms；若有 `Retry-After`，最多接受 2 s，且仍受总 deadline 约束；
- cancellation 立即中止等待和 retry。

**禁止重放**

- retry 仅重发当前尚未产生可用响应的 provider request；
- 已完成工具的 `call_id`、规范化参数 fingerprint 和结果保存在请求内存 transcript，continuation 失败不得重执行；
- 同一 `tool_name + canonical arguments` 再次出现，确定性终止为 `duplicate_tool_call`。

**验收**

fake provider 证明 retry 分类、次数、jitter 边界、`Retry-After` cap、deadline/cancel 传播以及已完成工具零重放。

### 3.5 `M6B-CONCURRENCY`（`RESOLVED`）

**选定政策**

- 继承单 service process / 单 Uvicorn worker；不新增后台 worker、进程池或 durable queue；
- 每进程最多 2 个 active preview；semaphore 等待上限 250 ms；
- 获取失败返回 HTTP 429、稳定错误码 `PREVIEW_OVERLOADED`、header `Retry-After: 1`；
- 每个 model turn 最多接受并执行 1 个工具；provider 若返回多个调用，以稳定 guard 终止，不执行其中任何一个；
- 结果严格按 turn index / call id 顺序追加，不并行执行工具；
- preview semaphore 与正式 Search/QA/session 不共用。

**取消与验收**

客户端取消或 deadline 到达后释放 request semaphore，且不再启动工具、retry 或 continuation；已开始的非协作同步工具继续占用
实际工作 permit 直到自然结束。并发测试覆盖 2 active、第三个过载、250 ms 等待、取消释放、实际工具容量恢复、正式服务不占
preview 容量和多工具 block 拒绝。

### 3.6 `M6B-TRACE`（`RESOLVED`）

**生命周期与访问**

- `agent_trace` 与领域 `tool_trace` / `domain_trace` 分离；
- 只返回给当前通过 Bearer auth 的 preview 请求方；响应结束后丢弃；
- 不落磁盘、不建 SQLite 表、不跨重启保留、不建立共享 trace 查询 endpoint；
- HMAC key 在进程启动时随机生成，只存在内存，永不持久化。

**允许字段**

- trace schema version、turn index、模型 ID；
- HMAC 后的 correlation/request/call ID；
- 工具名、canonical parameter hash；
- 结果状态、稳定错误码、原始/返回字节数；
- stop/termination reason、usage、估算费用、latency、retry 和 guard 元数据。

**禁止字段**

- 原始 prompt、thinking、arguments/query；
- 用户答案、知识正文、quiz 正文、review 内容；
- API key、inbound token、proxy credential；
- Windows/POSIX/UNC/traversal 宿主路径；
- provider 原始异常文本或响应 header/body。

应用日志只能使用同一 allowlist 的聚合元数据。隐私验收须使用路径、secret、正文和异常 canary，覆盖成功、前置失败、
loop 终止、日志、trace、response 和 OpenAPI。

### 3.7 `M6B-P95`（`RESOLVED`）

**阻断性离线 benchmark**

- scripted fake provider、BM25、已发布 warm snapshot、scope=`DEFAULT_PLUS_EXTRAS`；
- 固定混合 retrieve / quiz-preview / review-due / final workload；
- 20 次 warm-up，随后 200 个 measured samples，并发 2；
- reference environment 上 service 端到端 p95 `<= 1,000 ms`；
- unexpected termination/timeout rate = 0；预算/终止确定性重放一致率 = 100%；
- 记录 exact revision、CPU、OS、Python、snapshot generation、workload digest、样本数和各分位数。

**真实 Anthropic smoke**

- 仅手工显式 opt-in，至少 10 个固定 case；
- 只记录 sanitized p50/p95、usage、tool success、model 和 termination；
- p95 必须低于 45 s hard deadline，但该小样本不是稳定 SLA，不阻塞默认离线 CI，也不得冒充离线 benchmark。

阈值或 workload 的实质变化须重开本决策。当前阻断性离线 benchmark 已按冻结契约运行：20 warm-up、200 measured、
并发 2，p95 5.179 ms，零 unexpected termination，规范化重放一致率 100%；详见 `docs/baselines.md`。真实 Anthropic
smoke 本次未运行，不据此声称真实 provider 性能。

### 3.8 `M6B-FAILURE-SEMANTICS`（`RESOLVED`）

**路由与前置错误**

- route disabled：路由和默认 OpenAPI 中不存在；
- enabled pre-loop：401 `PREVIEW_UNAUTHORIZED`、422 请求校验错误、429 `PREVIEW_OVERLOADED`、
  503 `PREVIEW_PROVIDER_NOT_CONFIGURED`。

**进入 loop 后的统一 envelope**

```text
status = completed | terminated
termination_reason = stable machine-readable value
answer? / sources?
agent_trace = sanitized allowlist metadata
usage
model_turn_count
tool_call_count
```

`completed` 只允许模型给出可接受的最终文本并满足所有输出预算。稳定 termination reason 至少覆盖：

- `provider_unavailable`、`provider_auth_failed`、`provider_rejected`、`provider_refusal`、`provider_timeout`；
- `deadline_exceeded`、`max_turns`、`max_tool_calls`；
- `input_token_budget`、`output_token_budget`、`cost_budget`、`tool_result_budget`、`answer_budget`；
- `unknown_tool`、`unauthorized_tool`、`invalid_tool_arguments`、`tool_failed`、`duplicate_tool_call`；
- `multiple_tool_calls`、`unexpected_stop_reason`、`cancelled`。

provider 的 `max_tokens`、`refusal`、`pause_turn` 或任何未知 stop reason 不得报告为 `completed`。不得返回原始 provider
异常。任意成功或失败路径都不得创建/修改 formal session、提交答案、写 mastery/review history、注册/删除 Source，
也不得调用状态机作为 fallback。

**零写入验收**

测试须对真实隔离 SQLite 比较前后 logical dump/hash、row counts、`PRAGMA data_version`、connection `total_changes`，
并 monkeypatch session/answer/review/source 写入口为 fail-fast；成功及全部失败路径都必须证明零领域写入。

## 4. 已实现子阶段与证据映射

批准身份已在生产表面出现前同步。以下实现都位于获批的默认关闭、只读范围内，不改变 M7：

### M6b-1：准入同步、工具注册与只读目录（已实现）

- `platform/app/tool_registry.py`：显式 allowlist、重复名拒绝、strict schema、本地校验、授权双检和显式结果投影；
- 只注册 `retrieve`、`quiz_preview`、`review_due`，且要求 `READ + NONE + idempotent`；
- `tests/M6b/test_tool_registry.py` 覆盖 unknown/write/non-idempotent、schema、授权与路径/metadata 投影边界。

### M6b-2：原生 Anthropic adapter（已实现）

- `platform/app/llm_client.py`：provider-neutral 类型和官方 `AnthropicLLMClient`，固定 `claude-opus-5`、官方 endpoint、
  adaptive thinking、low effort、native blocks、token count 与 `max_retries=0`；
- adapter 内保留 Messages API continuation 所需完整 replay；SDK 类型、thinking 与 replay payload 不出 adapter；
- `platform/requirements.txt` 锁定 `anthropic>=1.2.0,<2`，closeout 环境实装 1.2.0；
- `tests/M6b/test_llm_client.py` 覆盖 request shape、thinking/tool replay、usage、异常映射、SDK 初始化失败、
  token-count/message/usage 结构异常，以及 provider 原始数据净化。

### M6b-3：受限只读预览编排（已实现）

`platform/app/preview_agent.py` 实现“预算/deadline guard → token count → model turn → native tool block → registry/schema/
authorization → bounded tool execution → sanitized result → next turn/termination”。同步工具经 service-lifetime
`ToolWorkLimiter`（容量冻结为 2，由 `PreviewService` 跨请求共享）在真实 deadline 内执行；timeout 或异常后不把结果写回
conversation、不 continuation。已开始的非协作同步函数仍占用工作槽直至自然结束。请求内保存 transcript、fingerprint、trace
与预算；完成工具不重放，重复 canonical call 终止。`tests/M6b/test_preview_agent.py` 覆盖 retry、timeout、cancel、慢工具
deadline、敏感工具异常、turn/call/token/cost/result/answer 预算、duplicate/multiple calls 与 provider stop reasons。

### M6b-4：独立服务、安全与隐私（已实现）

- `platform/app/preview_service.py` 与 `platform/app/main.py`：启动期路由开关、常量时间 Bearer、auth-before-config、容量 2、
  250 ms semaphore、429/503、sanitized 422、HMAC trace 和 `DEFAULT_PLUS_EXTRAS` context；
- `platform/app/config.py` / `platform/.env.example`：严格布尔值、预算只能收紧；provider/model/endpoint/TLS/allowlist/
  capacity/retry/pricing/retention 不可覆盖；
- `tests/M6b/test_preview_service.py`、`test_main_preview_integration.py`、`test_preview_config.py` 验证默认 route/OpenAPI
  absence、enabled API、认证、容量、清理和配置；
- `test_preview_read_only.py` 以真实隔离 SQLite 和 fail-fast 写入口验证成功/失败零领域写入，并验证 preview extras 与正式
  default-only scope；`test_preview_privacy.py` 覆盖 prompt/query/body/secret/path/provider exception/header/body canary。

### M6b-5：离线评测、CI 与文档收口（已完成）

- `tests/M6b/conftest.py` 与 retrieval fixture 显式关闭向量路，benchmark 和只读测试固定 BM25，不依赖本机 embedding 模型；
- `tests/M6b/test_preview_benchmark.py` 使用真实 PreviewService/Agent/Registry/三个只读工具、BM25 warm published snapshot
  和 scripted fake provider；20 warm-up、200 measured、并发 2；独立 marker `m6b_benchmark`，普通套件必须
  `-m "not m6b_benchmark"`；
- 记录型报告必须同时给出 `M6B_BENCHMARK_EVIDENCE_ID`，报告文件名必须包含该 ID，并以 exclusive-create 写入，禁止覆盖；
- `.github/workflows/offline-ci.yml` 阻断执行 M6b 普通套件和独立 benchmark job，artifact 名与 evidence ID 绑定；不注入 provider key/token；
- `tests/regression/test_ci_contract.py` 锁定上述离线 CI 契约；
- 首轮 closeout 结果与 digest 追加在 `docs/baselines.md`。真实 Anthropic smoke 保持显式非阻断，本次未运行。

## 5. 阶段隔离测试与实测结果

历史 `tests/M6a/` 和 `platform/tests/` 未修改。`tests/M6b/` 实际包含：

```text
test_llm_client.py              adapter、native replay、usage、错误与隐私
test_preview_agent.py           有限 loop、重试、超时、取消、预算、重复与终止
test_preview_service.py         route、Bearer、503/429、deadline、清理与 envelope
test_main_preview_integration.py 默认关闭/启用 app 与 OpenAPI
test_preview_config.py          严格布尔值与只能收紧配置
test_tool_registry.py           allowlist、schema、授权与投影
test_preview_read_only.py       scope 隔离与 SQLite 零领域写入
test_preview_privacy.py         prompt/body/secret/path/provider canary
test_preview_benchmark.py       20 warm-up、200 measured、concurrency=2、p95
```

2026-08-28 首轮 closeout 实测：M6b 111 passed；M6a 124 passed；M5c 聚焦 7 passed；M0_M2 18 passed；
非 slow regression 49 passed、3 deselected；slow RAG 3 passed；platform 40 passed；根级 527 passed、1 个显式 online
crawler smoke skipped；M3d 6 passed。当前 M6b 共收集 129 项：普通套件 126 项（实测 126 passed、3 deselected）、
专用 benchmark 3 项（实测 3 passed）。根级 `tests/` 实测 546 collected、545 passed、1 skipped；合并 `tests platform/tests` 实测 586 collected、585 passed、1 skipped。
默认 OS/DS/CO 90 题 Recall@3 分别为 0.987/0.929/1.000。完整命令、环境、benchmark 与报告 digest 见
`docs/baselines.md`。

## 6. 已落地代码结构与配置

```text
platform/app/
  llm_client.py
  tool_registry.py
  preview_agent.py
  preview_service.py
  config.py
  main.py

tests/M6b/
```

Preview 配置使用独立 `SA_AGENT_PREVIEW_*` 命名空间，provider key 仅接受 `ANTHROPIC_API_KEY`。默认开关为 false；
除启用/token 和 §3.3 可收紧预算外，不开放 provider/model/base URL/TLS/allowlist/capacity/retry/pricing/retention 覆盖。

## 7. 风险与后续归属

| 风险 | M6b 已冻结控制 | 后续 |
| --- | --- | --- |
| JSON 文本被误称 Function Calling | 只接受原生 strict block；无 text fallback | M10 扩展 provider 评测时仍须分协议计量 |
| Agent 绕过只读边界 | registry metadata + explicit allowlist + 本地 schema/授权双检 | M10 才可能增加写工具 |
| 失败造成重复副作用 | M6b 零写入、已完成工具零重放、不做状态机 fallback | M10 冻结 checkpoint/幂等/恢复后再讨论写路径 |
| 循环失控或成本不可控 | deadline、turn/call/token/cost/result/answer 硬预算 | M10 才实现完整 Runner 护栏 |
| trace 泄露学习内容 | 请求内存 allowlist trace，正文/凭据/路径/异常禁止进入 | 持续复用 observability 过滤 |
| preview 影响正式服务 | 独立 semaphore、默认无路由、单 worker 且无后台 continuation | 已在收口复验 API/OpenAPI/SSE/session |

M10 的完整范围包括可选自主 Runner、写工具授权、checkpoint/resume、幂等副作用、失败恢复、Agent 任务评测和 MCP。
M6b 完成不代表这些能力已实现。

## 8. 准入记录、实施分支与状态边界

准入准备分支为：

```text
docs/m6b-admission-prep
```

2026-08-27，justtodo123 按 `plan_revision=v2.1`、`decision_set_version=m6b-decision-set-v1`、
`protected_parent_head=65fa55af051ba4751464752edba9255f076496f1` 与
`candidate_tree_digest=a8e33b5345b12c5e10da5294b49e699cf838fcb4cb17550d0879186fe3fe0d2c`，明确批准 M6b
进入 `ADMITTED` 并实施默认关闭的只读 Agent Preview；批准明确不包含 M7。

获批实现当前保存在实施分支 `feature/m6b-readonly-preview` 的未提交工作树中；该分支仍以受保护 parent
`65fa55af051ba4751464752edba9255f076496f1` 为 `HEAD`，未 commit、push 或 merge。准入准备分支名称仅作为历史记录，
不用于声称当前 checkout。

不得自动 commit、push 或 merge。M6b 已在全部 closeout 门禁通过并完成证据同步后切换为
`ADMITTED / COMPLETE`。M7 的十二项决策、`M7-PROTECTED-BASELINE` 和批准记录不因本计划、runbook、M6b baseline、
批准或 M6b 完成而改变。
