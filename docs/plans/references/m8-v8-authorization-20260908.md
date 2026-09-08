# 授权书：sa.m8.admission-evidence.v8 临时合成实验

授权日期：2026-09-08
授权对象：`sa.m8.admission-evidence.v8` / `precommit-v8`
授权协议：`docs/plans/m8-v8-admission-protocol.md`（独立静态审阅 §8 已 `PASS`）
文档状态：**已授权，仅允许 scaled smoke**
授权人（负责人）：用户于当前会话明确授权

兹授权严格按照 `precommit-v8` 的不可颠倒 hard gate 顺序，在一个全新的唯一系统临时根目录中准备并执行 v8 临时合成实验。授权范围和冻结约束如下。

## 1. 环境与依赖（精确版本，安装后必须自校验）

- CPython `3.11.9`（必须对 `sys.version` 进行精确断言）
- `lancedb==0.38.0`
- `qdrant-client==1.19.0`
- `numpy==2.4.6`
- `psutil==7.2.2`
- `pyarrow==25.0.1`
- 不得使用仓库 venv；必须在唯一新临时根目录中创建独立 venv
- 依赖版本必须从安装元数据读取并与以上清单逐项核对

## 2. 数据范围

- 仅使用协议冻结的合成预编码向量：`synthetic-unit-vector-v1`
- seed：`20260906`
- dimension：`512`
- dtype：`float32`
- normalization：L2 归一化
- 不得读取、复制或索引 `D:\111_Others_Subjects`
- 不得复用 v1–v7 的 harness、venv、sample、index、report、inventory、receipt、publication 或统计结果

## 3. 磁盘预算双门禁（v8 最终冻结值）

- 依赖门禁绝对上限：`PACKAGE_FOOTPRINT_CAP = 1073741824` bytes（`1024 MiB = 1 GiB`）
- 工作区预留：`WORK_RESERVE_MIB = 1536`（`1.5 GiB`）
- 工作区门禁：`peak_disk_cap = per_operation_peak_disk_max + 1536 MiB`
- 根目录总上限：`temporary_root_peak_max = PACKAGE_FOOTPRINT_CAP + peak_disk_cap`
- `PACKAGE_FOOTPRINT_CAP` 与 `WORK_RESERVE_MIB` 均在 acquisition 前冻结，不得根据实测结果反推修改
- acquisition 后立即记录 `measured_package_footprint`；若超过 `1073741824` bytes，立即以 `ABORTED` 终止
- 创建后、操作中采样、sample 完成后或 workload 完成后的工作区 peak disk 超过 `peak_disk_cap`，立即以 `ABORTED` 终止
- `residual_bytes_max = 0`、`cleanup_failure_count = 0`
- 磁盘门禁失败不得发布性能终态或候选比较结论

## 4. `qdrant-client-local` 预检

- 在 acquisition 前的磁盘预算预检中，必须核对 `qdrant-client-local` 是否引入本地 server 二进制
- 如存在本地 server 二进制，其磁盘占用必须计入 `measured_package_footprint`
- 本授权不允许启动 Qdrant server、container、网络服务或持久服务

## 5. 执行范围

- 执行范围（负责人已确认）：☒ **仅 scaled smoke**　☐ smoke 通过后允许 full
- smoke workload 固定为：
  - `smoke-1s-32`（1 source × 32 chunks）
  - `smoke-2s-64`（2 sources × 32 chunks）
- 三个冻结候选：`sqlite-linear`、`lancedb-embedded`、`qdrant-client-local`
- 每个 backend/workload 仅运行一次 repetition
- query：20 warmup + 12 measured（exact、perturbed semantic、owner/source filter、no-hit 各 3 个）
- lifecycle：build、import、rebuild、reopen、migration 各 1 warmup + 2 measured
- smoke timing 仅作诊断，不得用于性能 pass/fail、排名或后端选择
- smoke hard gate 包括 correctness、per-combination fixture coverage `11/11`、run-level fixture inventory `66/66`、probe-query inventory `660/660`、network、cleanup、disk budget、hash/inventory/evidence-chain 与 basic completion
- smoke hard gate 全部通过时，终态只能是 `SMOKE_NON_ADMISSION`
- 任一 smoke hard gate 失败时，终态必须为 `ABORTED` 或 `INVALID`
- **本授权不允许 full protocol**。即使 `smoke_integrity_pass=true`，如需 full，必须由负责人另行书面加签扩展授权，不得自动启动

## 6. 不可颠倒的执行顺序（hard gate）

必须严格依次执行：

1. 创建全新的唯一系统临时根目录；
2. 全新生成 v8 harness；
3. 在 acquisition 前完成 harness 独立静态审计并取得 `PASS`；
4. 完成磁盘预算预检；
5. 创建 CPython `3.11.9` venv 并安装冻结依赖；
6. 校验 Python 与依赖精确版本；
7. 执行 scaled smoke；
8. 独立核对 hash、fixture 库存、11/11 覆盖、probe-query 库存、network、cleanup 和 residual；
9. 记录仅-smoke 终态，不进入 full；
10. 独立审阅完成后删除临时根目录，并确认无残留。

任何步骤在其前置步骤完成前执行，尤其是 venv/acquisition 早于 harness 独立静态审计 `PASS`，该尝试自动判为 `INVALID`；不得事后补审、恢复或作为决策证据。

## 7. 授权边界（明确不包含）

本授权不包含：

- full protocol
- 生产依赖或生产代码变更
- adapter、schema、API、runtime switch、worker
- service/container、部署或生产测试
- 后端选择、候选排名、Decision ID 关闭
- M8 admission 或生产实现授权
- commit、merge 或 push

即使 smoke 全部通过，也只能形成 `M8-BENCHMARK` 的人工 decision input。M8 继续保持 `BLOCKED / NOT_STARTED`，八项 Decision 保持 `OPEN`。

## 8. 清理与证据要求

- 所有 venv、harness、corpus、sample、index、cache、report、inventory、receipt、publication 和状态文件必须位于唯一新临时根目录
- 每个 sample 使用唯一目录，并在 `finally` 中完成 close/flush、测量、清理与 residual 核对
- report/publication 必须绑定 experiment/protocol、frozen-config hash、report hash、inventory digest、gate summary 与唯一终态
- 独立证据核对完成后，必须删除完整临时根目录并确认 `residual_bytes=0`
- 仓库仅可记录去敏治理结论，不得保存 raw report 或临时实验产物

## 9. 授权确认

授权人（负责人）：用户于当前会话确认

确认事项：

- 执行范围：**仅 smoke**
- `PACKAGE_FOOTPRINT_CAP`：**1073741824 bytes（1 GiB）**
- `WORK_RESERVE_MIB`：**1536 MiB**
- 授权日期：2026-09-08
