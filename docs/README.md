# 项目文档（docs/）

> StudyAssistanceAgent 项目文档目录。包含项目计划、外部资料索引、开发规范、面试叙事。

## 文档结构

```
docs/
├── README.md              # 本导航文件
├── PLAN.md                # ★ 项目计划与路线图（里程碑、技术选型、风险）
├── baselines.md            # RAG 评测基线记录（keyword-only vs hybrid 对比）
├── demo.md                 # 离线演示手册（一键启动 + 学习闭环）
├── reference/             # 外部参考资料索引
│   ├── README.md          # 索引总览与维护规则
│   ├── _template.md       # 新课程索引模板
│   └── {course}.md        # 各课程原始资料登记（路径、类型、状态）
├── plans/                 # 学习计划、项目执行计划、计划辅助调查
│   ├── README.md          # 计划目录说明
│   ├── references/        # 辅助计划决策的分析与事实调查
│   │   ├── README.md
│   │   ├── agent-alignment-analysis.md
│   │   ├── recruitment-driven-feasibility.md
│   │   └── stage-advancement-analysis.md
│   ├── m3-engineering-execution-plan.md
│   ├── m4-knowledge-base-scale-plan.md
│   ├── m5-agent-session-delivery-plan.md
│   ├── m6a-harness-skeleton-plan.md
│   └── m6b-agent-core-plan.md
├── standards/             # 开发规范
│   ├── git-conventions.md # Git 提交规范（Conventional Commits）
│   └── runtime-contracts.md # 数据源门禁、检索参数、错误码、质量分层
└── interview/             # 面试叙事（AI 应用开发岗）
    ├── README.md          # 一句话叙事 + 设计决策 + 考点映射 + 能力边界
    └── StudyAssistanceAgent_requirement.md  # Agent 招聘对齐原始调查
```

## 各目录说明

### demo.md — 离线演示手册

一键启动、工作台学习闭环和真实工具调用链。详见 [demo.md](demo.md)。

### PLAN.md — 项目计划

核心文件。定义项目定位（通用学习 Agent harness）、技术选型、里程碑（M0~M5 MVP，M6+ 规划中）。
**每次会话开工前先看本文档**，明确当前里程碑与退出条件。

### plans/ — 学习计划与项目工程执行计划

- 个人复习计划由 `review-plan` Skill 或 API 生成。
- M3 执行记录见 [plans/m3-engineering-execution-plan.md](plans/m3-engineering-execution-plan.md)，已于 2026-08-18 合并到 `master`。
- M4 知识库规模计划见
  [plans/m4-knowledge-base-scale-plan.md](plans/m4-knowledge-base-scale-plan.md)，课程条目已补齐，实现提交 `106164d` 已进入 `master`。
- M5 会话化与交付计划见
  [plans/m5-agent-session-delivery-plan.md](plans/m5-agent-session-delivery-plan.md)，已作为 MVP 冻结。
- M6a/M6b 执行计划：
  [plans/m6a-harness-skeleton-plan.md](plans/m6a-harness-skeleton-plan.md)（契约与兼容骨架，前置 crawler 收口）和
  [plans/m6b-agent-core-plan.md](plans/m6b-agent-core-plan.md)（独立只读原生工具调用预览）。
- 当前 M6b 不接管正式学习会话；完整自主 Runner、写工具、checkpoint/幂等和 Agent 评测后移 M10。
- 默认 RAG 评测仍为 OS/DS/CO 三课 90 题；Network 评测集为显式运行的独立扩展。
- `plans/references/` 只存放辅助决策的分析与事实调查，**不能作为最终支撑来源**。

### reference/ — 外部资料索引

映射层：将 `D:\111_Others_Subjects` 中的原始资料目录登记为可检索的索引。
- 主索引：[reference/README.md](reference/README.md) — 按优先级分类（核心专业课 / 专业拓展 / 其他）
- 各课程索引：`reference/{course}.md` — 记录该课程原始资料的路径、文件类型、整理状态

**维护规则**：
- 新增外部资料 → 在 [reference/README.md](reference/README.md) 中加一行，并新建/追加对应课程索引文件
- 某课程已整理笔记 → 将状态改为 `📝 笔记已建`
- 更新知识库时同步刷新本索引

### standards/ — 开发规范

- [git-conventions.md](standards/git-conventions.md)：Conventional Commits 规范，含类型表、scope 约定、撤销速查
- [runtime-contracts.md](standards/runtime-contracts.md)：数据源类型与入库门禁、embedding/索引参数、稳定错误码、生成分层与 P99

### interview/ — 面试叙事

面向 **AI 应用开发岗** 的面试备战文档：
- 一句话项目叙事
- 5 个设计决策与能力映射
- 考点映射、数据驱动优化实锤、常见追问
- 现行能力边界：领域状态机编排，不是 ReAct / Function Calling；与 PLAN v2.2 / runtime-contracts 同一口径
- 招聘对齐原始调查： [interview/StudyAssistanceAgent_requirement.md](interview/StudyAssistanceAgent_requirement.md)

---

## 文档维护规范

1. **每次改动后，及时更新对应的 README.md**：若改动涉及目录结构、新增文件、API 变更、状态变化，务必同步刷新从当前目录到项目根目录的各级 README。
2. **PLAN.md 随里程碑推进更新**：完成一个里程碑后标记为 ✅ 并记录关键产出。
3. **reference/ 索引与知识库同步**：笔记入库时更新对应课程索引状态。
4. **所有文档使用中文**，Markdown 格式，行宽 ≤ 120 字符。

---

*创建：2026-08-11 · 更新：2026-08-20（定位改为通用学习 Agent harness）· 维护：随项目演进同步更新*
