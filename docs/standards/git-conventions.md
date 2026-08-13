# Git 提交规范（Conventional Commits）

> 本仓库遵循 [Conventional Commits 规范](https://www.conventionalcommits.org/zh-hans/)，以生成清晰、机器可读的提交历史，并为未来的 changelog 自动化做准备。

## 提交信息结构

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型 `<type>`（必填）

| type | 用途 | 示例 |
| --- | --- | --- |
| `feat` | 新增功能/能力 | `feat: add quiz generator skill` |
| `fix` | 修复缺陷 | `fix: correct os chapter link` |
| `docs` | 文档/笔记/知识库变更 | `docs(course/os): add memory management notes` |
| `refactor` | 重构，不改功能 | `refactor: extract index generator` |
| `test` | 测试相关 | `test: add frontmatter validation cases` |
| `chore` | 构建、配置、依赖等杂项 | `chore: set up commitizen` |
| `style` | 格式（代码风格，不影响逻辑） | `style: normalize markdown line width` |
| `perf` | 性能优化 | `perf: cache reference index` |

### 范围 `<scope>`（可选推荐）
- 课程类（针对 `knowledge/` 变更）：`os`、`ds`（数据结构）、`co`（计算机组成原理）、`db`、`network`、`ai`、`se` 等。
- 项目类：`docs`、`tools`、`agent`、`skill`、`meta`（根目录配置）、`ci`。

### 摘要 `<subject>`（必填）
- 英文、动词开头、现在时、命令式：`add`、`fix`、`update` 而非 `added`、`fixed`。
- 首字母小写，末尾不加句号。
- 长度 ≤ 50 字符。

### 正文 `<body>`（可选）
- 说明**为什么**，而不是**怎么做**。
- 一段描述即可，需要换行时用空行分隔。

### 脚注 `<footer>`（可选）
- 关联 issue/PR：`Closes #12`
- **本仓库约定**：结束处附加。

## 完整示例

```
docs(course/os): add memory management notes

Summarize paging/segmentation from textbook ch4.
Link to external raw materials in docs/reference/os.md.
```
```
feat(skill): add spaced-repetition review skill

Closes #3
```

## 工具

- 使用 [Commitizen](https://github.com/commitizen/cz-cli) 交互式生成符合规范的提交信息：

```bash
npx --no-install commitizen --version   # 检查
node --eval "require('./package.json')" # 版本约束可定义在 devDependencies
npm i -g commitizen
```

> 手动提交时，先 `git status` 与 `git diff` 再次确认改动内容，再写提交信息。commitizen / cz-conventional-changelog 配置见 [package.json](../../package.json)。

## 分支与合并策略（Feature Branch 工作流）

### 核心原则

- **每个里程碑阶段从 `master` 切独立分支开发**，完成后由人工合并回 `master`。
- **每个阶段开始前，确保上一阶段分支已合并到 `master`**，并从最新 `master` 切新分支。
- 不在 `master` 上直接提交功能性改动（仅允许紧急修复 + 文档微调）。
- 合并使用 `git merge --no-ff`，保留分支历史轨迹。

### 分支命名规范

```
feature/m{里程碑}-{简短描述}
```

| 分支名 | 对应阶段 | 说明 |
|--------|----------|------|
| `feature/m1a-os-knowledge` | M1 数据先行 — OS 扩写 | OS 知识库 6→15 篇 + 评测基线 |
| `feature/m1b-ds-knowledge` | M1 数据先行 — DS 知识库 | DS 0→10 篇 + 评测集 |
| `feature/m1c-co-knowledge` | M1 数据先行 — CO 知识库 | CO 0→10 篇 + 评测集 |
| `feature/m1d-platform-polish` | M1 数据先行 — 平台增强 | 评测脚本对比模式 + 端点增强 |
| `feature/m2a-review-plan` | M2 Agent 能力 — 复习计划 | 复习计划生成 skill/接口 |
| `feature/m2b-quiz-generator` | M2 Agent 能力 — 随堂测验 | 自动出题 + 工具调用演示 |
| `feature/m3a-vector-store` | M3 工程质量 — 向量库升级 | 替换线性扫描为 sqlite-vec/Chroma |
| `feature/m3b-observability` | M3 工程质量 — 可观测性 | 日志/延迟/缓存命中埋点 |
| `fix/{简短描述}` | 紧急修复 | 直接基于 `master`，修复后立即合并 |
| `docs/{简短描述}` | 文档批量更新 | 不影响代码的纯文档变更 |

### 阶段开发流程

```bash
# 1. 确认当前在 master 且工作区干净
git switch master
git status

# 2. 切新阶段分支
git switch -c feature/m1a-os-knowledge

# 3. 开发 + 提交（遵循 Conventional Commits）
git add knowledge/os/xxx.md
git commit -m "docs(course/os): add detailed scheduling algorithm notes"

# 4. 开发完成，合并回 master（人工操作）
git switch master
git merge --no-ff feature/m1a-os-knowledge -m "merge: M1a OS knowledge base expansion"

# 5. （可选）推送 master + 删除本地分支
git push origin master
git branch -d feature/m1a-os-knowledge
```

### 分支粒度原则

- 每个分支的**生命周期尽量控制在 1 周内**，避免长时间偏离 master 导致合并 diff 堆积。
- 若一个里程碑工作量超过 1 周，拆分为多个子阶段分支（如 M1 拆为 m1a/m1b/m1c/m1d）。
- 知识库条目（`knowledge/`）是纯内容新增，跨分支几乎无冲突；平台代码（`platform/`）和文档（`CLAUDE.md`、`PLAN.md`）改动时优先合并后再切新分支。

### 合并检查清单

- [ ] 上一阶段分支已合并到 `master`
- [ ] `git log --oneline --graph` 确认历史清晰
- [ ] 相关文档（README、PLAN.md）已随改动更新
- [ ] （如有评测集）已跑评估并记录基线数字对比

## 撤销与回退速查

```bash
# 撤销最近一次提交，保留改动
git reset --soft HEAD~1
# 撤销最近一次提交，保留改动到暂存区，但重写提交信息
git commit --amend
# 查看最近日志
git log --oneline
```

## 收起、应避免

- ❌ 一次提交混合多种类型（如改笔记 + 修配置 + 加脚本混在一个 commit）。
- ❌ 提交信息含糊：`update`、`fix stuff`、`yuj`。
- ❌ 提交四类无关的变更（参考 [git-conventions、原子提交](https://www.conventionalcommits.org/)）。
- ✅ 每个 commit 只做一件事；笔记/规范变更与代码变更分开。
