# 面试价值文档（面向 AI 应用开发岗）

> 本项目在你的简历/面试叙事中的定位、可讲的技术点、以及如何把「自学工具」讲成「有工程深度的项目」。
> 目标岗位：**AI 应用开发**（RAG / Agent / 模型调用 / 检索系统方向）。

## 一、一句话叙事

> **「我给自己做了一个课程学习+面试备战系统：把课程按考点/面经/掌握度建成 Markdown 知识库，做了多路召回 RAG（本地 BGE + BM25 + RRF）和 FastAPI 学习会话。核心演示是工作台里的一次闭环：检索讲解 → 出题 → 评估 → 记录复习，响应里带 `tool_trace`；无 LLM、无向量模型时也能离线跑，CI 用 BM25 回归。我用它复习操作系统并准备 AI 应用开发面试。」**

**为什么这个叙事强**：它不是「又做了一个 AI 客服」，而是同时证明 4 件事——领域数据建模、RAG 落地、Agent 工具调用、真实使用闭环。

## 二、面试官会问「为什么这么做」→ 你该答的设计决策

| 决策 | 你的答案（一句话） | 体现的能力 |
| --- | --- | --- |
| 为什么知识库是 Markdown + frontmatter | 「数据是个人资产，格式必须可读、可版本化、可迁移；检索在文件层做，零依赖」 | 权衡取舍、务实 |
| 为什么向量用本地 BGE 而非在线 API | 「隐私、成本、离线可用；嵌入是语义检索的关键，本地推理也是可以讲的能力」 | 对 embedding 的理解 |
| 为什么多路召回（向量+BM25+RRF） | 「向量抓语义、关键词抓术语精确匹配，RRF 融合避免单一信号失灵，且无需调参」 | 混合检索知识 |
| 为什么用 FastAPI 而非 Spring | 「轻量、Python 生态适合 RAG/Agent 快速迭代，个人项目启动快」 | 技术选型判断 |
| 为什么要有降级路径 | 「LLM/向量不可用时返回笔记摘要，保证『总是有输出』——线上系统最看重的是可用性」 | 工程鲁棒性思维 |

## 三、面经知识库

面经条目导航见 [knowledge/interview/README.md](../../knowledge/interview/README.md)，当前覆盖 51 条 OS、DS、CO、RAG/Agent 与项目追问。

## 四、项目亮点 → 面试考点映射表

| 项目功能 | 面试考点 | 可深挖的问题 |
| --- | --- | --- |
| 多路召回 RAG（向量+BM25+RRF） | **Q173 RAG 效果评估**、混合检索 | RRF 为什么用 k=60？BM25 的 IDF 怎么算？两路结果怎么融合？ |
| 本地 BGE 向量（sentence-transformers） | **Embedding 原理**、余弦相似度、向量数据库 | 语义检索 vs 关键词检索差异？embedding 维度怎么定？为什么 saying normalize？ |
| 知识库切分（frontmatter 解析 + 按 `##` 切块） | **Chunking 策略** | 切块大小怎么选？太小/太大会怎样？metadata 有什么用？ |
| 带 JSON 缓存的索引构建 | **缓存失效策略**、性能优化 | mtime 快检为什么可靠？缓存破坏怎么恢复？ |
| LLM 上下文注入 + 勒令带出处 | **Prompt 工程**、幻觉控制 | 为什么让模型标注出处？万一知识库没有答案怎么办？ |
| SSE 流式输出 `/api/v1/qa/stream` | **SSE vs WebSocket**、流式输出 | 为什么用 SSE 不用 WebSocket？心跳怎么加？ |
| 优雅降级（无向量/无 LLM 仍可用） | **可用性设计**、失败恢复 | fallback 路径如何保证不误导用户？ |
| `health` 端点 + 可观测角度量 | Actuator / 度量埋点 | RAG 检索延迟、缓存命中率怎么统计？ |
| 多轮工具编排（`/api/v1/study-sessions` + 工作台） | **Tool Orchestration**、Agent 编排 | 工具选择逻辑？`tool_trace` 怎么证明？答对/答错分支怎么走？ |
| 间隔重复复习排程（`review-due`） | **状态管理**、遗忘曲线 | 间隔序列怎么定？历史怎么持久化？逾期怎么计算？ |
| 复习计划生成（`review-plan`） | **任务规划**、知识图谱 | 条目怎么排序？时间怎么分配？章节依赖怎么处理？ |
| 测验生成（`quiz`，三数据源） | **数据聚合**、多源融合 | 三个数据源怎么去重？难度怎么筛选？答案怎么验证？ |

## 五、数据驱动优化的实锤（面试最加分）

参考项目一句「调整切片大小 512→1024 召回率从 62% 提升到 79%」就是它的杀手锏。对应的真实数字：

- **BM25 候选池截断**：`SA_BM25_POOL=50` 只搜前 50 片，知识库扩到 15 篇后 OS Recall@3 从 1.000 掉到 0.650；改为全库检索后回到 0.970。
- **当前离线 90 题 BM25 Recall@3**：OS 1.000、DS 0.929、CO 1.000（`python tools/run_evaluation.py`）。
- **交付延迟**（无模型）：冷启动约 9.0s，热启动 `/health` 19.8ms，一次学习会话 139.8ms。

面试时讲「先量化、再修根因」，不要只讲加了向量。

## 六、真实工具调用链（学习会话）

核心演示不再只是 Skill 里手工串联服务，而是 `POST /api/v1/study-sessions` 留下的 `tool_trace`。
一次答对闭环的真实步骤：

```text
create -> qa -> explain -> quiz -> evaluate -> review-log -> completed
```

| 步骤 | 服务 | 作用 |
| --- | --- | --- |
| `qa` | `QaService` | 检索知识片段并返回出处 |
| `explain` | `StudySessionService` | 把检索结果收成讲解 |
| `quiz` | `QuizService` | 出 1 至 2 道相关题 |
| `evaluate` | `StudySessionService` | 确定性评估，不依赖 LLM |
| `review-log` | `ReviewSchedulerService` | 写入间隔重复复习记录 |

答错分支是 `evaluate -> remediation -> retry`；连续两次答错后结束并给出完整参考。
工作台只渲染这些状态，不复制状态机。离线启动见 [docs/demo.md](../demo.md)。

## 七、常见追问 & 备好答案


- **「这项目和网上 RAG demo 有什么区别？」** → 多路召回 + RRF 不是单一向量检索；真实使用数据（真题/自己的笔记）；有评估闭环。
- **「向量库为什么不用 Milvus / Chroma？」** → 个人规模（几百片）线性扫描足够，之后换弹性的接入即可，接口（vector_store.py）已抽象。
- **「如何避免回答幻觉？」** → 勒令只基于检索片段、标注出处、无命中时明确说「知识库暂无」。
- **「并发量表级？」** → 诚实：个人项目，但 FastAPI 异步 + 流式已具备；如要规模化再加缓存/分片（这反而是加分项——你知道边界）。
- **「这算 Agent 吗？有没有 ReAct / Function Calling？」** → 学习会话是服务端状态机编排现有 QA/Quiz/Review，`tool_trace` 记录固定步骤；没有 LLM 自主选工具。招聘对照与是否立项见下方相关材料，不要把未实现能力讲成现状。

## 八、给简历的一句话亮点（可替换用）

> 「设计并实现个人学习 Agent：Markdown 知识库 → 混合检索（BGE + BM25 + RRF）→ 服务端学习会话编排（带出处问答、测验、间隔重复）→ 最小工作台与离线 CI；90 题 BM25 Recall@3 ≥ 0.92。」

## 九、相关材料与能力边界

现行叙事讲的是**领域状态机编排的学习 Agent**：可讲混合检索、学习会话、`tool_trace`、离线降级和 90 题评测。
这不是通用 ReAct / Function Calling，也不要把招聘对照清单当成已实现能力。

| 文件 | 用途 |
| --- | --- |
| [StudyAssistanceAgent_requirement.md](StudyAssistanceAgent_requirement.md) | 对照 Agent 招聘要求与参考架构的原始调查 |
| [../plans/references/agent-alignment-analysis.md](../plans/references/agent-alignment-analysis.md) | 对本仓库的核实与是否立项建议；不是执行计划 |

被追问「为什么不做 ReAct」时：教学流程已知，所以默认走确定性闭环，保证复习记录和离线可用。分析结论是维持 M5 收口，暂不新开平台里程碑。

---

*维护：2026-08-20 补充招聘对齐材料入口；面试前复习一句话、工具调用链、三个量化数字和能力边界。*
