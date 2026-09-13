# M8 active execution protocol `draft-0.8` P0 技术审查记录

> **状态：`COMPLETED / AI_ASSISTED_MECHANICAL_REVIEW / NOT_EVIDENCE_OF_CORRECTNESS`**
>
> 本文件由独立进程 `tools/m8_draft_reviewer.py` 机械核验后填充。**审查者不是人类 reviewer，而是一个与起草脚本
> 无导入关系的独立程序**；其结论为 `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`。签名时点见 §6。
>
> 需特别声明：本审查**不是**人类独立 reviewer 的审查，也未满足项目对“起草方与审查方分离”的人类组织性要求。
>
> **本文件是 `draft-0.9` 修订授权的直接上游依据。** 在独立 reviewer 完成本框架前，
> [`draft-0.9` 授权记录](m8-active-execution-protocol-draft-0.9-authorization-20260913.md) §0 所述缺口仍未闭合。

- 审查对象：`docs/plans/references/m8-active-execution-protocol-draft-0.8.md`
- 被审字节数：`180033`
- 被审 SHA-256：`b151eea4aacf393599f76606da422d63310d1b04a9af7d0784943f920c33a5b9`
- 上游被审对象：`draft-0.7`，`175826` bytes，
  SHA-256 `45b57530674da2a4375b9d5ed9dc5702a55cf155c3fd3112081f84bb40e618c0`
- 修订生成方式：脚本 `apply_draft08_revision.py`（8 处精确字节替换）
- 审查日期：2026-09-13
- 审查范围依据：**无独立 authorization 记录**；见
  [`m8-active-execution-protocol-draft-0.9-authorization-20260913.md`](m8-active-execution-protocol-draft-0.9-authorization-20260913.md) §0 所述治理缺口
- 审查类型：P0 技术口径审查（仅技术文字；不产生任何执行权限）
- 审查者独立性：**部分成立** —— 由独立进程 `tools/m8_draft_reviewer.py` 执行，不导入起草脚本；但审查者为
  程序而非人类 reviewer，人类组织性独立性仍不成立

## 0. 缺口声明

`draft-0.8` 在形成时**未落盘**独立 P0 审查记录。本文件据 `apply_draft08_revision.py` 的静态文本与逐字节
diff 重建事实，并由独立进程 `tools/m8_draft_reviewer.py` 对协议 blob 重新推导后给出结论（见 §1、§6）。
该结论为**程序化机械核验**结果，不等于人类独立 reviewer 的技术认可。

`draft-0.9` 的授权记录以本版的三项缺陷清单为上游依据；本文件即 `draft-0.9` 授权记录 §0 所述缺口的关键
补环，但**不**为 `draft-0.9` 提供授权来源。

## 1. 结论

**`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**

机械核验结果：`draft-0.8` 已修复其声称处理的 `draft-0.7` 三项缺陷（B1–B3），但**残留 3 项阻断缺陷**
（§2.1 的 A/B/C）与 2 项非阻断残留（a/b），因此判为退回。该结论不产生任何执行、准入、发布或后端选择
权限。

> 一致性说明：本结论与 `apply_draft09_revision.py` 头注释所声称的“`draft-0.8` 经 P0 审查退回”**方向一致**，
> 且本文件的残留缺陷清单与 `draft-0.9` 实际修复的 A/B/C/D 项逐项对应。本文件即 `draft-0.9` 授权记录 §0
> 所述缺口的关键补环。

## 2. 缺陷闭合判定

本版修订自 `draft-0.7` 定点处理下列 3 项阻断缺陷（依据 `apply_draft08_revision.py` 头注释与 diff 重建）：

| 编号 | 推定缺陷 | 采用方案 | 判定（机械核验） |
| --- | --- | --- | --- |
| B1 | `STREAM_SCOPE=volume-root` 的判定依据引用了语义不匹配的 `authoritative_handle_source` | 引入 `opens_volume_root` | **已修复** |
| B2 | `allowed_system_streams.observation` 被声明但无任何校验点消费 | 在 §7 建立消费逻辑 | **已修复** |
| B3 | §7 要求的逐操作 stream 复验无法在闭合矩阵中表达 | 新增 `stream_reverify` / `stream_scope` / `stream_query_source` | **已修复** |

### 2.1 残留缺陷（本版仍存在）

**阻断（三项，均由 `draft-0.9` 修复）：**

| 编号 | 残留缺陷（阻断） | 证据 |
| --- | --- | --- |
| A | scope 被错误固化为 profile 常量，而 `parent-walk` 逐级打开 volume root 与普通目录，一个 profile 无法承载两种对象 | 正文无 `per-open` |
| B | `stream_scope` 为单一标量（`derived-from-profile`），无法表达 per-open 派生 | `stream_scope:oneOf[literal["derived-from-profile"]` |
| C | `stream_query_source.handle_source` 允许 `root-directory-handle`，与 §7 正文冲突 | `handle_source:enum[root-directory-handle,opened-file-handle]` |

**非阻断（两项，由 `draft-0.9` 的 D 项清理）：**

| 编号 | 残留缺陷（非阻断） | 证据 |
| --- | --- | --- |
| a | 装饰字段 `allowed_system_streams_closed` 被声明但无校验点消费 | `allowed_system_streams_closed` |
| b | 不可达成员 `stream_reverify=not-applicable` 在 enum 中保留 | `stream_reverify:enum[required,not-applicable]` |

## 3. 范围合规

`draft-0.7` → `draft-0.8` 的逐字 diff 统计（机械核验，可复现）：

- 变更行数：`74`
- 变更块（hunk）数：`9`
- 与 `apply_draft08_revision.py` 的 8 处 EDITS：hunk 数多于 EDITS 数，属插入型替换产生多个不相邻 diff 块
  所致；已逐 hunk 归类，无未归类改动

| hunk | 位置（推定） | 归类 |
| --- | --- | --- |
| 1 | 头部版本号与修订依据（一）（二）（三） | 版本同步 |
| 2 | §2.2 `STREAM_SCOPE` 判定依据改为 `opens_volume_root` 与 `leaf_kind` | B1 |
| 3 | `NT_OPEN_PROFILE` 新增 `opens_volume_root:BOOL` | B1 |
| 4 | `opens_volume_root` 的逐 profile 取值说明 | B1 |
| 5 | `FILE_OPERATION` 新增 `stream_reverify` / `stream_scope` / `stream_query_source` | B3 |
| 6 | 三个新字段的逐 operation 取值说明 | B3 |
| 7 | allowlist 增列 `allowed_system_streams_closed:true` | B2 |
| 8 | §7 改写以消费 `observation` 与强制复验 | B2 + B3 |
| 9 | §7 与 FILE_OPERATION 说明段的机械连带 | B2 + B3 连带 |

**冻结字节不变量核查（已机械核验）**：72 行映射表在 `draft-0.7` 与 `draft-0.8` 中均为 72 行且逐行文本完全
一致；`entries:72..72` / `required_stable_codes:72..72` 未变。

**修订范围统计（已机械核验）**：`draft-0.7` → `draft-0.8` 共 **9 个 hunk、74 行变更**（hunk 数多于脚本 8 处
EDITS，因插入型替换产生不相邻 diff 块）。

## 4. 新缺陷与遗留观察（已填充）

机械核验判定 `draft-0.8` 残留 3 项阻断缺陷（A/B/C）与 2 项非阻断残留（a/b），见 §2.1。三项阻断缺陷与
`apply_draft09_revision.py` 头注释所称的 A/B/C **逐项对应**。

**对 D 项的判定**：`allowed_system_streams_closed` 与 `stream_reverify=not-applicable` 在本版中存在，但**未
构成阻断缺陷**——前者是无可消费点的装饰字段，后者是不可达的 enum 成员，二者不影响可执行性，属应当清理的
冗余项。它们由 `draft-0.9` 的 D 项一并清理。

**非阻断观察**：

1. `draft-0.8` 将 `opens_volume_root` 作为 scope 判定依据，方向是对“可机械判定”的改进，但引入了新的语义
   错位（profile 常量无法覆盖 `parent-walk` 的多对象场景），即缺陷 A；
2. 未触及 72 行表、状态机或 §10.1 门禁；无越界改动；
3. 因 `draft-0.8` 本身处于 `NEVER_AUTHORIZED`，本审查不对其正当性作任何判断，也不为 `draft-0.9` 提供
   授权来源。

## 5. 零授权与后续前置关系

被审文本仍写明其自身不授权创建 identity/binding/root、获取或安装依赖、生成 source、运行 preflight 或
benchmark、发布证据、改变 M8 registry、准入 M8、选择后端或生产开工。本框架不改变该条款。

`draft-0.8` 即使取得 P0 结论，仍为未绑定、未授权、从未执行的 protocol blob；不得 binding 或授权。
M8 保持 `BLOCKED / NOT_STARTED`；八项 Decision 保持 `RESOLVED`。

## 6. 签署

- 审查者：`tools/m8_draft_reviewer.py`（独立进程，未导入任何 `apply_draft0X_revision.py`）
- 审查者类型：**AI / 程序化机械核验**（非人类独立 reviewer）
- 独立性声明：程序与起草脚本无导入或调用关系，所有事实由协议 blob 自身重新推导；但**人类组织意义上的
  起草/审查分离未成立**。
- 审查完成日期：2026-09-13
- 结论：**`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**（3 项残留阻断缺陷 + 2 项非阻断残留）

> 本文件不提交、不合并、不推送（除非另行取得明确授权）。
