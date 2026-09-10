# `precommit-v12` 阶段 1 协议（root provenance / source authoring）

- experiment ID：`sa.m8.admission-evidence.v12`
- protocol：`precommit-v12`
- 状态：**`INDEPENDENT_STATIC_AUDIT_FAILED`（阶段 1 已消费；V12 永久封口）**
- 前置处置：V8 `INVALID`、V9 `PRE_FREEZE_STATIC_AUDIT_FAILED`、V10
  `PRE_SOURCE_GOVERNANCE_INVALID`、V11 `PRE_SOURCE_PROVENANCE_INVALID`；四者永久不可复用
- 最终状态权威：[`docs/PLAN.md`](../../PLAN.md)

## 1. 目标与边界

V12 仅重新建立可信的阶段 1 证据身份，并重新实现 V11 暴露问题后的六个 source。授权范围止于：创建新根、写入并
立即验证 marker、source-only authoring、作者侧只读复核、source freeze、生成 source manifest 与
source-generation inventory。禁止执行或 import 生成 Python，禁止 preflight、venv、dependency acquisition、smoke、
full、benchmark、后端选择、M8 admission、生产实现、commit、merge 或 push。

仅允许合成预编码向量 `synthetic-unit-vector-v1`，seed `20260906`，512 维，`float32`，L2 归一化。严禁读取、
复制或索引 `D:\111_Others_Subjects`。候选仅为 `sqlite-linear`、`lancedb-embedded`、
`qdrant-client-local`；Qdrant 只能使用本地 `path=`，不得启动 server、container、listener 或网络服务。

## 2. 不可颠倒的阶段 1 顺序

1. 先形成明确指向 V12 阶段 1 的书面授权。
2. 在 system-temp 中排他创建全新随机根；确认根为空且根自身及父链无 symlink/reparse/link。
3. 初始 marker allowlist 必须从第一次写入起完整覆盖九个阶段 1 文件：marker、六个 source、source manifest、
   source-generation inventory。
4. 用 `O_CREAT | O_EXCL` 语义写入唯一 `root-provenance.json`。任何 overwrite、truncate、rename-over-existing 或
   check-then-replace 均禁止。
5. marker 写入后、任何 source 写入前立即只读验证：UTF-8 无 BOM、无 CR、恰好一个末尾 LF、解析值与 canonical
   bytes 完全相等、self-digest 可重算、根除 marker 外仍为空、全根及父链无 symlink/reparse/link。
6. 只有第 5 步全部通过，才可 source-only 地写入六个 source。任一失败立即将 V12 判为 `INVALID`，不得清理后继续。
7. 作者侧只读复核通过后冻结 source；随后排他写入 canonical `source-manifest.json` 与
   `source-generation-inventory.json`。两者记录规范化相对路径、file type、byte size、SHA-256、records digest、
   experiment/protocol，并绑定 marker 原始 bytes。
8. 阶段 1 停止。独立会话审计前不得创建 execution gate、release artifact 或任何运行期文件。

## 3. 九文件初始 allowlist

1. `root-provenance.json`
2. `STATIC-AUDIT-CHECKLIST.md`
3. `acquisition-preflight.py`
4. `frozen-config.json`
5. `precommit_v12_smoke.py`
6. `requirements.txt`
7. `run_smoke.py`
8. `source-manifest.json`
9. `source-generation-inventory.json`

source freeze 时根内必须恰好为以上九个普通文件；不得出现目录、bytecode、venv、缓存、symlink、reparse point、
hard link、alternate data stream、根外解析路径或未登记 artifact。

## 4. source 实现硬门禁

- 所有 JSON loader 必须验证 UTF-8 无 BOM、无 CR、恰好一个末尾 LF、canonical-byte equality、`allow_nan=False`、
  递归拒绝 NaN/Infinity 与绝对路径；所有 evidence writer 必须排他写入并 fsync。
- 根、目录和文件必须以 `lstat`/reparse/hard-link/resolved-containment 检查保护；backend 目录须在写入前安全排他创建。
- network/DNS guard 必须在任何第三方 import 前安装，覆盖 socket construction、connect/create_connection、
  getaddrinfo/gethostbyname/gethostbyname_ex/getnameinfo/getfqdn/gethostname 与常见 HTTP helper。
- invalid fixture 必须在 publication 前被拒绝并保持 last-good；tombstone 必须证明物理保留但不可见；hard delete
  必须证明物理移除且剩余检索连续有效；不得用常量 `True`、伪造 receipt 或不可失败断言代替机械证据。
- cleanup receipt 必须绑定 root provenance、source manifest/inventory、config、gate、audit、release 与各运行
  inventory digest，记录峰值、删除 exact set、零残留和 self-digest；report 再绑定 cleanup receipt，publication 再绑定
  report，形成无环证据链。cleanup/publication 失败必须 fail closed。
- 成功终态只能为 `SMOKE_NON_ADMISSION`，失败终态只能为 `ABORTED` 或 `INVALID`。六项库存口径分别为 fixture
  `11`、probe-query `10`、smoke fixture `66/66`、full fixture `495/495`、smoke probe-query `660/660`、full
  probe-query `4,950/4,950`。

## 5. 独立审计与后续授权（历史门禁，现已失败）

source freeze 后，协议要求由未编写、未修复、未执行 V12 harness 的独立会话重算 marker/source/tree/config/
manifest/inventory digest，核对字节合同、路径/链接、网络、数据、fault fixture、cleanup、终态和不可变写入边界。
作者会话不得自判 `PASS`；只有独立审计明确 `PASS` 后，负责人原本才可另行、分离地授权 preflight。

该门禁已于 `2026-09-09T12:12:34Z` 得到 **`FAIL`**，故其成功分支永久不可达。现行报告见
[`m8-v12-independent-static-audit-fail-20260909.md`](m8-v12-independent-static-audit-fail-20260909.md)，
处置见 [`m8-v12-disposition-20260909.md`](m8-v12-disposition-20260909.md)。较早的历史
`PASS` 记录已失效，不得作为 gate、release、preflight 或执行输入。V12 不得继续；M8 仍为
`BLOCKED / NOT_STARTED`。

## 6. 2026-09-09 阶段 1 冻结结果

- 临时根：`sa-m8-v12-9fd8842953bd49b6924428a8461a5b1c`（只记录 basename）
- marker SHA-256：`746c7bd7c0ebb783dedb4a25ad08abfb2afcd1120ad408db5dfb39c43eaba7ce`
- source records SHA-256：`8f1477622dcc0795a9924814f689b6498b0bcb31fdb404d516c919180bf70e71`
- source manifest SHA-256：`22c2a544fdacf1829dc1fa0f4e13f6b9d4e99be52f15f5ca3f1ec46d68b38df7`
- source-generation inventory self-digest：
  `200fd331c2c1f72d0fb1b9a28bc7d9a91d42b359ec06607fb8d8b1b55cf883ae`
- freeze UTC：`2026-09-09T10:21:13Z`

作者侧只读复核确认根内恰好九个普通文件；各文件无 BOM、无 CR、恰好一个终止 LF、无 reparse、hard-link count
均为 1、仅有默认 data stream。manifest/inventory 均通过 canonical-byte equality、自摘要与 source hash 重算。
`generated_python_executed=false`、`preflight_started=false`、`venv_created=false`、
`acquisition_performed=false`。这些事实只证明阶段 1 source freeze，不构成独立审计 `PASS`。
