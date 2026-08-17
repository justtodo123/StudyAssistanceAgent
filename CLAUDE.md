# CLAUDE.md — StudyAssistanceAgent 项目指导

本项目使用 Claude Code 开发与维护。本文件是 Agent 的项目级指导，包含**开发规范、知识库约定、常见命令**。

## 项目概述

**个人计算机学习助手**。目标用户是大学计算机专业学生（本人）。以 **Agent 工作流 + 本地 Markdown 知识库** 为核心形态：
- 外部原始课程资料存放在 `D:\111_Others_Subjects`（**不复制进仓库**，人工整理；仓库仅维护索引与精炼笔记）。
- 知识库本体是仓库内的 `knowledge/` 目录（Markdown 笔记，越精炼越好，不存大文件）。

### 为什么这样设计（记录关键决策）
- **形态选择**：以 Claude Code 的 agents/skills/CLAUDE.md 驱动学习辅助，配合 FastAPI RAG 后端（多路召回 + 带出处问答），个人项目启动快、演进灵活（见 `docs/PLAN.md`）。
- **资料联动**："两者并存" —— 原始大文件（PDF/PPT/实验工程）保留外部目录，精炼笔记与题解迁入 `knowledge/`，仓库内维护映射关系。
- **Git 主分支**：本地默认分支为 `master`，推送 GitHub 时为个人项目直接在主分支提交交付。

## 目录结构

```
knowledge/        # ★ 知识库（每门课程一个目录，含导航与条目）
platform/         # Python 后端（FastAPI + 多路召回 RAG + 带出处问答）
  app/            #   应用代码（入口/检索/向量/问答/索引/模型/配置）
  tests/          #   检索链路冒烟测试
tools/            # 辅助脚本（RAG 评测脚本 + 课程评测集 JSON）
docs/             # 项目文档：PLAN、reference 索引、standards、interview
.claude/          # agents、skills、hooks 自定义配置
```

## 开发规范

### 1. 通用约定
- **语言**：仓库文档与笔记优先使用**中文**；代码与 git 提交信息使用**英文**。
- **文件命名**：低横线（`kebab-case`），如 `memory-management.md`、`sorting-exercises.md`；分支名使用 `feature/`、`fix/`、`docs/` 前缀。
- **文档格式**：Markdown。每个知识条目使用统一的 frontmatter（见 `knowledge/README.md`）。
- **行宽**：正文每行不超过 120 字符（英文），中文句子按语义换行。
- **编码**：`.md` 文档统一 UTF-8 无 BOM；`*.doc/*.pdf` 等原始资料一律不入库。

### 2. 知识库写作规范
见 [knowledge/README.md](knowledge/README.md)。要点：
- 每门课程在 `knowledge/{course}/` 下建目录，含 `README.md`（课程导航）+ 各主题条目。
- 每个笔记条目带 frontmatter：`tags`、`course`、`difficulty`、`updated`。
- 只写**精炼、可复用的内容**；引用的外部原始资料只在条目中记录路径指向 `D:\111_Others_Subjects`，不复制内容。

### 3. 资料整理流程
1. 新拿到课程资料 → 先在 `docs/reference/` 登记索引（记录课程、路径、文件类型概览、备注）。
2. 人工挑选需要精炼的章节 → 在 `knowledge/{course}/` 写笔记。
3. 大文件（实验工程代码、PDF/PPT）→ 保留在外部目录，仓库索引中记录即可。

### 4. Git 规范
- **提交规范**：遵循 Conventional Commits，详见 [docs/standards/git-conventions.md](docs/standards/git-conventions.md)。
- **提交类型**：`docs`（文档/笔记）、`feat`（新增能力）、`fix`（修复）、`refactor`、`test`、`chore`。
- **提交信息语言**：英文。示例：`docs(course/os): add memory management notes`。
- **大小写**：提交信息用命令式、首字母小写。
- **特殊约定**：`knowledge/` 内容提交时若与某门课程强相关，在 scope 中标注课程名（如 `os`、`ds`、`co`）。
- **分支策略**：采用 Feature Branch 工作流，每个阶段从 `master` 切独立分支开发，人工合并。详见 [docs/standards/git-conventions.md](docs/standards/git-conventions.md)。

### 5. 常用命令
```bash
# 预览知识库结构
tree knowledge/ -L 2

# 后端：安装环境 + 启动 API（platform/ 下）
cd platform
python -m venv .venv && ./.venv/Scripts/python -m pip install -r requirements.txt
./.venv/Scripts/uvicorn app.main:app --reload   # http://127.0.0.1:8000

# 后端：跑测试
./.venv/Scripts/python -m pytest tests/ -q

# RAG 效果评估（数据驱动优化的核心工具）
python tools/run_evaluation.py -k 1,3,5

# 提交（Conventional Commits 向导）
git cz
```

> 后端 `requirements.txt` 中 `sentence-transformers` 为**可选依赖**：安装后自动启用本地 BGE 向量检索；未安装则降级为纯关键词（BM25）检索，功能不断。配置见 `platform/.env.example`。

## 常用 agents / skills

已定义 agents：
- **Requirement_helper**（[.claude/agents/Requirement_helper.md](.claude/agents/Requirement_helper.md)）：需求分析代理，把模糊需求澄清为可执行 PRD。

已定义 skills：
- **requirements-clarity**（`.claude/skills/requirements-clarity/`）：需求澄清技能，通过系统性提问和 100 分评分机制，将模糊需求转化为可执行的 PRD 文档。
- **problem-record**（`.claude/skills/problem-record/`）：问题记录技能，在解决一个非平凡 bug/回归后，引导按模板记录症状→定位→根因→修复→经验到 `proced_problem/` 目录。
- **review-plan**（`.claude/skills/review-plan/`）：复习计划生成技能，输入课程+目标日期，生成分日学习计划并写入 `docs/plans/`。

内置可用 skills（由 Claude Code 提供）：
- `search` — AI 时代的聚合搜索（Exa 引擎），查外部资料/最新信息/技术文档
- `dataviz` — 数据可视化（charts、SVG、dashboard），含设计规范
- `update-config` — 配置 Claude Code settings.json（权限、环境变量、hooks）
- `keybindings-help` — 自定义键盘快捷键
- `simplify` — 审查代码复用/简化/效率，质量优化
- `fewer-permission-prompts` — 扫描 transcript 减少权限提示
- `loop` — 定时执行 prompt/slash 命令
- `claude-api` — Claude API / Anthropic SDK 参考
- `run` — 启动/驱动项目 app 查看变更
- `init` — 初始化新 CLAUDE.md
- `security-review` — 安全审查当前分支变更

> 新增 agent/skill 时同步更新 `.claude/` 目录并在此登记。

## 文档维护规范（CRITICAL）

### 每层目录必须有 README.md

每个子目录必须有 README.md 作为导航入口：
- `docs/README.md` — 文档目录导航
- `platform/README.md` — API 文档与启动指南
- `tools/README.md` — 工具脚本文档
- `knowledge/README.md` — 知识库导航与写作约定

### 每次改动后，及时更新从当前目录到项目根目录的说明文档

**具体操作**：
1. **新增/删除/移动文件** → 更新所在目录的 README.md（目录结构、模块说明）
2. **新增功能/API 变更** → 更新 `platform/README.md`（端点/配置/降级路径）
3. **新增工具脚本** → 更新 `tools/README.md`
4. **里程碑推进** → 更新 `docs/PLAN.md` 状态标记
5. **状态/版本号变更** → 更新 `README.md`（根目录）的 `当前状态` 行和功能表格
6. **知识库条目增删** → 更新 `knowledge/{course}/README.md` 的章节地图和 `knowledge/README.md` 的课程登记表
7. **外部资料整理状态变化** → 更新 `docs/reference/README.md` 主索引

**检查清单**（每次提交前）：
- [ ] 根 `README.md` 的状态/功能表/目录树是否与当前一致
- [ ] `docs/PLAN.md` 里程碑是否反映最新进度
- [ ] 子目录 README 是否涵盖了该目录下的所有模块/文件
- [ ] `knowledge/` 各课程 README 条目数与索引是否准确

## 注意事项 / 约束
- ❌ **不要**把 `D:\111_Others_Subjects` 的内容直接复制进仓库（含 PDF/PPT/工程代码）。仓库只放索引与精炼笔记。
- ❌ **不要**在仓库内创建 gitee/github 的大文件仓库策略之外的二进制文件。
- ✅ 每次会话开工先看 `docs/PLAN.md` 当前里程碑与 `knowledge/README.md` 的导航，明确本次要做什么。
