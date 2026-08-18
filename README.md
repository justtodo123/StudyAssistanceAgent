# StudyAssistanceAgent · 计算机学习助手

> 面向**大学计算机专业学生**的个人学习助手。以 **Claude Code Agent 工作流 + 本地知识库**为核心，
> 汇集课程笔记、例题、面经与学习方法；搭载 **FastAPI 多路召回 RAG 后端**，通过对话式提问与自动化任务辅助学习。

**当前状态**：`v1.6 M5e 可复现交付` — `python tools/start_local.py` 一键离线启动；CI 跑阶段测试、回归和评测冒烟。

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
| 课程笔记管理 | 结构化笔记、例题、错题集的创建与检索 | ✅ 已实现（OS 20 篇 + DS 20 篇 + CO 20 篇） |
| 多路召回 RAG | BM25 关键词 + BGE 向量 + RRF 融合检索，带出处标注 | ✅ 已实现（文件去重、课程过滤） |
| RAG 评测 | 一条命令评测 OS 38 + DS 28 + CO 24 共 90 题，输出汇总指标和 JSON 报告 | ✅ 已实现（默认离线 BM25 Recall@3：OS 1.000、DS 0.929、CO 1.000） |
| 学习计划 | 按课程/考试生成学习路线与计划 | ✅ 已实现（API `/api/v1/review-plan` + Skill `review-plan`） |
| 测验生成 | 从知识条目例题、评测集、概念标签自动出题 | ✅ 已实现（API `/api/v1/quiz` + Skill `quiz-generator`） |
| 复习提醒 | 结合遗忘曲线的复习排程 | ✅ 已实现（API `/api/v1/review-log` + `/api/v1/review-due` + Skill `review-due`） |
| 面经整理 | 按知识点聚合面试真题 | ✅ 已实现（51 条，覆盖 OS/DS/CO/RAG/Agent/项目） |
| 多轮工具编排 | QA→讲解→出题→评估→记录复习完整链路 | ✅ 已实现（API `/api/v1/study-sessions` + Skill `study-assistant`） |
| 学习工作台 | 最小交互页面，调用正式会话 API 完成学习闭环 | ✅ 已实现（`GET /`） |
| 离线交付 | 一键启动、健康检查、离线 CI 与演示基线 | ✅ 已实现（`tools/start_local.py` + `.github/workflows/offline-ci.yml`） |

## 目录结构

```
StudyAssistanceAgent/
├── CLAUDE.md              # Agent 项目指导（开发规范、知识库约定）
├── README.md              # 本文件（项目概览）
├── knowledge/             # ★ 本地知识库（Markdown 笔记，项目核心资产）
│   ├── README.md          # 知识库导航与写作约定
│   ├── _templates/        # 条目模板
│   ├── os/                # 操作系统（20 篇）
│   ├── ds/                # 数据结构（20 篇）
│   ├── co/                # 计算机组成原理（20 篇）
│   └── interview/         # 面经知识库（51 条）
├── docs/                  # 项目文档
│   ├── README.md          # 文档目录导航
│   ├── PLAN.md            # ★ 项目计划（路线图）
│   ├── reference/         # 外部参考资料索引（D:\111_Others_Subjects 的映射）
│   ├── standards/         # 开发规范（Git 提交规范等）
│   ├── plans/              # 学习计划与项目工程执行计划
│   └── interview/         # 面试叙事与考点映射（AI 应用开发岗）
├── platform/              # Python 后端（FastAPI + 轻量 RAG）
│   ├── README.md          # API 文档与启动指南
│   ├── app/               # 应用代码
│   │   ├── main.py        # FastAPI 入口（search/qa/quiz/review/study-sessions + 工作台）
│   │   ├── retrieval.py   # 多路召回 + RRF 融合
│   │   ├── bm25.py        # BM25 关键词检索（bigram 分词）
│   │   ├── vector_store.py# 本地 BGE 向量存储（可选依赖）
│   │   ├── qa.py          # 问答服务（LLM 生成 / 降级笔记摘要）
│   │   ├── knowledge_index.py # 知识库索引（Markdown 切分 + 缓存）
│   │   ├── review_plan.py # 复习计划服务（分日学习计划生成）
│   │   ├── quiz.py       # 测验生成服务（例题+评测集+概念模板）
│   │   ├── review_scheduler.py # 复习排程服务（遗忘曲线间隔重复）
│   │   ├── study_session.py # 学习会话编排（状态机 + 工具轨迹）
│   │   ├── learning_store.py # SQLite 会话/复习仓储
│   │   ├── observability.py # 进程内指标与结构化日志
│   │   ├── models.py      # Pydantic 领域模型
│   │   ├── config.py      # 环境变量配置
│   │   └── static/           # 最小学习工作台静态页
│   ├── tests/             # 冒烟测试
│   ├── requirements.txt   # Python 依赖
│   └── .env.example       # 环境变量模板
├── tools/                 # 辅助脚本
│   ├── README.md          # 工具文档
│   ├── run_evaluation.py  # 统一 RAG 评测入口（三课 90 题 / JSON 报告）
│   ├── start_local.py     # 一键启动与 /health 检查
│   └── evaluations/       # 评测集（JSON，每课一个文件）
├── tests/                 # ★ 迭代测试体系（阶段隔离架构）
│   ├── TEST_PLAN.md       # 测试计划文档
│   ├── conftest.py        # 跨阶段共享 fixtures
│   ├── M0_M2/             # 基线回归测试（18 项）
│   ├── M3a/               # 向量库迁移测试（22 项）
│   ├── M3b/               # 可观测性测试（13 项）
│   ├── M3c/               # 面经库测试（10 项）
│   ├── M3d/               # 文档完整性测试（6 项）
│   ├── M4/                # 课程知识库规模测试（14 项）
│   ├── M5a/               # 评测入口测试（26 项）
│   ├── M5b/               # 学习会话测试（18 项）
│   ├── M5c/               # 学习状态持久化测试（14 项）
│   ├── M5d/               # 学习工作台测试（10 项）
│   ├── M5e/               # 可复现交付测试（15 项）
│   ├── regression/        # 跨阶段回归套件（21 项）
│   └── utils/             # 测试工具函数
├── proced_problem/        # 问题记录库（踩坑复盘）
│   ├── README.md          # 导航与记录列表
│   ├── _template.md       # 记录模板（7 章：症状→复现→定位→根因→方案→验证→经验）
│   └── *.md               # 按序号排列的问题记录
├── .github/               # 离线 CI（阶段测试 / 回归 / 评测冒烟）
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
./.venv/Scripts/python ../tools/start_local.py   # 或 uvicorn；http://127.0.0.1:8000/

# 4. 运行冒烟测试
./.venv/Scripts/python -m pytest tests/ -q

# 5. 跑 RAG 评测（验证检索效果）
cd ..
./platform/.venv/Scripts/python tools/run_evaluation.py

# 6. 运行迭代测试体系（根目录下）
./platform/.venv/Scripts/python -m pytest tests/ -v            # 根级阶段测试与回归（187 项）
./platform/.venv/Scripts/python -m pytest tests/M0_M2/ -v     # 基线回归
./platform/.venv/Scripts/python -m pytest tests/regression/ -v # 回归套件
./platform/.venv/Scripts/python -m pytest tests/ -m m3d        # M3d 文档检查
./platform/.venv/Scripts/python -m pytest tests/ -m m4         # M4 知识库规模检查
./platform/.venv/Scripts/python -m pytest tests/ -m m5a        # M5a 评测入口检查
./platform/.venv/Scripts/python -m pytest tests/ -m m5b        # M5b 学习会话检查
./platform/.venv/Scripts/python -m pytest tests/ -m m5c        # M5c 持久化检查
./platform/.venv/Scripts/python -m pytest tests/ -m m5d        # M5d 学习工作台检查
./platform/.venv/Scripts/python -m pytest tests/ -m m5e        # M5e 可复现交付检查
```

> 在 Claude Code 中打开本仓库即自动加载 `CLAUDE.md`，可调用内置 agents 与 skills。API 文档见 [platform/README.md](platform/README.md)。

## API 端点（概览）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/` | GET | 最小学习工作台（讲解、作答、反馈、复习记录） |
| `/health` | GET | 健康检查（向量引擎、知识库路径、索引/缓存/延迟指标、LLM 配置状态） |
| `/api/v1/search` | POST | 检索知识库片段（多路召回 + RRF 融合） |
| `/api/v1/qa` | POST | 问答（检索 → 可选 LLM 生成 → 带出处回答） |
| `/api/v1/qa/stream` | POST | 流式问答（SSE，同上但逐段输出） |
| `/api/v1/review-plan` | POST | 复习计划生成（课程+目标日期 → 分日学习计划） |
| `/api/v1/quiz` | POST | 测验生成（课程+题数 → 三种题型混合出题） |
| `/api/v1/review-log` | POST | 记录复习完成（更新间隔重复排程） |
| `/api/v1/review-due` | GET | 查询今日待复习条目（基于遗忘曲线） |
| `/api/v1/study-sessions` | POST | 创建学习会话（检索讲解并出题） |
| `/api/v1/study-sessions/{id}` | GET | 查询学习会话状态与工具轨迹 |
| `/api/v1/study-sessions/{id}/answers` | POST | 提交答案并评估掌握度 |

> 完整 API 文档、配置说明、架构图见 [platform/README.md](platform/README.md)。

## 项目文档导航

| 文档 | 说明 |
| --- | --- |
| [docs/PLAN.md](docs/PLAN.md) | ★ 项目计划与路线图（里程碑、技术选型、风险） |
| [tests/TEST_PLAN.md](tests/TEST_PLAN.md) | ★ 迭代测试计划（阶段隔离、回归策略、执行矩阵） |
| [docs/reference/README.md](docs/reference/README.md) | 外部原始资料索引（D:\111_Others_Subjects 映射） |
| [docs/interview/README.md](docs/interview/README.md) | 面试叙事：一句话 + 5 设计决策 + 8 考点 + 3 优化点 |
| [docs/demo.md](docs/demo.md) | 离线演示手册（一键启动与学习闭环） |
| [docs/baselines.md](docs/baselines.md) | RAG 与交付延迟基线 |
| [docs/standards/git-conventions.md](docs/standards/git-conventions.md) | Git 提交规范（Conventional Commits） |
| [docs/plans/m3-engineering-execution-plan.md](docs/plans/m3-engineering-execution-plan.md) | M3 工程质量阶段执行记录（已完成） |
| [docs/plans/m4-knowledge-base-scale-plan.md](docs/plans/m4-knowledge-base-scale-plan.md) | M4 课程知识库规模补齐计划（范围、验收、分支） |
| [knowledge/README.md](knowledge/README.md) | 知识库导航与写作规范（含 51 条面经） |
| [CLAUDE.md](CLAUDE.md) | Agent 项目级开发指导 |

## Git 与贡献

- 提交规范见 [docs/standards/git-conventions.md](docs/standards/git-conventions.md)
- 开发规范见 [CLAUDE.md](CLAUDE.md) 与 [docs/standards/](docs/standards/)

## License

[MIT](LICENSE)



> **M4 status (2026-08-18):** M3d and M4 are now on `master`. M4 expands OS/DS/CO to 20 entries each (60 course entries total) and adds 15 evaluation questions. The M3c interview bank still contains 51 entries and is integrated with indexing, search, and QA sources.
