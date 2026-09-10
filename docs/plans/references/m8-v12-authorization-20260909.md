# V12 授权记录：`sa.m8.admission-evidence.v12`（阶段 1）

- experiment ID：`sa.m8.admission-evidence.v12`
- protocol：`precommit-v12`
- 授权日期：2026-09-09
- 授权人（负责人）：用户于当前会话明确授权
- 状态：**`CONSUMED / TERMINATED`（阶段 1 已完成；后续独立静态审计 `FAIL`）**

## 1. 精确授权对象

- 唯一随机临时根：
  `C:\Users\Lenovo\AppData\Local\Temp\sa-m8-v12-9fd8842953bd49b6924428a8461a5b1c`
- nonce：`8c866b27e5a14df3bfc48f085e6435f2`
- marker UTC：`2026-09-09T09:42:37Z`
- V11 disposition digest：`d9dda09590956d185c96fcd828ce9daea2288b545f82887f0ec28c91ad07b64d`

本授权只允许按 [`m8-v12-admission-protocol.md`](m8-v12-admission-protocol.md) 的不可颠倒顺序完成阶段 1。
marker 初始 allowlist 必须在第一次写入时完整覆盖九个文件；marker 写入后、任何 source 写入前，必须立即完成 UTF-8
无 BOM、无 CR、恰好一个末尾 LF、canonical-byte equality、self-digest、根仍仅含 marker 且无任何 link/reparse 的
只读验证。任一失败立即停止，V12 不得修复后继续。

## 2. 允许动作

1. 排他创建上述唯一新根并写入唯一 marker。
2. marker 即时验证全部通过后，source-only 地重新实现六个 V12 source；不得执行、import 或编译。
3. 作者侧只读复核并冻结 source。
4. 排他生成 canonical `source-manifest.json` 与 `source-generation-inventory.json`，使阶段 1 根最终恰好包含九个
   普通文件。

## 3. 明确禁止

本授权不含独立审计 `PASS`、execution gate、release artifact、preflight、venv、dependency acquisition、smoke、
full、benchmark、后端选择、Decision 关闭、M8 admission、生产实现、commit、merge 或 push。独立审计必须由未参与
V12 authoring/repair/execution 的独立会话完成；独立 `PASS` 后仍须分别取得 preflight 与执行授权。

本授权形成时，M8 保持 `BLOCKED / NOT_STARTED`，八项 Decision 保持 `OPEN`。

## 4. 授权消费结果

阶段 1 已按授权完成并停止：marker 初始 allowlist 覆盖九个文件，source tree 已冻结，manifest 与 inventory 已排他
生成并重算通过。关键绑定如下：

- marker SHA-256：`746c7bd7c0ebb783dedb4a25ad08abfb2afcd1120ad408db5dfb39c43eaba7ce`
- source records SHA-256：`8f1477622dcc0795a9924814f689b6498b0bcb31fdb404d516c919180bf70e71`
- source manifest SHA-256：`22c2a544fdacf1829dc1fa0f4e13f6b9d4e99be52f15f5ca3f1ec46d68b38df7`
- source-generation inventory self-digest：
  `200fd331c2c1f72d0fb1b9a28bc7d9a91d42b359ec06607fb8d8b1b55cf883ae`

本授权已消费完毕；后续全新独立只读审计于 `2026-09-09T12:12:34Z` 给出 **`FAIL`**。现行审计报告见
[`m8-v12-independent-static-audit-fail-20260909.md`](m8-v12-independent-static-audit-fail-20260909.md)，永久处置见
[`m8-v12-disposition-20260909.md`](m8-v12-disposition-20260909.md)。较早的历史 `PASS` 记录及其 audit digest
已失效，不得采用。

本授权至此终止：不得补充 V12 audit record、execution gate、release、preflight、venv、依赖或运行产物，不得
修复、恢复、重跑、重判或复用 V12 root、nonce、source、manifest、inventory、digest 或其他 artifact。任何后续
V13 必须另建身份、协议、根、证据链并取得新的书面授权；本记录不构成 V13 协议、授权或开工。本授权终止时，
M8 继续保持 `BLOCKED / NOT_STARTED`，八项 Decision 继续为 `OPEN`。2026-09-10 后续状态以现行主计划和治理快照为准；
后来的 Decision closure 不恢复或重新授权本 V12 身份。
