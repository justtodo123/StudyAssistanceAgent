# Platform — FastAPI RAG 后端

> StudyAssistanceAgent 的 Python 后端服务。提供知识库检索、带出处问答、SSE 流式输出、复习计划生成和学习工作台。

## 架构

```
提问 → MultiRecallService（course 过滤前置）
         ├─ 路1: LocalVectorStore（BGE 余弦，可选依赖）
         └─ 路2: Bm25Search（bigram 关键词）
      → RRF 融合（k=60）+ 文件级去重
      → QaService: LLM 生成（勒令带出处）| 降级笔记摘要（句子边界截断）
      → FastAPI /api/v1/{search, qa, qa/stream, quiz, review-plan, review-log, review-due}
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
│   ├── vector_store.py    # 本地 BGE 向量存储（可选依赖，未装时优雅降级）
│   ├── qa.py              # 问答服务（LLM 生成 / 降级笔记摘要）
│   ├── knowledge_index.py # 知识库索引（Markdown 切分 + frontmatter 解析 + JSON 缓存）
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
├── requirements-dev.txt   # 开发依赖（pytest 等）
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
  "knowledge_root": ".../knowledge",
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
- `knowledge_root`：知识库根目录路径，仅用于诊断配置，不包含密钥。
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

检索服务使用有界的进程内结果缓存；知识库索引使用 `.cache/knowledge_index.json` 缓存。
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

## 配置

复制 `.env.example` → `.env`，按需修改：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SA_KNOWLEDGE_ROOT` | `../knowledge` | 知识库根目录路径 |
| `SA_TOP_K` | `5` | 检索返回数量 |
| `SA_BM25_POOL` | `0` | BM25 候选池大小（`0`=全库检索，个人规模下推荐） |
| `SA_USE_VECTOR` | `true` | 是否启用向量检索 |
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

## M6 规划边界（尚未实现）

M6a 将在不改变现有 API 的前提下收敛 Source/存储职责/Tool/Runner 契约；M6b 只增加独立、只读的原生
工具调用 preview，不接管 `/api/v1/study-sessions`，不写学习状态，也不新增 `SA_RUNNER=react`。
完整自主 Runner、写工具、checkpoint/幂等和 Agent 评测属于 M10。当前配置表和 API 清单不包含这些规划能力。

默认 RAG 基线仍为 OS/DS/CO 三课 90 题；Network 30 题为显式运行的扩展集。

## 降级路径

| 场景 | 行为 |
| --- | --- |
| `sentence-transformers` 未安装 | 向量路自动跳过，回退纯关键词（BM25）检索 |
| LLM API 未配置 | 问答返回笔记摘要，而非 AI 生成 |
| LLM API 调用失败 | 同上，并附带失败提示 |

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
./.venv/Scripts/uvicorn app.main:app --reload   # http://127.0.0.1:8000/

# 跑测试
./.venv/Scripts/python -m pytest tests/ -q
```

> `sentence-transformers` 为可选依赖：安装后自动启用本地 BGE 向量检索；未安装则降级为纯关键词（BM25）检索，功能不断。

---

*创建：2026-08-11 · 更新：2026-08-21（同步 M6 只读预览边界与三课评测基线）· 维护：随 API 变更同步更新*



## M3a vector storage

The default backend is a persistent SQLite vector store configured by `SA_VECTOR_STORE_PATH`. Set `SA_VECTOR_STORE=linear` to use the original in-memory backend. The index stores chunk fingerprints and the embedding model name, and rebuilds automatically when knowledge content or the model changes. SQLite itself does not require `sentence-transformers`; text queries still require an encoder, and unavailable encoders fall back to BM25.
