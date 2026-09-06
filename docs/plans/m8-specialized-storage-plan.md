# M8 专业化检索存储准备计划

> 当前状态：设计准备；`BLOCKED / NOT_STARTED`，未获准开工
> 前置：`M8-M7-EXIT=SATISFIED`；M8 自身决策与批准仍未闭合
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)

## 1. 范围与非目标

M8 在 M7 已完成 lifecycle/delete/isolation/fallback 与冻结 1k/3k 退出证据后，规划统一 control plane、后端迁移和可回滚切换。`M8-M7-EXIT` 已因技术证据与 2026-09-06 独立人工完成批准而成为 `SATISFIED`；这只关闭事实型前置，不批准 M8。LanceDB、Qdrant 和 Milvus 均未选定或获批，不得静默引入依赖或服务。学习状态、会话和复习历史继续由现有 SQLite 领域仓储负责。

本计划不实现 Source 生命周期、目标规划、自主 Runner，也不因计划文件存在而添加依赖、容器、服务、schema
migration 或生产 adapter。

## 2. 前置证据与继承不变量

| Prerequisite ID | 当前状态 | 准入所需证据 |
| --- | --- | --- |
| `M8-M7-EXIT` | `SATISFIED` | M7 lifecycle/delete/isolation/fallback contract、保护回归、冻结 1k/3k benchmark、独立完成批准；证据见 `docs/PLAN.md`、M7 计划与 `docs/baselines.md` |

继承 M0–M5 API/学习闭环、SQLite session 恢复、默认 90 题、路径隐私和默认离线能力。专业向量后端不得成为
学习状态存储，不得绕过 Source authorization，也不得使无可选依赖的本地启动失效。

## 3. 强制决策

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M8-CONTROL-SCHEMA` | `OPEN` | 后端无关的 identity/revision/metadata/schema version、control/data plane 职责、权威来源和升级规则 |
| `M8-MIGRATION` | `OPEN` | SQLite 到目标后端的导出、校验、shadow read、cutover、失败恢复、回滚、稳定 ID 和删除状态保持 |
| `M8-LANCEDB-CRITERIA` | `OPEN` | 选择或不选择 LanceDB 的规模、质量、延迟、运维、Windows/离线打包阈值和证据 |
| `M8-QDRANT-CRITERIA` | `OPEN` | 允许 Qdrant 的数据规模、并发、服务化与运维阈值；本地/离线默认不得静默转为服务依赖 |
| `M8-BACKEND-PARITY` | `OPEN` | protocol、filter、排序容差、metadata、upsert/delete、snapshot 和 error mapping 的一致性标准 |
| `M8-FALLBACK` | `OPEN` | 缺依赖、索引损坏、Qdrant 不可用、维度/模型不匹配、迁移中断和离线启动 fallback 矩阵 |
| `M8-DEPENDENCY-PACKAGING` | `OPEN` | 可选依赖分组、锁定/安装体积、平台支持、许可证、容器边界和升级/卸载影响 |
| `M8-BENCHMARK` | `OPEN` | 数据规模、查询集、质量等价、p50/p95、索引/重建时间、磁盘/内存、并发、硬件、样本数和选择阈值 |

每项必须给出单一选定政策或明确“不采用”的结论；未选择的后端列表、README 声称或无复现脚本的数字不能标为
`RESOLVED`。

## 4. 准入检查与批准记录

- [x] M7 退出证据与独立完成批准证明 lifecycle、delete、isolation 和 fallback 已稳定；
- [ ] 八项强制决策全部 `RESOLVED`，依赖加入前已完成选择与打包决策；
- [ ] migration/cutover/rollback 和 backend parity 有可执行测试方案；
- [ ] benchmark 能比较当前 SQLite linear/BM25 与候选后端，并冻结 workload/阈值；
- [ ] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表一致；
- [ ] 用户或项目负责人完成批准。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | — |
| approved_at | — |
| approval_reference | — |
| plan_revision | — |
| decision_set_version | — |

批准为空，M8 保持 `BLOCKED / NOT_STARTED`。M7 已完成只关闭 `M8-M7-EXIT`，不解决 M8 的八项强制决策或批准；Milvus 也不是已选后端。
Agent 不得自行批准。

## 5. 获准后的拟实施顺序

1. 冻结后端无关 protocol/control schema 和 parity tests；
2. 实现导出、完整性校验和可重复 migration，不先切换默认读取；
3. shadow read 对比质量、filter、删除和故障行为；
4. 仅在冻结 benchmark 达标后 cutover，并保留明确回滚窗口；
5. 验证缺依赖/服务不可用时默认离线路径，再决定是否扩大 rollout。

拟新增 `tests/M8/` 覆盖 protocol parity、migration、fallback、delete/snapshot 和 backend selection；真实服务测试必须
与默认离线 CI 分离且显式启用。退出条件包括迁移可校验/回滚、稳定 ID 与隔离保持、默认 90 题不退化、离线
fallback 可用，以及获批后端达到冻结阈值。

## 6. 撤销与后续边界

后端版本、依赖打包、数据 schema、性能 workload 或 M7 contract 发生实质变化时必须 `REVOKED` 并重新批准。
M9 不得把本计划存在当作数据层已稳定的证据。
