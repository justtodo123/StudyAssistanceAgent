# `precommit-v8` 正式冻结协议（仅 scaled smoke 已授权）

- 状态：**正式冻结；独立静态审阅 `PASS`；仅 scaled smoke 已获授权**
- experiment ID：`sa.m8.admission-evidence.v8`
- protocol：`precommit-v8`
- 起草依据：`docs/plans/m8-specialized-storage-plan.md` §3.20 人工校准、§3.21 `precommit-v6` 已审阅设计、§3.21.11 `v6` 磁盘预算归因分析、§3.21.12 `v7` 磁盘预算修正公式（草案）、§3.21.13 `v7` 执行处置（`INVALID`）、`precommit-v7` 协议文本
- 起草日期：2026-09-08
- 本文件冻结执行前协议文本；执行权限来自 `references/m8-v8-authorization-20260908.md`，当前仅允许 scaled smoke，禁止 full 和任何生产变更。

## 0. 为什么是 v8（继承与修订来源）

`precommit-v8` 基于 `precommit-v7` 已审阅设计，落实 `v7` 执行处置（§3.21.13）确立的**两项必改项**：

1. **去自引用的磁盘预算门禁**：v7 的 `package_footprint_cap = measured_package_footprint + 64 MiB`
   是自引用公式（门禁上限依赖它自身要去 gate 的 `measured` 变量，无法在 acquisition 前冻结）。
   v8 改为 **acquisition 前冻结的绝对常量门禁**（见 §4.1）。
2. **不可颠倒的冻结执行顺序**：v7 实际执行时 acquisition 早于 harness 独立静态审计，顺序颠倒导致
   `INVALID`。v8 将执行顺序定义为**不可颠倒的 hard gate**（见 §5），任何顺序颠倒一律判 `INVALID`。

除上述两项外，其余协议语义全部沿袭 `precommit-v7` 已审阅内容。`v7` 因顺序违规以 `INVALID` 终态关闭，
无可采纳证据（§3.21.13），不得复用其 harness、venv、sample、index、report、inventory、receipt、
publication 或统计结果；可复用的只有本计划中公开冻结的协议语义。

## 1. 与 `precommit-v7` 的关系

`precommit-v8` 在 `precommit-v7` 已审阅设计的基础上，**仅变更两处**：磁盘预算依赖门禁的去自引用
（§4.1）与执行顺序的不可颠倒 hard gate 化（§5）。其余协议语义（smoke/full 分离、六项库存口径、终态
规则、环境、候选）逐条继承 `precommit-v7`，任何未在本文件显式修改的 v7 约束在本协议中继续有效。

## 2. smoke 与 full 的职责边界（沿袭 v7 §2 = v6 §3.21.1）

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

## 3. full 停止条件与重试规则（沿袭 v7 §3 = v6 §3.21.2）

- full 遇到磁盘预算 watchdog 超限、cleanup receipt 缺失、probe 非 `11/11`、网络探测触发或任何
  `unexpected_error`，必须停止并发布 `ABORTED` 或 `INVALID`，不得继续计分或从 partial artifacts 恢复数值。
- 同一 experiment ID 只允许一个终态 publication。失败不得通过反复调整实现、分母或门槛伪装为通过；任何
  实质修改必须建立新 experiment ID、新 protocol 和新的授权链。
- per-sample 唯一目录、`finally` 清理、atomic cleanup receipt、`residual_bytes_max=0`、哈希绑定、库存
  digest、11 个单一变更 fixture 与三候选后端 `sqlite-linear`、`lancedb-embedded`、`qdrant-client-local`
  继续沿用 v5 已审阅的 hard-boundary 实现要求。

## 4. v8 磁盘预算模型（去自引用，来自 §3.21.11/§3.21.12/§3.21.13）

仍采用双门禁模型，但**依赖门禁改为 acquisition 前冻结的绝对常量**，消除 v7 的自引用。

### 4.1 依赖门禁（去自引用）

- **依赖门禁上限 `PACKAGE_FOOTPRINT_CAP` 是 acquisition 前冻结的绝对字节常量**，不是任何实测量的函数。
  本协议正式冻结 `PACKAGE_FOOTPRINT_CAP = 1073741824`（1024 MiB = 1 GiB），覆盖冻结依赖
  （lancedb + pyarrow + numpy + grpcio + qdrant-client + psutil ≈ 143 MiB 压缩 wheel、解压后约
  3–4 倍 ≈ 500–570 MiB）叠加 `qdrant-client-local` 可能的本地 server 二进制余量。该值必须保持为
  acquisition 前确定的绝对常量。
- 门禁判定：`measured_package_footprint ≤ PACKAGE_FOOTPRINT_CAP` 才允许进入 build 阶段；否则立即
  `ABORTED`。`measured_package_footprint` 是被 gate 的测量量，不进入 cap 定义本身。

### 4.2 工作区门禁

- **工作区门禁 `peak_disk_cap = per_operation_peak_disk_max + WORK_RESERVE_MIB`**。
  `WORK_RESERVE_MIB = 1536`（1.5 GiB），基于 3.18.1 的 `per_operation_peak_disk_max`（10k rebuild
  约 275 MiB）放大，使 v8 工作区门禁约 `1.8 GiB`。
- `per_operation_peak_disk_max` 由冻结公式 `B = 10,000 × 512 × 4 + canonical UTF-8 metadata bytes`
  及其派生的 `per_instance_disk_max` 定义，保持 §3.18.1 不变。

### 4.3 根目录总上限

- `temporary_root_peak_max = PACKAGE_FOOTPRINT_CAP + peak_disk_cap`
  （均为 acquisition 前可确定的常量之和），v8 约为 `1 GiB + 1.8 GiB ≈ 2.8 GiB`，显著高于 v6 的
  786.9 MiB，且不依赖实测 footprint。

### 4.4 watchdog 行为

- acquisition 完成后立即记录 `measured_package_footprint`，超过依赖门禁 `PACKAGE_FOOTPRINT_CAP`
  立即 `ABORTED`；任何创建后、操作中采样、sample 完成后、workload 完成后的 `peak_disk` 超过工作区
  门禁 `peak_disk_cap` 立即 `ABORTED`；`residual_bytes_max = 0`、`cleanup_failure_count = 0` 保持。
  仅 `ABORTED`，不发布任何性能终态。

### 4.5 门禁数值冻结纪律

- `PACKAGE_FOOTPRINT_CAP`、`WORK_RESERVE_MIB` 必须是 acquisition 前冻结的常量，不得在观察实测结果后
  反推修改；如需调整，须建立新 experiment ID 与新授权链。

## 5. 冻结执行顺序（不可颠倒的 hard gate，来自 §3.21.13 必改项 2）

以下执行顺序是 **hard gate，任何顺序颠倒立即判 `INVALID`**，不得以"结果正确"补救：

1. 创建全新的唯一系统临时根目录（必须是一个新的、不复用任何旧目录的路径）；
2. 全新生成 v8 harness（不复用 v7/v6/v5 任何 harness 文件）；
3. **独立静态审计 harness**（在 acquisition 之前完成，逐项核对并留记录）；
4. 磁盘预算预检（按 §4 冻结门禁 + `qdrant-client-local` server 二进制实测）；
5. 创建 CPython `3.11.9` venv 并安装冻结依赖（**acquisition 必须严格在步骤 3 之后**）；
6. 校验 Python 版本与依赖版本（`sys.version` 精确断言 + 安装元数据核对）；
7. 执行 scaled smoke（`smoke-1s-32`、`smoke-2s-64`）；
8. 独立证据核对（hash、fixture 库存、11/11 覆盖、probe-query 库存、network、cleanup、residual）；
9. 仅 `smoke_integrity_pass=true` 时，才允许评估是否进入 full（且须授权允许）；
10. 独立审阅结果 → 留记录 → 删除临时根目录并确认无残留。

**强制条款**：若任何步骤在其前置步骤完成前执行（尤其 acquisition/venv 创建早于 harness 独立静态审计），
则该尝试自动判为 `INVALID`，不得补审、不得恢复、不得作为任何决策证据。harness 静态审计 `PASS` 前
不得 acquisition；acquisition 前不得执行任何 smoke 或 full 测量。

## 6. 环境、候选与六项库存口径（沿袭 v7 §5）

- v8 环境固定为 CPython `3.11.9`、LanceDB `0.38.0`、Qdrant Client `1.19.0`、NumPy `2.4.6`、
  psutil `7.2.2` 与 PyArrow `25.0.1`；安装后必须断言精确 Python 版本，依赖版本必须从安装元数据读取并
  与该清单一致。固定 synthetic vector model/version、seed、dimension、dtype 与 normalization 继续沿用
  3.18 和本协议绑定的 frozen config，不得观察结果后变更。
- 当前不得把本文件视为 acquisition 授权；上述精确 PyPI 清单和唯一新临时根目录仍必须在授权文本中再次
  明确。授权还必须明确只允许 smoke，或允许在 smoke 独立审计通过后继续 full，不能由执行者自行推定。
- 不再混用 1k、3k、10k 的 source namespace；每个 fault probe 只改变一个绑定，并记录 expected/actual
  code 与 `candidate_accessed`。不得读取或复制 `D:\111_Others_Subjects`，不得启动 Qdrant server、container
  或持久服务。
- 独立审阅者是未编写且未执行该 v8 harness 的独立审计角色；项目没有专职角色时，必须由单独会话完成静态
  checklist 与证据核对，并留下 experiment/protocol、frozen-config hash、publication/report hash、库存
  digest、probe coverage、network、cleanup 和 residual 的逐项审阅记录。独立审阅不能以"程序退出成功"替代。
- 在任何 v8 acquisition 前，必须完成 harness 静态审计、scaled smoke 设计审阅和磁盘预算预检；取得授权
  后仍须按 §5 的不可颠倒顺序执行。v8 harness 必须在全新临时根目录中重新生成或重新实现，不能复制、修改
  或复用已删除的 v5/v6/v7 harness、venv、sample、index、report、inventory、receipt、publication 或
  统计结果；可复用的只有本计划中公开冻结的协议语义。
- canonical frozen config 必须分别记录且不得混用以下六项口径：禁止以泛化的 `probe_count`、
  `probe_queries_per_fixture` 或其他单一字段替代它们，也不得互作分母或在 inventory 中合并计数：
  - `fault_fixture_count=11`：3.18.2 列出的十一类独立 fault fixture；每个 backend/workload/repetition
    必须核对 fixture coverage `11/11`；
  - `probe_query_count=10`：每个 fixture 内用于验证拒绝、零命中、reopen 或 rollback 行为的固定
    probe-query 数量；它不是 fixture 数量，不得作为 `11/11` 的分母；
  - `smoke_probe_inventory=66`：`3 backends × 2 smoke workloads × 1 repetition × 11 fixtures = 66/66`，
    与 3.19 已核对的 v5 smoke fixture 实测一致；仅用于 smoke fixture report/inventory；
  - `full_probe_inventory=495`：`3 backends × 3 full workloads × 5 repetitions × 11 fixtures = 495/495`；
    仅用于 full fixture report/inventory，不得套用 smoke 的 `66/66`；
  - `smoke_probe_query_inventory=660`：`66 × probe_query_count=10 = 660/660`，仅用于 smoke
    probe-query 样本库存核对；
  - `full_probe_query_inventory=4,950`：`495 × probe_query_count=10 = 4,950/4,950`，仅用于 full
    probe-query 样本库存核对。
  `6` 只是 smoke 的 backend×workload 组合数，不是每个 fixture 内的 probe query 数量，不得作为 frozen
  config 分母写入。smoke report 必须分别核对 per-combination fixture coverage `11/11`、run-level
  fixture inventory `66/66` 与 probe-query inventory `660/660`；full report 必须分别核对 per-combination
  `11/11`、run-level fixture inventory `495/495` 与 probe-query inventory `4,950/4,950`。
- 即使 full 全部通过，结果也只能作为 `M8-BENCHMARK` 的人工 decision input，不选择后端、不关闭决策、
  不准入、不授权生产，也不自动 commit、merge 或 push。

## 7. 边界声明

本协议文件本身不构成执行授权。当前独立授权见
`references/m8-v8-authorization-20260908.md`，已明确指向 `sa.m8.admission-evidence.v8` / `precommit-v8`、
精确 PyPI 版本、唯一新临时根目录、仅合成数据、仅 scaled smoke、生产与服务边界、
`PACKAGE_FOOTPRINT_CAP = 1073741824` bytes、`WORK_RESERVE_MIB = 1536` 以及审计后的完整清理要求。
该授权明确禁止 full；即使 `smoke_integrity_pass=true`，也不得自动进入 full。

协议静态审阅 `PASS` 与仅-smoke 授权均已闭合，但执行仍必须从 §5 第一步开始，不得提前 acquisition、创建
venv 或执行 smoke。M8 继续保持 `BLOCKED / NOT_STARTED`，八项 Decision 保持 `OPEN`，无后端选择、
无 admission、无生产实现授权。

## 8. 独立静态审阅记录（`PASS`）

- 审阅会话独立性：本会话未编写本 `precommit-v8` 协议文件，未编写且未执行 v8 harness（该 harness 尚不存在），
  符合 §6 与 3.21.3 定义的独立审阅者要求。
- 审阅日期：2026-09-08
- 结论：`PASS`

| 条款 | 结论 | 审阅要点 |
| --- | --- | --- |
| §0 为什么是 v8 | `PASS` | 明确声明基于 v7 已审阅设计并落实 §3.21.13 确立的两项必改项（去自引用的磁盘预算门禁、不可颠倒的冻结执行顺序），且显式声明 v7 `INVALID` 终态证据无效、禁止复用其产物，仅复用公开冻结的协议语义——与主计划 §3.21.13 一致。 |
| §1 与 v7 关系 | `PASS` | 仅变更两处（§4.1 去自引用、§5 顺序 hard gate），其余协议语义（smoke/full 分离、六项库存口径、终态规则、环境、候选）逐条继承 v7 已审阅内容，未在本文件显式修改的 v7 约束继续有效——继承范围界定清晰，无遗漏。 |
| §2 smoke/full 职责 | `PASS` | smoke 终态固定 `SMOKE_NON_ADMISSION`；白名单 correctness/11-11 probe/network/cleanup/inventory/disk budget/basic completion；hard gate 失败唯一合法终态 `ABORTED`/`INVALID`，不得以 `SMOKE_NON_ADMISSION` 为失败通过终态；p99/median drift/lifecycle 相对延迟仅诊断；full 沿用 3.10/3.14/3.16/3.18、1k/3k/10k、5 repetition、query 20+200、lifecycle 5+20；smoke workload `smoke-1s-32`/`smoke-2s-64`、12 measured（4×3）、lifecycle 1+2——与 v7 §2 逐字一致。 |
| §3 full 停止与重试 | `PASS` | full 遇磁盘 watchdog/缺 receipt/probe 非 11-11/网络/`unexpected_error` → 停止并 `ABORTED`/`INVALID`；单终态；实质修改须新 ID+新协议+新授权链；三候选与 per-sample 清理/hard-boundary 延续。 |
| §4 磁盘预算去自引用（必改项1） | `PASS` | `PACKAGE_FOOTPRINT_CAP` 是 acquisition 前冻结的**绝对字节常量**（建议 1 GiB），非任何实测量的函数；`measured_package_footprint` 仅作被 gate 的测量量，不进入 cap 定义，`measured ≤ cap` 在 1 GiB 上限下可失败、非机械恒真——消除了 §3.21.13 指出的 v7 自引用缺陷。工作区门禁 `peak_disk_cap=per_operation_peak+1536 MiB` 与根上限 `PACKAGE_FOOTPRINT_CAP+peak_disk_cap`（≈2.8 GiB）均为 acquisition 前可确定常量之和；watchdog 任一超限仅 `ABORTED`；冻结纪律禁止按实测反推。 |
| §5 冻结执行顺序（必改项2） | `PASS` | 十步顺序为不可颠倒 hard gate：新临时根目录→全新 harness→独立静态审计（acquisition 前）→磁盘预算预检→建 venv 装依赖（acquisition 严格在步骤3后）→版本自校验→scaled smoke→独立证据核对→仅 `smoke_integrity_pass=true` 才评估 full→独立审阅并删除临时根；强制条款明确 acquisition/venv 早于 harness 静态审计即判 `INVALID`，不得补审——直接针对 v7 `INVALID` 根因（§3.21.13）。 |
| §6 环境与六项口径 | `PASS` | CPython 3.11.9 + LanceDB 0.38.0 / Qdrant Client 1.19.0 / NumPy 2.4.6 / psutil 7.2.2 / PyArrow 25.0.1，与 3.18/3.19/3.21.9 一致；六项口径（fixture 11 / probe-query 10 / smoke fixture 66 / full fixture 495 / smoke probe-query 660 / full probe-query 4,950）分别记录、禁止混用或共用分母；`6` 是 backend×workload 组合数非 per-fixture query；禁混 namespace、禁读 `D:\111_Others_Subjects`、禁启动 Qdrant server/container/service；独立审阅者定义与 checklist 完整；禁复用 v1–v7 产物；full 通过也只是 M8-BENCHMARK 输入。 |
| §7 边界声明 | `PASS` | 本协议不构成执行授权；授权须重申 experiment ID/精确 PyPI/唯一新临时根/仅合成数据/执行范围/生产与服务边界/`PACKAGE_FOOTPRINT_CAP` 与 `WORK_RESERVE_MIB` 冻结值/完整清理；未审阅通过前不得 acquisition 或执行；M8 保持 `BLOCKED / NOT_STARTED`、八项决策 `OPEN`、无后端选择/准入/生产授权——与主计划治理边界一致。 |

总评：`PASS`。`precommit-v8` 正确落实了 §3.21.13 要求的两项必改项：磁盘预算依赖门禁已由自引用公式改为 acquisition 前冻结的绝对常量（§4.1），执行顺序固化为不可颠倒的 hard gate（§5），并对 v7 的 `INVALID` 处置做出显式、可追溯的继承与排除；其余协议语义忠实沿袭 v7 已审阅内容，六项库存口径与引用章节均与主计划一致，未发现自引用漏洞或内部矛盾。

本 `PASS` 仅表示协议文本完成静态审阅，**不构成**后端选择、决策关闭、M8 准入、生产实现、commit、merge
或 push 授权。独立的 V8 书面授权现仅允许 scaled smoke，明确禁止 full；执行仍须严格按 §5 的不可颠倒
顺序开始，且全新 harness 必须在 acquisition 前另行取得独立静态审计 `PASS`。

> 审阅来源注：协议起草会话未自行判定 `PASS`；§8 记录来自未编写本协议、未编写且未执行 v8 harness 的
> 独立会话逐项审阅。
