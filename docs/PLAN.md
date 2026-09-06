# 项目计划 · StudyAssistanceAgent

> 通用学习 Agent 的 harness 框架。M0–M5 是最小实现（默认计算机知识包 + 学习闭环）。
> **双目标**：① 按用户目标把任意知识源学完（产品价值）；② 可讲清 Agent harness / RAG / 计划执行（工程价值）。
> 状态图例：⬜ 未开始 ｜ 🔄 进行中 ｜ ✅ 完成
> **当前阶段**：M6a、M6b、M7 均为 `ADMITTED / COMPLETE`；M7 基础设施范围已获批，生产开工门禁为
> `AUTHORIZED`，并于 2026-09-06 在独立人工完成批准后成为 `ADMITTED / COMPLETE`；M8–M10 的事实型
> M7 退出前置已满足，但 M8–M10 自身仍为 `BLOCKED / NOT_STARTED`。
> 2026-08-31 P0 治理冻结复测已完成：默认 OS/DS/CO 90 题保持可信默认包政策，Network candidate 不进入默认索引；
> M7 基础设施准入不关闭 Network P0，也不批准任何 Network 文档。
> 里程碑、准入与退出方向以**本文**为准。
> **准入门禁**：[`docs/standards/stage-admission-gates.md`](standards/stage-admission-gates.md)；机器登记见
> [`stage-admission-gates.json`](standards/stage-admission-gates.json)。计划或登记表单独变更均不能批准阶段。
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
| 存储 | 当前学习状态与向量持久化均为 SQLite；M8 规划 LanceDB/Qdrant | 当前向量仍为线性余弦；协议可替换且默认离线可跑 |
| 数据源 | 默认人工 Markdown pack；网页/AI 只产生候选或响应 | 检索允许名单见 runtime-contracts；不把原始 PDF 写入 Git |

**架构**（参考 `ai_agent_platform` 的 MultiRecall/RRF/LongContext 模式，做个人级瘦身）：

```
提问 / 工作台 GET /
  → MultiRecallService
       ├─ 路1: SqliteVectorStore（BGE，可选；持久化 + 线性余弦）
       │        └─ SA_VECTOR_STORE=linear 时使用内存 LocalVectorStore
       └─ 路2: Bm25Search（bigram 关键词）
    → RRF 融合 → 带 file 出处
    → QaService: LLM 生成或降级笔记摘要
    → StudySessionService: QA → Quiz → 评估 → review-log
    → platform/.cache/learning_state.sqlite3 + FastAPI /api/v1/{search,qa,study-sessions,...}
```

稳定契约（已落地，不另开里程碑）：数据源类型与入库门禁、embedding/索引参数表、
`detail.code` 错误码、QA `generation_layer`、`/health` 的 P50/P95/P99。详见
[`docs/standards/runtime-contracts.md`](standards/runtime-contracts.md)。

## 三、里程碑

### M0：仓库与规范初始化 ✅
- ✅ 仓库基础文件、CLAUDE.md、Git 规范、知识库框架、参考资料索引、项目计划
- ✅ Python 平台骨架（FastAPI + 多路召回 + 降级 + SSE）
- ✅ 「提问→检索 knowledge/→带出处回答」核心链路（当时 6 项平台测试覆盖索引、BM25、检索与 QA 服务；SSE 端点契约由后续回归测试补齐）
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
- ✅ 「多轮工具调用」演示：Skill `study-assistant` 串联 QA + Quiz + Review-log（当时 6 项集成测试）；正式答案评估和状态转换在 M5b 落地
- **退出条件**：✅ ≥2 个学习辅助能力可在 API/skill 中演示（实际 4 个），能答「工具编排」追问。

### M3：工程质量与沉淀（M3a/M3b/M3c/M3d 均已完成）
> **分支映射**：`feature/m3a-vector-store` → `feature/m3b-observability` →
> `feature/m3c-interview-bank` → `docs/m3d-project-closure`
> **当前状态**：M3a 向量存储迁移、M3b 可观测性、M3c 面经库和 M3d 文档闭环均已完成；M3d 已于 2026-08-18 通过 `--no-ff` 合并到 `master`。
- ✅ M3a：落地共享 `VectorStore` 协议与持久化 `SqliteVectorStore`，保留内存 linear 后端和 BM25 降级；支持 chunk-ID upsert、全量替换、迁移、重启恢复、阈值/维度校验，并按内容 fingerprint 与 embedding 模型元数据自动重建（当时阶段快照：M3a 22 项、平台原始测试 40 项）
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
- **退出条件**：✅ 三门课程各 ≥20 篇、评测引用有效、Recall@3 ≥0.8、阶段测试与回归通过；2026-08-18 历史离线 BM25 基线为 OS 1.000、DS 0.929、CO 1.000。

### M5：学习 Agent 会话化与可交付演示（已完成）
> **执行计划**：`docs/plans/m5-agent-session-delivery-plan.md`
> **收口**：Level 1（M5a/M5b）与 Level 2（M5c/M5d/M5e）均已完成，作为 harness 的最小实现冻结。
> 2026-08-20 起产品定位升级为通用学习 Agent harness，后续阶段见 M6–M10。
- ✅ M5a：统一三课 90 题离线评测入口，支持汇总指标和 JSON 报告（2026-08-18 历史基线：OS 1.000、DS 0.929、CO 1.000）。
- ✅ M5b：实现服务端学习会话状态机，编排 QA、Quiz、答案评估和 Review-log（`POST/GET /api/v1/study-sessions`）。
- ✅ M5c：使用 SQLite 持久化会话、答题记录、掌握度和复习历史（`platform/.cache/learning_state.sqlite3`，兼容读取 `review_history.json`）。
- ✅ M5d：提供最小学习工作台，完成讲解、作答、反馈和复习记录交互（`GET /`）。
- ✅ M5e：增加离线 CI、一键启动、模型缓存说明和演示基线。
- **Level 1 退出条件**：一条命令完成 90 题离线评测；一个 API 会话完成“检索→讲解→出题→作答→评估→记录复习”；无 LLM 和向量模型时仍可运行。
- **完整退出条件**：✅ 会话可跨重启恢复；工作台可完成学习闭环；离线 CI 与一键启动已落地；阶段测试、回归和平台测试保持通过。
- **收口结论**：M5 作为 MVP 关闭。默认学习闭环与离线交付不再回退；通用运行时与可插拔数据源改由 M6 起按路线图建设。

### M6–M10：通用学习 Agent Harness（M6a/M6b/M7 已完成，M8–M10 仍阻断）
> **最终依据**：本节（M6–M10）。辅助分析见 `docs/plans/references/`，冲突时以本文为准。
> **统一门禁**：[`stage-admission-gates.md`](standards/stage-admission-gates.md) 定义决策、准入、撤销与禁止事项；
> [`stage-admission-gates.json`](standards/stage-admission-gates.json) 只用于机器检查，不能单独批准阶段。
> **保护基线**：M0–M5 回归必须持续全绿；默认自动发现 OS/DS/CO 三课 90 题，Network 30 题仍为显式扩展集。
> 2026-08-25 M6a 保护基线已在受标识候选树上真实复验并满足 prerequisite；这不构成 M6a 批准或能力实现。
> 当前证据：`docs/baselines.md`；2026-08-31 默认 Recall@3 为 OS 1.000、DS 0.929、CO 1.000，加权 0.978。

| 阶段 | 准入 | 交付 | 准备/执行计划 | 当前结论 |
| --- | --- | --- | --- | --- |
| M6a | `ADMITTED` | `COMPLETE` | [`m6a-harness-skeleton-plan.md`](plans/m6a-harness-skeleton-plan.md) | 八项强制决策与保护基线已闭合；justtodo123 于 2026-08-25 批准开工，M6a-1 与 M6a-2 自动化门禁已通过，M6a-4 已完成收口 |
| M6b | `ADMITTED` | `COMPLETE` | [`m6b-agent-core-plan.md`](plans/m6b-agent-core-plan.md) | 获批的默认关闭只读 Agent Preview 已实现并完成 closeout：阶段隔离、隐私/零写入、离线 p95、文档、治理与完整回归门禁通过；批准明确不包含 M7 |
| M7 | `ADMITTED` | `COMPLETE` | [`m7-source-lifecycle-plan.md`](plans/m7-source-lifecycle-plan.md) | 十二项强制决策、保护基线、Source lifecycle/delete/isolation/fallback、冻结 1k/3k BGE 与五格式 100×20 parser/normalized/lifecycle 证据已闭合。原 2026-08-31 准入与开工授权保持不变；justtodo123 于 2026-09-06 在 `m7-infrastructure-only-v1` 范围内独立批准 `M7 COMPLETE`。技术证据本身不产生批准；M6b preview、Quiz、Review Plan 与 study-sessions 仍不含用户源 |
| M8 | `BLOCKED` | `NOT_STARTED` | [`m8-specialized-storage-plan.md`](plans/m8-specialized-storage-plan.md) | `M8-M7-EXIT=SATISFIED`；M8 自身八项强制决策、后端选择与独立批准仍未闭合，Milvus/LanceDB/Qdrant 均未选定或获批 |
| M9 | `BLOCKED` | `NOT_STARTED` | [`m9-goal-driven-planning-plan.md`](plans/m9-goal-driven-planning-plan.md) | `M9-M7-EXIT=SATISFIED`；仍等待 M8 退出，计划/mastery 权威设定与独立批准仍 `OPEN` |
| M10 | `BLOCKED` | `NOT_STARTED` | [`m10-autonomous-runner-plan.md`](plans/m10-autonomous-runner-plan.md) | `M10-M7-EXIT=SATISFIED`；仍等待 M8/M9，写授权、恢复、rollout 与独立批准仍 `OPEN` |

阶段只有在所有强制 Decision 为 `RESOLVED`、前置/保护证据有效、兼容不变量确认且用户或项目负责人填写批准
记录后，才能由本文同步改为 `ADMITTED`。批准范围只能缩小边界，不能批准被排除的数据或下游阶段；若登记独立
生产开工门禁，只有 `AUTHORIZED` 后交付才能进入 `IN_PROGRESS`。Agent 不得自行批准准入或开工。前提失效时
改为 `REVOKED` 并停止生产实施。

**依赖顺序**：M6b 与 M7 都只依赖 M6a 退出证据，彼此不互为前置。M7 已完成 Source Registry、
source-local FULL/INCREMENTAL/delete/isolation、FTS5/vector/offline fail-closed、Search/QA overlay 与冻结技术验收，
并于 2026-09-06 取得独立完成批准。因此 M8/M9/M10 的事实型 M7 退出前置均为 `SATISFIED`；这不批准任何下游阶段。
M8 仍须闭合自身决策、后端选择、依赖、迁移、parity、fallback、benchmark 与人工批准；M9 仍依赖 M8，M10 仍依赖
M8–M9，且都不以 M6b 为写路径或 Source 生命周期前置。

- ✅ **M6a-P0 crawler 前置收口**：`tests/M6_crawler` 使用独立 marker `m6_crawler`；离线测试 mock HTTP；
  CI job `crawler-offline` 安装 `tools/crawler/requirements.txt` 并跑 `-m "m6_crawler and not online"`。
  默认写入 `platform/.cache/crawler-candidates/`，不自动注册 Source。在线 smoke 仅显式
  `workflow_dispatch`。不代表 M7 生命周期完成。
- ✅ **M6a Harness 兼容骨架**：M6a-1 协议契约和 M6a-2 默认 `knowledge-pack` 的
  Source / SourceChunk / RetrievalIndex 薄兼容适配已通过自动化门禁；M6a-3 确定性工具、状态机 Runner、启动期静态额外源、default/combined generation 分离和单进程 service lock 已落地；M6a-4 文档、API/OpenAPI/链接检查与收口已完成。
  - 仓储按职责区分 LearningStateRepository、ReviewRepository、SourceRegistry 与 RetrievalIndex；复用现有
    `SqliteLearningStore` 和 `VectorStore`，不创建承载所有数据的泛化 Store。
  - Runner 必须表达跨请求的 `start/resume/get` 或 `step(event)` 语义；正式学习状态仍由现有状态机负责。
  - Tool 使用 `ToolContext`、结构化 `ToolResult`、能力/副作用分类；领域写入不绕过状态机和领域服务。
  - Source 身份按逻辑命名空间定义：`source_id + logical_uri` 稳定派生 document ID，chunk ID 带切块版本；
    本地挂载移动不改变身份，绝对路径不进入响应、日志或 trace。
  - 缓存/索引失效覆盖 revision/fingerprint、解析切块版本、检索配置和 embedding 元数据；快照替换清理
    stale BM25/vector/result-cache，M6a 额外源只进入 Search/QA，不扩散到 Quiz、Review Plan、默认评测或 crawler。
  - `StudySessionService` 继续独占状态转换、答案评估、持久化与 review-log；用户/模型/audit 三层可见性和
    `domain_trace`/`agent_trace` 分离。运行时删除、tombstone 与增量删除传播留给 M7。
  - 保持现有 API/OpenAPI、旧会话恢复和默认三课 90 题基线兼容。
  - 执行计划：`docs/plans/m6a-harness-skeleton-plan.md`。
- ✅ **M6b Agent 只读预览（工具调用决策层）**：获批范围、closeout 门禁与证据同步均已完成，当前为
  `ADMITTED / COMPLETE`。独立 `POST /api/v1/agent-preview` 仅在启动前显式启用并配置至少
  32 UTF-8 字节的 Bearer secret 时注册；默认应用与 OpenAPI 无该路由。
  - 使用官方 Anthropic SDK、固定 `claude-opus-5`、adaptive thinking、low effort 和原生 strict
    `tool_use/tool_result`；provider-neutral adapter 不把 SDK 对象、thinking 或原始 provider 数据泄露到领域边界。
  - 显式 allowlist 仅开放 `retrieve`、`quiz_preview`、`review_due`，注册与执行双重校验
    `READ + NONE + idempotent + read permission`；preview 检索使用 `DEFAULT_PLUS_EXTRAS`，正式学习会话继续固定
    `DEFAULT_ONLY`。
  - manual loop 受总 deadline、model/token-count/tool timeout、turn/call/token/cost/result/answer 预算、容量 2、
    retry/no-replay、重复调用熔断、取消和稳定 termination reason 约束；失败不创建正式 session 或写领域状态。
  - HMAC `agent_trace` 与状态机 `domain_trace` 分离，只保留 allowlist 元数据并在响应后丢弃。prompt 与受限工具结果会
    发送给 Anthropic；本地日志、trace、错误、OpenAPI、持久化与未授权边界不得泄露 prompt、正文、凭据、路径或
    provider 原始响应。
  - `tests/M6b/` 2026-08-28 首轮 111 项全通过；阻断性 fake-provider benchmark 为 20 次 warm-up、200 次
    measured、并发 2，p95 5.179 ms，0 unexpected termination，replay consistency 100%。该 p95 只属于首轮
    closeout，不得与后续 stabilization 证据混用。
  - 2026-08-29 stabilization：当前共收集 129 项（普通套件 126 passed、3 deselected；专用 `m6b_benchmark`
    3 passed）。独立 evidence `stabilization-20260829-03` 的同规模 benchmark 为 p95 9.252 ms，200 次
    `completed`，意外终止 0，重放一致率 100%。真实 Anthropic smoke 未运行，不据此声称 provider 性能。
  - 不新增 `SA_RUNNER=react`，不接管 `/api/v1/study-sessions`；写工具、checkpoint/幂等、自主 Runner 和 Agent
    任务评测仍属于 M10。
  - 执行计划：`docs/plans/m6b-agent-core-plan.md`。
- ✅ **M7 用户数据源与千级检索**：基础设施范围已于 2026-08-31 获批并获得独立开工授权；在冻结技术证据
  与 correctness 收口完成后，justtodo123 于 2026-09-06 明确批准 `M7 COMPLETE`，当前为
  `ADMITTED / COMPLETE`。完成批准仅适用于 `m7-infrastructure-only-v1`，且与 admission、implementation-start
  记录分离；benchmark `m7_exit=true`、测试或技术全绿本身均不能产生该批准。Source Registry、manifest/parser、
  normalized document、FULL/INCREMENTAL、delete/isolation、generation-bound FTS5/vector、offline fail-closed 与
  Search/QA 的受信任内部 principal overlay 已落地；M6b preview、Quiz、Review Plan 与 study-sessions 仍不含用户源。
  2026-09-04 冻结 1k/3k BGE 完整协议通过；2026-09-06 在 `platform/.venv311` 的 CPython 3.11.9 精确冻结依赖环境中
  复跑 Markdown/TXT/PDF/PPTX/DOCX 各 100 个运行时 fixture × 20 次，五格式全 PASS、五类失败计数均为 0，
  `external_source_reads=0`、`tmp_only=true`，报告只写系统临时目录且不入库。correctness 收口后 `tests/M7/`
  收集 270 项；Python 3.13.3 的三个 TXT failure 是精确 `cpython-textio==3.11.9` 合同的预期 fail-closed；CPython 3.11.9
  根级复验为 825 passed、1 skipped。公共 Search/QA 请求体不接受 caller-selected `principal_id`，可信 principal 仅作为
  内部服务边界；用户源读后 operation-lock 复核是有界进程内保护，不是跨进程 read lease。Network 文档晋升、P0 语料
  闭环、任何 corpus 自动批准、M8 专业存储和 Milvus 后端选择仍在批准范围外。
- ⬜ **M8 专业化存储**：准备计划见
  [`m8-specialized-storage-plan.md`](plans/m8-specialized-storage-plan.md)；`M8-M7-EXIT` 已满足，但 M8 自身决策与批准仍未闭合。
  Milvus、LanceDB、Qdrant 均未选定或获批，不能在依赖、迁移、parity、fallback 和选择阈值闭合前成为默认。
- ⬜ **M9 目标驱动计划**：准备计划见
  [`m9-goal-driven-planning-plan.md`](plans/m9-goal-driven-planning-plan.md)；planner/mastery schema、唯一写入权威、
  偏差重规划、外部 AI 隐私/fallback 和评测阈值未闭合前保持阻断。
- ⬜ **M10 完整自主 Runner 与 Harness 对外**：准备计划见
  [`m10-autonomous-runner-plan.md`](plans/m10-autonomous-runner-plan.md)；在 M7–M9 退出后仍须先闭合写授权、
  checkpoint、幂等、EffectLedger、恢复、Agent 评测、manifest、MCP 和 rollout。状态机继续作为正式默认和
  无 LLM 降级路径。

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

一句话 + 5 个设计决策 + 学习状态机工具链 + 能力边界：正式路径是状态机；M6b 是已完成收口且默认关闭的
只读 native tool-call preview；完整自主 Runner 在 M10 且不替换教学法。招聘对照原文不是执行计划。

---

*创建：2026-08-10 · PLAN 文档修订：v2.15（不是产品发布版本）· 更新：2026-09-06（M7 在独立人工批准后为
`ADMITTED / COMPLETE`；M8/M9/M10 的事实型 M7 退出前置已满足，但 Network/M8/Milvus/M9/M10 均未获批）·
维护：每次会话开工查看本文档*
