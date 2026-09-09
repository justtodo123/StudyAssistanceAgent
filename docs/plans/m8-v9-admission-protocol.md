# `precommit-v9` 新实验协议（独立静态审计前停止）

- experiment ID：`sa.m8.admission-evidence.v9`
- protocol：`precommit-v9`
- 状态：**pre-freeze static-audit failure；根永久冻结且不可复用；未授权执行**
- 本文件是新实验的冻结协议草案，不构成 preflight、acquisition、smoke 或 full 的执行授权。

## 1. V8 前置处置与新身份

V8（`sa.m8.admission-evidence.v8` / `precommit-v8`）已因 source-only provenance 失败以唯一终态
`INVALID` 永久封口。V8 的 bytecode 污染、过期 inventory/gate 及所有 V8 artifact 均只属于失败处置上下文，
不得作为 V9 的源码、数据、统计或证据输入，也不得复制或复用 V8 的 harness、venv、sample、index、report、
inventory、receipt、publication、bytecode 或统计结果。该历史草案曾要求绑定“仓库中记录的 V8 处置摘要 digest”，
但没有同时冻结可独立重算的 canonical V8 disposition payload 与 digest 值；该绑定合同因此不完整，不能追溯补造，
也不得复制到任何后继协议。

V9 是全新的 experiment/protocol 身份，必须使用全新的系统临时根、root owner marker、source-only source tree、
manifest、冻结配置、inventory、execution gate、独立审计记录及（若日后获授权）新的运行证据链。

## 2. 严格边界

- 仅允许合成预编码向量：`synthetic-unit-vector-v1`、seed `20260906`、dimension `512`、`float32`、L2 归一化。
- 严禁读取、复制或索引 `D:\111_Others_Subjects`，严禁把其内容导入实验或仓库。
- 严禁启动 Qdrant server、container、网络服务或持久服务；`qdrant-client-local` 只能使用允许的本地嵌入模式。
- 候选仅为 `sqlite-linear`、`lancedb-embedded`、`qdrant-client-local`。
- 范围最多为经单独书面授权的 scaled smoke：`smoke-1s-32` 与 `smoke-2s-64`，各一 repetition。
- 不允许 full、性能排名、后端选择、Decision 关闭、M8 admission、生产实现、commit、merge 或 push。
- 成功终态只能是 `SMOKE_NON_ADMISSION`；失败终态只能是 `ABORTED` 或 `INVALID`。

## 3. 环境与冻结门禁

如后续另获授权，环境必须精确为 CPython `3.11.9`，并从安装元数据核对：

- `lancedb==0.38.0`
- `numpy==2.4.6`
- `psutil==7.2.2`
- `pyarrow==25.0.1`
- `qdrant-client==1.19.0`

依赖门禁为 acquisition 前冻结的绝对常量 `PACKAGE_FOOTPRINT_CAP=1073741824` bytes；工作区预留为
`WORK_RESERVE_MIB=1536`。不得根据实测结果反推修改任一冻结值。发现 `qdrant-client-local` 引入本地 server
binary 时，必须计入 footprint；不允许启动该 binary。

六项库存口径必须分别记录，不得混用：fixture `11`、probe-query `10`、smoke fixture `66/66`、full fixture
`495/495`、smoke probe-query `660/660`、full probe-query `4,950/4,950`。

## 4. source-only provenance 合同

1. 直接在系统临时目录中排他创建不可预测的新根；不得复用任何 V8 根或旧路径。
2. 写入任何源码前，核对根为空、无链接、无 reparse point，并写入唯一 `root-provenance.json`。该 marker
   原拟包含 experiment/protocol、UTC 创建时间、随机 nonce、系统临时父目录、V8 处置 digest、允许的 artifact
   前缀及 `pre_source_root_empty=true`；其中 V8 digest 因缺少同步冻结的 canonical payload/value 而不可满足。
3. 仅写入六个冻结源码文件：`STATIC-AUDIT-CHECKLIST.md`、`acquisition-preflight.py`、`frozen-config.json`、
   `precommit_v9_smoke.py`、`requirements.txt`、`run_smoke.py`。所有路径必须位于新根内。
4. source manifest 必须记录规范化相对路径、文件类型、byte size、SHA-256、experiment/protocol，并绑定
   manifest digest。发现 `__pycache__`、`.pyc`、`.pyo`、venv、build cache、symlink、reparse point、根外路径、
   重复路径或未登记文件时，立即以 `INVALID` 停止；不得删除污染后继续。
5. 生成 source inventory 时排除 inventory 自身与 execution gate，并绑定 root provenance bytes、完整有序 source
   records、source digest 以及 `venv_created=false`、`acquisition_performed=false`、
   `generated_python_executed=false`。
6. 任一冻结源码或配置变化都使 manifest、inventory、gate 失效；不得在原 ID、原根或旧 digest 上打补丁。

## 5. 不可颠倒的执行顺序

以下顺序是 hard gate：

以下九步是 V9 的历史草案顺序，不得复制到后继协议；其中第 5 步把 gate 放在 audit record 前，是本次失败处置
已确认的阻断缺陷之一：

1. 新建唯一系统临时根并写 root provenance；
2. 生成并修复全新的 V9 source tree/harness；
3. 冻结并独立重算 source manifest、source/tree/harness/config hashes；
4. 独立静态审计 source tree 与证据链；
5. 原拟冻结一次性、不可覆盖且默认关闭的 `execution-gate.json`，再把其 digest 交给独立审计者；该顺序无效；
6. 原拟由独立审计者新增不可变 audit record，再以 release artifact 绑定 `PASS` audit record 与负责人书面授权；
7. 原拟在 preflight receipt 有效且另有授权后 acquisition、创建 venv 和核对版本；
8. 原拟在 acquisition measurement 有效且另有 smoke 授权后运行 scaled smoke；
9. 原拟在独立核对证据、终态、cleanup 与 residual 后删除新根并确认 `residual_bytes=0`。

后继协议必须先由独立审计者排他写入 `PASS` audit record，之后才可创建与该 record 绑定的一次性 closed execution
gate；preflight 仍须另行取得明确书面授权和 release artifact。

本次治理工作明确停止在 source freeze 与独立审计记录之后、任何 release artifact 之前：不得 preflight、创建
venv、安装依赖、acquisition、smoke、full 或任何 benchmark 测量。

## 6. 独立静态审计要求

审计者必须未编写、未修复且未执行 V9 harness。审计必须独立重算并记录：root provenance、source-only manifest、
bytecode count、source/tree/harness/config/inventory hashes、路径和数据边界、网络与 Qdrant 禁止项、artifact
containment、终态 schema、stop rules 及 gate freshness。V8 predecessor digest 合同因定义不完整而不能通过；
不得以猜测值、forensic artifact 或追溯补造的 payload 代替。其余每项均须有 `PASS`/`FAIL`，并绑定审计者
独立性声明、时间、输入 digest 和 audit-record hash；该缺失合同已足以阻止 V9 取得整体 `PASS`。

任何缺失、哈希不匹配、非源码文件、bytecode 或边界违规都只能产生 `INVALID`/`ABORTED`，不得事后补审、重算、
重判、恢复或更新旧 inventory/gate。当前作者/修复者会话不具备独立审计资格。

## 7. V9 pre-freeze static-audit failure disposition

作者侧只读复核在 source freeze 前发现足以阻断 provenance、execution safety、evidence integrity 和 correctness
gate 的实质缺陷，包括：frozen config 非 canonical LF JSON、`query_sample()` backend 目录创建顺序不安全、
source inventory schema 缺少规范化相对路径/file type/byte size、gate 未绑定独立 audit record 与负责人 release
authorization、root-wide symlink/reparse/resolved-containment 检查不完整、network guard 的 DNS/name-lookup
覆盖不完整、invalid fixture rejection/last-good rollback/tombstone/hard-delete 物理语义未成为 success gate、
cleanup receipt 缺少完整 binding 与 self-digest、failure publication 可能静默吞错、serializer 未显式拒绝
NaN/Infinity，以及 loaded evidence 缺少统一递归 absolute-path rejection。

该复核不是独立静态审计，不产生 `PASS`，也没有创建 source inventory、execution gate、preflight receipt、venv、
acquisition、smoke、full 或 benchmark。当前 V9 根只能作为 pre-freeze static-failure context；不得在原根修复、
清理后继续、补审、重算、重判、恢复、重跑或复用，作者侧 findings 不得当作正式 audit record。V9 授权未消费，
继续保持 `NOT_AUTHORIZED`，不能授权任何后续动作。去敏治理处置 payload（canonical JSON，无尾随换行）为：

```json
{"execution_authorized":false,"execution_gate_created":false,"experiment_id":"sa.m8.admission-evidence.v9","independent_static_audit_pass":false,"protocol":"precommit-v9","root_reusable":false,"source_frozen":false,"source_inventory_created":false,"status":"PRE_FREEZE_STATIC_AUDIT_FAILED"}
```

其 SHA-256 为 `f0590baaf24a187db010539f8d5e2ebfbf19616cfc3cae43dd431202a8a16eb6`；它不是实验、
独立审计、cleanup 或执行证据。

本段原先要求下一次尝试使用 `sa.m8.admission-evidence.v10` / `precommit-v10`；该历史后继指令已因 V10 的
`PRE_SOURCE_GOVERNANCE_INVALID` 处置而 `superseded`，不得作为现行操作要求。任何后续尝试必须使用新的递增
身份；当前治理上下文仅指向 `sa.m8.admission-evidence.v11` / `precommit-v11`，且不构成任何阶段授权。独立
静态审计 `PASS` 前，所有 preflight、venv、依赖获取/安装、acquisition、smoke、full 和 benchmark 均禁止。

## 8. 治理终态

协议文本完成静态审阅不等于 harness 独立审计通过，也不等于任何执行授权。V9 当前为 `NOT_AUTHORIZED`；M8
继续保持 `BLOCKED / NOT_STARTED`，八项 Decision 保持 `OPEN`。任何后续 preflight 或实验阶段都必须有新的、
明确指向后继递增身份（当前为 `sa.m8.admission-evidence.v11` / `precommit-v11`）的负责人书面授权，不得指向
已永久冻结的 V9，也不得从 V8 授权继承。
