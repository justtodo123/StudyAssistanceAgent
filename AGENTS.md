# StudyAssistanceAgent — Codex 项目指导

> 面向大学计算机专业学生的个人学习助手。以 **Agent 工作流 + 本地 Markdown 知识库** 为核心，
> 搭载 FastAPI 多路召回 RAG 后端，通过对话式提问与自动化任务辅助学习。

---

## 项目结构与模块组织

```
knowledge/      # ★ 知识库（课程笔记、例题、面经，项目核心资产）
platform/       # Python 后端（FastAPI + 多路召回 RAG + 带出处问答）
tests/          # ★ 迭代测试体系（阶段隔离架构，187 项）
tools/          # 辅助脚本（RAG 评测、一键启动、评测集 JSON）
docs/           # 项目文档（PLAN 路线图、参考索引、开发规范、面试材料）
proced_problem/ # 问题记录库（踩坑复盘，按序号排列）
.claude/        # Claude Code 的 agents、skills、hooks 配置（Codex 不使用）
.github/        # 离线 CI（阶段测试 / 回归 / 评测冒烟）
```

> 各模块内部结构见对应目录的 README.md。

---

## 构建、测试与开发命令

**不要凭推理猜测命令，先读对应模块的 README 获取准确指令。**

| 任务 | 命令存储位置 |
|------|-------------|
| 后端安装、启动、冒烟测试 | [`platform/README.md`](platform/README.md) |
| 一键启动工作台 / 健康检查 | [`tools/README.md`](tools/README.md) → `start_local.py` 章节 |
| RAG 效果评测（三课 90 题） | [`tools/README.md`](tools/README.md) → `run_evaluation.py` 章节 |
| 迭代测试体系（阶段测试 / 回归套件 / marker 筛选） | [`tests/TEST_PLAN.md`](tests/TEST_PLAN.md) |
| 快速开始（克隆到跑通全流程） | 根 [`README.md`](README.md) → 快速开始章节 |

> 若上述 README 中未找到所需命令，向用户说明并请求指引。

---

## 编码风格与命名约定

- **Python**：4 空格缩进，PEP 8。`snake_case` 模块/函数/变量，`PascalCase` 类/Pydantic 模型，大写常量。
- **API 契约**放 `models.py`，业务逻辑放独立 service 模块，不提交缓存/venv/secrets。
- **Markdown**：清晰标题、简练段落、代码块标注语言。
- **仓库文档/笔记**优先中文；代码与 git 提交信息使用英文。
- **文件命名**：`kebab-case`（如 `memory-management.md`）。

---

## 测试指南

使用 pytest。文件命名 `test_*.py`，函数命名 `test_<behavior>`。每次后端行为变更需新增/更新测试。

核心设计：阶段隔离、共享 fixtures、回归前置、pytest markers 按阶段筛选。

详见 [`tests/TEST_PLAN.md`](tests/TEST_PLAN.md)。

---

## Git 提交与分支规范

- 遵循 Conventional Commits：`feat(platform): add review endpoint`、`docs(course/os): clarify scheduling notes`
- 提交信息英文、命令式、首字母小写
- 分支：`feature/`、`fix/`、`docs/` 前缀
- 详见 [`docs/standards/git-conventions.md`](docs/standards/git-conventions.md)

---

## 知识库写作规范

每门课程在 `knowledge/{course}/` 下建目录，含 `README.md`（课程导航）+ 各主题条目。
每个笔记条目带 frontmatter（title / course / tags / difficulty / updated）。
只写精炼、可复用的内容；外部原始资料只记录路径指向 `D:\111_Others_Subjects`，不复制内容。

详见 [`knowledge/README.md`](knowledge/README.md)。

---

## 资料整理流程

1. 新课程资料 → 先在 `docs/reference/` 登记索引
2. 人工挑选精炼章节 → 在 `knowledge/{course}/` 写笔记
3. 大文件（实验工程、PDF/PPT）→ 保留在外部目录，仓库索引记录即可

详见 [`docs/reference/README.md`](docs/reference/README.md)。

---

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

## 写后验证规则
每次使用 Write/Edit 工具修改文件后，必须用 Read 工具回读目标文件，
确认内容已变更，再报告任务完成。跳过验证视为任务未完成

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

**要求**：每节必须有具体数据/命令/输出；定位过程至少 3 步或排除过 1 个误判；通用经验用可操作的 checklist 句式 。

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
| `/` | GET | 最小学习工作台 |
| `/health` | GET | 健康检查 |
| `/api/v1/search` | POST | 检索知识库片段 |
| `/api/v1/qa` | POST | 问答（检索 → LLM 生成/降级摘要） |
| `/api/v1/qa/stream` | POST | 流式问答（SSE） |
| `/api/v1/review-plan` | POST | 复习计划生成 |
| `/api/v1/quiz` | POST | 测验生成 |
| `/api/v1/review-log` | POST | 记录复习完成 |
| `/api/v1/review-due` | GET | 查询今日待复习条目 |
| `/api/v1/study-sessions` | POST | 创建学习会话 |
| `/api/v1/study-sessions/{id}` | GET | 查询学习会话 |
| `/api/v1/study-sessions/{id}/answers` | POST | 提交会话答案 |

## 注意事项

- ❌ 不要把 `D:\111_Others_Subjects` 的内容复制进仓库
- ❌ 不要创建二进制文件（PDF/PPT/工程代码不入库）
- ✅ 每次会话开工先看 `docs/PLAN.md` 当前里程碑
- ✅ 仓库文档/笔记用中文，代码/git 用英文
- ✅ 每阶段开发完成后跑 `tests/` 对应阶段测试 + `tests/regression/` 回归套件
- ✅ 新增测试遵循阶段隔离原则，不修改其他阶段的测试文件
