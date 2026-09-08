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

### 3.10 本轮实验授权与预冻结门槛（仍不闭合决策）

负责人 `justtodo123` 于 2026-09-06 明确授权一次可丢弃的、临时隔离的 LanceDB/Qdrant 比较实验，
仅用于形成 M8 decision evidence。授权范围不包含 M8 admission、后端选择、生产实现、提交/合并/推送，
也不包含 Milvus、Qdrant server/container/service、持久运行服务或任何生产依赖变更。实验不得读取或复制
`D:\111_Others_Subjects`；所有 harness、synthetic corpus、vector、index、cache、venv、package archive
和 raw report 必须位于唯一系统临时目录，完成审阅后清除。

在首次 acquisition 或 measured run 前，冻结以下配置为
`sa.m8.admission-evidence.v1` 的 `precommit-v1`；配置摘要必须覆盖 seed、1k/3k workload、10k 容量层、
model/version、dimension、normalization、dtype、query/gold set、top-k、filter、warmup/measured、
候选 mode、重复次数、报告 schema 和本节门槛。观察 measured 结果后不得修改；若需修改，必须创建新的
experiment ID 和摘要，不得混用结果。建议的保守门槛如下：

- **hard correctness**：未授权、跨 owner/source、stale generation/snapshot、错误 identity、tombstone/
  hard-delete、未发布或部分构建结果、路径/凭据/源内容泄露均为零；count、identity-set、必需 metadata、
  dimension/model/generation/snapshot 校验及规定 fault probe 的 fail-closed 行为为 100%。
- **quality**：Recall@1/3/5 分别不低于 `0.70/0.85/0.90`；相对同一 workload 的 SQLite baseline 各项
  绝对下降不超过 `0.01`；exact/flat top-k set agreement 不低于 `0.99`，approximate top-5 overlap
  不低于 `0.98`；五次重复的 recall spread 不超过 `0.01`。归一化 cosine 分数 `1e-4` 内按 tie 处理，
  报告按 stable chunk ID 规范化排序。
- **latency**：1k/3k query 和 filtered-query p95 不超过
  `max(1.25 * SQLite p95, SQLite p95 + 25 ms)`，p99 不超过 `1.50 * SQLite p99`；import/rebuild/
  migration p95 不超过 SQLite 的 `1.25` 倍；五次重复 median drift 不超过 `20%`。
- **capacity/resource**：10k 只有在全部 hard gate 通过且 query p95 比 SQLite 低至少 `25%`，或负责人
  记录 SQLite 无法合理提供的明确容量/运维优势时，才具备采用理由；否则为不采用。peak RSS 不超过
  `max(1.5 * SQLite peak RSS, SQLite peak RSS + 256 MiB)`，10k 绝对上限为 `1.5 GiB`，index disk 不超过
  `2 * (raw float-vector bytes + UTF-8 metadata bytes) + 64 MiB`，隔离环境增量不超过 `1 GiB`。
- **lifecycle/offline**：支持持久化的 mode reopen/recovery、last-good、rollback 和兼容重放均为 100%；
  delete barrier 后命中、已发布 partial build、failed cutover stale result 和 measured unexpected error
  均为零。运行时无 outbound network、无持久服务，默认 SQLite/BM25 路径无变化。

本节是负责人批准的实验范围和预冻结设计，不是八项决策的最终单一结论；八项 ID 必须继续保持 `OPEN`，
候选结果不能自动选择后端、生成 `RESOLVED`、改变 `BLOCKED / NOT_STARTED` 或产生批准记录。

### 3.11 `precommit-v1` 的可执行冻结配置

以下配置在 acquisition 前冻结；它只刻画**合成、已预编码向量的数据面**，不声称代表完整 M7
end-to-end BGE 检索，也不能单独支持生产后端选择。这样可在不读取真实资料、不复制仓库语料且不将模型
缓存带入实验目录的前提下，先比较 SQLite linear、LanceDB embedded 与 Qdrant Client local mode 的存储和
查询行为。若未来要比较真实 BGE 路径，必须另建 experiment ID、重新冻结模型缓存位置与完整输入摘要。

| 项 | 冻结值 |
| --- | --- |
| experiment ID / protocol | `sa.m8.admission-evidence.v1` / `precommit-v1` |
| executor | CPython `3.11.9`；每次尝试均新建于唯一系统临时根目录的 venv；不得使用或修改仓库 venv |
| candidates | `sqlite-linear`（基线）、`lancedb-embedded`、`qdrant-client-local`；后两者均为显式临时本地 mode，不启动 Qdrant server/container/service |
| corpus | seed `20260906`，三个 synthetic owner/source namespace；stable chunk ID 为 `m8-{source}-{ordinal:05d}`；UTF-8 metadata 不含宿主机路径、源内容、凭据或真实 URI |
| vector input | `synthetic-unit-vector-v1`，model/version 同名，`512` dimensions、`float32`、L2 normalized；每个 chunk/query 由固定 seed 生成，query 不调用 embedding runtime |
| workloads | `1k-single`（1 source × 1,000 chunks）、`3k-aggregate`（3 × 1,000）、`10k-capacity`（10 × 1,000）；每个 chunk 有 source/owner/generation/snapshot/tombstone/filter metadata |
| query/gold set | 每个 1k/3k workload 固定 200 个：50 exact、50 perturbed semantic、50 owner/filter、50 no-hit；exact 与 semantic 的 gold 为目标 chunk，filter 的 gold 必须属于目标 owner/source，no-hit 的 gold 为空 |
| top-k / filter | `top_k=1/3/5`；filter 为 owner、source、published generation/snapshot 与 `tombstone=false` 的交集；稳定比较以 chunk ID 的规范化排序消除同分歧义 |
| sampling | 每 backend/workload 五个独立重复；query 为 `20 warmup + 200 measured`；build/rebuild/import/reopen 为 `5 warmup + 20 measured`；10k 不产生后端选择结论，只记录容量门槛 |
| candidate mode | 仅 exact/flat 搜索；不得为候选调入 HNSW/IVF 或未冻结的 ANN 参数；Qdrant 使用 local client，LanceDB 使用临时本地目录 |
| fault probes | wrong dimension、missing required metadata、wrong/stale generation/snapshot、cross-owner/source filter、tombstone、partial/unpublished build、reopen、last-good/rollback simulation；期望均 fail closed 或零命中 |
| network / lifecycle | installer acquisition 结束后 measured run 的 outbound network 为零；无持久服务；实验进程退出后临时根目录之外不得留下 index/cache/report/artifact |

结构化报告固定 schema 为 `sa.m8.admission-evidence.report.v1`。顶层必须有：`experiment_id`、
`protocol`、`frozen_config_sha256`、`environment`、`dependency_versions`、`redaction_checks`、
`temporary_root_kind`、`network_observation`、`backends`、`workloads`、`gate_evaluation`、
`unexpected_errors`、`limitations` 和 `cleanup`。每个 backend/workload/repetition 必须有：corpus、query、
metadata 与 config hashes；build/rebuild/import/reopen/query 分位数；RSS、disk、count、identity-set digest；
Recall@1/3/5、exact set agreement、top-5 overlap；filter/tombstone/generation/snapshot/fault 结果；错误类别和
非泄露检查。报告只写临时根目录，汇总时仅能进入本计划的脱敏文字结论；raw JSON 不入库。

### 3.12 2026-09-06 首次执行记录：无效，不作为决策证据

已在唯一系统临时根目录中完成一次 `sa.m8.admission-evidence.v1` / `precommit-v1` 的可丢弃执行：
CPython `3.11.9`，LanceDB `0.38.0`、Qdrant Client `1.19.0`、NumPy `2.4.6`、psutil `7.2.2`、
PyArrow `25.0.1`；九个 backend/workload 组合均完成，运行时未记录 unexpected error、持久服务或真实
源输入。raw report 未进入仓库，且在审阅后删除。

该次执行**不满足冻结协议，故判定为无效，不能作为 `M8-BENCHMARK`、候选后端选择、任何决策关闭或
准入的证据**。审阅发现临时 harness 的 `source_for()` 将 `1k-single` 和 `10k-capacity` 都限制为三个
source namespace，分别偏离冻结的 `1 × 1,000` 与 `10 × 1,000` source 结构；此外，top-5 overlap 把
50 个预期为空的 no-hit query 计为零，导致即使 SQLite canonical baseline 的 aggregate overlap 也仅为
`0.75`，并使所有 parity gate 机械失败。harness 还未实现冻结表中全部的 required-metadata、stale
 generation/snapshot、partial/unpublished、reopen、last-good/rollback fault probe。因此不得从该次
运行的延迟、资源或质量数值推导候选优劣。

如负责人仍需可用于决策的比较，必须新建 experiment ID 与配置摘要，修正 corpus namespace 与空结果
parity 统计，完整实现冻结的 fault probes，并重新进行独立审阅；不得复用本次 raw report 或将其与后续
结果混合。本记录不改变八项 Decision ID 的 `OPEN`、M8 的 `BLOCKED / NOT_STARTED` 或空批准字段。

### 3.13 2026-09-06 `v2` 执行记录：无效，不作为决策证据

在随后一次使用修正 corpus、empty-result parity 和 harness-level fault probes 的临时 `v2` 尝试中，九个
组合虽然完成且没有 workload error，但报告环境实际为 CPython `3.13.3`，偏离预定的 CPython `3.11.9`。
因此本次尝试同样无效，不能与前次结果混用，也不得据此比较候选、关闭任何决策或改变 M8 状态。raw report、
venv、harness、日志和索引仍只在系统临时目录；审阅后必须删除。

后续如继续，必须以新的 experiment ID，在 CPython `3.11.9` 隔离 venv 中重新执行，并保持本节已修正的
corpus、empty-result parity 和 probe 覆盖；任何结果仍仅是 decision evidence input，不构成 backend
selection 或 admission。

### 3.14 `precommit-v3` 修正冻结配置（已执行但无效）

独立预审发现 `precommit-v1` 的“固定三个 namespace”与 `10k-capacity` 的 `10 × 1,000` source 结构冲突，
且 10k 是否执行 query、empty/no-hit parity、exact/flat 下的 overlap 口径和 control-plane fault probe 边界
仍不够明确。因此下一次有效尝试使用新 experiment ID `sa.m8.admission-evidence.v3`、protocol
`precommit-v3`，不得复用或合并前两次 raw report。除以下修正外，3.10–3.11 的版本、阈值、临时目录、
报告和清理约束继续适用：

- workload 分别创建 `1`、`3`、`10` 个 source namespace，每个 source 恰有 `1,000` chunks；source ID 为
  `source-{ordinal:02d}`，owner ID 为 `owner-{ordinal % 3:02d}`，stable chunk ID 仍为
  `m8-{source}-{ordinal:05d}`。1k 因此只有一个 source/owner，3k 覆盖三个 owner，10k 的十个 source
  确定性分配给三个 owner；wrong-owner probe 使用语料中不存在的 owner。
- 1k、3k、10k 均执行固定 200 个 query 与 `20 warmup + 200 measured`；10k 的 query 仅用于容量、资源、
  hard-correctness 和相对延迟门禁，不单独产生后端选择结论。三种 workload 均使用 50 exact、50
  perturbed semantic、50 owner/source filter 和 50 no-hit；query/gold/config hash 必须逐 workload 记录。
- no-hit 的预期与实际均为空时，empty-result agreement 记为 `1.0`；一方非空时记为 `0.0`。top-5 overlap
  只对预期非空 query 计算，no-hit 单独汇总 empty-result agreement，不以零值稀释 overlap。候选均为
  exact/flat，因此 `approximate_top5_overlap` 记为 `not_applicable`，同时以 `top5_overlap_vs_sqlite`
  执行原 `0.98` parity 门禁。
- 每个 backend/workload 执行五个独立 repetition；每个 repetition 的 query 使用规定 warmup/measured。
  build、rebuild、import、reopen 各自执行 `5 warmup + 20 measured`，每个样本使用全新的 backend 实例或
  明确关闭后重新打开的持久实例；不得把一次操作拆成多个伪样本。cold query 单独记录但不纳入冻结
  warm-query latency 门禁。
- wrong dimension 与 backend 原生 schema/filter/delete 行为由候选后端实测；required metadata、stale
  generation/snapshot、partial/unpublished、last-good/rollback 是 harness control-plane publication
  wrapper 的 fault probe。wrapper 必须先校验 authoritative manifest 和 published pointer，且未发布、
  stale 或验证失败的 candidate 永远不能进入 query path；这些 probe 不得被描述成候选数据库的原生能力。
- Qdrant point ID 使用由 stable chunk ID 确定性派生的 UUID，并把原 stable chunk ID 保留在 payload；所有
  parity、identity-set digest 和报告比较均使用 stable chunk ID。LanceDB 使用显式 Arrow schema 和
  pre-filter；两个候选均须在报告中证明 exact/flat 配置、required metadata 预校验以及关闭后 reopen。

该修正冻结发生在 `v3` acquisition 和 measured run 前；执行后不得观察结果再改值。如实现或依赖 API
要求再次改变上述口径，必须停止本次尝试、记录无效原因并创建新的 experiment ID。

### 3.15 2026-09-06 `v3` 执行记录：无效，不作为决策证据

`sa.m8.admission-evidence.v3` 在获准的 PyPI acquisition 后使用唯一系统临时目录与 CPython `3.11.9`
启动，冻结依赖版本与预定一致；Qdrant local mode 运行时也明确报告其为 exact brute-force search。但是，
临时 harness 在完成 measured backend loops 后因错误读取 `qdrant_client.__version__` 而在写出结构化报告前
失败，未产生可审阅的 raw report。进一步静态复核发现该 harness 没有按冻结协议实现
`5 warmup + 20 measured` 的 build/rebuild/import/reopen 样本，也没有实际执行完整 fault probe 与 gate
calculation。因此该尝试整体无效；进程内数值不得从失败现场恢复、推导或与其他 experiment 混合。

### 3.16 `precommit-v4` 最终口径修正（已执行但无效）

下一次尝试使用新 experiment ID `sa.m8.admission-evidence.v4`、protocol `precommit-v4`。除 3.14 外，
在 acquisition 和 measured run 前进一步冻结以下定义，以消除 `v3` 静态复核发现的统计和操作歧义：

- Recall@1/3/5 仅以 150 个预期非空 query 为分母；50 个 no-hit 只进入 empty-result agreement，且必须
  `50/50` 为空。`top5_overlap_vs_sqlite` 也只以 SQLite top-5 非空 query 为分母，按
  `|candidate ∩ sqlite| / |sqlite|` 计算；exact-set agreement 覆盖全部 200 个 query，empty/empty 为相等。
- 每次 query repetition 先执行固定 20 个 warmup，再逐个计时全部 200 个 measured query；p50/p95/p99
  基于五次 repetition 合计 1,000 个单 query 样本，而不是五个 repetition 平均值。quality 分 repetition
  报告，recall spread 取五次最大值减最小值。
- `build` 指从空目录创建 schema/collection/table 并导入完整 workload；`import` 指在已创建的空 schema 中
  导入完整 workload；`rebuild` 指从已填充实例开始，删除旧数据面后重新创建并导入完整 workload；
  `reopen` 指关闭已持久化的完整实例，重新连接并校验 count、identity-set 与固定 sentinel query；
  `migration` 指从 canonical row manifest materialize 新候选实例并完成 count、identity、metadata 和
  config 校验。每项各执行 5 个 warmup 和 20 个 measured full-workload 样本，样本结束即删除其临时实例。
- SQLite baseline 使用文件型 SQLite 表保存同一 float32 vector 与 metadata，并以 NumPy exact cosine 线性
  扫描查询；上述五项操作使用与候选相同的完整 workload 和边界定义。操作延迟比值只比较同名操作，
  不以 schema 创建、单行写入或进程启动时间冒充其他操作。
- 每个 backend/workload/repetition 的 probe 分母固定为 10：wrong dimension、missing required metadata、
  stale generation、stale snapshot、cross-owner/source、tombstone、hard-delete、partial/unpublished、
  reopen validation、last-good/rollback。预期拒绝或零命中计为 pass；已分类的预期拒绝写入
  `expected_errors`，未分类异常、错误返回或泄露写入 `unexpected_errors`，hard gate 要求 `10/10`。
- measured 阶段通过进程内 socket guard 阻止任何 outbound connect；发生尝试即写入 unexpected error 并
  使 network gate 失败。依赖版本从安装元数据读取，不依赖包是否暴露 `__version__`。peak RSS 使用采样
  线程覆盖操作区间；磁盘统计在关闭实例后、删除前执行。

`v4` 仍只是合成预编码向量的数据面决策输入。即使全部门禁通过，也不能自动选择后端、关闭八项决策、
授权生产实现或改变 `BLOCKED / NOT_STARTED`。

### 3.17 2026-09-06 `v4` 完整执行记录：中止且无效，不作为决策证据

`sa.m8.admission-evidence.v4` 在获准的唯一系统临时目录、CPython `3.11.9` 与冻结依赖下完成了非准入
scaled smoke；smoke 只验证报告结构、三个后端的基本调用、五类 lifecycle 字段、十类 probe 分类、网络
阻断和脱敏检查能够运行，按设计不满足 frozen sample count，不能成为准入证据。

随后启动的完整 frozen run 未生成 `report.json` 或 `publication.json`，因此没有可审阅、可校验或可发布的
完整证据。执行审计还发现临时 harness 将每个 workload 的五类 lifecycle 各保留 `5 warmup + 20 measured`
个完整索引实例，且 `rebuild` 同时保留旧实例和 replacement；运行推进到 3k Qdrant query 前，临时根目录已
增长到约 `7.0 GiB`。该行为偏离 3.16 中“样本结束即删除其临时实例”的冻结要求，并造成不必要的本机临时
磁盘占用。为避免继续扩大占用，执行被人工停止；未恢复任何进程内数值，也未把 partial artifacts 当作结果。

静态复核同时确认该 harness 的 `stale_generation` 与 `stale_snapshot` control-plane probe 只改变 manifest，
却未同步改变 published pointer 中的 manifest digest，因此实际拒绝原因是 `stale_manifest`，没有独立证明
冻结的 generation/snapshot mismatch 分类；`tombstone` 与 `hard_delete` 也复用了不存在 owner 的空结果，
没有对真实 tombstoned/deleted identity 执行删除屏障验证。故即使该进程继续完成，其 probe 证据仍不满足
`precommit-v4`。本次完整运行整体判定为无效，不得据此比较 SQLite、LanceDB 或 Qdrant，不得关闭任何
Decision ID、选择后端、批准 M8 或授权生产实现。审阅记录完成后，raw partial indexes、smoke reports、venv
和 harness 必须从系统临时目录清除。

若仍需继续实验，必须使用新的 experiment ID，在 measured run 前修正 per-sample cleanup，并让 stale
manifest、stale generation、stale snapshot、真实 tombstone 与 hard-delete barrier 分别具有可判别的 fixture、
预期错误分类和查询断言；新尝试不得复用或混合 `v1`–`v4` 的 raw/partial 数值。

### 3.18 `precommit-v5` 静态冻结设计（执行后保留为历史协议）

下一次实验只能使用新 experiment ID `sa.m8.admission-evidence.v5` 与 protocol `precommit-v5`。本节仅冻结
静态设计；不继承此前只针对 `v3` 的 PyPI acquisition 授权，不授权安装、smoke 或 measured run。除本节
修正外，3.10、3.14 和 3.16 的 synthetic corpus、版本、query、sampling、quality/latency/resource 门槛、
临时目录与非准入边界继续适用；不得复用或混合 `v1`–`v4` 的 raw/partial 数值。

#### 3.18.1 样本隔离、磁盘预算与清理 receipt

- sample key 固定为 `experiment/backend/workload/operation/phase/ordinal`；每个 sample 使用唯一目录和全新
  backend instance，不得跨样本复用实例、数据文件或 backend cache。`rebuild` 的 old/replacement 是唯一
  允许的双实例窗口，且必须位于同一 sample 目录。
- 每个 sample 必须在 `finally` 中依次执行：backend close/flush、记录 elapsed/RSS/过程 peak disk 与
  close-after disk、递归清理、检查 sample 路径不存在且 residual bytes 为零、原子写出不含路径的 cleanup
  receipt。任何 close、测量、删除或复核失败均停止该 backend/workload，不能继续计分。
- staging record 与 cleanup receipt 写在独立于 sample data 的 audit 目录；每条记录先写同目录临时文件，
  `fsync` 后以 replace/rename 原子发布，并绑定 sample hash。删除 source/index 不能删除对应 receipt。
- 冻结原始 10k 预算基数 `B = 10,000 * 512 * 4 + canonical UTF-8 metadata bytes`，metadata bytes 在 corpus
  生成后、任何 backend build 前由规范序列化计算并写入 frozen config。预算为：
  `per_instance_disk_max = 2 * B + 64 MiB`；`per_operation_peak_disk_max` 在 `rebuild` 为
  `2 * per_instance_disk_max + 64 MiB`，其余操作为 `per_instance_disk_max + 64 MiB`；
  `temporary_root_peak_max = per_operation_peak_disk_max + 512 MiB`（包含 venv、staging、WAL、Arrow/cache
  和报告预留）；sample data 的 `residual_bytes_max = 0`、`cleanup_failure_count = 0`。较小 workload 沿用
  10k 上限，避免按实测结果修改预算。
- acquisition 完成后先记录 venv/package footprint；若其与预留相加已超过 root 预算，或任何创建后、操作中
  采样、sample 完成后、workload 完成后的 watchdog 超预算，立即停止并只发布 `ABORTED`。无法关闭文件
  句柄并清理的 backend 不得重试掩盖残留，也不得继续其完整 run。

#### 3.18.2 可判别 fault fixture 与稳定分类

每项 fixture 只能改变一个绑定，并记录 fixture ID、mutation、expected/actual code、pointer/manifest digest、
generation、snapshot、规范化 result IDs 与 `candidate_accessed`。每个 backend/workload/repetition 固定以下
十一个独立 probe，必须 `11/11`；这显式取代 `v4` 的十项分母：

| Probe | 单一变化与断言 |
| --- | --- |
| `wrong_dimension` | 只改变 query vector dimension；返回 `DIMENSION_MISMATCH`，不访问 candidate |
| `missing_required_metadata` | 从 otherwise-valid manifest 只删除 `model`；返回 `METADATA_INVALID` |
| `stale_manifest` | 只破坏 pointer 绑定的 manifest digest；返回 `STALE_MANIFEST`，零结果 |
| `stale_generation` | pointer 与 manifest digest 保持自洽，只让 authoritative generation 与 candidate generation 不同；返回 `STALE_GENERATION` |
| `stale_snapshot` | pointer 与 manifest digest 保持自洽，只让 authoritative snapshot 与 candidate snapshot 不同；返回 `STALE_SNAPSHOT` |
| `cross_owner_source` | 使用语料中两个真实且不匹配的 owner/source 组成 filter；返回空集，不以不存在 owner 代替 |
| `tombstone` | 对基线可命中的 delete sentinel 写真实 tombstone；控制面查询零命中，但物理对象仍存在 |
| `hard_delete` | 对同一 sentinel 完成保留期后的物理 purge；对象、索引、cache 与 provenance 均不存在，并产生 immutable receipt |
| `partial_unpublished` | candidate 存在但无 published pointer；返回 `UNPUBLISHED_CANDIDATE`，且 candidate 不可读 |
| `reopen_validation` | 关闭重开后 count、identity digest、manifest digest 与 sentinel query 全部一致，否则 `REOPEN_INVALID` |
| `last_good_rollback` | 新 candidate 校验失败或 cutover 中断；只读取旧 published generation，绝不访问 candidate |

`last_good` 只适用于仍可证明 authorization、lifecycle、delete barrier、identity 与 generation 的已验证旧发布；
其中任一条件不可证明时必须完全 fail closed，不得为了可用性返回 stale user-source 数据。

#### 3.18.3 真实 tombstone、hard-delete 与 receipt

- 每个删除 fixture 先发布包含稳定 `delete-sentinel` identity 的独立 source，基线 exact/filter query 必须命中；
  fixture 不得与质量/延迟 corpus 共用可变状态。
- Tombstone 后必须同时证明逻辑检索为零、物理 data-plane object 仍存在；hard-delete 仅在冻结模拟时钟满足
  retention policy 后执行，并验证 backend object/index、wrapper cache、provenance 全部清除。
- Immutable delete receipt 至少绑定 request/source/sentinel identity-set digest、各存储清理计数与 digest、
  policy version、逻辑删除时间、物理完成时间和结果码。相同 request 重放必须返回相同 receipt；中断或
  receipt 缺失时状态保持 `DELETE_PENDING` 且查询 fail closed，不能报告完成。
- 这些是实验 publication wrapper 对 M7 语义的 fixture，不得宣称 LanceDB、Qdrant 或 SQLite 数据面原生
  提供 M7 lifecycle、授权或 receipt 权威能力。

#### 3.18.4 两阶段报告与唯一终态 publication

- 所有 sample/probe/cleanup 原始记录只进入 audit staging；完整 inventory 必须与 frozen expected inventory
  的数量和 digest 一致。样本清理完成不删除 staging audit record。
- 全部样本、probe、network/redaction、预算和 cleanup gate 完成后，先原子生成 canonical `report.json`，
  其中包含 frozen config hash、sample inventory digest、gate evaluation 及 invalid/abort 原因，再重新读取并
  校验其 digest、schema 与 required inventory。
- 只有上述复核全部通过才能原子生成 `publication.json`，绑定 experiment/protocol、report SHA-256、frozen
  config hash、inventory digest、gate summary 与终态 `COMPLETE`。任何异常、超预算、清理失败、缺样本或
  序列化失败只能生成终态 `ABORTED`/`INVALID` publication，且不得包含性能排名或候选比较结论。
- 同一 experiment ID 只允许一个终态 publication；不能从 partial report 补写 `COMPLETE`。raw report 只留在
 临时根目录供独立审阅，审阅后连同 venv、harness、indexes 和 cache 一并删除；仓库只记录脱敏结论。

#### 3.18.5 预执行门禁与治理边界

在任何新 acquisition 前，必须先完成 harness 静态审阅、scaled smoke 设计审阅和磁盘预算预检，并重新取得
明确指向 `v5`、PyPI、精确版本和新系统临时目录的依赖授权。smoke 也只能在该授权后执行，并必须使用与 full
run 相同的 cleanup、probe 与 publication 代码路径；仅缩小 corpus/sample count，终态固定为
`SMOKE_NON_ADMISSION`。

即使 `v5` 有效且全部技术门禁通过，也只形成 `M8-BENCHMARK` 的人工决策输入，不能自动关闭该决策或其他
七项 Decision ID，不能选择 LanceDB/Qdrant、增加生产依赖、创建 adapter/`tests/M8`、改变 M8
`BLOCKED / NOT_STARTED`、填写批准字段或授权生产开工。Milvus、Qdrant server/container/service、真实源
输入、外部目录读取、M9 与 M10 继续排除。

### 3.19 2026-09-07 `v5` scaled smoke 正式处置：证据有效但门禁未通过

负责人另行明确授权 `sa.m8.admission-evidence.v5` 在新的唯一系统临时目录内安装冻结依赖并先执行
scaled smoke。最终 harness 经独立静态复核后，在 CPython `3.11.9`、LanceDB `0.38.0`、Qdrant Client
`1.19.0`、NumPy `2.4.6`、psutil `7.2.2`、PyArrow `25.0.1` 和合成预编码向量下完成三个冻结候选后端的
smoke；所有运行内容均位于 Windows 用户级系统临时目录中的唯一根目录，未使用仓库 venv 或真实源资料。

这里的“证据有效”只表示独立审阅可验证 publication、report、frozen config 与 inventory 的身份和哈希绑定，
且能够核对运行库存、hard gate 与清理终态；不表示技术门禁通过。harness 发布的协议终态仍为
`INVALID / GATE_FAILED`，不是 `SMOKE_NON_ADMISSION`，因此不得启动完整 frozen run。

正式处置如下：

- correctness 与全部十一类 probe 均通过（`60/60` quality/SQLite alignment、`66/66` probe）；网络尝试为
  `0`，清理失败为 `0`，sample residual bytes 为 `0`，共核对 `96` 个样本。
- report SHA-256 为 `1ec6be1a819759332a1e3edd93270efdb2be8ddff6bbcbfe0203fc03f4b53b98`，
  frozen-config SHA-256 为 `d97897e6236d30fa1edee0c5edb19063dd45fd83558421425684c3a7ca9125bb`，
  inventory digest 为 `aea84a32c94ffc912e1058e84feae5945462e509b27b8c776a213c29ab3919bd`；
  expected/actual inventory 数量和 digest 均通过独立复核。这里只记录脱敏摘要，不保存 raw JSON。
- `latency` 为 `16/24`、`lifecycle_latency` 为 `6/18`、`median_drift` 为 `33/36`，故
  `overall_pass=false`。这些失败发生在极小 workload 和缩减采样的 smoke 中，固定启动、提交与 wrapper
  开销相对 SQLite 亚毫秒基线占主导；该结果不能被解释为任一后端的质量缺陷、性能排名或后端选择结论。
- 本记录只将本次 smoke 作为一条“证据有效但门禁未通过”的人工 decision input；不得与无效的 `v1`–`v4`
  raw、partial 或派生数值混合、平均、复用或补写为通过结果。
- 不写入候选排名，不选择 SQLite、LanceDB、Qdrant 或 Milvus，不批准生产依赖、adapter、migration、API、
  runtime switch、worker、service/container、部署配置或生产测试变更，也不授权生产实现。
- M8 继续保持 `BLOCKED / NOT_STARTED`；`M8-CONTROL-SCHEMA`、`M8-MIGRATION`、
  `M8-LANCEDB-CRITERIA`、`M8-QDRANT-CRITERIA`、`M8-BACKEND-PARITY`、`M8-FALLBACK`、
  `M8-DEPENDENCY-PACKAGING` 与 `M8-BENCHMARK` 八项决策全部保持 `OPEN`；backend selection、admission
  和批准字段继续为空。
- 独立审阅完成后，三个 `v5` 临时根目录及其中的 venv、harness、cache、corpus、index、sample、raw report、
  inventory、receipt 和 publication 已全部删除，并确认无匹配的 `v5` 临时目录或状态文件残留。

本处置关闭的是本次临时 smoke 的审阅与清理流程，不关闭任何 M8 Decision ID，也不构成修改门禁、启动下一版
实验、运行 full protocol、M8 准入、合并或推送授权。若继续实验，必须先形成并审阅新的冻结协议与独立授权。

### 3.20 2026-09-07 smoke 性能门禁人工校准审阅（仅作为未来协议输入）

针对 `v5` scaled smoke 暴露出的统计口径问题，负责人完成以下人工校准；这些结论只约束未来协议草案，
不回写或改判 `v5`，也不表示 `v6` 已冻结、获准 acquisition、获准执行或可以直接运行 full protocol：

- 32/64 chunks 的 scaled smoke 不执行 query p99 相对比例门禁。此规模下解释器、计时与调度等固定开销
  占比过高，不满足候选与 SQLite 基线可比的前提；相对性能门禁仅可在完整 workload 中裁决。
- 两次 measured lifecycle sample 不用于判定 median drift。两个观测不足以形成有意义且稳定的漂移统计，
  易被单次 GC 或调度抖动主导；median drift 仅可在 full run 的五次 repetition 上计算。
- scaled smoke 不对 lifecycle 执行相对延迟裁决。未来协议继续遵守 3.16 的同名操作边界，不把进程启动、
  schema 创建、提交或 publication wrapper 等固定开销冒充被比较操作；smoke 只检查 lifecycle 能否完成及
  count、identity 和必要状态是否正确。
- smoke 的职责是验证 harness、冻结依赖加载、probe、清理、网络阻断和证据链能够端到端运行，而不是预先
  裁决性能。smoke 可以保留诊断性 timing，但该数值不得计入性能 pass/fail、候选排名或后端选择；性能裁决
  只允许发生在另行冻结并获准执行的 full protocol。

本次校准不删除 correctness、probe、network、cleanup、hash、inventory、预算和 residual 等 smoke hard gate；
任一 hard gate 失败仍必须停止，且不得启动 full run。未来若建立 `v6`，必须使用新的 experiment ID，明确区分
`smoke_integrity_pass` 与 `full_performance_pass`，先完成静态审阅并取得针对精确依赖、全新临时目录、smoke 和
后续 full run 的独立授权。`v5` 继续保持 `INVALID / GATE_FAILED`，不得按本节追溯重算为通过。

### 3.21 `precommit-v6` 静态冻结设计（未授权 acquisition 或执行）

根据 3.20 人工校准，未来协议使用新 experiment ID `sa.m8.admission-evidence.v6` 与 protocol
`precommit-v6`。本节冻结的是执行前的协议文本，不授权 acquisition、smoke、full run 或任何生产变更；协议
必须在 v6 acquisition 和 measured run 前完成审阅，执行后不得依据观察到的结果修改样本、门槛、分母或终态。

#### 3.21.1 smoke 与 full 的职责边界

- smoke 的唯一裁决对象是 harness、依赖加载、probe 覆盖、网络阻断、清理、库存、磁盘预算和证据链的基本
  运行完整性；终态固定为 `SMOKE_NON_ADMISSION`，即使白名单 hard gate 全部通过，也不形成后端选择或准入。
- smoke 白名单包括 correctness、11/11 probe coverage、network、cleanup、inventory、disk budget 和
  basic completion。若任一 smoke hard gate 失败，smoke 终态必须为 `ABORTED` 或 `INVALID`，不得发布
  `SMOKE_NON_ADMISSION` 作为通过终态；query p99 比例、median drift 与 lifecycle 相对延迟只允许记录为
  诊断信息，不得计入 smoke pass/fail、排名或后端选择。
- lifecycle smoke 只验证同名操作能够完成以及 count、identity 和必要状态正确；不得把进程启动、schema
  创建、提交或 publication wrapper 固定开销纳入相对比较。full 仍遵守 3.16 的同名操作边界。
- full 才裁决完整 quality、query latency、lifecycle latency、resource、reliability 和 packaging 门槛，
  沿用 3.10、3.14、3.16 与 3.18 的已审阅定义；完整 workload 保持 1k/3k/10k corpus 结构。每个
  backend/workload 执行五次独立 repetition，每次 query 为 20 warmup + 200 measured；每类 lifecycle
  操作为 5 warmup + 20 measured full-workload 样本。median drift 仅在 full 的五次 repetition 上计算。
- smoke workload 固定为 `smoke-1s-32`（1 source × 32 chunks）与 `smoke-2s-64`（2 sources × 32
  chunks），每个 backend/workload 运行一次 repetition。每次 query 先做 20 个 warmup，再计时 12 个
  measured query（exact、perturbed semantic、owner/source filter、no-hit 各 3 个）；build、import、rebuild、
  reopen、migration 各做 1 warmup + 2 measured。所有 timing 仅作诊断，缩小规模不能改变 full 的 corpus
  namespace、分母或阈值定义。

#### 3.21.2 full 停止条件与重试规则

- full 遇到磁盘预算 watchdog 超限、cleanup receipt 缺失、probe 非 `11/11`、网络探测触发或任何
  `unexpected_error`，必须停止并发布 `ABORTED` 或 `INVALID`，不得继续计分或从 partial artifacts 恢复数值。
- 同一 experiment ID 只允许一个终态 publication。失败不得通过反复调整实现、分母或门槛伪装为通过；任何
  实质修改必须建立新 experiment ID、新 protocol 和新的授权链。
- per-sample 唯一目录、`finally` 清理、atomic cleanup receipt、`residual_bytes_max=0`、哈希绑定、库存
  digest、11 个单一变更 fixture 与三候选后端 `sqlite-linear`、`lancedb-embedded`、`qdrant-client-local`
  继续沿用 v5 已审阅的 hard-boundary 实现要求。

#### 3.21.3 环境、候选与审阅前置条件

- v6 环境固定为 CPython `3.11.9`、LanceDB `0.38.0`、Qdrant Client `1.19.0`、NumPy `2.4.6`、
  psutil `7.2.2` 与 PyArrow `25.0.1`；安装后必须断言精确 Python 版本，依赖版本必须从安装元数据读取并
  与该清单一致。固定 synthetic vector model/version、seed、dimension、dtype 与 normalization 继续沿用
  3.18 和本协议绑定的 frozen config，不得观察结果后变更。
- 当前不得把本节视为 acquisition 授权；上述精确 PyPI 清单和唯一新临时根目录仍必须在授权文本中再次
  明确。授权还必须明确只允许 smoke，或允许在 smoke 独立审计通过后继续 full，不能由执行者自行推定。
- 不再混用 1k、3k、10k 的 source namespace；每个 fault probe 只改变一个绑定，并记录 expected/actual
  code 与 `candidate_accessed`。不得读取或复制 `D:\111_Others_Subjects`，不得启动 Qdrant server、container
  或持久服务。
- 独立审阅者是未编写且未执行该 v6 harness 的独立审计角色；项目没有专职角色时，必须由单独会话完成静态
  checklist 与证据核对，并留下 experiment/protocol、frozen-config hash、publication/report hash、库存
  digest、probe coverage、network、cleanup 和 residual 的逐项审阅记录。独立审阅不能以“程序退出成功”替代。
- 在任何 v6 acquisition 前，必须完成 harness 静态审计、scaled smoke 设计审阅和磁盘预算预检；取得授权
  后仍须按“静态审计 → smoke → 独立审计 → 满足 smoke 白名单才可 full”的顺序执行。v6 harness 必须在
  全新临时根目录中重新生成或重新实现，不能复制、修改或复用已删除的 v5 harness、venv、sample、index、
  report、inventory、receipt、publication 或统计结果；可复用的只有本计划中公开冻结的协议语义。
- canonical frozen config 必须分别记录且不得混用以下五项口径：禁止以泛化的 `probe_count`、
  `probe_queries_per_fixture` 或其他单一字段替代它们，也不得互作分母或在 inventory 中合并计数：
  - `fault_fixture_count=11`：3.18.2 列出的十一类独立 fault fixture；每个 backend/workload/repetition
    必须核对 fixture coverage `11/11`；
  - `probe_query_count=10`：每个 fixture 内用于验证拒绝、零命中、reopen 或 rollback 行为的固定
    probe-query 数量；它不是 fixture 数量，不得作为 `11/11` 的分母；
  - `smoke_probe_inventory=66`：`3 backends × 2 smoke workloads × 1 repetition × 11 fixtures = 66/66`，
    与 3.19 已核对的 v5 smoke fixture 实测一致；仅用于 smoke fixture report/inventory；
  - `full_probe_inventory=495`：`3 backends × 3 full workloads × 5 repetitions × 11 fixtures = 495/495`；
    仅用于 full fixture report/inventory，不得套用 smoke 的 `66/66`；
  - `smoke_probe_query_inventory=660` 与 `full_probe_query_inventory=4,950`：分别由
    `66 × probe_query_count=10` 与 `495 × probe_query_count=10` 得出，仅用于独立的 probe-query 样本库存核对。
  `6` 只是 smoke 的 backend×workload 组合数，不是每个 fixture 内的 probe query 数量，不得作为 frozen
  config 分母写入。smoke report 必须分别核对 per-combination fixture coverage `11/11`、run-level
  fixture inventory `66/66` 与 probe-query inventory `660/660`；full report 必须分别核对 per-combination
  `11/11`、run-level fixture inventory `495/495` 与 probe-query inventory `4,950/4,950`。
- 即使 full 全部通过，结果也只能作为 `M8-BENCHMARK` 的人工 decision input，不选择后端、不关闭决策、
  不准入、不授权生产，也不自动 commit、merge 或 push。

本节不构成 v6 执行授权。未来授权必须明确指向 `sa.m8.admission-evidence.v6` / `precommit-v6`、精确
PyPI 版本、唯一新临时根目录、仅合成数据、执行范围（仅 smoke 或 smoke 通过后 full）、生产与服务边界以及
审计后的完整清理要求；不满足这些条件时，v6 保持未启动。

#### 3.21.4 2026-09-07 文本补丁（已进入 3.21.5 重审）

独立审阅者认为 v6 协议文本与处置方案整体自洽、可执行，但在冻结前识别出两个文本级缺口；本次已按意见
修改：3.21.1 把任一 smoke hard gate 失败的唯一合法终态绑定为 `ABORTED` 或 `INVALID`，3.21.3 在
canonical config 契约中区分 `fault_fixture_count=11` 与 `probe_queries_per_fixture=6`（对应 `66/66`），
并禁止二者共用分母或库存计数。由于协议文本已经发生修改，3.21 必须由符合 3.21.3 定义的独立审阅者重新逐项审阅；在留下补丁后
PASS 结论前，不得把该协议视为已完成静态审阅，也不得进入 acquisition 或执行。

本次补丁不构成临时根目录创建、依赖安装、smoke、full、后端选择、决策关闭、M8 准入、生产实现、commit、
merge 或 push 授权。重审通过后的下一步仍须由负责人针对 `sa.m8.admission-evidence.v6` / `precommit-v6`
明确批准含 seed `20260906`、model/version `synthetic-unit-vector-v1`、精确依赖版本、全新唯一系统临时根目录和
允许执行范围的授权文本。授权后仍按“新临时根目录 → 全新生成 harness → 独立静态审计 → 磁盘预算预检 →
CPython `3.11.9` venv 与版本自校验 → scaled smoke → 独立证据核对 → 仅
`smoke_integrity_pass=true` 才 full → 独立审阅 full → 删除整个临时根目录并确认无残留”执行；任何结果都只
作为 `M8-BENCHMARK` 人工 decision input。

#### 3.21.5 2026-09-07 独立重审记录（`NOT PASS`）

独立审阅会话未编写且未执行 v6 harness（该 harness 尚不存在），于 2026-09-07 按 3.21.3 对 3.21 全文
（含 3.21.4 工作区文本补丁）逐项重审。本记录不是 acquisition、smoke、full、后端选择、决策关闭、M8
准入、生产实现、merge 或 push 授权。

| 条款 | 结论 | 审阅要点 |
| --- | --- | --- |
| 3.21 题头 | `PASS` | 新 experiment `sa.m8.admission-evidence.v6` / protocol `precommit-v6`；只冻执行前协议文本；不授权 acquisition 或执行；执行后不得按观察结果改样本、门槛、分母或终态。 |
| 3.21.1 职责与采样 | `PASS` | smoke 只裁决 harness、依赖、probe 覆盖、网络、清理、库存、磁盘预算和证据链完整性；p99 比例、median drift 与 lifecycle 相对延迟仅诊断；lifecycle smoke 只验证同名操作完成及 count/identity/必要状态；full 沿用 3.10/3.14/3.16/3.18 与 1k/3k/10k、五次 repetition、query `20 warmup + 200 measured`、lifecycle `5 warmup + 20 measured`；smoke workload 固定 `smoke-1s-32` / `smoke-2s-64`、每组合一次 repetition、12 个 measured query、lifecycle `1 warmup + 2 measured`，与 3.20 校准一致。 |
| 3.21.1 失败终态补丁 | `PASS` | 任一 smoke hard gate 失败必须发布 `ABORTED` 或 `INVALID`，不得把 `SMOKE_NON_ADMISSION` 当作失败通过终态；成功路径仍为非准入终态 `SMOKE_NON_ADMISSION`。这与 3.19 中 v5 因性能门禁发布 `INVALID / GATE_FAILED`、从而不能进入 full 的教训一致。 |
| 3.21.2 | `PASS` | full 遇磁盘预算 watchdog、缺 cleanup receipt、probe 非 `11/11`、网络探测或任何 `unexpected_error` 必须停止并发布 `ABORTED`/`INVALID`；同一 experiment ID 只允许一个终态；实质修改必须新 ID、新 protocol 和新授权链；三候选与 v5 hard-boundary 延续。 |
| 3.21.3 环境与治理 | `PASS` | CPython `3.11.9` 与 LanceDB `0.38.0` / Qdrant Client `1.19.0` / NumPy `2.4.6` / psutil `7.2.2` / PyArrow `25.0.1`；本节不是授权；授权须重申精确版本、唯一新临时根和执行范围；禁止混用 1k/3k/10k namespace、读取外部资料目录、启动 Qdrant server/container/service；独立审阅者与 hash/inventory/probe/network/cleanup/residual checklist 完整；禁止复用已删除 v5 产物；即使 full 通过也只是 `M8-BENCHMARK` 输入。 |
| 3.21.3 fixture/库存补丁 | `FAIL` | 补丁把 `66/66` 写成 `11 × probe_queries_per_fixture=6`，并把 `6` 解释为每个 fixture 内的 probe query 数，还要求 smoke 与 full 都核对 `66/66`。这与 3.18.2（每个 backend/workload/repetition 必须 `11/11`）和 3.19（v5 smoke `66/66` probe、共 `96` 个样本）不一致。v5/v6 smoke 拓扑为 3 backends × 2 workloads × 1 repetition；`3×2×11=66`，`3×2×(11 probe + 5 lifecycle)=96`。`6` 只是 smoke 的 backend×workload 组合数，不是 per-fixture query 分母。full 库存应为 `3 backends × 3 workloads × 5 repetitions × 11 fixtures = 495/495`，不得套用 smoke 的 `66/66`。`66/66` 出处是 3.19，不是 3.20。 |
| 3.21.4 程序要求 | `PASS` | 正确要求协议文本修改后必须重审；补丁本身不构成执行或提交授权；后续仍须负责人对 seed `20260906`、`synthetic-unit-vector-v1`、精确依赖、新临时根和允许范围作书面授权。 |

非阻断观察：3.21.1 白名单未点名 hash/residual（3.20 曾单列，3.21.3 审阅清单已覆盖）；`smoke_integrity_pass` 与 `full_performance_pass` 在 3.21.4 使用，但未在 3.21.1 绑定字段语义。下次文本修订时应写明前者仅由 smoke 白名单 hard gate 置位，诊断性 timing 不得置位。

总评：`NOT PASS`。必须先把 3.21.3 的 canonical config 契约改为同时记录且不得混用的三项口径，并由未编写该修正的独立会话再次逐项重审至 `PASS` 后，才能把 `precommit-v6` 视为已完成静态审阅：

- `fault_fixture_count=11`：3.18.2 的十一类独立 fixture；每个 backend/workload/repetition 核对 coverage `11/11`；
- smoke probe 库存：`3 × 2 × 1 × 11 = 66/66`（与 3.19 已核对的 v5 smoke 实测一致）；
- full probe 库存：`3 × 3 × 5 × 11 = 495/495`。

在此之前不得 acquisition，不得创建 v6 临时根目录或 venv，不得执行 smoke 或 full。

#### 3.21.6 2026-09-07 库存口径修正（待独立会话重审，仍为 `NOT PASS`）

同一会话已按 3.21.5 要求改写 3.21.3 的 canonical config 契约：删除 `probe_queries_per_fixture=6`，改为
分别记录 `fault_fixture_count=11`、`smoke_probe_inventory=66` 与 `full_probe_inventory=495`。因本会话
既是 3.21.5 审阅者又是该修正作者，按 3.21.3/3.21.4 不得在本会话给出补丁后 `PASS`，也不得把
`precommit-v6` 视为已完成静态审阅。

下次独立重审必须由未编写 3.21.6 修正的会话，对 3.21 全文（含本次库存口径）逐项留下 PASS/审阅记录。
在该 `PASS` 之前，不得 acquisition，不得创建 v6 临时根目录或 venv，不得执行 smoke 或 full。本次修正
不构成执行、后端选择、决策关闭、M8 准入、生产实现、merge 或 push 授权。3.21.5 的非阻断观察（hash/
residual 白名单点名，以及 `smoke_integrity_pass` / `full_performance_pass` 字段绑定）仍可在下次文本
修订中一并处理，但不作为本次修正范围。

#### 3.21.7 2026-09-07 独立重审记录（`PASS`）

独立审阅会话未编写 3.21.6 库存口径修正，未编写且未执行 v6 harness（该 harness 尚不存在），于
2026-09-07 按 3.21.3 定义对 3.21 全文（含 3.21.4 文本补丁、3.21.5 重审记录、3.21.6 库存口径修正）
逐项重审。本记录是静态审阅结论，不是 acquisition、smoke、full、后端选择、决策关闭、M8 准入、生产
实现、merge 或 push 授权。

库存口径数学核验：`fault_fixture_count=11`（3.18.2 十一类单一变更 fixture）；`smoke_probe_inventory`
`3 × 2 × 1 × 11 = 66/66`（与 3.19 已核对的 v5 smoke 实测一致）；`full_probe_inventory`
`3 × 3 × 5 × 11 = 495/495`（数学成立）；交叉验证 3.19 的 `3 × 2 × (11 probe + 5 lifecycle) = 96`
个样本与实测一致；`6` 仅是 smoke 的 backend×workload 组合数，不是 per-fixture query 分母。

| 条款 | 结论 | 审阅要点 |
| --- | --- | --- |
| 3.21 题头 | `PASS` | 新 ID `sa.m8.admission-evidence.v6` / protocol `precommit-v6`；只冻结执行前协议文本；不授权 acquisition 或执行；执行后不得按观察结果改样本、门槛、分母或终态。 |
| 3.21.1 职责与采样 | `PASS` | smoke 只裁决 harness/依赖/probe 覆盖/网络/清理/库存/磁盘预算/证据链完整性；p99 比例、median drift、lifecycle 相对延迟仅诊断；lifecycle smoke 只验证完成与 count/identity/必要状态；full 沿用 3.10/3.14/3.16/3.18、1k/3k/10k、5 repetition、query `20+200`、lifecycle `5+20`；smoke workload `smoke-1s-32`/`smoke-2s-64`、12 measured query（4 类×3）、lifecycle `1+2`，与 3.20 校准一致。 |
| 3.21.1 失败终态补丁 | `PASS` | 任一 smoke hard gate 失败 → 唯一合法终态 `ABORTED`/`INVALID`，不得发布 `SMOKE_NON_ADMISSION`；成功路径仍为非准入终态；与 3.19 v5 `INVALID / GATE_FAILED` 教训一致。 |
| 3.21.2 | `PASS` | full 遇磁盘 watchdog/缺 receipt/probe 非 11-11/网络触发/`unexpected_error` → 停止并 `ABORTED`/`INVALID`；同一 experiment ID 单终态；实质修改须新 ID+新协议+新授权链；三候选 `sqlite-linear`/`lancedb-embedded`/`qdrant-client-local` 与 v5 hard-boundary 延续。 |
| 3.21.3 环境与治理 | `PASS` | CPython 3.11.9 + 五精确版本与 3.19 实测一致；本节不是授权；授权须重申精确版本/唯一新临时根/执行范围；禁混用 namespace、禁读 `D:\111_Others_Subjects`、禁启动 Qdrant server/container/service；独立审阅者定义与 checklist 完整；禁复用已删除 v5 产物；full 通过也只是 `M8-BENCHMARK` 输入。 |
| 3.21.3 库存口径修正 | `PASS` | 三项口径（11 / 66 / 495）分别记录、分别核对、禁止混用或共用分母；`66/66` 出处修正为 3.19；`6` 身份说明正确；full 不套用 smoke 的 `66/66`。3.21.5 的 FAIL 项已解决。 |
| 3.21.4 / 3.21.5 / 3.21.6 | `PASS` | 补丁程序要求、`NOT PASS` 判定与三项修正要求、审阅者与修正作者同会话不得自判 PASS 的程序合规性均自洽。 |

非阻断观察（不构成 FAIL，建议下次文本修订一并处理）：① 3.21.1 白名单未点名 hash/residual，建议与 3.20 对齐；②
`smoke_integrity_pass` / `full_performance_pass` 字段语义未绑定，建议写明前者仅由 smoke 白名单 hard gate 置位、
诊断性 timing 不得置位，后者仅由 full 门槛裁决置位。

总评：`PASS`。3.21.5 的阻塞项（库存口径）已由 3.21.6 正确修复；本会话为未编写 3.21.6 修正的独立审阅者，
`precommit-v6` 可视为已完成静态审阅。本 PASS 不构成 acquisition、临时根目录创建、venv 创建、依赖安装、
smoke、full、后端选择、决策关闭、M8 准入、生产实现、merge 或 push 授权；下一步仍须负责人签署指向 v6 的
书面授权（seed `20260906`、`synthetic-unit-vector-v1`、精确依赖版本、唯一新临时根目录、执行范围勾选）。

#### 3.21.8 2026-09-07 `probe_query_count` 契约补正（待独立重审，当前 `NOT PASS`）

后续核对发现 3.21.7 的独立重审遗漏了授权包已冻结的 `probe_query_count=10`，因此该次 `PASS` 被本记录
撤销，不能作为 acquisition 或执行前置证据。3.21.3 已补正为同时且独立记录：

- fixture 口径：`fault_fixture_count=11`、smoke `66/66`、full `495/495`；
- probe-query 口径：`probe_query_count=10`、smoke `660/660`、full `4,950/4,950`。

fixture coverage 与 probe-query sample inventory 必须分别核对，禁止共用名称、分母或库存。由于本会话编写了
本次补正，不得自行给出补丁后 `PASS`；必须由未编写本修正且未编写/执行 v6 harness 的独立会话重新审阅
3.21 全文。在明确留下 `PASS` 前，`precommit-v6` 当前审阅状态为 `NOT PASS`，不得创建临时根目录、venv，
不得 acquisition，也不得执行 smoke 或 full。本补正及后续重审均不构成 commit、merge 或 push 授权。

#### 3.21.9 2026-09-07 独立重审记录（`PASS`）

独立审阅会话未编写 3.21.3 `probe_query_count` 补正、未编写 3.21.8 撤销记录、未编写且未执行 v6 harness
（该 harness 尚不存在），于 2026-09-07 按 3.21.3 定义对 3.21 全文（含 3.21.4–3.21.8）逐项重审。本记录是
静态审阅结论，不是 acquisition、smoke、full、后端选择、决策关闭、M8 准入、生产实现、merge 或 push 授权。

| 条款 | 结论 | 审阅要点 |
| --- | --- | --- |
| 3.21.1 失败终态 | `PASS` | L481–482：任一 smoke hard gate 失败 → 唯一合法终态 `ABORTED`/`INVALID`；`SMOKE_NON_ADMISSION` 仅限成功路径。 |
| 3.21.1 职责与采样 | `PASS` | smoke 仅裁决 harness/依赖/probe/网络/清理/库存/磁盘/证据链；p99、median drift、lifecycle 相对延迟仅诊断。 |
| 3.21.2 | `PASS` | full 遇 watchdog/缺 receipt/probe 非 11-11/网络/`unexpected_error` → `ABORTED`/`INVALID`；单终态；实质修改须新 ID。 |
| 3.21.3 环境与治理 | `PASS` | CPython 3.11.9 + 五精确版本；本节不是授权；独立审阅者定义完整。 |
| 3.21.3 六项口径 | `PASS` | `fault_fixture_count=11`、`probe_query_count=10`、smoke fixture `66/66`、full fixture `495/495`、smoke probe-query `660/660`、full probe-query `4,950/4,950`；禁止共用名称、分母或库存。660 = 66×10 是 probe-query 断言库存，不与 96 个物理样本冲突。 |
| 3.21.4–3.21.7 | `PASS` | 补丁程序、NOT PASS 判定、库存修正与审阅者独立性要求均自洽。 |
| 3.21.8 | `PASS` | 正确撤销 3.21.7 PASS（遗漏 `probe_query_count=10`），并要求未编写该补正的独立会话重审。 |
| §3.18–3.19 交叉验证 | `PASS` | 3.18.2 的十一 fixture 与 3.19 的 66/66 + 96 样本一致；`660` 不等于物理样本数。 |
| §3.20 校准 | `PASS` | hard gate 保留、性能裁决延迟至 full，3.21.1 忠实复现。 |
| 整体治理 | `PASS` | BLOCKED/NOT_STARTED、八项 OPEN、空批准字段、无后端选择、无 admission。 |

总评：`PASS`。`precommit-v6` 当前可视为已完成静态审阅。本 PASS 不构成 acquisition、临时根目录创建、venv、
依赖安装、smoke、full、后端选择、决策关闭、M8 准入、生产实现、merge 或 push 授权；下一步仍须按负责人已签署的
授权文本执行（seed `20260906`、`synthetic-unit-vector-v1`、精确依赖版本、唯一新临时根目录、Smoke 后允许 Full）。

#### 3.21.10 2026-09-08 `v6` smoke 处置（`ABORTED`，证据链无效）

负责人授权的唯一一次 `sa.m8.admission-evidence.v6` / `precommit-v6` synthetic-only smoke，在临时 harness
取得独立静态 `PASS` 后启动。运行在进入冻结 lifecycle/fixture inventory 前触发
`DISK_PREFLIGHT_FAILED`，进程以 `ABORTED`、`smoke_integrity_pass=false`、
`full_performance_pass=null`、`non_admission=true` 结束；未执行 full、未选择后端、未关闭 Decision ID，
也不构成 M8 准入或生产开工授权。

终态文件内部的直接绑定如下：

- `report.json` SHA-256 为
  `21185c4c1cd6110953b58e3167fc6f11ca6ece5ccddbdc3cd9e33e0c9412c6f4`，与 publication 和 final
  run-state 一致；
- `publication.json` SHA-256 为
  `9f8df0aecb6fa5359fab260fde2c60bdf870132bab6d19b80fef80f8643e8f68`，与 final run-state 一致；
- final run-state 为 `TERMINAL`，publication 声明网络观察 `attempt_count=0`；该观察仅覆盖 harness
  执行期，不覆盖此前已获准的依赖 acquisition。

独立证据审计结论为 `EVIDENCE INVALID`，因此上述文件不能作为有效的 v6 smoke decision evidence：

- final run-state 只保留直接 predecessor digest，未保留可逐级复核的 predecessor artifacts，也未在终态中完整绑定
  owner marker；
- report/publication 未绑定 frozen-config hash、预检测量和完整 inventory digest；
- 临时 audit 目录存在三个无法归属于本次 preflight 失败运行的旧 probe cleanup receipts，导致静态审计无法证明
  本次运行从未进入 fixture/probe inventory，也无法证明唯一运行边界；
- 终态未保存 package footprint、free-space 和 root measurement。执行后非权威复测观察到 package 约
  `550,266,930` bytes、root 约 `550,698,690` bytes；按冻结公式，package 加 `512 MiB` reserve 为
  `1,087,137,842` bytes，高于 root cap `825,157,508` bytes，但该复测未被终态哈希绑定，不能补写成运行证据。

本 experiment ID 已产生终态，不得清除证据后重跑、调整预算后重判或继续 full。任何后续实验都必须使用新
experiment ID、全新唯一临时根目录、修订后的协议与 harness、独立静态审阅和新的明确执行授权。M8 继续保持
`BLOCKED / NOT_STARTED`，八项 Decision 继续为 `OPEN`。

#### 3.21.11 2026-09-08 `v6` 磁盘预算归因分析（`v7` 预算公式修正依据）

针对 3.21.10 的 `DISK_PREFLIGHT_FAILED` 根因做独立归因。冻结公式（342–346 行）反推 root cap
`825,157,508` 得到 `metadata≈1.26 MiB`，各项为：`B≈21.7 MiB`、`per_instance≈105.5 MiB`、
`per_operation_peak(rebuild)≈274.9 MiB`、`temporary_root_peak_max=786.9 MiB`。

实测与缺口：package（依赖 venv）`550,266,930`（≈524.8 MiB）；`package + 512 MiB reserve =
1,087,137,842`（≈1,036.8 MiB）高于 root cap `825,157,508`（≈786.9 MiB），缺口 ≈ `261,980,334`
bytes（≈249.8 MiB）。

**根因判定**：不是公式结构错误，而是固定 `512 MiB` reserve 对 LanceDB 体系的依赖规模严重低估——
仅依赖 venv 实测即需 ≈525 MiB，已耗尽全部 reserve，staging/WAL/Arrow/报告/corpus 无空间。

依赖体积归因（PyPI 冻结版本实测 wheel 压缩体积）：

| 包 | wheel | 说明 |
| --- | --- | --- |
| lancedb 0.38.0 | 99.3 MiB | 主力；强制引入 lance-namespace(Lance 引擎) 与 pyarrow>=16 |
| pyarrow 25.0.1 | 26.6 MiB | LanceDB 硬依赖，Arrow 存储引擎 |
| numpy 2.4.6 | 12.0 MiB | 公共依赖 |
| qdrant-client 1.19.0 | 0.4 MiB | 纯 Python 瘦客户端；但 `qdrant-client-local` 可能引入本地 server 二进制（待实测） |
| grpcio（传递） | 4.9 MiB | qdrant-client 的 gRPC 层 |
| psutil 7.2.2 | 0.1 MiB | 极小 |

**结论**：LanceDB 全家桶（lancedb + lance-namespace + pyarrow + numpy ≈ 138+ MiB 压缩 wheel）解压后
磁盘占用约 3–4 倍（与实测 524.8 MiB package 吻合），是预算被突破的绝对主因；未启用 pylance/embeddings/
clip 等 heavy extra。

**v7 预算公式修正建议**（不作为本次变更，待 v7 协议独立审阅）：
1. 将固定 `512 MiB` reserve 替换为"实测依赖 footprint + 独立工作 reserve"双门禁模型；
2. 建议 `temporary_root_peak_max = measured_package_footprint + work_reserve`，`work_reserve≥1.5 GiB`
   （10k 的 per_operation_peak 本身 ~275 MiB，叠加 rebuild 需余量），即 v7 root cap 约 `2 GiB+`；
3. 拆成两个独立门禁：`package_footprint ≤ cap1`（依赖上限）与 `peak_disk ≤ cap2`（工作区上限），不混算；
4. `qdrant-client-local` 是否引入本地 server 二进制是不确定项，须在 v7 预检时实测纳入。

本归因不构成 acquisition、执行、后端选择、决策关闭、M8 准入或生产授权。

#### 3.21.12 2026-09-08 `v7` 磁盘预算修正公式（草案，待 v7 协议独立审阅）

基于 3.21.11 归因，修订 3.18.1 的磁盘预算定义。本草案**未生效**，仅作为 `sa.m8.admission-evidence.v7`
协议起草输入；生效需 v7 协议冻结并取得独立审阅 `PASS` 与负责人授权。修订要点：

1. **废除固定 `512 MiB` reserve**。原 `temporary_root_peak_max = per_operation_peak_disk_max + 512 MiB`
   对 LanceDB 体系依赖规模严重低估（3.21.11），予以废弃。
2. **双门禁模型**。拆分两个相互独立、不混算的预算上限：
   - **依赖门禁** `package_footprint_cap`：等于实测 venv/package 解压后 footprint（acquisition 后立即
     实测），加固定安全余量 `PACKAGE_RESERVE_MIB = 64`。`measured_package_footprint ≤
     package_footprint_cap` 才允许进入 build 阶段。
   - **工作区门禁** `peak_disk_cap`：覆盖 staging、WAL、Arrow/cache、corpus、index 与报告，
     `peak_disk_cap = per_operation_peak_disk_max + WORK_RESERVE_MIB`。`WORK_RESERVE_MIB` 基于
     3.18.1 的 `per_operation_peak_disk_max`（10k rebuild 约 275 MiB）放大，建议
     `WORK_RESERVE_MIB = 1536`（1.5 GiB），使 v7 工作区门禁约 `1.8 GiB`；最终值在 v7 冻结时确定。
   - 根目录总上限 `temporary_root_peak_max = measured_package_footprint + peak_disk_cap`，
     即 v7 约为 `package(~525 MiB) + 1.8 GiB ≈ 2.3 GiB`，显著高于 v6 的 786.9 MiB。
3. **watchdog 行为不变**：acquisition 后先记录 package footprint，超过依赖门禁立即 `ABORTED`；任何
   创建后、操作中采样、sample 完成后、workload 完成后的 `peak_disk` 超过工作区门禁立即 `ABORTED`；
   `residual_bytes_max = 0`、`cleanup_failure_count = 0` 保持。仅 `ABORTED`，不发布任何性能终态。
4. **`qdrant-client-local` 不确定项**：是否引入本地 server 二进制待 v7 预检实测；若引入，纳入
   package footprint 门禁核算。
5. **门禁数值冻结纪律**：`PACKAGE_RESERVE_MIB` 与 `WORK_RESERVE_MIB` 必须在 v7 acquisition 前冻结，
   不得在观察实测结果后反推修改；如需调整，须建立新 experiment ID 与新授权链。

本草案不构成 acquisition、执行、后端选择、决策关闭、M8 准入或生产授权。

#### 3.21.13 2026-09-08 `v7` 执行处置（`INVALID`，无可采纳证据）

负责人确认仅允许 smoke 的 `sa.m8.admission-evidence.v7` / `precommit-v7` synthetic-only 尝试，因执行顺序
违规而终止。冻结顺序要求“全新 harness → 独立静态审计 → 磁盘预算预检 → venv/acquisition → 版本自校验 →
scaled smoke”；实际在全新 harness 完成且取得独立静态 `PASS` 前，已创建 CPython 3.11.9 venv 并开始依赖
acquisition。该顺序颠倒破坏了运行前置边界，不能通过事后补审恢复有效性。

本次尝试唯一终态为 `INVALID`，`smoke_integrity_pass=false`。scaled smoke 与 full 均未运行，未产生可采纳的
correctness、fault fixture、network、cleanup、inventory、disk-budget、evidence-chain 或性能证据；已完成的依赖安装
和预检观察也不得作为 V7 decision evidence，不产生候选排名、后端选择、Decision 关闭、M8 准入或生产开工授权。

执行终止后已停止未完成的 harness 生成，并通知独立静态审阅和证据核对会话不再处理本次尝试。唯一系统临时根目录及
临时根外的终态副本均已删除，删除后复核临时根不存在且 `residual_bytes=0`。仓库只保留本节的去敏治理事实，不保留
venv、package、harness、sample、index、report、inventory、receipt、publication 或其他临时产物。

同一 experiment ID 已产生 `INVALID` 终态，不得恢复、补审、重跑、重判或继续 full。任何后续实验必须使用新的
experiment ID、protocol、唯一临时根目录、全新 harness、独立静态审阅和新的明确书面授权。

另确认 V7 的依赖门禁 `package_footprint_cap = measured_package_footprint + 64 MiB` 为自引用公式：被门禁变量同时
决定自身上限，使 `measured_package_footprint ≤ package_footprint_cap` 在非负 reserve 下机械恒真，不能形成可失败的
预算门禁。后续 `precommit-v8` 必须在 acquisition 前冻结不依赖实测 footprint 的绝对 package cap，并把“全新临时
根目录 → 全新 harness → 独立静态 `PASS` → 磁盘预算预检 → venv/acquisition → 版本自校验 → scaled smoke”定义为
不可颠倒的 hard gate；缺少任一修订不得授权执行。

M8 继续保持 `BLOCKED / NOT_STARTED`，八项 Decision 继续为 `OPEN`。本处置不构成 v8 协议、v8 静态审阅、v8
执行授权、commit、merge 或 push 授权。

#### 3.21.14 2026-09-08 `v8` 协议冻结与仅-smoke 授权

`sa.m8.admission-evidence.v8` / `precommit-v8` 已形成正式冻结协议并取得独立静态审阅 `PASS`。协议将
`PACKAGE_FOOTPRINT_CAP = 1073741824` bytes 固定为 acquisition 前确定、且不依赖实测 footprint 的绝对常量；
`WORK_RESERVE_MIB = 1536`。同时将“全新唯一临时根目录 → 全新 harness → acquisition 前独立 harness 静态审计
`PASS` → 磁盘预算预检 → venv/acquisition → 版本自校验 → scaled smoke”冻结为不可颠倒的 hard gate。

负责人已明确授权仅执行 scaled smoke，禁止 full。该授权不允许跳过全新 harness 的 acquisition 前独立静态审计，
也不构成后端选择、Decision 关闭、M8 admission、生产实现、merge 或 push 授权。M8 继续保持
`BLOCKED / NOT_STARTED`，八项 Decision 继续为 `OPEN`。

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
