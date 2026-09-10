# M8 V12 独立静态审计 FAIL 报告：`sa.m8.admission-evidence.v12`

- experiment ID：`sa.m8.admission-evidence.v12`
- protocol：`precommit-v12`
- 审计目标：冻结根 `sa-m8-v12-9fd8842953bd49b6924428a8461a5b1c`
- 审计类型：全新、独立、只读静态审计
- 审计 UTC：`2026-09-09T12:12:34Z`
- 冻结 UTC（作者侧）：`2026-09-09T10:21:13Z`
- 审计结论：**`FAIL`**

## 1. 独立性与边界

本审计由未编写、未修复、未 import、未编译且未执行 V12 source 的独立会话完成。
审计期间未修改仓库或冻结根，未创建文件、目录、缓存、venv、gate、receipt、report 或 publication，未安装依赖、联网或运行 preflight、smoke、full、benchmark；仅对冻结根字节、JSON、目录元数据和静态源码进行只读核验。
本报告不构成 preflight、执行、后端选择、M8 admission、生产实现或任何后续授权。

## 2. 冻结根 exact set 与独立重算摘要

冻结根实测恰含以下九个 regular files，无子目录、venv、bytecode、cache、gate、receipt、report、publication、symlink 或 reparse；各文件 `st_nlink=1`，仅观察到默认 NTFS data stream，无额外 ADS。

| 文件 | byte size | SHA-256 |
|---|---:|---|
| `root-provenance.json` | 1104 | `746c7bd7c0ebb783dedb4a25ad08abfb2afcd1120ad408db5dfb39c43eaba7ce` |
| `STATIC-AUDIT-CHECKLIST.md` | 4217 | `8790c7fe8faf6fd7533ff631e6d985d12138055b7dbe43a61ad5daa87bbe6769` |
| `acquisition-preflight.py` | 17122 | `a554c61f0f44360d9ca29eacd886c6f8900f545c0724f8f0daa14bae7aa339f4` |
| `frozen-config.json` | 2990 | `bea3ab1cbb8fc5edc6c8f162eab682e329bb4511a93c4d03a821864c67e362ba` |
| `precommit_v12_smoke.py` | 37262 | `57d71228acd1dfe94a964be065db84cf833d3bb9ec0a79bb3f52fcaa777b8dd3` |
| `requirements.txt` | 81 | `a90774e803f61ec359146cc7f2891d80b91cb6dec33879e1e03070769f6b1250` |
| `run_smoke.py` | 11622 | `5acf76fe0b088e83c8b7c8086c387afcafab042bad8831472324bd76c30f9fc2` |
| `source-manifest.json` | 1351 | `22c2a544fdacf1829dc1fa0f4e13f6b9d4e99be52f15f5ca3f1ec46d68b38df7` |
| `source-generation-inventory.json` | 2199 | `3c710204ecc9aa0ca3001f61c006cb151ecf3d0cf9a1d913e64b693fb8bb0607` |

其他独立重算值：

- source records SHA-256：`8f1477622dcc0795a9924814f689b6498b0bcb31fdb404d516c919180bf70e71`
- marker `payload_sha256`：`0fa7815aba8637039d4f15f506915ba6b04d40abf547795cfdd0ca7c2512d634`
- manifest `manifest_payload_sha256`：`e8cc0ea6f98ca9f9b83315e0d1513dfa6fcc5d03fc5963222ee1d2ec522b3757`
- inventory self-digest：`200fd331c2c1f72d0fb1b9a28bc7d9a91d42b359ec06607fb8d8b1b55cf883ae`

九文件 exact set、canonical JSON、self-digest、source records digest、manifest/inventory 绑定及上述 SHA-256 均核验一致。

## 3. A–G 静态审计结果

- **A provenance：部分通过。** 根身份、nonce、experiment、protocol、allowlist、marker 字节合同和 self-digest 一致；marker 后 source 前根仅含 marker 的历史时序无法由冻结态重放，只能以 marker 自述佐证。
- **B source freeze/inventory：通过。** 六个 source、manifest、inventory、路径/type/size/SHA、records digest 和四项未执行标志均一致。
- **C 字节/JSON/不可变写入：通过。** canonical LF JSON、NaN/Infinity/绝对路径拒绝、`O_CREAT|O_EXCL`、写满循环、flush/fsync 和 self-digest 逻辑静态覆盖。
- **D 路径、链接与网络：不通过。** 阶段 1 冻结态检查到位，但运行期树扫描和 cleanup 未覆盖 hard-link count 与 ADS。
- **E 后端/lifecycle：不通过。** 三后端路径、向量派生和静态 fault 分支存在，但 tombstone 与 hard-delete 缺乏充分的 before/after 检索证据，且未执行验证。
- **F 证据/cleanup/终态：不通过。** 运行期 hard-link/ADS 防护缺失；异常路径没有可机械证明的失败终态与 cleanup 闭合。
- **G 后续阶段边界：通过。** 冻结根内没有 gate、venv、receipt、sample、report、publication 或运行目录；本审计不授权任何后续阶段。

## 4. 四项阻断缺陷

### 4.1 tombstone 前置可见性未证明

位置：`precommit_v12_smoke.py:667-674`。

实现仅在 tombstone 后检查目标键不在前五个搜索结果中，并检查物理状态 `tombstoned=True`；没有保存并比较 tombstone 前目标可见性。因此无法机械排除目标原本就不可见，不能证明“物理保留但逻辑不可见”由 tombstone 导致。

### 4.2 hard-delete 检索连续性未证明

位置：`precommit_v12_smoke.py:674-679`。

实现仅检查目标物理消失、状态长度减少一和一次剩余搜索非空，没有与删除前结果或 oracle 比较，未验证剩余记录检索的连续性、排序正确性和完整性。

### 4.3 运行期 hard-link / ADS 门禁缺失

位置：`precommit_v12_smoke.py:738-746`（`tree_bytes`）及 `749-771`（`safe_cleanup`）。

运行期树扫描和清理只检查 symlink/reparse/resolved-containment，未逐文件检查 `st_nlink == 1`，也未检查运行期文件 ADS。containment 不能替代 hard-link/ADS 门禁，无法完整证明 cleanup exact-set 的安全性。

### 4.4 异常路径没有可机械证明的失败终态与 cleanup 闭合

位置：`precommit_v12_smoke.py:892-955` 及顶层异常处理 `949-955`。

runtime/inventory、cleanup receipt、report、publication 依次生成时，若 cleanup、receipt、report 或 publication 任一步失败，异常路径仅打印错误并退出码 5；没有排他写入 `ABORTED`/`INVALID` 终态，没有保证失败后的残留运行目录清理，也没有失败后 residual scan。因此不满足 fail-closed 与失败终态要求。

## 5. 未独立验证的限制

以下事项无法从冻结态重放，故不冒充运行期事实：marker 后 source 前根状态的即时历史时序、三后端实际运行结果、fixture 与 probe 的实际库存、cleanup 实际 zero-residual、历史是否曾存在 ADS，以及第三方库运行时行为。

## 6. 结论与授权边界

V12 阶段 1 独立静态审计结论为 **`FAIL`**。冻结根身份、九文件集合和字节摘要仍可作为历史快照，但不能作为 PASS 或任何执行门禁输入。

本报告不授权 preflight、venv、dependency acquisition、smoke、full、benchmark、后端选择、M8 admission、生产实现、commit、merge 或 push。M8 继续保持 **`BLOCKED / NOT_STARTED`**；`sqlite-linear`、`lancedb-embedded`、`qdrant-client-local` 均未选择或批准。

V12 必须永久失败封口；不得原地修复、补审、恢复、重跑、重判或复用 root、nonce、source、manifest、inventory、digest 或其他 artifact。任何修复只能在全新 V13 身份中另行提出、授权和审计。

## 7. 2026-09-10 后续状态

上段关于 V13 的表述记录了本报告形成时唯一允许的后继方向，并不构成 V13 授权。其后提出的 V13 草案最终在
未 binding、未建根、未 source freeze、未获授权且从未执行的状态下永久停止；见
[`m8-v13-disposition-20260910.md`](m8-v13-disposition-20260910.md)。同日闭合的八项 M8 Decision 也不修复、恢复或
重判 V12。任何后续实证必须使用全新协议身份，不得复用 V12 或 V13。
