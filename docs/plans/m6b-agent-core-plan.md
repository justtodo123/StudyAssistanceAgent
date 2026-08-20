# M6b Agent 核心（ReAct + 工具调用）执行计划

> 版本：v1.0
> 制定日期：2026-08-20
> 当前状态：未开工
> 适用范围：工具注册表 + Function Calling + ReAct 推理循环 + 安全护栏 + 降级路径
> 前置条件：M6a 协议先行完成，Tool/Runner 协议已定义
> 后续阶段：M7 用户数据源与千级检索
> 招聘价值：★★★★★ 直接补齐 H1（Agent 推理循环）和 H2（工具调用）两个致命面试缺口

## 1. 背景

M6a 定义了 Source/Store/Tool/Runner 四协议，并将现有服务适配为 Tool 实现、学习状态机适配为 `StateMachineRunner`。
但项目仍然是「确定性编排」——LLM 不参与工具选择，步骤由状态机硬编码。

对照 Agent 岗招聘要求，**两个致命缺口**：

| 缺口 | 现状 | 面试风险 |
| --- | --- | --- |
| H1 Agent 推理循环（ReAct） | 无 LLM 自主循环，只有确定性状态机 | ★★★★★ 致命 |
| H2 工具调用（Function Calling） | `tool_trace` 硬编码串联，无注册表 | ★★★★★ 致命 |

M6b 的目标是**在 M6a 协议层之上，实现 LLM 自主选择工具的推理循环**，同时保留状态机为默认路径和降级路径。

**为什么可以提前做（不等 M7–M9）**：
- ReAct 循环只依赖 Tool 协议（M6a），不依赖用户数据源（M7）、存储替换（M8）或计划执行（M9）
- 面试演示用默认知识包（OS/DS/CO 60 篇）足够
- 状态机仍为默认路径，ReAct 是可选 Runner，不影响现有功能

## 2. 阶段目标与非目标

### 2.1 阶段目标

1. 实现工具注册表：基于 M6a Tool 协议，用装饰器注册工具
2. 实现 Function Calling：LLM 根据工具描述自主选择调用哪个工具
3. 实现 ReAct 推理循环：Thought→Action→Observation→Final Answer
4. 实现安全护栏：最大步数、单步超时、重复观测熔断
5. 保留降级路径：无 LLM 时 100% 走原状态机

### 2.2 非目标

- 不替换现有学习状态机——ReAct 是可选 Runner，不是替换
- 不实现多 Agent 协作（CrewAI/AutoGen）——投入产出比低
- 不实现多模型路由——单 OpenAI 兼容接口 + 降级够用
- 不实现语义缓存——那是 M8 或更后
- 不引入 LangChain / LangGraph——自研轻量实现，面试可讲深度
- 不做 MCP 协议——那是 M10

## 3. 子阶段拆分

### M6b-1：工具注册表

**目标**：基于 M6a Tool 协议，实现装饰器注册和自动发现。

任务：

- [ ] 新建 `platform/app/tool_registry.py`
- [ ] 实现 `@tool` 装饰器：注册 `name`、`description`、`parameters`、`execute`
- [ ] 实现 `ToolRegistry` 类：`register()`、`get()`、`list_tools()`、`get_tool_descriptions()`
- [ ] `get_tool_descriptions()` 返回 Function Calling 格式的工具描述列表
- [ ] 将 M6a 的 `RetrieveTool`、`QuizTool`、`ReviewDueTool`、`ReviewLogTool` 用装饰器注册
- [ ] 在 `tests/M6b/` 增加注册、发现、描述格式测试

退出条件：

- 注册表可列出所有已注册工具
- 工具描述格式符合 OpenAI Function Calling 的 `tools` 参数规范
- 注册表测试通过

**面试话术**：「工具用注册表+装饰器注册，新增工具只需加一个函数和装饰器，不需要改任何调用方代码。」

### M6b-2：Function Calling

**目标**：让 LLM 根据工具描述自主选择调用哪个工具。

任务：

- [ ] 新建 `platform/app/function_calling.py`
- [ ] 实现 `FunctionCaller` 类：
  - `build_prompt(question, tools)` — 构建含工具描述的系统提示词
  - `parse_response(llm_output)` — 解析 LLM 返回的 JSON，提取 `tool_name` 和 `arguments`
  - `execute_call(tool_name, arguments)` — 从注册表获取工具并执行
- [ ] 系统提示词模板：告诉 LLM 可用工具列表、调用格式（JSON）、约束条件
- [ ] 解析 LLM 输出：支持 JSON 格式的 `{"tool": "retrieve", "arguments": {"question": "...", "course": "os"}}`
- [ ] 错误处理：工具不存在、参数校验失败、LLM 输出格式错误
- [ ] 在 `tests/M6b/` 增加提示词构建、响应解析、工具执行测试（mock LLM）

退出条件：

- 给定一个问题和工具列表，`FunctionCaller` 能构建提示词、解析响应、执行工具
- 错误情况有明确的异常处理
- 测试通过（使用 mock LLM，不依赖真实 API）

**面试话术**：「Function Calling 的核心是工具描述序列化和结构化输出解析。我用 JSON Schema 描述工具参数，让 LLM 按格式输出工具调用。」

### M6b-3：ReAct 推理循环

**目标**：实现 Thought→Action→Observation→Final Answer 循环。

任务：

- [ ] 新建 `platform/app/react_agent.py`
- [ ] 实现 `ReActAgent` 类：
  - `run(question, course)` — 主循环入口
  - `_think(question, history)` — 生成 Thought（LLM 推理当前应做什么）
  - `_act(thought)` — 根据 Thought 选择工具并执行（Action + Observation）
  - `_finalize(history)` — 生成 Final Answer（LLM 综合所有 Observation）
- [ ] 循环逻辑：
  1. 初始提示词：问题 + 可用工具列表
  2. 每轮：LLM 输出 Thought → 选择 Action（工具调用）→ 获取 Observation
  3. 将 Observation 注入下一轮上下文
  4. LLM 输出 Final Answer 或达到步数限制
- [ ] 上下文管理：历史 Thought/Action/Observation 拼接为完整上下文
- [ ] Token 预算：上下文长度控制，避免超出模型限制
- [ ] 在 `tests/M6b/` 增加循环执行、多步推理、上下文注入测试（mock LLM）

退出条件：

- 给定一个问题，`ReActAgent` 能完成至少一步 Thought→Action→Observation
- 多步推理时，前一步的 Observation 正确注入下一步上下文
- Final Answer 综合了所有 Observation
- 测试通过（使用 mock LLM）

**面试话术**：「我自研了 ReAct 循环，核心是上下文管理——每一步的 Observation 注入下一步，让 LLM 能基于已有信息决定是否继续。」

### M6b-4：安全护栏

**目标**：防止 ReAct 循环失控。

任务：

- [ ] 在 `ReActAgent` 中实现三道防御：
  1. **最大步数限制**：默认 8 步，超过强制生成 Final Answer
  2. **单步超时**：默认 30s，超时终止当前步骤
  3. **重复观测熔断**：同一 `action_name + observation_hash` 出现 ≥3 次立即停止
- [ ] 每道防御触发时记录日志（`observability.log_operation`）
- [ ] 最终必须落到讲解或复习记录，不允许空转
- [ ] 在 `tests/M6b/` 增加步数限制、超时、重复熔断测试

退出条件：

- 超过最大步数时循环终止，返回已有结果
- 单步超时时有明确的超时处理
- 重复观测时熔断生效
- 所有防御触发时有结构化日志

**面试话术**：「ReAct 循环有三道防御：最大步数防无限循环，单步超时防工具卡死，重复观测熔断防 LLM 打转。每道防御触发都有日志，可追溯。」

### M6b-5：Runner 适配与降级路径

**目标**：将 `ReActAgent` 包装为 `ReActRunner`，通过配置切换。

任务：

- [ ] 新建 `platform/app/runners/react.py`
- [ ] 实现 `ReActRunner`：实现 Runner 协议，内部调用 `ReActAgent`
- [ ] 配置切换：`SA_RUNNER=state_machine`（默认）或 `SA_RUNNER=react`
- [ ] 降级逻辑：
  - `SA_RUNNER=react` 但无 `SA_LLM_API_KEY` → 自动降级为 `StateMachineRunner`
  - ReAct 循环执行失败 → 捕获异常，降级为 `StateMachineRunner`
  - 降级时记录日志
- [ ] 更新 `main.py`：根据配置选择 Runner 实例
- [ ] 现有 API 端点通过 Runner 调用（`study-sessions` 不变）
- [ ] 在 `tests/M6b/` 增加 Runner 切换、降级、API 兼容测试

退出条件：

- `SA_RUNNER=state_machine` 时行为与 M5 完全一致
- `SA_RUNNER=react` + 有 LLM key 时走 ReAct 循环
- `SA_RUNNER=react` + 无 LLM key 时降级为状态机
- ReAct 执行失败时降级为状态机
- 所有现有 API 行为不变
- 测试通过

**面试话术**：「ReAct 是可选 Runner，通过配置切换。无 LLM 时自动降级为状态机，ReAct 失败也降级。两层正交：状态机保证教学法不被破坏，ReAct 保证 Agent 自主性。」

### M6b-6：文档与收口

**目标**：更新文档，反映 Agent 核心能力。

任务：

- [ ] 更新 `platform/README.md`：新增 ReAct 配置说明、工具注册表、降级路径
- [ ] 更新 `docs/PLAN.md`：标记 M6b 完成状态
- [ ] 更新 `docs/interview/README.md`：新增 ReAct 循环、工具注册表、降级设计的面试话术
- [ ] 运行完整回归：M6b 测试 + M6a + M0_M2 + regression + platform/tests

退出条件：

- 所有文档与代码一致
- 回归测试全部通过
- 面试话术已更新

## 4. 测试策略

新增测试遵循阶段隔离，不修改 M0–M5 和 M6a 存量测试。

```text
tests/M6b/    工具注册表、Function Calling、ReAct 循环、安全护栏、Runner 切换/降级
```

验收顺序：

```text
tests/M6b/
  → tests/M6a/
  → tests/M0_M2/
  → tests/regression/
  → platform/tests/
  → 三课离线 RAG 评测
  → 文档检查
  → 人工审查与合并
```

## 5. 代码结构

```text
platform/app/
  tool_registry.py      # 工具注册表 + @tool 装饰器
  function_calling.py   # FunctionCaller：提示词构建 + 响应解析 + 工具执行
  react_agent.py        # ReActAgent：Thought→Action→Observation→Final Answer 循环 + 安全护栏
  runners/
    __init__.py
    state_machine.py    # StateMachineRunner（M6a 已创建）
    react.py            # ReActRunner（包装 ReActAgent）

tests/M6b/
  test_tool_registry.py     # 注册、发现、描述格式
  test_function_calling.py  # 提示词构建、响应解析、工具执行
  test_react_agent.py       # 循环执行、多步推理、上下文注入
  test_safety.py            # 步数限制、超时、重复熔断
  test_runner_switch.py     # Runner 切换、降级、API 兼容
```

## 6. 配置项

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SA_RUNNER` | `state_machine` | Runner 类型：`state_machine` 或 `react` |
| `SA_REACT_MAX_STEPS` | `8` | ReAct 最大步数 |
| `SA_REACT_STEP_TIMEOUT` | `30` | 单步超时（秒） |
| `SA_REACT_REPEAT_LIMIT` | `3` | 同一 action+observation 重复次数熔断阈值 |

## 7. 风险与决策

| 风险 | 决策 |
| --- | --- |
| ReAct 循环消耗大量 Token | 设置最大步数（8）和上下文长度控制；面试可讲「成本可控」 |
| LLM 输出格式不稳定 | 支持 JSON 提取 + 容错解析；格式错误时重试一次或降级 |
| ReAct 替换状态机导致教学法被破坏 | ReAct 是可选 Runner，配置切换；默认仍是状态机 |
| 安全护栏过于宽松或严格 | 参数可配置；先用保守默认值，后续根据评测调整 |
| 工具注册表过度设计 | 注册表只做 name→Tool 映射，不超过 100 行代码 |
| mock LLM 测试不代表真实行为 | 真实 LLM 行为验证放在集成测试，不阻塞 M6b 验收 |

## 8. 分支与提交建议

```text
feature/m6b-agent-core
```

建议提交：

```text
feat(platform): add tool registry with decorator registration
feat(platform): add function calling with prompt builder
feat(platform): add ReAct agent with safety guards
feat(platform): add ReActRunner with fallback to state machine
test(platform): add M6b tool registry and ReAct tests
docs(platform): document M6b agent core and ReAct config
```

合并方式：

```powershell
git switch master
git pull --ff-only origin master
git merge --no-ff feature/m6b-agent-core -m "merge: complete M6b agent core (ReAct + tool calling)"
```

## 9. 验收门禁

- [ ] `tests/M6b/` 全部通过
- [ ] `tests/M6a/` 全部通过
- [ ] `tests/M0_M2/` 全部通过
- [ ] `tests/regression/` 全部通过
- [ ] `platform/tests/` 全部通过
- [ ] 三课离线 RAG 评测 Recall@3 不退化
- [ ] `SA_RUNNER=state_machine` 时所有 API 行为不变
- [ ] `SA_RUNNER=react` + 有 LLM key 时 ReAct 循环可执行
- [ ] `SA_RUNNER=react` + 无 LLM key 时降级为状态机
- [ ] 安全护栏（步数/超时/重复）测试覆盖
- [ ] `git diff --check` 和 Python 编译检查通过
- [ ] 文档与代码一致

## 10. 面试话术汇总

| 能力 | 话术 |
| --- | --- |
| ReAct 循环 | 「我自研了 ReAct 循环，带最大步数/超时/重复观测熔断三道防御。核心是上下文管理——每一步的 Observation 注入下一步，让 LLM 能基于已有信息决定是否继续。」 |
| 工具注册表 | 「工具用注册表+装饰器注册，新增工具只需加一个函数和装饰器，不需要改任何调用方代码。工具描述符合 OpenAI Function Calling 规范。」 |
| Function Calling | 「Function Calling 的核心是工具描述序列化和结构化输出解析。我用 JSON Schema 描述工具参数，让 LLM 按格式输出工具调用。」 |
| 降级设计 | 「ReAct 是可选 Runner，通过配置切换。无 LLM 时自动降级为状态机，ReAct 失败也降级。两层正交：状态机保证教学法不被破坏，ReAct 保证 Agent 自主性。」 |
| 双层架构 | 「项目有两层：底层是面向学习闭环的领域状态机，编码了教学法；上层是可选的 ReAct 推理循环，让 LLM 自主选择工具。这不是通用 Agent 框架，而是领域 Agent 的双层架构。」 |

## 11. 下一步

M6b 完成后进入 M7：用户数据源与千级检索。
届时 ReAct 循环可调用的工具将包含用户注册的额外源，而不仅是默认 `knowledge/`。
