# 需求澄清 PRD（prds/）

> 本目录只存放 `requirements-clarity` 产出的产品需求文档。
> **最终计划依据**仍是 [`docs/PLAN.md`](../PLAN.md)。
> PRD、阶段计划和 JSON 登记表都不能单独批准阶段；M6a/M6b 当前授权分别来自完整门禁与独立负责人批准记录。

## 目录结构

```
prds/
├── README.md                                          # 本导航：定位、复选框约定、依赖顺序
└── study-assistance-agent-project-plan-v1.0-prd.md    # 项目计划澄清 PRD v1.0
```

## 功能与定位

- 记录模糊需求被澄清后的结论、不改路线图的推荐实现，以及可检查的验收口径。
- 不替代 [`docs/PLAN.md`](../PLAN.md) 的里程碑、退出方向与当前状态。
- 不替代 [`docs/standards/stage-admission-gates.md`](../standards/stage-admission-gates.md) 的准入/撤销规则。
- 不替代 [`docs/plans/`](../plans/README.md) 中的阶段准备/执行计划。

## 复选框约定

PRD 将复选框分成三类，必须结合所在小节或行首标签解读：

- **现行保护** `[x]`：现行 M0–M5 已满足或治理规则已经生效，后续变更仍须持续保护。
- **准入复验** `[ ]`：申请阶段准入时必须重新验证并留证；通过复验仍不能替代负责人批准。
- **未来验收** `[ ]`：仅在对应阶段获 `ADMITTED` 后实施和验收；不表示已开工、已实现或已批准。
- 勾选、测试通过或 PRD 存在，都不能替代 `ADMITTED` 准入批准。

## M6b / M7 依赖顺序

以 [`docs/PLAN.md`](../PLAN.md) 与 [`stage-admission-gates.json`](../standards/stage-admission-gates.json) 为准：

- M6a-P0 crawler 已收口，只构成 M6a 前置证据。
- M6b 只依赖 M6a 退出与保护基线，不依赖 M7。
- M7 只依赖 M6a Source 契约与保护基线，不依赖 M6b。
- M6b 与 M7 彼此不互为前置；各自的 Source/退出证据和保护基线必须独立留证，专属决策与批准也必须分别闭合。
  M6b 默认关闭的只读 preview 已完成全部 closeout 门禁与证据同步，现为 `ADMITTED / COMPLETE`；M7 基础设施
  scope 的技术验收已完成，并于 2026-09-06 在 `m7-infrastructure-only-v1` 范围内取得独立人工完成批准，现为
  `ADMITTED / COMPLETE`。Network 不在 scope 内，技术证据本身不产生批准。
- M8/M9/M10 的事实型 M7 退出前置已满足；M9 已于 2026-09-22 在 `m9-plan-lifecycle-v1` 范围内取得独立完成
  批准，现为 `ADMITTED / COMPLETE`。**M10 的十一项强制决策已全部 `RESOLVED`，并于 2026-09-22 在
  `m10-autonomous-runner-v1` 范围内获批开工，并于 2026-09-23 在原范围内取得独立完成批准，现为
  `ADMITTED / COMPLETE`；`implementation_start` 保持 `AUTHORIZED`**。
  M8 仍因其他前置、强制决策和独立批准未闭合而保持 `BLOCKED / NOT_STARTED`。Milvus 未选定或获批。

## 当前文件

| 文件 | 说明 | 地位 |
| --- | --- | --- |
| [study-assistance-agent-project-plan-v1.0-prd.md](study-assistance-agent-project-plan-v1.0-prd.md) | 项目计划澄清 PRD v1.0 | 辅助澄清；最终依据是 PLAN.md |

---

*创建：2026-08-24 · 更新：2026-09-23（同步 M10 独立完成批准；M8 与 M11–M12 仍阻断）·
维护：新增/修订 PRD 时同步本表*