# StudyAssistanceAgent · 计算机学习助手

> 面向**大学计算机专业学生**的个人学习助手。以 **Claude Code Agent 工作流 + 本地知识库**为核心，
> 汇集课程笔记、例题、面经与学习方法；搭载 **FastAPI 多路召回 RAG 后端**，通过对话式提问与自动化任务辅助学习。

**当前状态**：`v0.4 M1a 完成` — OS 知识库 15 篇完成，hybrid RAG 评测 Recall@3=0.970（33 题评测集，全 15 篇覆盖），评测文档 [docs/baselines.md](docs/baselines.md)

---

## 项目定位

- 🎯 **目标人群**：大学计算机专业学生（本人）
- 📚 **知识范围**：操作系统、数据结构、计算机组成原理、数据库、算法、计算机网络、软件工程等核心课程
- 🧭 **使用方式**：在 Claude Code 中通过 `CLAUDE.md`、agents 与 skills 驱动学习辅助任务；或通过 REST API 调用检索/问答
- 📦 **资料联动**：原始课程资料保留在 `D:\111_Others_Subjects`（人工整理），仓库内维护索引与精炼笔记

## 功能方向（迭代中）

| 能力 | 说明 | 状态 |
| --- | --- | --- |
| 知识问答 | 基于知识库 + 外部资料回答课程问题，支持 LLM 生成或降级笔记摘要 | ✅ 已实现 |
| 课程笔记管理 | 结构化笔记、例题、错题集的创建与检索 | ✅ 已实现（OS 15 篇） |
| 多路召回 RAG | BM25 关键词 + BGE 向量 + RRF 融合检索，带出处标注 | ✅ 已实现 |
| OS 真题评测 | 33 题 RAG 评测集，支持 Recall/Precision/F1/Latency 量化 | ✅ 已实现 |
| 学习计划 | 按课程/考试生成学习路线与计划 | ✅ 规划中 |
| 复习提醒 | 结合遗忘曲线的复习排程 | ⏳ 构想 |
| 面经整理 | 按知识点聚合面试真题 | ⏳ 构想 |

## 目录结构

```
StudyAssistanceAgent/
├── CLAUDE.md              # Agent 项目指导（开发规范、知识库约定）
├── README.md              # 本文件（项目概览）
├── knowledge/             # ★ 本地知识库（Markdown 笔记，项目核心资产）
│   ├── README.md          # 知识库导航与写作约定
│   ├── _templates/        # 条目模板
│   └── {course}/          # 每门课程一个目录（当前已建：os/）
├── docs/                  # 项目文档
│   ├── README.md          # 文档目录导航
│   ├── PLAN.md            # ★ 项目计划（路线图）
│   ├── reference/         # 外部参考资料索引（D:\111_Others_Subjects 的映射）
│   ├── standards/         # 开发规范（Git 提交规范等）
│   └── interview/         # 面试叙事与考点映射（AI 应用开发岗）
├── platform/              # Python 后端（FastAPI + 轻量 RAG）
│   ├── README.md          # API 文档与启动指南
│   ├── app/               # 应用代码
│   │   ├── main.py        # FastAPI 入口（/health, /api/v1/search, /api/v1/qa, /api/v1/qa/stream）
│   │   ├── retrieval.py   # 多路召回 + RRF 融合
│   │   ├── bm25.py        # BM25 关键词检索（bigram 分词）
│   │   ├── vector_store.py# 本地 BGE 向量存储（可选依赖）
│   │   ├── qa.py          # 问答服务（LLM 生成 / 降级笔记摘要）
│   │   ├── knowledge_index.py # 知识库索引（Markdown 切分 + 缓存）
│   │   ├── models.py      # Pydantic 领域模型
│   │   └── config.py      # 环境变量配置
│   ├── tests/             # 冒烟测试
│   ├── requirements.txt   # Python 依赖
│   └── .env.example       # 环境变量模板
├── tools/                 # 辅助脚本
│   ├── README.md          # 工具文档
│   ├── run_evaluation.py  # RAG 评测脚本（Recall@k / F1 / 延迟）
│   └── evaluations/       # 评测集（JSON，每课一个文件）
├── proced_problem/        # 问题记录库（踩坑复盘）
│   ├── README.md          # 导航与记录列表
│   ├── _template.md       # 记录模板（7 章：症状→复现→定位→根因→方案→验证→经验）
│   └── *.md               # 按序号排列的问题记录
├── .claude/               # Agent 配置（agents、skills、hooks）
└── .gitignore
```

## 快速开始

```bash
# 1. 克隆
git clone <repo-url> && cd StudyAssistanceAgent

# 2. （可选）安装提交规范工具
npm i -g commitizen

# 3. 启动 API 后端（platform/ 下）
cd platform
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.txt
./.venv/Scripts/uvicorn app.main:app --reload   # http://127.0.0.1:8000

# 4. 运行冒烟测试
./.venv/Scripts/python -m pytest tests/ -q

# 5. 跑 RAG 评测（验证检索效果）
cd ..
./platform/.venv/Scripts/python tools/run_evaluation.py -k 1,3,5
```

> 在 Claude Code 中打开本仓库即自动加载 `CLAUDE.md`，可调用内置 agents 与 skills。API 文档见 [platform/README.md](platform/README.md)。

## API 端点（概览）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/health` | GET | 健康检查（向量引擎、知识库路径、LLM 配置状态） |
| `/api/v1/search` | POST | 检索知识库片段（多路召回 + RRF 融合） |
| `/api/v1/qa` | POST | 问答（检索 → 可选 LLM 生成 → 带出处回答） |
| `/api/v1/qa/stream` | POST | 流式问答（SSE，同上但逐段输出） |

> 完整 API 文档、配置说明、架构图见 [platform/README.md](platform/README.md)。

## 项目文档导航

| 文档 | 说明 |
| --- | --- |
| [docs/PLAN.md](docs/PLAN.md) | ★ 项目计划与路线图（里程碑、技术选型、风险） |
| [docs/reference/README.md](docs/reference/README.md) | 外部原始资料索引（D:\111_Others_Subjects 映射） |
| [docs/interview/README.md](docs/interview/README.md) | 面试叙事：一句话 + 5 设计决策 + 8 考点 + 3 优化点 |
| [docs/standards/git-conventions.md](docs/standards/git-conventions.md) | Git 提交规范（Conventional Commits） |
| [knowledge/README.md](knowledge/README.md) | 知识库导航与写作规范 |
| [CLAUDE.md](CLAUDE.md) | Agent 项目级开发指导 |

## Git 与贡献

- 提交规范见 [docs/standards/git-conventions.md](docs/standards/git-conventions.md)
- 开发规范见 [CLAUDE.md](CLAUDE.md) 与 [docs/standards/](docs/standards/)

## License

[MIT](LICENSE)
