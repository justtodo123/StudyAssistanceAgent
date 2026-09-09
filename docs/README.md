# 项目文档（docs/）

> StudyAssistanceAgent 项目文档目录。包含项目计划、外部资料索引、开发规范、面试叙事、需求澄清 PRD。

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
│   ├── document-mapping.json # Network/Interview 逐文档 P0 治理登记
│   └── {course}.md        # 各课程原始资料登记（路径、类型、状态）
├── plans/                 # 学习计划、项目执行计划、计划辅助调查
│   ├── README.md          # 计划目录说明
│   ├── references/        # 辅助计划决策的分析与事实调查
│   │   ├── README.md
│   │   ├── agent-alignment-analysis.md
│   │   ├── recruitment-driven-feasibility.md
│   │   ├── stage-advancement-analysis.md
│   │   ├── m8-v7-authorization-20260908.md # V7 仅-smoke 待签范围记录；尝试已 INVALID
│   │   ├── m8-v8-authorization-20260908.md # V8 历史授权已消费并失效；执行已 INVALID
│   │   ├── m8-v9-authorization-20260909.md # V9 PRE_FREEZE_STATIC_AUDIT_FAILED；不可授权
│   │   ├── m8-v10-authorization-20260909.md # V10 PRE_SOURCE_GOVERNANCE_INVALID；不可授权
│   │   ├── m8-v11-authorization-20260909.md # V11 PRE_SOURCE_PROVENANCE_INVALID；授权已消费
│   │   ├── m8-v12-authorization-20260909.md # V12 阶段 1 授权已消费；V12 已封口
│   │   ├── m8-v12-disposition-20260909.md # V12 永久处置；不可复用
│   │   ├── m8-v12-independent-static-audit-20260909.md # V12 历史审计 PASS 已失效
│   │   └── m8-v12-independent-static-audit-fail-20260909.md # V12 独立静态审计 FAIL
│   ├── m3-engineering-execution-plan.md
│   ├── m4-knowledge-base-scale-plan.md
│   ├── m5-agent-session-delivery-plan.md
│   ├── m6a-harness-skeleton-plan.md
│   ├── m6b-agent-core-plan.md
│   ├── m7-source-lifecycle-plan.md
│   ├── m7-p0-corpus-governance-report.md # P0 文档级语料治理结果与未解决项
│   ├── data-expansion-runbook.md # M7 数据扩展非权威未来参考；不批准语料
│   ├── m8-specialized-storage-plan.md
│   ├── m8-v7-admission-protocol.md # V7 静态冻结协议；执行尝试已 INVALID
│   ├── m8-v8-admission-protocol.md # V8 历史冻结协议；执行已 INVALID
│   ├── m8-v9-admission-protocol.md # V9 PRE_FREEZE_STATIC_AUDIT_FAILED；不可复用
│   ├── m8-v10-admission-protocol.md # V10 PRE_SOURCE_GOVERNANCE_INVALID；不可复用
│   ├── m8-v11-admission-protocol.md # V11 PRE_SOURCE_PROVENANCE_INVALID；不可复用
│   ├── m8-v12-admission-protocol.md # V12 INDEPENDENT_STATIC_AUDIT_FAILED；不可复用
│   ├── m9-goal-driven-planning-plan.md
│   └── m10-autonomous-runner-plan.md
├── standards/             # 开发规范
│   ├── git-conventions.md # Git 提交规范（Conventional Commits）
│   ├── runtime-contracts.md # 数据源门禁、检索参数、错误码、质量分层
│   ├── stage-admission-gates.md # M6a–M10 阶段准入规则
│   └── stage-admission-gates.json # 阶段准入机器登记
├── interview/             # 面试叙事（AI 应用开发岗）
│   ├── README.md          # 一句话叙事 + 设计决策 + 考点映射 + 能力边界
│   └── StudyAssistanceAgent_requirement.md  # Agent 招聘对齐原始调查
└── prds/                  # 需求澄清产出的 PRD（非正式路线图）
    ├── README.md          # 目录定位、复选框约定、M6b/M7 依赖顺序
    └── study-assistance-agent-project-plan-v1.0-prd.md
```

## 各目录说明

### demo.md — 离线演示手册

一键启动、工作台学习闭环和真实工具调用链。详见 [demo.md](demo.md)。

### PLAN.md — 项目计划

核心文件。定义项目定位（通用学习 Agent harness）、技术选型与里程碑；M0–M7 已收口，M8–M10 仍阻断。
**每次会话开工前先看本文档**，明确当前里程碑与退出条件。

### prds/ — 需求澄清 PRD

存放 requirements-clarity 技能产出的产品需求文档，用于记录澄清结论、推荐实现与验收口径。
目录说明见 [prds/README.md](prds/README.md)；当前 PRD：[prds/study-assistance-agent-project-plan-v1.0-prd.md](prds/study-assistance-agent-project-plan-v1.0-prd.md)。
PRD 不能替代 [PLAN.md](PLAN.md)，也不能单独批准 M6a–M10。

### plans/ — 学习计划与项目工程执行计划

- 个人复习计划由 `review-plan` Skill 或 API 生成。
- M3 执行记录见 [plans/m3-engineering-execution-plan.md](plans/m3-engineering-execution-plan.md)，已于 2026-08-18 合并到 `master`。
- M4 知识库规模计划见
  [plans/m4-knowledge-base-scale-plan.md](plans/m4-knowledge-base-scale-plan.md)，课程条目已补齐，实现提交 `106164d` 已进入 `master`。
- M5 会话化与交付计划见
  [plans/m5-agent-session-delivery-plan.md](plans/m5-agent-session-delivery-plan.md)，已作为 MVP 冻结。
- M6a/M6b 执行计划：
  [plans/m6a-harness-skeleton-plan.md](plans/m6a-harness-skeleton-plan.md)（契约与兼容骨架；M6a-1 协议契约与 M6a-2 默认包适配的自动化门禁已通过，M6a-3 与 M6a-4 已完成）和
  [plans/m6b-agent-core-plan.md](plans/m6b-agent-core-plan.md)（独立只读原生工具调用预览）。M6a 当前为
  `ADMITTED / COMPLETE`。M6b 已完成 M6a 退出证据、八项强制决策、专属保护基线和独立人工批准，当前为
  `ADMITTED / COMPLETE`；获批的默认关闭只读 preview 已完成全部 closeout 门禁与证据同步；准入规则见
  [standards/stage-admission-gates.md](standards/stage-admission-gates.md)，
  机器登记见 [standards/stage-admission-gates.json](standards/stage-admission-gates.json)。M6b/M7 以 M6a 退出证据为
  共同必要前置，彼此不互为前置。M7 的决策、保护基线、基础设施范围准入与生产开工授权已闭合，并于
  2026-09-06 在 `m7-infrastructure-only-v1` 范围内取得独立人工完成批准，当前为 `ADMITTED / COMPLETE`。
  Source Registry、manifest/parser、normalized document、source-local FULL/INCREMENTAL/delete/isolation、FTS5/vector/offline
  fail-closed 与 Search/QA 内部可信 principal overlay 已完成；技术证据本身不产生批准。M8/M9/M10 的事实型
  M7 退出前置已满足，但阶段仍阻断；Network/M8/Milvus/M9/M10 未获批。
- M7–M10 准入准备计划：
  [plans/m7-source-lifecycle-plan.md](plans/m7-source-lifecycle-plan.md)、
  [plans/m8-specialized-storage-plan.md](plans/m8-specialized-storage-plan.md)、
  [plans/m8-v7-admission-protocol.md](plans/m8-v7-admission-protocol.md)（静态协议曾通过审阅，但 V7 尝试已因顺序违规
  `INVALID`；处置见主 M8 计划 §3.21.13）、
  [plans/m8-v8-admission-protocol.md](plans/m8-v8-admission-protocol.md)（历史冻结；协议文本曾通过独立静态审阅，但执行根已
  `INVALID`，不得继续或复用）、
  [plans/m8-v9-admission-protocol.md](plans/m8-v9-admission-protocol.md)（`PRE_FREEZE_STATIC_AUDIT_FAILED`；身份与根
  永久冻结且不可复用）、[plans/m8-v10-admission-protocol.md](plans/m8-v10-admission-protocol.md)
  （`PRE_SOURCE_GOVERNANCE_INVALID`；身份与根不可复用）、
  [plans/m8-v11-admission-protocol.md](plans/m8-v11-admission-protocol.md)
  （`PRE_SOURCE_PROVENANCE_INVALID`；身份、根与 source 不可复用）和
  [plans/m8-v12-admission-protocol.md](plans/m8-v12-admission-protocol.md)
  （阶段 1 已 source freeze，但独立静态审计 `FAIL`；`INDEPENDENT_STATIC_AUDIT_FAILED` 不可复用）、
  [plans/m9-goal-driven-planning-plan.md](plans/m9-goal-driven-planning-plan.md)、
  [plans/m10-autonomous-runner-plan.md](plans/m10-autonomous-runner-plan.md)。计划存在只代表设定澄清准备，不能推导实现或批准。
- M7 P0 语料治理结果见
  [plans/m7-p0-corpus-governance-report.md](plans/m7-p0-corpus-governance-report.md)：82 篇 mapping 已建立，但 Network
  31 篇仍缺逐文档 URL/原创与许可闭环，当前停止等待人工复核。
- 当前 M6b 不接管正式学习会话；完整自主 Runner、写工具、checkpoint/幂等和 Agent 评测后移 M10。
- 默认 RAG 评测仍为 OS/DS/CO 三课 90 题；Network 评测集为显式运行的独立扩展。
- `plans/references/` 只存放辅助决策的分析与事实调查，**不能作为最终支撑来源**。V7 仅-smoke 待签范围记录见
  [plans/references/m8-v7-authorization-20260908.md](plans/references/m8-v7-authorization-20260908.md)；V8 历史授权记录见
  [plans/references/m8-v8-authorization-20260908.md](plans/references/m8-v8-authorization-20260908.md)，现已消费并失效。
  V9 未授权状态见
  [plans/references/m8-v9-authorization-20260909.md](plans/references/m8-v9-authorization-20260909.md)，已登记为
  `PRE_FREEZE_STATIC_AUDIT_FAILED`；V10 未授权状态见
  [plans/references/m8-v10-authorization-20260909.md](plans/references/m8-v10-authorization-20260909.md)，已登记为
  `PRE_SOURCE_GOVERNANCE_INVALID`；V11 历史授权与失败处置见
  [plans/references/m8-v11-authorization-20260909.md](plans/references/m8-v11-authorization-20260909.md)，V12 阶段 1
  授权见 [plans/references/m8-v12-authorization-20260909.md](plans/references/m8-v12-authorization-20260909.md)。
  V12 独立静态审计最终 `FAIL`，报告见
  [plans/references/m8-v12-independent-static-audit-fail-20260909.md](plans/references/m8-v12-independent-static-audit-fail-20260909.md)，
  永久处置见
  [plans/references/m8-v12-disposition-20260909.md](plans/references/m8-v12-disposition-20260909.md)；V12 已封口且不可复用，
  未取得 preflight 或执行授权。

### reference/ — 外部资料索引

映射层：将 `D:\111_Others_Subjects` 中的原始资料目录登记为可检索的索引。
- 主索引：[reference/README.md](reference/README.md) — 按优先级分类（核心专业课 / 专业拓展 / 其他）
- 各课程索引：`reference/{course}.md` — 记录该课程原始资料的路径、文件类型、整理状态
- 文档级 P0 治理：[reference/document-mapping.json](reference/document-mapping.json) — 登记 Network/Interview 82 篇正文的
  稳定身份、来源、审核与许可状态；不作为 M7 runtime provenance、生产开工或 Network 晋升批准
- 只读盘点：`tools/source_inventory.py` 输出文件级 manifest，区分工程文件与学习资料；`study_document` 仅表示
  candidate 分类，不能授权入库或发布

**维护规则**：
- 新增外部资料 → 在 [reference/README.md](reference/README.md) 中加一行，并新建/追加对应课程索引文件
- 某课程已整理笔记 → 将状态改为 `📝 笔记已建`
- 更新知识库时同步刷新本索引

### standards/ — 开发规范

- [git-conventions.md](standards/git-conventions.md)：Conventional Commits 规范，含类型表、scope 约定、撤销速查
- [runtime-contracts.md](standards/runtime-contracts.md)：数据源类型与入库门禁、embedding/索引参数、稳定错误码、生成分层与 P99
- [stage-admission-gates.md](standards/stage-admission-gates.md)：M6a–M10 决策、准入、撤销、批准与阻断规则
- [stage-admission-gates.json](standards/stage-admission-gates.json)：供文档回归读取的机器可读状态登记

### interview/ — 面试叙事

面向 **AI 应用开发岗** 的面试备战文档：
- 一句话项目叙事
- 5 个设计决策与能力映射
- 考点映射、数据驱动优化实锤、常见追问
- 现行能力边界：正式路径是领域状态机；M6b 另有默认关闭的只读 native tool-call preview，不是 ReAct 或完整自主 Runner
- 招聘对齐原始调查： [interview/StudyAssistanceAgent_requirement.md](interview/StudyAssistanceAgent_requirement.md)

---

## 文档维护规范

1. **每次改动后，及时更新对应的 README.md**：若改动涉及目录结构、新增文件、API 变更、状态变化，务必同步刷新从当前目录到项目根目录的各级 README。
2. **PLAN.md 随里程碑推进更新**：完成一个里程碑后标记为 ✅ 并记录关键产出。
3. **reference/ 索引与知识库同步**：笔记入库时更新对应课程索引状态。
4. **所有文档使用中文**，Markdown 格式，行宽 ≤ 120 字符。

---

*创建：2026-08-11 · 更新：2026-09-09（V8–V12 已分别失败封口且不可复用；Network/M8/Milvus/M9/M10 未获批）·维护：随项目演进同步更新*
