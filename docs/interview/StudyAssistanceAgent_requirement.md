> **地位**：2026-08-20 招聘对照调查快照，**不是执行计划**。
> 现行口径以 [docs/PLAN.md](../PLAN.md) 和 [docs/standards/runtime-contracts.md](../standards/runtime-contracts.md) 为准。
> 其中「M6b 上 ReAct / 用 JSON 冒充 Function Calling / 187 项测试」等表述已过期：M6b 是只读原生工具调用 preview；完整自主 Runner 在 M10；测试数量以 pytest 收集为准。

StudyAssistanceAgent
与 Agent 招聘要求对齐分析报告
—— 参考 ai-agent-platform 架构 · 面向 2027 届秋招 Agent 开发岗

一、结论摘要
基于对 StudyAssistanceAgent 源码的逐模块盘点，对照参考项目 ai-agent-platform（Spring Boot 3 + LangChain4j）的架构能力，以及与近期 Agent 招聘要求（ReAct 循环、工具调用、RAG、记忆、评估、可观测、成本控制）逐项对齐，核心结论：
现状：你的项目已具备「多路召回 RAG + 学习会话编排 + 评测 + 工程化」这一套扎实底座，测试体系（187 项）与文档完整度甚至优于参考项目。
核心差距：但它本质是「RAG 问答 + 确定性编排」，不是「LLM 自主决策的 Agent」。与招聘要求差距最集中的三个模块是：Agent 推理循环（ReAct）、真正的工具调用（Function Calling/注册表）、Agent 全链路评估。
对齐方式：参考 ai-agent-platform 不必迁移到 Java——它的价值在于提供「模块清单」：把它的 ReAct 循环、语义缓存、工具注册表、多模型路由、熔断重试、可观测、限流/成本预算等能力，用 Python 在现有 FastAPI 代码上增量补齐即可。
二、项目现状 vs ai-agent-platform 能力对照
能力维度	ai-agent-platform（参考）	StudyAssistanceAgent（现状）	差距
ReAct 推理循环	自研 ReAct（Thought-Action-Observation）+ 死循环防护 + 超时	无 LLM 自主循环，仅确定性状态机（create→qa→quiz→evaluate→review-log）	大：核心缺口
工具调用	工具注册表自动发现（数据库查询 + 外部 API）	有 tool_trace 编排，但无注册表、无 Function Calling、工具为硬编码串联	大
多路召回 RAG	Milvus 向量 + BM25 + RRF 融合（k=60）	BM25 + BGE 向量 + RRF（k=60，同参数）	小：仅缺 Milvus 向量库
高级 RAG	Adaptive RAG（Query Router/查询改写/Self-RAG）	无查询改写、无自适应检索、无 Self-RAG	中
语义缓存	embedding 余弦相似度缓存（0.92/24h）降本	仅结果 LRU 缓存（128 条）	中：缺语义级缓存
多模型路由	策略模式切换 DeepSeek/通义/豆包/Ollama + 降级	单 OpenAI 兼容接口 + 降级笔记摘要	中
熔断与重试	Resilience4j（熔断 50%/30s + 重试 3 次/2s）	仅 try/except 降级	中：缺韧性
可观测	Prometheus/Grafana/Micrometer	进程内指标 + 结构化日志 + /health	中：缺导出
安全与成本	JWT + 限流(30/min) + Token 成本预算	无认证、无限流、无成本预算	中：缺
评测	RAG 评测 + JMeter 压测 + 质量基线	90 题 Recall@3 ≥0.92 + 延迟基线	小：缺 Agent 级评估
流式输出	SSE	SSE（/api/v1/qa/stream）	已具备
会话记忆	Redis 24h TTL + 长会话摘要压缩	SQLite 持久化 + 遗忘曲线	小：缺摘要压缩
测试/CI	193 测试 + JaCoCo 45% + CI/CD + Docker Compose	187 测试 + GitHub Actions（离线）	小：缺 Docker Compose
三、与招聘要求对齐的差距矩阵
按前面整理的 13 个知识模块，对齐到本项目现状，标注优先级（P0 必须 / P1 建议 / P2 加分）：
招聘要求	本项目现状	对齐动作	优先级
B1 Agent 循环（ReAct/Agentic Loop）	无	新增 ReAct 推理循环：Thought→Action→Observation→Final Answer + 死循环防护 + 超时	P0
B2 工具调用（Function Calling/注册表/MCP）	tool_trace 硬编码编排	抽象工具注册表，用 Function Calling 驱动 LLM 自主选择工具（如：检索/出题/记复习/查面经）	P0
C2 高级 RAG（查询改写/自适应/语义缓存）	无	加查询改写 + 语义缓存（embedding 余弦），复用现有 BGE	P1
D1 Agent 评估体系	仅 RAG Recall@3	加 Agent 全链路评估：任务成功率/工具调用准确率/成本/延迟	P1
多模型路由 + 熔断重试	单模型 + try/except	策略模式接入多模型（DeepSeek/通义/Ollama）+ 熔断重试降级	P1
D2 可观测性	进程内指标	指标导出为 Prometheus 格式 + 简单 Grafana	P2
D3 限流 / Token 成本预算	无	加 Redis 或进程内限流 + Token 消耗估算与上限	P2
D4 协议（MCP/A2A）	无	（了解即可，可选）暴露 MCP 工具描述	P2
B3 记忆（会话摘要）	遗忘曲线（长期记忆）	加会话摘要压缩/滑动窗口（工作记忆）	P2
四、对齐改造方案（按优先级）
P0-1 新增 ReAct 推理循环（最关键，直接补齐"Agent"属性）
在现有 qa 服务之上，新增 react_agent 模块，把「检索→生成」升级为「LLM 自主推理循环」：
实现 ReAct 循环：Thought → Action（调用工具）→ Observation → Final Answer，用结构化 JSON 让 LLM 输出动作。
内置安全护栏（参考参考项目）：最大步数限制（如 8 步）、单步超时（如 30s）、重复观测熔断（同一动作+观测出现 N 次即终止）。
复用现有服务为工具：search（多路召回）、quiz（出题）、review_log（记复习）注册为工具，供 LLM 调用。
保留现有确定性会话作为"降级路径"，无 LLM 时仍可离线跑。
P0-2 工具注册表 + Function Calling
把目前硬编码的工具轨迹抽象成统一注册表，形成可扩展、可讲深度的工具体系：
定义 Tool 协议（name/description/parameters/execute），用装饰器注册（@tool("retrieve", "检索知识库")）。
新增 generate_tool_call 端点：输入问题 → LLM 返回工具调用 → 执行 → 反馈 observation → 循环。
工具示例：retrieve（多路召回）、quiz（出题）、review_due（待复习）、search_interview（面经检索）。
P1-1 语义缓存（降本）
在现有结果缓存基础上，加 embedding 语义缓存：
用现有 BGE 模型计算问题 embedding，与缓存问题做余弦相似度，超过阈值（如 0.92）直接返回历史答案。
缓存带 TTL（如 24h），可统计命中率（已有 metrics 框架可扩展 cache_hit）。
P1-2 查询改写 + Agent 全链路评估
查询改写：对模糊/口语化问题，先用 LLM 改写为标准检索 query 再做 RAG（可作 P1）。
Agent 评估：扩展 run_evaluation.py，新增工具调用成功率、任务完成率、成本（token 数）、延迟四类指标，形成 Agent 评测集（如"给一道题→能否自主检索并出题"）。
P1-3 多模型路由 + 熔断重试
参考参考项目的 Resilience4j 模式，在 Python 侧用轻量实现：
策略模式封装模型提供方（DeepSeek/通义/Ollama），配置化切换 + 主模型失败自动降级到本地 Ollama。
实现简单熔断（失败率阈值触发熔断，冷却后恢复）+ 重试（如 2 次，指数退避）。
P2（可选加分）可观测导出 / 限流成本 / 会话摘要 / MCP
把 metrics 导出为 Prometheus 文本格式（/metrics 端点），配简单 Grafana 面板。
进程内固定窗口限流 + Token 消耗估算与预算上限（低成本实现）。
长会话滑动窗口 + 摘要压缩（工作记忆）。
可选：按 MCP 规范暴露工具描述，面试可讲支持 MCP 协议。
五、每项改造的面试可讲点
改造项	面试时怎么讲	对应考点
ReAct 循环	"我自研了 ReAct 循环，带最大步数/超时/重复观测熔断三道防御"	B1 Agentic Loop、死循环防御
工具注册表 + Function Calling	"工具用注册表+装饰器注册，LLM 自主选择调用，tool_trace 记录完整轨迹"	B2 工具调用
语义缓存	"用 embedding 余弦相似度做语义缓存，命中直接返回，降本可量化"	D3 成本、C2 语义缓存
多模型路由+熔断	"策略模式切模型，主模型失败自动降级本地，熔断避免雪崩"	韧性、多模型
Agent 全链路评估	"从 Recall@3 扩展到任务成功率/工具调用准确率/成本/延迟"	D1 Agent 评估
可观测/限流	"指标导出 Prometheus，加限流与 Token 预算"	D2/D3
六、建议执行路线
阶段	任务	验收标准
第1步（P0）	实现 ReAct 循环 + 工具注册表 + Function Calling	LLM 能自主"检索→出题→评估"完成一次学习闭环
第2步（P0）	加安全护栏（步数/超时/重复熔断）+ 降级路径	无 LLM 仍可离线跑，现有 187 测试全绿
第3步（P1）	语义缓存 + 查询改写	命中率指标可统计，Recall 评测不退化
第4步（P1）	Agent 全链路评估集	输出成功率/成本/延迟报告
第5步（P1）	多模型路由 + 熔断重试	配置化切换 + 故障降级演示
第6步（P2，可选）	Prometheus 导出 / 限流 / 会话摘要 / MCP	可观测 + 成本 + 协议加分项

说明：本报告基于对 StudyAssistanceAgent 源码（platform/app 各模块、tools/run_evaluation.py、docs/interview/README.md 等）的实际调研，及 ai-agent-platform（888newstep）README/架构、近期 Agent 招聘 JD 与面试复盘资料综合分析。改造均建议在现有 Python/FastAPI 代码上增量进行，不迁移到 Java。