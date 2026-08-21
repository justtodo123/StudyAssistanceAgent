# 项目计划 · StudyAssistanceAgent

> 通用学习 Agent 的 harness 框架。M0–M5 是最小实现（默认计算机知识包 + 学习闭环）。
> **双目标**：① 按用户目标把任意知识源学完（产品价值）；② 可讲清 Agent harness / RAG / 计划执行（工程价值）。
> 状态图例：⬜ 未开始 ｜ 🔄 进行中 ｜ ✅ 完成
> **当前阶段**：M6a 前置 crawler 收口；M6a/M6b 已完成设计、尚未开工。里程碑与退出方向以**本文**为准。
> `docs/plans/references/` 只辅助决策，不是最终依据。
> 数据源门禁、embedding/索引参数、错误码、生成分层与延迟分位数见
> [`docs/standards/runtime-contracts.md`](standards/runtime-contracts.md)。
> **M6 拆分说明**：M6 按“前置收口 → 契约收敛 → 兼容骨架 → 只读 Agent 预览”推进。M6b 不接管正式
> `study-sessions`；完整自主 Runner、写工具与 Agent 评测后移到 M10。

## 一、项目定位（一句话）

**「通用学习 Agent harness」**：用户接入知识源、声明等级/掌握度/目标 → 外部 AI（可降级）生成学习计划 →
harness 按计划从知识库选题并跑学习闭环（讲解/测验/复习）→ 监控进度与偏差。
仓库内 OS/DS/CO 笔记是默认知识包，不是唯一数据源。

## 二、技术选型（已拍板）

| 层 | 选型 | 理由 |
| --- | --- | --- |
| 知识库 | 纯 Markdown + frontmatter（`knowledge/`） | 数据是个人资产，可读/可版本化/可迁移 |
| 后端 | Python + FastAPI + uvicorn | 轻量、RAG/Agent 生态好、面试叙事友好 |
| 向量 | 本地 BGE（sentence-transformers），可选安装 | 离线、零 API 成本、隐私；未装时自动降级关键词 |
| 检索 | BM25 + 向量多路召回 + RRF 融合 | 混合检索，鲁棒、无需调参 |
| LLM | OpenAI 兼容接口（DeepSeek 等），可配 | 不配则降级为笔记摘要，保证总是有输出 |
| 存储 | 控制面 SQLite；向量 SQLite→LanceDB，万级可选 Qdrant | 协议可替换；默认离线可跑 |
| 数据源 | 默认人工 Markdown pack；网页/AI 只产生候选或响应 | 检索允许名单见 runtime-contracts；不把原始 PDF 写入 Git |

**架构**（参考 `ai_agent_platform` 的 MultiRecall/RRF/LongContext 模式，做个人级瘦身）：

```
提问 / 工作台 GET /
  → MultiRecallService
       ├─ 路1: LocalVectorStore(BGE，可选)
       └─ 路2: Bm25Search(bigram 关键词)
    → RRF 融合 → 带 file 出处
    → QaService: LLM 生成或降级笔记摘要
    → StudySessionService: QA → Quiz → 评估 → review-log
    → SQLite learning_state + FastAPI /api/v1/{search,qa,study-sessions,...}
```

稳定契约（已落地，不另开里程碑）：数据源类型与入库门禁、embedding/索引参数表、
`detail.code` 错误码、QA `generation_layer`、`/health` 的 P50/P95/P99。详见
[`docs/standards/runtime-contracts.md`](standards/runtime-contracts.md)。

## 三、里程碑

### M0：仓库与规范初始化 ✅
- ✅ 仓库基础文件、CLAUDE.md、Git 规范、知识库框架、参考资料索引、项目计划
- ✅ Python 平台骨架（FastAPI + 多路召回 + 降级 + SSE）
- ✅ 「提问→检索 knowledge/→带出处回答」验证链路（6 个测试通过，检索/问答/流式端点验证）
- ✅ 面试价值文档（docs/interview/）与 RAG 评估脚本（tools/run_evaluation.py）
- ✅ OS 知识库首轮 6 篇条目 + 20 题 RAG 评测集（tools/evaluations/os.json）
- ✅ 各级 README.md 文档就绪（根/ docs/ platform/ tools/ knowledge/）
- ✅ 接入 GitHub 远程仓库（origin 已配置，`feature/m1a-os-knowledge` 经 PR #1 合并）
- **退出条件**：初始实现 + 平台骨架 + 双目标文档就绪，远程可克隆。

### M1：数据先行（核心专业课知识库）
> 目标：让「自学价值」真实落地，同时给 M2 平台喂真数据。
> **分支映射**：`feature/m1a-os-knowledge` → `feature/m1b-ds-knowledge` →
> `feature/m1c-co-knowledge` → `feature/m1d-platform-polish`
- ✅ 操作系统：`knowledge/os/`（进程/调度/同步/死锁/内存/文件）→ 15 篇条目 + 真题复盘（M1a 完成，hybrid RAG 评测 Recall@3=0.970，33 题评测集覆盖全部条目）
- ✅ 数据结构复习：`knowledge/ds/`（绪论/线性表/栈队列/串数组广义表/树/图/查找/排序/堆与优先队列/真题复盘）10 篇完成（M1b 完成）
- ✅ 计算机组成原理：`knowledge/co/`（概述/数据表示/运算器/存储系统/指令系统/CPU设计/总线I/O/MIPS实验/浮点数运算/期考复盘）10 篇完成（M1c 完成）
- ✅ 每课配 RAG 评测集：OS 33 题 + DS 23 题 + CO 19 题，共 75 题
- ✅ 计算机网络：`knowledge/network/`（概述/体系结构/性能指标/物理层/编码/信道容量/数据链路层/差错控制/流量控制/CSMA-CD/以太网/网络层/IP/子网划分/ARP-ICMP/路由/NAT/传输层/TCP连接/TCP可靠/TCP拥塞/UDP/应用层/DNS/HTTP/FTP-SMTP/Socket/安全概述/加密签名/防火墙-VPN/真题复盘）31 篇完成 + 评测集 30 题
- **退出条件**：4 门课各 ≥10 篇条目；评测 Recall@3 ≥ 0.8；能演示「问真题→检索到→带出处答」。

#### M1d：平台打磨（已完成）
> **目标**：评测闭环 + 平台体验 + 文档同步，满足 M1 退出条件。
> **状态**：已完成；当前项目已进入 M3 工程质量与沉淀阶段。
> **分支**：`feature/m1d-platform-polish`

**待办清单**：
1. ✅ **全量评测跑通**：OS Recall@3=1.000, DS=0.957, CO=1.000（均≥0.8）
2. ✅ **补足条目数**：DS 9→10（+堆与优先队列）、CO 9→10（+浮点数运算）
3. ✅ **检索质量调优**：RRF 文件去重 + 课程过滤前移 + 摘要截断优化
4. ✅ **平台体验优化**：同上三项优化 + 6 测试全通过
5. ✅ **文档同步**：更新 PLAN.md、各课程 README、knowledge/README
6. ✅ **演示验证**：确保「问真题→检索到→带出处答」链路可用（OS Recall@3=1.000, DS=0.957, CO=1.000，3 道真题端到端 QA 验证通过）

### M2：Agent 学习辅助能力（面试深水区）
> **分支映射**：`feature/m2a-review-plan` → `feature/m2b-quiz-generator`
- ✅ 复习计划生成（skill/接口）：课程+目标 → 分日学习计划（API `/api/v1/review-plan` + Skill `review-plan`）
- ✅ 随堂测验生成：从条目/真题自动出题（API `/api/v1/quiz` + Skill `quiz-generator`，三数据源：例题+评测集+概念模板）
- ✅ 复习排程：基于遗忘曲线的间隔重复提醒（API `/api/v1/review-log` + `/api/v1/review-due` + Skill `review-due`，间隔序列 1→2→4→8→16→32 天）
- ✅ 「多轮工具调用」演示：问知识点→查笔记→出题→断言掌握（Skill `study-assistant`，串联 QA+Quiz+Review-log，6 个集成测试）
- **退出条件**：✅ ≥2 个学习辅助能力可在 API/skill 中演示（实际 4 个），能答「工具编排」追问。

### M3：工程质量与沉淀（M3a/M3b/M3c/M3d 均已完成）
> **分支映射**：`feature/m3a-vector-store` → `feature/m3b-observability` →
> `feature/m3c-interview-bank` → `docs/m3d-project-closure`
> **当前状态**：M3a 向量存储迁移、M3b 可观测性、M3c 面经库和 M3d 文档闭环均已完成；M3d 已于 2026-08-18 通过 `--no-ff` 合并到 `master`。
- ✅ 可选：接入本地 SQLite 向量库，并保留线性后端与 BM25 降级路径
- ✅ 观测/日志：检索/QA 延迟、进程内缓存指标、健康检查字段与敏感信息过滤
- ✅ 面经库 `knowledge/interview/`：51 条，覆盖 OS/DS/CO/RAG/Agent/项目追问
- ✅ 完成项目状态、测试统计、文档导航与退出条件的统一收口；课程知识库数量补齐另开独立阶段。
- **退出条件结论（M3 阶段）**：部分满足。面经 51 条（≥50）、75 题 RAG 评测闭环和面试追问材料已满足；当时长期要求“三门课程各 ≥20 篇”尚未满足，已由 M4 独立阶段补齐。

### M4：课程知识库规模补齐（已完成并进入 master）
> **分支**：`feature/m4-knowledge-scale`
> **当前状态**：OS、DS、CO 已分别从 15/10/10 篇补齐至 20/20/20 篇，共 60 篇课程条目；
> 新增 15 道评测题，M4 阶段测试 14 项、根级测试 104 项和平台测试 40 项全部通过；
> 实现提交 `106164d` 已于 2026-08-18 进入 `master`。
- ✅ OS 新增线程、IPC、实时调度、文件分配、设备管理 5 篇。
- ✅ DS 新增分治、动态规划、AVL/B+ 树、并查集、字符串匹配、哈希、图算法、外部排序 10 篇。
- ✅ CO 新增数制、乘除法、Cache、地址转换、控制器、流水线、中断、总线、性能 10 篇。
- **退出条件**：✅ 三门课程各 ≥20 篇、评测引用有效、Recall@3 ≥0.8、阶段测试与回归通过；离线 BM25 评测为 OS 1.000、DS 0.929、CO 1.000。

### M5：学习 Agent 会话化与可交付演示（已完成）
> **执行计划**：`docs/plans/m5-agent-session-delivery-plan.md`
> **收口**：Level 1（M5a/M5b）与 Level 2（M5c/M5d/M5e）均已完成，作为 harness 的最小实现冻结。
> 2026-08-20 起产品定位升级为通用学习 Agent harness，后续阶段见 M6–M10。
- ✅ M5a：统一三课 90 题离线评测入口，支持汇总指标和 JSON 报告（离线 BM25 Recall@3：OS 1.000、DS 0.929、CO 1.000）。
- ✅ M5b：实现服务端学习会话状态机，编排 QA、Quiz、答案评估和 Review-log（`POST/GET /api/v1/study-sessions`）。
- ✅ M5c：使用 SQLite 持久化会话、答题记录、掌握度和复习历史（`platform/.cache/learning_state.sqlite3`，兼容读取 `review_history.json`）。
- ✅ M5d：提供最小学习工作台，完成讲解、作答、反馈和复习记录交互（`GET /`）。
- ✅ M5e：增加离线 CI、一键启动、模型缓存说明和演示基线。
- **Level 1 退出条件**：一条命令完成 90 题离线评测；一个 API 会话完成“检索→讲解→出题→作答→评估→记录复习”；无 LLM 和向量模型时仍可运行。
- **完整退出条件**：✅ 会话可跨重启恢复；工作台可完成学习闭环；离线 CI 与一键启动已落地；阶段测试、回归和平台测试保持通过。
- **收口结论**：M5 作为 MVP 关闭。默认学习闭环与离线交付不再回退；通用运行时与可插拔数据源改由 M6 起按路线图建设。

### M6–M10：通用学习 Agent Harness（设计完成，尚未开工）
> **最终依据**：本节（M6–M10）。辅助分析见 `docs/plans/references/`，冲突时以本文为准。
> **当前状态**：先完成 M6a 前置 crawler 收口；M6a/M6b 仅完成设计。M0–M5 回归必须持续全绿。
> **执行计划**：`docs/plans/m6a-harness-skeleton-plan.md`、`docs/plans/m6b-agent-core-plan.md`。
> **评测基线**：默认只自动发现 OS/DS/CO 三课 90 题；Network 30 题是显式运行的扩展集，不进入默认门禁。

- ⬜ **M6a-P0 crawler 前置收口**：登记既有 `tools/crawler/` 与 `tests/M6_crawler/`，固定独立依赖、marker、
  CI/测试方式和人工审核后入库边界。crawler 默认写入 `platform/.cache/crawler-candidates/`，
  不自动注册 Source，也不代表 M7 生命周期完成。入库门禁已按 runtime-contracts 生效。
- ⬜ **M6a Harness 兼容骨架**：先完成契约收敛，再适配现有实现。
  - 仓储按职责区分 LearningStateRepository、ReviewRepository、SourceRegistry 与 RetrievalIndex；复用现有
    `SqliteLearningStore` 和 `VectorStore`，不创建承载所有数据的泛化 Store。
  - Runner 必须表达跨请求的 `start/resume/get` 或 `step(event)` 语义；正式学习状态仍由现有状态机负责。
  - Tool 使用 `ToolContext`、结构化 `ToolResult`、能力/副作用分类；领域写入不绕过状态机和领域服务。
  - Source 预留稳定 source/document/chunk ID、logical URI、fingerprint/revision/delete 语义；M6a 只做启动期
    静态额外 Markdown 源 bootstrap，持久化注册、增量同步、删除传播和多源隔离留给 M7。
  - 保持现有 API/OpenAPI、旧会话恢复和默认三课 90 题基线兼容。
  - 执行计划：`docs/plans/m6a-harness-skeleton-plan.md`。
- ⬜ **M6b Agent 只读预览（工具调用决策层）**：独立 preview 入口 + ToolRegistry + provider-neutral
  `LLMClient`/`ModelTurn` + 原生 provider tool-call adapter。文本 JSON 只能作为显式兼容 fallback，不能冒充
  原生 Function Calling。仅开放 retrieve、quiz preview、review-due 等只读工具，禁止写会话、掌握度和复习历史。
  - 预览循环采用 model turn → validate → authorize → execute → append result；不要求或持久化原始 Thought。
  - 设总 deadline、模型/工具超时、turn/tool-call/token/cost/result-size 预算、取消、重复调用熔断和确定性终止。
  - `agent_trace` 与状态机 `domain_trace` 分离；不记录原始 Thought、用户答案、知识正文或密钥。
  - 不新增 `SA_RUNNER=react`，不接管 `/api/v1/study-sessions`，preview 失败也不启动状态机作为无条件回退。
  - 执行计划：`docs/plans/m6b-agent-core-plan.md`。
- ⬜ **M7 用户数据源与千级检索**：持久化源注册/同步、revision/delete、跨源隔离、FTS5 和 1k–3k chunk 基线。
- ⬜ **M8 专业化存储**：统一控制面 schema；默认 LanceDB；Qdrant 作为万级可选项；保留离线降级。
- ⬜ **M9 目标驱动计划**：外部 AI 按等级/掌握度/目标生成计划；按计划选题；监控进度和偏差。
- ⬜ **M10 完整自主 Runner 与 Harness 对外**：在 M7–M9 契约稳定后实现可选自主 Runner、写工具授权、
  checkpoint/resume、幂等副作用和失败恢复；建立 Agent 任务评测（成功率、工具选择/参数合法率、终止、成本、
  延迟），并交付知识包 manifest 与 MCP 最小实现。状态机继续作为正式默认和无 LLM 降级路径。

**总退出方向**：用户能自定义知识源，在百/千/万级数据上按目标学习并看到计划执行情况；无外部 AI 时仍可
运行。M6b 只验证隔离的只读工具调用，完整自主 Runner 到 M10 才作为与教学状态机正交的可选执行器落地。

## 四、风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 数据先行但精力有限，笔记跟不上 | M1 切入最急的课（如 OS 考前）；单篇笔记 20 分钟，按真题驱动 |
| 检索效果差（Recall 低） | 用评测脚本量化；调整切块策略（小节切分 vs 整篇）、扩 tags |
| 面试被追问「和 RAG demo 有何不同」 | docs/interview/README 已备 8 大追问答案；多用「数据驱动优化」叙事 |
| 参考项目 Java/Spring 太重不适合 | 已确认 Python 栈 + 本地向量 + 降级路，仍借鉴其 MultiRecall/RRF 模式 |
| 本机 GitHub 访问受限 | SSH 走 443 已配置；push 由用户手动完成 |
| 做成空框架、课内体验变差 | M6a 保持 API 与旧会话兼容；正式状态由学习状态机继续负责 |
| Agent 预览误写学习状态 | M6b 使用独立只读入口和工具 allowlist；完整写工具与 Runner 后移 M10 |
| Agent 失败后重复副作用 | M6b 不执行写工具；M10 在 checkpoint、授权和幂等契约完成后才接正式执行路径 |
| crawler 产物污染默认知识包 | crawler 只生成候选 Markdown；人工审核并显式注册后才进入检索 |
| 万级数据污染 Git 仓库 | 用户源放仓库外；Git 只存默认 pack 与配置 |
| 外部 AI 把全书塞进上下文 | Planner 只使用目录摘要 + 掌握度，不喂原文全书 |

## 五、面试叙事核心（详见 docs/interview/README.md）

一句话 + 5 个设计决策 + 学习状态机工具链 + 能力边界：正式路径是状态机；M6b 是只读 preview（未开工）；
完整自主 Runner 在 M10 且不替换教学法。招聘对照原文不是执行计划。

---

*创建：2026-08-10 · 版本：v2.2（2026-08-21：落地 runtime-contracts，统一面试口径）· 维护：每次会话开工查看本文档*



### M3a: Vector-store migration (completed 2026-08-17)

- Added the shared `VectorStore` protocol and a persistent SQLite implementation.
- Retained the `linear` in-memory backend for rollback and debugging.
- Added chunk-ID upsert, full replacement, migration, restart persistence, threshold filtering,
  and dimension validation.
- Persisted chunk fingerprints and embedding model metadata so stale indexes rebuild automatically.
- Preserved BM25 fallback when sentence-transformers is unavailable.
- Validation: 22 M3a tests, 40 M0-M2 plus M3a tests, and 21 regression tests passed.
