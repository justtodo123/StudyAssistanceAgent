# M6–M10 阶段推进分析（辅助决策）

> **文档地位：辅助决策，不是最终计划依据。**
> 最终支撑来源只有 [`docs/PLAN.md`](../../PLAN.md)。
> 若本文与 PLAN 冲突，以 PLAN 为准；不要用本文开工、验收或改技术选型。
> 日期：2026-08-20
> 对照：[`docs/interview/StudyAssistanceAgent_requirement.md`](../../interview/StudyAssistanceAgent_requirement.md)
> **历史状态提示（2026-08-21）**：本文保留当时的顺序分析。其“M6 不上 preview / 完整 Agent 留 M10”建议
> 已被后续权威路线图细化为“M6b 只读工具调用预览，完整自主 Runner 仍在 M10”。涉及 M6/M10 范围时只以
> [`docs/PLAN.md`](../../PLAN.md) 和对应执行计划为准。

## 1. 本文解决什么

PLAN 已把定位定为「通用学习 Agent harness」，并把 M0–M5 冻成 MVP。本文只分析：

1. 后续阶段按什么顺序推进更稳
2. 招聘对照文档里哪些能力该并进哪个阶段
3. 哪些看起来像 P0、但对 harness 定位是干扰项

本文不代替执行计划：没有分支名承诺、没有任务工时、没有「必须按这里验收」。

## 2. 和招聘对照文档的关系

`StudyAssistanceAgent_requirement.md` 的价值是**模块清单**，不是产品路线。

它判断对的部分：

- 现状是确定性学习闭环，不是 LLM 自主 Agent
- `tool_trace` 还不是工具注册表 / Function Calling
- 应留在 Python/FastAPI 上增量，不迁 Java
- 无 LLM 时必须能降级

它不能直接当推进顺序的原因：

- 把 ReAct 写成立刻要做的 P0，会跳过 Source/Store，框架还没能加用户数据
- 把 Milvus / Redis / JWT / Grafana / MCP 当成中等缺口，和「单用户、本地优先、万级再上独立向量服务」冲突
- 验收故事是「LLM 自主检索→出题」，新定位的核心故事是「按用户目标执行计划并监控」

建议映射（仅供 PLAN 维护时参考）：

| 招聘对照项 | 建议挂靠阶段 | 不应挂靠的原因 |
| --- | --- | --- |
| 工具协议 / 注册表 | M6 | 现有 QA/Quiz/Review 先变成 Tool，Runner 才能换 |
| 额外知识源、规模 | M7 | 没有 Source，换库也加不了用户数据 |
| 向量库专业化（LanceDB/Qdrant） | M8 | PLAN 已选嵌入式优先，不是 Milvus |
| 语义缓存、查询改写 | M8 或更后 | 先有可切换 Store，缓存才有稳定 embedding |
| 画像 / 外部 AI 规划 / 监控 | M9 | 这是新定位的产品核心，但依赖目录与掌握度表 |
| 可选 ReAct、Agent 评测 | M10 | 有 Tool + 计划执行后，ReAct 才是可回退的 Runner |
| Prometheus/Grafana/JWT/MCP/Docker Compose | 不进 M6–M9 | 单用户学习 harness 不是平台运维题 |

## 3. 为什么必须按 M6 → M10，而不是按招聘 P0 开工

依赖是单向的：

```text
M6 协议（Source/Store/Tool/Runner）
  → M7 用户能加源，千级还能搜
    → M8 存储可替换，万级有退路
      → M9 计划能看到「有什么知识、学会了什么」
        → M10 换 Runner / 做 Agent 评测才有意义
```

若先做 ReAct：模型会调用写死的 `knowledge/` 检索，用户自定义源、计划执行、监控都接不上。
若先上 Qdrant：数据仍只有默认 pack，千级/万级问题不会出现，只会增加离线 CI 负担。
若先做「更聪明的 QA」：新定位要的是按计划学，不是更好的聊天。

## 4. 各阶段推进分析

下列「建议关注点」用于判断 PLAN 里该阶段是否写够；不是新的退出条件。

### M6 Harness 骨架

**PLAN 已定**：协议先行，额外 Markdown 源，API 兼容 MVP，不上独立向量库，不上 ReAct。

推进时真正难的不是写 ABC 四个 Protocol，而是**现有服务能换实现而不改 URL**。
`/api/v1/search|qa|quiz|study-sessions` 必须仍可用，默认 Runner 仍是学习状态机。

招聘对照可吸收：Tool 的 name/description/parameters/execute。
不要吸收：generate_tool_call 端点、ReAct 循环。那是 M10 的可选 Runner，提前做会把状态机旁路掉。

决策提示：

- 额外源只要能配置进检索，M6 目的就达到了；不要在 M6 做源管理 UI
- `learner_id=local` 够用；账号体系仍是非目标
- 若发现必须改 API 字段，应先改 PLAN 再改代码，而不是在分析里默认加字段

### M7 用户数据源与千级检索

**PLAN 已定**：源注册/同步、FTS5、1k–3k chunk 基线；不做爬虫、不做重型 PDF 解析。

这是「通用」能否成立的第一道关。用户加不了自己的目录，harness 就仍是课程助手。

招聘对照里「缺 Milvus」在本阶段应忽略。千级先把内存 BM25 挪到磁盘（FTS5），向量继续走已有 `VectorStore` 协议即可。
规模测试要用夹具，不要把外部课程库拷进 Git。

决策提示：

- 同步必须可中断续跑，否则用户源会让工作台卡住
- 默认 pack 的 90 题 Recall@3 仍是回归尺，不是「用户源也要 0.8」
- PDF 保持「用户自己导出文本再接入」；与仓库「不入库二进制」一致

### M8 专业化存储

**PLAN 已定**：统一 schema；默认 LanceDB；Qdrant 万级可选；SQLite 线性后端降级。

招聘对照想用 Milvus，与 PLAN 冲突 → 以 PLAN 为准。
LanceDB 解决单机千到万、零运维；Qdrant 只在万级夹具冒烟时需要，不应变成默认依赖。

可顺手考虑、但不要写成 M8 必做：基于 BGE 的语义缓存（招聘 C2）。
没有稳定 embedding 后端就做缓存，命中率数字没有意义。

决策提示：

- 控制面（计划、掌握度、事件）和向量面分开，避免再出现 JSON 缓存扛主路径
- 迁移必须从 M5 的 `vector_store.sqlite3` / `learning_state.sqlite3` 能过来
- 无 LanceDB 时仍要能启动，这与「无 BGE 降级」是同一条产品原则

### M9 目标驱动计划与执行监控

**PLAN 已定**：画像（等级/掌握度/目标/每日预算）→ 外部 AI 生成计划（只看目录摘要）→ 按计划选题 → 监控偏差。
无 AI 则扩展现有 `review-plan`，且必须读掌握度。

这是新定位的产品阶段。招聘对照几乎没写「计划执行」，只写了 ReAct；二者不要混。
ReAct 是选工具的循环；M9 是选「今天学哪一条知识」的循环。后者才是学习 Agent。

决策提示：

- Planner 禁止喂全书；只喂标题、tags、难度、掌握度
- 「下一步」连续多轮来自计划，才能证明不是随机 QA
- 现有 study-sessions 应能带上计划引用，但不删除旧契约
- 监控先回答三个问题即可：进度、逾期、掌握度变化。不要先上 Grafana

### M10 Harness 对外

**PLAN 已定**：知识包 manifest、可选 ReAct、Agent 评测（mock 进 CI）；ReAct 关闭时与 M9 一致。

这里才对接招聘对照的 B1/B2/D1：

- ReAct + 步数/超时/重复熔断
- 工具由注册表调用，而不是硬编码
- 评测从 Recall@3 扩展到任务成功、工具合法、成本

前提是 M6–M9 已经能「按计划学一块用户源里的知识」。否则评测集只能再测一遍课内 RAG。

决策提示：

- ReAct 必须是可选 Runner，失败回退状态机
- 非 CS 夹具 pack 能跑通，才算 harness，而不是口头通用
- Token 预算可以很轻（计数 + 上限），不必上 Redis 限流
- MCP/A2A 了解即可，M10 仍非必须

## 5. 明确不建议提前做的事

即使招聘对照标了 P0/P1，也不建议在对应阶段之前做：

- 迁移 Java / LangChain4j / Spring
- 以 Milvus 替换当前向量协议
- JWT、多租户、Grafana 大盘
- 用 ReAct 替换学习状态机
- 把用户原始 PDF/PPT 提交进本仓库
- 在 M6 未完成时写 `m6-harness-skeleton-plan.md` 并开工实现（用户已暂缓）

## 6. 给 PLAN 维护者的检查清单

更新 `docs/PLAN.md` 时可用，不必把本清单抄进 PLAN：

- [ ] 阶段顺序仍是接口 → 数据源 → 存储 → 计划执行 → 可选 Runner
- [ ] 默认 Runner 仍是学习闭环，ReAct 仍可选
- [ ] 存储默认离线可跑，Qdrant 仍非默认
- [ ] 外部 AI 只看目录摘要，不看全书
- [ ] 用户源在仓库外
- [ ] 无 LLM / 无向量模型时核心路径仍在
- [ ] 招聘对照里的 Grafana/JWT/MCP 没有被写成下一阶段必做

## 7. 结论

后续推进应按 PLAN 已写的 M6–M10 走：先能扩展，再能变大，再能按目标学，最后才允许模型自己选工具。
招聘对照文档用来查漏，不用来排序。

下一步若要开工，应先改 `docs/PLAN.md` 的当前阶段状态，再另写执行计划；不要把本文当成开工许可。