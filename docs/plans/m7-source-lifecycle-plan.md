# M7 用户 Source 生命周期与千级检索准备计划

> 当前状态：设计准备；`BLOCKED / NOT_STARTED`，未获准开工
> 前置：M6a Source 契约与兼容骨架退出证据；另须独立形成 M7 保护基线证据并完成本阶段准入批准
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)

## 1. 范围与非目标

M7 在 M6a 稳定 Source identity 和静态快照边界后，规划用户源持久化注册、同步、删除、多源隔离以及
1k–3k chunk 可复现检索。它不迁移到 LanceDB/Qdrant，不实现目标规划或自主 Runner，也不把外部原始
PDF/PPT 复制进仓库。

本计划存在只表示准备工作。所有设定、证据和批准闭合前，不得创建生产 Source Registry、同步 worker、
schema migration、依赖、API 或运行时开关。

## 2. 前置证据与继承不变量

| Prerequisite ID | 当前状态 | 准入所需证据 |
| --- | --- | --- |
| `M7-M6A-SOURCE-CONTRACT` | `OPEN` | M6a identity、额外源校验、generation 切换、缓存失效和路径隐私的退出证据 |
| `M7-PROTECTED-BASELINE` | `OPEN` | M7 专属 workload、p50/p95、资源、成本、质量阈值及现有保护基线复验方案的证据 |

M7 完整继承统一准入政策中的 M0–M5 不变量：正式状态转换继续由 `StudySessionService` 掌握；旧 SQLite
session 可恢复；默认 OS/DS/CO 90 题和 Network 显式扩展边界不变；默认离线路径不依赖外部模型或新服务；
对外结果、日志和 trace 不泄露宿主机绝对路径。

## 3. 强制决策

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M7-LIFECYCLE-SCHEMA` | `OPEN` | Source/revision/sync/error/audit 的版本化 schema、状态转换、约束、升级兼容和权威写入者 |
| `M7-SYNC-SEMANTICS` | `OPEN` | 全量/增量同步、并发、重试、取消、中断恢复、generation 可见性和 last-good snapshot |
| `M7-DELETE-SEMANTICS` | `OPEN` | delete/tombstone/保留期/硬删除/恢复，以及 BM25/vector/result cache 的删除传播与可证明完成条件 |
| `M7-ISOLATION` | `OPEN` | learner/source namespace、授权模型、查询 filter、跨源隔离和越权拒绝语义 |
| `M7-FTS5-TOKENIZER` | `OPEN` | 中文 tokenizer 明确选型、规范化、打包可用性、索引兼容和不可用 fallback |
| `M7-SCALE-LIMITS` | `OPEN` | source/document/chunk/bytes 上限，同步、增量更新、重建和查询支持目标及超限行为 |
| `M7-BENCHMARK` | `OPEN` | 可复现 1k/3k chunk fixture、中文查询与标注、Recall@k、p50/p95、索引大小、同步/重建时间、硬件、样本数和阈值 |
| `M7-OFFLINE-FALLBACK` | `OPEN` | 无可选 tokenizer/vector、索引损坏或用户源不可用时的离线启动、查询、修复和用户可见错误语义 |

每项只有按统一政策记录明确选定值、默认与覆盖、校验/失败行为、兼容/隐私影响、适用阈值、证据、责任人和
日期后才能标为 `RESOLVED`。候选项、`TBD`、无 workload 的数字或“实施时决定”都保持 `OPEN`。

## 4. 准入检查与批准记录

- [ ] M6a Source 契约及保护基线退出证据真实有效；
- [ ] 八项强制决策全部为 `RESOLVED`，阶段计划与登记表证据一致；
- [ ] 生命周期状态机、删除传播、隔离和离线 fallback 可通过契约/故障注入方案验证；
- [ ] benchmark fixture、workload、硬件和阈值在写性能代码前冻结；
- [ ] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表状态一致；
- [ ] 用户或项目负责人完成批准。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | — |
| approved_at | — |
| approval_reference | — |
| plan_revision | — |
| decision_set_version | — |

批准为空，M7 保持 `BLOCKED / NOT_STARTED`。Agent 不得自行批准。

## 5. 获准后的拟实施顺序

1. 先落地版本化 lifecycle schema、repository contract 和迁移/回滚测试；
2. 实现单源完整快照，再实现受限增量同步和并发/中断语义；
3. 实现 tombstone、索引/cache 删除传播和隔离过滤；
4. 在离线 fallback 可用后接入明确选定的 FTS5 tokenizer；
5. 运行冻结的 1k/3k workload，根据证据决定是否进入 M8，而不是预先引入专业后端。

拟新增测试仅作为获准后方案：`tests/M7/` 覆盖 lifecycle、sync、delete、isolation、fallback；benchmark 使用可生成
fixture，不把用户原始材料提交到 Git。退出条件包括所有契约/保护回归通过、默认 90 题不退化、删除后各索引
不可召回、隔离零越权，以及冻结 benchmark 达标。

## 6. 撤销与后续边界

任何 identity、删除、隔离、tokenizer 或 benchmark 前提实质变化，都将已准入状态改为 `REVOKED` 并停止实施。
M8 只能使用 M7 的真实退出证据，不能把本计划或 collect-only 当作专业存储开工依据。
