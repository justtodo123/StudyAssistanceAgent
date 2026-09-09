# `precommit-v11` 历史失败协议（`PRE_SOURCE_PROVENANCE_INVALID`）

- experiment ID：`sa.m8.admission-evidence.v11`
- protocol：`precommit-v11`
- 状态：**`PRE_SOURCE_PROVENANCE_INVALID`；身份、根与 source 永久不可复用**
- 前置处置：V8 `INVALID`、V9 `PRE_FREEZE_STATIC_AUDIT_FAILED`、V10 `PRE_SOURCE_GOVERNANCE_INVALID`（三者永久不可复用）
- 本文件现为去敏历史处置记录，**不构成**任何后继身份或阶段授权。
- 最终状态权威：[`docs/PLAN.md`](../PLAN.md)；准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)

## 1. 身份与前置处置

V8（`sa.m8.admission-evidence.v8` / `precommit-v8`）已因 source-only provenance 失败以 `INVALID` 永久封口；
V9（`sa.m8.admission-evidence.v9` / `precommit-v9`）已在 source freeze 前的作者侧只读复核中发现阻断缺陷，
根永久冻结且不可复用；V10（`sa.m8.admission-evidence.v10` / `precommit-v10`）因治理记录明确禁止创建根期间
错误建根、且首个 root-provenance 的 `allowed_artifact_prefixes` 未允许未来 source artifact 而以
`PRE_SOURCE_GOVERNANCE_INVALID` 永久封口。

V11 只能引用仓库中的去敏处置 digest 作为 predecessor context，不得读取、复制或复用 V8/V9/V10 的任何
harness、venv、source、sample、index、report、inventory、receipt、publication、bytecode、统计结果或临时根。
V11 predecessor 仅绑定以下去敏处置 digest：

- V9：`f0590baaf24a187db010539f8d5e2ebfbf19616cfc3cae43dd431202a8a16eb6`
- V10：`1a7043b78e51d293ba5e0d37a7e0bfc409b05f0ba7d0bfb20010dea34aa8d4e9`

不得绑定或继承 V9/V10 的 root artifact。V11 是全新 experiment/protocol 身份，必须使用全新的、不可预测的
系统临时根、root provenance marker、source-only source tree、manifest、冻结配置、inventory、execution gate、
独立审计记录及（若日后获授权）新的运行证据链。

## 2. 严格范围与禁止事项

- 仅允许合成预编码向量：`synthetic-unit-vector-v1`，seed `20260906`，512 维，`float32`，L2 归一化。
- 严禁读取、复制或索引 `D:\111_Others_Subjects`，严禁将其内容导入实验或仓库。
- 候选仅为 `sqlite-linear`、`lancedb-embedded`、`qdrant-client-local`；Qdrant 只能使用本地 `path=`，
  不得启动 server、container、listener、网络服务或持久服务。
- 即使获得后续授权，范围最多为 `smoke-1s-32` 与 `smoke-2s-64` 的 scaled smoke；full、benchmark、性能排名、
  后端选择、Decision 关闭、M8 admission、生产实现、commit、merge、push 均不在本协议授权内。
- 成功终态（若日后运行）只能是 `SMOKE_NON_ADMISSION`；失败终态只能是 `ABORTED` 或 `INVALID`。
- M8 继续保持 `BLOCKED / NOT_STARTED`，八项 Decision 保持 `OPEN`；LanceDB、Qdrant、Milvus 均未选定或获批。

## 3. 正确的 provenance 与门禁顺序（不可颠倒的 hard gate）

V11 严格按照以下不可颠倒的顺序推进；任何步骤前置未完成即执行，均自动判为 `INVALID`，不得补审、重算、恢复
或重判。

1. **书面授权（root-provenance/source-authoring）**：负责人明确书面授权，指向 `sa.m8.admission-evidence.v11`
   / `precommit-v11` 的 root-provenance 与 source-authoring 阶段。**此授权必须先行，否则不得创建根**（规避
   V10 违规）。
2. **创建 V11 根**：在 system-temp 中排他创建全新、不可预测的根，随后立即写入 canonical `root-provenance.json`。
   该 marker 必须包含 experiment/protocol、UTC 创建时间、随机 nonce、系统临时父目录、predecessor disposition
   digest、`pre_source_root_empty=true`，**且 `allowed_artifact_prefixes` 必须同时允许 marker 自身与全部
   六个未来 source artifact**（规避 V10 缺陷）。
3. **生成并修复 source tree**：仅允许协议列明的六个源码/配置文件的 source-only authoring；任何 `.pyc`、`.pyo`、
   `__pycache__`、venv、构建缓存、symlink、reparse point、根外路径、重复或未登记文件都立即 `INVALID`，
   不得清理后继续（规避 V9 的 containment 缺陷）。
4. **作者侧只读复核 + source freeze**：source freeze 前由作者侧做只读复核；通过后独立生成 canonical
   source manifest 与 source-generation inventory，记录规范化相对路径、file type、byte size、SHA-256、
   experiment/protocol 和 records digest（规避 V9 的 inventory schema 缺陷）。
5. **独立静态审计 PASS**：由未编写、未修复、未执行 harness 的独立会话，独立重算 root/source/tree/harness/
   config/inventory hashes，核对网络、数据、路径、终态与 immutable-write 边界，并排他写入独立 audit record。
6. **一次性 closed execution gate + release authorization**：只有独立 audit `PASS` 后，才可生成绑定该 audit
   record 的一次性、不可覆盖、默认关闭的 `execution-gate.json`，并另行取得明确指向 `precommit-v11` 及
   preflight 阶段的负责人书面授权和 release artifact（规避 V9 的"gate 先于 audit record"缺陷）。
7. **后续阶段逐项授权**：preflight、venv/acquisition、版本核对、smoke、cleanup 各自仍需对应的新增书面授权；
   独立 PASS 不自动授权任何后续阶段。

## 4. source-only provenance 合同

1. 创建根后、写入任何源码前，核对根为空、无链接、无 reparse point，并写入唯一 canonical `root-provenance.json`。
2. 仅写入六个冻结源码文件：`STATIC-AUDIT-CHECKLIST.md`、`acquisition-preflight.py`、`frozen-config.json`、
   `precommit_v11_smoke.py`、`requirements.txt`、`run_smoke.py`。所有路径必须位于新根内。
3. source manifest 必须记录规范化相对路径、file type、byte size、SHA-256、experiment/protocol，并绑定 manifest
   digest。发现污染时立即 `INVALID`，不得删除污染后继续。
4. 生成 source inventory 时排除 inventory 自身与 execution gate，并绑定 root provenance bytes、完整有序 source
   records、source digest 以及 `venv_created=false`、`acquisition_performed=false`、`generated_python_executed=false`。
5. 任一冻结源码或配置变化都使 manifest、inventory、gate 失效；不得在原 ID、原根或旧 digest 上打补丁。

## 5. 实现与证据硬门禁（source authoring 时必须满足）

以下约束必须在 V11 source 中真实实现，作为独立静态审计的可验证对象（修复 V9 的 8 类缺陷）：

1. **canonical JSON**：所有配置与证据文件必须为 canonical UTF-8 JSON，LF 结尾、`allow_nan=False`（显式拒绝
   NaN/Infinity）、sort_keys、separators=(",",":")。`frozen-config.json` 必须为 canonical LF JSON，能被
   preflight/launcher 的 canonical loader 接受（修复 V9 缺陷 1）。
2. **不可变写入**：用 `O_CREAT | O_EXCL` 排他创建，不得 overwrite、truncate、rename-over-existing 或
   check-then-replace；任何已存在文件不得覆盖（修复 V9 的写入顺序缺陷）。
3. **目录创建顺序**：backend 目录创建必须安全、排他、可证明先于任何写入（修复 V9 缺陷 2：`query_sample()`
   目录创建顺序）。
4. **source inventory schema**：记录规范化相对路径、file type、byte size 与 SHA-256（修复 V9 缺陷 3）。
5. **containment 检查**：根级 symlink/reparse/resolved-containment 检查完整；所有输入、输出和加载的 evidence
   递归拒绝 absolute path（修复 V9 缺陷 5 与 serializer 缺陷）。
6. **network/DNS guard**：在任何第三方 import 前安装，覆盖 socket construction、connect helpers 与 name lookup
   helpers（修复 V9 缺陷 6）。
7. **fault fixture 语义**：每个 invalid fixture 必须在 publication 前被拒绝并保持 last-good generation；tombstone
   证明物理保留而不可见；hard delete 证明物理移除且剩余检索连续有效（修复 V9 缺陷 7）。
8. **cleanup receipt 与 fail-closed**：cleanup receipt 包含完整上游绑定、峰值、零残留与 self-digest；任何 cleanup、
   写入或 publication 失败必须 fail closed，不得静默吞错或伪造成功终态（修复 V9 缺陷 8）。
9. **execution gate 绑定**：gate 必须在独立 audit record 与负责人 release authorization 之后创建，并绑定两者
   （修复 V9 缺陷 4）。
10. **predecessor digest 合同**：V9/V10 去敏处置 digest 已在上方冻结为可独立重算的 canonical payload 值，V11
    的 predecessor binding 必须引用这些已冻结值，不得再以"合同不完整"拒绝（修复 V9 的 digest 合同缺陷）。

## 6. 独立静态审计要求

审计者必须未编写、未修复且未执行 V11 harness。审计必须独立重算并记录：root provenance、source-only manifest、
bytecode count、source/tree/harness/config/inventory hashes、路径和数据边界、network 与 Qdrant 禁止项、artifact
containment、终态 schema、stop rules 及 gate freshness。predecessor digest 合同（第 5.10 条）已完整冻结，必须
纳入审计。其余每项均须有 `PASS`/`FAIL`，并绑定审计者独立性声明、时间、输入 digest 和 audit-record hash。
任何缺失、哈希不匹配、非源码文件、bytecode 或边界违规都只能产生 `INVALID`/`ABORTED`，不得事后补审、重算、
重判、恢复或更新旧 inventory/gate。当前作者/修复者会话不具备独立审计资格。

## 7. 环境与冻结门禁（source authoring 的目标，非授权 preflight）

如后续另获授权，环境必须精确为 CPython `3.11.9`，并从安装元数据核对：`lancedb==0.38.0`、`numpy==2.4.6`、
`psutil==7.2.2`、`pyarrow==25.0.1`、`qdrant-client==1.19.0`。依赖门禁为 acquisition 前冻结的绝对常量
`PACKAGE_FOOTPRINT_CAP=1073741824` bytes；工作区预留为 `WORK_RESERVE_MIB=1536`。不得根据实测结果反推修改任一
冻结值。发现 `qdrant-client-local` 引入本地 server binary 时，必须计入 footprint；不允许启动该 binary。
六项库存口径必须分别记录，不得混用：fixture `11`、probe-query `10`、smoke fixture `66/66`、full fixture
`495/495`、smoke probe-query `660/660`、full probe-query `4,950/4,950`。

## 8. 2026-09-09 治理终态

历史协议第 3.2 步只显式要求初始 allowlist 覆盖 marker 与六个 source，第 3.4 步又要求生成 manifest 与 inventory；
二者合并后并未机械地写明后两项也必须由初始 allowlist 覆盖。因此，不得倒推声称 V11 当时已有清晰的九文件
allowlist 合同；该规范缺口本身也是阶段 1 provenance 无法成立且不能原地补写的原因。

V11 阶段 1 曾取得明确书面授权并创建唯一临时根，但首个 `root-provenance.json` 的初始
`allowed_artifact_prefixes` 只覆盖 marker 与六个 source，遗漏阶段 1 必须生成的 `source-manifest.json` 和
`source-generation-inventory.json`。对 marker 的只读字节核对同时确认：UTF-8 无 BOM、无 CR，但没有末尾 LF，
不满足 canonical JSON 证据要求的“恰好一个末尾 LF”。因此 V11 在 source freeze 前以唯一终态
`PRE_SOURCE_PROVENANCE_INVALID` 永久封口；不得修复 marker、补写 allowlist、生成 manifest/inventory、补审、
恢复、重跑、重判或复用 V11 的身份、根、source、hash、inventory 或其他 artifact。

去敏处置 canonical payload（无尾随换行）为：

```json
{"experiment_id":"sa.m8.admission-evidence.v11","generated_python_executed":false,"marker_canonical_lf":false,"marker_initial_allowlist_complete":false,"preflight_started":false,"protocol":"precommit-v11","root_reusable":false,"source_freeze_completed":false,"source_reusable":false,"status":"PRE_SOURCE_PROVENANCE_INVALID","violations":["root_marker_allowlist_omitted_stage1_manifest_and_inventory","root_marker_missing_single_terminal_lf"]}
```

其 SHA-256 为 `d9dda09590956d185c96fcd828ce9daea2288b545f82887f0ec28c91ad07b64d`。该 digest 只绑定治理处置，
不是实验、审计、cleanup 或执行证据。V11 未执行 generated Python、preflight、venv、acquisition、smoke、full
或 benchmark。后继只能使用全新的递增身份；该记录形成时指定的历史后继为
`sa.m8.admission-evidence.v12` / `precommit-v12`，其现行处置见下文。

M8 继续保持 `BLOCKED / NOT_STARTED`，八项 Decision 保持 `OPEN`。以上关于 V12 source freeze 后进行独立审计、以及
独立 `PASS` 后再另行取得 preflight 与执行授权的内容，是 V11 记录形成时的历史后续流程要求，现已被 V12
独立静态审计 `FAIL` 及 §3.21.20 / V12 disposition superseded。V12 已以
`INDEPENDENT_STATIC_AUDIT_FAILED` 永久封口且不可复用；当前没有 V12 后续动作或现行后继。
