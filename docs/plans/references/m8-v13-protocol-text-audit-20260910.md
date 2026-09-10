# M8 V13 协议文本审计记录

- 审计对象：[`m8-v13-admission-protocol.md`](m8-v13-admission-protocol.md)
- experiment ID：`sa.m8.admission-evidence.v13`
- protocol：`precommit-v13`
- 审计日期：2026-09-10
- 审计类型：协议文本设计审计（非运行审计、非 source-freeze 后独立静态审计）
- 最终结论：**`PASS_AFTER_REVISION / DRAFT_NOT_AUTHORIZED`**

## 1. 范围与边界

本次只检查仓库内 V13 协议文本的拓扑、顺序、exact-set、失败闭合和可审计性，并在仍处于
`DRAFT / NOT_AUTHORIZED`、尚未创建任何 V13 根或冻结 source 的前提下修订同一 V13 草案。

本次没有创建临时根、root marker、audit root、gate root 或 execution root；没有生成、执行、import 或编译
harness；没有运行 Python、preflight、smoke、full、benchmark 或测试 harness；没有创建 venv、安装/获取依赖、
联网或读取 `D:\111_Others_Subjects`。本记录不构成 V13 root/source authoring 授权、未来独立静态审计 `PASS`、
execution gate、release、运行授权、后端选择或 M8 admission。

## 2. 初审结论

修订前结论为 **`NOT_PASS / REVISION_REQUIRED`**。V13 已覆盖 V12 的四项缺口，但仍有五项协议级机械歧义：

1. source-freeze root 被限制为九文件，但 audit record 和 execution gate 没有独立存放根、allowlist 与跨根绑定；
2. report、publication 与成功 terminal 的前置关系存在循环表述；
3. failure cleanup 没有冻结 delete exact set 与 retained exact set，证据文件可能被误删；
4. primary terminal 与 fallback 的互斥、双文件和双失败判定不唯一；
5. execution root 只有总 allowlist，没有按运行阶段限制文件提前出现。

任一项都会使未来静态审计或运行 verifier 无法仅依据文件拓扑和 digest 得到唯一判断，因此授权前必须修订。

## 3. 修订闭合结果

### 3.1 Audit/gate 存放拓扑：`PASS`

协议现定义互不嵌套的四根：`S` source-freeze、`A` audit、`G` gate、`E` execution。每个根拥有独立随机
basename/nonce、provenance marker、初始 allowlist 和 exact set。audit record 只能位于 `A`，release authorization
与 execution gate 只能位于 `G`；`S` 永久保持九文件。跨根绑定固定为 `S → A → G → E` 单向 digest 链，后根不得
回写前根。

### 3.2 成功终态顺序：`PASS`

成功路径固定为：

`probes → cleanup → residual scan → cleanup receipt → report → verify report → publication → verify publication → terminal(SMOKE_NON_ADMISSION) → verify terminal → stop`

`publication.json` 在 terminal 出现前只是不可采纳的 envelope；terminal 最后绑定 publication 与全部上游 digest，
写入后禁止继续写文件。该顺序没有环形依赖。

### 3.3 Cleanup retained exact set：`PASS`

cleanup 只能删除 runtime inventory 标记的 `ephemeral-runtime` exact set。provenance、inventory、probe、
failure-intent、进入失败前已有的 report/publication、residual scan、receipt 和 terminal witness 必须保留。
`zero_residual` 明确定义为“临时运行数据零残留”，不是“execution root 为空”；独立审计可以回读原文件并重算 digest。

### 3.4 Primary/fallback 排他：`PASS`

正常路径只能存在有效 `terminal.json`。fallback 只有在 primary create/write/fsync/read-back/validation 失败时才可
出现，且只能声明 `INVALID`。有效 primary 与任何 fallback 同存为 `INVALID_DUAL_TERMINAL`；无效/partial primary
与有效 fallback 同存时，fallback 只证明 `INVALID`。两者均缺失或不可验证时，verifier 固定输出
`UNVERIFIABLE_TERMINAL` 并使用退出码 `97`，不得采纳 report/publication。

### 3.5 Execution 阶段 exact set：`PASS`

协议现定义成功阶段 `E0_PROVENANCE` 至 `E6_SUCCESS`，以及由 `entered_from_stage` 推导的失败阶段
`F1_INTENT` 至 `F3_TERMINAL`。总 allowlist 不再等同于阶段许可；failure、cleanup、report、publication、terminal
提前出现或跳级均可由文件集合机械判为 `INVALID`。

## 4. 最终结论

五项初审缺口均已在同一 V13 草案中闭合，协议文本设计结论为
**`PASS_AFTER_REVISION / DRAFT_NOT_AUTHORIZED`**。该 PASS 只说明当前文档对本次五项检查具有单一、无环、可机械
审计的设计，不证明未来 source 实现正确，也不替代 source freeze 后由独立会话完成的静态审计。

V13 在本次审计形成时仍为 `DRAFT / NOT_AUTHORIZED`，M8 仍为 `BLOCKED / NOT_STARTED`，八项 Decision 仍为
`OPEN`。由于审计和修订发生在任何 V13 授权、建根或 source freeze 之前，本次当时无需递增到 V14；一旦发生上述
任一冻结事件，实质协议变更必须使用新身份。

## 5. 2026-09-10 后续状态

本记录的 `PASS_AFTER_REVISION` 只保留为当时协议文本设计审计事实，从未产生 repository binding、建根、source
freeze、source-freeze 后独立静态审计 `PASS` 或执行授权。八项 M8 Decision 后来另行全部 `RESOLVED`，但 M8 继续
`BLOCKED / NOT_STARTED`；V13 也后来处置为
[`SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`](m8-v13-disposition-20260910.md)。V13 不得再修订、
binding、建根、授权、执行或复用；任何后续 M8 实证必须使用全新协议身份。
