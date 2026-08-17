# 项目计划 · StudyAssistanceAgent

> 面向大学计算机专业学生的个人学习助手 + 面向 **AI 应用开发岗** 的面试项目。
> **双目标**：① 帮助自己学懂每门课（自学价值）；② 简历上可讲的完整 Agent/RAG 工程（面试价值）。
> 状态图例：⬜ 未开始 ｜ 🔄 进行中 ｜ ✅ 完成

## 一、项目定位（一句话）

**「自己的课程学习+面试备战系统」**：Markdown 课程知识库（考点/面经/掌握度）→ 多路召回 RAG（本地 BGE 向量+BM25+RRF）→ FastAPI 轻量 Agent → 带出处问答 + 复习计划/测验。

## 二、技术选型（已拍板）

| 层 | 选型 | 理由 |
| --- | --- | --- |
| 知识库 | 纯 Markdown + frontmatter（`knowledge/`） | 数据是个人资产，可读/可版本化/可迁移 |
| 后端 | Python + FastAPI + uvicorn | 轻量、RAG/Agent 生态好、面试叙事友好 |
| 向量 | 本地 BGE（sentence-transformers），可选安装 | 离线、零 API 成本、隐私；未装时自动降级关键词 |
| 检索 | BM25 + 向量多路召回 + RRF 融合 | 混合检索，鲁棒、无需调参 |
| LLM | OpenAI 兼容接口（DeepSeek 等），可配 | 不配则降级为笔记摘要，保证总是有输出 |
| 存储 | 无 DB，JSON 缓存索引 | 个人规模（几百片）足够，零运维 |

**架构**（参考 `ai_agent_platform` 的 MultiRecall/RRF/LongContext 模式，做个人级瘦身）：

```
提问 → MultiRecallService
         ├─ 路1: LocalVectorStore(BGE 余弦近邻)
         └─ 路2: Bm25Search(bigram 关键词)
      → RRF 融合 → 结果(带 file 出处)
      → QaService: LLM 生成(勒令带出处) 或 降级笔记摘要
      → FastAPI /api/v1/{search,qa,qa/stream}
```

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
> **分支映射**：`feature/m1a-os-knowledge` → `feature/m1b-ds-knowledge` → `feature/m1c-co-knowledge` → `feature/m1d-platform-polish`
- ✅ 操作系统：`knowledge/os/`（进程/调度/同步/死锁/内存/文件）→ 15 篇条目 + 真题复盘（M1a 完成，hybrid RAG 评测 Recall@3=0.970，33 题评测集覆盖全部条目）
- ✅ 数据结构复习：`knowledge/ds/`（绪论/线性表/栈队列/串数组广义表/树/图/查找/排序/堆与优先队列/真题复盘）10 篇完成（M1b 完成）
- ✅ 计算机组成原理：`knowledge/co/`（概述/数据表示/运算器/存储系统/指令系统/CPU设计/总线I/O/MIPS实验/浮点数运算/期考复盘）10 篇完成（M1c 完成）
- ✅ 每课配 RAG 评测集：OS 33 题 + DS 23 题 + CO 19 题，共 75 题
- **退出条件**：3 门课各 ≥10 篇条目；评测 Recall@3 ≥ 0.8；能演示「问真题→检索到→带出处答」。

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

### M3：工程质量与沉淀（测试骨架已建立，功能待落地）
> **分支映射**：`feature/m3a-vector-store` → `feature/m3b-observability`
> **当前状态**：M3a/M3b/M3c/M3d 的阶段测试和契约已预置，但功能尚未整体交付；M3c 因 `knowledge/interview/` 尚不存在而条件跳过 10 项测试。
- ⬜ 可选：接入在线/本地向量库（如 sqlite-vec/Chroma）替换线性扫描
- ⬜ 观测/日志：检索延迟、缓存命中率、问答日志（对应可观测性面试点）
- ⬜ 面经库 `knowledge/interview/`：按知识点聚合面经题 ≥50
- ⬜ 沉淀个人方法论：复习笔记规范复盘、PLAN 裁剪
- **退出条件**：M1 三门全 ≥20 篇、面经 ≥50、评测闭环跑通、面试 8 大追问都能讲清。

## 四、风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 数据先行但精力有限，笔记跟不上 | M1 切入最急的课（如 OS 考前）；单篇笔记 20 分钟，按真题驱动 |
| 检索效果差（Recall 低） | 用评测脚本量化；调整切块策略（小节切分 vs 整篇）、扩 tags |
| 面试被追问「和 RAG demo 有何不同」 | docs/interview/README 已备 8 大追问答案；多用「数据驱动优化」叙事 |
| 参考项目 Java/Spring 太重不适合 | 已确认 Python 栈 + 本地向量 + 降级路，仍借鉴其 MultiRecall/RRF 模式 |
| 本机 GitHub 访问受限 | SSH 走 443 已配置；push 由用户手动完成 |

## 五、面试叙事核心（详见 docs/interview/README.md）

一句话 + 5 个设计决策 + 8 个考点映射 + 3 个量化优化点（RAG 评测、切块调优、缓存命中）。

---

*创建：2026-08-10 · 版本：v1.0（M1d+M2 已完成：三课 35 篇条目、75 题评测集、完整测试 121 项，当前 107 passed/14 skipped；M3 测试骨架已建立）· 维护：每次会话开工查看本文档*
