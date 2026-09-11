# V11 授权记录：`sa.m8.admission-evidence.v11`（阶段 1：root-provenance / source authoring）

- experiment ID：`sa.m8.admission-evidence.v11`
- protocol：`precommit-v11`
- 授权日期：2026-09-09
- 授权人（负责人）：用户于当前会话明确授权
- 状态：**`CONSUMED / PRE_SOURCE_PROVENANCE_INVALID`（不得继续或复用）**

本记录是负责人签发的、明确指向 V11 root-provenance / source-authoring 阶段的书面授权（V10 §3.21.17 处置
所要求的初始授权）。它**仅授权以下动作，不授权任何执行阶段**。

## 1. 授权范围（阶段 1，仅此四项）

1. **创建 V11 根**：在 system-temp 中排他创建全新、不可预测的根
   `<system-temp>/sa-m8-v11-679fc578a7d84e51ffc1fa0210a2be94`，创建后立即写入 canonical
   `root-provenance.json`，其 `allowed_artifact_prefixes` 必须同时允许 marker 自身与全部六个未来 source 文件
   （规避 V10 违规）。
2. **source authoring**：在根内 source-only 地生成/修复六个冻结 source 文件：
   `STATIC-AUDIT-CHECKLIST.md`、`acquisition-preflight.py`、`frozen-config.json`、`precommit_v11_smoke.py`、
   `requirements.txt`、`run_smoke.py`。**只写文件，不编译、不 import、不执行**。
3. **作者侧只读复核 + source freeze**：对冻结 source 做只读复核，生成 canonical source manifest 与
   source-generation inventory（记录规范化相对路径、file type、byte size、SHA-256、experiment/protocol、
   records digest）。
4. **根内卫生**：确认无 `.pyc`/`.pyo`/`__pycache__`/venv/symlink/reparse/根外路径/重复/未登记文件。

## 2. 冻结约束（阶段 1 必须遵守）

- 数据：仅合成预编码向量 `synthetic-unit-vector-v1`、seed `20260906`、512 维、`float32`、L2 归一化。
- 严禁读取、复制或索引 `D:\111_Others_Subjects`。
- 候选：`sqlite-linear`、`lancedb-embedded`、`qdrant-client-local`；Qdrant 仅本地 `path=`，不得启动 server/
  container/listener/网络/持久服务。
- 磁盘门禁冻结值：`PACKAGE_FOOTPRINT_CAP=1073741824` bytes；`WORK_RESERVE_MIB=1536`。
- 环境目标（仅 source authoring 目标，非 preflight 授权）：CPython `3.11.9`、`lancedb==0.38.0`、
  `numpy==2.4.6`、`psutil==7.2.2`、`pyarrow==25.0.1`、`qdrant-client==1.19.0`。
- 六项库存口径：fixture `11`、probe-query `10`、smoke fixture `66/66`、full fixture `495/495`、smoke
  probe-query `660/660`、full probe-query `4,950/4,950`。

## 3. 明确禁止（本授权不含，且未获另一书面授权前均禁止）

- 创建 venv、安装或获取依赖、preflight、acquisition、smoke、full、benchmark。
- 执行/编译/import 任何生成 Python、运行 harness 或任何生成程序。
- 后端选择、候选排名、Decision 关闭、M8 admission、生产实现、commit、merge、push。
- 不得修复、补审、恢复、重跑或复用 V8/V9/V10 的任何根、source、harness、venv、artifact、授权或统计结果。

## 4. predecessor 绑定

V11 仅绑定以下去敏处置 digest 作为 predecessor context，不绑定任何 V8/V9/V10 root artifact：

- V9：`f0590baaf24a187db010539f8d5e2ebfbf19616cfc3cae43dd431202a8a16eb6`
- V10：`1a7043b78e51d293ba5e0d37a7e0bfc409b05f0ba7d0bfb20010dea34aa8d4e9`

## 5. 阶段边界与后续授权

阶段 1 完成后停在 source freeze + source-generation inventory，**不得**自判独立审计 PASS。独立静态审计必须由
未编写、未修复、未执行 harness 的独立会话完成并排他写入 audit record；只有独立 `PASS` 后，才可另行取得明确
指向 `precommit-v11` 及 preflight 阶段的负责人书面授权。本授权不构成、也不继承任何 preflight 或执行授权。

实际 V11 marker 的初始 allowlist 遗漏 `source-manifest.json` 与 `source-generation-inventory.json`，且 marker
没有末尾 LF。原授权第 1 项只显式要求 allowlist 覆盖 marker 与六个 source，第 3 项则另行授权生成 manifest 与
inventory，未清楚表达后两项也必须由**初始** allowlist 覆盖；这是原授权文字与阶段 1 完整 provenance 合同之间的
表述缺口，不得事后倒推为当时已有明确九文件要求。该缺口不改变实际 marker 不完整、阶段 1 授权已消费及 V11
`PRE_SOURCE_PROVENANCE_INVALID` 的终态；本授权不得继续、恢复、补审，也不授权 V12 或任何后继动作。V12 的历史
阶段 1 另有新的书面授权、随机根、nonce、marker、source tree、manifest 与 inventory，但现亦已永久封口且不可复用。

M8 继续 `BLOCKED / NOT_STARTED`，八项 Decision 继续 `OPEN`。
