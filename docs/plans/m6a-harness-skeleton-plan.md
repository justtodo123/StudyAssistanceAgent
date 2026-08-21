# M6a Harness 骨架（契约先行）执行计划

> 版本：v2.0
> 制定日期：2026-08-21
> 当前状态：设计完成，未开工；前置 M6a-P0 crawler 离线测试与独立 CI 已收口
> 适用范围：Source/Store/Tool/Runner 契约、现有状态机兼容、启动期静态额外 Markdown 源
> 后续阶段：M7 用户数据源生命周期；M6b 为独立的只读 Agent 预览

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
内容 fingerprint、revision，以及未来的删除/失效语义。M6a 的 `MarkdownPackSource` 只在启动时读取默认
`knowledge/` 和显式配置的额外目录；不得把绝对路径作为对外 ID 或日志字段。

### 2.2 存储职责

不要使用原计划中混合会话和向量的 `Store`。按职责记录以下边界：

- `LearningStateRepository`：会话、答题、掌握度和恢复所需的控制状态；复用 `SqliteLearningStore`；
- `ReviewRepository`：复习历史与待复习查询，可由现有 SQLite 实现提供；
- `SourceRegistryRepository`：M7 才负责持久化用户源注册；M6a 仅保留启动配置；
- `RetrievalIndex`/`VectorStore`：检索索引和向量生命周期；复用现有 `VectorStore` 协议及实现，
  不把 LanceDB/Qdrant 写成学习状态存储。

### 2.3 Tool

Tool 使用 `ToolContext`（learner、source namespace、权限、取消/预算和 correlation ID）和结构化
`ToolResult`（数据、来源、错误码、是否可重试、trace 元数据）。参数使用 JSON Schema；工具明确标记
read-only、idempotent 或具有副作用。M6a 适配确定性服务，领域写入仍由 `StudySessionService` 和领域
服务控制；工具存在不等于允许 Agent 调用。

### 2.4 Runner

Runner 必须表达跨请求生命周期，而不是只有 `run(context)`：至少定义 `start`、`resume/get` 和
`step(event)`（或等价的状态快照、等待输入、取消、错误和副作用语义）。`StateMachineRunner` 是当前
正式路径的薄包装，保持现有会话恢复、答案提交、评估和复习记录行为。M6b 不消费它来替换正式 API；
完整自主 Runner 留给 M10。

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
- 为额外源生成不冲突的 source/document/chunk ID，并在检索融合中保留出处；
- 不持久化注册、不做同步/删除、不泄露外部绝对路径；默认无额外源时与 M5 一致。

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
- 多 source ID 不冲突、revision/fingerprint、额外源检索融合；
- 默认 API/OpenAPI 契约不变，外部绝对路径不出现在响应和日志；
- 默认评测发现集合仍为 OS/DS/CO 共 90 题，Network 扩展集不自动加入；
- crawler 依赖/测试可复现，候选产物不自动污染默认知识包。

退出条件：M6a 测试和回归通过；默认三课 Recall@3 不退化；正式学习状态机仍是唯一当前 Runner；文档
与实现边界一致。M6a 完成后可进入 M7；M6b 是其后的独立只读 preview，不是正式 Runner 替换。

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

## 6. 风险与决策

| 风险 | 决策 |
| --- | --- |
| 抽象层破坏已有状态机 | 先做契约测试，适配器保持薄，`StudySessionService` 仍为领域权威 |
| Store 边界继续混淆 | 学习状态、复习、源注册和检索索引分责，复用现有实现 |
| crawler 污染默认 pack | 候选产物须人工审核并显式注册，默认评测集合固定 90 题 |
| 额外源 ID 或路径泄露 | 稳定 namespace/逻辑 URI；绝对路径只留在受控本地配置 |
| M6b 误用写工具 | 工具记录副作用分类，preview 另有只读 allowlist |

## 7. 分支、提交与下一步

```text
feature/m6a-harness-skeleton
```

建议提交：crawler 收口、协议与 contract tests、适配器与 StateMachineRunner、静态 Source、文档与回归。
不自动 push、不修改历史。M6a 后进入 M7 Source 生命周期；M6b 只读 Agent preview 依赖 M6a 契约，完整
自主 Runner、写工具、checkpoint/幂等和 Agent 评测依赖 M7–M9 后在 M10 实现。
