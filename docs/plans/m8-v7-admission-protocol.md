# `precommit-v7` 静态冻结设计（未授权 acquisition 或执行）

- 状态：**草案，未生效**
- experiment ID：`sa.m8.admission-evidence.v7`
- protocol：`precommit-v7`
- 起草依据：`docs/plans/m8-specialized-storage-plan.md` §3.20 人工校准、§3.21 `precommit-v6` 已审阅设计、§3.21.11 `v6` 磁盘预算归因分析、§3.21.12 `v7` 磁盘预算修正公式
- 本文件冻结的是执行前的协议文本，**不授权** acquisition、smoke、full run 或任何生产变更。

## 1. 与 `precommit-v6` 的关系

`precommit-v7` 在 `precommit-v6` 已审阅设计的基础上，**仅变更磁盘预算模型**（见 §4），其余协议语义
全部沿袭 `precommit-v6` 已审阅内容，逐条继承于 `m8-specialized-storage-plan.md` §3.21。任何未在本文件
显式修改的 v6 约束，在本协议中继续有效。v6 因磁盘预算 `DISK_PREFLIGHT_FAILED` 以 `ABORTED` 终态关闭，
证据无效（§3.21.10），不得复用其 harness、venv、sample、index、report、inventory、receipt、publication
或统计结果；可复用的只有本计划中公开冻结的协议语义。

## 2. smoke 与 full 的职责边界（沿袭 v6 §3.21.1）

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

## 3. full 停止条件与重试规则（沿袭 v6 §3.21.2）

- full 遇到磁盘预算 watchdog 超限、cleanup receipt 缺失、probe 非 `11/11`、网络探测触发或任何
  `unexpected_error`，必须停止并发布 `ABORTED` 或 `INVALID`，不得继续计分或从 partial artifacts 恢复数值。
- 同一 experiment ID 只允许一个终态 publication。失败不得通过反复调整实现、分母或门槛伪装为通过；任何
  实质修改必须建立新 experiment ID、新 protocol 和新的授权链。
- per-sample 唯一目录、`finally` 清理、atomic cleanup receipt、`residual_bytes_max=0`、哈希绑定、库存
  digest、11 个单一变更 fixture 与三候选后端 `sqlite-linear`、`lancedb-embedded`、`qdrant-client-local`
  继续沿用 v5 已审阅的 hard-boundary 实现要求。

## 4. v7 磁盘预算模型（本协议唯一实质变更，来自 §3.21.12）

废弃 v6 沿用的固定 `512 MiB` reserve 公式（§3.18.1），采用**双门禁模型**：

1. **依赖门禁** `package_footprint_cap`：等于 acquisition 后实测 venv/package 解压 footprint 加固定
   安全余量 `PACKAGE_RESERVE_MIB = 64`。`measured_package_footprint ≤ package_footprint_cap` 才允许
   进入 build 阶段；否则立即 `ABORTED`。
2. **工作区门禁** `peak_disk_cap`：覆盖 staging、WAL、Arrow/cache、corpus、index 与报告，
   `peak_disk_cap = per_operation_peak_disk_max + WORK_RESERVE_MIB`。
   `WORK_RESERVE_MIB = 1536`（1.5 GiB），基于 3.18.1 的 `per_operation_peak_disk_max`（10k rebuild
   约 275 MiB）放大，使 v7 工作区门禁约 `1.8 GiB`。
3. **根目录总上限** `temporary_root_peak_max = measured_package_footprint + peak_disk_cap`，v7 约
   `package(~525 MiB) + 1.8 GiB ≈ 2.3 GiB`，显著高于 v6 的 786.9 MiB。
4. **watchdog 行为**：acquisition 后先记录 package footprint，超过依赖门禁立即 `ABORTED`；任何创建后、
   操作中采样、sample 完成后、workload 完成后的 `peak_disk` 超过工作区门禁立即 `ABORTED`；
   `residual_bytes_max = 0`、`cleanup_failure_count = 0` 保持。仅 `ABORTED`，不发布任何性能终态。
5. **`qdrant-client-local` 不确定项**：是否引入本地 server 二进制待 v7 预检实测；若引入，纳入
   package footprint 门禁核算。
6. **门禁数值冻结纪律**：`PACKAGE_RESERVE_MIB` 与 `WORK_RESERVE_MIB` 必须在 v7 acquisition 前冻结，
   不得在观察实测结果后反推修改；如需调整，须建立新 experiment ID 与新授权链。
7. `B = 10,000 × 512 × 4 + canonical UTF-8 metadata bytes` 及其派生的 `per_instance_disk_max`、
   `per_operation_peak_disk_max` 定义保持 §3.18.1 不变，仅 reserve 项由固定 `512 MiB` 改为上述双门禁。

## 5. 环境、候选与审阅前置条件（沿袭 v6 §3.21.3）

- v7 环境固定为 CPython `3.11.9`、LanceDB `0.38.0`、Qdrant Client `1.19.0`、NumPy `2.4.6`、
  psutil `7.2.2` 与 PyArrow `25.0.1`；安装后必须断言精确 Python 版本，依赖版本必须从安装元数据读取并
  与该清单一致。固定 synthetic vector model/version、seed、dimension、dtype 与 normalization 继续沿用
  3.18 和本协议绑定的 frozen config，不得观察结果后变更。
- 当前不得把本文件视为 acquisition 授权；上述精确 PyPI 清单和唯一新临时根目录仍必须在授权文本中再次
  明确。授权还必须明确只允许 smoke，或允许在 smoke 独立审计通过后继续 full，不能由执行者自行推定。
- 不再混用 1k、3k、10k 的 source namespace；每个 fault probe 只改变一个绑定，并记录 expected/actual
  code 与 `candidate_accessed`。不得读取或复制 `D:\111_Others_Subjects`，不得启动 Qdrant server、container
  或持久服务。
- 独立审阅者是未编写且未执行该 v7 harness 的独立审计角色；项目没有专职角色时，必须由单独会话完成静态
  checklist 与证据核对，并留下 experiment/protocol、frozen-config hash、publication/report hash、库存
  digest、probe coverage、network、cleanup 和 residual 的逐项审阅记录。独立审阅不能以“程序退出成功”替代。
- 在任何 v7 acquisition 前，必须完成 harness 静态审计、scaled smoke 设计审阅和磁盘预算预检；取得授权
  后仍须按“静态审计 → smoke → 独立审计 → 满足 smoke 白名单才可 full”的顺序执行。v7 harness 必须在
  全新临时根目录中重新生成或重新实现，不能复制、修改或复用已删除的 v5/v6 harness、venv、sample、index、
  report、inventory、receipt、publication 或统计结果；可复用的只有本计划中公开冻结的协议语义。
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

## 6. 边界声明

本文件不构成 v7 执行授权。未来授权必须明确指向 `sa.m8.admission-evidence.v7` / `precommit-v7`、精确
PyPI 版本、唯一新临时根目录、仅合成数据、执行范围（仅 smoke 或 smoke 通过后 full）、生产与服务边界、
`PACKAGE_RESERVE_MIB` 与 `WORK_RESERVE_MIB` 冻结值，以及审计后的完整清理要求。本协议在通过独立静态
审阅 `PASS` 前不得 acquisition、创建临时根目录或 venv、执行 smoke 或 full；M8 继续保持
`BLOCKED / NOT_STARTED`，八项 Decision 保持 `OPEN`，无后端选择、无 admission、无生产实现授权。

## 7. 独立静态审阅记录（`PASS`）

- 审阅会话独立性：本会话未编写本 `precommit-v7` 协议文件，未编写且未执行 v7 harness（该 harness 尚不存在），
  符合 3.21.3 定义的独立审阅者要求。
- 审阅日期：2026-09-08
- 结论：`PASS`

| 条款 | 结论 | 审阅要点 |
| --- | --- | --- |
| §1 与 v6 关系 | `PASS` | 仅变更磁盘预算模型，其余沿袭 v6 已审阅内容；显式声明 v6 `ABORTED` 终态证据无效、禁止复用其产物，仅复用公开冻结的协议语义。 |
| §2 smoke/full 职责 | `PASS` | smoke 终态固定 `SMOKE_NON_ADMISSION`；白名单含 correctness/11-11 probe/network/cleanup/inventory/disk budget/basic completion；hard gate 失败唯一合法终态 `ABORTED`/`INVALID`，不得以 `SMOKE_NON_ADMISSION` 为失败通过终态；p99/median drift/lifecycle 相对延迟仅诊断；full 沿用 3.10/3.14/3.16/3.18、1k/3k/10k、5 repetition、query 20+200、lifecycle 5+20；smoke workload 1s-32/2s-64、12 measured（4×3）、lifecycle 1+2——与 v6 已审阅内容逐字一致。 |
| §3 full 停止与重试 | `PASS` | full 遇磁盘 watchdog/缺 receipt/probe 非 11-11/网络/`unexpected_error` → `ABORTED`/`INVALID`；单终态；实质修改须新 ID+新协议+新授权链；三候选与 per-sample 清理/hard-boundary 延续。 |
| §4 磁盘预算双门禁 | `PASS` | 废弃固定 512 MiB reserve（v6 失败根因，§3.21.11）；依赖门禁 `package_footprint_cap=实测+64 MiB`、工作区门禁 `peak_disk_cap=per_operation_peak+1536 MiB`、根上限≈2.3 GiB；watchdog 任一超限仅 `ABORTED`；`qdrant-client-local` 不确定项待预检实测；reserve 值 acquisition 前冻结、不得按实测反推；B/per_instance/per_operation 定义保持 3.18.1 不变——修正方向与 3.21.11 归因一致且无统计矛盾。 |
| §5 环境与六项口径 | `PASS` | CPython 3.11.9 + 五精确版本；安装后断言 Python 版本、依赖从安装元数据核对；六项口径（fixture 11 / probe-query 10 / smoke fixture 66 / full fixture 495 / smoke probe-query 660 / full probe-query 4,950）分别记录、禁止混用或共用分母；`6` 是 backend×workload 组合数非 per-fixture query；report 分别核对 11-11 / 66-66 / 660-660 / 495-495 / 4,950-4,950；禁混 namespace、禁读外部目录、禁起 server/container/service；独立审阅者定义与 checklist 完整；禁复用 v5/v6 产物；full 通过也只是 M8-BENCHMARK 输入。 |
| §6 边界声明 | `PASS` | 本协议不构成执行授权；授权须重申精确 PyPI/唯一新临时根/仅合成数据/执行范围/生产与服务边界/两个 reserve 冻结值/完整清理；未审阅通过前不得 acquisition 或执行；M8 BLOCKED/NOT_STARTED、八项决策 OPEN、无后端选择/准入/生产授权。 |

总评：`PASS`。`precommit-v7` 可作为已完成静态审阅的协议文本。磁盘预算双门禁修正解决了 v6 `DISK_PREFLIGHT_FAILED` 根因（§3.21.11/§3.21.12），其余协议语义忠实沿袭 v6 已审阅内容。

本 `PASS` 不构成 acquisition、临时根目录创建、venv 创建、依赖安装、smoke、full、后端选择、决策关闭、
M8 准入、生产实现、merge 或 push 授权；下一步仍须负责人签署指向 v7 的书面授权（seed `20260906`、
`synthetic-unit-vector-v1`、精确依赖版本、唯一新临时根目录、执行范围勾选、`PACKAGE_RESERVE_MIB=64` 与
`WORK_RESERVE_MIB=1536` 冻结值），授权后按“新临时根目录 → 全新 harness → 静态审计 → 磁盘预算预检 →
CPython 3.11.9 venv → 版本自校验 → scaled smoke → 独立证据核对 → 仅 `smoke_integrity_pass=true` 才
full → 独立审阅 full → 删除临时根目录”执行。
