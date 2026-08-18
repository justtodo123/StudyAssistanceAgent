# StudyAssistanceAgent — Codex 项目指导

> 面向大学计算机专业学生的个人学习助手。以 **Agent 工作流 + 本地 Markdown 知识库** 为核心，
> 搭载 FastAPI 多路召回 RAG 后端，通过对话式提问与自动化任务辅助学习。

---

## 项目结构与模块组织

```
knowledge/          # ★ 知识库（每门课程一个目录，含导航与条目）
platform/           # Python 后端（FastAPI + 多路召回 RAG + 带出处问答）
  app/              #   应用代码（入口/检索/向量/问答/索引/模型/配置）
  tests/            #   检索链路冒烟测试（40 项）
tests/              # ★ 迭代测试体系（阶段隔离架构，67 项）
  TEST_PLAN.md      #   测试计划文档
  conftest.py       #   跨阶段共享 fixtures
  M0_M2/            #   基线回归（18 项）
  M3a/              #   向量库迁移测试
  M3b/              #   可观测性测试
  M3c/              #   面经库测试
  M3d/              #   文档完整性测试
  regression/       #   跨阶段回归套件（21 项）
  utils/            #   测试工具函数
tools/              # 辅助脚本（RAG 评测脚本 + 课程评测集 JSON）
docs/               # 项目文档：PLAN、reference 索引、standards、interview
.claude/            # Claude Code 的 agents、skills、hooks 配置（Codex 不使用）
proced_problem/     # 问题记录库（踩坑复盘）
```

- 课程笔记在 `knowledge/{os,ds,co}/`；模板在 `knowledge/_templates/`。
- 项目计划、参考资料、面试材料、开发规范在 `docs/`。
- 后端在 `platform/app/`，含 retrieval、indexing、QA、quiz、review-plan、review-scheduler 模块。
- 评测数据集和脚本在 `tools/`。

## 构建、测试与开发命令

在 `platform/` 目录下运行后端命令：

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload   # http://127.0.0.1:8000
.\.venv\Scripts\python -m pytest tests/ -q       # 冒烟测试（40 项）
```

迭代测试体系（项目根目录下）：

```bash
.\platform\.venv\Scripts\python -m pytest tests/ -v              # 全部测试（67 项）
.\platform\.venv\Scripts\python -m pytest tests\M0_M2\ -v       # 基线回归
.\platform\.venv\Scripts\python -m pytest tests\regression\ -v  # 回归套件
.\platform\.venv\Scripts\python -m pytest tests\ -m m3a          # 按阶段筛选（m3a/m3b/m3c/m3d/m4/m5a/slow）
```

RAG 效果评估（项目根目录）：

```bash
python tools/run_evaluation.py                # 三课 90 题离线 BM25
```

提交规范向导：`git cz`

> `requirements.txt` 中 `sentence-transformers` 为可选依赖：安装后启用本地 BGE 向量检索；未安装则降级为纯 BM25 关键词检索。配置见 `platform/.env.example`。

## 编码风格与命名约定

- **Python**：4 空格缩进，PEP 8。`snake_case` 模块/函数/变量，`PascalCase` 类/Pydantic 模型，大写常量。
- **API 契约**放 `models.py`，业务逻辑放独立 service 模块，不提交缓存/venv/secrets。
- **Markdown**：清晰标题、简练段落、代码块标注语言。
- **仓库文档/笔记**优先中文；代码与 git 提交信息使用英文。
- **文件命名**：`kebab-case`（如 `memory-management.md`）。

## 测试指南

使用 pytest。文件命名 `test_*.py`，函数命名 `test_<behavior>`。每次后端行为变更需新增/更新测试，覆盖检索排序、API 模型、降级行为、调度逻辑。提交前跑完整测试套件。

### 迭代测试体系（tests/）

详见 `tests/TEST_PLAN.md`。核心设计：

- **阶段隔离**：每阶段测试独立目录（`tests/M3a/`、`tests/M3b/` 等），新增阶段不修改存量测试代码
- **共享 fixtures**：公共 fixture 集中在 `tests/conftest.py`，各阶段 import 使用
- **回归前置**：每阶段开发完成后，先跑本阶段测试，再跑 `tests/regression/` 回归套件
- **pytest markers**：`@pytest.mark.m3a` 等按阶段筛选，`@pytest.mark.slow` 标记慢速测试
- **条件跳过**：M3c 面经目录不存在时自动 skip，创建后自动启用
- **存量不动**：`platform/tests/` 的 40 个原始测试不修改，根级 `tests/` 是增量扩展

### 测试目录结构

| 目录 | 用途 | 测试数 |
|------|------|--------|
| `tests/M0_M2/` | 基线回归（知识库/检索/问答/测验/排程/计划） | 18 |
| `tests/M3a/` | 向量库迁移（接口一致性/数据迁移/降级路径） | 11 |
| `tests/M3b/` | 可观测性（延迟度量/日志/健康检查） | 9 |
| `tests/M3c/` | 面经库（规模/格式/课程覆盖/检索集成） | 11 |
| `tests/M3d/` | 文档完整性（README 链接/PLAN 一致性） | 6 |
| `tests/regression/` | 跨阶段回归（API 契约/RAG 质量/数据完整性） | 21 |
| `platform/tests/` | 原始冒烟测试（不修改） | 40 |

## Git 提交与分支规范

- 遵循 Conventional Commits：`feat(platform): add review endpoint`、`docs(course/os): clarify scheduling notes`
- 提交信息英文、命令式、首字母小写
- 分支：`feature/`、`fix/`、`docs/` 前缀
- 详见 `docs/standards/git-conventions.md`

## 知识库写作规范

每门课程在 `knowledge/{course}/` 下建目录，含 `README.md`（课程导航）+ 各主题条目。

每个笔记条目带 frontmatter：
```yaml
---
title: 条目标题
course: os | ds | co
tags: [topic1, topic2]
difficulty: 入门 | 中等 | 进阶
updated: 2026-08-10
---
```

- 只写精炼、可复用的内容；外部原始资料只记录路径指向 `D:\111_Others_Subjects`，不复制内容。
- 引用格式：`参考原始资料：docs/reference/os.md#章节名`

## 资料整理流程

1. 新课程资料 → 先在 `docs/reference/` 登记索引
2. 人工挑选精炼章节 → 在 `knowledge/{course}/` 写笔记
3. 大文件（实验工程、PDF/PPT）→ 保留在外部目录，仓库索引记录即可

## 文档维护规范（CRITICAL）

每次改动后及时更新说明文档：
- 新增/删除/文件 → 更新所在目录 README.md
- 新功能/API 变更 → 更新 `platform/README.md`
- 里程碑推进 → 更新 `docs/PLAN.md`
- 知识库条目增删 → 更新 `knowledge/{course}/README.md` + `knowledge/README.md`

提交前检查清单：
- [ ] 根 `README.md` 状态/功能表/目录树一致
- [ ] `docs/PLAN.md` 里程碑反映最新进度
- [ ] 子目录 README 覆盖所有模块/文件
- [ ] `tests/` 新增测试遵循阶段隔离（不修改其他阶段文件）
- [ ] 本阶段测试 + 回归套件全部通过

---

# Skills（技能指令）

> 以下章节等价于 Claude Code 的 skills 系统。当用户请求匹配某个技能的触发条件时，
> 按该技能的指令执行，而不是走默认流程。

---

## Skill: requirements-clarity — 需求澄清

**触发**：需求不清晰、功能复杂（预计超过 2 天工作量）、涉及跨团队协作时。
**不触发**：提及具体文件路径、包含代码片段、引用现有函数、有明确复现步骤的 bug 修复。

**流程**：

1. **初始分析**：解析需求 → 生成功能名（kebab-case）→ 初始清晰度评分（0-100 分）
   - 评分维度：功能清晰度 /30 + 技术具体性 /25 + 实现完整性 /25 + 业务上下文 /20
2. **差距分析**：从功能范围、用户交互、技术约束、业务价值四维度识别缺失信息
3. **交互式澄清**：每轮 2-3 个问题，基于回答递进，更新评分
4. **PRD 生成**：评分 ≥90 后，输出到 `./docs/prds/{feature_name}-v{version}-prd.md`

**核心原则**：系统性提问（每次一类问题）、质量驱动迭代（≥90 分才出 PRD）、可执行输出（具体验收标准 + 阶段计划）。

---

## Skill: problem-record — 问题记录

**触发**：非平凡 bug 已定位根因并修复，涉及 ≥2 个排查步骤，有通用价值。
**不触发**：拼写/lint 错误、一眼能看出的命名冲突、一次性环境问题。

**流程**：

1. 确认 `proced_problem/` 目录和 `_template.md` 存在
2. 分配序号（已有文件最大序号 +1）
3. 按模板填写 7 章：症状 → 复现条件 → 定位过程 → 根因 → 解决方案 → 验证 → 通用经验
4. 更新 `proced_problem/README.md` 导航
5. 展示给用户确认

**要求**：每节必须有具体数据/命令/输出；定位过程至少 3 步或排除过 1 个误判；通用经验用可操作的 checklist 句式。

---

## Skill: review-plan — 复习计划生成

**触发**：用户要求生成学习计划、复习计划、考前安排、复习时间表。
**不触发**：问知识点（用 QA）、做测验（用 quiz-generator）、查看进度（用 review-due）。

**参数**：
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `course` | 课程简称（os/ds/co） | 必填 |
| `target_date` | 目标日期 | 14 天后 |
| `hours_per_day` | 每天可用学时 | 2.0 小时 |

**流程**：
1. 收集参数 → 2. 读取课程全部条目（按文件去重） → 3. 按难度分配时间（入门 25min/中等 35min/进阶 50min） → 4. 贪心填充每日容量 → 5. 输出到 `docs/plans/{plan_name}-plan.md`

第 2 天起每天开头预留 10 分钟复习前一天内容。

---

## Skill: quiz-generator — 测验生成

**触发**：用户要求出题、做练习、生成测验、随堂测试、自测题。
**不触发**：问知识点（用 QA）、生成计划（用 review-plan）、查看进度（用 review-due）。

**参数**：
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `course` | 课程简称 | 必填 |
| `count` | 题目数量 | 5（范围 1-20） |
| `difficulty` | 难度筛选 | 不筛选 |
| `topics` | 标签筛选 | 不筛选 |

**三种题型**：
1. **经典例题**（example）：从条目 `## 经典例题` 段落提取，含完整参考答案
2. **检索题**（retrieval）：从评测集加载，需查阅知识条目验证
3. **概念题**（concept）：从 tags 生成 "什么是 X？" 型问题

**交互式模式**：一次呈现一题 → 等待作答 → 对比答案 → 最后汇总得分。

---

## Skill: review-due — 复习排程

**触发**：用户问今天该复习什么、哪些逾期了、查看复习进度、记录复习完成。
**不触发**：生成计划（用 review-plan）、做测验（用 quiz-generator）、问知识点（用 QA）。

**间隔重复算法**：
| 复习次数 | 间隔 |
|----------|------|
| 第 1 次 | 1 天 |
| 第 2 次 | 2 天 |
| 第 3 次 | 4 天 |
| 第 4 次 | 8 天 |
| 第 5 次 | 16 天 |
| 第 6 次+ | 32 天 |

**查询**：`GET /api/v1/review-due?course={course}`
**记录**：`POST /api/v1/review-log`，body: `{"file": "knowledge/os/xxx.md", "course": "os"}`

优先展示逾期最久的条目。记录后立即告知下次复习时间。

---

## Skill: study-assistant — 多轮工具编排学习助手 ⭐

> **面试演示重点**：展示 Agent 多轮工具调用 / Tool Orchestration 能力。

**触发**：用户要求「学一个知识点」「帮我学一下 XX」「交互式学习」「边学边练」。
**不触发**：只想问问题（用 QA）、只想做题（用 quiz-generator）、想安排计划（用 review-plan）。

**编排流程**（6 步闭环）：

```
用户提出学习主题
    ↓
步骤 1: QA 检索 → POST /api/v1/qa（获取知识条目 + 来源）
    ↓
步骤 2: 知识讲解 → 结构化呈现（核心概念 + 关键原理 + 易错点，≤200 字）
    ↓
步骤 3: 出题测验 → POST /api/v1/quiz（优先 example 题型，1-2 题）
    ↓
步骤 4: 等待用户作答
    ↓
步骤 5: 评估掌握度 → 对比参考答案或 QA 验证
    ├── 答对 → 步骤 6a: 记录掌握
    └── 答错 → 补充讲解 → 回到步骤 3（连续 2 次错则给完整讲解）
    ↓
步骤 6: 记录复习 → POST /api/v1/review-log
    ↓
学习总结（含「工具调用链」面试演示亮点）
```

**最后必须展示工具调用链总结**：
```
1. QA 检索 → 获取 N 条知识片段
2. 知识讲解 → 提炼核心要点
3. 出题测验 → M 道题
4. 掌握度评估 → 评分
5. 复习记录 → 下次日期
```

---

# Agent: Requirement_helper — 需求分析代理

**用途**：把模糊需求澄清为可执行 PRD。当需求描述模糊、不完整或需要系统性澄清时使用。

**能力**：
1. 需求收集与理解（通过提问澄清模糊需求）
2. 需求分类与整理（功能/非功能/业务规则/界面/数据需求）
3. 编写 SRS 需求规格说明书
4. 用户故事与用例（User Story / Use Case）
5. 需求建模（业务流程、状态转换、数据流）
6. 需求验证与确认（识别模糊性、遗漏和冲突）

**配合技能**：遇到模糊需求时调用 `requirements-clarity` 技能进行深度澄清（100 分评分系统）。

---

## API 端点速查

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/search` | POST | 检索知识库片段 |
| `/api/v1/qa` | POST | 问答（检索 → LLM 生成/降级摘要） |
| `/api/v1/qa/stream` | POST | 流式问答（SSE） |
| `/api/v1/review-plan` | POST | 复习计划生成 |
| `/api/v1/quiz` | POST | 测验生成 |
| `/api/v1/review-log` | POST | 记录复习完成 |
| `/api/v1/review-due` | GET | 查询今日待复习条目 |

## 注意事项

- ❌ 不要把 `D:\111_Others_Subjects` 的内容复制进仓库
- ❌ 不要创建二进制文件（PDF/PPT/工程代码不入库）
- ✅ 每次会话开工先看 `docs/PLAN.md` 当前里程碑
- ✅ 仓库文档/笔记用中文，代码/git 用英文
- ✅ 每阶段开发完成后跑 `tests/` 对应阶段测试 + `tests/regression/` 回归套件
- ✅ 新增测试遵循阶段隔离原则，不修改其他阶段的测试文件
