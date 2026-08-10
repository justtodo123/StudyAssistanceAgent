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

## 分支与合并策略（个人项目，登 GitHub）

- 本人直接在 `master` 上提交（个人项目，单干模式）。
- 涉及大规模变更或实验时可起分支：`git switch -c feature/spaced-repetition`，完成后 `git merge --no-ff`。

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
