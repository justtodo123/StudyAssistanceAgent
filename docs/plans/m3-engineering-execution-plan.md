# M3 工程质量与沉淀 · 当前执行计划

> 版本：v1.0
> 制定日期：2026-08-18
> 当前状态：执行中
> 适用范围：StudyAssistanceAgent 的 M3a～M3d 工程质量工作

## 1. 计划定位

本文件是**项目工程执行计划**，用于把 `docs/PLAN.md` 中的 M3 里程碑拆解为可执行的四个阶段，并统一约束代码、测试、文档、知识库和 Git 分支的推进方式。

它不是：

- `review-plan` Skill 生成的个人课程复习计划；
- 按天安排学习时间的日程表；
- 替代 `docs/PLAN.md` 的项目总路线图。

文件之间的职责如下：

| 文件 | 定位 |
| --- | --- |
| `docs/PLAN.md` | 项目总路线图、里程碑目标和长期退出条件 |
| `docs/plans/m3-engineering-execution-plan.md` | 当前 M3 的阶段任务、分支策略、验收门禁和执行顺序 |
| `docs/plans/README.md` | `docs/plans/` 目录导航 |
| `tests/TEST_PLAN.md` | 阶段测试隔离、fixture 和回归测试规则 |
| `docs/standards/git-conventions.md` | 分支、提交、合并和提交信息规范 |

本计划的核心原则是：**先收口已有 M3a WIP，再逐阶段推进 M3b、M3c、M3d；每一阶段独立分支、独立验收、人工合并，不在 `master` 上直接提交功能代码。**

## 2. 当前基线（2026-08-18）

### 2.1 功能基线

- M1 已完成：OS 15 篇、DS 10 篇、CO 10 篇，共 35 篇课程条目。
- M1 评测集共 75 题，三门课程 Recall@3 均达到当前基线要求。
- M2 已完成：复习计划、测验生成、复习排程、多轮工具编排。
- M3a 实现已经存在于当前工作区，但尚未形成正式提交和合并记录。
- `knowledge/interview/` 当前不存在，M3c 面经库尚未开始。

### 2.2 测试基线

最近一次检查结果：

| 测试范围 | 结果 |
| --- | --- |
| `tests/M0_M2/` | 18 passed |
| `tests/M3a/` | 22 passed |
| `tests/M3b/` | 11 passed，1 skipped；部分断言仍是占位断言 |
| `tests/M3c/` | 10 skipped；原因是面经目录不存在 |
| `tests/M3d/` | 6 passed |
| `tests/regression/` | 21 passed |
| `platform/tests/` | 40 passed |

由于本机 pytest 默认临时目录存在权限问题，后续验证统一允许使用工作区临时目录：

```powershell
$py = ".\\platform\\.venv\\Scripts\\python.exe"
$base = ".\\.tmp-test\\m3"
& $py -m pytest tests/M3a/ -q --basetemp "$base\\m3a"
& $py -m pytest tests/regression/ -q --basetemp "$base\\regression"
```

`--basetemp` 只是本机测试环境规避方案，不改变项目运行时逻辑；不得把测试缓存、SQLite 缓存或虚拟环境提交到仓库。

## 3. 总体目标与非目标

### 3.1 总体目标

1. 将 M3a 向量存储迁移从工作区 WIP 收口为可审查、可合并的工程变更。
2. 为检索链路建立真实可用的延迟、缓存、日志和健康检查能力。
3. 建立不少于 50 条、可检索、可追问的面经知识库。
4. 让代码、测试、文档、导航和项目计划在 M3 结束时保持一致。

### 3.2 当前不做的事情

- 不复制 `D:\111_Others_Subjects` 中的原始资料到仓库。
- 不引入超出当前个人规模需要的分布式数据库或复杂运维系统。
- 不为了“通过测试”保留被注释掉的占位断言；M3b 必须补齐真实行为验证。
- 不在本计划中重写 M1/M2 已稳定的 API 契约，除非回归测试证明存在缺陷。
- 不把 M3a、M3b、M3c、M3d 的无关改动混入同一个提交或同一个阶段分支。

## 4. 四阶段执行计划

### 阶段一：M3a 向量存储迁移收口

**目标**：将当前未提交的 SQLite 向量存储实现整理为正式功能，并保留线性内存后端和 BM25 降级路径。

**建议分支**：`feature/m3a-vector-store`

**当前特殊处理**：当前工作区已经在 `master` 上存在 M3a 未提交改动。不得在 `master` 上提交这些功能改动。先审查 `git diff`，再把现有 WIP 迁移到 `feature/m3a-vector-store`；
迁移后应确认 `master` 不再承载该 WIP。

### 工作项

- [ ] 审查 `platform/app/vector_store.py` 的协议、SQLite 实现、线性实现和迁移逻辑。
- [ ] 删除 `platform/app/retrieval.py` 中的无用变量，修复配置注释乱码。
- [ ] 确认 `SA_VECTOR_STORE`、`SA_VECTOR_STORE_PATH` 在根目录和 `platform/` 启动方式下行为一致。
- [ ] 检查空索引、重复 upsert、内容变化、模型变化、维度不一致和重启恢复。
- [ ] 保持 sentence-transformers 不可用时的 BM25 fallback。
- [ ] 将代码、测试、配置和文档拆成可读的原子提交。

### 建议提交拆分

```text
feat(platform): add persistent sqlite vector store
test(platform): cover vector store migration cases
docs(platform): document vector store configuration
```

### 验收门禁

- [ ] `tests/M3a/`：22 项通过。
- [ ] `tests/M0_M2/`：18 项通过。
- [ ] `tests/regression/`：21 项通过。
- [ ] `platform/tests/`：40 项通过。
- [ ] `git diff --check` 和 Python 编译检查通过。
- [ ] `README.md`、`platform/README.md`、`docs/PLAN.md` 已反映 M3a 的真实状态。
- [ ] 人工检查 SQLite 文件、缓存、`.venv` 未进入 Git。

### 合并方式

```powershell
git switch master
git pull --ff-only origin master
git merge --no-ff feature/m3a-vector-store -m "merge: complete M3a vector store migration"
```

合并前必须由人工确认测试结果；合并后再开始 M3b 分支。

### 阶段二：M3b 可观测性落地

**目标**：把当前 M3b 测试骨架中的占位断言转化为真实的健康检查、结构化日志和延迟指标。

**建议分支**：`feature/m3b-observability`

**分支起点**：M3a 已通过验收并以 `--no-ff` 合并到最新 `master` 后创建。

### 工作项

- [ ] 为 `/health` 增加稳定字段：`vector_engine`、`knowledge_root`、`index_size`、`cache_status`、`avg_latency_ms`。
- [ ] 为搜索和 QA 增加结构化日志，至少记录操作类型、课程过滤、结果数量和耗时。
- [ ] 日志中不得输出 API key、密码、token 或完整敏感环境变量值。
- [ ] 记录检索延迟和重复请求的缓存表现，明确统计口径。
- [ ] 将 `tests/M3b/` 中注释掉的断言改为实际断言。
- [ ] 保持 `/health`、搜索、QA 现有 API 契约不破坏。

### 建议提交拆分

```text
feat(platform): add retrieval observability
test(platform): verify health metrics and log redaction
docs(platform): document observability fields
```

### 验收门禁

- [ ] M3b 测试不再依赖占位断言。
- [ ] `/health` 字段稳定且不泄露敏感值。
- [ ] 搜索和 QA 均能产生日志，日志包含耗时和结果数量。
- [ ] 重复检索的延迟和缓存状态可以被测试或健康检查观察。
- [ ] M0_M2、M3a、M3b 和 regression 全部通过。
- [ ] 记录一次基线延迟和一次优化后的对比数据，写入 `docs/baselines.md` 或平台文档。

### 阶段三：M3c 面经库建设

**目标**：建立可被检索、可被 QA 引用、可支持项目追问的面经知识库。

**建议分支**：`feature/m3c-interview-bank`

**分支起点**：M3b 已合并到最新 `master` 后创建。

### 内容规模

至少 50 条 Markdown 面经条目，建议按以下结构分配：

| 类别 | 数量建议 |
| --- | ---: |
| OS 面试题 | 15 |
| DS 面试题 | 10 |
| CO 面试题 | 10 |
| RAG/Agent 工程题 | 10 |
| 项目介绍、系统设计和追问 | 5 |
| 合计 | 50 |

### 工作项

- [ ] 创建 `knowledge/interview/README.md`，说明目录结构、主题导航和写作规范。
- [ ] 每条记录包含规范 frontmatter：`title`、`course`、`tags`、`difficulty`、`updated`。
- [ ] 每条面经尽量包含问题、回答要点、项目结合点和可继续追问方向。
- [ ] 覆盖 OS、DS、CO 三门课程，并覆盖 RAG/Agent 项目追问。
- [ ] 验证面经能进入索引、搜索结果和 QA 来源。
- [ ] 不复制外部原始资料，只保留必要的提炼内容和引用路径。
- [ ] 同步更新 `knowledge/README.md`、根 README 和必要的面试文档。

### 建议提交拆分

```text
docs(interview): add interview bank navigation
docs(interview): add course interview entries
test(interview): validate interview bank coverage
```

### 验收门禁

- [ ] `knowledge/interview/` 至少 50 条非二进制 Markdown 条目。
- [ ] M3c 10 项测试全部通过，不再条件跳过。
- [ ] OS、DS、CO 三门课程均有面经覆盖。
- [ ] 面经可以通过搜索召回，并在 QA 响应中作为来源出现。
- [ ] 课程 README、知识库总 README、根目录导航保持一致。

### 阶段四：M3d 文档闭环与最终回归

**目标**：统一项目状态、文档导航、测试统计和 M3 退出条件，形成可演示、可维护的交付基线。

**建议分支**：`docs/m3d-project-closure`

**分支起点**：M3c 已合并到最新 `master` 后创建。

### 工作项

- [ ] 修订 `docs/PLAN.md`，准确标记 M3a、M3b、M3c、M3d 状态。
- [ ] 更新根 README 的当前状态、功能表、目录树和测试统计。
- [ ] 更新 `platform/README.md` 的配置、健康检查和可观测性说明。
- [ ] 更新 `docs/plans/README.md` 和 `docs/README.md` 的文档导航。
- [ ] 检查所有内部 Markdown 链接和课程导航。
- [ ] 重新确认 M3 退出条件，尤其是“三门课程各 20 篇”与当前 15/10/10 条目的差距。
- [ ] 如果仍保留“三门课程各 20 篇”作为退出条件，另开独立知识库分支补齐，不在文档中静默降低标准。

### 验收门禁

- [ ] `tests/M0_M2/`、`tests/M3a/`、`tests/M3b/`、`tests/M3c/`、`tests/M3d/` 全部通过。
- [ ] `tests/regression/` 和 `platform/tests/` 全部通过。
- [ ] 根 README、`docs/PLAN.md`、各级 README 的状态和数量一致。
- [ ] M3 退出条件有明确的“已满足/未满足”结论。
- [ ] `git diff --check` 通过，工作区只保留计划中明确的文档变更。

## 5. Git 分支与提交规范

### 5.1 分支规则

- 功能开发不得直接提交到 `master`。
- 每个阶段从**最新且已合并上一阶段的 `master`** 创建独立分支。
- 分支命名遵循：`feature/m{阶段}-{简短描述}`；纯文档收口使用 `docs/{简短描述}`。
- 每个分支尽量控制在一周内；超过一周拆成更小阶段。
- 阶段完成后使用 `git merge --no-ff`，保留阶段历史。
- 未经人工确认，不自动删除分支、不自动 push、不直接合并远程。

### 5.2 当前 M3a WIP 的迁移步骤

当前工作区不是干净的 `master`，因此严格执行以下顺序：

```powershell
# 1. 先确认改动只属于 M3a
git status --short
git diff --stat
git diff -- platform/app/vector_store.py platform/app/retrieval.py

# 2. 将现有 WIP 迁移到阶段分支，不在 master 上提交
git switch -c feature/m3a-vector-store

# 3. 在阶段分支上按文件范围拆分提交
git status --short
git add platform/app/vector_store.py platform/app/retrieval.py platform/app/config.py platform/.env.example
git commit -m "feat(platform): add persistent sqlite vector store"

# 测试和文档分别提交
git add tests/M3a/
git commit -m "test(platform): cover vector store migration cases"
git add README.md platform/README.md docs/PLAN.md
# 根据最终改动范围选择 docs scope
git commit -m "docs(platform): document vector store configuration"
```

如果审查发现 WIP 混入了无关改动，应先使用 `git restore` 或交互式暂存拆分；不得用 `git reset --hard` 粗暴丢弃用户改动。

### 5.3 提交信息规则

- 使用 Conventional Commits。
- 提交信息使用英文、动词开头、现在时、命令式，首字母小写。
- 每个提交只表达一个逻辑目的。
- 代码、测试、文档尽量分开提交。
- 提交前执行 `git status`、`git diff --check` 和对应阶段测试。
- 不提交 `.venv/`、`.pytest_cache/`、`.tmp-test/`、SQLite 缓存、模型缓存、密钥文件或二进制资料。

## 6. 跨阶段测试门禁

每一阶段都必须遵循：

```text
阶段测试 → M0_M2 基线 → regression 回归 → 文档检查 → 人工审查 → --no-ff 合并
```

建议命令：

```powershell
$py = ".\\platform\\.venv\\Scripts\\python.exe"
$base = ".\\.tmp-test\\m3"

# 阶段测试示例
& $py -m pytest tests/M3a/ -v --basetemp "$base\\m3a"

# 基线和回归
& $py -m pytest tests/M0_M2/ -v --basetemp "$base\\m0-m2"
& $py -m pytest tests/regression/ -v --basetemp "$base\\regression"

# 原始平台测试
& $py -m pytest platform/tests/ -v --basetemp "$base\\platform"

# 文档和代码检查
git diff --check
& $py -m compileall -q platform/app
```

M3c 之前，允许测试因 `knowledge/interview/` 不存在而跳过；M3c 合并后不再接受该跳过状态。M3b 合并前不接受仍依赖注释占位断言的“通过”。

## 7. 风险与决策点

| 风险/决策点 | 处理方式 |
| --- | --- |
| 当前 M3a WIP 位于 `master` 工作区 | 先迁移到 `feature/m3a-vector-store`，不在 `master` 提交功能 |
| pytest 默认临时目录权限不足 | 使用工作区 `--basetemp`；记录为环境问题，不修改业务代码 |
| 测试运行时间较长 | 先保证正确性；后续单独优化 fixture、索引初始化和缓存隔离 |
| M3b 测试存在占位断言 | 补齐真实实现和断言后才算阶段完成 |
| M3c 面经目录不存在 | 创建目录和导航后再取消条件跳过 |
| M3 退出条件要求三门各 20 篇 | M3d 阶段明确是否补齐；不静默修改目标 |
| 代码、知识库和文档容易混合冲突 | 按阶段分支和原子提交拆分，合并前更新各级 README |

## 8. 当前执行顺序

```text
M3a 收口并合并
    ↓
M3b 可观测性实现并合并
    ↓
M3c 面经库建设并合并
    ↓
M3d 文档闭环、退出条件确认与最终回归
```

当前第一项动作：**不要在 `master` 上提交现有 M3a WIP；先将其迁移到 `feature/m3a-vector-store`，然后完成 M3a 代码审查和测试验收。**
