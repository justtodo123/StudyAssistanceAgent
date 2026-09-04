# Platform — FastAPI RAG 后端

> StudyAssistanceAgent 的 Python 后端服务。提供学习工作台、知识库检索、带出处问答、SSE 流式输出、
> 测验、复习计划/排程和服务端学习会话。

## 架构

```
提问 / 工作台 GET /
  → MultiRecallService（course 过滤前置）
       ├─ 路1: SqliteVectorStore（BGE 可选；持久化 + 线性余弦）
       │        └─ SA_VECTOR_STORE=linear 时使用内存 LocalVectorStore
       └─ 路2: Bm25Search（bigram 关键词）
    → RRF 融合（k=60）+ 文件级去重
    → QaService: LLM 生成 | 降级笔记摘要
    → StudySessionService: QA → Quiz → 评估 → review-log
    → FastAPI 工作台与 /api/v1/{search,qa,qa/stream,quiz,review-plan,review-log,review-due,study-sessions}
```

**M1d 优化**：课程过滤前移至检索阶段（避免无关课程占位）、RRF 结果按文件去重（同文件只保留最高分 chunk）、摘要截断在句子边界。

**M4 优化**：无明确课程过滤的学习问题优先返回课程笔记，面试问题优先返回面经条目，README 导航片段不会挤占有效知识条目。

## 目录结构

```
platform/
├── README.md              # 本文件（API 文档与启动指南）
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI 入口：search/qa/quiz/review/study-sessions + 工作台
│   ├── models.py          # Pydantic 领域模型（RetrievalChunk, SearchRequest, QaRequest 等）
│   ├── config.py          # 环境变量配置（dotenv → 常量）
│   ├── retrieval.py       # 多路召回 + RRF 融合（MultiRecallService）
│   ├── bm25.py            # BM25 关键词检索（中文 bigram + 英文整词分词）
│   ├── vector_store.py    # SQLite/内存向量后端（BGE 可选；当前均为线性余弦）
│   ├── qa.py              # 问答服务（LLM 生成 / 降级笔记摘要）
│   ├── knowledge_index.py # 知识库索引兼容视图（Markdown 快照 + JSON 缓存）
│   ├── markdown_parser.py # 共享 Markdown frontmatter/H2 解析原语
│   ├── protocols.py       # M6a provider-neutral harness 契约
│   ├── llm_client.py      # M6b provider-neutral Anthropic Messages adapter
│   ├── tool_registry.py   # M6b 只读工具 allowlist、schema 与结果投影
│   ├── preview_agent.py   # M6b 有限 native tool-use loop 与预算/终止语义
│   ├── preview_service.py # M6b 独立认证、容量与 HTTP preview surface
│   ├── source_registry.py # M7-1 Source Registry 生命周期控制面（独立 SQLite）
│   ├── source_manifest.py # M7 用户源文件 manifest、格式接纳与 canonical digest
│   ├── parser_matrix.py   # M7 五格式冻结 parser contract 与 fail-closed 解析
│   ├── normalized_document.py # M7 跨格式 normalized units、chunks 与缓存
│   ├── user_source_snapshot.py # M7 source-local FULL candidate 与原子发布
│   ├── user_source_sync.py # M7 source-local FULL/INCREMENTAL sync worker
│   ├── source_delete.py   # M7 source-local tombstone/hard-delete 合同
│   ├── source_isolation.py # M7 查询前 owner-only 隔离门
│   ├── fts5_tokenizer.py  # M7 jieba==0.42.1 FTS5 tokenizer 合同
│   ├── user_source_fts5.py # M7 generation-bound SQLite FTS5 索引
│   ├── user_source_vector.py # M7 generation-bound source-local vector 索引
│   ├── source_offline.py  # M7 离线 fail-closed 校验与显式 FULL repair
│   ├── user_source_search.py # M7 用户源 Search/cache/RRF/provenance overlay
│   ├── retrieval_index.py # M6a 默认包快照到旧 RetrievalChunk 的兼容适配器
│   ├── sources/           # 默认知识包与静态额外源适配器（见子目录 README）
│   ├── combined_snapshot.py # 默认包 + 启动期额外源的不可变组合快照
│   ├── snapshot_publisher.py # 原子发布 CURRENT/PREVIOUS 与 last-good
│   ├── worker_topology.py # 单进程 / 单 worker service.lock 门禁
│   ├── source_config.py   # SA_EXTRA_SOURCES 与资源上限解析
│   ├── tools/             # 确定性 Retrieve/Quiz/ReviewDue 适配器
│   ├── runners/           # StateMachineRunner 薄适配
│   ├── source_policy.py   # 数据源类型与入库门禁
│   ├── errors.py          # 稳定错误码
│   ├── observability.py   # 进程内延迟/缓存指标与结构化日志
│   ├── review_plan.py     # 复习计划服务（分日学习计划生成）
│   ├── quiz.py            # 测验生成服务（例题+评测集+概念模板三数据源）
│   ├── review_scheduler.py # 复习排程服务（遗忘曲线间隔重复）
│   ├── study_session.py   # 学习会话编排（状态机 + 工具轨迹）
│   ├── learning_store.py   # SQLite 会话/复习仓储
│   └── static/workbench/    # 最小学习工作台（HTML/CSS/JS）
├── tests/
│   ├── test_retrieval.py  # 检索链路冒烟测试（6 个用例）
│   ├── test_review_plan.py # 复习计划测试（8 个用例）
│   ├── test_quiz.py       # 测验生成测试（11 个用例）
│   ├── test_review_scheduler.py # 复习排程测试（9 个用例）
│   └── test_study_assistant.py # 多轮工具编排集成测试（6 个用例）
├── requirements.txt       # 核心依赖
├── requirements-dev.txt   # 开发依赖（pytest、httpx2、PyYAML）
└── .env.example           # 环境变量模板（复制为 .env 后修改）
```

平台原始测试共 40 项，历史 M5 验收时已全部通过；根目录阶段化测试、crawler 前置测试和回归套件见
`../tests/TEST_PLAN.md`。文档中的历史通过数不代表本次修改已重新执行完整测试。

## API 端点

### 学习工作台

```
GET /
```

启动后端后打开 `http://127.0.0.1:8000/`，首屏即为学习工作台。页面只调用正式会话 API 和待复习接口：

- `GET /api/v1/review-due`
- `POST /api/v1/study-sessions`
- `GET /api/v1/study-sessions/{id}`
- `POST /api/v1/study-sessions/{id}/answers`

可完成今日待复习、主题讲解、单题作答、反馈和复习记录，不复制服务端状态机。

### 健康检查

```
GET /health
```

响应示例：
```json
{
  "status": "UP",
  "vector_engine": "sqlite",
  "knowledge_root": "knowledge-pack",
  "index_size": 123,
  "cache_status": "warm",
  "avg_latency_ms": 0.06,
  "p50_latency_ms": 0.05,
  "p95_latency_ms": 0.12,
  "p99_latency_ms": 0.20,
  "sample_count": 12,
  "llm_configured": false
}
```

字段说明：
- `vector_engine`：当前向量后端；可为 `linear` / `sqlite`，不可用时带 `-unavailable` 后缀。
- `knowledge_root`：默认知识包的稳定逻辑标识 `knowledge-pack`，不返回宿主机目录路径。
- `index_size`：当前索引中的有效 Markdown 切片数。
- `cache_status`：进程内最近一次索引/检索缓存状态，取值为 `cold`、`warm` 或 `unknown`。
- `avg_latency_ms`：当前进程保留的最近操作样本平均耗时（毫秒）；服务重启后重新统计。
- `p50_latency_ms` / `p95_latency_ms` / `p99_latency_ms`：同一批样本的分位数；不是 SLO。
- `sample_count`：参与统计的样本数，最多 200。
- `llm_configured`：是否配置 LLM API key 的布尔值，不返回 key 本身。

### 可观测性与日志

搜索和 QA 会通过 `app` logger 输出单行 JSON 结构化日志。日志只包含安全元数据：
`event`、`duration_ms`、`result_count`，以及可选的 `course`、`mode`、`cache_hit`。
问题正文、检索内容、API key、密码、token 和 Authorization 不会写入日志。

检索服务使用有界的进程内结果缓存，键按 scope + generation 隔离：`DEFAULT_ONLY` 使用 default generation，
`DEFAULT_PLUS_EXTRAS` 使用 combined generation。额外源变更不会清空默认包缓存。知识库索引使用
`.cache/knowledge_index.json` 与 generation 元数据缓存。内容变更导致对应 generation 改变时，旧索引视图和结果缓存不会复用。
服务启动只允许一个进程、一个 uvicorn worker；锁文件为 `platform/.cache/index/service.lock`，
含 pid/nonce/started_at。`WEB_CONCURRENCY`/`UVICORN_WORKERS` 必须为 1 或未设置；不支持 `SA_INDEX_READONLY`。
`/health` 的延迟和缓存字段用于运行时诊断，不作为持久化监控指标。
完整参数表、错误码和生成分层见 [docs/standards/runtime-contracts.md](../docs/standards/runtime-contracts.md)。

### 检索

```
POST /api/v1/search
Content-Type: application/json

{
  "question": "进程调度算法有哪些",
  "top_k": 5,
  "course": "os",
  "use_vector": true
}
```

响应字段：
- `mode`: `"hybrid"`（向量+BM25）或 `"keyword-only"`（仅 BM25 或向量不可用时的降级）
- `results`: 切片列表，每条含 `file`（出处）、`title`、`course`、`score`、`content` 等

### 问答

```
POST /api/v1/qa
Content-Type: application/json

{
  "question": "什么是虚拟内存",
  "top_k": 5,
  "course": null,
  "use_vector": true,
  "use_llm": false
}
```

- `use_llm: true` 时若配置了 LLM，则调用 AI 生成带出处的回答
- `use_llm: false` 或 LLM 不可用/失败时，自动降级为笔记摘要（结构化展示检索到的知识库片段）
- 响应含 `generation_layer`：`grounded_llm` / `note_summary` / `no_hit`

### 流式问答（SSE）

```
POST /api/v1/qa/stream
Content-Type: application/json

{
  "question": "分页和分段的区别",
  "use_llm": false
}
```

响应为 SSE（`text/event-stream`）：第一条 `data` 为来源元数据，后续每条为正文段落 `delta`，最后以 `[DONE]` 结束。

### 测验生成

```
POST /api/v1/quiz
Content-Type: application/json

{
  "course": "os",
  "count": 5,
  "difficulty": "中等",
  "topics": ["进程", "调度"]
}
```

- `course`：必填，课程简称（os / ds / co）
- `count`：可选，题目数量（1-20），默认 5
- `difficulty`：可选，难度筛选（入门 / 中等 / 进阶）
- `topics`：可选，按标签筛选，如 `["进程", "调度"]`

响应字段：
- `questions`: 题目列表，每题含 `question`（题干）、`type`（example/retrieval/concept）、`answer`（参考答案，仅 example 有）、`source_file`（来源）、`tags`
- `summary`: 汇总（total_pool / filtered / by_type）

三种题型：
- **example**：经典例题，从知识条目 `## 经典例题` 提取，含完整参考答案
- **retrieval**：检索题，来自评测集，无答案，需查阅知识条目验证
- **concept**：概念题，从 tags 模板生成，鼓励自行查阅

### 复习计划

```
POST /api/v1/review-plan
Content-Type: application/json

{
  "course": "os",
  "target_date": "2026-09-01",
  "hours_per_day": 2.0,
  "plan_name": "os-midterm"
}
```

- `course`：必填，课程简称（os / ds / co）
- `target_date`：可选，目标日期（YYYY-MM-DD），默认 14 天后
- `hours_per_day`：可选，每天可用学时（0.5-8.0），默认 2.0
- `plan_name`：可选，计划名称，默认 `{course}-plan`

响应字段：
- `days`: 分日任务列表，每天含多个 `PlanTask`（file / title / difficulty / estimated_minutes / priority / tags）
- `summary`: 汇总（total_entries / by_difficulty / tip）
- `total_hours`: 预计总学时

### 记录复习

```
POST /api/v1/review-log
Content-Type: application/json

{
  "file": "knowledge/os/process-management.md",
  "course": "os"
}
```

- `file`：必填，知识条目文件路径
- `course`：可选，课程简称

响应：记录复习次数、计算下次复习时间（间隔序列：1→2→4→8→16→32 天）

### 查询待复习

```
GET /api/v1/review-due?course=os
```

- `course`：可选，按课程筛选

响应字段：
- `entries`: 待复习条目列表，含 `days_overdue`（逾期天数）、`interval_days`（当前间隔）、`review_count`（累计次数）
- `summary`: 汇总（total_tracked / overdue / due_today / upcoming）

### 学习会话

```
POST /api/v1/study-sessions
Content-Type: application/json

{
  "topic": "死锁",
  "course": "os",
  "question_count": 1,
  "use_llm": false
}
```

```
GET /api/v1/study-sessions/{session_id}
POST /api/v1/study-sessions/{session_id}/answers
Content-Type: application/json

{
  "answer": "互斥、占有并等待、不可剥夺、循环等待"
}
```

- 创建会话时编排 QA 检索与讲解，再出 1 至 2 道题。
- 答案评估默认使用确定性规则；不配置 LLM 时完整链路仍可运行。
- 答对则完成并记录复习；答错一次给提示并重试；连续两次答错后返回完整参考并结束。
- 响应包含 `state`、`sources`、`attempt_count`、`score`、`review` 和 `tool_trace`。
- 非法状态转换返回 409，未知会话返回 404；`detail` 为 `{code, message, retryable}`。
- 会话、答题记录和复习历史默认写入 `platform/.cache/learning_state.sqlite3`；服务重启后可按 `session_id` 恢复未完成会话。现有 `review_history.json` 仍可兼容读取。

### Agent Preview（M6b，默认关闭）

M6b 提供独立的只读 native tool-call preview，不替代正式学习会话，也不调用
`StateMachineRunner` 或写入学习状态。只有进程启动前显式设置
`SA_AGENT_PREVIEW_ENABLED=true` 且 `SA_AGENT_PREVIEW_TOKEN` 至少包含 32 个 UTF-8 字节时，才注册：

```
POST /api/v1/agent-preview
Authorization: Bearer <preview-token>
Content-Type: application/json

{
  "prompt": "解释进程调度",
  "learner_id": "demo"
}
```

Preview 使用服务端 `ANTHROPIC_API_KEY` 调用固定官方 Anthropic endpoint 和
`claude-opus-5`，采用 adaptive thinking、low effort 与原生 `tool_use/tool_result`。
请求可使用 `retrieve`、`quiz_preview`、`review_due` 三个显式 allowlist 只读工具；检索范围为
`DEFAULT_PLUS_EXTRAS`，而正式学习会话仍固定为 `DEFAULT_ONLY`。

响应为不含原始 provider 数据的 bounded envelope：

```json
{
  "status": "completed",
  "termination_reason": "completed",
  "answer": "……",
  "sources": [],
  "agent_trace": [],
  "usage": {
    "input_tokens": 12,
    "output_tokens": 8,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "estimated_cost_usd": 0.00042
  },
  "model_turn_count": 1,
  "tool_call_count": 0
}
```

总 deadline、模型轮次、工具调用、token、费用、结果和答案均有硬上限；每进程最多 2 个活动
preview，过载返回 `429 PREVIEW_OVERLOADED`（`Retry-After: 1`）。未认证返回 `401`，请求校验失败
返回不回显输入的 `422 PREVIEW_REQUEST_INVALID`，已认证但缺少 Anthropic key 返回结构化 `503`
`PREVIEW_PROVIDER_NOT_CONFIGURED`。loop 内的 provider、工具、预算和取消失败以稳定
`termination_reason` 返回，不暴露 provider 原始异常。

同步只读工具运行在默认线程池中；Python 无法安全强杀已经开始执行的非协作同步函数。因此请求超时或取消会立即停止
Preview 的 model/tool/retry continuation，不追加晚到的 tool result，也不写回领域状态，但实际工具工作槽会一直占用到该
函数自然返回或抛错后才释放。请求容量槽与实际工具工作槽是两层独立限制。

Preview trace 只在当前认证响应中短暂存在，标识使用进程内 HMAC；日志、trace、错误和持久化不包含
prompt、thinking、原始参数、知识正文、凭据、宿主绝对路径或 provider 原始响应。为完成 preview，
prompt 与受限工具结果会发送给 Anthropic；上述“不泄漏”约束针对本地日志、响应中的 trace/错误边界、OpenAPI、
持久化和未授权边界。授权响应的 `answer` 可能包含模型生成内容。所有成功及失败路径都不创建 session、不提交答案、
不写 review/mastery/source 状态。

### Source Registry 与 source-local FULL/INCREMENTAL/delete/isolation（M7，独立控制面）

M7-1 新增 `app/source_registry.py`，实现 `sa.source.lifecycle.v1` 的版本化 Source 控制面：canonical
`user-{UUIDv7}` 身份、16 条合法生命周期边、expected-version CAS、不可变 `SourceRevision`、append-only
`AuditEvent`、owner-only 隔离和完整 schema manifest fail-closed。五类 lifecycle record 均已具备持久化与重启读取，
所有生命周期写入与审计在独立 SQLite 事务中完成；`SyncRun` 现承载 request/run、checkpoint、heartbeat 与 cancel 标记。

同一 M7 局部切片还提供 `source_manifest.py`、`parser_matrix.py`、`normalized_document.py`、
`user_source_snapshot.py`、`user_source_sync.py`、`source_delete.py`、`source_isolation.py`、`fts5_tokenizer.py`、`user_source_fts5.py`、`user_source_vector.py` 与 `source_offline.py`：支持用户源的文件级 canonical manifest、Markdown/纯文本/PDF/PPTX/DOCX 五格式
冻结 parser contract、统一 normalized document/chunk identity，已注册单源的离线 FULL candidate、校验和、
last-good 与 `CURRENT`/`PREVIOUS` convenience pointers，M7-2 起已发布 snapshot 绑定 generation/`manifest_digest` 且进程内 LRU 上限 16，以及受限 INCREMENTAL、request/run 幂等、单 active run、
cancel/retry/checkpoint/recovery，以及 tombstone/read barrier、索引/cache 不可读传播、30 天 hard-delete receipt 与查询前隔离过滤。FULL/INCREMENTAL/delete/isolation 只生成 source-local 内部工件；lifecycle 的
immutable revision 才是 published generation 的权威，且重复请求与无变化 INCREMENTAL 对同一 generation 幂等。

默认启动仍不创建 Source Registry。Search/QA 在请求携带可选 `principal_id` 且 registry 已存在时，才会懒加载用户源 FTS5+vector overlay 并与默认/extra 结果 RRF 融合；公开出处为 `user://{source_id}/{logical_uri}`。M6b preview、Quiz、Review Plan 与 study-sessions 不接收该 overlay。用户源 vector 与 FTS5 绑定同一 published generation 和 identity-set；缺依赖或元数据不一致时用户源 fail closed，不降级到默认包 keyword-only。不构成 M7 exit。M6a 静态额外源、默认 pack、学习状态 SQLite 与 M6b preview 均保持原契约。

## 配置

复制 `.env.example` → `.env`，按需修改：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SA_KNOWLEDGE_ROOT` | `../knowledge` | 知识库根目录路径 |
| `SA_TOP_K` | `5` | 检索返回数量 |
| `SA_BM25_POOL` | `0` | BM25 候选池大小（`0`=全库检索，个人规模下推荐） |
| `SA_USE_VECTOR` | `true` | 是否启用向量检索 |
| `SA_VECTOR_STORE` | `sqlite` | 向量后端；`linear` 使用内存 `LocalVectorStore` |
| `SA_VECTOR_STORE_PATH` | `platform/.cache/vector_store.sqlite3` | 默认 `SqliteVectorStore` 持久化路径 |
| `SA_EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | BGE 嵌入模型名 |
| `SA_EMBEDDING_NORMALIZE` | `true` | 向量 L2 归一化 |
| `SA_EMBEDDING_DIM` | `512` | BGE-small-zh 期望维度（入库仍校验） |
| `SA_CHUNK_MIN_CHARS` | `15` | 过短切片丢弃 |
| `SA_VECTOR_THRESHOLD` | `0.0` | 余弦下限 |
| `SA_VECTOR_INDEX_TYPE` | `linear_cosine` | 当前索引类型；ANN 属于 M8 |
| `SA_RRF_K` | `60` | RRF 融合常数 |
| `SA_LLM_BASE_URL` | — | LLM API 地址（OpenAI 兼容） |
| `SA_LLM_API_KEY` | — | LLM API 密钥 |
| `SA_LLM_MODEL` | — | LLM 模型名（如 `deepseek-chat`） |
| `SA_LLM_TEMPERATURE` | `0.3` | 生成温度 |
| `SA_LLM_TIMEOUT_S` | `60` | 单次生成超时（秒） |
| `SA_LEARNING_STORE_PATH` | `platform/.cache/learning_state.sqlite3` | 学习会话与复习历史 SQLite |
| `SA_SOURCE_REGISTRY_PATH` | `platform/.cache/source_registry.sqlite3` | M7-1 独立 Source Registry；默认启动路径暂不创建 |
| `SA_USER_SOURCE_CACHE_PATH` | `platform/.cache/user-sources` | M7 用户源 snapshot/FTS5/vector 缓存；仅在 Search/QA 提供 principal 且 registry 已存在时懒加载 |
| `SA_INDEX_CACHE_PATH` | `platform/.cache/index` | 组合快照与 `service.lock` |
| `SA_EXTRA_SOURCES` | `[]` | 启动期静态额外 Markdown 源，最多 3 个；只进 Search/QA |
| `SA_EXTRA_SOURCES_STRICT` | `true` | 额外源失败时拒绝整次发布 |
| `SA_EXPECTED_DEFAULT_PACK_REVISION` | 空 | 默认包大幅缩减时的精确 revision 确认 |
| `SA_AGENT_PREVIEW_ENABLED` | `false` | 启动期注册只读 Agent Preview；默认路由与 OpenAPI 均不存在 |
| `SA_AGENT_PREVIEW_TOKEN` | 空 | Preview Bearer secret；启用时至少 32 个 UTF-8 字节 |
| `ANTHROPIC_API_KEY` | 空 | Preview 专用服务端 Anthropic 凭据；不复用 `SA_LLM_API_KEY` |
| `SA_AGENT_PREVIEW_DEADLINE_SECONDS` | `45` | 请求总 deadline；只能收紧 |
| `SA_AGENT_PREVIEW_MODEL_TIMEOUT_SECONDS` | `20` | 单次模型 timeout；只能收紧 |
| `SA_AGENT_PREVIEW_TOKEN_COUNT_TIMEOUT_SECONDS` | `3` | 单次 token count timeout；只能收紧 |
| `SA_AGENT_PREVIEW_TOOL_TIMEOUT_SECONDS` | `2` | 单次只读工具 timeout；只能收紧 |
| `SA_AGENT_PREVIEW_MAX_MODEL_TURNS` | `4` | 最大模型轮次；只能收紧 |
| `SA_AGENT_PREVIEW_MAX_TOOL_CALLS` | `3` | 最大工具调用数；只能收紧 |
| `SA_AGENT_PREVIEW_MAX_INPUT_TOKENS` | `12000` | 累计 provider input token 上限；只能收紧 |
| `SA_AGENT_PREVIEW_MAX_OUTPUT_TOKENS` | `4096` | 累计 provider output token 上限；只能收紧 |
| `SA_AGENT_PREVIEW_MAX_TURN_OUTPUT_TOKENS` | `1024` | 单轮 output token 上限；只能收紧 |
| `SA_AGENT_PREVIEW_MAX_COST_USD` | `0.20` | 冻结价格表估算费用上限；只能收紧 |
| `SA_AGENT_PREVIEW_MAX_PROMPT_BYTES` | `8192` | UTF-8 prompt 字节上限；只能收紧 |
| `SA_AGENT_PREVIEW_MAX_TOOL_RESULT_BYTES` | `12288` | 单项模型可见工具结果字节上限；只能收紧 |
| `SA_AGENT_PREVIEW_MAX_TOTAL_TOOL_RESULT_BYTES` | `24576` | 累计模型可见工具结果字节上限；只能收紧 |
| `SA_AGENT_PREVIEW_MAX_ANSWER_BYTES` | `8192` | 最终答案 UTF-8 字节上限；只能收紧 |

Preview 的 model、官方 endpoint、TLS 校验、tool allowlist、capacity=2、应用级最大一次 retry、thinking、
价格表和 trace retention 均不可由环境变量覆盖。配置布尔值、数字或“只能收紧”约束无效时启动即 fail closed。

## M6/M7 边界

M6a 已完成 Source/存储职责/Tool/Runner 薄适配、启动期静态额外源、default/combined generation 分离、单进程拓扑门禁和文档收口。
M6b 已实现独立、默认关闭、只读的原生工具调用 preview，并完成 closeout 收口，当前为 `ADMITTED / COMPLETE`。
它不接管 `/api/v1/study-sessions`，不写学习状态，也不新增 `SA_RUNNER=react`。完整自主 Runner、写工具、checkpoint/幂等和 Agent 评测属于 M10。

M7 当前为 `ADMITTED / IN_PROGRESS`。已实施的是独立 Source Registry 加上 source-local manifest、冻结 parser matrix、normalized document、
离线单源 FULL candidate/发布合同、受限 incremental sync worker、已冻结的 source-local delete/isolation/FTS5/vector/offline 合同，以及 Search/QA 可选 principal overlay；阶段测试 `tests/M7/` 当前为 205 项（含 M7-2 snapshot identity/LRU、M7-4 exact-query/query-encode 与 M7-5 READY/CURRENT 指针合同）。M6b preview 仍不含用户源。当前测试与 disposable 1k/3k 证据不构成 M7 exit；`sa.source.benchmark.v1` 的 `m7_exit=true` 也不是阶段退出。
默认 RAG 基线仍为 OS/DS/CO 三课 90 题；Network 30 题为显式运行的扩展集。

## 降级路径

| 场景 | 行为 |
| --- | --- |
| `sentence-transformers` 未安装 | 默认 pack/extras 向量路自动跳过，回退纯关键词（BM25）；M7 用户源查询 fail closed，不降级 |
| LLM API 未配置 | 问答返回笔记摘要，而非 AI 生成 |
| LLM API 调用失败 | 同上，并附带失败提示 |
| Agent Preview 未启用 | 路由不注册，默认 OpenAPI 不出现该端点 |
| Preview 未认证 / 请求无效 | 返回净化后的 401 / 422，不回显 token、prompt 或被拒输入 |
| Preview provider key 缺失 | 认证后返回结构化 503；Search/QA/session 不受影响 |
| Preview 过载 | 最多等待 250 ms，随后返回 429 与 `Retry-After: 1` |
| Preview loop 失败或预算耗尽 | 返回稳定 `terminated` envelope，不降级为正式状态机或写操作 |

**核心原则：保证总是有输出。**

## 可选 BGE 模型（非基础验收前提）

默认演示和 CI 使用 `SA_USE_VECTOR=false`，不访问 Hugging Face，不加载 BGE。

| 项 | 说明 |
| --- | --- |
| 模型名 | `BAAI/bge-small-zh-v1.5`（`SA_EMBEDDING_MODEL`） |
| Hugging Face 缓存 | 默认 `~/.cache/huggingface`，可用 `HF_HOME` 覆盖 |
| 项目向量库 | `platform/.cache/vector_store.sqlite3`（`SA_VECTOR_STORE_PATH`） |

预下载（只需一次，需要网络）：

```bash
./.venv/Scripts/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"
```

离线启动：

```bash
# 无模型：纯 BM25
set HF_HUB_OFFLINE=1
python tools/start_local.py

# 已有缓存：允许向量路但禁止再下载
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
python tools/start_local.py --use-vector
```


## 运行

仓库根目录一条命令启动（默认离线 BM25，不下载模型、不要求 LLM key）：

```bash
python tools/start_local.py          # 启动并等待 /health
python tools/start_local.py --check  # 只做健康检查
```

成功后打开 `http://127.0.0.1:8000/`。演示步骤见 [docs/demo.md](../docs/demo.md)。

```bash
# 安装环境
cd platform
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.txt

# 启动 API / 学习工作台
./.venv/Scripts/uvicorn app.main:app --workers 1   # http://127.0.0.1:8000/

# 跑测试
./.venv/Scripts/python -m pytest tests/ -q
```

> `sentence-transformers` 为可选依赖：安装后自动启用本地 BGE 向量检索；未安装则降级为纯关键词（BM25）检索，功能不断。

## 当前向量存储

默认后端是由 `SA_VECTOR_STORE_PATH` 配置的持久化 `SqliteVectorStore`；设置
`SA_VECTOR_STORE=linear` 可切换到内存 `LocalVectorStore`。两者当前都使用线性余弦检索，ANN、LanceDB 与
Qdrant 属于 M8。索引保存 chunk fingerprint 和 embedding 模型名，知识内容或模型变化时自动重建；编码器
不可用时检索降级为 BM25。

---

*创建：2026-08-11 · 更新：2026-09-04（M7-5 READY/CURRENT 指针一致性；`tests/M7/` 205 项；M7 仍为 `ADMITTED / IN_PROGRESS`）· 维护：随 API/配置变更同步更新*
