# M6a Harness 骨架（契约先行）执行计划

> 版本：v2.0
> 制定日期：2026-08-21
> 当前状态：设计草案已形成；`BLOCKED / NOT_STARTED`，未获准开工
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)；最终状态权威为 [`docs/PLAN.md`](../PLAN.md)
> 适用范围：Source/Store/Tool/Runner 契约、现有状态机兼容、启动期静态额外 Markdown 源
> 后续阶段：M7 用户数据源生命周期；M6b 为独立的只读 Agent 预览

## 0. 准入状态与强制设定

M6a-P0 crawler 已完成只构成前置证据，不批准 M6a 生产实现。在本节全部决策闭合、保护基线有真实
通过证据并由用户/项目负责人批准前，本计划持续为 `BLOCKED / NOT_STARTED`。计划中的代码结构、配置名和
实施顺序均为获准后的拟议内容，不是当前能力。

### 0.1 前置证据

| Prerequisite ID | 当前状态 | 准入所需证据 |
| --- | --- | --- |
| `M6A-P0` | `SATISFIED` | `tests/M6_crawler/` 与 `.github/workflows/offline-ci.yml` |
| `M6A-PROTECTED-BASELINE` | `OPEN` | 当前 revision 上 API/OpenAPI/SSE、旧会话恢复、`platform/tests/` 40 项和默认 90 题质量门禁的真实通过记录；`collect-only` 不算通过 |

### 0.2 强制决策

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M6A-SOURCE-POLICY` | `OPEN` | 缺失/非法 `source_type` 与 `ingest_status`、candidate 内容和部分源加载失败的拒绝、启动失败或 last-good 语义；可信默认 pack 的兼容例外不得扩散到用户源 |
| `M6A-IDENTITY` | `OPEN` | `source_id + logical_uri → document_id`、确定性 chunk key、schema version、URI 规范化、冲突和迁移；绝对路径不得进入稳定 ID 或对外结果 |
| `M6A-EXTRA-SOURCES` | `OPEN` | 启动期额外源配置的精确 schema、允许目录、优先级、校验、错误语义及 Search/QA-only 传播边界 |
| `M6A-CACHE-KEYS` | `OPEN` | source/revision/generation、fingerprint、解析/切块版本、检索配置、embedding 与生成参数进入各层 cache key 的规则和失效矩阵 |
| `M6A-SNAPSHOT-SWITCH` | `OPEN` | staging、校验、原子 generation 切换、重建期间读取、中断恢复、stale 清理、上一 generation 保留及回滚触发 |
| `M6A-SOURCE-LIMITS` | `OPEN` | 源数、文件数、单文件/总字节、chunk 数、启动/重建时间支持上限与超限行为 |
| `M6A-WORKER-TOPOLOGY` | `OPEN` | 单 worker 限制，或多 worker 的刷新所有权、锁、读一致性和启动竞争语义 |
| `M6A-TRACE-RETENTION` | `OPEN` | audit metadata 的存储、容量、保留期、轮转/删除、访问和脱敏；正文、答案、密钥及绝对路径不得写入 trace |

每项从 `OPEN` 改为 `RESOLVED` 时，必须按统一政策记录选定值、默认与覆盖、校验/失败行为、兼容与隐私影响、
适用阈值、证据、责任人和日期。候选列表、`TBD` 或“实现时决定”不能闭合决策。

### 0.3 全量准入检查与批准

- [ ] 八项强制决策全部为 `RESOLVED`，且阶段计划与登记表证据一致；
- [ ] M6a-P0 与保护基线证据在待实施 revision 上真实有效；
- [ ] 已逐项确认统一政策中的 M0–M5 兼容不变量；
- [ ] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表状态一致；
- [ ] 用户或项目负责人完成批准记录。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | — |
| approved_at | — |
| approval_reference | — |
| plan_revision | — |
| decision_set_version | — |

批准记录为空，因此当前不得创建生产协议/适配器、运行时开关、schema migration、依赖、worker、部署配置或正式
执行路径。允许的工作仅限设定澄清、契约/测试/benchmark 方案、只读调查和另行批准的可丢弃实验。获准后才可
实施第 3 节子阶段；第 4 节 contract tests 和 benchmark 是实施/退出门禁，不是尚未实现却要求在开工前通过的证据。

## 1. 背景与边界

M0–M5 已形成可离线运行的学习闭环：OS/DS/CO 三课 60 篇课程条目、默认 90 题评测、FastAPI
学习会话状态机、SQLite 持久化和工作台。现有代码仍以具体服务之间的直接调用为主，M6a 先收敛
契约，再做薄适配，不能用抽象破坏已经冻结的 API 和状态机。

`tools/crawler/` 与 `tests/M6_crawler/` 已存在，但 crawler 还不是完整 Source 生命周期。它在 M6a
开工前单独收口：只生成候选 Markdown，经过人工审核和显式目录配置后才可进入知识源；不得自动改变
默认 `knowledge/` 或默认三课 90 题评测。持久化源注册、增量同步、删除传播、多源隔离和千级索引留给 M7。

### 1.1 阶段目标

1. 定义与现有实现一致的职责契约，不先创建泛化的“一统 Store”或一次性 Runner。
2. 将现有学习状态机、确定性检索/测验/复习服务包装为可测试的适配边界。
3. 支持启动期配置的额外 Markdown 源，同时保持默认源和 API 行为不变。
4. 固化 crawler 的依赖、测试、CI 和人工审核边界。

### 1.2 非目标

- 不实现 ReAct、Function Calling、Agent preview 或自主 Runner；
- 不新增 `SA_RUNNER=react`，不改变 `/api/v1/study-sessions` 的执行路径；
- 不把 `SqliteLearningStore` 改写成向量、文档或源注册的总 Store；
- 不做用户源持久化注册、增量同步、删除、UI 或 1k–3k chunk 优化；
- 不把 crawler 输出自动写入默认知识包或扩大默认评测集合；
- 不引入新的外部存储依赖。

## 2. M6a-0：契约收敛与开工门禁

先写契约说明和 contract tests，再实现适配器。四类边界如下：

### 2.1 Source

Source 至少描述 `source_id`、`source_type`、source/document/chunk 的稳定命名空间、logical URI、
内容 fingerprint、revision，以及未来的删除/失效语义。身份规则固定如下：

- `source_id` 是逻辑命名空间，不直接使用本机挂载目录或绝对路径；移动本地目录不改变对外身份；
- `logical_uri` 是 Source 内可移植的文档地址；不同 Source 中相同相对路径不得冲突；
- `document_id` 由 `source_id + logical_uri` 稳定派生；
- `fingerprint` 表示规范化文档内容，`revision` 表示 Source 快照；两者职责不可混用；
- `chunk_id` 由稳定 `document_id`、确定性 chunk key 和 chunking schema version 派生，切块规则升级可显式失效旧 ID。

M6a 的 `MarkdownPackSource` 只在启动时读取默认 `knowledge/` 和显式配置的额外目录。绝对路径只允许留在
受控本地配置，不得出现在 API 响应、模型/工具结果、日志或 trace 中。

### 2.2 存储职责

不要使用原计划中混合会话和向量的 `Store`。按职责记录以下边界：

- `LearningStateRepository`：复用现有 `StudySessionRepository` / `SqliteLearningStore`，负责会话、答题、
  掌握度和恢复所需的控制状态，不复制已有持久化；
- `ReviewRepository`：复用现有 `ReviewHistoryRepository`、`ReviewHistoryRepositoryAdapter` 与 SQLite 实现，
  负责复习历史和待复习查询；
- `SourceRegistryRepository`：M7 才负责持久化用户源注册；M6a 仅保留启动配置；
- `RetrievalIndex`/`VectorStore`：检索索引和向量生命周期；复用现有 `VectorStore` 协议及实现，
  不把 LanceDB/Qdrant 写成学习状态存储。

新增协议只能按这些职责适配现有实现，不得复制数据库表、形成平行仓储或重新引入承载所有领域数据的泛化 Store。

### 2.3 Tool

Tool 使用 `ToolContext`（learner、source namespace、权限、取消/预算和 correlation ID）和结构化
`ToolResult`（数据、来源、错误码、是否可重试、trace 元数据）。参数使用 JSON Schema；工具明确标记
read-only、idempotent 或具有副作用。M6a 适配确定性服务，领域写入仍由 `StudySessionService` 和领域
服务控制；工具存在不等于允许 Agent 调用。

### 2.4 Runner

Runner 必须表达跨请求生命周期，而不是只有 `run(context)`：至少定义 `start`、`resume/get` 和
`step(event)`（或等价的状态快照、等待输入、取消、错误和副作用语义）。`StateMachineRunner` 是当前
正式路径的薄包装；`StudySessionService` 仍是状态转换、答案评估、持久化和 review-log 的唯一领域权威，
适配器不得建立第二套状态机。M6b 不消费它来替换正式 API，也不得在 preview 失败时把它作为无条件回退；
完整自主 Runner 留给 M10。

### 2.5 缓存、索引与可见性

索引/缓存键和失效输入必须显式覆盖 Source identity、revision/fingerprint、解析与切块 schema version、
检索配置，以及 embedding 模型/维度。额外 Source 加载失败时保持默认 pack 的上一完整快照；禁止把部分加载
结果与默认索引混合提交。完整快照替换后必须移除 stale BM25、vector 和 result-cache 数据。

同一工具执行结果分三层表达：

1. **用户响应**：保留兼容字段和安全、可解释的出处；
2. **模型/工具可见结果**：限量内容、logical identity 与授权范围内 metadata，不含宿主机绝对路径；
3. **audit trace**：只记录 correlation ID、稳定逻辑 ID、状态、耗时、错误码和副作用分类等安全元数据。

现有状态机的 `domain_trace` 与未来 preview 的 `agent_trace` 分离，不把知识正文、用户答案或密钥复制到 trace。

## 3. 子阶段

### M6a-P0：crawler 前置收口

任务：

- 登记 `tools/crawler/`、`tests/M6_crawler/` 及 `tools/crawler/requirements.txt`；
- 明确 fetch/clean/convert/dedup/pipeline 的输入输出、依赖安装和离线/在线边界；
- 已落地独立 marker `m6_crawler`、CI job `crawler-offline` 和 mock HTTP 夹具；在线 smoke 仅显式启用；
- 明确候选 Markdown 必须经人工审核、显式目录配置后才入源；默认 pack 和默认评测不受影响。

退出条件：✅ crawler 阶段测试可独立运行（`m6_crawler and not online`），依赖和 CI job `crawler-offline` 已文档化，且不被宣称为 M7 Source 生命周期。

### M6a-1：协议与契约测试

- 创建 `platform/app/protocols.py`，定义 Source、职责拆分后的存储边界、Tool、Runner 数据类/协议；
- 定义 `SourceChunk`、`ToolContext`、`ToolResult`、`RunnerContext`、`RunnerResult`；
- 协议层不导入业务实现；
- 覆盖结构化错误、权限/副作用标记、source/chunk ID 稳定性和跨请求状态契约。

### M6a-2：现有服务适配

- 创建 `platform/app/tools/`，提供 Retrieve、Quiz、ReviewDue 等确定性适配器；
- ReviewLog 若保留为领域服务适配，必须标为写工具，不能进入 M6b preview allowlist；
- `StudySessionService` 保持直接、类型安全的领域调用，不强制通过通用 Tool envelope；
- 创建 `platform/app/runners/state_machine.py`，包装现有状态机而不改变 API schema。

### M6a-3：启动期静态额外源

- 创建 `MarkdownPackSource`，包装现有索引能力；
- 通过 `SA_EXTRA_SOURCES` 注册额外 Markdown 目录；
- 为额外源生成不冲突的 source/document/chunk ID，并在 Search/QA 结果中以兼容方式附加 source metadata；
  现有公开 `file` 字段继续保留；
- M6a 的额外 Source 只传播到 Search/QA 及 QA 提供的安全出处，不自动改变 Quiz、Review Plan、默认评测或
  crawler 注册；
- 不持久化注册、不做运行时同步/删除、不泄露外部绝对路径；默认无额外源时与 M5 一致；
- 静态 Source 重建采用完整快照替换并清理 stale BM25、vector 和 result-cache 数据。M6a 只承诺这种
  重建清理；运行时 delete API、tombstone、增量删除传播和生命周期历史属于 M7。

### M6a-4：文档与收口

同步 `platform/README.md`、`docs/PLAN.md`、`docs/plans/README.md` 和 `tests/TEST_PLAN.md`。完整验收顺序：

```text
tests/M6_crawler/
  → tests/M6a/
  → tests/M0_M2/ + tests/regression/ + platform/tests/
  → 默认 OS/DS/CO 90 题离线 RAG 评测
  → API/OpenAPI/链接检查 → 人工审查
```

## 4. 测试与验收门禁

新增测试放在 `tests/M6a/`，不修改 M0–M5 存量测试，至少覆盖：

- 协议 contract tests、旧会话恢复、`start/resume/step` 生命周期；
- ToolContext、JSON Schema 参数、结构化错误和写工具拒绝；
- 多 source ID 不冲突、revision/fingerprint、额外源 Search/QA 检索融合；
- 缓存与索引失效覆盖 Source/revision/fingerprint、解析/切块版本、检索配置、embedding 模型与维度；
  加载额外源失败不得污染默认 pack，完整快照替换必须清理 stale 索引与结果缓存；
- 验证额外源不自动进入 Quiz、Review Plan、默认评测或 crawler 注册；
- 默认 API/OpenAPI 契约不变，现有 `file` 字段兼容，外部绝对路径不出现在响应、模型/工具结果、日志或 trace；
- 默认评测发现集合仍为 OS/DS/CO 共 90 题，Network 扩展集不自动加入；
- crawler 依赖/测试可复现，候选产物不自动污染默认知识包。

退出条件：M6a 测试和回归通过；默认三课 Recall@3 不退化；正式学习状态机仍是唯一当前 Runner；文档
与实现边界一致。M6a 退出证据只是 M6b 与 M7 的共同必要前置；两阶段仍须分别完成各自决策、专属保护基线和负责人批准，彼此不构成前置。M6b 是独立只读 preview，不是正式 Runner 替换。

## 5. 代码结构与配置规划

```text
platform/app/
  protocols.py
  tools/                 # 确定性工具适配器；写工具单独标记
  runners/state_machine.py
  sources/markdown_pack.py

tests/M6_crawler/       # crawler 前置收口（既有目录）
tests/M6a/               # 契约、适配器、Runner、Source
```

计划配置：`SA_EXTRA_SOURCES` 只表示启动期静态目录列表。crawler marker、独立依赖和 CI 安装是 M6a-P0
实施项；在实际配置落地前不得宣称已完成。

## 6. 风险与拟定方向（不得替代强制决策）

| 风险 | 决策 |
| --- | --- |
| 抽象层破坏已有状态机 | 先做契约测试，适配器保持薄，`StudySessionService` 仍为领域权威 |
| Store 边界继续混淆 | 学习状态、复习、源注册和检索索引分责，复用现有实现 |
| crawler 污染默认 pack | 候选产物须人工审核并显式注册，默认评测集合固定 90 题 |
| 额外源 ID 或路径泄露 | 稳定 namespace/逻辑 URI；绝对路径只留在受控本地配置；用户/模型/audit 三层可见性 |
| 快照替换残留 stale 数据 | 失效键覆盖 Source/解析/检索/embedding 输入；原子替换并清理 BM25/vector/result cache |
| 静态额外源意外扩散 | M6a 仅接 Search/QA，不自动改变 Quiz、Review Plan、默认评测或 crawler 注册 |
| M6b 误用写工具 | 工具记录副作用分类，preview 另有只读 allowlist |

## 7. 分支、提交与下一步

```text
feature/m6a-harness-skeleton
```

建议提交：crawler 收口、协议与 contract tests、适配器与 StateMachineRunner、静态 Source、文档与回归。
不自动 push、不修改历史。M6b 与 M7 均以 M6a 退出证据为共同必要前置，并在各自准入、专属保护基线和批准闭合后独立推进，彼此不互为前置；完整自主 Runner、写工具、checkpoint/幂等和 Agent 评测依赖 M7–M9 后在 M10 实现。
