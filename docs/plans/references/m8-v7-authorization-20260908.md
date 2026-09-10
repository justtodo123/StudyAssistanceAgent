# 授权书：sa.m8.admission-evidence.v7 临时合成实验

授权日期：2026-09-08
授权对象：`sa.m8.admission-evidence.v7` / `precommit-v7`
授权协议：`docs/plans/references/m8-v7-admission-protocol.md`（独立静态审阅 §7 已 `PASS`）
文档状态：**待签范围记录；V7 执行尝试已 `INVALID`，处置见主 M8 计划 §3.21.13**
授权人（负责人）：____________

兹授权在一个新的唯一系统临时根目录中准备并执行 v7 临时合成实验，具体如下：

## 1. 环境与依赖（精确版本，安装后必须自校验）

- CPython `3.11.9`（`sys.version` 精确断言）
- `lancedb==0.38.0`、`qdrant-client==1.19.0`、`numpy==2.4.6`、
  `psutil==7.2.2`、`pyarrow==25.0.1`（版本从安装元数据读取核对）
- 不得使用仓库 venv；必须新建独立 venv

## 2. 数据范围

- 仅使用协议冻结的合成预编码向量（`synthetic-unit-vector-v1`，seed `20260906`，
  512 维 float32，L2 归一化）
- 不得读取或复制 `D:\111_Others_Subjects`
- 不得复用任何 v1–v6 harness、环境、样本、索引、报告或统计结果

## 3. 磁盘预算双门禁（v7 冻结值）

- `PACKAGE_RESERVE_MIB = 64`：依赖门禁 `package_footprint_cap = measured_package_footprint + 64 MiB`
- `WORK_RESERVE_MIB = 1536`（1.5 GiB）：工作区门禁
  `peak_disk_cap = per_operation_peak_disk_max + 1536 MiB`
- 根目录总上限 `temporary_root_peak_max = measured_package_footprint + peak_disk_cap`（约 2.3 GiB）
- 上述冻结值必须在 acquisition 前生效，不得在观察实测结果后反推修改
- acquisition 后先记录 package footprint，超依赖门禁立即 `ABORTED`；任何阶段 `peak_disk` 超工作区
  门禁立即 `ABORTED`；仅发布 `ABORTED`，不发布任何性能终态

## 4. `qdrant-client-local` 预检

- v7 预检时须实测 `qdrant-client-local` 是否引入本地 server 二进制；若引入，将其纳入
  package footprint 门禁核算

## 5. 执行范围

- 先重新生成 v7 harness，完成独立静态审计和磁盘预算预检，再执行 scaled smoke
  （`smoke-1s-32`、`smoke-2s-64`）
- **只有 smoke 通过** correctness、fault-fixture `11/11`、network、cleanup、inventory、
  disk-budget 和 evidence-chain hard gates，且经独立审计确认后，**才允许继续 full protocol**
  （1k/3k/10k × 5 repetitions；fixture inventory `66/66`、`495/495` 与 probe-query inventory
  `660/660`、`4,950/4,950` 分别核对）
- smoke 性能数值仅作诊断，不参与 smoke pass/fail
- 执行范围勾选（负责人已确认）：☒ 仅 smoke　☐ smoke 通过后允许 full
  注：smoke 独立核对通过后，如需要继续 full，须在现有授权基础上由负责人另行加签扩展，不自动启动 full。

## 6. 边界（本授权不包含）

生产依赖、生产代码、adapter、schema、API、runtime switch、worker、service/container、
部署、生产测试、后端选择、M8 任何决策关闭、M8 admission、生产实现、commit、merge 或 push。

## 7. 其他约束

- 不得启动 Qdrant server、container、网络服务或持久服务
- 所有 venv、harness、corpus、index、cache、report、inventory、receipt、publication
  和状态文件必须留在该临时根目录，并在独立审计完成后全部删除（`residual_bytes_max=0`）

授权人签字：____________　　日期：____________
