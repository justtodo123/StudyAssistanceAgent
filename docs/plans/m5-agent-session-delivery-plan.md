# M5 学习 Agent 会话化与可交付演示计划

> 版本：v1.0
> 制定日期：2026-08-18
> 当前状态：M5a 已完成，下一步 M5b
> 适用范围：RAG 评测入口、学习会话编排、学习状态持久化、最小交互界面和可复现交付

## 1. 背景

M0 至 M4 已完成知识库、混合检索、问答、测验、复习计划、复习排程、可观测性和课程规模建设。
当前项目已经具备 8 个 API 端点、60 篇课程条目、51 条面经和 90 道评测题，但能力仍以独立 API、Skill
和测试代码为主要入口，尚未形成可持续使用的后端学习会话。

检索发现的主要缺口：

- `platform/tests/test_study_assistant.py` 通过测试代码顺序调用 QA、Quiz 和 Review 服务，没有正式会话协调器；
- `platform/app/main.py` 没有统一的学习会话 API，也没有会话状态和工具调用轨迹；
- 复习历史存储在单个 `review_history.json`，没有答题结果、掌握度和会话恢复能力；
- `tools/run_evaluation.py` 默认只运行 3 个内置示例，不能一条命令评测现有三课 90 题；
- 当前没有面向完整学习闭环的最小交互工作台，也没有离线 CI 或一键交付入口。

因此，M5 不继续追求课程数量，而是把已有能力组织成一个可验证、可恢复、可演示的学习 Agent。

## 2. 阶段目标与非目标

### 2.1 阶段目标

1. 建立统一、离线可复现的三课 RAG 评测入口。
2. 实现服务端学习会话状态机，真实编排 QA、Quiz、掌握度评估和 Review-log。
3. 持久化学习会话、答题结果和掌握度，支持服务重启后恢复。
4. 提供完成学习闭环所需的最小交互工作台。
5. 建立不依赖 Hugging Face 下载和外部 LLM 的基础 CI/演示路径。

### 2.2 非目标

- 不在 M5 第一轮继续扩充课程条目或新增课程；
- 不自研通用 Agent 框架，继续复用现有 QA、Quiz 和 Review 服务；
- 不在第一轮实现用户系统、权限、多人协作或云端同步；
- 不要求外部 LLM 或 BGE 模型作为基础验收前提；
- 不为展示效果引入与个人学习场景无关的复杂前端框架。

## 3. 阶段拆分

### M5a：评测入口可复现化

目标：让仓库中的 90 道评测题通过一条命令完整执行，并产生可比较结果。

任务：

- 让 `tools/run_evaluation.py` 支持自动发现并运行 OS、DS、CO 三个评测集；
- 保留 `--test-set` 单文件模式，增加课程筛选和汇总结果；
- 支持控制台输出和 JSON 报告，记录模式、题数、Recall@k、Precision@k、F1 和延迟；
- 默认使用 `SA_USE_VECTOR=false` 的离线 BM25 基线，向量评测作为显式可选模式；
- 同步 `tools/README.md`、`docs/baselines.md` 和实际 38/28/24 题统计；
- 在 `tests/M5a/` 增加参数解析、评测集发现、聚合计算和报告格式测试。

退出条件：

- 一条命令完整评测三课 90 题；
- 三课 Recall@3 均不低于 0.8；
- 无网络、无模型缓存、无 LLM key 时可重复执行；
- 报告不写入 Git 跟踪范围，除非人工确认作为新基线提交。

### M5b：学习会话状态机

目标：把现有服务调用链变成正式后端能力，而不是只在测试和 Skill 中手工串联。

建议状态：

```text
created
  -> explaining
  -> awaiting_answer
  -> evaluating
     -> remediation -> awaiting_answer
     -> completed
```

最小 API：

```text
POST /api/v1/study-sessions
GET  /api/v1/study-sessions/{session_id}
POST /api/v1/study-sessions/{session_id}/answers
```

任务：

- 新增 `StudySessionService`，只负责编排，不复制检索、出题或排程算法；
- 创建会话时执行 QA 检索与讲解，再生成 1 至 2 道相关题目；
- 提交答案后执行确定性基础评估；LLM 评估仅作为可选增强；
- 答对时完成会话并记录复习，答错时进入补充讲解和重试；
- 连续两次答错后返回完整参考讲解，避免无限循环；
- 响应中保留来源文件、当前状态、尝试次数、得分和工具调用轨迹；
- 在 `tests/M5b/` 增加状态转换、错误分支、降级路径和 API 契约测试。

退出条件：

- 一个 API 会话可完成“检索→讲解→出题→作答→评估→记录复习”；
- 状态转换由服务控制，非法转换返回明确错误；
- 不配置 LLM 时完整链路仍可运行；
- 工具调用轨迹能说明每一步使用的服务、结果数量和状态变化。

### M5c：学习状态持久化

目标：让学习进度从临时 JSON 文件升级为可恢复的本地状态。

任务：

- 定义 `StudySessionRepository` 和 `ReviewHistoryRepository` 接口；
- 使用标准库 SQLite 保存会话、答题记录、掌握度和复习历史；
- 提供现有 `review_history.json` 的一次性迁移或兼容读取；
- 保证重复提交答案和重复记录复习具备明确的幂等行为；
- 增加重启恢复、迁移、并发写入和损坏降级测试。

退出条件：

- 服务重启后可以恢复未完成会话和历史进度；
- 现有复习历史不因升级丢失；
- SQLite 文件继续位于 `platform/.cache/`，不得进入 Git。

### M5d：最小学习工作台

目标：让用户无需直接调用 REST API，也能完成一次学习闭环。

最小视图：

- 今日待复习；
- 主题输入与课程选择；
- 知识讲解和来源列表；
- 单题作答、反馈与补充讲解；
- 会话完成结果和下次复习日期。

约束：

- 优先使用 FastAPI 可直接提供的轻量 Web 资源，避免先引入复杂前端工程；
- 不做营销首页，首屏直接进入学习工作台；
- 不在第一版加入账号、社交、主题商店或复杂可视化；
- 前端只调用正式会话 API，不复制业务状态机。

### M5e：可复现交付

目标：让项目可以在新环境中稳定启动、测试和演示。

任务：

- 增加离线 BM25 模式的 CI，运行阶段测试、回归测试和评测冒烟；
- 提供一条本地启动命令和健康检查；
- 明确可选 BGE 模型的预下载、缓存目录和离线启动方式；
- 记录冷启动、热启动和完整学习会话的延迟基线；
- 更新项目演示文档和面试叙事中的真实工具调用链。

## 4. 分层验收与范围控制

为避免再次出现“核心任务已完成，但完整验收长期阻塞可见结果”，M5 使用两级验收。

### Level 1：第一轮最小交付

只包含 M5a 和 M5b：

- 三课 90 题一键离线评测；
- 服务端学习会话状态机；
- 3 个最小会话 API；
- M5a/M5b 阶段测试和现有回归测试；
- 对应 API 与计划文档。

Level 1 不要求 SQLite 会话持久化、Web 工作台、CI 或向量模型部署。上述任务不得阻塞第一轮提交。

### Level 2：完整 M5 交付

包含 M5c、M5d 和 M5e：

- 会话与学习进度持久化；
- 最小学习工作台；
- 离线 CI 和一键启动；
- 完整演示与性能基线。

### 时间盒规则

- 每个子阶段独立分支、独立测试、独立提交；
- 单次执行超过 30 分钟仍未形成可审查产物时，先提交已完成检查点；
- 非核心验收失败时记录待办，不扩大当前子阶段；
- 完整根级和平台测试仅在共享行为变化或准备合并时运行。

## 5. 测试策略

新增测试遵循阶段隔离，不修改 M0 至 M4 存量测试。

```text
tests/M5a/   评测发现、聚合指标、报告格式、离线模式
tests/M5b/   会话状态机、API 契约、答对/答错分支、工具轨迹
tests/M5c/   SQLite 仓储、迁移、重启恢复、幂等性
tests/M5d/   工作台静态资源和关键交互冒烟
tests/M5e/   启动、健康检查、离线配置和交付检查
```

验收顺序：

```text
本子阶段测试
  -> tests/regression/
  -> tests/M0_M2/
  -> platform/tests/
  -> 三课离线 RAG 评测
  -> 文档检查
  -> 人工审查与合并
```

## 6. 数据模型与边界

建议的核心会话字段：

| 字段 | 说明 |
| --- | --- |
| `session_id` | 稳定会话 ID |
| `course` / `topic` | 课程与学习主题 |
| `state` | 当前状态机状态 |
| `sources` | QA 检索来源 |
| `questions` | 当前测验题目 |
| `attempt_count` | 当前尝试次数 |
| `score` | 掌握度评分 |
| `tool_trace` | 工具调用与状态变化摘要 |
| `created_at` / `updated_at` | 会话时间戳 |

边界约束：

- API 契约放在 `platform/app/models.py`；
- 编排逻辑放在独立 service 模块；
- 持久化通过 repository 接口访问；
- QA、Quiz、Review 服务保持单一职责；
- 用户答案、知识正文和密钥不得写入结构化运行日志。

## 7. 风险与决策

| 风险 | 决策 |
| --- | --- |
| 答案评估依赖 LLM，受网络影响 | Level 1 使用确定性规则和参考答案；LLM 仅增强 |
| 会话编排变成通用 Agent 框架 | 只支持既定学习闭环和有限状态机 |
| 前端扩大工程范围 | M5d 只做最小工作台，不阻塞 M5a/M5b |
| JSON 历史迁移导致数据丢失 | 先备份、兼容读取，再切换 SQLite |
| 评测受向量模型下载影响 | 默认离线 BM25；向量评测显式启用 |
| 测试时间再次膨胀 | 阶段定向测试优先，完整回归仅在合并前运行 |

## 8. 分支与提交建议

```text
feature/m5a-evaluation-runner
feature/m5b-study-session
feature/m5c-learning-persistence
feature/m5d-learning-workbench
chore/m5e-reproducible-delivery
docs/m5-project-closure
```

建议提交：

```text
feat(tools): add unified course evaluation runner
feat(platform): add study session orchestrator
feat(platform): persist learning sessions in sqlite
feat(web): add minimal learning workbench
chore(ci): add offline regression workflow
docs(plan): close M5 delivery milestone
```

不自动 push，不删除阶段分支，不改写历史。每个子阶段通过人工审查后以 `--no-ff` 合并到 `master`。

## 9. 下一步

M5a 已完成：`python tools/run_evaluation.py` 可离线评测三课 90 题，并输出汇总指标与 JSON 报告。
下一步只启动 M5b 学习会话状态机；不提前实现 SQLite、Web 工作台或 CI。
