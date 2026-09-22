# 项目计划 · StudyAssistanceAgent

> 通用学习 Agent 的 harness 框架。M0–M5 是最小实现（默认计算机知识包 + 学习闭环）。
> **双目标**：① 按用户目标把任意知识源学完（产品价值）；② 可讲清 Agent harness / RAG / 计划执行（工程价值）。
> 状态图例：⬜ 未开始 ｜ 🔄 进行中 ｜ ✅ 完成
> **当前阶段**：M6a、M6b、M7 均为 `ADMITTED / COMPLETE`；M7 基础设施范围已获批，生产开工门禁为
> `AUTHORIZED`，并于 2026-09-06 在独立人工完成批准后成为 `ADMITTED / COMPLETE`；M9 于 2026-09-20 在
> `m9-plan-lifecycle-v1` 范围内获批为 `ADMITTED / IN_PROGRESS`，并于 2026-09-21 由 owner 以 plan_revision v1.3
> **显式扩张**该范围（新增 `m9.bounded-grounding-retrieval` 与 `m9.plan-identity-fidelity`；扩张不触发 §4 撤销，
> 理由见 M9 计划 §4.1），再以 plan_revision v1.4 **窄口径扩张**至步骤 6（新增 `m9.external-ai`：默认关闭的
> 可选外部 AI 路径 + 冻结任务集 1K 比较；`M9-EVALUATION` 原值不动、延迟/成本仍暂缓，10K/100K 逐字记为
> M8/M11 依赖，理由见 M9 计划 §4.2），再以 plan_revision v1.5 **解冻 `M9-EVALUATION` 的延迟/成本维度**
> 为冻结评测（范围**仅限 M9 外部 AI 路径**：CI 侧冻结预算执行、真实 provider 读数走显式 opt-in 且非门禁；
> 该变更**触发 §4 撤销过渡**，与 v1.3/v1.4 相反，理由见 M9 计划 §4.3）；M9 已于 **2026-09-22 在
> `m9-plan-lifecycle-v1` 范围内获批 `COMPLETE`**（§4 要求的独立 `completion_approval` 见 M9 计划 §4.5；
> 三条 caveat——冻结范围仅限 M9 外部 AI 路径、真实 provider 仍未验证、10K/100K 属 M8/M11——随收口
> **一并接受而非解除**）；M8 与 M10–M12 自身仍为
> `BLOCKED / NOT_STARTED`；M8 active execution protocol `draft-0.10`
> 曾完成 P0/P1/P2 并到达 `BINDING_FROZEN`，但 2026-09-14 独立 P3 文本审计因三项阻断性
> schema/治理闭合缺陷判定 `REJECTED / stop`（`FAILED / RETURNED`）。不得 `request-p4`，且未授权或执行任何
> experiment root 创建、依赖获取、输入准备、benchmark、发布、后端选择或 M8 admission。
> 2026-08-31 P0 治理冻结复测已完成：默认 OS/DS/CO 90 题保持可信默认包政策，Network candidate 不进入默认索引；
> M7 基础设施准入不关闭 Network P0，也不批准任何 Network 文档。
> 里程碑、准入与退出方向以**本文**为准。
> **准入门禁**：[`docs/standards/stage-admission-gates.md`](standards/stage-admission-gates.md)；机器登记见
> [`stage-admission-gates.json`](standards/stage-admission-gates.json)。计划或登记表单独变更均不能批准阶段。
> `docs/plans/references/` 存放辅助分析与限定范围的历史治理记录；它们不具阶段权威，不能产生新授权。
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
| 存储 | 当前学习状态与向量持久化均为 SQLite；M8 将评估 LanceDB/Qdrant 等候选，尚未选择 | 当前向量仍为线性余弦；协议可替换且默认离线可跑 |
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
> 2026-08-20 起产品定位升级为通用学习 Agent harness，后续阶段见 M6–M12。
- ✅ M5a：统一三课 90 题离线评测入口，支持汇总指标和 JSON 报告（2026-08-18 历史基线：OS 1.000、DS 0.929、CO 1.000）。
- ✅ M5b：实现服务端学习会话状态机，编排 QA、Quiz、答案评估和 Review-log（`POST/GET /api/v1/study-sessions`）。
- ✅ M5c：使用 SQLite 持久化会话、答题记录、掌握度和复习历史（`platform/.cache/learning_state.sqlite3`，兼容读取 `review_history.json`）。
- ✅ M5d：提供最小学习工作台，完成讲解、作答、反馈和复习记录交互（`GET /`）。
- ✅ M5e：增加离线 CI、一键启动、模型缓存说明和演示基线。
- **Level 1 退出条件**：一条命令完成 90 题离线评测；一个 API 会话完成“检索→讲解→出题→作答→评估→记录复习”；无 LLM 和向量模型时仍可运行。
- **完整退出条件**：✅ 会话可跨重启恢复；工作台可完成学习闭环；离线 CI 与一键启动已落地；阶段测试、回归和平台测试保持通过。
- **收口结论**：M5 作为 MVP 关闭。默认学习闭环与离线交付不再回退；通用运行时与可插拔数据源改由 M6 起按路线图建设。

### M6–M12：通用学习 Agent Harness 与规模化落地（M6a/M6b/M7/M9 已完成，M8 与 M10–M12 仍阻断）
> **最终依据**：本节（M6–M12）。辅助分析见 `docs/plans/references/`，冲突时以本文为准。
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
| M8 | `BLOCKED` | `NOT_STARTED` | [计划](plans/m8-specialized-storage-plan.md) | 八项 Decision 已 `RESOLVED`；`draft-0.10` P3 拒绝链冻结；`draft-0.11` 独立 P3 已 `REJECTED / stop`，失败链冻结；执行、后端选择和 admission 未授权；100K 专业化存储容量验证暂缓，现有 SQLite 线性余弦 + BM25 满足当前个人规模 |
| M9 | `ADMITTED` | `COMPLETE` | [`m9-goal-driven-planning-plan.md`](plans/m9-goal-driven-planning-plan.md) | `M9-M7-EXIT`、`M9-M8-EXIT`（维持当前 SQLite/BM25 后端）均已 `SATISFIED`；八项强制决策全部 `RESOLVED`；justtodo123 于 2026-09-20 在 `m9-plan-lifecycle-v1` 范围内批准开工（生成 + 采纳 + 进度 + 偏差重规划；v1.1 时外部 AI 与 mastery 写入除外）。确定性 Planner、计划生命周期与跳过/逾期偏差信号已实现；`M9-EXECUTION-DEVIATION` 决策值在 v1.2 实质变更，撤销与重新准入过渡已登记在 `admission_history`；步骤 3 的三个只读投影（mastery、授权 Source 摘要、先修关系 topic graph）均已实现并接入确定性 Planner（计划身份含派生输入摘要；先修违反由 `summary.prerequisites.violations` 可测，真语料实测为 0）；2026-09-21 owner 以 v1.3 扩张范围至步骤 4（拆为 4a/4b），4a 受限检索接缝（`PlanGroundingService`，四类预算 + fail-closed 交叉校验）与 4b 计划身份往返保真（principal 进身份键与记录 payload、经单点 `_public_plan` 剥离后不进响应体）均已完成；步骤 4c 修复了步骤 3 记录的复习历史冻结快照残留（`main.py` 改注入只读活投影）；步骤 4d 关闭了 §4 记录的准入留痕覆盖缺口（`_registry_references` 现同时枚举 `admission_history[].reference`，纯治理测试硬化）；2026-09-21 owner 再以 v1.4 窄口径扩张至步骤 6，`m9.external-ai` 移入 `included`（排除项只剩 mastery 写入），实现默认关闭的可选外部 AI 路径与冻结任务集 1K 比较；**`M9-EVALUATION` 原值未动**（延迟/成本仍 `DEFERRED`），10K/100K 容量验证逐字记为 M8（`BLOCKED`）/ M11 依赖、本次不触碰，故步骤 6 仅为**窄口径**推进、评测 workload 整体仍未冻结；该窄口径**已实施完成**（adapter 默认关闭 + 冻结任务集 1K 比较，读数见下方步骤 6 段）；2026-09-21 另交付 M9 **退出条件证据**——`tests/M9/test_mastery_write_authority.py` 以动态源文件枚举钉住「正式 mastery 只有一个写入权威」（写 `study_sessions`/`answer_attempts` 者恰好是 `learning_store.py`，M9 的 8 个模块与写权威导入不可达）；该增量**不新增写路径**（`m9.mastery-write` 仍在 `excluded`）、不改 `plan_revision`、不写 `admission_history`；2026-09-22 owner 再以 plan_revision v1.5 **解冻 `M9-EVALUATION` 的延迟/成本维度**为冻结评测（`ADMITTED→REVOKED→ADMITTED` 过渡已登记在 `admission_history`，`M9-EVALUATION` 为 M9 首个**真正触发** §4 的变更），冻结口径**仅限 M9 外部 AI 路径**：CI 臂在 `tests/M9/test_plan_ai_benchmark.py` 以确定性 stub 驱动真实 `client_factory=` 接缝，冻结**预算被强制执行**（`-m m9_benchmark`）；真实 provider 读数走 `tests/M9/test_plan_ai_provider_smoke.py`（`online` + skip 门控、**非门禁、本次未运行**）。故 M9 七项退出条件**在各自声明的范围内**均已挣得；**2026-09-22 owner 在 `m9-plan-lifecycle-v1` 范围内批准 `M9 COMPLETE`**（§4 要求的独立 `completion_approval`，五项字段齐全，见 M9 计划 §4.5），登记表 `delivery_status` 改为 `COMPLETE`、下游 `M10-M9-EXIT` 随之由 `OPEN` 改为 `SATISFIED`（**只登记事实，不构成 M10 的准入批准**）。**三条 caveat 随收口一并接受、未解除**：① 冻结评测范围仅限 M9 外部 AI 路径（**不是**全项目评测，遵循度仍为定性）；② 真实 provider 的延迟/成本/失败模式**仍未验证**（arm B 未运行，且被刻意排除在门禁判据之外）；③ 10K/100K 属 M8（`BLOCKED`）/ M11（拟议）。收口时另登记一条**已知限制**（不阻塞收口）：外部 AI 路径的 `PlanAIRequest` **不含先修关系**，而 `goal_planner._ai_order` 拿先修违反数作闸门丢弃整个置换——即模型被要求满足一个从不告诉它的约束；2026-09-22 一次**第三方 provider 探针**（**非 arm B、非 M9 证据、不进门禁**，产物在 gitignored 的 `artifacts/`）实测披露先修边可把采纳率由 `5/10` 提到 `8/10`（仅改措辞无效，`4/10`）。修复它需动 `M9-EXTERNAL-AI` 的 `MINIMAL_DISCLOSURE` 披露范围，**本次不动**，留作后续阶段输入 |
| M10 | `ADMITTED` | `IN_PROGRESS` | [`m10-autonomous-runner-plan.md`](plans/m10-autonomous-runner-plan.md) | **2026-09-22 获批准入并授权开工**（范围 `m10-autonomous-runner-v1`，plan_revision v1.0，批准引用逐字为「允许执行」；`implementation_start` 同步 `AUTHORIZED`）。三项前置 `M10-M7-EXIT` / `M10-M8-EXIT` / `M10-M9-EXIT` 自 2026-09-22 起**均已 `SATISFIED`**——其中 `M10-M8-EXIT` 以 owner 当日批准的**维持现状结论**兑现（数据面维持 SQLite/BM25，100K 专业化存储容量验证保持待命参考，见 M10 计划 §2.1），**不是容量证据**；阻断项只剩十一项强制决策与 owner 的独立准入批准。**十一项已于 2026-09-22 全部由 owner 批准 `RESOLVED`**（闭合批次 ① `M10-AUTHORITY` + `M10-WRITE-AUTHORIZATION`，批次 ②③ 九项，见 [`m10-decision-closure-v1.md`](plans/references/m10-decision-closure-v1.md)）。准入检查表中「十一项决策」「MCP/manifest 边界」「三份文档一致」已勾选；**仍差两项可执行的落盘物**——写副作用 crash-point/越权/重放的**测试方案**、以及**冻结的 Agent 评测任务集**（决策层已指定矩阵与阈值，方案与任务集尚未写成文件，不需新的 owner 裁定）——以及 owner 的独立准入批准。**准入检查表六项已于 2026-09-22 全部勾选**（第 3、4 项由 [`m10-test-plan-v1.md`](plans/references/m10-decision-closure-v1.md) 关闭），随后获批准入。**实施进度：§5 步骤 1 已完成**——新增 `platform/app/runner_authority.py`（写 allowlist 与只读 preview **不相交**、确认令牌绑定、撤销、追加式审计只留摘要）与 `platform/app/effect_ledger.py`（**独立** SQLite 文件、版本化 meta、**`pending` 先于领域写入**、幂等重放），`RUNNER_WRITE_TOOL_ALLOWLIST` **冻结为空**且两模块**未接入 `main.py`**；证据见 `tests/M10/`（34 项，`m10` 标记）。其余六步未开始 |
| M11 | `BLOCKED` | `NOT_STARTED` | [`m11-data-scaling-plan.md`](plans/m11-data-scaling-plan.md) | 拟议真实数据规模化阶段；正式退出目标为 10K approved chunks，3K 为先行 Gate，全部 Decision 与批准 `OPEN` |
| M12 | `BLOCKED` | `NOT_STARTED` | [`m12-cloud-deployment-plan.md`](plans/m12-cloud-deployment-plan.md) | 拟议可选云端单用户部署；本地离线仍为默认，服务器 baseline、十三项 Decision 与批准全部 `OPEN` |

阶段只有在所有强制 Decision 为 `RESOLVED`、前置/保护证据有效、兼容不变量确认且用户或项目负责人填写批准
记录后，才能由本文同步改为 `ADMITTED`。批准范围只能缩小边界，不能批准被排除的数据或下游阶段；若登记独立
生产开工门禁，只有 `AUTHORIZED` 后交付才能进入 `IN_PROGRESS`。Agent 不得自行批准准入或开工。前提失效时
改为 `REVOKED` 并停止生产实施。

**依赖顺序**：M6b 与 M7 都只依赖 M6a 退出证据，彼此不互为前置。M7 已完成 Source Registry、
source-local FULL/INCREMENTAL/delete/isolation、FTS5/vector/offline fail-closed、Search/QA overlay 与冻结技术验收，
并于 2026-09-06 取得独立完成批准。因此 M8/M9/M10 的事实型 M7 退出前置均为 `SATISFIED`；这不批准任何下游阶段。
M8 的八项政策 Decision 已闭合，但仍须完成新实证协议、后端选择和人工 admission；M9 的 M8 退出前置已通过
「维持当前 SQLite/BM25 后端」分支满足（100K 专业化存储容量验证暂缓），但 M9 不因此获得 M8 的 100K 数据面
或执行授权；M10 的 `M10-M8-EXIT` 于 2026-09-22 由 owner 以**同一条维持现状结论**分支兑现（见 M10 计划 §2.1），
`M10-M7-EXIT` 与 `M10-M9-EXIT` 此前已 `SATISFIED`，故 M10 三项前置**均已满足**——这**不构成 M10 的准入批准**，
M10 仍为 `BLOCKED / NOT_STARTED`，等待自身十一项强制决策与独立批准；M11 拟依赖 M8–M10 的真实退出并交付
10K approved chunks（**注意**：M8 走维持现状分支后不会产生「真实退出证据」，M11 的 `M8/M9/M10 真实退出证据`
一条需在 M11 准入前重新澄清）；M12 拟依赖
M8–M11 并交付可选云端单用户 profile。所有阶段都不以 M6b 为写路径或 Source 生命周期前置。

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
  收集 277 项（2026-09-22 收口后缺陷修正新增 `test_parser_timeout.py` 7 项，见 §五 v2.38）；Python 3.13.3 执行
  274 passed / 3 failed，三个 TXT failure 是精确 `cpython-textio==3.11.9` 合同的预期 fail-closed；CPython 3.11.9
  根级复验为 825 passed、1 skipped。公共 Search/QA 请求体不接受 caller-selected `principal_id`，可信 principal 仅作为
  内部服务边界；用户源读后 operation-lock 复核是有界进程内保护，不是跨进程 read lease。Network 文档晋升、P0 语料
  闭环、任何 corpus 自动批准、M8 专业存储和 Milvus 后端选择仍在批准范围外。
- ⬜ **M8 专业化存储**：准备计划见
  [`m8-specialized-storage-plan.md`](plans/m8-specialized-storage-plan.md)；`M8-M7-EXIT` 已满足，负责人及独立批准人
  `justtodo123` 于 2026-09-10 对八项 Decision 逐项明确批准并全部 `RESOLVED`；该批准不等于阶段 admission。V8 执行根已 `INVALID`，V9 已 `PRE_FREEZE_STATIC_AUDIT_FAILED`，V10 已
  `PRE_SOURCE_GOVERNANCE_INVALID`，V11 已 `PRE_SOURCE_PROVENANCE_INVALID`；四者的 experiment/protocol
  身份、根、source 与 artifact 均不得修复、恢复、补审、重跑或复用。V12 已取得仅限阶段 1 的书面授权，完成全新
  随机根、九文件初始 allowlist、marker 即时字节验证、六个 source 重写、source freeze、manifest 与 inventory，
  但独立静态审计于 `2026-09-09T12:12:34Z` 判定 `FAIL`；V12 以 `INDEPENDENT_STATIC_AUDIT_FAILED` 永久封口且
  不可复用，从未进入 preflight 或执行阶段。任何后继实验须由负责人另行书面授权并从全新身份开始。当前 M8 已
  冻结为 local-first 可扩展检索数据面：SQLite/M7 是控制面权威，SQLite linear 是 oracle/fallback，LanceDB 为
  10K–100K 单机第一评估候选，Qdrant 仅为云端/服务化条件候选，Milvus 当前不采用；尚未选择或批准任何专业后端。
  `100K` 只表示 synthetic/半合成容量与生命周期证据，不表示 100K 真实语料。V13 的历史协议文本审计曾在
  2026-09-10 修订后得到 `PASS_AFTER_REVISION / DRAFT_NOT_AUTHORIZED`；该结果只评价当时的文本设计，从未产生
  repository binding、建根、source freeze、独立静态审计 PASS 或执行授权。八项批准记录见
  [`m8-decision-closure-v1.md`](plans/references/m8-decision-closure-v1.md)，范围决策见
  [`m8-m12-scope-decision-v1.md`](plans/references/m8-m12-scope-decision-v1.md)。V13 已因不适配新 100K 目标处置为
  [`SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`](plans/references/m8-v13-disposition-20260910.md)，不得
  填充占位符、binding、修订、建根、授权、执行或复用；后续实证须使用全新协议身份，重新冻结
  `1K correctness / 10K single-user / 100K capacity+filter`，并按 `S → A → G → E` 分离书面授权。
  2026-09-12 负责人已通过独立
  [`draft-0.4` 修订授权记录](plans/references/m8-active-execution-protocol-draft-0.4-authorization-20260912.md)
  主动发起 active execution protocol `draft-0.4`，仅允许定点修订 `draft-0.3` P0 退回的 12 项技术闭合缺陷。
  该版本已于同日经未参与起草的 independent reviewer 完成 P0 技术审查，并以 3 项新增 schema/状态/证据闭合
  缺陷退回；审查记录见
  [`m8-active-execution-protocol-draft-0.4-review-20260912.md`](plans/references/m8-active-execution-protocol-draft-0.4-review-20260912.md)。
  负责人随后另行发起定点修订 `draft-0.5`（授权记录见
  [`m8-active-execution-protocol-draft-0.5-authorization-20260912.md`](plans/references/m8-active-execution-protocol-draft-0.5-authorization-20260912.md)），
  仅处理该 3 项阻断缺陷；2026-09-13 经未参与起草的 independent reviewer 完成 P0 技术审查，取得
  [`PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`](plans/references/m8-active-execution-protocol-draft-0.5-review-20260913.md)：
  4 项缺陷全部机械闭合，72 行映射表逐字节未变，未引入新的阻断缺陷。该接受只表示当时的技术文字被接受；
  `draft-0.5` 历史对象保持
  `UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`，本次修订未创建 experiment/protocol 执行身份或 binding，也未授权
  建根、依赖、输入生成、preflight、benchmark、证据发布、M8 admission 或任何 backend selection，更不自动产生
  `draft-0.6`。后续 `draft-0.10` 虽另行完成 P0/P1/P2 并冻结 repository binding，但 2026-09-14 的
  [独立 P3 文本审计](plans/references/m8-draft010-p3-independent-text-audit-20260914.md)发现 gate-specific role/独立性、
  P8 `admission_scope` 与 P3 `text_audit_ref` artifact schema 三项阻断缺陷，结论为
  `REJECTED / stop`（`FAILED / RETURNED`）。该链不得 `request-p4`；未创建 machine P3 gate，且未授权建根、
  依赖获取、输入准备、preflight、benchmark、证据发布、后端选择或 M8 admission。若修订协议，须形成新的
  协议版本并重新完成 P0/P1/P2，不得就地改写冻结对象。Successor `draft-0.11` 已由独立 reviewer `justtodo123`
  完成 P0 技术文字接受，并由 owner `justtodo123` 完成 P1/P2；全新 identity、parent-binding 与 repository-binding 已
  冻结；独立 reviewer `external-reviewer-01` 已判定 draft-0.11 P3 `REJECTED / stop`，记录 14 项阻断 finding；
  未授权建根、依赖、输入、执行、发布、后端选择或 M8 admission。
- 🔄 **M9 目标驱动计划**：执行计划见
  [`m9-goal-driven-planning-plan.md`](plans/m9-goal-driven-planning-plan.md)；八项强制决策已 `RESOLVED` 并在
  `m9-plan-lifecycle-v1` 范围内获批开工，确定性生成、采纳/进度/重规划与跳过+逾期偏差信号已实现。
  外部 AI 隐私/fallback 已由 v1.4 的窄口径兑现（默认关闭、最小披露、硬超时+成本预算、确定性 fallback）；
  评测 workload 整体仍未冻结，不得据此扩大 rollout。步骤 3 已完成——三个只读投影（mastery、
  授权 Source 摘要、先修关系 topic graph）均已实现并接入确定性 Planner（聚合身份为知识条目 file 路径；
  计划身份含派生输入摘要）。先修关系由 60 条课程条目的 frontmatter `prerequisites:` 声明，Planner 以
  Kahn 拓扑排序产出先修合法顺序，`summary.prerequisites.violations` 直接度量退出判据「先修违反=0」
  （真语料实测 0）；`unorderable()` 是图级环诊断，刻意不进计划 `summary`。
  步骤 4 已由 owner 于 2026-09-21 以 plan_revision v1.3 显式扩张授权（新增
  `m9.bounded-grounding-retrieval` 与 `m9.plan-identity-fidelity`），拆为 4a/4b。
  **4a 已完成**：`platform/app/plan_grounding.py` 的只读 `PlanGroundingService` 复用
  `MultiRecallService.recall` 而非新建检索实现，冻结四类预算（top_k / 证据字节 / 用户源数 / 超时，
  只能收紧）并加一道独立 fail-closed 交叉校验——不在可用集合内的 `user://` 来源一律丢弃，
  未注入投影 / 无 principal / 控制面异常三种不确定都收敛到空集。**关键定性**：M7 早已在检索路径
  端到端拒绝 stale/deleted 源，缺的不是实现而是 Planner 从未接上检索路径，故
  `STALE_DELETED_SOURCE_ENTRY_ZERO` 此前无端到端证据；4a 补的正是这条接缝与它的证据。
  grounding 刻意**不进** `plan_id`、也**不进** `summary`（前者会让 reindex churn 计划身份，后者会破坏
  「同一 `plan_id` ⇒ 相同 `summary`」）。**未新增任何公开路由**，`PUBLIC_API_PATHS` 未改动；
  能力装配于 `main.py` 但**生产休眠**（principal 按设计是内部边界，无路由传它），
  故该判据在**服务层接缝**上证明，不是公共 API 上的端到端隔离。
  **4b 已完成**：修掉步骤 3 记录的两处已证实缺陷——① `_plan_id` 身份键不含 principal，而 `event_id`
  是 `(plan_id, task_id, event)` 的哈希、同样不含 principal 成分，两个 principal 生成同一 Goal 会撞同一
  `plan_id`，后者的 `completed` 被 `INSERT OR IGNORE` 静默去重、把前者的任务标成完成；②
  `_response_to_record` 无 `summary` 键、`_plan_to_request` 只还原 5 个请求字段，principal 进入计划路径后
  `replan` 会以「无 principal」重新生成、源范围静默改变。身份键追加**带标签**的 principal 段且**仅在非
  None 时**追加，故 `principal_id=None` 的身份与接入前逐字节相同、既有计划 id 不 churn；principal 是
  **内部记录键**，经单点 `_public_plan` 在所有读取路径上剥离，不进任何 HTTP 响应体（`GoalPlanRequest` /
  `GoalPlanResponse` 均无该字段，故也不进 OpenAPI schema）。**仍未新增任何公开路由**，`PUBLIC_API_PATHS`
  与路由 docstring 未改动；**未 bump `SCHEMA_VERSION`**（payload 是 JSON blob，无 DDL）。
  迁移语义：非 None principal 下的旧 id 不再匹配新生成结果，旧记录仍可 `GET`/`adopt`/`progress`/`replan`
  （主键查找，读时不重算），不回填、不改写。**评测 workload 冻结（步骤 6 的整体口径）仍在范围外**；
  外部 AI 已由 v1.4 窄口径纳入，见下方步骤 6。
  **4c 已完成**（步骤 3 已记录残留的修复，**非**范围扩张——批准字段与 `admission_history` 均未改动）：
  `main.py` 原先传 `review_history=_learning_store.all_reviews()`，那是构造时求值一次的快照，于是同一进程内
  新记录的复习永不反映到计划上（`reviewed` 标志、排序优先级，以及经 `_derived_digest` 参与 `plan_id` 的
  身份全部停在进程启动时刻），而紧邻的 mastery 投影刻意传活对象，两条同源只读输入一个冻结一个实时。
  新增 `ReviewHistoryProjection`（只返回成员资格，形状对齐既有三个只读投影）并注入活对象；未注入时回落到
  构造时的快照，既有调用方行为逐字节不变。**迁移语义**：进程内新记录的复习现在会改变 `plan_id`（此前该承诺
  在 mastery 侧成立、在复习侧不成立），旧 id 仍可 `GET`/`adopt`/`progress`/`replan`，不回填、不改写；
  未新增公开路由，未 bump `SCHEMA_VERSION`。
  **4d 已完成**（关闭 §4 已记录缺口，纯治理测试硬化、**非**能力）：`admission_history[].reference` 此前未纳入
  `tests/regression/test_governance_contract.py` 的 `_registry_references` 白名单枚举，`stage-admission-gates.md`
  §7 明文要求的「必须是仓库内可移植路径」只靠人工约束。现折进同一白名单（复用既有校验器，不另写一套），并补
  `test_admission_history_records_are_well_formed`：先断言 `records` 非空（否则新增的那段 yield 空转，而 allowlist
  用例仍全绿），再逐条断言键集恰为 §7 五键、`from`/`to` 属 `{BLOCKED, ADMITTED, REVOKED}` 且不相等。
  变异验证：把 `reference` 换成宿主绝对路径 → allowlist 用例恰好 1 项失败；删掉整个 `admission_history` →
  allowlist 用例仍全绿、只有键集用例变红。未新增能力 / 路由 / 字段，未改批准字段与 `admission_history` 内容。
  **步骤 6 窄口径已由 owner 以 plan_revision v1.4 批准**（2026-09-21）：owner 原指令要求推进到步骤 6 的完整口径
  （含 1K/10K/100K 容量验证），但该口径**不可准入**——10K/100K 会撞 M6a 合并硬上限 2,000 chunks 且 §5 禁止
  提高限制，该分级本身是 M8 的强制决策 `M8-BENCHMARK`（M8 `BLOCKED / NOT_STARTED`、`approval_scope: null`），
  10K 真实数据属拟议 M11；原指令还要求验证延迟与成本，而 `M9-EVALUATION` 的 `RESOLVED` 值以
  `..._LATENCY_COST_DEFERRED` 结尾，解冻会构成实质变更并强制 `REVOKED`。owner 遂裁定取**窄口径**：
  `m9.external-ai` 移入 `included`（`excluded` 只剩 `m9.mastery-write`），冻结任务集上比较确定性与 AI 路径，
  容量只在 1K 跑，**`M9-EVALUATION` 原值不动**，故不触发 §4 撤销、一次批准即可实施。理由与「本次明确不做」
  清单见 M9 计划 §4.2；实现进度见该计划 §5.1。
  **该窄口径已实施完成**（`platform/app/plan_ai_adapter.py` 默认关闭；`tests/M9/test_plan_ai_adapter.py` 59 项、
  `tests/M9/test_plan_ai_benchmark.py` 3 项，后者标记 `m9_benchmark` 并作为独立 CI 步骤运行）。冻结任务集
  比较的读数是：两种语料规模（实测 10 vs 1000 chunks）下送往 AI 的 prompt 字节数与条目数**逐字相同**
  （输入有界），两条路径先修违反均为 0，确定性可重放。**必须按窄口径读**：这只证明**输入不随语料规模增长**，
  M9 既不存储也不索引 1K chunks，故**不是容量声明**；AI 路径在 CI 由确定性 stub 驱动，真实 provider 的
  延迟/成本/失败模式**未验证**；10K/100K 仍是 M8（`BLOCKED`）/ M11（拟议）依赖。
  **评测口径已由 owner 以 plan_revision v1.5 解冻**（2026-09-22）：`M9-EVALUATION` 的延迟/成本维度由
  `..._LATENCY_COST_DEFERRED` 改为冻结评测，**这是 M9 第一个真正触发 §4 撤销的变更**（v1.3/v1.4 都在论证
  「为何不触发」；§4.2 末段早已逐字预言本次），过渡已登记在 `admission_history`，v1.5 当时 live 字段仍为
  `ADMITTED / IN_PROGRESS`（**2026-09-22 收口后 `delivery_status` 已改为 `COMPLETE`**，见下方 v2.35）。
  冻结口径**仅限 M9 外部 AI 路径**，分两臂：**CI 臂（门禁）**在
  `tests/M9/test_plan_ai_benchmark.py` 以冻结预算矩阵驱动**真实** `build_anthropic_proposer(client_factory=…)`
  接缝，逐场景断言稳定原因码——`prompt` 预算在调用 provider **之前**返回（provider 调用数为 0）、`cost`
  预算在收到**合法**置换时仍丢弃它（硬上限而非告警阈值）、`deadline` 由 `_run_blocking` 强制；**必须按窄口径读**：
  stub 下延迟是桥接开销、成本由脚本化 usage 算出，故 CI 臂证明的是**预算被强制执行**，**不是**性能；
  `max_input_tokens` / `model_timeout_seconds` **不在本地执行**（报告里有机器可读的 `enforced_locally` /
  `not_enforced_locally`）；`max_output_tokens` 当时也列在 `not_enforced_locally` 里，但它**既非 provider 侧
  也非本地执行**——累积值**没有运行期执行点**（2026-09-22 的缺陷修正后更正，见 v2.34），`deadline` 守卫
  **放弃线程而非取消它**。**真实 provider 臂
  （非门禁）**见 `tests/M9/test_plan_ai_provider_smoke.py`（`online` + skip 门控、花费上限默认 $1.00、
  只记脱敏字段），**本次未运行**，故真实 provider 的延迟 / 成本 / 失败模式**仍未验证**。10K/100K 仍不触碰。
- ⬜ **M10 完整自主 Runner 与 Harness 对外**：准备计划见
  [`m10-autonomous-runner-plan.md`](plans/m10-autonomous-runner-plan.md)；在 M7–M9 退出后仍须先闭合写授权、
  checkpoint、幂等、EffectLedger、恢复、Agent 评测、manifest、MCP 和 rollout。状态机继续作为正式默认和
  无 LLM 降级路径；10K/100K ingestion、embedding 和 reindex 长任务必须异步、可取消、可恢复且不产生半发布 generation。
- ⬜ **M11 真实数据规模化**：准备计划见
  [`m11-data-scaling-plan.md`](plans/m11-data-scaling-plan.md)；正式退出目标为 10K 个许可清晰、来源可追溯、质量可验证的
  approved chunks。3K 为先行 Gate；30K/100K 为后续扩展 Gate，不阻塞 M11 完成。100K synthetic capacity 不能冒充
  真实数据质量证据。
- ⬜ **M12 可选云端单用户部署**：准备计划见
  [`m12-cloud-deployment-plan.md`](plans/m12-cloud-deployment-plan.md)；本地离线 profile 永久保留且仍是默认。云端仅为
  显式 opt-in 单用户部署，须闭合服务器、安全、身份、备份、成本、数据驻留和 rollback Decision；多租户和百万级不在范围。

**总退出方向**：用户能自定义知识源，在 1K/10K/100K 分层容量下按目标学习并看到计划执行情况；M11 交付 10K
高质量真实数据，M12 提供可选云端单用户部署；无外部 AI、无云端和无专业依赖时仍可运行。M6b 只验证隔离的只读工具调用，完整自主 Runner 到 M10 才作为与教学状态机正交的可选执行器落地。

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

*创建：2026-08-10 · PLAN 文档修订：v2.41（不是产品发布版本）· 更新：2026-09-22（**M10 实施步骤 1 完成**：
冻结 authority / capability / EffectLedger schema，**先实现拒绝路径**。新增两个生产模块——
`platform/app/runner_authority.py`（写 allowlist **与只读 preview allowlist 不相交**、注册期与执行期双重拒绝、
确认令牌绑定 `(job_id, tool_name, 参数摘要)`、撤销使未决授权失效、追加式审计**只留参数摘要**、六态跃迁合法性、
幂等键派生）与 `platform/app/effect_ledger.py`（**独立** SQLite 文件 + 版本化 `runner_meta`、
`runner_jobs` / `effect_ledger` / `effect_events` / `job_checkpoints`、**`pending` 先于领域写入**以闭合
「已 apply 无台账行」的崩溃窗口、同键重放返回已记录 effect、同键不同参数判冲突）。`RUNNER_WRITE_TOOL_ALLOWLIST`
**冻结为空**（生产上什么都注册不了），且两模块**未接入 `main.py`**——无路由、无开关、无后台 worker，
故「默认关闭是恒等操作」在**结构上**成立而非靠约定。新增 `tests/M10/`（34 项，`m10` 标记已登记进 `pytest.ini`），
全量 1282 → 1316 collected、1277 → 1311 passed、2 skipped、3 failed（3 项仍为 M7 TXT parser 按设计 fail closed）。
**本次实施中修正了三处我自己写错的东西**：① 测试方案 §6 原写「Runner 侧模块不 import `sqlite3`」——在独立库
裁定下**不成立**（台账必然自建库），已改为「不 import 领域仓储、不引用其写方法」；② 首版边界守卫用**裸子串**
判「写领域表」，被 `main.py` 的 `_study_sessions` 属性名与 `mastery_projection.py` 文档字符串**两次误伤**，
已改用与 `tests/M9/` 同形的**写语句正则**；③ 删掉两处**不可达**的守卫并改为**钉住上游契约**——不可达的守卫
比没有守卫更糟，它读起来像在执行。变异验证：去掉撤销检查 / 令牌参数不匹配 / allowlist 不相交 / 幂等重放，
各自恰好判红对应用例）· 上一修订 v2.40（2026-09-22：**M10 获批准入并授权开工**：
owner 逐字指令「允许执行」，回应「下一步：M10 准入 + 开工批准」。登记表 `admission_status` 由 `BLOCKED` 改为
`ADMITTED`、`delivery_status` 由 `NOT_STARTED` 改为 `IN_PROGRESS`，新增 §4 五项批准字段（`plan_revision`
v1.0、`decision_set_version` m10-decision-set-v1）与 `approval_scope` `m10-autonomous-runner-v1`
（`included` 11 项与十一项决策一一对应；`excluded` 5 项：M11 数据扩展、M12 云部署、多 worker 拓扑、
M8 后端选择、10K/100K 真实数据），`implementation_start` 同步 `AUTHORIZED`。准入检查表**六项全部勾选**。
**关键限定**：`approval_scope` 只用于缩小边界，**不**把被排除项隐式提升为已批准；**不产生**
`completion_approval`；不改十一项决策值；**不豁免 §6 继承不变量**（状态机仍为正式默认、`StudySessionService`
仍独占领域写入、M6b 仍是隔离只读 preview）。这是 M9 收口以来**第一次进入生产实施**。本次为**治理记录变更**：
未改生产代码、未新增公开路由、未 bump `SCHEMA_VERSION`）· 上一修订 v2.39（2026-09-22：M10 **决策闭合批次 ②③
获批准**：owner 逐字指令「全部批准（推荐）」，`CHECKPOINT` / `IDEMPOTENCY` / `EFFECT-LEDGER` / `RECOVERY` /
`OFFLINE-DEFAULT` / `MANIFEST` / `EVALUATION` / `MCP` / `ROLLOUT` 九项由 `OPEN` 改为 `RESOLVED`。
至此 **M10 十一项强制决策全部 `RESOLVED`**。M10 计划 §3 决策表同步更新（此前批次 ① 漏改的两行由
`test_stage_plans_track_registry_decision_status` 抓出——该护栏即为此新增）。准入检查表中「十一项决策」
「MCP/manifest 边界」「三份文档一致」已勾选，**仍差两项可执行的落盘物**：写副作用 crash-point / 越权 /
重放的**测试方案**与**冻结的 Agent 评测任务集**（决策层已指定 10 点矩阵、0 容忍阈值与两臂分工，但方案与
任务集尚未写成文件；二者**不需要新的 owner 裁定**）。**关键限定**：决策闭合**不构成** M10 准入批准——
`admission_status` 仍 `BLOCKED`、`approval` 五字段仍为空、`implementation_start` 仍为 `null`；不授权开工，
不创建任何生产物件；**不触发 §4 撤销、不写 `admission_history`**（M10 从未准入）。本次为**纯治理记录变更**：
未改生产代码、未新增公开路由、未 bump `SCHEMA_VERSION`）· 上一修订 v2.38（2026-09-22：**M7 收口后缺陷修正——
解析路径墙钟上界**，属生产代码改动：`MAX_FILE_BYTES` / `MAX_PDF_PAGES` 等约束的是解析器**拿到多少输入**，
不是**能跑多久**；内部死循环的解析器既不返回也不抛异常，故解析路径上任何 `except` 对它都是盲的，调用永不返回，
在强制的单 worker 拓扑下会卡死**整个进程**。`parse_document` / `parse_file` 新增 `timeout_seconds`
（默认 `PARSE_TIMEOUT_SECONDS = 30.0`），校验与既有 `max_bytes` 同形（正的有限数且不得超过冻结默认），
超时抛新增稳定码 `SOURCE_PARSE_TIMEOUT`；接缝**格式无关**，五格式统一施加。新增
`tests/M7/test_parser_timeout.py`（7 项，**新文件**，未改任何存量 M7 测试），`tests/M7/` 270 → 277 项、
267 → 274 passed（3 项 TXT 基线失败**未增加**——新测试对不可用格式 skip 而非断言）。
**为何不升级 pypdf pin**：pin 是承重的（`require_parser` 精确匹配、M7 冻结策略串、M8 metadata-discovery 的
`SCOPE_ASSERTIONS` 与 scope builder 从 HEAD 读 `requirements.txt`），且升级只修那两个 DoS 通告、
**不改变「解析没有时间上界」这一缺陷本身**。**为何不触发 M7 §6 撤销**：parser matrix 身份、normalized
document 形状、`document_id` 派生与公开路由逐字未动，正常解析产出逐字节不变。**残留（逐字记录，不得后读时
当作已解决）**：① 线程被**放弃而非取消**（Python 无法强杀线程），泄漏限制为「每次发布尝试至多一个」；
② 进程级隔离是更强的修法，本次不做；③ 默认 30 秒是估计而非实测基线；④ `txt` 在本机不经此路径。
变异验证：超时码改成 `PARSE_FAILED` → 3 项失败；去掉「只能收紧」校验 → 1 项失败；**完全移除上界不会判红而是
让测试挂起**——实施中一次把 mock 打错位置（替换 `_run_bounded` 本身而非解析器）实测整套测试 300 秒不返回）·
上一修订 v2.37（2026-09-22：M10 **决策闭合批次 ①**：
owner 批准 `M10-AUTHORITY` 与 `M10-WRITE-AUTHORIZATION` 由 `OPEN` 改为 `RESOLVED`（批准引用逐字为
「按顺序进行即可」，回应「确认后我把它标为已批准、把登记表两项转 `RESOLVED`，再写批次 ②」；按本仓既有惯例
逐字引用原话并说明解读）。闭合面见新增的 [`m10-decision-closure-v1.md`](plans/references/m10-decision-closure-v1.md)，
其 §1 给出可直接落登记表的 `value` 令牌串与十项必备内容。**关键限定**：这**不批准 M10 准入**（`admission_status`
仍 `BLOCKED`、`approval` 五字段仍为空、尚有九项 `OPEN`）；**不授权开工**（不建写工具、不改 `tool_registry.py`、
不新增路由/开关、不建 `tests/M10/`）；**不创建独立 SQLite 文件或定义其 schema**（属批次 ②）；**不改写 M6b**
已交付并冻结的只读 preview；**不触发 §4 撤销、不写 `admission_history`**（M10 从未准入）。另修一处**事实错误**：
草案曾把 `M10-AUTHORITY` 写成「全仓唯一写者」，核对后 `learning_store.py` 有**四个**写者（`save` / `save_review` /
`save_plan` / `save_progress_event`，由三个服务调用），唯一性只在**领域服务层**成立——该更正已写进闭合记录。
本次为**纯治理记录变更**：未改生产代码、未新增公开路由、未 bump `SCHEMA_VERSION`）· 上一修订 v2.36（2026-09-22：
`M10-M8-EXIT` **维持现状
结论**：owner 在「`M10-M8-EXIT` 怎么处理」的裁定中选择「走维持现状结论分支」——M10 数据面维持当前
SQLite registry + linear cosine + 默认 BM25，100K 专业化存储容量验证保持**待命参考**，不新建协议、不做实验、
不冻结 digest。登记表 `M10-M8-EXIT` 由 `OPEN` 改为 `SATISFIED`，M10 计划新增 §2.1 记录裁定字段、三条依据与
五条「本裁定不做什么」。**关键限定**：这**不构成 M10 的准入批准**（`admission_status` 仍 `BLOCKED`、
`approval` 五字段仍为空，M10 仍需自身十一项强制决策与独立批准）；**不批准 M8 的任何执行**（不选后端、不建
`tests/M8/`、不做 100K 实证，M8 仍 `BLOCKED / NOT_STARTED`，其 §9 剩余准入项不因本裁定减少）；**不产生任何
容量证据**；**不改写 `references/` 下的历史治理记录**。**不触发 §4 撤销、不写 `admission_history`**——§4 的撤销
前提是**已准入阶段**的前提发生实质变化，而 M10 从未准入，不存在可撤销的准入；`admission_history` 的
`from` / `to` 语义是准入状态，本次为 `BLOCKED → BLOCKED`，写入会造成语义错配且会被
`test_admission_history_records_are_well_formed` 的 `from != to` 断言判红。同时**登记一处下游缺口**：M8 走维持
现状分支后**不会**产生「真实退出证据」，故 M11 的 `M8/M9/M10 真实退出证据有效` 一条需在 M11 准入前重新澄清
（已在 M11 计划就地标注）。本次为**纯治理记录变更**：未改任何生产代码、未新增公开路由、未 bump
`SCHEMA_VERSION`）· 上一修订 v2.35（2026-09-22：M9 **收口**：owner 在
`m9-plan-lifecycle-v1` 范围内批准 `M9 COMPLETE`，登记表 `delivery_status` 由 `IN_PROGRESS` 改为 `COMPLETE`
并新增 §4 要求的**独立** `completion_approval`（批准人 / 日期 / 引用 / scope / 证据五字段齐全，
`approval_scope` 与准入批准**逐字相同**、未扩大）。`approval`（v1.5 准入批准）与 `admission_history`
**均未改动**——本次是 `ADMITTED → ADMITTED`，写 `admission_history` 会造成语义错配，且会被
`test_admission_history_records_are_well_formed` 的 `from != to` 断言判红。下游 `M10-M9-EXIT` 由 `OPEN`
改为 `SATISFIED`，**只登记事实、不构成 M10 的准入批准**（M10 仍需 `M10-M8-EXIT` 与自身 11 项 `OPEN` 决策）。
**三条 caveat 随收口一并接受、未解除**：① 冻结评测范围**仅限 M9 外部 AI 路径**（非全项目评测，遵循度仍为
定性）；② 真实 provider 的延迟/成本/失败模式**仍未验证**（arm B 未运行，且被刻意排除在门禁判据外）；
③ 10K/100K 属 M8（`BLOCKED`）/ M11（拟议）。另登记一条**已知限制**（不阻塞收口）：外部 AI 路径的
`PlanAIRequest` **不含先修关系**，而 `goal_planner._ai_order` 拿先修违反数作闸门丢弃整个置换——即模型被
要求满足一个从不告诉它的约束；2026-09-22 一次**第三方 provider 探针**（**非 arm B、非 M9 证据、不进门禁**，
产物在 gitignored 的 `artifacts/`）实测披露先修边可把采纳率由 `5/10` 提到 `8/10`，而仅改措辞无效（`4/10`）。
修复它需动 `M9-EXTERNAL-AI` 的 `MINIMAL_DISCLOSURE` 披露范围，**本次不动**，留作后续阶段输入。本次为**纯治理
记录变更**：未改任何生产代码、未新增公开路由、未 bump `SCHEMA_VERSION`；`tests/M9` 354 项与全量
1272 collected / 1267 passed / 2 skipped / 3 failed 均不变）
· 上一修订 v2.34（2026-09-22：M9 **三处缺陷修正**，
**均不触发 §4 撤销**：① 外部 AI 路径的 output 预算曾把**累积**值（2048）直接当作 `create_turn` 的
`max_tokens` 传下去，而 `llm_client.create_turn` 硬拒大于 `MAX_TURN_OUTPUT_TOKENS`(1024) 的值——于是
**默认配置下**每次调用都在发出任何 HTTP 请求之前抛 `ValueError`，被回退路径收敛成 `provider_unavailable`，
整条外部 AI 路径静默失效，而既有测试全绿。**为何全绿**：`test_plan_ai_adapter.py` 修复前收集 50 项，其中
凡是构造 adapter 的都经 `proposer=` 注入同步 stub（其余只碰 dataclass / 载荷 / 解析 / 预算校验等接缝），
故没有一项触到那个调用点；而修复前**默认运行**的真实桥驱动者 `test_plan_ai_benchmark.py` **穿过**了该调用点
却没抓到——它的 `_StubClient.create_turn` 把 `max_tokens` 直接丢掉，于是超限的 2048 照样通过
（`test_plan_ai_provider_smoke.py` 同样走真实桥，但默认 skip）。真教训是**桥接 stub 必须复刻客户端的硬拒**。
现拆成两个字段：新增的 `max_turn_output_tokens`（单轮，默认 1024）**在本地执行**，并新增
`SA_PLAN_AI_MAX_TURN_OUTPUT_TOKENS`（只能收紧）；累积值 `max_output_tokens` 则**没有运行期执行点**（修复把
唯一送出它的调用点换成了单轮值），**但并非无人读**——`_validate_limits` 在构造期校验它（正整数、≤ 冻结默认、
≤ `max_input_tokens`）并据此给单轮值定上界。② `_distribute` 把
`total_days`（请求窗口）当硬截断，排不完的任务被一次性倾倒进一个不设上限的「第 `total_days + 1` 天」——
默认请求下该天 114 个任务 / 3890 分钟，而当日可用仅 110 分钟（**35.4 倍**，分母为当日可用容量
`hours_per_day × 60 − 10`；探针集内最高是 `0.5 小时/天` 的 4590/20 = **229.5 倍**）。现改为**逐天追加**，
追加的天受同一容量约束。判据取自声明而非
自造：`hours_per_day` 是每日**容量**、`target_date` 是**视野**，超出窗口本就合法（`review_plan.py` 的
「剩余任务追加到最后一天（如果超出天数）」是唯一的正面声明，M9 逐字继承），违反声明的是**每日容量**。
③ `limit_env_names()`（步骤 6 引入，docstring 自述「供配置层与测试共用同一份清单」）按 `PlanAILimits` 的
**字段名**推导，于是宣传了一个配置层**不兑现**的 `SA_PLAN_AI_MAX_RETRIES`（`max_retries` 有字段但刻意不可由
环境变量覆盖，见 `platform/README.md`）——操作者照它设值会**静默无效**：配置层不报错，预算也不收紧。
实测旧代码：宣传清单 9 项、兑现清单 8 项，差集恰为该名。现改为直接取自配置层真正兑现的
`config._PLAN_AI_LIMIT_ENV`（两者**同源**），并新增护栏用例断言两份清单逐个相同且宣传清单非空。
**为何不触发 §4**：`M9-EXTERNAL-AI` 的决策值不含任何数字，2048/1024 是实现常量；两个冻结摘要
（`workload_digest` / `budget_scenario_digest`）修正后重算**逐字节不变**，故 1K 与预算矩阵的历史读数
继续可比；`plan_id` 不随分日变化（把 `_distribute` 换成只产出一个空天的桩，`plan_id` 逐字节不变），
计划身份这一兼容不变量未被触碰。③ 则**连决策值都不涉及**——它只改一个辅助函数的数据来源，且该函数**当前
无生产调用方**（全仓只有测试引用），故其运行期行为不变。故属**兑现**既有决策而非**改判据**——不 bump
`plan_revision`、不新增 `approval_reference`、不新增 `admission_history` 记录、不新增公开路由
（详见 M9 计划 §4.4）。
**诚实残留**：`and day_tasks` 守卫保证每天第一个任务必被放入，故单条任务超容量时该天仍会超出——保证是
「每天**至多一个**任务造成超出」，不是「绝不超出」；且与 `review_plan.py` **刻意分叉**（该服务有同一缺陷，
但 `platform/tests/test_review_plan.py` 的 `actual_days <= max_days + 1` 明确容忍它，且该套件按仓库约定
冻结不动）。`tests/M9` 327 → 354 项（新增 `test_day_distribution.py` 18 项 + adapter 9 项；
`m9_benchmark` 3 与 `online` 3 均为 `m9` 的**子集**，不另计）；全量 1245 → 1272 collected、1267 passed、
2 skipped、3 failed（3 项为 M7 TXT parser 按设计 fail closed）。另修一处**标记卫生**缺陷：
`tests/M9/test_mastery_write_authority.py` 缺 `pytestmark`，致 `-m m9` 少收集 8 项而文档按 324 报数
（实际 319）——现 354 项**全部**带 `m9` 标记）
· 上一修订 v2.33（2026-09-22：M9 **评测口径解冻**：
owner 以 plan_revision v1.5 把 `M9-EVALUATION` 的延迟/成本维度由 `..._LATENCY_COST_DEFERRED` 改为冻结评测。
这是 M9 **第一个真正触发 §4 撤销**的变更（v1.3/v1.4 都在论证「为何不触发」），`ADMITTED→REVOKED→ADMITTED`
过渡已登记在 `admission_history`（live 字段仍 `ADMITTED / IN_PROGRESS`，理由见 M9 计划 §4.3）。冻结口径
**仅限 M9 外部 AI 路径**，分两臂：CI 臂在 `tests/M9/test_plan_ai_benchmark.py` 以冻结预算矩阵驱动**真实**
`build_anthropic_proposer(client_factory=…)` 接缝（用 `proposer=` 注入会绕过 `_run_blocking`，故那样断言
deadline 是假证据），逐场景断言稳定原因码；真实 provider 臂新增 `tests/M9/test_plan_ai_provider_smoke.py`
（`online` + skip 门控、花费上限默认 $1.00、只记脱敏字段、**非门禁、本次未运行**）。**必须按窄口径读**：
stub 下延迟是桥接开销、成本由脚本化 usage 算出，故 CI 臂冻结的是**预算被强制执行**而非性能；
`max_input_tokens` / `model_timeout_seconds` / `max_output_tokens` 不在本地执行（报告含机器可读的
`enforced_locally` / `not_enforced_locally`）。`tests/M9` 324 → 327 项（`m9` 321 → 324 + `m9_benchmark` 3）；
全量 1242/1238 → 1245/1240（另 2 项 skip）。M9 七项退出条件**在各自声明的范围内**已挣得，但**不得**读成
「M9 完成」——真实 provider 性能被刻意排除在门禁判据外且仍未验证，`COMPLETE` 另需独立 `completion_approval`，
本次不申请）
· 上一修订 v2.32（2026-09-21：M9 **退出条件证据**：新增
`tests/M9/test_mastery_write_authority.py`，以**动态枚举** `platform/app/` 全部源文件（当前 60 个）钉住
「正式 mastery 只有一个写入权威」——写 `study_sessions`/`answer_attempts` 的模块**恰好**是 `learning_store.py`，
M9 的 8 个模块与写权威**导入不可达**（AST 闭包断言）。既有测试是逐模块证明「我没写」，本次补上**闭包**证明；
该增量**不新增写路径**（`m9.mastery-write` 仍在 `excluded`，M9 计划 §1/§2 明令 Planner 不得成为第二套 mastery
权威）、**不改 `plan_revision`、不写 `admission_history`、未新增公开路由**。`tests/M9` 316 → 324 项
（`m9` 313 → 321 + `m9_benchmark` 3）；M9 退出条件中**仅「冻结评测达标」仍未挣得**，故 M9 尚不具备退出条件）
· 上一修订 v2.31（2026-09-21：M9 步骤 6 窄口径**实施完成**：
默认关闭的可选外部 AI 路径 + 冻结任务集 1K 比较（`m9_benchmark`，独立 CI 步骤）。读数是输入有界（10 vs 1000
实测 chunks 下 prompt 逐字相同）、两路径先修违反为 0、确定性可重放；**不是容量声明**，AI 路径在 CI 用 stub，
真实 provider 延迟/成本/失败模式未验证，10K/100K 仍属 M8（`BLOCKED`）/ M11，`M9-EVALUATION` 未动、评测
workload 未冻结）
· 上一修订 v2.30（2026-09-21：owner 以 plan_revision v1.4 把 `m9.external-ai` 移入 `included`（`excluded` 只剩
`m9.mastery-write`），批准实现默认关闭的可选外部 AI 路径与冻结任务集 1K 比较；完整口径不可准入（10K/100K 撞
M6a 2,000 chunks 硬上限且分级属 M8 的 `M8-BENCHMARK`，10K 真实数据属 M11；延迟/成本解冻会构成对
`M9-EVALUATION` 的实质变更并强制 `REVOKED`），故 `M9-EVALUATION` 原值不动、不触发 §4 撤销、不写
`admission_history`；理由见 M9 计划 §4.2）
· 上一修订 2026-09-21（M9 步骤 4d：关闭 §4 已记录的
准入留痕覆盖缺口——`tests/regression/test_governance_contract.py` 的 `_registry_references` 白名单现同时枚举
`admission_history[].reference`，并补非空性护栏与 §7 五键键集断言；纯治理测试硬化，未新增能力 / 路由 / 字段，
未改批准字段与 `admission_history` 内容；`tests/regression` 62 → 79 项（含同日既有增量），外部 AI 与评测
workload 仍未完成）
· 上一修订 2026-09-21（M9 步骤 4c：修复步骤 3
已记录的残留——`main.py` 原先把 `all_reviews()` 在 import 时冻结成快照，改为注入只读活投影
`ReviewHistoryProjection`，使 `reviewed` 标志、排序优先级与 `plan_id` 随进程内新复习刷新（对齐紧邻的
mastery 投影）；未注入时回落快照，既有调用方逐字节不变；`tests/M9` 245 → 263 项；非范围扩张，
未改批准字段与 `admission_history`，未新增公开路由，外部 AI 与评测 workload 仍未完成）
· 上一修订 2026-09-21（M9 步骤 4b：计划身份
按 principal 分隔（带标签段、仅非 None 时追加，故 `principal_id=None` 的身份逐字节不变），
`_response_to_record` 补 `summary`、`replan` 保真还原 principal 与源范围；principal 是内部记录键，经单点
`_public_plan` 在所有读取路径上剥离，不进 HTTP 响应体；`tests/M9` 219 → 245 项；未新增公开路由，
外部 AI 与评测 workload 仍未完成）
· 上一修订 2026-09-21（M9 步骤 4a：owner 以
plan_revision v1.3 显式扩张 `m9-plan-lifecycle-v1` 范围至步骤 4（拆为 4a/4b），受限检索接缝
`PlanGroundingService` 与四类预算、fail-closed 交叉校验已交付；`STALE_DELETED_SOURCE_ENTRY_ZERO` 首次在
服务层接缝上有端到端证据，`tests/M9` 187 → 219 项；未新增公开路由，外部 AI、评测 workload 与 4b 未完成）
· 上一修订 2026-09-21（M9 步骤 3 收尾：先修关系
只读投影已交付并接入确定性 Planner，`M9-EVALUATION` 的「先修违反=0」在真语料上实测成立；M9 其余边界不变，
步骤 4 与评测 workload 未获批）· 上一修订 2026-09-14（M8 八项 Decision 已 `RESOLVED`；`draft-0.10` 的 P3 拒绝链
保持冻结；successor `draft-0.11` 已完成 P0/P1/P2 并到达 `BINDING_FROZEN` 后独立 P3 `REJECTED / stop`；执行、
后端选择与阶段批准均未完成，M8 保持 `BLOCKED / NOT_STARTED`）· 维护：每次会话开工查看本文档*
