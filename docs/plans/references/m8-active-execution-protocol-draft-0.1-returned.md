# M8 active execution protocol 草案

> 文档状态：`DRAFT / UNBOUND / NOT_STATICALLY_AUDITED / NOT_AUTHORIZED / NEVER_EXECUTED`
> 文档版本：`draft-0.1`（仅为文档修订号，不是 experiment ID 或 executable protocol ID）
> 起草日期：2026-09-11
> 阶段状态：M8 继续 `BLOCKED / NOT_STARTED`
> 政策依据：[`m8-decision-closure-v1.md`](m8-decision-closure-v1.md)
> 路线图权威：[`docs/PLAN.md`](../../PLAN.md)

## 1. 文档定位与零授权声明

本文是全新的 M8 active execution protocol 草案，只冻结未来受控实证需要接受审阅的文本口径。本文不复用、
修订、延续或授权 V1-V13 的任何 experiment ID、protocol ID、root、binding、source、artifact、report、结果或
审计结论。历史材料只能解释治理风险，不能作为本协议的当前证据。

当前不分配新的 experiment ID 或 executable protocol ID，不建立 repository binding，不创建实验根、venv、
source、corpus、query/gold、wheel cache、report 或 cleanup artifact。以下字段保持机械阻断：

| 字段 | 当前值 |
| --- | --- |
| `experiment_id` | `null` |
| `executable_protocol_id` | `null` |
| `repository_commit` | `null` |
| `protocol_blob_sha256` | `null` |
| `experiment_root` | `null` |
| `dependency_lock_digest` | `null` |
| `corpus_manifest_digest` | `null` |
| `query_gold_digest` | `null` |
| `protocol_text_audit_status` | `NOT_STARTED` |
| `prepared_source_audit_status` | `NOT_STARTED` |
| `execution_authorization` | `NOT_GRANTED` |

任一字段仍为 `null`、审阅不是独立 `PASS`、或授权范围不精确时，唯一合法动作是停止；不得安装依赖、创建根、
生成 harness、运行 smoke/full benchmark 或写入任何候选结论。

## 2. 目标、范围与非目标

本协议只回答一个问题：在现行 SQLite/M7 控制面和默认离线路径完全不变时，LanceDB 嵌入式数据面能否在固定的
1K/10K/100K synthetic workload 上满足正确性、生命周期、资源和本地单用户收益门槛，从而成为后续人工选择的
合格输入。

本协议范围包括：

- SQLite linear exact oracle 的只读对照；
- LanceDB embedded exact/flat active candidate 的隔离实证；
- 1K correctness、10K single-user、100K capacity 和 100K filtered 四层 workload；
- identity、owner/source、generation/snapshot、tombstone/hard-delete、reopen/recovery 和 fallback；
- query/build/lifecycle 延迟、RSS、磁盘、安装体积、离线和 cleanup/residual；
- 独立静态审阅、分离授权、执行后独立核验和唯一终态。

本协议明确排除：

- Qdrant client/server、Milvus 和任何其他专业后端；
- `100k-concurrent`、多进程、多用户、服务化、container、listener、云端和网络依赖；
- 真实 100K 语料质量、embedding 模型优劣或 M11 数据质量结论；
- 生产 adapter、dependency、schema、API、flag、worker、service、deployment 或默认路由变更；
- `D:\111_Others_Subjects` 的读取、复制、索引或摘要；
- M8 admission、生产开工、backend selection、commit、merge 或 push 授权。

Qdrant 只有在负责人另行确认云端、常驻服务、多进程或并发需求后，才能进入另一份新修订协议；不得向本文追加。

## 3. 分离决策与授权链

下列决定必须由负责人分别书面作出，前一项通过不蕴含后一项：

| 顺序 | 决定 | 当前状态 | 允许的下一步 |
| --- | --- | --- | --- |
| `P0` | 接受本文技术口径 | `OPEN` | 仅允许记录接受或退回修订 |
| `P1` | 允许创建全新实验身份 | `OPEN` | 仅填写新 ID；不得使用 V1-V13 身份 |
| `P2` | 允许建立 repository binding | `OPEN` | 冻结 commit、原始 blob SHA-256 和输入清单 |
| `P3` | 允许独立审阅已绑定协议文本 | `OPEN` | 只审文本；不得建根、准备或执行 |
| `P4` | 允许隔离准备 | `OPEN` | 创建唯一临时根，生成 harness/input 并校验 wheel；不得 measured run |
| `P5` | 接受 prepared source/input 独立审阅 | `OPEN` | 冻结 source/harness/dependency/input digest；不得执行 |
| `P6` | 允许执行受控实证 | `OPEN` | 只执行授权明确列出的 smoke/full 层级 |
| `P7` | 接受独立结果核验 | `OPEN` | 只确认 evidence disposition，不改变阶段状态 |
| `P8` | 是否准入 M8 | `OPEN` | 必须另行更新 PLAN 与 registry |
| `P9` | 是否选择某个后端 | `OPEN` | 与 P8 分开；可选择“不采用” |

P0-P5 的任何活动都不是 benchmark execution。P6 必须引用 exact experiment/protocol identity、binding、候选版本、
允许层级、临时根、时限和 cleanup 责任。P7-P9 禁止由脚本、分数、平均值或本草案自动生成。

## 4. 候选集合与评价层级

### 4.1 冻结候选集合

| 角色 | 冻结名称 | 模式 | 是否可被选择 |
| --- | --- | --- | --- |
| correctness oracle / fallback | `sqlite-linear-exact` | 现有 SQLite 持久化 + exact cosine | 否；它是现行基线 |
| active candidate | `lancedb-embedded-exact` | 本地 embedded、exact/flat、无服务 | 仅 P9 可决定 |
| lexical compatibility sentinel | `bm25-existing-default` | 只核对默认路径未变化 | 否；不参加向量排名 |
| excluded | Qdrant、Milvus、其他后端 | 任意 | 否；不得加载或探测 |

候选集合是 hard-bound allowlist。发现额外 backend import、进程、端口、package 或结果字段时，证据为 `INVALID`。

### 4.2 评价层级

| 层级 | 名称 | 裁决范围 |
| --- | --- | --- |
| `L0` | binding/environment | 身份、digest、版本、硬件、磁盘、离线和根隔离 |
| `L1` | 1K correctness | oracle parity、identity/filter、删除、故障与错误分类 |
| `L2` | 10K single-user | 本地单用户 query/build/lifecycle 性能和重复性 |
| `L3` | 100K capacity | 容量、资源、reopen/rebuild/recovery 和收益 |
| `L4` | 100K filtered | owner/source/generation/snapshot/tombstone 过滤与隔离 |
| `L5` | operational closure | 默认路径、无网络/服务、report 完整性和零残留 |

所有 correctness、安全、授权、删除、离线和清理门禁都是 hard gate，不得以加权总分抵消。性能达标只形成
`adoption_eligible=true` 的候选输入，不形成 backend selection。

## 5. 执行环境冻结

### 5.1 固定环境

以下是草案的唯一目标环境；任一稳定字段变化必须回到 P0 形成新文档修订并重审：

| 字段 | 冻结值 |
| --- | --- |
| OS | Microsoft Windows 11，kernel `10.0.26200`, x64 |
| filesystem | 系统 `%TEMP%` 所在本地 NTFS `C:` 卷 |
| CPU | AMD Ryzen 7 7840H，8 cores / 16 logical processors |
| physical RAM | `16,309,932,032` bytes |
| Python | CPython `3.11.9`, 64-bit Windows |
| approved launcher | `platform/.venv311/Scripts/python.exe` |
| launcher SHA-256 | `E28F5B95E929738774687CD6F9F5A8C1B54B16053E9B0D4381A476BC1EC523FF` |
| process topology | 单个 benchmark coordinator；每个 measured sample 独立 child process |
| network | outbound/inbound 均禁止；不得绑定端口或启动服务 |
| clock | `time.perf_counter_ns()`；墙钟只用于审计时间戳，不用于 pass/fail |
| locale/timezone | 报告记录实际值；序列化与排序固定 UTF-8 / ordinal，不依赖 locale |

起草时观察到系统默认 `python` 是 `3.13.3`，不是本协议解释器。未来命令若未显式使用已冻结的 CPython 3.11.9，
L0 必须失败。起草时观察到可用物理内存约 0.47 GiB；因此当前主机不满足下述执行前置，本次不得执行。

### 5.2 每次执行前的易变资源门禁

这些值必须在创建 candidate 数据前记录；不满足时终态为 `ABORTED_PREFLIGHT`：

- available physical memory `>= 8 GiB`；
- 系统 `%TEMP%` 所在卷 available free space `>= 16 GiB`；
- CPU logical count 精确为 `16`，无其他 benchmark 进程；
- repository tracked worktree 与已绑定 commit 一致；允许的未跟踪项精确为空；
- 默认 SQLite/BM25 路径的保护性只读检查通过；
- 网络阻断探针、端口监听基线和 child-process allowlist 已启用；
- 临时根解析后位于系统 temp，且此前不存在。

### 5.3 候选依赖草案锁

| package | 拟冻结版本 | 用途 |
| --- | --- | --- |
| `lancedb` | `0.38.0` | 唯一 active candidate |
| `pyarrow` | `25.0.1` | LanceDB 数据交换 |
| `numpy` | `2.4.6` | 冻结向量表示与 oracle 计算 |
| `psutil` | `7.2.2` | child-process/RSS/连接观测 |

这些版本是规范性草案值，不是对历史运行结果的引用。P4 获批后才能下载 Windows x86-64 / CPython 3.11 对应 wheel，
冻结完整传递依赖的文件名、版本、size、SHA-256、license 和 index source，生成 canonical lock digest。禁止 sdist、
VCS、editable、`latest`、范围版本、运行期解析和网络安装。任一 wheel/metadata 不可得或不兼容时，协议退回修订，
不得替换版本后继续同一身份。

## 6. Corpus、vector、query 与 gold 冻结

### 6.1 通用生成规则

| 字段 | 冻结值 |
| --- | --- |
| seed | unsigned 64-bit integer `20260911` |
| namespace | ASCII `sa-m8-active-corpus-20260911` |
| dimension | `512` |
| dtype | little-endian IEEE-754 `float32` |
| normalization | L2；以 float64 累加后归一化，再 cast 为 float32 |
| metric | cosine；已归一化向量可用 dot product |
| vector profile | `synthetic-shake256-unit-vector-512-f32-v1` |
| row identity | `chunk-{workload}-{i:06d}`，`i` 从 0 起 |
| text payload | 仅固定 ASCII synthetic metadata；无真实正文 |
| serialization | canonical JSON Lines，UTF-8、LF、key ordinal、无 BOM |

第 `i` 行的原始向量 bytes 定义为：

1. preimage 为 `namespace || 0x00 || seed_uint64_le || i_uint64_le`；
2. 用 SHAKE-256 输出 `2048` bytes；
3. 每 4 bytes 按 little-endian `uint32 u_j` 解码；
4. 映射 `x_j = 2 * ((u_j + 0.5) / 2^32) - 1`；
5. 用 float64 计算 L2 norm 并归一化，最后逐维 cast 为 float32。

不得使用随机库的默认 generator、Python hash、时间、线程顺序或 backend 输出生成输入。生成器 source、source digest、
corpus manifest 和逐层 corpus SHA-256 必须在 candidate import 前由独立审阅者重算并冻结。

该 synthetic profile 只验证数据面，不冒充 `BAAI/bge-small-zh-v1.5` 的语义质量。报告仍须记录现行生产 profile
`BAAI/bge-small-zh-v1.5 / 512 / float32 / L2 normalized` 为 compatibility target，二者不得混称。

### 6.2 Corpus 层级与 metadata 分布

| workload | physical rows | owner × source/owner × chunks/source | 状态分布 |
| --- | ---: | --- | --- |
| `1k-correctness` | 1,000 | `5 × 10 × 20` | 100% active/current |
| `10k-single-user` | 10,000 | `10 × 20 × 50` | 100% active/current |
| `100k-capacity` | 100,000 | `20 × 50 × 100` | 100% active/current |
| `100k-filtered` | 100,000 | `20 × 50 × 100` | 80% active、10% stale generation、5% stale snapshot、5% tombstone |

owner、source 与 local chunk index 按上表的 row-major 顺序生成。`100k-filtered` 中 `i mod 20` 为 `0..15` 时 active，
`16..17` 时 stale generation，`18` 时 stale snapshot，`19` 时 tombstone。current generation/snapshot 固定为
`generation-0002` / `snapshot-0002`，stale 固定为 `generation-0001` / `snapshot-0001`。

owner ID 固定为 `owner-{o:03d}`，source ID 固定为 `source-{o:03d}-{s:03d}`。`content_fingerprint` 是按 key ordinal
序列化除自身外全部 metadata 后追加 vector little-endian bytes 所得 bytes 的 SHA-256 小写十六进制值。

每行 metadata 的 exact key set 为 `chunk_id`、`owner_id`、`source_id`、`generation_id`、`snapshot_id`、
`tombstoned`、`vector_profile`、`dimension`、`normalization`、`content_fingerprint`。额外、缺失、null 或类型变化
均使 input freeze 失败。

### 6.3 Query/gold 集

每层对全部 active row 计算 `SHA256(namespace || workload || query_kind || chunk_id)`，按 digest bytes、再按 chunk ID
升序选择前 N 个目标，不得由 backend 采样。hit query 使用目标行的 exact float32 vector。reference gold 用独立
NumPy exhaustive float64 dot product，在应用同一 filter 后按 score 降序和 `chunk_id` ordinal 升序计算 top 5；
candidate 不参与 gold 生成。

| workload | hit | exact filtered hit | deny/no-hit | total unique queries |
| --- | ---: | ---: | ---: | ---: |
| `1k-correctness` | 200 | 100 | 100 | 400 |
| `10k-single-user` | 400 | 200 | 100 | 700 |
| `100k-capacity` | 800 | 0 | 200 | 1,000 |
| `100k-filtered` | 400 | 400 | 200 | 1,000 |

filtered hit 必须同时带 exact owner/source/generation/snapshot 和 `tombstoned=false`。deny/no-hit 将目标 owner 或 source
替换为不存在的稳定 ID，并固定 `score_threshold=0.999999`；input freeze 必须证明 oracle 返回空。任一 collision、gold
重复、目标非 active 或 oracle 非确定性都使本身份在执行前失效，不得换 seed 后继续。

固定 `top_k` 分布为 1/3/5 各占 measured hit queries 的 `20%/40%/40%`；no-hit 固定 `top_k=5`。所有 query、filter、
gold、score 和排序必须写入 canonical query/gold manifest，并在 candidate import 前冻结单一 SHA-256。

## 7. Warmup、measured 与 sample count

### 7.1 Query 与 build 样本

| workload | repetitions | query warmup / measured（每 repetition） | build warmup / measured |
| --- | ---: | ---: | ---: |
| `1k-correctness` | 5 | `20 / 200` | `1 / 5` |
| `10k-single-user` | 5 | `50 / 500` | `1 / 5` |
| `100k-capacity` | 3 | `100 / 1,000` | `1 / 3` |
| `100k-filtered` | 3 | `100 / 1,000` | `1 / 3` |

每个 backend/workload/repetition 使用相同 query ordinal 顺序；顺序由 seed、workload 和 repetition 经过 SHA-256
排序得到。warmup 不进入统计，但必须走相同代码路径并单独计数。build 每个 measured sample 使用新空目录，禁止累积。

### 7.2 Lifecycle 样本

`incremental_upsert=1%`、`replace=10%`、`tombstone=1%`、`hard_delete=1%`、`reopen`、`rebuild`、
`rollback_after_failed_candidate` 七项操作使用相同语义边界。1K/10K 每项 `1 warmup + 20 measured`；100K 两层每项
`1 warmup + 5 measured`。每个样本在独立 child process 和独立 sample root 中完成 prepare、operation、query verify、
close、reopen verify 和 cleanup，不能把一个操作拆成多个伪样本。

### 7.3 Fault inventory

候选必须覆盖以下 14 个 deterministic fixture：unauthorized owner、cross source、stale generation、stale snapshot、
wrong dimension、wrong vector profile、tombstone、hard delete、partial build、corrupt manifest/index、interrupted build、
interrupted publish/cutover、missing dependency、outbound network/service attempt。

- 1K：`14 fixtures × 3 repetitions = 42` fixture instances，每个 instance 20 个 probe queries；
- 100K capacity：删除/损坏/中断相关 6 个 fixture 各 1 次，每个 instance 10 个 probe queries；
- 总库存：`48` fixture instances、`900` probe queries；
- 每个 fixture 必须有 precondition、injected fault、expected stable code、postcondition、reopen 和 cleanup receipt；
- 非法结果不能因返回空集而误判通过，必须先证明相同目标在 fault 前可见。

达到冻结的 stop gate 后，所有计划中的下游样本必须逐项记录为 `NOT_RUN_GATE_STOP`，并引用触发 gate；这些不是缺样本。
除此之外的缺样本、重复 sample ID、warmup 混入 measured、跨样本复用 index 或分母不匹配都使证据 `INVALID`。

## 8. 容差、数值阈值与裁决

### 8.1 统计口径

- latency 使用 `perf_counter_ns`，报告整数 ns；p50/p95/p99 用 nearest-rank，不插值；
- 每个 repetition 分别报告，再对 repetition percentile 取 median；不得只报告 pooled 最优值；
- RSS 每 10 ms 采样 coordinator 及全部 descendants 的 working set，报告 baseline、peak 和 delta；
- disk 使用分配 bytes 与 logical bytes，取较大值；dependency footprint 与 index/sample root 分开；
- score 以 float64 oracle 比较；绝对误差容差 `1e-5`；score 差 `<= 1e-6` 视为 tie，并按 chunk ID 排序；
- SQLite score 固定为 normalized-vector dot product；LanceDB cosine distance 固定转换为 `score = 1 - distance`；
- latency repetition median 的最大/最小比不得超过 `1.20`；超过即重复性 gate 失败，不允许删异常样本。

### 8.2 Hard correctness 与安全门禁

以下门禁全部要求精确满足：

- identity/count/metadata round-trip、filter、gold 和 required fault classification 为 `100%`；
- unauthorized、cross-owner/source、stale generation/snapshot、tombstone、hard-deleted、partial/unpublished hit 为 `0`；
- hard-delete 后 candidate object、index segment 引用和 reopen hit 均为 `0`，receipt 完整率 `100%`；
- exact top-k identity set 与 oracle agreement 为 `1.000`；Recall@1/3/5 均为 `1.000`，MRR 为 `1.000`；
- no-hit precision 为 `1.000`；unexpected error、path/body/credential/backend raw error leakage 均为 `0`；
- network connection、listener、service/container process 和生产树写入均为 `0`；
- cleanup 后 experiment root residual entries/bytes、child process 和 open handle 均为 `0`。

任一 hard gate 失败不能被延迟或资源优势抵消。

### 8.3 性能、容量与资源门禁

| 指标 | 10K hard gate | 100K hard gate |
| --- | --- | --- |
| unfiltered query p95 | `<= 50 ms` 且 `<= 1.25 × SQLite` | `<= 100 ms` |
| unfiltered query p99 | `<= 100 ms` 且 `<= 1.50 × SQLite` | `<= 200 ms` |
| filtered query p95/p99 | `<= 75 / 150 ms` | `<= 150 / 300 ms` |
| cold reopen + first query p95 | `<= 2 s` | `<= 5 s` |
| measured build p95 | `<= 30 s` | `<= 300 s` |
| rebuild p95 | `<= 45 s` | `<= 360 s` |
| candidate peak RSS delta | `<= max(1.5 × SQLite, SQLite + 512 MiB)` | 同左且绝对 `<= 3 GiB` |
| candidate index disk | `<= 2.5 × canonical input + 256 MiB` | 同左且绝对 `<= 2 GiB` |
| isolated dependency footprint | `<= 2 GiB` | 同一环境，只计一次 |
| lifecycle success / reopen parity | `100%` | `100%` |

sample root 总预算为 `8 GiB`，达到 `7 GiB` 时 watchdog 必须停止新样本并进入 cleanup。所有绝对阈值和比值必须同时
满足；资源采样允许的测量误差为 `5%`，但预算和 cleanup 零残留不提供容差。

### 8.4 “技术通过”与“值得采用”分离

candidate 只有在 L0-L5 全部 hard gate 通过时才是 `technical_gates_pass=true`。在此基础上，以下收益门槛也全部
满足时才可写 `adoption_eligible=true`：

- 100K unfiltered query p95 `<= 0.70 × SQLite p95`；
- 100K filtered query p95 `<= 100 ms`；
- 100K measured build p95 `<= 180 s`；
- candidate peak RSS delta `<= 2 GiB`；
- 无新增默认依赖、服务、网络、授权权威或不可恢复运维负担。

`adoption_eligible=true` 仍不选择后端；P9 可以选择 LanceDB 或“不采用”。若技术证据有效但收益门槛失败，合法结论是
`VALID_NOT_ADOPTION_ELIGIBLE`，不得调低阈值重跑同一身份。

## 9. Report schema 冻结

唯一 machine report 为 canonical JSON，schema ID 固定 `sa.m8.active-evidence-report.v1`，必须包含以下 exact 顶层 key：

```json
[
  "schema_id",
  "identity",
  "binding",
  "authorization",
  "environment",
  "dependency_lock",
  "input_manifests",
  "sample_plan",
  "sample_inventory",
  "oracle_results",
  "candidate_results",
  "fault_results",
  "gates",
  "violations",
  "cleanup",
  "execution_disposition"
]
```

约束如下：

- `identity` 必须与 P1 新身份一致，且不得包含 V1-V13 ID；
- `binding` 必须包含 repo-relative protocol path、commit、blob SHA-256、source digest 和 harness digest；
- `authorization` 必须包含 P0-P6 的 reference、approver、timestamp、exact scope；
- `environment` 必须包含 OS/CPU/RAM/disk/Python、locale、timezone、process、port 和 network inventories；
- `input_manifests` 必须包含 corpus/query/gold/vector profile 的 count、digest 和 generator digest；
- `sample_inventory` 必须逐项给 planned/observed/warmup/measured/valid/invalid，禁止只给汇总百分比；
- `gates` 每项包含 `gate_id`、`class`、`expected`、`actual`、`pass`、`evidence_refs`；
- `cleanup` 包含 root allowlist、before/after inventory、close/kill/delete attempts、residual entries/bytes/handles；
- 禁止绝对用户路径、正文、vector raw bytes、credential、完整 environment variable 或 backend 原始异常；
- non-finite number 禁止序列化；key ordinal、UTF-8、LF，SHA-256 针对 canonical bytes。

执行报告只能写 `EXECUTION_FINISHED_PENDING_VERIFICATION` 或明确 abort/invalid 原因，不能自行写最终采纳结论。
独立核验使用另一份 schema `sa.m8.active-evidence-verification.v1`，重算 digest、sample inventory、percentile、gate 和
cleanup 后才给 evidence disposition。

## 10. 执行、失败、cleanup 与 residual 路径

### 10.1 允许的未来路径

P4 获批后，唯一实验根必须是当时不存在的系统 temp 子目录，名称由新 experiment ID 的 SHA-256 前 16 位和
128-bit CSPRNG nonce 组成。所有 venv、wheel、source、corpus、gold、index、sample、raw report 和日志只能位于该根。
resolved path、volume serial、file ID、reparse point、hard-link count 和 NTFS alternate data streams 必须在写前及清理前核对。

仓库、`platform/.cache`、用户 profile、全局 pip cache、系统 site-packages、外部资料目录和其他 temp root 均不在
allowlist。禁止 symlink/junction/reparse point、hard link、ADS、父目录写入和环境变量扩张后的越界路径。

### 10.2 执行顺序

```text
P0 protocol accepted
  -> P1 new identity authorized
  -> P2 repository binding frozen
  -> P3 independent protocol text audit PASS
  -> P4 isolated preparation authorized
  -> P5 prepared source/input independent audit PASS and digests frozen
  -> P6 exact execution scope authorized
  -> L0 preflight
  -> L1 correctness
  -> L2 10K
  -> L3 100K capacity
  -> L4 100K filtered
  -> execution report
  -> independent result verification
  -> cleanup and residual verification
  -> evidence disposition
  -> separate P8 admission decision
  -> separate P9 backend-selection decision
```

L1 未通过不得进入 L2；L2 未通过不得进入 L3；L3 未通过不得进入 L4。smoke 若未来需要，必须在 P6 中精确授权，
只能检查 harness/inventory/cleanup，所有性能数字标为 diagnostic 且不得与 full report 合并。

### 10.3 唯一 evidence disposition

| 终态 | 含义 | 是否可支持 P8/P9 |
| --- | --- | --- |
| `VALID_ADOPTION_ELIGIBLE` | 独立核验确认全部 hard gate 与收益门槛通过 | 仅作为输入；不自动批准 |
| `VALID_NOT_ADOPTION_ELIGIBLE` | 证据完整，但至少一项技术或收益门槛失败 | 可支持“不采用”；不自动决定 |
| `INVALID_PROTOCOL_DEVIATION` | identity/input/sample/schema/授权偏离 | 否 |
| `ABORTED_PREFLIGHT` | 执行前资源、版本、根或环境门禁失败 | 否 |
| `ABORTED_RUNTIME` | watchdog、unexpected error、进程或故障注入导致中止 | 否 |
| `CLEANUP_INCOMPLETE` | 任一 residual、handle、process 或 receipt 不完整 | 否 |

同一 experiment ID 只允许一个终态。不得补跑缺样本、删除异常值、覆写 report、从 partial 恢复为 valid，或把多个身份
拼接成完整证据。实质修订必须新建文档修订、重新接受 P0-P6，并由负责人决定是否允许新的实验身份。

### 10.4 Cleanup 必达条件

独立核验者先在只读状态下核对 raw evidence，再触发已审计 cleanup。cleanup 必须关闭 backend、释放 handle、终止
allowlisted child、删除全部 sample/index/corpus/wheel/venv/source/log/report 临时对象，最后删除 experiment root 本身。
核验者必须确认 root 不存在、父 temp 没有同 nonce sibling、residual bytes/entries/handles/process/listeners 为零。

若需要保留结果，只能在 cleanup 前由独立核验者产生脱敏 verification report 的 canonical bytes 和 SHA-256；实际写入
仓库、外部 archive 或其他路径需要另一份明确授权，不在 P6 内。cleanup 失败永远覆盖性能结论，终态固定
`CLEANUP_INCOMPLETE`。

## 11. 独立静态审阅清单

独立审阅分两次进行：P3 只审已绑定协议文本；P5 审 P4 产生的 prepared source、harness、dependency lock 和
input manifest。审阅者不得是对应 protocol/harness 作者，也不得安装依赖或执行 benchmark。两次审阅合计至少确认：

- 本文与新身份均不复用 V1-V13；所有历史结果未进入当前 evidence；
- P0-P6 引用、binding、commit/blob/source/harness/dependency/input digest 完整且互相一致；
- candidate allowlist 精确为 SQLite oracle、LanceDB candidate 和 BM25 sentinel；
- corpus/query/gold 可独立重算，分布、count、sample denominator 和 fault inventory 无歧义；
- hard correctness、性能、资源、收益门槛和统计算法可机械计算且执行后不可变；
- report schema、failure terminal、唯一 publication、cleanup 和 residual 路径闭合；
- 无 production tree、默认 SQLite/BM25/vector、API、registry 或 M8-M12 状态变化；
- 无外部资料读取、网络、server/container/listener、全局安装或 repository write；
- harness 对所有 writer/cleanup 阶段具有 deterministic fault hooks，不用随机 sleep 模拟顺序；
- 审阅输出只能是 `PASS` 或 `FAIL`；任一文本/source 修改都会使 PASS 失效并要求重审。

本文当前没有独立审阅结论。起草者自检、文档测试或 git diff 不得填写任何 audit status 为 `PASS`。

## 12. 待负责人分别填写的记录

| 决定 | 负责人 | 日期 | 书面引用 | 结论 |
| --- | --- | --- | --- | --- |
| P0 接受协议文本 | - | - | - | `OPEN` |
| P1 允许创建新实验身份 | - | - | - | `OPEN` |
| P2 允许 repository binding | - | - | - | `OPEN` |
| P3 允许独立协议文本审阅 | - | - | - | `OPEN` |
| P4 允许隔离准备 | - | - | - | `OPEN` |
| P5 接受 prepared source/input 独立审阅 | - | - | - | `OPEN` |
| P6 允许受控执行 | - | - | - | `OPEN` |
| P7 接受独立结果核验 | - | - | - | `OPEN` |
| P8 M8 admission | - | - | - | `OPEN` |
| P9 backend selection | - | - | - | `OPEN` |

## 13. 当前结论

本文完成后仍只是 `DRAFT / UNBOUND / NOT_STATICALLY_AUDITED / NOT_AUTHORIZED / NEVER_EXECUTED`。它不创建新的实验
身份或目录，不批准 acquisition、安装、benchmark、后端、M8 admission 或生产实现。下一合法动作只能是负责人对 P0
书面接受或退回草案；未经 P0-P6 分离授权，不得沿执行链继续。
