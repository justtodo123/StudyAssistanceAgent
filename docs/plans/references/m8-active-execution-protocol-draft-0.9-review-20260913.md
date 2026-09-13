# M8 active execution protocol `draft-0.9` P0 技术审查记录

> **状态：`COMPLETED / AI_ASSISTED_MECHANICAL_REVIEW / NOT_EVIDENCE_OF_CORRECTNESS`**
>
> 本文件由独立进程 `tools/m8_draft_reviewer.py` 机械核验后生成。**审查者不是人类 reviewer，而是一个与起草脚本
> 无导入关系的独立程序**；其结论为 `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`。签名时点见 §6。
>
> 需特别声明：本审查**不是**人类独立 reviewer 的审查，也未满足项目对“起草方与审查方分离”的人类组织性要求；
> 它只是在可机械判定的范围内重建了事实并给出一致性结论。该结论**不产生任何执行、准入或后端权限**。

- 审查对象：`docs/plans/references/m8-active-execution-protocol-draft-0.9.md`
- 被审字节数：`182575`
- 被审 SHA-256：`162c9047ddeaceda59d7da79f8dfbf45234a89e2b00fd271e72473bbc6cca5b4`
- 上游被审对象：`draft-0.8`，`180033` bytes，
  SHA-256 `b151eea4aacf393599f76606da422d63310d1b04a9af7d0784943f920c33a5b9`
- 上游缺陷依据：`apply_draft09_revision.py` 头注释与本仓库 §2.1（`draft-0.8` 审查记录）
- 审查日期：2026-09-13
- 审查范围依据：[`m8-active-execution-protocol-draft-0.9-authorization-20260913.md`](m8-active-execution-protocol-draft-0.9-authorization-20260913.md)
- 审查类型：P0 技术口径审查（仅技术文字；不产生任何执行权限）
- 审查者独立性：**部分成立** —— 由独立进程 `tools/m8_draft_reviewer.py` 执行，该程序不导入任何起草脚本，
  所有事实由协议 blob 自身重新推导；但审查者为程序而非人类 reviewer，人类组织性独立性仍不成立。

## 0. 审查模型说明

`draft-0.9` 是当前链条的末端版本（尚无后继草案）。因此本审查**不采用** `draft-0.6`/`0.7`/`0.8` 所用的
“残留缺陷猎取”模型（那需要以后继版本定义残留集合），而改用末端核验模型，同时回答两个问题：

1. **claimed repairs**：本版声称处理的 `draft-0.8` 缺陷 A/B/C/D 是否全部机械闭合？
2. **retained invariants**：整条链（`draft-0.6` 起引入）的既有设计骨架是否仍然成立且未被破坏？

只有两者全部成立才判 `PASS`。两项判定均针对**协议正文**，标题的修订说明注释（`> ` 开头行）被排除在
schema 断言之外，以免变更日志文字误满足或误违反任何字段级检查。

## 1. 结论

**`PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`**

`draft-0.9` 被审的精确字节通过 P0 技术口径机械核验：`draft-0.8` 的三项阻断缺陷（A scope 固化、B
`stream_scope` 标量、C 查询来源冲突）与 D 项两处清理（`allowed_system_streams_closed` 装饰字段、不可达的
`stream_reverify=not-applicable`）全部机械闭合，且整条链的保留不变量全部成立。

该结论只表示技术文字在机械范围内被接受，**不产生任何 M8 执行、准入、发布或后端选择权限**：

- 不构成 experiment ID、executable protocol ID、repository binding、experiment root、nonce 或任何 S/A/G/E 根；
- 不授权获取/安装依赖、生成 source/corpus/query/gold、运行 preflight/smoke/full/benchmark、发布证据或写入运行期 artifact；
- 不改变 M8 registry 与阶段状态，不构成 M8 admission，也不构成对 LanceDB/Qdrant/Milvus 或任何后端的选择；
- P1–P9/P7A 仍须各自另行形成满足前置关系的外部记录，任何一步都不得由本结论自动推导。

> 一致性与边界说明：本结论由程序机械得出，与 `draft-0.9` 授权记录 §1 所列 A/B/C/D 四项逐项对应。它**不**
> 提升 `draft-0.9` 的治理地位——该版的上游 `draft-0.6`–`draft-0.8` 仍为 `NEVER_AUTHORIZED`，`draft-0.9`
> 自身仍为未绑定、未授权、从未执行的 protocol blob。

## 2. 缺陷闭合判定

| 编号 | `draft-0.8` 缺陷 | 判定 | 依据（机械核验） |
| --- | --- | --- | --- |
| A | scope 被错误固化为 profile 常量，而 `parent-walk` 逐级打开 volume root 与普通目录，一个 profile 无法承载两种对象 | **CLOSED** | 正文含 `` `STREAM_SCOPE` 是 **per-open** 的 ``；`NT_OPEN_PROFILE` 已无 `opens_volume_root`；§7 要求 walk 开始时先冻结起始卷根 handle 与其 `FILE_IDENTITY`，逐次 open 与之比对 |
| B | `stream_scope` 为单一标量（`derived-from-profile`），无法表达 per-open 派生 | **CLOSED** | 单一标量字段已由 `stream_scope_per_open:"required"` 取代；已无 `stream_scope:oneOf[literal["derived-from-profile"]` |
| C | `stream_query_source.handle_source` 允许 `root-directory-handle`，与 §7 正文冲突 | **CLOSED** | `stream_query_source` 现为 `oneOf[literal["not-applicable"],{information_class:"FileStreamInformation",api:"NtQueryInformationFile",handle_source:"opened-file-handle"}]`，来源仅 `opened-file-handle` |
| D-1 | 装饰字段 `allowed_system_streams_closed` 被声明但无校验点消费 | **CLOSED** | 正文（排除修订注释行后）已无该字段 |
| D-2 | 不可达成员 `stream_reverify=not-applicable` 在 enum 中保留 | **CLOSED** | 已无 `stream_reverify:enum[`；改为逐字常量 `stream_reverify:"required"` |

**注意（避免误判）**：`authoritative_handle_source` 是**另一个独立字段**，在 §7 中仍合法地取
`enum[root-directory-handle,opened-file-handle]`。C 项只约束 `stream_query_source.handle_source`，不约束
`authoritative_handle_source`。本核验针对后者字段名精确匹配，未误伤。

## 3. 保留不变量核查（整条链）

下列设计骨架自 `draft-0.6` 引入、经 `0.7`/`0.8` 传承，在 `draft-0.9` 中**全部成立**：

| 不变量 | 判定 |
| --- | --- |
| `STREAM_SCOPE` 仍为三值闭合枚举 `enum[file,directory,volume-root]` | **HOLDS** |
| `SYSTEM_RESERVED_STREAM` 仍恰有一处定义（未重复引入） | **HOLDS** |
| `allowed_system_streams` 基数仍为派生常量 `3..3`，按 `scope` 为键 | **HOLDS** |
| `observation` 仍被 §7 消费（`并按该行的 observation 判定`） | **HOLDS** |
| `FileStreamInformation` 仍为流清单的查询信息类 | **HOLDS** |
| interposition 的 ADS carve-out 保留（列入 allowlist 的系统保留流不算 ADS） | **HOLDS** |
| 卷根身份经 `NtQueryInformationFile(FileIdInformation)` 在 `opened-file-handle` 上取得，并与冻结 `FILE_IDENTITY` 逐字段比对 | **HOLDS** |

## 4. 冻结字节不变量核查

`sa.m8.status-map.v1.payload` 的映射表在 `draft-0.5` 至 `draft-0.9` 中：

- 行数恒为 **72 行**；
- 逐行文本**完全一致**（与 `draft-0.5` 基线机械比对通过）；
- `entries:72..72` 与 `required_stable_codes:72..72` 基数未变。

这延续了 `draft-0.5` 审查记录所确认的“72 行映射表逐字节未变”这一关键不变量。

## 5. 修订范围统计

`draft-0.8` → `draft-0.9` 的逐字 diff：

- 变更行数：`89`
- 变更块（hunk）数：`13`
- 与 `apply_draft09_revision.py` 的 10 处 EDITS：hunk 数多于 EDITS 数，因插入型替换在文本中产生多个不相邻
  diff 块所致；已逐 hunk 归类，无未归类改动。

**未越界**：本次修订未触及状态机、deadline、§10.1 的 26 项技术门禁，未改动 72 行表。

## 6. 签署

- 审查者：`tools/m8_draft_reviewer.py`（独立进程，未导入任何 `apply_draft0X_revision.py`）
- 审查者类型：**AI / 程序化机械核验**（非人类独立 reviewer）
- 独立性声明：程序与起草脚本无导入或调用关系，所有事实（字节、摘要、72 行表、缺陷字段、保留不变量）均由
  协议 blob 自身重新推导，不采信起草脚本的任何断言；但**人类组织意义上的起草/审查分离未成立**。
- 审查完成日期：2026-09-13
- 结论：**`PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`**

## 7. 零授权与后续前置关系

被审文本仍写明其自身不授权创建 identity/binding/root、获取或安装依赖、生成 source、运行 preflight 或
benchmark、发布证据、改变 M8 registry、准入 M8、选择后端或生产开工。本审查确认该条款未被削弱。

`draft-0.9` 取得本次机械 PASS 后仍为**未绑定、未授权、从未执行**的 protocol blob。M8 保持
`BLOCKED / NOT_STARTED`；八项 Decision 保持 `RESOLVED`（2026-09-10）；admission approval 字段保持为空；
implementation-start 保持未授权。

本文件不提交、不合并、不推送（除非另行取得明确授权）。
