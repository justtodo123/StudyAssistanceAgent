# 运行时契约 · 数据源 / 检索参数 / 错误码 / 质量分层

> 最终计划依据仍是 [`docs/PLAN.md`](../PLAN.md)。本文是跨里程碑的稳定契约，不替代 M6a/M6b 执行计划。
> 创建：2026-08-21 · 维护：契约变更时同步代码、`platform/README.md` 与面试叙事。

现行实现：M0–M5 学习闭环。本文把此前只散落在代码里的约定写成可讲、可测的合同。

## 1. 数据源类型与入库门禁

检索语料是允许名单，不是「磁盘上有 Markdown 就能搜」。

| `source_type` | 含义 | 默认可检索 | 谁产生 |
| --- | --- | --- | --- |
| `human_markdown` | 仓库内人工笔记（默认 pack） | 是（`ingest_status=approved`） | 人工写作 |
| `web_candidate` | 网页抓取候选 | 否 | `tools/crawler` |
| `web_reviewed` | 网页候选经人工审核并显式晋升 | 是 | 人工审核后改 frontmatter / 复制到课程目录 |
| `ai_draft` | 模型生成草稿 | 否 | QA/Quiz/计划等生成结果 |
| `user_registered` | 用户注册源（M7） | 是（注册完成后） | M7 Source 生命周期 |

`ingest_status`：`candidate` / `approved` / `rejected`。缺省按 `human_markdown` + `approved` 处理，保证现有笔记不回退。

**入库门禁（已落地）**

1. crawler 默认写到 `platform/.cache/crawler-candidates/{course}`，不写 `knowledge/{course}`。
2. 未加 `--allow-knowledge-write` 时，禁止写入 `knowledge/`（`knowledge/_inbox/` 除外）。
3. 索引跳过 `_templates/`、`_inbox/`。
4. `source_type` 不在允许名单，或 `ingest_status != approved` 的文件不进入检索。
5. AI 生成内容只出现在 API 响应里，禁止回写为默认知识包。

网页源要进入检索，必须：人工审核 → 精炼成笔记 → `source_type=web_reviewed` 且 `ingest_status=approved` → 放到课程目录或 M7 注册源。这不是 M7 的完整生命周期，只是门禁。

## 2. Embedding / 索引参数表

当前向量检索是 **SQLite 存向量 + 线性余弦扫描**，不是 HNSW/IVF。面试只讲已实现参数；ANN 参数留给 M8。

| 参数 | 当前值 | 可配环境变量 | 作用 |
| --- | --- | --- | --- |
| 嵌入模型 | `BAAI/bge-small-zh-v1.5` | `SA_EMBEDDING_MODEL` | 中文语义向量 |
| 向量归一化 | `true` | `SA_EMBEDDING_NORMALIZE` | `encode(normalize_embeddings=...)` |
| 期望维度 | `512` | `SA_EMBEDDING_DIM` | BGE-small-zh 默认维；入库仍做维度校验 |
| 切块策略 | Markdown `##` 小节 | — | 不以固定 token 窗切块 |
| 最短切片 | `15` 字符 | `SA_CHUNK_MIN_CHARS` | 过滤占位噪音 |
| 向量索引 | `linear_cosine` | `SA_VECTOR_INDEX_TYPE` | 现状；M8 才允许 `hnsw`/`ivf` |
| 向量阈值 | `0.0` | `SA_VECTOR_THRESHOLD` | 余弦下限，默认不过滤 |
| BM25 候选池 | `0`（全库） | `SA_BM25_POOL` | `0` 避免扩库后静默丢文件 |
| 返回条数 | `5` | `SA_TOP_K` | 检索/问答默认 top_k |
| RRF `k` | `60` | `SA_RRF_K` | 多路融合常数 |
| LLM 温度 | `0.3` | `SA_LLM_TEMPERATURE` | 生成稳定性 |
| LLM 超时 | `60s` | `SA_LLM_TIMEOUT_S` | 单次生成超时 |
| 向量开关 | CI/演示 `false`；代码默认 `true` | `SA_USE_VECTOR` | 离线路径必须显式关闭 |

M8 才讨论的索引参数（现在不要当成已实现）：HNSW `M` / `efConstruction` / `efSearch`，IVF `nlist` / `nprobe`，FTS5 tokenizer。

## 3. 稳定错误码

HTTP 状态码是传输层；`detail.code` 才是契约。

```json
{"code": "SESSION_NOT_FOUND", "message": "...", "retryable": false}
```

| code | HTTP | retryable | 何时出现 |
| --- | --- | --- | --- |
| `WORKBENCH_UNAVAILABLE` | 404 | 否 | 工作台静态页缺失 |
| `SESSION_NOT_FOUND` | 404 | 否 | 学习会话不存在 |
| `ILLEGAL_SESSION_STATE` | 409 | 否 | 非法状态转换（如已结束后再答题） |
| `SOURCE_INGEST_DENIED` | 403 | 否 | crawler 试图写入默认知识包 |
| `VECTOR_DIMENSION_MISMATCH` | 500 | 否 | 查询/入库向量维不一致 |
| `LLM_NOT_CONFIGURED` | 503 | 否 | 预留：强制 LLM 路径但未配置 key（当前 QA 降级，不抛） |
| `LLM_GENERATION_FAILED` | 503 | 是 | 预留：生成失败且调用方要求失败而非降级 |
| `TOOL_PERMISSION_DENIED` | 403 | 否 | 预留：M6b 只读 preview 拒绝写工具 |
| `BUDGET_EXCEEDED` | 429 | 是 | 预留：M6b 步数/token/cost 预算耗尽 |

已落地的是会话 404/409 和工作台 404。其余码先入库，M6b/M7 按表使用，不另起名字。

## 4. 生成质量分层与延迟分位数

**生成分层（QA `generation_layer`）**

| 层 | 含义 | 何时 |
| --- | --- | --- |
| `grounded_llm` | 模型基于检索片段生成，且有出处 | `use_llm` 且调用成功、有 sources |
| `note_summary` | 本地笔记摘要，不是模型创作 | 无 key、关闭 LLM、或生成失败降级 |
| `no_hit` | 知识库无命中 | sources 为空 |

这不是 LLM-as-judge。当前质量信号是：层标记 + 出处列表 + 离线 Recall@3。忠实度/引用覆盖率评测仍属 M10 Agent 评测，不提前宣称。

**延迟分位数**

`/health` 在进程内样本上暴露：

- `avg_latency_ms`
- `p50_latency_ms`
- `p95_latency_ms`
- `p99_latency_ms`
- `sample_count`（最多 200，重启清零）

这是诊断字段，不是 SLO 承诺。个人单机没有 P99 SLA；面试讲「用分位数看尾延迟，而不是只看平均」。

## 5. 与 PLAN / 面试的同一口径

| 问题 | 现行口径 |
| --- | --- |
| 现在是不是 ReAct Agent？ | 不是。正式路径是学习状态机。 |
| M6b 做什么？ | 独立只读原生工具调用 preview，不接管 `study-sessions`，不写学习状态。 |
| 完整自主 Runner 何时？ | M10，且仍是可选执行器，不替换教学状态机。 |
| 网页/AI 算不算知识源？ | 网页只产生候选；AI 只产生响应。能检索的只有审核后的笔记/注册源。 |
| 向量库是不是 Qdrant？ | 现在是 SQLite + 线性扫描。LanceDB/Qdrant 是 M8。 |

招聘对照原文 [`docs/interview/StudyAssistanceAgent_requirement.md`](../interview/StudyAssistanceAgent_requirement.md) 是 2026-08-20 的调查快照，**不是**执行计划。
