# M8 V12 历史独立静态审计 PASS 记录（已失效）

> **`INVALIDATED / SUPERSEDED BY INDEPENDENT FAIL`**
>
> 本记录保留 `2026-09-09T11:32:50Z` 初次独立审计当时的 `PASS` 判断与输入摘要，仅用于历史追溯。
> `2026-09-09T12:12:34Z` 的全新独立只读审计发现四项阻断缺陷并给出 `FAIL`，因此本记录及其
> audit digest 自该时起失效，不得用于 execution gate、release、preflight、执行、后端选择或 M8 admission。
> 现行审计结论见
> [`m8-v12-independent-static-audit-fail-20260909.md`](m8-v12-independent-static-audit-fail-20260909.md)，
> 永久处置见 [`m8-v12-disposition-20260909.md`](m8-v12-disposition-20260909.md)。

- experiment ID：`sa.m8.admission-evidence.v12`
- protocol：`precommit-v12`
- 审计目标：冻结根 `sa-m8-v12-9fd8842953bd49b6924428a8461a5b1c`
  （`C:\Users\Lenovo\AppData\Local\Temp\sa-m8-v12-9fd8842953bd49b6924428a8461a5b1c`）
- 审计类型：独立静态只读审计
- 审计 UTC：`2026-09-09T11:32:50Z`
- 冻结 UTC（作者侧）：`2026-09-09T10:21:13Z`
- 历史审计结论：**`PASS`（已失效，不得采用）**
- 历史 audit digest：
  `81b23dbbbc8a23b024eee7c1d7cec589efacb3744abb463de173f63a10d8743b`
  （已失效，不得作为 gate 或授权输入）

## 审计者独立性声明

本记录描述初次独立会话当时的审计输入和判断。后续 FAIL 审计未读取、引用或采用本文，故其独立性不受本文影响。
本文不再代表现行结论，也不得通过改写正文把后续发现伪装成首次审计当时已经给出的判断。

## 历史审计输入 digest

- marker（`root-provenance.json`）SHA-256：
  `746c7bd7c0ebb783dedb4a25ad08abfb2afcd1120ad408db5dfb39c43eaba7ce`
- source records SHA-256：
  `8f1477622dcc0795a9924814f689b6498b0bcb31fdb404d516c919180bf70e71`
- source manifest SHA-256：
  `22c2a544fdacf1829dc1fa0f4e13f6b9d4e99be52f15f5ca3f1ec46d68b38df7`
- inventory self-digest：
  `200fd331c2c1f72d0fb1b9a28bc7d9a91d42b359ec06607fb8d8b1b55cf883ae`

## 历史判断摘要

初次审计确认了冻结根身份、九文件集合、canonical JSON、自摘要、source records digest、
manifest/inventory 交叉绑定、阶段 1 文件元数据以及静态网络边界，并据此给出 `PASS`。
该判断未识别后续独立审计确认的以下机械证据缺口：

1. tombstone 前目标可见性未证明；
2. hard-delete 后剩余检索连续性未证明；
3. 运行期 hard-link count 与 ADS 门禁缺失；
4. 异常路径缺少可机械证明的失败终态、失败 cleanup 与 residual scan。

因此，历史 `PASS` 仅说明首次审计者当时的判断，不再具有规范性、门禁性或授权效力。

## 历史边界

初次静态审计没有运行 generated Python、preflight、smoke、full、benchmark 或测试，没有创建 venv、gate、receipt、report、publication 或运行产物，也没有选择或批准任何后端。
冻结态无法重放 marker 后、source 前根状态的历史时序，也不能证明三后端运行结果、cleanup zero-residual 或第三方库运行时行为。

## 现行效力

现行结论仅以新的独立 `FAIL` 报告和 V12 disposition 为准。本历史记录不得解释为：

- V12 已通过静态审计；
- 可以创建 execution gate 或 release；
- 可以运行 preflight、创建 venv、获取依赖或执行 smoke/full/benchmark；
- 任一候选后端已被选择或批准；
- M8 已启动、准入或解除阻断；
- 可以修复、恢复、重跑、重判或复用 V12。

## 2026-09-10 后续状态

八项 M8 Decision 后来全部 `RESOLVED`，V13 也后来处置为
`SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`。两项后续事实均不恢复本记录的效力，不改变
`2026-09-09T11:32:50Z` 初次判断的历史内容，也不推翻 `2026-09-09T12:12:34Z` 独立 `FAIL` 的现行结论。
V12 继续永久封口；未来实证必须使用全新协议身份。
