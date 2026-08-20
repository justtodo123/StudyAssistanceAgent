# M6a Harness 骨架（协议先行）执行计划

> 版本：v1.0
> 制定日期：2026-08-20
> 当前状态：未开工
> 适用范围：Source/Store/Tool/Runner 四协议定义 + 额外 Markdown 源注册 + API 兼容 MVP
> 前置条件：M0–M5 全部回归通过
> 后续阶段：M6b Agent 核心（ReAct + 工具调用）

## 1. 背景

M0–M5 已完成最小学习闭环：60 篇课程条目、90 题评测、187 项测试、服务端会话状态机、工作台。
但现有系统是「硬编码编排」——QA、Quiz、Review 服务直接调用，没有统一的协议层。

M6a 的目标是**抽象出四协议**（Source/Store/Tool/Runner），为 M6b 的 Function Calling 和 ReAct 循环打基础，同时不破坏现有 API 和学习闭环。

**为什么协议先行**：
- 工具注册表（M6b）依赖 Tool 协议——没有协议就没有 `name/description/parameters/execute`
- Runner 协议让学习状态机和 ReAct 循环成为可替换的实现，而不是改代码
- Source 协议让用户数据源（M7）能接入检索，而不是只用默认 `knowledge/`

## 2. 阶段目标与非目标

### 2.1 阶段目标

1. 定义 Source/Store/Tool/Runner 四协议（Python Protocol / ABC）
2. 将现有 QA、Quiz、Review、Search 服务适配为 Tool 协议实现
3. 将现有学习状态机适配为 Runner 协议实现
4. 支持额外 Markdown 源通过配置注册（不改代码）
5. 保持所有现有 API（`/api/v1/search|qa|quiz|study-sessions|...`）不变

### 2.2 非目标

- 不实现 ReAct 循环或 Function Calling（那是 M6b）
- 不接入外部向量库（Milvus/Qdrant/LanceDB，那是 M8）
- 不实现用户数据源同步（那是 M7）
- 不实现目标驱动计划（那是 M9）
- 不改变默认 Runner——学习状态机仍是默认路径
- 不引入新依赖（纯 Python Protocol/ABC）
- `learner_id=local` 够用，不做账号体系

## 3. 四协议设计

### 3.1 Source 协议（数据源）

```python
class Source(Protocol):
    """知识数据源：提供可检索的知识块。"""
    source_id: str
    source_type: str  # "markdown_pack" | "user_directory" | ...

    def list_chunks(self) -> list[SourceChunk]: ...
    def get_chunk(self, chunk_id: str) -> SourceChunk | None: ...
```

现有适配：`knowledge/` 目录作为默认 `markdown_pack` 源。
M7 扩展：用户注册的目录作为额外源。

### 3.2 Store 协议（存储）

```python
class Store(Protocol):
    """学习状态存储：会话、答题记录、掌握度、复习历史。"""
    def save_session(self, session: StudySession) -> None: ...
    def get_session(self, session_id: str) -> StudySession | None: ...
    def list_sessions(self, learner_id: str) -> list[StudySession]: ...
    def save_review(self, entry: ReviewEntry) -> None: ...
    def get_due_reviews(self, learner_id: str) -> list[ReviewEntry]: ...
```

现有适配：`SqliteLearningStore` 已实现大部分接口，需对齐协议签名。
M8 扩展：统一 schema + LanceDB/Qdrant。

### 3.3 Tool 协议（工具）

```python
class Tool(Protocol):
    """可被 Runner 调用的工具。"""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema 格式

    def execute(self, **kwargs) -> ToolResult: ...
```

现有适配：QA 检索、Quiz 出题、Review-due 查询、Review-log 记录 → 各注册为一个 Tool。
M6b 扩展：工具注册表 + Function Calling。

### 3.4 Runner 协议（执行器）

```python
class Runner(Protocol):
    """学习执行器：决定下一步做什么。"""
    def run(self, context: RunnerContext) -> RunnerResult: ...
```

现有适配：`StudySessionService` 包装为 `StateMachineRunner`。
M6b 扩展：`ReActRunner` 作为可选实现。

## 4. 阶段拆分

### M6a-1：协议定义与接口注册

**目标**：定义四协议，创建 `platform/app/protocols.py`。

任务：

- [ ] 新建 `platform/app/protocols.py`，定义 `Source`、`Store`、`Tool`、`Runner` 四个 Protocol 类
- [ ] 为每个协议编写 docstring 和类型注解
- [ ] 定义 `SourceChunk`、`ToolResult`、`RunnerContext`、`RunnerResult` 数据类
- [ ] 在 `tests/M6a/` 增加协议实例化和接口契约测试
- [ ] 协议不导入任何业务模块，保持纯接口

退出条件：

- 四协议可被 import，有完整类型注解和 docstring
- 协议测试通过

### M6a-2：现有服务适配 Tool 协议

**目标**：把 QA、Quiz、Review-due、Review-log 适配为 Tool 实现。

任务：

- [ ] 新建 `platform/app/tools/` 包
- [ ] 实现 `RetrieveTool`：包装 `MultiRecallService.recall()`
- [ ] 实现 `QuizTool`：包装 `QuizService.generate()`
- [ ] 实现 `ReviewDueTool`：包装 `ReviewSchedulerService.get_due()`
- [ ] 实现 `ReviewLogTool`：包装 `ReviewSchedulerService.log_review()`
- [ ] 每个 Tool 有 `name`、`description`、`parameters`（JSON Schema）和 `execute()`
- [ ] 现有 `study_session.py` 通过 Tool 调用服务（内部重构，不改 API 契约）
- [ ] 在 `tests/M6a/` 增加工具注册、调用和结果格式测试

退出条件：

- 每个 Tool 可独立调用，返回 `ToolResult`
- `study-sessions` API 行为不变（回归测试通过）
- 工具测试覆盖注册、调用、异常处理

### M6a-3：Runner 协议适配

**目标**：将学习状态机包装为 `StateMachineRunner`。

任务：

- [ ] 新建 `platform/app/runners/` 包
- [ ] 实现 `StateMachineRunner`：包装现有 `StudySessionService`
- [ ] Runner 的 `run()` 接收 `RunnerContext`（learner_id, topic, course），返回 `RunnerResult`（session_id, state, tool_trace）
- [ ] 现有 API 端点通过 Runner 调用（内部重构，不改 API 契约）
- [ ] 在 `tests/M6a/` 增加 Runner 状态转换和结果测试

退出条件：

- `StateMachineRunner` 可替代直接调用 `StudySessionService`
- 所有现有 API 行为不变
- Runner 测试覆盖正常流程和异常分支

### M6a-4：Source 协议与额外源注册

**目标**：将 `knowledge/` 适配为默认 Source，支持配置额外 Markdown 源。

任务：

- [ ] 实现 `MarkdownPackSource`：包装 `knowledge_index.build_index_cached()`
- [ ] 支持通过 `SA_EXTRA_SOURCES` 环境变量注册额外 Markdown 目录
- [ ] 额外源的 chunk 进入同一检索池，与默认源一起参与 RRF 融合
- [ ] 在 `tests/M6a/` 增加额外源注册、chunk 发现和检索融合测试

退出条件：

- 默认 `knowledge/` 作为 `MarkdownPackSource` 正常工作
- 配置额外目录后，检索结果包含额外源的内容
- 不配置额外源时，行为与 M5 完全一致

### M6a-5：文档与收口

**目标**：更新文档，反映协议层状态。

任务：

- [ ] 更新 `platform/README.md`：新增协议说明和配置项
- [ ] 更新 `docs/PLAN.md`：标记 M6a 完成状态
- [ ] 更新 `docs/plans/README.md`：登记 M6a 计划状态
- [ ] 运行完整回归：M6a 测试 + M0_M2 + regression + platform/tests

退出条件：

- 所有文档与代码一致
- 回归测试全部通过

## 5. 测试策略

新增测试遵循阶段隔离，不修改 M0–M5 存量测试。

```text
tests/M6a/    协议契约、工具注册/调用、Runner 状态转换、额外源注册
```

验收顺序：

```text
tests/M6a/
  → tests/M0_M2/
  → tests/regression/
  → platform/tests/
  → 三课离线 RAG 评测
  → 文档检查
  → 人工审查与合并
```

## 6. 代码结构

```text
platform/app/
  protocols.py          # Source/Store/Tool/Runner 四协议 + 数据类
  tools/
    __init__.py
    retrieve.py         # RetrieveTool
    quiz.py             # QuizTool
    review_due.py       # ReviewDueTool
    review_log.py       # ReviewLogTool
  runners/
    __init__.py
    state_machine.py    # StateMachineRunner（包装 StudySessionService）
  sources/
    __init__.py
    markdown_pack.py    # MarkdownPackSource

tests/M6a/
  test_protocols.py     # 协议接口契约
  test_tools.py         # 工具注册与调用
  test_runners.py       # Runner 状态转换
  test_sources.py       # 额外源注册
```

## 7. 风险与决策

| 风险 | 决策 |
| --- | --- |
| 协议层增加复杂度，现有代码过度抽象 | 协议只做接口定义，不改核心算法；现有服务内部逻辑不变 |
| Tool 协议与 M6b Function Calling 的 parameters 格式不兼容 | Tool 的 `parameters` 统一用 JSON Schema，M6b 直接复用 |
| 额外源注册影响检索质量 | 默认源和额外源走同一 RRF 融合，Recall@3 回归不退化 |
| Runner 协议过度设计 | `StateMachineRunner` 只是 `StudySessionService` 的薄包装，不引入新抽象层 |
| 子阶段过多导致工期膨胀 | M6a-1 到 M6a-4 可合并为 2–3 个原子提交，不必严格按子阶段拆分 |

## 8. 分支与提交建议

```text
feature/m6a-harness-skeleton
```

建议提交：

```text
feat(platform): add Source/Store/Tool/Runner protocols
feat(platform): add tool adapters for QA/Quiz/Review
feat(platform): add StateMachineRunner
feat(platform): add extra source registration via config
test(platform): add M6a protocol and integration tests
docs(platform): document M6a harness skeleton
```

合并方式：

```powershell
git switch master
git pull --ff-only origin master
git merge --no-ff feature/m6a-harness-skeleton -m "merge: complete M6a harness skeleton"
```

## 9. 验收门禁

- [ ] `tests/M6a/` 全部通过
- [ ] `tests/M0_M2/` 全部通过
- [ ] `tests/regression/` 全部通过
- [ ] `platform/tests/` 全部通过
- [ ] 三课离线 RAG 评测 Recall@3 不退化
- [ ] 所有现有 API 行为不变（`/api/v1/search|qa|quiz|study-sessions|review-log|review-due`）
- [ ] `git diff --check` 和 Python 编译检查通过
- [ ] 文档与代码一致

## 10. 面试话术

M6a 完成后可讲：

> 我设计了四层协议架构：Source 管数据源接入，Store 管状态持久化，Tool 管可调用能力，Runner 管执行策略。
> 现有学习状态机是 Runner 的一个实现，后面做 ReAct 时只需要加一个新 Runner，不需要改底层服务。
> 这是**面向变化点的设计**——我知道下一步要加 LLM 自主决策，所以先把变化点隔离出来。

## 11. 下一步

M6a 完成后进入 M6b：基于 Tool 协议实现工具注册表 + Function Calling + ReAct 循环。
详见 `docs/plans/m6b-agent-core-plan.md`。
