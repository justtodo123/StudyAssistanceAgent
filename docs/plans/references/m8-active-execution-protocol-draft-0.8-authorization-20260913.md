# M8 active execution protocol `draft-0.8` 修订事后补正记录

> **状态：`RETROACTIVE_CORRECTION / NOT_A_PRIOR_AUTHORIZATION / NOT_EVIDENCE`**
>
> **本文件不是一份授权记录。** 它是一份**事后补正**：如实记载 `draft-0.8` 的修订在**没有事先授权**的情况下
> 已经发生这一事实，并确定其治理地位为 `UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`。本文件不追溯赋予该
> 修订任何正当性，不使其免于审查，也不产生任何执行、准入、绑定或后端选择权限。

- 补正对象：`docs/plans/references/m8-active-execution-protocol-draft-0.8.md`
- 补正日期：2026-09-13
- 负责人：`justtodo123`
- 上游被修订对象：`draft-0.7`，`175826` bytes，
  SHA-256 `45b57530674da2a4375b9d5ed9dc5702a55cf155c3fd3112081f84bb40e618c0`
- 本版字节数：`180033`
- 本版 SHA-256：`b151eea4aacf393599f76606da422d63310d1b04a9af7d0784943f920c33a5b9`
- 修订生成方式：脚本 `apply_draft08_revision.py`（8 处精确字节替换）
- 治理地位：**`UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`**
- 特别说明：本版是 [`draft-0.9` 修订授权记录](m8-active-execution-protocol-draft-0.9-authorization-20260913.md)
  的直接上游依据，因此其未授权状态对 `draft-0.9` 的治理链条有直接影响

## 0. 补正事由

`draft-0.8` 的形成**跳过了 authorization 前置环节**：修订文本已由脚本 `apply_draft08_revision.py` 写出，但
仓库中**不存在**该版对应的授权记录。因此该修订属于**未经事先授权的自行续版**，其流程来源不闭合。

`draft-0.8` 的上游 `draft-0.6`、`draft-0.7` 同样处于未授权状态（见各自补正记录）。**连续三版均无事先授权**，
这是本轮 M8 治理链路上的一段连续缺口，需在本记录中明确。

本文件的作用**仅限于如实补正这一事实**，不追认其正当性。

## 1. 修订内容的事实记载

据 `apply_draft08_revision.py` 的静态文本与 `draft-0.7` → `draft-0.8` 的逐字 diff 重建，本次未授权修订共
**9 个变更块（hunk）、74 行变更**（hunk 数多于脚本 EDITS 数，属插入型替换产生不相邻 diff 块所致），方向如下：

| 编号 | 内容 |
| --- | --- |
| B1 | `STREAM_SCOPE=volume-root` 的判定依据改为 `opens_volume_root` 与 `leaf_kind`（替换语义不匹配的 `authoritative_handle_source`） |
| B2 | 在 §7 建立对 `allowed_system_streams.observation` 的消费逻辑 |
| B3 | 在 `FILE_OPERATION` 中新增 `stream_reverify` / `stream_scope` / `stream_query_source`，使逐操作 stream 复验可在闭合矩阵中表达 |

上述三项依据 `apply_draft08_revision.py` 头注释，**该注释声称 `draft-0.7` 经 P0 审查退回**，但退回记录未落盘，
故这三项仅为**待复核的推定缺陷**。

同时须记载：`apply_draft09_revision.py` 头注释进一步声称 **`draft-0.8` 自身亦经 P0 审查退回**
（推定缺陷 A：scope 被错误固化为 profile 常量；B：`stream_scope` 为单一标量无法表达 per-open 派生；
C：`stream_query_source.handle_source` 允许 `root-directory-handle` 与 §7 冲突）。该退回同样未落盘为独立
记录，属**未核验的推定**。

## 2. 治理地位判定

| 维度 | 判定 |
| --- | --- |
| 事先授权 | **不存在** —— 无 authorization 记录 |
| 负责人发起 | **无法核验** —— 无独立记录可证 |
| 独立 P0 审查 | **未落盘** —— 无审查记录文件，仅有脚本头注释 |
| returned 字节归档 | **不存在** —— 无 `-returned` 副本 |
| 绑定 / 执行 / 准入 | **全部未发生** |
| 最终地位 | **`UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`** |

**本文件不将 `draft-0.8` 转变为已授权版本。** `draft-0.8` 正文仍只作历史追溯。

## 3. 明确不产生的事项

本补正记录不包含、也不得被解释为包含以下任何一项：

- 追溯性授权或追认 `draft-0.8` 的合法性；
- 使 `draft-0.8`、`draft-0.7` 或 `draft-0.6` 免于审查、binding 或处置；
- 为 `draft-0.9` 的授权记录提供授权来源（`draft-0.9` 的授权来源是负责人 2026-09-13 的明确发起行为，
  与本补正记录无关）；
- 创建 experiment ID、executable protocol ID、repository binding、experiment root、nonce 或任何 S/A/G/E 根；
- 授权获取/安装依赖、生成 source/corpus/query/gold、运行 preflight/smoke/full/benchmark、发布证据或写入运行期 artifact；
- 改写 M8 registry、阶段状态或批准字段；准入 M8、批准开工或选择任何专业后端；
- 预先写入任何 P0 审查结论。

## 4. 与 `draft-0.9` 授权记录的关系

[`draft-0.9` 修订授权记录](m8-active-execution-protocol-draft-0.9-authorization-20260913.md) §4 明文禁止
"追溯性补认 `draft-0.6`/`draft-0.7`/`draft-0.8` 或使它们免于审查"。**本补正记录与该禁令一致，不与之冲突**：
本文件不做补认、不给正当性、不免除审查，只是把事实与地位写清。

`draft-0.9` 授权记录 §0 声明其缺陷清单"来自 `apply_draft09_revision.py` 的静态文本，并非来自一份已归档的
`draft-0.8` review 记录"，并因此在本记录中确认该上游缺口。本文件即该缺口的补正动作之一；另一部分为其审查
记录框架 [`draft-0.8` P0 技术审查记录（框架）](m8-active-execution-protocol-draft-0.8-review-20260913.md)。

## 5. 状态边界

本补正记录的形成不改变以下事实：M8 保持 `BLOCKED / NOT_STARTED`；八项 Decision 保持 `RESOLVED`（2026-09-10
已批准）；admission approval 字段保持为空；implementation-start 保持未授权。本文件不提交、不合并、不推送。

Agent 不得自行发起修订、自行批准准入、自行宣布 P0 结论或自行选择后端。
