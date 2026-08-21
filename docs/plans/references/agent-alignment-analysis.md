# Agent 招聘要求对齐分析（计划辅助调查）

> 类型：辅助计划决策的分析与事实调查，**不是**执行计划，不替代 `docs/PLAN.md`
> 日期：2026-08-20
> 源文档：`docs/interview/StudyAssistanceAgent_requirement.md`
> 对照范围：当前仓库 `platform/app/`、`docs/PLAN.md`、M5 收口结论

本文件只回答三件事：源文档主张什么、对照本项目是否成立、下一步该不该开新阶段。

## 1. 源文档观点摘要

`StudyAssistanceAgent_requirement.md` 的核心判断可以收成四条：

1. **底座已经够用。** 多路召回 RAG、学习会话、90 题评测、187 项测试和文档完整度，已经能支撑自学与面试叙事。
2. **产品形态不是 LLM 自主 Agent。** 现有闭环是确定性编排：`create → qa → quiz → evaluate → review-log`，不是 Thought-Action-Observation 循环。
3. **与 Agent 岗要求的缺口集中在三处。** ReAct 推理循环、可注册的 Function Calling、Agent 全链路评估。其余（语义缓存、多模型路由、熔断、Prometheus、限流、MCP）被标成 P1/P2。
4. **对齐方式应增量而非换栈。** 参考 `ai-agent-platform` 的是模块清单，不是把项目迁到 Java/Spring。

源文档给出的优先级：

| 优先级 | 源文档主张立刻补的能力 |
| --- | --- |
| P0 | ReAct 循环、工具注册表 + Function Calling、死循环/超时护栏、保留离线降级 |
| P1 | 语义缓存、查询改写、Agent 评测、多模型路由、熔断重试 |
| P2 | Prometheus/Grafana、限流与 Token 预算、会话摘要、MCP |

## 2. 对照本仓库的事实核对

源文档对「现状」的判断大体正确，但有几处需要按代码收紧，避免后续计划建立在夸大缺口上。

| 源文档说法 | 仓库事实 | 结论 |
| --- | --- | --- |
| 无 LLM 自主循环，只有确定性状态机 | `study_session.py` 状态为 `created → explaining → awaiting_answer → evaluating → remediation → completed`；服务只编排已有 QA/Quiz/Review，不让模型选下一步 | 成立 |
| `tool_trace` 是硬编码串联 | `StudySessionService._trace()` 按固定步骤写入 `create/qa/explain/quiz/...`；没有工具协议、没有 LLM function call | 成立 |
| BM25 + BGE + RRF，`k=60` | `retrieval.py` 中 `RRF_K = 60`；向量后端是 SQLite/linear，接口在 `vector_store.py` | 成立；缺的是 Milvus，不是混合检索 |
| 仅 LRU 结果缓存 128 条 | `MultiRecallService._result_cache` 容量 128，按 `(question, top_k, threshold, course)` 精确命中 | 成立；已有余弦计算，但只用于向量检索 |
| 单 OpenAI 兼容接口 + 摘要降级 | `qa.py`：有 `SA_LLM_API_KEY` 则调 `/chat/completions`，失败或未配置则拼笔记摘要 | 成立 |
| 进程内指标 + `/health` | `observability.py` 记录延迟、cache hit、index size；无 Prometheus 导出 | 成立 |
| 90 题 Recall@3，缺 Agent 级评估 | `tools/run_evaluation.py` 评检索质量，不评工具选择、任务成功、token 成本 | 成立 |
| SQLite + 遗忘曲线，缺会话摘要 | `learning_store.py` 持久化会话/答题/复习；`review_scheduler.py` 做间隔重复，不是工作记忆压缩 | 成立 |
| 测试/CI 只缺 Docker Compose | 根级 `tests/` + `platform/tests/` + 离线 GitHub Actions；个人学习场景不依赖 Compose | 缺口被夸大 |
| 无认证/无限流是中等缺口 | 单用户本地工作台，`docs/PLAN.md` 明确非目标含用户系统与权限 | 对招聘 JD 成立，对本项目目标不成立 |

与计划文档的硬约束：

- `docs/PLAN.md` / 根 `README.md`：M5 已收口，下一步是工作台使用与面试彩排，**不再扩平台功能**。
- M5 非目标：**不自研通用 Agent 框架**，继续复用 QA、Quiz、Review。
- 现有学习闭环已经可演示：`POST /api/v1/study-sessions` + 工作台 + `tool_trace`。

## 3. 对源文档的评价

### 3.1 同意

- 「RAG + 确定性编排」和「LLM 自主 Agent」不是同一类系统。面试若按 ReAct/Function Calling 追问，现有实现会被问穿。
- 参考 Java 项目只取其模块清单，是正确约束；换栈会毁掉现有 187 项测试和离线交付。
- 若未来要补 Agent 属性，必须保留无 LLM 降级。这与当前 `qa.py`、离线 CI、BM25 评测一致。
- 工具注册表比再堆检索功能更接近招聘话术，也比接入 Milvus 更值。

### 3.2 不同意或需要降权

1. **不要把 P0 当成现在必须开工的 M6。** 源文档把 ReAct 写成「最关键、直接补齐 Agent 属性」，但这与 M5 收口和双目标冲突。本项目首先是学习工具，Agent 叙事建立在真实学习闭环上，不是建立在通用运行时上。
2. **不要用 ReAct 替换学习会话状态机。** 学习闭环是已知流程：先讲解、再出题、答错补讲、最后记复习。LLM 自主选工具可能跳过 `review-log`、连续出题或在检索里打转。状态机编码的是教学法，不是「还没来得及做成 Agent」的半成品。
3. **不要按参考项目把 Prometheus、JWT、Redis、Grafana、MCP、Docker Compose 写进下一阶段。** 这些对 Spring Boot 平台有意义，对单用户本地助手是搬运成本。面试官更吃「为什么不做」而不是「我也有 Grafana」。
4. **Milvus 不是本项目的检索缺口。** 几百个 chunk 上 SQLite 向量 + BM25 已经有 Recall@3 ≥ 0.92。换向量库不增加自学价值，也不自动变成 Agent。
5. **测试数量 187 vs 193 不是差距。** 本仓库阶段隔离测试和离线 CI 已经能讲；为对齐数字补测试没有意义。

## 4. 建议（给计划决策用）

**当前建议：不开新的平台里程碑。**

原因：

- M5 退出条件已满足，根 README 明确「不再扩平台功能」。
- 现有系统缺的是持续使用和面试彩排，不是再一个运行时。
- 源文档是招聘对齐调查，证据不足以上升为 `m6-*-plan.md`。

**建议的默认行动：**

1. 按 `docs/demo.md` 把工作台学习闭环跑熟，能口头讲清 `tool_trace`。
2. 面试叙事保持诚实：这是**领域状态机编排的学习 Agent**，不是通用 ReAct Agent。
3. 把本文件留在 `docs/plans/references/`，等出现明确招聘目标或使用中的真实痛点，再决定是否立项。

**只有同时满足下面条件，才值得写下一份执行计划：**

- 目标岗位明确要求 Function Calling / Agent 循环，且现有话术无法过关；
- 方案保证现有 `/api/v1/study-sessions`、工作台、187 项测试、离线 BM25 评测不被破坏；
- 范围能在一层增量里讲完，而不是复制 `ai-agent-platform`。

## 5. 若未来立项，最小可做范围

若以后开阶段，建议叫「可选决策层」，不要叫「通用 Agent 平台」。原则是：**状态机仍是默认路径，LLM 只在配置存在时多一种选工具的方式。**

| 顺序 | 做什么 | 为什么值得 | 验收 |
| --- | --- | --- | --- |
| 1 | 把 QA/检索、Quiz、review-due、review-log 收成统一 Tool 协议（name/description/parameters/execute） | 现有服务已经能干活，缺的是可讲述的工具边界；也为 Function Calling 做接口 | 工具可单测；`study-sessions` 仍走原状态机 |
| 2 | 可选 ReAct/function-call 循环，仅 `SA_LLM_API_KEY` 开启 | 补招聘话术，但不替换教学法 | 最大步数、单步超时、重复观测熔断；无 LLM 时 100% 走旧路径 |
| 3 | 给 `run_evaluation.py` 加小组 Agent 任务集（脚本化，可 mock LLM） | 有数字才能讲「工具调用准确率/任务成功率」 | 离线可跑；不依赖真实模型下载 |
| 4 | 复用 BGE 做问答语义缓存（阈值 + TTL + `cache_hit` 指标） | 现成 embedding 和 metrics，成本故事可量化 | Recall@3 不退化；命中率可从 `/health` 或日志看到 |

建议的护栏（若做 ReAct，必须一起做）：

- 最大步数（建议 8）
- 单步超时（建议 30s）
- 同一 action+observation 重复 N 次立即停止
- 最终必须能落到讲解或复习记录，不允许空转
- 失败回退到当前 `StudySessionService`

## 6. 明确不做

- 不迁移 Java/Spring/LangChain4j
- 不把 Milvus、Redis、JWT、Grafana 当作对齐必需品
- 不把 MCP/A2A 当实现目标，了解协议即可
- 不删除或旁路现有学习会话 API 和工作台
- 不在没有评测数字前宣称「已经是 ReAct Agent」

## 7. 对面试材料的影响

当前 `docs/interview/README.md` 的叙事仍然成立，但要改一处边界表述：

- **可以讲：** Markdown 知识库、混合检索、带出处问答、服务端学习会话、`tool_trace`、离线降级、90 题 Recall@3。
- **不要讲成：** 已经实现 ReAct、工具注册表、Function Calling、Agent 全链路评估。
- **被追问「这算 Agent 吗」时的建议答法：** 这是面向学习闭环的领域 Agent：工具和步骤是确定性的，因为教学流程已知；通用 ReAct 会破坏复习记录和离线可用性。若岗位要求自主工具选择，可以沿 Tool 协议做增量，而不是推翻现有状态机。

相关材料分工：

| 文件 | 角色 |
| --- | --- |
| `docs/interview/StudyAssistanceAgent_requirement.md` | 招聘对齐原始调查（模块对照与 P0/P1/P2 清单） |
| `docs/plans/references/agent-alignment-analysis.md` | 对本仓库的核实与计划建议（本文件） |
| `docs/interview/README.md` | 现行面试叙事，不以源文档的改造清单为已实现能力 |
| `docs/PLAN.md` | 仍是里程碑唯一真源；在新执行计划出现前保持 M5 收口 |

## 8. 结论

源文档作为**招聘能力对照表**有价值，作为**立刻开工说明书**过重。

本项目已经具备可演示的学习 Agent 闭环；真正的缺口是「LLM 是否自主选工具」，不是检索、测试或文档。当前更优决策是继续使用与彩排。若未来因岗位要求立项，只做 Tool 协议 + 可选循环 + 小规模 Agent 评测，并继续把确定性会话当作默认和降级路径。