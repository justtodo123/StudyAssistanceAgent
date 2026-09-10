# M8 V12 独立静态审计处置：`sa.m8.admission-evidence.v12`

- experiment ID：`sa.m8.admission-evidence.v12`
- protocol：`precommit-v12`
- disposition date：2026-09-09
- independent audit UTC：`2026-09-09T12:12:34Z`
- 最终治理状态：**`INDEPENDENT_STATIC_AUDIT_FAILED`**
- M8 状态：**`BLOCKED / NOT_STARTED`**

## 1. 处置依据

全新独立只读审计对冻结根
`sa-m8-v12-9fd8842953bd49b6924428a8461a5b1c` 给出 **`FAIL`**。现行审计报告为
[`m8-v12-independent-static-audit-fail-20260909.md`](m8-v12-independent-static-audit-fail-20260909.md)。

`2026-09-09T11:32:50Z` 的较早 `PASS` 记录及其 audit digest 已失效，仅保留历史追溯，不得用于 gate、release、preflight 或任何授权；见
[`m8-v12-independent-static-audit-20260909.md`](m8-v12-independent-static-audit-20260909.md)。

## 2. 阻断缺陷

1. `precommit_v12_smoke.py:667-674` 未证明 tombstone 前目标可见，无法机械证明“物理保留但逻辑不可见”。
2. `precommit_v12_smoke.py:674-679` 未比较删除前后结果或 oracle，无法证明 hard-delete 后剩余检索连续、正确、完整。
3. `precommit_v12_smoke.py:738-746` 与 `749-771` 的运行期扫描/cleanup 未检查 hard-link count 与 ADS。
4. `precommit_v12_smoke.py:892-955` 的异常路径没有排他生成 `ABORTED`/`INVALID` 终态、失败 cleanup 和 residual scan，无法机械证明 fail-closed。

任一项都足以阻断独立静态审计 PASS；四项合并使 V12 不得进入 preflight 或任何执行阶段。

## 3. 历史冻结快照

V12 阶段 1 曾完成 source freeze，以下值仍只作为历史字节快照保存：

- root basename：`sa-m8-v12-9fd8842953bd49b6924428a8461a5b1c`
- nonce：`8c866b27e5a14df3bfc48f085e6435f2`
- freeze UTC：`2026-09-09T10:21:13Z`
- marker SHA-256：`746c7bd7c0ebb783dedb4a25ad08abfb2afcd1120ad408db5dfb39c43eaba7ce`
- source records SHA-256：`8f1477622dcc0795a9924814f689b6498b0bcb31fdb404d516c919180bf70e71`
- source manifest SHA-256：`22c2a544fdacf1829dc1fa0f4e13f6b9d4e99be52f15f5ca3f1ec46d68b38df7`
- source-generation inventory self-digest：
  `200fd331c2c1f72d0fb1b9a28bc7d9a91d42b359ec06607fb8d8b1b55cf883ae`

这些一致的 bytes/hash 只能证明被审计的 source 身份，不证明 source 满足协议，也不恢复旧 PASS。
本处置不另造 canonical disposition payload 或未实际重算的 disposition digest。

## 4. 未发生的阶段

V12 未运行 generated Python、preflight、venv、dependency acquisition、smoke、full、benchmark 或测试；未生成有效 execution gate、release、运行 inventory、cleanup receipt、report 或 publication；未选择或批准任何后端。

## 5. 永久封口规则

V12 从本处置起永久封口：

- 不得原地修改或修复冻结 source；
- 不得补审后把 V12 改判为 PASS；
- 不得恢复、重跑或重判 V12；
- 不得复用 V12 root、nonce、source、manifest、inventory、digest、audit 或其他 artifact；
- 不得为 V12 创建 gate、release、preflight 或任何执行产物；
- 阶段 1 授权已消费且终止，不得扩展为 V13 授权。

若继续治理，只能在另行书面批准后建立全新 V13 experiment、protocol、随机根、nonce、source、manifest、inventory 与独立审计链。本处置不构成 V13 协议、授权或开工。

## 6. M8 状态

M8 继续保持 **`BLOCKED / NOT_STARTED`**。八项强制 Decision 在本处置形成时全部保持 **`OPEN`**；
`sqlite-linear`、`lancedb-embedded`、`qdrant-client-local` 均未被选择、批准或准入生产。

## 7. 2026-09-10 后续状态

八项强制 Decision 后来经独立批准记录全部 `RESOLVED`，但该政策闭合不修复、恢复或重判 V12，也不选择后端、
批准 M8 admission 或授权生产开工。本处置第 5 节当时提出的全新 V13 后继方向后来同样在未 binding、未建根、
未 source freeze、未获授权且从未执行的状态下永久停止；见
[`m8-v13-disposition-20260910.md`](m8-v13-disposition-20260910.md)。任何后续 M8 实证必须使用全新协议身份，
不得复用 V12 或 V13。
