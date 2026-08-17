# Platform — FastAPI RAG 后端

> StudyAssistanceAgent 的 Python 后端服务。提供知识库检索、带出处问答、SSE 流式输出、复习计划生成能力。

## 架构

```
提问 → MultiRecallService（course 过滤前置）
         ├─ 路1: LocalVectorStore（BGE 余弦，可选依赖）
         └─ 路2: Bm25Search（bigram 关键词）
      → RRF 融合（k=60）+ 文件级去重
      → QaService: LLM 生成（勒令带出处）| 降级笔记摘要（句子边界截断）
      → FastAPI /api/v1/{search, qa, qa/stream, quiz, review-plan}
```

**M1d 优化**：课程过滤前移至检索阶段（避免无关课程占位）、RRF 结果按文件去重（同文件只保留最高分 chunk）、摘要截断在句子边界。

## 目录结构

```
platform/
├── README.md              # 本文件（API 文档与启动指南）
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI 入口：/health, /api/v1/search, /api/v1/qa, /api/v1/qa/stream
│   ├── models.py          # Pydantic 领域模型（RetrievalChunk, SearchRequest, QaRequest 等）
│   ├── config.py          # 环境变量配置（dotenv → 常量）
│   ├── retrieval.py       # 多路召回 + RRF 融合（MultiRecallService）
│   ├── bm25.py            # BM25 关键词检索（中文 bigram + 英文整词分词）
│   ├── vector_store.py    # 本地 BGE 向量存储（可选依赖，未装时优雅降级）
│   ├── qa.py              # 问答服务（LLM 生成 / 降级笔记摘要）
│   ├── knowledge_index.py # 知识库索引（Markdown 切分 + frontmatter 解析 + JSON 缓存）
│   ├── review_plan.py     # 复习计划服务（分日学习计划生成）
│   └── quiz.py            # 测验生成服务（例题+评测集+概念模板三数据源）
├── tests/
│   ├── test_retrieval.py  # 检索链路冒烟测试（6 个用例）
│   ├── test_review_plan.py # 复习计划测试（8 个用例）
│   └── test_quiz.py       # 测验生成测试（11 个用例）
├── requirements.txt       # 核心依赖
├── requirements-dev.txt   # 开发依赖（pytest 等）
└── .env.example           # 环境变量模板（复制为 .env 后修改）
```

## API 端点

### 健康检查

```
GET /health
```

响应示例：
```json
{
  "status": "UP",
  "vector_engine": "local",
  "knowledge_root": ".../knowledge",
  "llm_configured": false
}
```

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

## 配置

复制 `.env.example` → `.env`，按需修改：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SA_KNOWLEDGE_ROOT` | `../knowledge` | 知识库根目录路径 |
| `SA_TOP_K` | `5` | 检索返回数量 |
| `SA_BM25_POOL` | `0` | BM25 候选池大小（`0`=全库检索，个人规模下推荐） |
| `SA_USE_VECTOR` | `true` | 是否启用向量检索 |
| `SA_EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | BGE 嵌入模型名 |
| `SA_LLM_BASE_URL` | — | LLM API 地址（OpenAI 兼容） |
| `SA_LLM_API_KEY` | — | LLM API 密钥 |
| `SA_LLM_MODEL` | — | LLM 模型名（如 `deepseek-chat`） |

## 降级路径

| 场景 | 行为 |
| --- | --- |
| `sentence-transformers` 未安装 | 向量路自动跳过，回退纯关键词（BM25）检索 |
| LLM API 未配置 | 问答返回笔记摘要，而非 AI 生成 |
| LLM API 调用失败 | 同上，并附带失败提示 |

**核心原则：保证总是有输出。**

## 运行

```bash
# 安装环境
cd platform
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.txt

# 启动 API
./.venv/Scripts/uvicorn app.main:app --reload   # http://127.0.0.1:8000

# 跑测试
./.venv/Scripts/python -m pytest tests/ -q
```

> `sentence-transformers` 为可选依赖：安装后自动启用本地 BGE 向量检索；未安装则降级为纯关键词（BM25）检索，功能不断。

---

*创建：2026-08-11 · 更新：2026-08-17（M2 新增复习计划+测验生成端点）· 维护：随 API 变更同步更新*
