# M8 专业化检索存储准入准备计划

> 当前状态：准入准备；`BLOCKED / NOT_STARTED`，未获准开工
> 前置：`M8-M7-EXIT=SATISFIED`；M8 自身八项决策与批准仍未闭合
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)

## 1. Context、范围与非目标

M7 基础设施范围已在 `m7-infrastructure-only-v1` 内取得独立完成批准，故 `M8-M7-EXIT` 的事实型前置
已满足。这只关闭 M8 的前置事实，不批准 M8。M8 仍为 `BLOCKED / NOT_STARTED`，八项强制决策全部为
`OPEN`，批准字段为空；LanceDB、Qdrant、Milvus 均未选定。

本轮只做准入准备：decision records、后端无关 control/data-plane 契约、迁移/回滚/回退策略和
benchmark/test design。不得因本计划存在而创建生产 adapter、`tests/M8/`、schema migration、
依赖、runtime switch、API、worker、service/container 或部署配置；不得宣称后端已选择、能力已交付、
benchmark 已通过或 M8 已获批。不得读取或复制 `D:\111_Others_Subjects`，不得启动 Network promotion、
M9 或 M10。

专业向量后端（若未来获准）只能是可重建的数据面索引，不能成为 source lifecycle、授权、学习状态、
会话或 review history 的权威。现有 SQLite 领域仓储、M7 registry、默认 BM25、SQLite linear cosine、
默认离线启动和 M0–M5 学习闭环必须保持兼容。

## 2. 前置证据与不可削弱的不变量

| Prerequisite ID | 当前状态 | 证据/约束 |
| --- | --- | --- |
| `M8-M7-EXIT` | `SATISFIED` | `docs/PLAN.md`、`docs/plans/m7-source-lifecycle-plan.md`、`docs/baselines.md` |

后续任何实现必须继续保持：

- M7 SQLite registry 权威负责 source owner、revision、generation、lifecycle、删除状态和审计历史；
- 稳定 document/chunk identity、generation-bound snapshot、identity-set、owner isolation、tombstone、
  hard-delete receipt、retry、fail-closed 和路径隐私；
- 数据面索引可由获批的 authoritative revision/manifest 删除并重建，不能成为授权来源；
- 默认无可选依赖、无外部网络服务、无运行中服务时仍能启动并保留既有降级路径；
- `StudySessionService` 继续独占正式状态转换、答案评估、学习持久化和 review-log。

## 3. 八项强制决策（全部保持 OPEN）

所有记录必须先形成单一政策或明确“不采用”的结论，才能在未来标记 `RESOLVED`。候选列表、`TBD`、
空值、“实现时决定”或没有可复现证据都不满足准入门禁。本节只定义决策记录和定稿顺序，不替负责人
填写结论、批准或后端选择。

每条记录的必填字段为：Decision ID、问题与范围、单一政策/不采用结论、默认值与允许覆盖、排除范围、
输入校验与拒绝行为、失败行为、M0–M7 兼容影响、安全/隐私/授权/保留影响、workload 与量化阈值、
可复现证据、责任人、日期和复审条件。涉及删除或迁移时，还必须写明逻辑不可见、物理清理、审计
保留、hard-delete receipt、last-good、缓存/索引/出处、并发读、失败重试、幂等恢复和 fail-closed。

| Decision ID | 状态 | 本轮记录焦点 | 责任人/日期 |
| --- | --- | --- | --- |
| `M8-CONTROL-SCHEMA` | `OPEN` | control/data-plane 权威边界与 schema/version | — / — |
| `M8-MIGRATION` | `OPEN` | export、integrity、shadow read、cutover、rollback | — / — |
| `M8-LANCEDB-CRITERIA` | `OPEN` | 本地/嵌入式候选的选择或不采用标准 | — / — |
| `M8-QDRANT-CRITERIA` | `OPEN` | 服务型候选的选择或不采用标准 | — / — |
| `M8-BACKEND-PARITY` | `OPEN` | protocol、filter、排序、metadata、snapshot、error parity | — / — |
| `M8-FALLBACK` | `OPEN` | 缺依赖、损坏、服务故障与迁移中断矩阵 | — / — |
| `M8-DEPENDENCY-PACKAGING` | `OPEN` | 可选依赖、平台、离线、许可证与升级边界 | — / — |
| `M8-BENCHMARK` | `OPEN` | workload、指标、样本、环境与选择阈值 | — / — |

### 3.1 `M8-CONTROL-SCHEMA` — control/data-plane 边界

- **待定问题**：哪些 identity、revision、generation、snapshot、metadata 和 schema version 由
  M7 SQLite 权威保存，哪些可复制到数据面；如何升级和拒绝不兼容版本。
- **必须记录**：稳定 source/document/chunk ID、revision/generation、chunk policy、embedding
  model/version、dimension、normalization、index type、fingerprint/identity-set digest，以及
  control-plane 与 data-plane 的职责和原子发布关系。
- **验证要求**：旧 M0–M7 API/学习闭环、路径隐私、授权隔离、tombstone/hard-delete 语义不得变化；
  不匹配的 model/dimension/generation/snapshot 必须稳定拒绝，不能由索引自报权威状态。

### 3.2 `M8-MIGRATION` — export、migration、cutover 与 rollback

- **待定问题**：SQLite 到候选数据面的导出、完整性验证、shadow read、人工 cutover、回滚、恢复和
  幂等重放协议。
- **必须记录**：manifest 的 source/revision/generation scope、chunk IDs/fingerprints、model/
  dimension/chunk policy、normalization、count、identity-set digest、content/integrity checksum、
  tombstone/delete state、工具版本、时间和脱敏环境信息。
- **必须验证**：隔离构建 candidate index；校验 count、identity、dimension、metadata、删除状态；
  中断可恢复且不重复 embedding（兼容时）；失败不得静默切换；保留 last-good、明确 rollback point、
  原子发布和 hard-delete receipt 语义。

### 3.3 `M8-LANCEDB-CRITERIA` — LanceDB 独立准入标准

- **待定问题**：在本地/嵌入式、Windows 和离线场景下，LanceDB 何时达到相对 SQLite baseline 的客观
  质量、延迟、规模、资源和恢复要求，或明确不采用。
- **必须评估**：filter/metadata、build/rebuild、corruption/restart、RSS/磁盘、安装体积、许可证、
  维护/升级、无服务启动、可选依赖隔离和默认 fallback；所有结论必须由固定 workload 与结构化报告
  支撑。

### 3.4 `M8-QDRANT-CRITERIA` — Qdrant 独立准入标准

- **待定问题**：服务型/本地 Qdrant 的并发、规模、运维与恢复收益是否足以抵消服务、网络、Windows、
  离线打包和故障边界成本，或明确不采用。
- **必须评估**：同一 quality/parity/lifecycle 指标、服务不可用和 timeout 行为、资源/安装/许可证、
  显式 opt-in 方式。Qdrant 不得静默成为默认启动或离线路径依赖。

### 3.5 `M8-BACKEND-PARITY` — 后端行为等价

- **待定问题**：protocol、filter、metadata/provenance、upsert/delete、snapshot 和 error mapping
  的哪些行为必须完全相同，哪些 score/排序差异允许在明确容差内。
- **必须记录**：query/query-vector、`top_k`/threshold、确定性 tie policy、count/ids/is_synced、
  stable error taxonomy、generation/snapshot mismatch、tombstone/hard-delete、重启和部分写入恢复。
- **硬约束**：不允许跨 owner、stale generation、已删除或半迁移结果；数据面永远不能绕过 control plane。

### 3.6 `M8-FALLBACK` — 故障与离线回退

- **待定问题**：缺可选依赖、索引损坏、服务不可用、迁移中断、model/dimension 不匹配时，哪些路径可
  回退，哪些必须拒绝。
- **必须记录**：默认资料的 SQLite/BM25 可用性与 user-source 的 fail-closed 矩阵；授权、generation、
  deletion、identity 或 data-plane availability 无法证明时不得返回 stale、跨 owner、tombstoned 或
  半迁移数据；错误不得泄露绝对路径、源内容、凭据或原始 backend 错误。

### 3.7 `M8-DEPENDENCY-PACKAGING` — 可选依赖与打包

- **待定问题**：候选依赖分组、锁定版本、Windows/离线安装、体积、许可证、CI 隔离、服务边界和升级/
  卸载影响。
- **必须记录**：默认安装不新增强制依赖或网络服务；显式 opt-in 的安装失败、卸载、版本冲突和服务
  不可用行为；依赖变更如何触发重新验证和准入撤销。

### 3.8 `M8-BENCHMARK` — 比较 workload 与选择阈值

- **待定问题**：SQLite linear/BM25 baseline 与候选后端如何使用同一 corpus、embedding、query/gold set、
  硬件和样本协议比较，以及什么数值结果才足以支持选择或“不采用”。
- **必须记录**：固定 seed、临时目录、环境清单、样本数、warmup/measured、报告 schema、阈值、失败即
  fail-closed 和复现方式；不得把 M7 阈值自动继承为 M8 选择阈值。

### 3.9 定稿顺序

先闭合 control-plane 边界，再闭合 migration/cutover/rollback；随后 parity 和 fallback；然后独立
评估 LanceDB/Qdrant 与 dependency packaging；最后由负责人冻结 benchmark workload 和选择阈值。顺序
不构成后端选择、生产开工授权或 M8 准入。

## 4. 后端无关 control/data-plane 契约草案

本草案参考 [`platform/app/vector_store.py`](../../platform/app/vector_store.py) 的 `VectorStore`、
`SqliteVectorStore`、`LocalVectorStore`、`export_items()`、`migrate_store()`，以及
[`platform/app/protocols.py`](../../platform/app/protocols.py) 的 `SourceIdentity`、`SourceChunk`、
`RetrievalIndex`、`RetrievalSnapshot` 和 writer 语义；本轮不修改生产 protocol。

未来实现至少必须定义：

1. **身份与 metadata**：source、logical document/chunk、revision、generation、snapshot、chunk schema、
   embedding model/version、dimension、normalization、index type、content fingerprint 和 identity-set digest。
2. **数据面操作**：add/upsert、原子 replace-all/snapshot publication、filtered search、count、ids、
   synchronization validation、availability、export、rebuild 和 disposal。
3. **检索语义**：query/query-vector 输入互斥规则、normalized `top_k`、threshold、确定性排序/tie
   容差、metadata/provenance 往返、empty/no-result 行为和稳定错误分类。
4. **生命周期语义**：generation/snapshot 发布、tombstone 可见性、hard-delete 清理、stale-index 拒绝、
   部分写入恢复、缓存失效和 receipt 关联。
5. **控制面边界**：M7 registry 是 owner/lifecycle/revision/generation/delete 的唯一权威；数据面可丢弃、
   可重建、不可提供授权；学习状态和 session 永远不进入专业向量后端。

## 5. migration、shadow read、cutover 与 rollback 设计

未来流程按以下顺序运行，但本轮不执行：

1. 校验 source generation、snapshot、authorization 和 delete barrier 具备导出资格。
2. 导出已编码 vectors 和 authoritative metadata；兼容时不重复 embedding。
3. 在隔离位置构建 candidate index，不改变默认 pointer/read path。
4. 依据 manifest 校验 count、stable identity-set、fingerprint、dimension、model、metadata、generation、
   tombstone/delete state 和 integrity digest。
5. 对同一 query/gold set 进行 SQLite baseline 与 candidate shadow read，比较 quality、filter、owner
   isolation、provenance、ordering 和 failure behavior。
6. 仅在所有冻结门禁通过并取得人工授权后 cutover；保留 last-good SQLite/data-plane route 和 rollback
   window。
7. 要求 atomic publication、interruption recovery、idempotent replay、manifest 状态和 receipt 可审计；
   任何不一致都 fail closed，不得自动扩大 rollout。

## 6. LanceDB 与 Qdrant 评估维度（不选择后端）

两者必须在同一 synthetic workload 与 SQLite baseline 上独立评估：

- quality/parity、filter/metadata/provenance、稳定 ID 与 snapshot/delete 语义；
- ingest/query/rebuild/recovery latency、concurrency、RSS、磁盘和安装体积；
- Windows 兼容、离线安装、默认无服务启动、可选依赖隔离；
- corruption/restart/service timeout、可观测性、许可证、维护和升级负担；
- fallback 是否仍能保持默认离线与 user-source fail-closed。

Qdrant 若作为服务候选，服务必须显式 opt-in，不能隐式加入默认 CI、默认启动、授权或删除语义。
本计划不记录任何候选后端的选择、实现或达标结论；Milvus 同样未选定。

## 7. parity、lifecycle 与 fallback 测试设计

M8 被批准和开工前不创建 `tests/M8/`。获准后测试计划必须覆盖：

- empty/no-result、duplicate upsert、idempotent replace、restart、count/ids/is_synced；
- query text/query-vector、`top_k <= 0`、threshold、dimension/model/revision/generation/snapshot mismatch；
- metadata/provenance、score/tie ordering 容差、filter/owner isolation 和错误映射；
- publish/update/tombstone/hard-delete/recreate、cache invalidation、last-good、rollback；
- 中断 export/import/build/cutover、corruption、missing dependency、service timeout 和 recovery；
- 默认 BM25/SQLite fallback、user-source fail-closed、无绝对路径/凭据/源内容泄露。

默认资料与 user-source 的回退不能混淆：默认路径可保留现有 SQLite/BM25 能力；用户源在授权、
生命周期、删除、identity 或索引可用性无法证明时必须拒绝，不能为了可用性返回旧数据。

## 8. M8 比较 benchmark/test design（非运行时实现）

### 8.1 固定 workload

- 1k single-source 与 3k aggregate 作为与 M7 连续的基线；10k 只作为容量决策待定层；
- lexical、semantic、no-hit、mixed、owner/filter queries；`top_k` 1/3/5；cold 与 warm；
- build/rebuild、upsert/replace、shadow read、migration、tombstone/delete、restart、cutover、rollback；
- 受控 reader/writer 并发，明确不以随机 sleep 或 elapsed-time 断言替代 stage/fault hooks；
- 所有 fixture、corpus、report 写入系统临时目录，禁止读取外部原始资料目录。

### 8.2 测量协议与报告

复用 `tools/run_m7_frozen_benchmark.py` 的方法学：固定 seed、固定 model/embedding、query/gold set、
环境清单和版本摘要；query 默认设计参考 `20 warmup + 200 measured`，FULL/build 默认参考独立 OS 进程
`5 warmup + 20 measured`。结构化报告必须记录 backend/baseline、依赖/服务状态、平台硬件、corpus/query/
report hashes、sample count、redaction checks、错误/fallback 计数、每个门禁的 pass/fail 原因。

quick smoke 只能作为开发反馈，必须显式标记非冻结证据，不得选择后端、批准 M8 或授权生产实现。

### 8.3 待负责人定稿的阈值类别

`M8-BENCHMARK` 未 `RESOLVED` 前不填写最终数值；至少冻结以下类别：

1. hard correctness：未授权、stale generation、tombstone、wrong identity 结果必须为零；
2. quality：Recall@1/3/5、identity-set parity 与 SQLite baseline 非劣性；
3. latency：query p50/p95/p99、cold start、filtered query；
4. lifecycle：ingest、replace、delete、rebuild、migration、rollback、recovery；
5. resources：peak RSS、磁盘、CPU、安装/包体和服务开销；
6. reliability：重启、损坏、错误率、中断恢复、重复性和并发行为；
7. offline/packaging：默认路径无新增强制依赖、网络或服务；
8. operational safety：原子迁移、完整回滚、审计/receipt 完整性。

M7 的冻结门槛只作为方法和 baseline 参考，不能自动成为 M8 的选择门槛。

## 9. 准入检查与批准记录

- [x] `M8-M7-EXIT=SATISFIED`，证据可追溯至 M7 计划、baseline 和 `docs/PLAN.md`；
- [ ] 八项强制决策全部 `RESOLVED`；
- [ ] control/data-plane parity、migration/cutover/rollback 和 fallback 具有可执行的后续测试方案；
- [ ] benchmark workload、环境、样本协议和数值阈值已冻结；
- [ ] `docs/PLAN.md`、本计划和 registry 一致；
- [ ] 用户或项目负责人填写批准记录，并独立授权生产开工。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | — |
| approved_at | — |
| approval_reference | — |
| plan_revision | — |
| decision_set_version | — |

批准字段为空，M8 必须保持 `BLOCKED / NOT_STARTED`。Agent 不得自行批准；任何后续提交、合并或推送
也需再次取得明确授权。

## 10. 本轮允许范围与验证

本轮只允许修改准入准备文档和必要的导航说明，不修改生产代码、依赖、schema、API、开关、服务、
容器、部署配置或阶段测试目录。验证顺序：

1. 检查文档链接、Markdown 格式和 `git diff --check`；
2. 解析 registry，与本计划和 `docs/PLAN.md` 核对八个 Decision ID、`OPEN`、`M8-M7-EXIT=SATISFIED`、
   `BLOCKED / NOT_STARTED` 和空批准字段；
3. 运行既有 `tests/regression/test_docs_consistency.py` 与 `test_governance_contract.py`；
4. 静态审计无 `tests/M8`、无 M8 production adapter/API/flag/schema/service/container、无候选依赖、
   无外部源目录读取、无二进制或生成 artifact，且 M7 protected baseline 未变；
5. 不重跑 M7 benchmark 作为 M8 证据，不以测试结果自动修改状态或生成批准。

完成本轮后，M8 仍为 `BLOCKED / NOT_STARTED`；本计划只提供可供人工审阅和后续决策定稿的设计，
不构成能力交付、后端选择、准入或开工授权。

## 11. 撤销与后续边界

后续若改变 M7 contract、数据 schema、embedding/model、benchmark workload、依赖打包或后端策略，必须
重新审阅相关 decision record；实质变化时 M8 准入应 `REVOKED`，在重新澄清和批准前停止生产实施。M9
不得把本计划存在当作数据层已稳定的证据。
