# StudyAssistanceAgent 项目计划 - 产品需求文档 (PRD)

> **文档定位**：本文件是 `requirements-clarity` 澄清记录，不是路线图，也不是开工许可。
> **最终里程碑与准入仍以 `docs/PLAN.md` 为准。**
> 测试通过不能替代 `ADMITTED` 准入批准。
> 当前仅允许在各自批准范围内实施已获准阶段；M6b 的批准只覆盖默认关闭的只读 Agent Preview，不包含 M7。

## 需求描述

### 背景
- **业务问题**：需要一个可离线运行、可迁移的个人学习系统，把本地 Markdown 知识源变成「检索讲解 → 出题评估 → 复习记录」闭环，而不是一次性 RAG 演示。
- **目标用户**：大学计算机专业学生；后续也可接入自有知识源，不绑定单一课程。
- **价值主张**：默认计算机知识包先可用；正式学习路径由状态机保证可恢复、可降级；自主 Runner 作为正交可选执行器，不替换教学法。

### 功能概述
- **核心功能**：
  - 本地 Markdown 知识库 + BM25/向量多路召回 + 带出处问答
  - 正式学习状态机：讲解、测验、评估、复习记录、跨重启恢复
  - 最小工作台与 REST API
  - M6b 已实现的默认关闭隔离只读 Agent 预览；M10 可选自主 Runner
- **功能边界**：
  - 包括：已完成的 M0–M5 MVP；后续按准入推进 M6a–M10
  - 不包括：用 Runner 替换状态机；默认把网页/AI 草稿写入检索库；把用户源或 PDF 写入 Git
  - 不包括：在 `BLOCKED` 期间开始对应阶段的生产编码；M6b 批准不授权 M7
- **用户场景**：
  1. 打开工作台完成今日待复习、讲解、作答、反馈
  2. 通过 API 检索/问答/出题/复习，无 LLM 时仍返回笔记摘要
  3. 后续可选开启只读 preview 或自主 Runner，正式会话仍走状态机

### 详细需求
- **输入/输出**：课程/主题提问、测验答案、复习完成记录；输出带出处讲解、题目、评分、复习排程和会话状态。
- **用户交互**：`GET /` 工作台调用正式会话 API；REST/SSE 供脚本与评测复用。
- **数据需求**：`knowledge/` 人工笔记默认可检索；学习状态写入 SQLite；crawler 候选默认不可检索。
- **边界情况**：无向量模型回退 BM25；无 LLM 回退摘要；preview 失败不创建正式 session；旧会话可恢复。

## 设计决策

### 技术方案
- **架构选择**：Python + FastAPI + SQLite；检索为 BM25 + 可选 BGE + RRF。不把外部向量库或容器编排设为默认依赖。
- **关键组件**：`MultiRecallService`、`QaService`、`StudySessionService`、工作台、评测入口；M6b/M10 为独立 preview/Runner。
- **数据存储**：`learning_state.sqlite3` 与 `vector_store.sqlite3`；用户原始材料和大文件保存在仓库外，Git 只存默认 pack、精炼笔记与配置；Source Registry、revision、索引控制数据和 manifest 的本地持久化边界由 M7/M8/M10 对应阶段契约决定，不得把用户原始材料复制进 Git。
- **接口设计**：保持现有 `/api/v1/search|qa|quiz|review-*|study-sessions`；M6b 仅在显式启用时注册独立
  `/api/v1/agent-preview`，M6b/M10 均不得接管 `study-sessions`。

### 约束条件
- **性能要求**：继承现有 `/health` 分位数与默认 OS/DS/CO 90 题 Recall@3 保护基线；M6b–M10 仍须分别冻结与自身能力匹配的 workload、p50/p95、资源、成本和质量阈值，作为对应阶段的额外准入/退出门禁，不得用现有 90 题基线替代。
- **兼容性**：一键启动 `python tools/start_local.py`；相对路径 + 环境变量配置；不强制 LLM、BGE、Docker、Qdrant。
- **安全性**：API、日志、trace、错误、OpenAPI 和持久化不泄露宿主机绝对路径、密钥、用户答案或知识正文。
  M6b 为提供 preview 会把 prompt 与受限工具结果发送给 Anthropic；上述“不泄漏”约束针对本地和未授权边界。
- **可扩展性**：M7 才引入用户源生命周期；M8 才按 benchmark 选择专业存储。

### 依赖顺序
- M6a-P0 已收口，只构成 M6a 前置证据，不批准 M6a。
- M6b 以 M6a 退出证据为共同必要前置，并须独立满足 `M6B-PROTECTED-BASELINE`、专属决策和批准；不依赖 M7。
- M7 以 `M7-M6A-SOURCE-CONTRACT` 为共同必要前置，并须独立满足 `M7-PROTECTED-BASELINE`、专属决策和批准；不依赖 M6b。
- M6b 与 M7 彼此不互为前置；M6b 当前为 `ADMITTED / COMPLETE`。M7 基础设施范围的实现与技术验收已完成，
  并于 2026-09-06 在 `m7-infrastructure-only-v1` 范围内取得独立人工完成批准，当前为
  `ADMITTED / COMPLETE`；Network 不在 M7 scope 内，技术证据本身不产生批准。
- M8/M9/M10 的事实型 M7 退出前置已满足。M9 已于 2026-09-22 在 `m9-plan-lifecycle-v1` 范围内取得独立完成
  批准，现为 `ADMITTED / COMPLETE`（其 M8 前置以「维持当前 SQLite/BM25 后端」满足，非 M8 执行）；M10 的
  三项前置亦已于 2026-09-22 全部 `SATISFIED`（`M10-M8-EXIT` 走同一条维持现状结论分支，见 M10 计划 §2.1，
  非容量证据）；M8 仍须闭合自身决策与批准，M8 与 M10 保持 `BLOCKED / NOT_STARTED`（M10 等待自身十一项强制
  决策与独立批准），且不以 M6b 为写路径或 Source 生命周期前置。

### 风险评估
- **技术风险**：Runner 误写学习状态。缓解：状态机独占正式写入；M6b 只读；M10 完成授权/checkpoint/幂等后才写。
- **依赖风险**：外部 LLM 或模型下载失败。缓解：摘要降级与 `SA_USE_VECTOR=false` 离线路径。
- **进度风险**：把准入或准备计划当成生产开工许可。缓解：M7 虽已取得基础设施 scope 的
  `ADMITTED`，仍须独立 `implementation_start=AUTHORIZED` 才能实施；Network、M8、Milvus 不在批准范围内，
  以 `docs/PLAN.md` 为准。

## 验收标准

复选框分为三类：**现行保护** `[x]` 表示当前事实已满足且须持续保护；**准入复验** `[ ]` 表示申请准入时必须重新验证并留证；**未来验收** `[ ]` 表示仅在对应阶段 `ADMITTED` 后实施。任何勾选或测试通过都不能替代负责人批准。

### 现行保护（当前已满足并持续回归）
- [x] 无 LLM、无向量模型时，工作台仍能完成讲解 → 作答 → 评估 → 复习记录
- [x] 学习状态机继续独占 `/api/v1/study-sessions` 的状态转换与领域写入
- [x] crawler 候选默认不进入检索；未审核内容不能污染默认知识包
- [x] 旧 SQLite session 重启后可按 `session_id` 恢复
- [x] 默认 OS/DS/CO 90 题评测入口保持不变；Network 仍为显式扩展集
- [x] API/OpenAPI、错误码和生成分层不回退
- [x] 文档口径与 `docs/PLAN.md`、准入门禁一致
- [x] 换机器后仅需 Python 环境、仓库和可选 `.env` 即可启动
- [x] 用户知识源可放仓库外，不复制进 Git
- [x] 面试叙事仍表述：正式路径是状态机，Runner 是可选执行器

### 准入复验（申请各阶段准入时重新留证）
- [ ] **准入复验** 对应阶段的前置证据、专属保护基线、强制决策和批准记录全部闭合；通过复验不能替代 `ADMITTED` 批准
- [ ] **准入复验** 默认离线路径、旧 session 恢复、API/OpenAPI、路径隐私和 OS/DS/CO 90 题保护基线均重新通过
- [ ] **准入复验** 对应阶段独立冻结 workload、p50/p95、资源、成本和质量阈值，不以现有 90 题基线替代

### 未来验收（仅在对应阶段 `ADMITTED` 后实施）
- [ ] **未来验收** 自主 Runner 若启用，必须作为正交可选路径，失败不得回退创建正式 session（M10，`BLOCKED`）
- [x] **现行验收** M7 正式 Search/QA 内部可信 principal overlay、冻结 1k/3k BGE 与五格式 parser/lifecycle 证据已完成；2026-09-06 的独立人工批准完成阶段。Network 晋升仍须另行逐文档批准
- [ ] **未来验收** 本阶段测试、`tests/regression/` 与对应性能/评测门禁通过后，才可合并或宣称该阶段交付

## 执行阶段

### 阶段1：准备
**目标**：保持 M0–M5 可交付，不提前实现被阻断阶段
- [x] 以 `docs/PLAN.md` 为最终状态权威
- [x] M6a 准入前仅做设定澄清与准备计划；M6b 已按独立批准实现默认关闭的只读 preview；M7 基础设施已获得独立生产开工授权，
  已形成并冻结 Source Registry、manifest/parser、normalized document、source-local FULL/INCREMENTAL/delete/isolation 与 FTS5/offline fail-closed 局部合同；M8–M10 保持阻断
- **交付物**：现行 MVP + 准备计划
- **时间**：已完成 / 持续维护

### 阶段2：核心开发
**目标**：按准入顺序推进，不改现有里程碑切分；本阶段仅适用于已获 `ADMITTED` 的阶段。M6a 已完成；M6b
默认关闭的隔离只读 preview 已完成全部 closeout 门禁与证据同步；M7 基础设施已形成并冻结 Source Registry、
manifest/parser、normalized document、source-local FULL/INCREMENTAL/delete/isolation、FTS5/vector/offline fail-closed
与 Search/QA 内部可信 principal overlay 合同，并完成冻结 1k/3k BGE 与五格式证据；独立人工完成批准已登记。
M8–M10 继续阻断。
- [x] **现行保护** M6a：契约与兼容骨架，不改正式 API（`ADMITTED / COMPLETE`）
- [x] **收口验收** M6b：阶段隔离、隐私/零写入、离线 benchmark、回归和文档门禁均已通过，
  已切换为 `ADMITTED / COMPLETE`；该收口不依赖或批准 M7
- [x] **现行保护** M7 基础设施：Source Registry、manifest/parser、normalized document、source-local
  FULL/INCREMENTAL/delete/isolation、FTS5/vector/offline fail-closed、Search/QA overlay 与冻结技术验收已完成；
  2026-09-06 独立人工批准后为 `ADMITTED / COMPLETE`，范围仍限 `m7-infrastructure-only-v1`
- [ ] **未来验收** M8–M9：专业化存储与目标计划；事实型 M7 退出前置已满足，但 M8 自身门禁未闭合，M9 仍依赖 M8
- [ ] **未来验收** M10：可选自主 Runner，状态机仍为默认；事实型 M7 退出前置已满足，但仍依赖 M8–M9，
  不以 M6b 为写前置
- **交付物**：各阶段计划中的退出条件
- **时间**：阶段准入且适用的独立生产开工门禁为 `AUTHORIZED` 后才能开工

### 阶段3：集成与测试
**目标**：用现有测试体系验收，不另起并行测试框架
- [x] 现行回归与文档一致性测试继续保护 M0–M5
- [ ] **未来验收** 各未来阶段获准后，再跑对应阶段目录测试 + 回归套件
- [ ] **未来验收** 未来阶段仍须补充自身 workload 与路径隐私检查，不得只用现有 90 题基线替代
- **交付物**：pytest 与评测报告
- **时间**：每阶段收口时

### 阶段4：部署
**目标**：保持可移植，不新增部署里程碑
- [x] 默认交付仍是 `python tools/start_local.py` 与离线 CI
- [ ] **未来验收** Docker/单二进制只作为可选打包，不作为 M6–M10 开工条件
- **交付物**：一键启动与健康检查
- **时间**：随 M5e 已具备，后续只维护

---

**文档版本**：1.0
**创建时间**：2026-08-24
**澄清轮次**：3
**质量评分**：88/100
**状态说明**：本 PRD 记录澄清结论与不改路线图的推荐实现；最终里程碑与准入仍以 `docs/PLAN.md` 为准。